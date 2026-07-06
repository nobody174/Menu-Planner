"""
Backfill household data from JSON files to PostgreSQL JSONB columns.

One-time script to migrate existing household data from /app/data/households/<id>/*.json
files into the Household model's JSONB columns (recipes_db, pantry, categories, etc.).

Usage:
    python scripts/backfill_household_data.py [--dry-run]

Options:
    --dry-run   Show what would be migrated without actually committing to database
"""

import json
import sys
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from database.models import Household
from core.household_paths import HOUSEHOLDS_DIR


def load_json_file(path: Path):
    """Safely load JSON file, return None if missing or corrupt."""
    if not path.exists():
        return None
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"  ⚠️  Error reading {path.name}: {e}")
        return None


def backfill_household(session, household: Household, dry_run: bool = False):
    """Migrate one household's data from files to database JSONB columns."""
    hdir = HOUSEHOLDS_DIR / str(household.id)

    if not hdir.exists():
        print(f"  ℹ️  No data directory found (household never seeded)")
        return True

    # Load all JSON files
    recipes_db = load_json_file(hdir / 'recipes_db.json')
    pantry = load_json_file(hdir / 'pantry.json')
    categories = load_json_file(hdir / 'categories.json')
    weekly_menu = load_json_file(hdir / 'weekly_menu.json')
    activity_log = load_json_file(hdir / 'activity_log.json')
    removed_categories = load_json_file(hdir / 'removed_categories.json')
    imported_packs = load_json_file(hdir / 'imported_packs.json')

    # Report what we're about to migrate
    counts = {
        'recipes': len(recipes_db) if recipes_db else 0,
        'pantry_items': len(pantry) if pantry else 0,
        'categories': len(categories) if categories else 0,
        'activity_entries': len(activity_log) if activity_log else 0,
        'imported_packs': len(imported_packs) if imported_packs else 0,
    }

    print(f"  📊 Data to migrate:")
    print(f"      - {counts['recipes']} recipes")
    print(f"      - {counts['pantry_items']} pantry items")
    print(f"      - {counts['categories']} categories")
    print(f"      - {counts['activity_entries']} activity entries")
    print(f"      - {counts['imported_packs']} imported packs")

    if dry_run:
        print(f"  🔄 [DRY RUN] Would migrate data to database")
        return True

    # Migrate to database JSONB columns
    household.recipes_db = recipes_db
    household.pantry = pantry
    household.categories = categories
    household.weekly_menu = weekly_menu
    household.activity_log = activity_log
    household.removed_categories = removed_categories
    household.imported_packs = imported_packs

    try:
        session.commit()
        print(f"  ✅ Successfully migrated to database")
        return True
    except Exception as e:
        session.rollback()
        print(f"  ❌ Failed to save to database: {e}")
        return False


def main():
    """Backfill all households from file storage to database."""
    dry_run = '--dry-run' in sys.argv

    session = SessionLocal()
    try:
        households = session.query(Household).all()

        if not households:
            print("No households found in database.")
            return 0

        print(f"📋 Backfilling {len(households)} household(s) to PostgreSQL JSONB...")
        print()

        successful = 0
        failed = 0

        for i, household in enumerate(households, 1):
            print(f"[{i}/{len(households)}] Household: {household.name} ({household.id})")
            if backfill_household(session, household, dry_run):
                successful += 1
            else:
                failed += 1
            print()

        print("=" * 60)
        print(f"✅ Successful: {successful}")
        print(f"❌ Failed: {failed}")

        if dry_run:
            print("\n🔄 [DRY RUN COMPLETE] No data was actually committed.")
        else:
            print(f"\n✨ Backfill complete! {successful} household(s) migrated to database.")

        return 0 if failed == 0 else 1

    except Exception as e:
        print(f"Fatal error: {e}")
        return 1
    finally:
        session.close()


if __name__ == '__main__':
    sys.exit(main())
