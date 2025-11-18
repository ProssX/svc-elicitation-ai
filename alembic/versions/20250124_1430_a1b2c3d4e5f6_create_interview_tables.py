"""create_interview_tables

Revision ID: a1b2c3d4e5f6
Revises: 
Create Date: 2025-01-24 14:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create interview and interview_message tables with proper indexes and constraints.
    
    Tables:
    - interview: Stores interview metadata (employee_id, language, status, timestamps)
    - interview_message: Stores conversation messages (role, content, sequence_number)
    
    Relationships:
    - interview_message.interview_id -> interview.id_interview (CASCADE DELETE)
    """
    
    # Create ENUM types
    op.execute("CREATE TYPE language_enum AS ENUM ('es', 'en', 'pt')")
    op.execute("CREATE TYPE interview_status_enum AS ENUM ('in_progress', 'completed', 'cancelled')")
    op.execute("CREATE TYPE message_role_enum AS ENUM ('assistant', 'user', 'system')")
    
    # Create interview table
    op.create_table(
        'interview',
        sa.Column('id_interview', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique interview identifier (UUID v7 or v4)'),
        sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to employee.id_employee in svc-organizations-php'),
        sa.Column('language', postgresql.ENUM('es', 'en', 'pt', name='language_enum', create_type=False), nullable=False, comment='Interview language (es/en/pt)'),
        sa.Column('technical_level', sa.String(length=20), nullable=False, server_default='unknown', comment="User's technical level"),
        sa.Column('status', postgresql.ENUM('in_progress', 'completed', 'cancelled', name='interview_status_enum', create_type=False), nullable=False, server_default='in_progress', comment='Current interview status'),
        sa.Column('started_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='When the interview started'),
        sa.Column('completed_at', sa.DateTime(), nullable=True, comment='When the interview was completed'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        sa.Column('updated_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record last update timestamp'),
        sa.PrimaryKeyConstraint('id_interview'),
        comment='Interview sessions with metadata'
    )
    
    # Create indexes for interview table
    op.create_index('idx_interview_employee_id', 'interview', ['employee_id'])
    op.create_index('idx_interview_status', 'interview', ['status'])
    op.create_index('idx_interview_started_at', 'interview', ['started_at'])
    
    # Create interview_message table
    op.create_table(
        'interview_message',
        sa.Column('id_message', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique message identifier (UUID v7 or v4)'),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to parent interview'),
        sa.Column('role', postgresql.ENUM('assistant', 'user', 'system', name='message_role_enum', create_type=False), nullable=False, comment='Message role (assistant/user/system)'),
        sa.Column('content', sa.String(), nullable=False, comment='Message content/text'),
        sa.Column('sequence_number', sa.Integer(), nullable=False, comment='Message order in conversation (1-based)'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Message creation timestamp'),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id_interview'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_message'),
        comment='Interview messages with conversation history'
    )
    
    # Create indexes for interview_message table
    op.create_index('idx_interview_sequence', 'interview_message', ['interview_id', 'sequence_number'])


def downgrade() -> None:
    """
    Drop interview and interview_message tables and ENUM types.
    
    This will remove all interview data and related messages.
    Use with caution in production environments.
    """
    
    # Drop indexes
    op.drop_index('idx_interview_sequence', table_name='interview_message')
    op.drop_index('idx_interview_started_at', table_name='interview')
    op.drop_index('idx_interview_status', table_name='interview')
    op.drop_index('idx_interview_employee_id', table_name='interview')
    
    # Drop tables (CASCADE will handle foreign keys)
    op.drop_table('interview_message')
    op.drop_table('interview')
    
    # Drop ENUM types
    op.execute("DROP TYPE IF EXISTS message_role_enum")
    op.execute("DROP TYPE IF EXISTS interview_status_enum")
    op.execute("DROP TYPE IF EXISTS language_enum")
