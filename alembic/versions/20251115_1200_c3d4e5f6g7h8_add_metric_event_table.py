"""add_metric_event_table

Revision ID: c3d4e5f6g7h8
Revises: b2c3d4e5f6g7
Create Date: 2025-11-15 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'c3d4e5f6g7h8'
down_revision: Union[str, None] = 'b2c3d4e5f6g7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create metric_event table for storing performance and behavior metrics.
    
    Tables:
    - metric_event: Stores metric events (interview lifecycle, detection performance)
    
    Supports:
    - Interview started/completed events
    - Process detection invocation metrics (latency, confidence, timeouts, errors)
    - Historical analysis and time-series queries
    
    Relationships:
    - metric_event.interview_id -> interview.id_interview (optional, CASCADE DELETE)
    """
    
    # Create ENUM types for metric events
    op.execute("CREATE TYPE metric_type_enum AS ENUM ('interview_started', 'interview_completed', 'detection_invoked')")
    op.execute("CREATE TYPE metric_outcome_enum AS ENUM ('success', 'timeout', 'error', 'not_applicable')")
    
    # Create metric_event table
    op.create_table(
        'metric_event',
        sa.Column('id_event', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique event identifier (UUID v7 or v4)'),
        sa.Column('event_type', postgresql.ENUM('interview_started', 'interview_completed', 'detection_invoked', name='metric_type_enum', create_type=False), nullable=False, comment='Type of metric event (interview_started, interview_completed, detection_invoked)'),
        sa.Column('outcome', postgresql.ENUM('success', 'timeout', 'error', 'not_applicable', name='metric_outcome_enum', create_type=False), nullable=False, server_default='not_applicable', comment='Event outcome (success, timeout, error, not_applicable)'),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Reference to interview if event is interview-related'),
        sa.Column('latency_ms', sa.Numeric(precision=10, scale=2), nullable=True, comment='Event latency in milliseconds (for detection_invoked events)'),
        sa.Column('confidence_score', sa.Numeric(precision=4, scale=3), nullable=True, comment='Confidence score 0.000-1.000 (for successful detection_invoked events)'),
        sa.Column('question_count', sa.Integer(), nullable=True, comment='Number of questions in interview (for interview_completed events)'),
        sa.Column('early_finish', sa.Boolean(), nullable=True, comment='Whether interview finished before max_questions (for interview_completed events)'),
        sa.Column('completion_reason', sa.String(length=50), nullable=True, comment='Why interview ended: user_requested, agent_signaled, safety_limit, max_questions'),
        sa.Column('occurred_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='When the event occurred'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id_interview'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_event'),
        comment='Metric events for performance monitoring and historical analysis'
    )
    
    # Create indexes for efficient queries
    op.create_index('idx_metric_event_type_occurred', 'metric_event', ['event_type', 'occurred_at'])
    op.create_index('idx_metric_event_outcome_occurred', 'metric_event', ['outcome', 'occurred_at'])
    op.create_index('idx_metric_event_interview', 'metric_event', ['interview_id'])
    op.create_index('idx_metric_event_occurred_at', 'metric_event', ['occurred_at'])


def downgrade() -> None:
    """
    Drop metric_event table and related ENUM types.
    
    This will remove all metric event history.
    Use with caution in production environments.
    """
    
    # Drop indexes
    op.drop_index('idx_metric_event_occurred_at', table_name='metric_event')
    op.drop_index('idx_metric_event_interview', table_name='metric_event')
    op.drop_index('idx_metric_event_outcome_occurred', table_name='metric_event')
    op.drop_index('idx_metric_event_type_occurred', table_name='metric_event')
    
    # Drop table
    op.drop_table('metric_event')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS metric_outcome_enum")
    op.execute("DROP TYPE IF EXISTS metric_type_enum")
