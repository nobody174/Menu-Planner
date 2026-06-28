"""Add referral fields to users

Revision ID: b2c3d4e5f6a7
Revises: a1b2c3d4e5f6
Create Date: 2026-06-28 00:00:00.000000

"""
from typing import Sequence, Union
import secrets
import string

from alembic import op
import sqlalchemy as sa


revision: str = 'b2c3d4e5f6a7'
down_revision: Union[str, None] = 'a1b2c3d4e5f6'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _generate_code() -> str:
    alphabet = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(alphabet) for _ in range(8))


def upgrade() -> None:
    op.add_column('users', sa.Column('referral_code', sa.String(length=12), nullable=True))
    op.add_column('users', sa.Column('referred_by_user_id', sa.String(length=36), nullable=True))
    op.add_column('users', sa.Column('referred_by_code', sa.String(length=12), nullable=True))

    # Backfill referral_code for existing rows, then enforce NOT NULL + unique index.
    conn = op.get_bind()
    user_ids = [row[0] for row in conn.execute(sa.text('SELECT id FROM users')).fetchall()]
    used_codes = set()
    for user_id in user_ids:
        code = _generate_code()
        while code in used_codes:
            code = _generate_code()
        used_codes.add(code)
        conn.execute(
            sa.text('UPDATE users SET referral_code = :code WHERE id = :id'),
            {'code': code, 'id': user_id}
        )

    with op.batch_alter_table('users') as batch_op:
        batch_op.alter_column('referral_code', nullable=False)
        batch_op.create_unique_constraint('uq_users_referral_code', ['referral_code'])
        batch_op.create_index('ix_users_referral_code', ['referral_code'])


def downgrade() -> None:
    with op.batch_alter_table('users') as batch_op:
        batch_op.drop_index('ix_users_referral_code')
        batch_op.drop_constraint('uq_users_referral_code', type_='unique')
        batch_op.drop_column('referred_by_code')
        batch_op.drop_column('referred_by_user_id')
        batch_op.drop_column('referral_code')
