"""
Add file_hash column to documents table

Revision ID: 20250703_add_file_hash
Revises: 
Create Date: 2025-07-03
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '20250703_add_file_hash'
down_revision = None
branch_labels = None
depends_on = None

def upgrade():
    op.add_column('documents', sa.Column('file_hash', sa.String(), index=True, nullable=True))

def downgrade():
    op.drop_column('documents', 'file_hash') 