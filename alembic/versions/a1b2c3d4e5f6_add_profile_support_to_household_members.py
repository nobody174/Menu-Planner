"""Add profile support to household_members

Revision ID: a1b2c3d4e5f6
Revises: d0d40b4db7ac
Create Date: 2026-06-27 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'a1b2c3d4e5f6'
down_revision: Union[str, None] = 'd0d40b4db7ac'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('household_members', 'user_id', nullable=True)
    op.add_column('household_members', sa.Column('is_profile', sa.Boolean(), nullable=False, server_default=sa.false()))
    op.add_column('household_members', sa.Column('display_name', sa.String(length=100), nullable=True))
    op.add_column('household_members', sa.Column('avatar_type', sa.String(length=20), nullable=True))
    op.add_column('household_members', sa.Column('avatar_value', sa.String(length=500), nullable=True))


def downgrade() -> None:
    op.drop_column('household_members', 'avatar_value')
    op.drop_column('household_members', 'avatar_type')
    op.drop_column('household_members', 'display_name')
    op.drop_column('household_members', 'is_profile')
    op.alter_column('household_members', 'user_id', nullable=False)
