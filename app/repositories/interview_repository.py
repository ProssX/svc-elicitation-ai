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
        
        # Count total items
        count_stmt = select(func.count()).select_from(Interview).where(and_(*conditions))
        count_result = await self.db.execute(count_stmt)
        total_count = count_result.scalar()
        
        # Get paginated results
        offset = (page - 1) * page_size
        stmt = (
            select(Interview)
            .where(and_(*conditions))
            .order_by(Interview.started_at.desc())
            .limit(page_size)
            .offset(offset)
        )
        result = await self.db.execute(stmt)
        interviews = result.scalars().all()
        
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
            interview.status = InterviewStatusEnum.COMPLETED
            interview.completed_at = datetime.utcnow()
            interview.updated_at = datetime.utcnow()
            await self.db.flush()
            await self.db.refresh(interview)
        
        return interview
