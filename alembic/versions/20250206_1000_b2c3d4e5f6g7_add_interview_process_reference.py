"""add_interview_process_reference

Revision ID: b2c3d4e5f6g7
Revises: a1b2c3d4e5f6
Create Date: 2025-02-06 10:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'b2c3d4e5f6g7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Create interview_process_reference table to track process references in interviews.
    
    This table links interviews to processes identified during the conversation,
    enabling tracking of which interviews contributed to process discovery.
    
    Table:
    - interview_process_reference: Links interviews to processes with metadata
    
    Relationships:
    - interview_process_reference.interview_id -> interview.id_interview (CASCADE DELETE)
    - interview_process_reference.process_id: Logical reference to svc-organizations-php
    """
    
    # Create interview_process_reference table
    op.create_table(
        'interview_process_reference',
        sa.Column('id_reference', postgresql.UUID(as_uuid=True), nullable=False, comment='Unique process reference identifier (UUID v7 or v4)'),
        sa.Column('interview_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Reference to parent interview'),
        sa.Column('process_id', postgresql.UUID(as_uuid=True), nullable=False, comment='Logical reference to process in svc-organizations-php'),
        sa.Column('is_new_process', sa.Boolean(), nullable=False, server_default='false', comment='Whether this was a newly identified process'),
        sa.Column('confidence_score', sa.Numeric(precision=3, scale=2), nullable=True, comment='Process match confidence score (0.00 to 1.00)'),
        sa.Column('mentioned_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='When the process was mentioned in the interview'),
        sa.Column('created_at', sa.DateTime(), nullable=False, server_default=sa.text('NOW()'), comment='Record creation timestamp'),
        sa.ForeignKeyConstraint(['interview_id'], ['interview.id_interview'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id_reference'),
        sa.UniqueConstraint('interview_id', 'process_id', name='unique_interview_process'),
        comment='Process references linked to interviews'
    )
    
    # Create indexes for query optimization
    op.create_index('idx_interview_process_interview', 'interview_process_reference', ['interview_id'])
    op.create_index('idx_interview_process_process', 'interview_process_reference', ['process_id'])


def downgrade() -> None:
    """
    Drop interview_process_reference table.
    
    This will remove all process reference data.
    Use with caution in production environments.
    """
    
    # Drop indexes
    op.drop_index('idx_interview_process_process', table_name='interview_process_reference')
    op.drop_index('idx_interview_process_interview', table_name='interview_process_reference')
    
    # Drop table
    op.drop_table('interview_process_reference')
