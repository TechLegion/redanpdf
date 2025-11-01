"""add owner_email to documents

Revision ID: add_owner_email_001
Revises: 20250703_add_file_hash
Create Date: 2025-01-27 08:45:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'add_owner_email_001'
down_revision = '20250703_add_file_hash'
branch_labels = None
depends_on = None


def upgrade() -> None:
    """Add owner_email column to documents table for resilient file access"""
    # Add the owner_email column
    op.add_column('documents', sa.Column('owner_email', sa.String(255), nullable=True))
    
    # Create index for better performance
    op.create_index('idx_documents_owner_email', 'documents', ['owner_email'])
    
    # Populate owner_email column with data from users table
    op.execute("""
        UPDATE documents 
        SET owner_email = u.email 
        FROM users u 
        WHERE documents.owner_id = u.id;
    """)


def downgrade() -> None:
    """Remove owner_email column from documents table"""
    # Drop the index first
    op.drop_index('idx_documents_owner_email', table_name='documents')
    
    # Drop the column
    op.drop_column('documents', 'owner_email')
