"""add organization_id to interview

Revision ID: e5f6g7h8i9j0
Revises: d4e5f6g7h8i9
Create Date: 2025-11-17 15:00:00.000000

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision = 'e5f6g7h8i9j0'
down_revision = 'd4e5f6g7h8i9'
branch_labels = None
depends_on = None


def upgrade():
    """Add organization_id column to interview table"""
    # Add organization_id column (nullable initially for existing data)
    op.add_column('interview', 
        sa.Column('organization_id', postgresql.UUID(as_uuid=True), nullable=True,
                  comment='Reference to organization in svc-organizations-php')
    )
    
    # Create index for organization_id queries
    op.create_index('idx_interview_organization', 'interview', ['organization_id'])
    
    # Note: We don't make it NOT NULL because existing interviews don't have this data
    # In production, you would need to backfill this data before making it NOT NULL


def downgrade():
    """Remove organization_id column from interview table"""
    op.drop_index('idx_interview_organization', table_name='interview')
    op.drop_column('interview', 'organization_id')
