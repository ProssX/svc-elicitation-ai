"""
Process Reference Repository
Handles database operations for InterviewProcessReference entities
"""
from typing import Optional, List
from uuid import UUID
from datetime import datetime
from sqlalchemy import select, and_
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.exc import IntegrityError

from app.models.db_models import InterviewProcessReference


class ProcessReferenceRepository:
    """Repository for InterviewProcessReference CRUD operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    async def create(
        self,
        interview_id: UUID,
        process_id: UUID,
        is_new_process: bool = False,
        confidence_score: Optional[float] = None,
        mentioned_at: Optional[datetime] = None
    ) -> Optional[InterviewProcessReference]:
        """
        Create a new process reference for an interview
        
        Args:
            interview_id: Interview UUID
            process_id: Process UUID (logical reference to svc-organizations-php)
            is_new_process: Whether this is a newly identified process
            confidence_score: Match confidence score (0.0 to 1.0)
            mentioned_at: When the process was mentioned (defaults to now)
            
        Returns:
            Created process reference, or None if unique constraint violated
        """
        try:
            process_ref = InterviewProcessReference(
                interview_id=interview_id,
                process_id=process_id,
                is_new_process=is_new_process,
                confidence_score=confidence_score,
                mentioned_at=mentioned_at or datetime.utcnow()
            )
            
            self.db.add(process_ref)
            await self.db.flush()
            await self.db.refresh(process_ref)
            return process_ref
            
        except IntegrityError:
            # Unique constraint violation - interview already references this process
            await self.db.rollback()
            return None
    
    async def get_by_interview(
        self,
        interview_id: UUID
    ) -> List[InterviewProcessReference]:
        """
        Get all process references for a specific interview
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            List of process references ordered by mentioned_at
        """
        stmt = (
            select(InterviewProcessReference)
            .where(InterviewProcessReference.interview_id == interview_id)
            .order_by(InterviewProcessReference.mentioned_at.asc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_process(
        self,
        process_id: UUID
    ) -> List[InterviewProcessReference]:
        """
        Get all interview references for a specific process
        
        Args:
            process_id: Process UUID
            
        Returns:
            List of process references ordered by mentioned_at descending
        """
        stmt = (
            select(InterviewProcessReference)
            .where(InterviewProcessReference.process_id == process_id)
            .order_by(InterviewProcessReference.mentioned_at.desc())
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_by_id(
        self,
        reference_id: UUID
    ) -> Optional[InterviewProcessReference]:
        """
        Get a specific process reference by ID
        
        Args:
            reference_id: Process reference UUID
            
        Returns:
            Process reference if found, None otherwise
        """
        stmt = select(InterviewProcessReference).where(
            InterviewProcessReference.id_reference == reference_id
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none()
    
    async def exists(
        self,
        interview_id: UUID,
        process_id: UUID
    ) -> bool:
        """
        Check if a process reference already exists for an interview
        
        Args:
            interview_id: Interview UUID
            process_id: Process UUID
            
        Returns:
            True if reference exists, False otherwise
        """
        stmt = select(InterviewProcessReference).where(
            and_(
                InterviewProcessReference.interview_id == interview_id,
                InterviewProcessReference.process_id == process_id
            )
        )
        result = await self.db.execute(stmt)
        return result.scalar_one_or_none() is not None
