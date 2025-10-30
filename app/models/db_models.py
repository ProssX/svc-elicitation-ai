"""
Database Models for Interview Persistence
SQLAlchemy ORM models for storing interviews and messages in PostgreSQL
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, Enum as SQLEnum
from sqlalchemy.orm import relationship
from sqlalchemy.dialects.postgresql import UUID
from datetime import datetime
import uuid
import enum
import sys

from app.database import Base

# UUID v7 support for Python < 3.12
if sys.version_info >= (3, 12):
    uuid_generate = uuid.uuid7
else:
    # Fallback to uuid4 for Python < 3.12
    # Note: uuid4 doesn't have time-ordering like uuid7, but is compatible
    uuid_generate = uuid.uuid4


# Enums for type safety
# IMPORTANT: Enum names must match database values exactly
# PostgreSQL enum values are: 'es', 'en', 'pt' (lowercase)
class LanguageEnum(str, enum.Enum):
    """Supported interview languages"""
    es = "es"
    en = "en"
    pt = "pt"


class InterviewStatusEnum(str, enum.Enum):
    """Interview status states"""
    in_progress = "in_progress"
    completed = "completed"
    cancelled = "cancelled"


class MessageRoleEnum(str, enum.Enum):
    """Message role types"""
    assistant = "assistant"
    user = "user"
    system = "system"


class Interview(Base):
    """
    Interview entity - represents a complete interview session
    
    Stores metadata about the interview including:
    - Employee association (logical reference to svc-organizations-php)
    - Language and technical level
    - Status and timestamps
    - Relationship to messages
    """
    __tablename__ = "interview"
    
    # Primary Key - UUID v7 for time-ordered IDs (or uuid4 for Python < 3.12)
    id_interview = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_generate,
        comment="Unique interview identifier (UUID v7 or v4)"
    )
    
    # Foreign Key to Employee (logical reference, no physical FK)
    # Employee table is in svc-organizations-php database
    employee_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        index=True,
        comment="Reference to employee.id_employee in svc-organizations-php"
    )
    
    # Interview Metadata
    language = Column(
        SQLEnum(LanguageEnum, name="language_enum", create_type=False),
        nullable=False,
        comment="Interview language (es/en/pt)"
    )
    
    technical_level = Column(
        String(20),
        nullable=False,
        default="unknown",
        comment="User's technical level"
    )
    
    status = Column(
        SQLEnum(InterviewStatusEnum, name="interview_status_enum", create_type=False),
        nullable=False,
        default=InterviewStatusEnum.in_progress,  # Use lowercase enum name
        index=True,
        comment="Current interview status"
    )
    
    # Timestamps
    started_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the interview started"
    )
    
    completed_at = Column(
        DateTime,
        nullable=True,
        comment="When the interview was completed"
    )
    
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="Record last update timestamp"
    )
    
    # Relationships
    messages = relationship(
        "InterviewMessage",
        back_populates="interview",
        cascade="all, delete-orphan",
        order_by="InterviewMessage.sequence_number",
        lazy="selectin"
    )
    
    def __repr__(self):
        return f"<Interview(id={self.id_interview}, employee_id={self.employee_id}, status={self.status})>"


class InterviewMessage(Base):
    """
    Interview Message entity - represents a single message in the conversation
    
    Stores individual messages (questions and answers) with:
    - Role (assistant/user/system)
    - Content
    - Sequence number for ordering
    - Timestamps
    """
    __tablename__ = "interview_message"
    
    # Primary Key - UUID v7 for time-ordered IDs (or uuid4 for Python < 3.12)
    id_message = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_generate,
        comment="Unique message identifier (UUID v7 or v4)"
    )
    
    # Foreign Key to Interview with CASCADE delete
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey('interview.id_interview', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to parent interview"
    )
    
    # Message Data
    role = Column(
        SQLEnum(MessageRoleEnum, name="message_role_enum", create_type=False),
        nullable=False,
        comment="Message role (assistant/user/system)"
    )
    
    content = Column(
        String,
        nullable=False,
        comment="Message content/text"
    )
    
    sequence_number = Column(
        Integer,
        nullable=False,
        comment="Message order in conversation (1-based)"
    )
    
    # Timestamps
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Message creation timestamp"
    )
    
    # Relationships
    interview = relationship(
        "Interview",
        back_populates="messages"
    )
    
    # Indexes for query optimization
    __table_args__ = (
        Index('idx_interview_sequence', 'interview_id', 'sequence_number'),
        {'comment': 'Interview messages with conversation history'}
    )
    
    def __repr__(self):
        return f"<InterviewMessage(id={self.id_message}, interview_id={self.interview_id}, role={self.role}, seq={self.sequence_number})>"
