"""Add missing indexes on frequently-queried FK columns (B56, audit 2026-07-07).

households.owner_id, household_members.household_id/user_id,
recipes.household_id, weekly_menus.household_id, and
shopping_lists.household_id are queried on nearly every request
(current_household_id() alone runs a household_members.user_id lookup on
every call) but had no index - not urgent at the household counts this app
runs at today, but a real cost as it grows, and cheap to add now while the
tables are still small (no expensive backfill/lock concern on a full-table
index build).

Revision ID: d7ad4d9fa3eb
Revises: f6a7b8c9d0e1
Create Date: 2026-07-08 00:00:00.000000

"""
from alembic import op


# revision identifiers, used by Alembic.
revision = "d7ad4d9fa3eb"
down_revision = "f6a7b8c9d0e1"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index(
        "ix_households_owner_id", "households", ["owner_id"], unique=False
    )
    op.create_index(
        "ix_household_members_household_id",
        "household_members",
        ["household_id"],
        unique=False,
    )
    op.create_index(
        "ix_household_members_user_id",
        "household_members",
        ["user_id"],
        unique=False,
    )
    op.create_index("ix_recipes_household_id", "recipes", ["household_id"], unique=False)
    op.create_index(
        "ix_weekly_menus_household_id", "weekly_menus", ["household_id"], unique=False
    )
    op.create_index(
        "ix_shopping_lists_household_id",
        "shopping_lists",
        ["household_id"],
        unique=False,
    )


def downgrade() -> None:
    op.drop_index("ix_shopping_lists_household_id", table_name="shopping_lists")
    op.drop_index("ix_weekly_menus_household_id", table_name="weekly_menus")
    op.drop_index("ix_recipes_household_id", table_name="recipes")
    op.drop_index("ix_household_members_user_id", table_name="household_members")
    op.drop_index("ix_household_members_household_id", table_name="household_members")
    op.drop_index("ix_households_owner_id", table_name="households")
