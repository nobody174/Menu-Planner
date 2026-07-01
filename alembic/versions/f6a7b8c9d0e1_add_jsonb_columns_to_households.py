"""Add JSONB columns to households for data migration from file storage to database.

Revision ID: f6a7b8c9d0e1
Revises: a1b2c3d4e5f6
Create Date: 2026-07-01 12:00:00.000000

"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = 'f6a7b8c9d0e1'
down_revision = 'g6h7i8j9k0l1'
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add JSONB columns to households table for storing data currently in JSON files
    op.add_column('households', sa.Column('recipes_db', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('pantry', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('weekly_menu', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('categories', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('activity_log', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('removed_categories', sa.JSON(), nullable=True))
    op.add_column('households', sa.Column('imported_packs', sa.JSON(), nullable=True))


def downgrade() -> None:
    # Remove JSONB columns if migration is rolled back
    op.drop_column('households', 'imported_packs')
    op.drop_column('households', 'removed_categories')
    op.drop_column('households', 'activity_log')
    op.drop_column('households', 'categories')
    op.drop_column('households', 'weekly_menu')
    op.drop_column('households', 'pantry')
    op.drop_column('households', 'recipes_db')
