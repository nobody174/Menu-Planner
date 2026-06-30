"""Add email confirmation fields to users

Revision ID: f5a6b7c8d9e0
Revises: e4f5a6b7c8d9
Create Date: 2026-06-29 00:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = 'f5a6b7c8d9e0'
down_revision: Union[str, None] = 'e4f5a6b7c8d9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('users', sa.Column('email_confirmed_at', sa.DateTime(), nullable=True))
    op.add_column('users', sa.Column('email_confirmation_token', sa.String(length=64), nullable=True))
    op.create_index('ix_users_email_confirmation_token', 'users', ['email_confirmation_token'])

    # Grandfather in every account that existed before this feature shipped -
    # without this, every existing user (real trial testers included) would
    # be permanently locked out of login the moment this migration runs,
    # since they signed up under the old flow and have no way to retroactively
    # "confirm" an email they were never asked to confirm in the first place.
    # Only signups from this point forward go through the new confirm-before-login gate.
    op.execute("UPDATE users SET email_confirmed_at = CURRENT_TIMESTAMP WHERE email_confirmed_at IS NULL")


def downgrade() -> None:
    op.drop_index('ix_users_email_confirmation_token', table_name='users')
    op.drop_column('users', 'email_confirmation_token')
    op.drop_column('users', 'email_confirmed_at')
