"""Restore search_vector for FTS

Revision ID: restore_fts
Revises: 5768ea9a7865
Create Date: 2023-10-27
"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'restore_fts'
down_revision = '5768ea9a7865'
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.execute("ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS search_vector tsvector;")
    op.execute("CREATE INDEX IF NOT EXISTS idx_document_chunks_search_vector ON document_chunks USING GIN(search_vector);")
    op.execute("UPDATE document_chunks SET search_vector = to_tsvector('english', text);")

def downgrade() -> None:
    op.execute("DROP INDEX IF EXISTS idx_document_chunks_search_vector;")
    op.execute("ALTER TABLE document_chunks DROP COLUMN IF EXISTS search_vector;")
