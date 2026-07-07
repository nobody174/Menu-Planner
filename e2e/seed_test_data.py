#!/usr/bin/env python3
"""
Seed a confirmed test user + household + generated menu, for Playwright's
global-setup to log in as before running the visual-regression suite.

Run against a throwaway test database only - never point this at a real
dev or production database, since it creates fixed, predictable credentials.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import db
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household
from core.menu_generator import MenuGenerator

E2E_EMAIL = "e2e-test@example.com"
E2E_PASSWORD = "E2ETestPass123"
E2E_HOUSEHOLD_NAME = "Playwright Test Household"


def seed():
    db.drop_all()
    db.create_all()

    success, user, _ = create_user(E2E_EMAIL, E2E_PASSWORD)
    if not success:
        raise RuntimeError(f"Failed to create e2e test user: {user}")

    # Confirm via the real production code path (same one the email-link
    # click uses), rather than writing to email_confirmed_at directly.
    confirm_success, _ = confirm_email(user.email_confirmation_token)
    if not confirm_success:
        raise RuntimeError("Failed to confirm e2e test user's email")

    success, household, household_id = create_household(
        str(user.id), E2E_HOUSEHOLD_NAME
    )
    if not success:
        raise RuntimeError(f"Failed to create e2e test household: {household}")

    # Fixed seed, not the default random one: without this, every seed run
    # picks a different random set of recipes for the week, so a screenshot
    # baseline captured from one run can never reliably match a later run -
    # not a rendering bug, just non-deterministic test data. Confirmed via
    # a real CI failure (2026-07-07): the dashboard's Monday/Tuesday/
    # Wednesday recipes differed entirely between the baseline-capture run
    # and a later run, failing the visual diff on content, not layout.
    generator = MenuGenerator(household_id=household_id, seed=42)
    generator.run(save=True)

    print(f"Seeded e2e test user {E2E_EMAIL} / household {household_id}")


if __name__ == "__main__":
    seed()
