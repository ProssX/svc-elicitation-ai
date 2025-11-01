"""
Interview Repository
Handles database operations for Interview entities
"""
from typing import Optional, List, Tuple
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, func, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models.db_models import Interview, InterviewStatusEnum


class InterviewRepository:
    """Repository for Interview CRUD operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    async def create(self, interview: Interview) -> Interview:
        """
        Create a new interview in the database
        
        Args:
            interview: Interview instance to persist
            
        Returns:
            Created interview with generated ID
        """
        self.db.add(interview)
        await self.db.flush()
        await self.db.refresh(interview)
        return interview
    
    async def get_by_id(
        self, 
        interview_id: UUID, 
        employee_id: UUID
    ) -> Optional[Interview]:
        """
        Get interview by ID, validating it belongs to the employee
        
        Args:
            interview_id: Interview UUID
            employee_id: Employee UUID for authorization check
            
        Returns:
            Interview if found and belongs to employee, None otherwise
        """
        stmt = (
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(
                and_(
                    Interview.id_interview == interview_id,
                    Interview.employee_id == employee_id
                )
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_id_no_filter(
        self, 
        interview_id: UUID
    ) -> Optional[Interview]:
        """
        Get interview by ID without employee validation (for admin access)
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            Interview if found, None otherwise
        """
        stmt = (
            select(Interview)
            .options(selectinload(Interview.messages))
            .where(Interview.id_interview == interview_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def get_by_employee(
        self,
        employee_id: UUID,
        status: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Interview], int]:
        """
        List interviews for an employee with filters and pagination
        
        Args:
            employee_id: Employee UUID
            status: Filter by status (optional)
            language: Filter by language (optional)
            start_date: Filter by started_at >= start_date (optional)
            end_date: Filter by started_at <= end_date (optional)
            page: Page number (1-based)
            page_size: Items per page
            
        Returns:
            Tuple of (list of interviews, total count)
        """
        # Build base query
        conditions = [Interview.employee_id == employee_id]
        
        # Apply filters
        if status:
            conditions.append(Interview.status == status)
        
        if language:
            conditions.append(Interview.language == language)
        
        if start_date:
            conditions.append(Interview.started_at >= start_date)
        
        if end_date:
            conditions.append(Interview.started_at <= end_date)
        
        # Use window function to get count and data in single query
        offset = (page - 1) * page_size
        stmt = (
            select(
                Interview,
                func.count().over().label('total_count')
            )
            .where(and_(*conditions))
            .order_by(Interview.started_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        rows = result.all()
        
        if rows:
            interviews = [row[0] for row in rows]
            total_count = rows[0][1]
        else:
            interviews = []
            total_count = 0
        
        return list(interviews), total_count
    
    async def get_by_organization(
        self,
        organization_id: str,
        status: Optional[str] = None,
        language: Optional[str] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None,
        page: int = 1,
        page_size: int = 20
    ) -> Tuple[List[Interview], int]:
        """
        List all interviews for an organization with filters and pagination
        
        This method is used when a user has interviews:read_all permission
        and can see all interviews in their organization.
        
        Args:
            organization_id: Organization ID (from JWT)
            status: Filter by status (optional)
            language: Filter by language (optional)
            start_date: Filter by started_at >= start_date (optional)
            end_date: Filter by started_at <= end_date (optional)
            page: Page number (1-based)
            page_size: Items per page
            
        Returns:
            Tuple of (list of interviews, total count)
        """
        # Build base query - no employee_id filter for organization-wide access
        conditions = []
        
        # Apply filters
        if status:
            conditions.append(Interview.status == status)
        
        if language:
            conditions.append(Interview.language == language)
        
        if start_date:
            conditions.append(Interview.started_at >= start_date)
        
        if end_date:
            conditions.append(Interview.started_at <= end_date)
        
        # Execute count and select queries sequentially to avoid concurrency issues
        # Use a single query with window function to avoid multiple round trips
        offset = (page - 1) * page_size
        
        if conditions:
            # Use window function to get count and data in single query
            stmt = (
                select(
                    Interview,
                    func.count().over().label('total_count')
                )
                .where(and_(*conditions))
                .order_by(Interview.started_at.desc())
                .limit(page_size)
                .offset(offset)
            )
        else:
            stmt = (
                select(
                    Interview,
                    func.count().over().label('total_count')
                )
                .order_by(Interview.started_at.desc())
                .limit(page_size)
                .offset(offset)
            )
        
        result = await self.db.execute(stmt)
        rows = result.all()
        
        if rows:
            interviews = [row[0] for row in rows]
            total_count = rows[0][1]
        else:
            interviews = []
            total_count = 0
        
        return list(interviews), total_count
    
    async def update_status(
        self, 
        interview_id: UUID, 
        status: str
    ) -> Optional[Interview]:
        """
        Update interview status
        
        Args:
            interview_id: Interview UUID
            status: New status value
            
        Returns:
            Updated interview or None if not found
        """
        stmt = select(Interview).where(Interview.id_interview == interview_id)
        result = await self.db.execute(stmt)
        interview = result.scalar_one_or_none()
        
        if interview:
            interview.status = InterviewStatusEnum(status)
            interview.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(interview)
        
        return interview
    
    async def mark_completed(self, interview_id: UUID) -> Optional[Interview]:
        """
        Mark interview as completed
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            Updated interview or None if not found
        """
        stmt = select(Interview).where(Interview.id_interview == interview_id)
        result = await self.db.execute(stmt)
        interview = result.scalar_one_or_none()
        
        if interview:
            interview.status = InterviewStatusEnum.completed
            interview.completed_at = datetime.utcnow()
            interview.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(interview)
        
        return interview
