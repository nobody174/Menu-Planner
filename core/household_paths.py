"""
Per-household data directory resolution.

Each household gets its own folder under data/households/<household_id>/
with its own recipes_db.json, weekly_menu.json, categories.json, etc.
The original flat data/ directory's pre-existing files are treated as
the seed/default content copied into a household's folder the first
time that household needs it, so existing test data isn't lost.

B61 (2026-07-09): this file used to also hold a full parallel file-based
implementation of every household data type (categories, removed-category
tombstones, pantry, activity log) as a fallback for households with no
matching database row. Deleted after confirming, via Neon, that exactly 3
households exist and all are real DB rows, and that this Render service has
no persistent Disk attached - so a file-only household could not have
survived any deploy to exist. What remains here (household_dir(),
menu_file(), recipes_db_file(), the imported-packs file functions) is
either still genuinely used as a last-resort fallback inside a try/except
around a real DB call (core/menu_generator.py), or - imported_packs
specifically - is still the *only* implementation that feature has; it was
never actually wired up to the DB columns that exist for it. See B61 in
docs/BACKLOG.md.
"""

import json
import shutil
from pathlib import Path

from sqlalchemy.orm.attributes import flag_modified

DATA_DIR = Path(__file__).parent.parent / "data"
HOUSEHOLDS_DIR = DATA_DIR / "households"

# Static seed content (categories.json's base list, pantry_staples.json) is
# read from here instead of DATA_DIR - see the matching comment in
# deployment/flask_app.py for why. household data (HOUSEHOLDS_DIR) stays on
# DATA_DIR/the volume, only the read-only seed source moves.
SEED_DIR = Path(__file__).parent.parent / "data-seed"
if not SEED_DIR.exists():
    SEED_DIR = DATA_DIR

_SEED_FILES = ("weekly_menu.json", "recipes_db.json", "categories.json")
_PANTRY_STAPLES_FILE = SEED_DIR / "pantry_staples.json"

_pantry_translation_cache = None


def _pantry_translations():
    """Load the {en<->no} pantry staples translation pairs once and cache
    them. Returns (en_to_no, no_to_en) dicts, both lowercased. Only the known
    staples have a translation - anything a household types that isn't in
    this list has no automatic pair, by design (see pantry_staples.json)."""
    global _pantry_translation_cache
    if _pantry_translation_cache is not None:
        return _pantry_translation_cache

    en_to_no, no_to_en = {}, {}
    if _PANTRY_STAPLES_FILE.exists():
        try:
            with open(_PANTRY_STAPLES_FILE, "r", encoding="utf-8") as f:
                pairs = json.load(f).get("pantry_staples", [])
            for pair in pairs:
                en = pair.get("en", "").strip().lower()
                no = pair.get("no", "").strip().lower()
                if en and no:
                    en_to_no[en] = no
                    no_to_en[no] = en
        except Exception:
            pass

    _pantry_translation_cache = (en_to_no, no_to_en)
    return _pantry_translation_cache


def pantry_item_language(item: str) -> str:
    """Best guess at which language a pantry item string is in, based on the
    known staples translation list. Returns 'en', 'no', or 'both' (identical
    in both languages, e.g. 'salt') - callers treat 'both' as matching either
    language filter. Unknown/custom items default to 'en' (most users typing
    a fresh item are typing in whichever language they're currently using,
    and since it has no pair anyway, defaulting doesn't affect translation)."""
    en_to_no, no_to_en = _pantry_translations()
    item = item.strip().lower()
    is_en = item in en_to_no
    is_no = item in no_to_en
    if is_en and is_no:
        return "both"
    if is_no:
        return "no"
    return "en"


def pantry_item_translation(item: str):
    """The known translation of a pantry item, or None if it's not a
    recognized staple (e.g. something the household typed themselves)."""
    en_to_no, no_to_en = _pantry_translations()
    item = item.strip().lower()
    if item in en_to_no:
        return en_to_no[item]
    if item in no_to_en:
        return no_to_en[item]
    return None


def default_pantry_staples() -> list:
    """The sorted list of pantry staple items (both languages) a fresh
    household is seeded with. Pure read of the static seed file - no
    household-specific file I/O. Used directly by the DB-backed pantry seed
    path (B61, 2026-07-09); _seed_pantry() below still wraps this for
    household_dir()'s own directory-seeding step."""
    if not _PANTRY_STAPLES_FILE.exists():
        return []
    try:
        with open(_PANTRY_STAPLES_FILE, "r", encoding="utf-8") as f:
            pairs = json.load(f).get("pantry_staples", [])
        items = set()
        for pair in pairs:
            if pair.get("en"):
                items.add(pair["en"].strip().lower())
            if pair.get("no"):
                items.add(pair["no"].strip().lower())
        return sorted(items)
    except Exception:
        return []


def _seed_pantry(hdir: Path):
    """Writes the static staples list into a freshly-created household
    directory's pantry.json - part of household_dir()'s one-time directory
    seed, not something read back from again (B61, 2026-07-09: the DB pantry
    seed path no longer touches this at all, see default_pantry_staples())."""
    items = default_pantry_staples()
    if not items:
        return
    try:
        with open(hdir / "pantry.json", "w", encoding="utf-8") as f:
            json.dump(items, f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def household_dir(household_id: str) -> Path:
    """Return (creating if needed) the data directory for a household, seeded
    from the legacy global data/ files on first use. recipes_db.json starts
    empty so households don't inherit global recipes.

    B61 (2026-07-09): only reached today via menu_file()/recipes_db_file()'s
    callers in core/menu_generator.py's own try/except DB-failure fallback -
    a genuine last resort, not a routine code path."""
    hdir = HOUSEHOLDS_DIR / str(household_id)
    if not hdir.exists():
        hdir.mkdir(parents=True, exist_ok=True)
        for filename in _SEED_FILES:
            src = SEED_DIR / filename
            if src.exists():
                if filename == "recipes_db.json":
                    # Start empty so new households have a clean slate
                    with open(hdir / filename, "w", encoding="utf-8") as f:
                        json.dump([], f)
                else:
                    shutil.copy(src, hdir / filename)
        _seed_pantry(hdir)
    return hdir


def menu_file(household_id: str) -> Path:
    return household_dir(household_id) / "weekly_menu.json"


def recipes_db_file(household_id: str) -> Path:
    return household_dir(household_id) / "recipes_db.json"


def imported_packs_file(household_id: str) -> Path:
    return household_dir(household_id) / "imported_packs.json"


def load_imported_packs(household_id: str) -> dict:
    """Display metadata (name, icon, color) for recipe packs this household
    has imported, keyed by pack id - written at import time, read by the
    "Manage Recipe Packs" page. Tracked separately from recipe categories so
    importing a pack no longer overwrites a recipe's real dish-type category
    with the pack name (see BACKLOG_2026-06-30.md B4b).

    B61 (2026-07-09): unlike every other data type in this file, this one
    was never actually wired up to the DB columns that exist for it
    (load_imported_packs_from_db()/save_imported_packs_to_db() below are
    defined but have no real caller anywhere) - this file-based version is
    genuinely the only implementation, called unconditionally from
    deployment/routes/recipe_pack_routes.py. Since this Render service has
    no persistent Disk, this metadata likely doesn't survive a redeploy
    today - a real gap, not something this cleanup pass fixes. Flagged as a
    new backlog item rather than silently patched mid-cleanup."""
    path = imported_packs_file(household_id)
    if not path.exists():
        return {}
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_imported_pack_metadata(
    household_id: str, pack_id: str, display_name: str, icon: str, color: str
):
    """Record (or update) display metadata for one imported pack."""
    packs = load_imported_packs(household_id)
    packs[pack_id] = {"display_name": display_name, "icon": icon, "color": color}
    with open(imported_packs_file(household_id), "w", encoding="utf-8") as f:
        json.dump(packs, f, ensure_ascii=False, indent=2)


def remove_imported_pack_metadata(household_id: str, pack_id: str):
    """Forget a pack's display metadata once its recipes have all been removed."""
    packs = load_imported_packs(household_id)
    if pack_id in packs:
        del packs[pack_id]
        with open(imported_packs_file(household_id), "w", encoding="utf-8") as f:
            json.dump(packs, f, ensure_ascii=False, indent=2)


# Database-backed functions for F4 migration (PostgreSQL JSONB storage)
def load_recipes_db_from_db(household):
    """Load recipes_db from database JSONB column."""
    if household.recipes_db is None:
        return []
    return household.recipes_db if isinstance(household.recipes_db, list) else []


def load_pantry_from_db(household):
    """Load pantry from database JSONB column."""
    if household.pantry is None:
        return []
    return household.pantry if isinstance(household.pantry, list) else []


def load_removed_categories_from_db(household) -> set:
    """Codes of categories this DB-backed household has explicitly deleted or
    merged away (M2, audit 2026-07-07). This used to live only in a file on
    the Render disk (household_dir()/removed_categories.json) even for
    otherwise fully DB-backed households - the one piece of category state
    that wasn't actually in the database. Any disk loss/detach, or restoring
    Postgres from a backup onto a fresh volume, would silently resurrect
    every category a household had deliberately deleted, since the self-heal
    below has no surviving tombstone to check against.

    B61 (2026-07-09): the legacy-file read fallback has been removed - this
    Render service has no persistent Disk attached, so
    households/<id>/removed_categories.json could never have survived a
    deploy to read back here anyway. A non-list column now just means
    "nothing removed yet," which is the correct default."""
    if isinstance(household.removed_categories, list):
        return set(household.removed_categories)
    return set()


def mark_category_removed_to_db(household, code: str):
    """Record that this DB-backed household explicitly removed a category,
    directly in the JSONB column (M2). Caller is responsible for committing
    the session."""
    removed = load_removed_categories_from_db(household)
    removed.add(code)
    household.removed_categories = sorted(removed)
    flag_modified(household, "removed_categories")


def load_categories_from_db(household):
    """Load categories from database JSONB column with self-heal logic."""
    # Note: households whose 'categories' column was never seeded (None)
    # used to return [] here immediately, skipping the self-heal block below
    # entirely - meaning "Manage Categories" stayed permanently empty for
    # them (base_cats never got merged in), even though adding a custom
    # category worked fine (it just appended to an empty list).
    categories = household.categories if isinstance(household.categories, list) else []

    # Self-heal logic: ensure base categories are present
    try:
        base_path = SEED_DIR / "categories.json"
        if base_path.exists():
            with open(base_path, "r", encoding="utf-8") as f:
                base_cats = json.load(f)
        else:
            base_cats = []
    except Exception:
        base_cats = []

    removed_codes = load_removed_categories_from_db(household)
    existing_codes = {c.get("code") for c in categories if isinstance(c, dict)}
    missing = [
        c
        for c in base_cats
        if c.get("code") not in existing_codes and c.get("code") not in removed_codes
    ]

    if missing:
        categories.extend(missing)

    return categories


def load_weekly_menu_from_db(household):
    """Load weekly_menu from database JSONB column."""
    if household.weekly_menu is None:
        return {}
    return household.weekly_menu if isinstance(household.weekly_menu, dict) else {}


def load_activity_from_db(household):
    """Load activity_log from database JSONB column."""
    if household.activity_log is None:
        return []
    log = household.activity_log if isinstance(household.activity_log, list) else []
    return list(reversed(log))


def load_imported_packs_from_db(household):
    """Load imported_packs from database JSONB column."""
    if household.imported_packs is None:
        return {}
    return (
        household.imported_packs if isinstance(household.imported_packs, dict) else {}
    )


def save_recipes_db_to_db(household, recipes_data):
    """Save recipes_db to database JSONB column."""
    household.recipes_db = recipes_data
    flag_modified(household, "recipes_db")


def save_pantry_to_db(household, pantry_items):
    """Save pantry to database JSONB column."""
    household.pantry = sorted(set(pantry_items))
    flag_modified(household, "pantry")


def save_categories_to_db(household, categories_data):
    """Save categories to database JSONB column."""
    household.categories = categories_data
    flag_modified(household, "categories")


def save_weekly_menu_to_db(household, menu_data):
    """Save weekly_menu to database JSONB column.

    flag_modified() is required here, not optional: callers like
    /api/swap-recipe call load_weekly_menu_from_db() (which hands back
    household.weekly_menu directly, not a copy), mutate a nested dict
    inside it in place (e.g. target['recipe_id'] = ...), and then pass that
    SAME object straight back into this function. Because it's literally
    the same Python object SQLAlchemy already has loaded, a plain
    `household.weekly_menu = menu_data` assignment doesn't register as a
    change - there's no "before" state distinguishable from "after", since
    they're the same mutated object the whole time. That silently skipped
    the UPDATE entirely: the API call returned 200 "success" (the in-memory
    dict really was mutated correctly), but the swap never reached the
    database, so a follow-up read showed the old, unswapped menu. This is
    the root cause of the reported "swap day does nothing" / "recipe lands
    on the wrong day" bug - flag_modified() forces SQLAlchemy to include
    this column in the UPDATE regardless of object identity/equality."""
    household.weekly_menu = menu_data
    flag_modified(household, "weekly_menu")


def save_activity_to_db(household, activity_entries):
    """Save activity_log to database JSONB column (capped at 200 entries)."""
    household.activity_log = (
        activity_entries[-200:] if len(activity_entries) > 200 else activity_entries
    )
    flag_modified(household, "activity_log")


def save_imported_packs_to_db(household, packs_data):
    """Save imported_packs to database JSONB column."""
    household.imported_packs = packs_data
    flag_modified(household, "imported_packs")


def append_activity_to_db(household, actor: str, action: str):
    """Append entry to activity log in database."""
    from datetime import datetime

    entries = load_activity_from_db(household) if household.activity_log else []
    # Reverse back to original order (load_activity_from_db reverses for display)
    entries = list(reversed(entries))

    entries.append(
        {
            "timestamp": datetime.now().isoformat(),
            "actor": actor,
            "action": action,
        }
    )
    save_activity_to_db(household, entries)
