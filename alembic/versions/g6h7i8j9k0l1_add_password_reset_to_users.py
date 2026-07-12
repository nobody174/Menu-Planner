"""add password reset to users

Revision ID: g6h7i8j9k0l1
Revises: f5a6b7c8d9e0
Create Date: 2026-07-01

"""
from alembic import op
import sqlalchemy as sa

revision = 'g6h7i8j9k0l1'
down_revision = 'f5a6b7c8d9e0'
branch_labels = None
depends_on = None


def upgrade():
    op.add_column('users', sa.Column('password_reset_token', sa.String(64), nullable=True))
    op.add_column('users', sa.Column('password_reset_requested_at', sa.DateTime(), nullable=True))
    op.create_index('ix_users_password_reset_token', 'users', ['password_reset_token'])


def downgrade():
    op.drop_index('ix_users_password_reset_token', table_name='users')
    op.drop_column('users', 'password_reset_requested_at')
    op.drop_column('users', 'password_reset_token')
