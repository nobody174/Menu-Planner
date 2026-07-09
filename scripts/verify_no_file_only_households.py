#!/usr/bin/env python3
"""
B61 (2026-07-09): read-only check for "file-only" households - a household
directory under data/households/<id>/ with no matching row in the
households table. Several load/save helpers in deployment/app_core.py
(load_menu, save_menu, load_recipes_db, save_recipes_db,
_load_household_categories, _save_household_categories,
_mark_category_removed) still carry an "if not household: fall back to
file" branch left over from the F4 file-to-Postgres migration. Every
household is created with a DB row today (core/household_helpers.py's
create_household()), so that branch should be unreachable - but this has
never been confirmed against real production data, only reasoned about
from the code. Run this against production before deleting those
fallback branches.

Does NOT modify anything - read-only, safe to run any time.

Usage:
  Run via the Render Shell for this service, or locally with the
  production DATABASE_URL set:
    DATABASE_URL=<production-url> python scripts/verify_no_file_only_households.py
"""
import os
import sys
from pathlib import Path

import psycopg2

db_url = os.getenv("DATABASE_URL")
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

households_dir = Path(__file__).parent.parent / "data" / "households"

conn = psycopg2.connect(db_url, sslmode="require")
cur = conn.cursor()
cur.execute("SELECT id FROM households")
db_ids = {str(row[0]) for row in cur.fetchall()}
cur.close()
conn.close()

if not households_dir.exists():
    print(f"No {households_dir} directory found - nothing to check, all households are DB-only.")
    sys.exit(0)

file_ids = {p.name for p in households_dir.iterdir() if p.is_dir()}

orphaned = file_ids - db_ids

print(f"Households in Postgres: {len(db_ids)}")
print(f"Household directories on disk: {len(file_ids)}")

if orphaned:
    print(f"\nFOUND {len(orphaned)} file-only household(s) with NO matching DB row:")
    for hid in sorted(orphaned):
        print(f"  - {hid}")
    print(
        "\nDo NOT delete the file-fallback branches in deployment/app_core.py "
        "until these are resolved (either migrated into the DB or confirmed "
        "genuinely abandoned/safe to ignore)."
    )
    sys.exit(1)
else:
    print(
        "\nNo orphaned file-only households found - every household directory "
        "on disk (if any) has a matching DB row. Safe to delete the "
        "'if not household: fall back to file' branches in "
        "deployment/app_core.py (see B61 in docs/BACKLOG.md)."
    )
    sys.exit(0)
