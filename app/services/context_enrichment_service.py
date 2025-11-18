"""
Context Enrichment Service

Aggregates contextual information from multiple sources (backend APIs and local database)
to provide comprehensive context for conducting context-aware interviews.

This service implements parallel fetching, caching, and graceful degradation
to ensure interviews can proceed even when some context sources are unavailable.
"""
import logging
import asyncio
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.clients.backend_client import BackendClient
from app.services.context_cache import ContextCache
from app.models.context import (
    EmployeeContextData,
    RoleContextData,
    ProcessContextData,
    InterviewHistorySummary,
    InterviewContextData
)
from app.models.db_models import Interview, InterviewStatusEnum
from app.config import settings

logger = logging.getLogger(__name__)


class ContextEnrichmentService:
    """
    Service for aggregating interview context from multiple sources.
    
    Fetches and combines:
    - Employee profile and roles from backend
    - Organization processes from backend
    - Interview history from local database
    
    Implements caching and graceful degradation for reliability.
    """
    
    def __init__(
        self,
        backend_client: Optional[BackendClient] = None,
        cache: Optional[ContextCache] = None,
        cache_ttl: int = 300
    ):
        """
        Initialize context enrichment service.
        
        Args:
            backend_client: HTTP client for backend API (creates default if None)
            cache: Context cache instance (creates default if None)
            cache_ttl: Cache TTL in seconds (default: 300 = 5 minutes)
        """
        self.backend_client = backend_client or BackendClient()
        self.cache = cache or ContextCache(ttl_seconds=cache_ttl)
        logger.info("ContextEnrichmentService initialized")
    
    async def get_full_interview_context(
        self,
        employee_id: UUID,
        organization_id: str,
        auth_token: str,
        db: AsyncSession
    ) -> InterviewContextData:
        """
        Get complete context for starting an interview.
        
        Fetches employee, organization processes, and interview history in parallel
        for optimal performance. Uses caching to reduce backend API calls.
        
        Args:
            employee_id: UUID of the employee being interviewed
            organization_id: ID of the organization (from JWT token)
            auth_token: JWT token for backend authentication
            db: Database session for querying interview history
            
        Returns:
            InterviewContextData with all available context
            
        Note:
            Implements graceful degradation - returns partial context if some
            sources fail. Never raises exceptions to avoid blocking interviews.
        """
        logger.info(f"[PERF] Starting context loading for employee {employee_id}")
        start_time = datetime.utcnow()
        
        try:
            # Fetch employee context and interview history in parallel
            employee_start = datetime.utcnow()
            employee_task = self.get_employee_context(employee_id, organization_id, auth_token)
            history_task = self.get_interview_history_summary(employee_id, db)
            
            employee_context, interview_history = await asyncio.gather(
                employee_task,
                history_task,
                return_exceptions=True
            )
            employee_elapsed = (datetime.utcnow() - employee_start).total_seconds()
            
            # Handle exceptions from parallel tasks
            if isinstance(employee_context, Exception):
                logger.error(
                    f"[ERROR] Failed to fetch employee context for {employee_id}: "
                    f"{type(employee_context).__name__}: {str(employee_context)}",
                    extra={
                        "employee_id": str(employee_id),
                        "error_type": type(employee_context).__name__,
                        "elapsed_seconds": employee_elapsed
                    }
                )
                # Cannot proceed without employee context
                raise employee_context
            
            if isinstance(interview_history, Exception):
                logger.warning(
                    f"[ERROR] Failed to fetch interview history for {employee_id}: "
                    f"{type(interview_history).__name__}: {str(interview_history)}",
                    extra={
                        "employee_id": str(employee_id),
                        "error_type": type(interview_history).__name__,
                        "fallback": "empty_history"
                    }
                )
                # Use empty history as fallback
                interview_history = InterviewHistorySummary()
            
            logger.info(
                f"[PERF] Employee context and history loaded in {employee_elapsed:.3f}s",
                extra={
                    "employee_id": str(employee_id),
                    "elapsed_seconds": employee_elapsed,
                    "roles_count": len(employee_context.roles)
                }
            )
            
            # Fetch organization processes (requires organization_id from employee)
            processes_start = datetime.utcnow()
            organization_processes = await self.get_organization_processes(
                organization_id=employee_context.organization_id,
                auth_token=auth_token,
                limit=settings.max_processes_in_context
            )
            processes_elapsed = (datetime.utcnow() - processes_start).total_seconds()
            
            logger.info(
                f"[PERF] Organization processes loaded in {processes_elapsed:.3f}s",
                extra={
                    "organization_id": employee_context.organization_id,
                    "processes_count": len(organization_processes),
                    "elapsed_seconds": processes_elapsed
                }
            )
            
            # Assemble complete context
            context = InterviewContextData(
                employee=employee_context,
                organization_processes=organization_processes,
                interview_history=interview_history,
                context_timestamp=datetime.utcnow()
            )
            
            total_elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.info(
                f"[PERF] Context loading completed for employee {employee_id} "
                f"in {total_elapsed:.3f}s",
                extra={
                    "employee_id": str(employee_id),
                    "total_elapsed_seconds": total_elapsed,
                    "processes_count": len(organization_processes),
                    "interviews_count": interview_history.total_interviews,
                    "roles_count": len(employee_context.roles),
                    "performance_target_met": total_elapsed < 2.0
                }
            )
            
            return context
            
        except Exception as e:
            total_elapsed = (datetime.utcnow() - start_time).total_seconds()
            logger.error(
                f"[ERROR] Context loading failed for employee {employee_id}: "
                f"{type(e).__name__}: {str(e)}",
                extra={
                    "employee_id": str(employee_id),
                    "error_type": type(e).__name__,
                    "elapsed_seconds": total_elapsed
                }
            )
            raise
    
    async def get_employee_context(
        self,
        employee_id: UUID,
        organization_id: str,
        auth_token: str
    ) -> EmployeeContextData:
        """
        Get employee profile including roles.
        
        Fetches employee details and roles from backend, with caching.
        
        Args:
            employee_id: UUID of the employee
            organization_id: ID of the organization (from JWT token)
            auth_token: JWT token for backend authentication
            
        Returns:
            EmployeeContextData with profile and roles
            
        Raises:
            Exception: If employee cannot be fetched (critical failure)
        """
        logger.debug(f"Fetching employee context for {employee_id}")
        
        # Check cache first
        cached = self.cache.get("employee", employee_id)
        if cached:
            logger.debug(
                f"[CACHE] Cache HIT for employee {employee_id}",
                extra={"cache_key": f"employee:{employee_id}", "cache_hit": True}
            )
            return EmployeeContextData(**cached)
        
        logger.debug(
            f"[CACHE] Cache MISS for employee {employee_id}",
            extra={"cache_key": f"employee:{employee_id}", "cache_hit": False}
        )
        
        # Fetch from backend
        backend_start = datetime.utcnow()
        employee_data = await self.backend_client.get_employee(
            employee_id=employee_id,
            organization_id=organization_id,
            auth_token=auth_token
        )
        backend_elapsed = (datetime.utcnow() - backend_start).total_seconds()
        
        if not employee_data:
            logger.error(
                f"[ERROR] Employee {employee_id} not found in backend",
                extra={
                    "employee_id": str(employee_id),
                    "backend_call": "get_employee",
                    "success": False,
                    "elapsed_seconds": backend_elapsed
                }
            )
            raise ValueError(f"Employee {employee_id} not found")
        
        logger.debug(
            f"[BACKEND] Successfully fetched employee {employee_id}",
            extra={
                "employee_id": str(employee_id),
                "backend_call": "get_employee",
                "success": True,
                "elapsed_seconds": backend_elapsed
            }
        )
        
        # Extract organization ID and role IDs
        organization_id = employee_data.get("organizationId")
        if not organization_id:
            logger.error(
                f"[ERROR] Employee {employee_id} has no organization",
                extra={
                    "employee_id": str(employee_id),
                    "error": "missing_organization_id"
                }
            )
            raise ValueError(f"Employee {employee_id} has no organization")
        
        # Get role IDs from employee data
        role_ids = employee_data.get("roleIds", [])
        
        # Fetch organization and all roles in parallel
        fetch_tasks = [
            self.backend_client.get_organization(
                organization_id=organization_id,
                auth_token=auth_token
            )
        ]
        
        # Add tasks to fetch each role
        for role_id in role_ids:
            fetch_tasks.append(
                self.backend_client.get_role(
                    organization_id=organization_id,
                    role_id=role_id,
                    auth_token=auth_token
                )
            )
        
        # Execute all fetches in parallel
        results = await asyncio.gather(*fetch_tasks, return_exceptions=True)
        
        # First result is organization
        org_data = results[0] if results else None
        # Rest are roles
        roles_results = results[1:] if len(results) > 1 else []
        
        logger.debug(f"[DEBUG] Organization fetch result type: {type(org_data)}, value: {org_data}")
        
        # Handle organization fetch failure
        if isinstance(org_data, Exception) or not org_data:
            logger.warning(
                f"[ERROR] Failed to fetch organization {organization_id}, using ID only",
                extra={
                    "organization_id": organization_id,
                    "backend_call": "get_organization",
                    "success": False,
                    "error_type": type(org_data).__name__ if isinstance(org_data, Exception) else "not_found",
                    "fallback": "organization_id_as_name"
                }
            )
            organization_name = organization_id
        else:
            # Backend returns 'businessName' not 'name'
            organization_name = org_data.get("businessName", org_data.get("name", organization_id))
            logger.debug(
                f"[BACKEND] Successfully fetched organization {organization_id}, name: {organization_name}",
                extra={
                    "organization_id": organization_id,
                    "organization_name": organization_name,
                    "backend_call": "get_organization",
                    "success": True
                }
            )
        
        # Process roles results
        roles_data = []
        for role_result in roles_results:
            if isinstance(role_result, Exception):
                logger.warning(
                    f"[ERROR] Failed to fetch a role for employee {employee_id}",
                    extra={
                        "employee_id": str(employee_id),
                        "error_type": type(role_result).__name__,
                        "fallback": "skip_role"
                    }
                )
                continue
            elif role_result:
                roles_data.append(role_result)
        
        logger.debug(
            f"[BACKEND] Successfully fetched {len(roles_data)} roles for employee {employee_id}",
            extra={
                "employee_id": str(employee_id),
                "success": True,
                "roles_count": len(roles_data)
            }
        )
        
        # Build employee context
        first_name = employee_data.get("firstName", "")
        last_name = employee_data.get("lastName", "")
        full_name = f"{first_name} {last_name}".strip() or "Unknown"
        
        roles = [
            RoleContextData(
                id=UUID(role["id"]),
                name=role.get("name", "Unknown Role"),
                description=role.get("description")
            )
            for role in roles_data
            if "id" in role
        ]
        
        employee_context = EmployeeContextData(
            id=employee_id,
            first_name=first_name,
            last_name=last_name,
            full_name=full_name,
            organization_id=organization_id,
            organization_name=organization_name,
            roles=roles,
            is_active=employee_data.get("isActive", True)
        )
        
        # Cache the result
        self.cache.set("employee", employee_id, employee_context.model_dump())
        
        logger.debug(
            f"Fetched employee context for {employee_id}: "
            f"{full_name}, {len(roles)} roles"
        )
        
        return employee_context
    
    async def get_organization_processes(
        self,
        organization_id: str,
        auth_token: str,
        limit: int = 20
    ) -> List[ProcessContextData]:
        """
        Get existing processes for organization with filtering.
        
        Fetches active processes, sorted by most recently updated.
        Uses caching to reduce backend load.
        
        Args:
            organization_id: ID of the organization
            auth_token: JWT token for backend authentication
            limit: Maximum number of processes to return (default: 20)
            
        Returns:
            List of ProcessContextData (empty list if none or error)
            
        Note:
            Never raises exceptions - returns empty list on failure
            to allow interviews to proceed without process context.
        """
        logger.debug(
            f"Fetching organization processes for {organization_id} (limit: {limit})"
        )
        
        # Check cache first
        cache_key = UUID(int=hash(organization_id) & 0xFFFFFFFFFFFFFFFF)
        cached = self.cache.get("processes", cache_key)
        if cached:
            logger.debug(
                f"[CACHE] Cache HIT for organization processes {organization_id}",
                extra={
                    "cache_key": f"processes:{cache_key}",
                    "cache_hit": True,
                    "organization_id": organization_id,
                    "processes_count": len(cached)
                }
            )
            return [ProcessContextData(**p) for p in cached]
        
        logger.debug(
            f"[CACHE] Cache MISS for organization processes {organization_id}",
            extra={
                "cache_key": f"processes:{cache_key}",
                "cache_hit": False,
                "organization_id": organization_id
            }
        )
        
        try:
            # Fetch from backend
            backend_start = datetime.utcnow()
            processes_data = await self.backend_client.get_organization_processes(
                organization_id=organization_id,
                auth_token=auth_token,
                active_only=True,
                limit=limit
            )
            backend_elapsed = (datetime.utcnow() - backend_start).total_seconds()
            
            if not processes_data:
                logger.info(
                    f"[BACKEND] No processes found for organization {organization_id}",
                    extra={
                        "organization_id": organization_id,
                        "backend_call": "get_organization_processes",
                        "success": True,
                        "processes_count": 0,
                        "elapsed_seconds": backend_elapsed
                    }
                )
                return []
            
            logger.debug(
                f"[BACKEND] Successfully fetched {len(processes_data)} processes",
                extra={
                    "organization_id": organization_id,
                    "backend_call": "get_organization_processes",
                    "success": True,
                    "processes_count": len(processes_data),
                    "elapsed_seconds": backend_elapsed
                }
            )
            
            # Convert to ProcessContextData models
            processes = []
            for process in processes_data:
                try:
                    process_context = ProcessContextData(
                        id=UUID(process["id"]),
                        name=process.get("name", "Unknown Process"),
                        type=process.get("type", "unknown"),
                        type_label=process.get("typeLabel", "Unknown"),
                        is_active=process.get("isActive", True),
                        created_at=datetime.fromisoformat(
                            process.get("createdAt", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                        ),
                        updated_at=datetime.fromisoformat(
                            process.get("updatedAt", datetime.utcnow().isoformat()).replace("Z", "+00:00")
                        )
                    )
                    processes.append(process_context)
                except (KeyError, ValueError) as e:
                    logger.warning(
                        f"Skipping invalid process data: {process.get('id', 'unknown')} - {str(e)}"
                    )
                    continue
            
            # Sort by updated_at descending (most recent first)
            processes.sort(key=lambda p: p.updated_at, reverse=True)
            
            # Cache the result
            self.cache.set(
                "processes",
                cache_key,
                [p.model_dump() for p in processes]
            )
            
            logger.debug(
                f"Fetched {len(processes)} processes for organization {organization_id}"
            )
            
            return processes
            
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to fetch processes for organization {organization_id}: "
                f"{type(e).__name__}: {str(e)}",
                extra={
                    "organization_id": organization_id,
                    "backend_call": "get_organization_processes",
                    "success": False,
                    "error_type": type(e).__name__,
                    "fallback": "empty_processes_list"
                }
            )
            # Return empty list to allow interview to proceed
            return []
    
    async def get_interview_history_summary(
        self,
        employee_id: UUID,
        db: AsyncSession
    ) -> InterviewHistorySummary:
        """
        Get summary of employee's previous interviews.
        
        Aggregates interview counts, dates, and topics from local database.
        
        Args:
            employee_id: UUID of the employee
            db: Database session
            
        Returns:
            InterviewHistorySummary with aggregated data
            
        Note:
            Returns empty summary on error to avoid blocking interviews.
        """
        logger.debug(f"Fetching interview history for employee {employee_id}")
        
        try:
            # Query interview counts and last interview date
            count_stmt = select(
                func.count(Interview.id_interview).label("total"),
                func.count(
                    Interview.id_interview
                ).filter(
                    Interview.status == InterviewStatusEnum.completed
                ).label("completed"),
                func.max(Interview.started_at).label("last_date")
            ).where(
                Interview.employee_id == employee_id
            )
            
            result = await db.execute(count_stmt)
            row = result.one_or_none()
            
            if not row:
                logger.debug(f"No interview history found for employee {employee_id}")
                return InterviewHistorySummary()
            
            total_interviews = row.total or 0
            completed_interviews = row.completed or 0
            last_interview_date = row.last_date
            
            # For now, topics_covered is empty - could be enhanced later
            # by analyzing interview messages or extracting from completed interviews
            topics_covered = []
            
            summary = InterviewHistorySummary(
                total_interviews=total_interviews,
                completed_interviews=completed_interviews,
                last_interview_date=last_interview_date,
                topics_covered=topics_covered
            )
            
            logger.debug(
                f"Interview history for employee {employee_id}: "
                f"{total_interviews} total, {completed_interviews} completed"
            )
            
            return summary
            
        except Exception as e:
            logger.error(
                f"[ERROR] Failed to fetch interview history for employee {employee_id}: "
                f"{type(e).__name__}: {str(e)}",
                extra={
                    "employee_id": str(employee_id),
                    "database_call": "get_interview_history_summary",
                    "success": False,
                    "error_type": type(e).__name__,
                    "fallback": "empty_history_summary"
                }
            )
            # Return empty summary to allow interview to proceed
            return InterviewHistorySummary()
