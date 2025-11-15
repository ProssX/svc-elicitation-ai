"""add_dimensional_attrs_to_metrics

Revision ID: d4e5f6g7h8i9
Revises: c3d4e5f6g7h8
Create Date: 2025-11-15 20:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'd4e5f6g7h8i9'
down_revision: Union[str, None] = 'c3d4e5f6g7h8'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """
    Add dimensional attributes to metric_event table for better analytics
    
    Adds:
    - employee_id: For per-employee analysis
    - organization_id: For multi-tenant analytics  
    - language: For language segmentation
    
    These fields are denormalized from interview table for query performance.
    Allows direct filtering/grouping without JOINs.
    """
    
    # Add new columns
    op.add_column('metric_event', sa.Column('employee_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Employee who triggered the event (denormalized from interview)'))
    op.add_column('metric_event', sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True, comment='Organization context (for multi-tenant analytics)'))
    op.add_column('metric_event', sa.Column('language', sa.String(length=5), nullable=True, comment='Language of the interview (es/en/pt)'))
    
    # Create indexes for analytics queries
    op.create_index('idx_metric_event_employee', 'metric_event', ['employee_id'])
    op.create_index('idx_metric_event_organization', 'metric_event', ['organization_id'])
    op.create_index('idx_metric_event_language', 'metric_event', ['language'])
    
    # Create composite indexes for common query patterns
    op.create_index('idx_metric_event_org_type_occurred', 'metric_event', ['organization_id', 'event_type', 'occurred_at'])
    op.create_index('idx_metric_event_emp_type_occurred', 'metric_event', ['employee_id', 'event_type', 'occurred_at'])


def downgrade() -> None:
    """
    Remove dimensional attributes from metric_event table
    """
    
    # Drop composite indexes
    op.drop_index('idx_metric_event_emp_type_occurred', table_name='metric_event')
    op.drop_index('idx_metric_event_org_type_occurred', table_name='metric_event')
    
    # Drop simple indexes
    op.drop_index('idx_metric_event_language', table_name='metric_event')
    op.drop_index('idx_metric_event_organization', table_name='metric_event')
    op.drop_index('idx_metric_event_employee', table_name='metric_event')
    
    # Drop columns
    op.drop_column('metric_event', 'language')
    op.drop_column('metric_event', 'organization_id')
    op.drop_column('metric_event', 'employee_id')
