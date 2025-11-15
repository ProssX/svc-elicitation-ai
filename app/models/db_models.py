"""
Database Models for Interview Persistence
SQLAlchemy ORM models for storing interviews and messages in PostgreSQL
"""
from sqlalchemy import Column, String, DateTime, Integer, ForeignKey, Index, Enum as SQLEnum, Boolean, Numeric, UniqueConstraint
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
    
    process_references = relationship(
        "InterviewProcessReference",
        back_populates="interview",
        cascade="all, delete-orphan",
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


class InterviewProcessReference(Base):
    """
    Interview Process Reference entity - links interviews to processes
    
    Tracks which processes were discussed or identified during interviews:
    - Process association (logical reference to svc-organizations-php)
    - Whether the process was newly identified or existing
    - Confidence score for process matching
    - Timestamps for tracking
    """
    __tablename__ = "interview_process_reference"
    
    # Primary Key - UUID v7 for time-ordered IDs (or uuid4 for Python < 3.12)
    id_reference = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_generate,
        comment="Unique process reference identifier (UUID v7 or v4)"
    )
    
    # Foreign Key to Interview with CASCADE delete
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey('interview.id_interview', ondelete='CASCADE'),
        nullable=False,
        comment="Reference to parent interview"
    )
    
    # Foreign Key to Process (logical reference, no physical FK)
    # Process table is in svc-organizations-php database
    process_id = Column(
        UUID(as_uuid=True),
        nullable=False,
        comment="Logical reference to process in svc-organizations-php"
    )
    
    # Process Reference Metadata
    is_new_process = Column(
        Boolean,
        nullable=False,
        default=False,
        comment="Whether this was a newly identified process"
    )
    
    confidence_score = Column(
        Numeric(3, 2),
        nullable=True,
        comment="Process match confidence score (0.00 to 1.00)"
    )
    
    # Timestamps
    mentioned_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="When the process was mentioned in the interview"
    )
    
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    
    # Relationships
    interview = relationship(
        "Interview",
        back_populates="process_references"
    )
    
    # Constraints and Indexes
    __table_args__ = (
        UniqueConstraint('interview_id', 'process_id', name='unique_interview_process'),
        Index('idx_interview_process_interview', 'interview_id'),
        Index('idx_interview_process_process', 'process_id'),
        {'comment': 'Process references linked to interviews'}
    )
    
    def __repr__(self):
        return f"<InterviewProcessReference(id={self.id_reference}, interview_id={self.interview_id}, process_id={self.process_id}, is_new={self.is_new_process})>"


class MetricTypeEnum(str, enum.Enum):
    """Metric event types"""
    interview_started = "interview_started"
    interview_completed = "interview_completed"
    detection_invoked = "detection_invoked"


class MetricOutcomeEnum(str, enum.Enum):
    """Metric event outcomes"""
    success = "success"
    timeout = "timeout"
    error = "error"
    not_applicable = "not_applicable"  # For events that don't have success/failure (e.g. interview_started)


class MetricEvent(Base):
    """
    Metric Event - stores individual metric events for historical analysis
    
    Captures:
    - Interview lifecycle events (started, completed)
    - Process detection invocations (success, timeout, error)
    - Performance metrics (latency, confidence scores)
    - Completion reasons and question counts
    - Dimensional context (employee, organization, language) for analytics
    """
    __tablename__ = "metric_event"
    
    # Primary Key - UUID v7 for time-ordered IDs (or uuid4 for Python < 3.12)
    id_event = Column(
        UUID(as_uuid=True),
        primary_key=True,
        default=uuid_generate,
        comment="Unique event identifier (UUID v7 or v4)"
    )
    
    # Event Classification
    event_type = Column(
        SQLEnum(MetricTypeEnum, name="metric_type_enum", create_type=False),
        nullable=False,
        index=True,
        comment="Type of metric event (interview_started, interview_completed, detection_invoked)"
    )
    
    outcome = Column(
        SQLEnum(MetricOutcomeEnum, name="metric_outcome_enum", create_type=False),
        nullable=False,
        default=MetricOutcomeEnum.not_applicable,
        index=True,
        comment="Event outcome (success, timeout, error, not_applicable)"
    )
    
    # Optional Foreign Key to Interview (for interview-related events)
    interview_id = Column(
        UUID(as_uuid=True),
        ForeignKey("interview.id_interview", ondelete="CASCADE"),
        nullable=True,
        index=True,
        comment="Reference to interview if event is interview-related"
    )
    
    # Dimensional Attributes for Analytics (denormalized for query performance)
    employee_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Employee who triggered the event (denormalized from interview)"
    )
    
    organization_id = Column(
        UUID(as_uuid=True),
        nullable=True,
        index=True,
        comment="Organization context (for multi-tenant analytics)"
    )
    
    language = Column(
        String(5),
        nullable=True,
        index=True,
        comment="Language of the interview (es/en/pt)"
    )
    
    # Performance Metrics
    latency_ms = Column(
        Numeric(10, 2),
        nullable=True,
        comment="Event latency in milliseconds (for detection_invoked events)"
    )
    
    confidence_score = Column(
        Numeric(4, 3),
        nullable=True,
        comment="Confidence score 0.000-1.000 (for successful detection_invoked events)"
    )
    
    # Interview Completion Metrics
    question_count = Column(
        Integer,
        nullable=True,
        comment="Number of questions in interview (for interview_completed events)"
    )
    
    early_finish = Column(
        Boolean,
        nullable=True,
        comment="Whether interview finished before max_questions (for interview_completed events)"
    )
    
    completion_reason = Column(
        String(50),
        nullable=True,
        comment="Why interview ended: user_requested, agent_signaled, safety_limit, max_questions"
    )
    
    # Timestamps
    occurred_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        index=True,
        comment="When the event occurred"
    )
    
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="Record creation timestamp"
    )
    
    # Relationship to Interview (optional)
    interview = relationship(
        "Interview",
        foreign_keys=[interview_id],
        lazy="select"
    )
    
    # Indexes for query performance
    __table_args__ = (
        Index('idx_metric_event_type_occurred', 'event_type', 'occurred_at'),
        Index('idx_metric_event_outcome_occurred', 'outcome', 'occurred_at'),
        Index('idx_metric_event_interview', 'interview_id'),
        {'comment': 'Metric events for performance monitoring and historical analysis'}
    )
    
    def __repr__(self):
        return f"<MetricEvent(id={self.id_event}, type={self.event_type}, outcome={self.outcome}, occurred_at={self.occurred_at})>"
