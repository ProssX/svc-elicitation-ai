"""
Message Repository
Handles database operations for InterviewMessage entities
"""
from typing import List, Optional
from uuid import UUID
from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.db_models import InterviewMessage


class MessageRepository:
    """Repository for InterviewMessage CRUD operations"""
    
    def __init__(self, db: AsyncSession):
        """
        Initialize repository with database session
        
        Args:
            db: Async SQLAlchemy session
        """
        self.db = db
    
    async def create(self, message: InterviewMessage) -> InterviewMessage:
        """
        Create a new message in the database
        
        Args:
            message: InterviewMessage instance to persist
            
        Returns:
            Created message with generated ID
        """
        self.db.add(message)
        await self.db.flush()
        await self.db.refresh(message)
        return message
    
    async def get_by_interview(self, interview_id: UUID) -> List[InterviewMessage]:
        """
        Get all messages for an interview, ordered by sequence number
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            List of messages ordered by sequence_number
        """
        stmt = (
            select(InterviewMessage)
            .where(InterviewMessage.interview_id == interview_id)
            .order_by(InterviewMessage.sequence_number)
        )
        result = await self.db.execute(stmt)
        return list(result.scalars().all())
    
    async def get_last_sequence(self, interview_id: UUID) -> int:
        """
        Get the last sequence number for an interview
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            Last sequence number, or 0 if no messages exist
        """
        stmt = (
            select(func.max(InterviewMessage.sequence_number))
            .where(InterviewMessage.interview_id == interview_id)
        )
        result = await self.db.execute(stmt)
        max_sequence = result.scalar()
        return max_sequence if max_sequence is not None else 0
    
    async def count_by_interview(self, interview_id: UUID) -> int:
        """
        Count messages for an interview
        
        Args:
            interview_id: Interview UUID
            
        Returns:
            Total number of messages
        """
        stmt = (
            select(func.count())
            .select_from(InterviewMessage)
            .where(InterviewMessage.interview_id == interview_id)
        )
        result = await self.db.execute(stmt)
        return result.scalar()
