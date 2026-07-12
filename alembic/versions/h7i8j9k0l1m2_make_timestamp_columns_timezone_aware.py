"""Make timestamp columns timezone-aware (LO5)

Revision ID: h7i8j9k0l1m2
Revises: d7ad4d9fa3eb
Create Date: 2026-07-12

Every existing timestamp in these columns was written by datetime.utcnow(),
so they are already correct UTC instants - this migration only attaches the
UTC label so comparisons against datetime.now(timezone.utc) stop raising
"can't subtract offset-naive and offset-aware datetimes". No values change.

Postgres: TIMESTAMP -> TIMESTAMPTZ via `USING col AT TIME ZONE 'UTC'`, which
is a metadata-only reinterpretation (existing naive values are tagged UTC,
no row rewrite). SQLite has no separate tz-aware column type - it stores
ISO-format text either way, so this is a no-op there; the timezone-awareness
comes entirely from the Python-side change (models.py + call sites) once the
app process is running, regardless of backend.
"""
from alembic import op
import sqlalchemy as sa

revision = "h7i8j9k0l1m2"
down_revision = "d7ad4d9fa3eb"
branch_labels = None
depends_on = None

# (table, column) pairs for every datetime.utcnow()-populated column.
_COLUMNS = [
    ("users", "created_at"),
    ("users", "updated_at"),
    ("users", "email_confirmed_at"),
    ("users", "password_reset_requested_at"),
    ("households", "created_at"),
    ("households", "updated_at"),
    ("household_members", "joined_at"),
    ("recipes", "created_at"),
    ("recipes", "updated_at"),
    ("weekly_menus", "created_at"),
    ("weekly_menus", "updated_at"),
    ("shopping_lists", "created_at"),
    ("shopping_lists", "updated_at"),
]


def upgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        # SQLite (and anything else) has no distinct tz-aware column type -
        # nothing to alter at the schema level.
        return
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f'TYPE TIMESTAMPTZ USING "{column}" AT TIME ZONE \'UTC\''
        )


def downgrade():
    bind = op.get_bind()
    if bind.dialect.name != "postgresql":
        return
    for table, column in _COLUMNS:
        op.execute(
            f'ALTER TABLE {table} ALTER COLUMN "{column}" '
            f'TYPE TIMESTAMP USING "{column}" AT TIME ZONE \'UTC\''
        )
