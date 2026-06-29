"""
Per-household data directory resolution.

Each household gets its own folder under data/households/<household_id>/
with its own recipes_db.json, weekly_menu.json, categories.json, etc.
The original flat data/ directory's pre-existing files are treated as
the seed/default content copied into a household's folder the first
time that household needs it, so existing test data isn't lost.
"""

import json
import shutil
from pathlib import Path

DATA_DIR = Path(__file__).parent.parent / 'data'
HOUSEHOLDS_DIR = DATA_DIR / 'households'

_SEED_FILES = ('weekly_menu.json', 'recipes_db.json', 'categories.json')
_PANTRY_STAPLES_FILE = DATA_DIR / 'pantry_staples.json'

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
            with open(_PANTRY_STAPLES_FILE, 'r', encoding='utf-8') as f:
                pairs = json.load(f).get('pantry_staples', [])
            for pair in pairs:
                en = pair.get('en', '').strip().lower()
                no = pair.get('no', '').strip().lower()
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
        return 'both'
    if is_no:
        return 'no'
    return 'en'


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


def _seed_pantry(hdir: Path):
    """New households start with a pre-filled pantry of common staples in
    both languages (so the per-language filter in the UI has something to
    show regardless of which language the household is using) rather than
    empty - the household then edits it (removes what they never keep, adds
    what they always have) to make it their own."""
    if not _PANTRY_STAPLES_FILE.exists():
        return
    try:
        with open(_PANTRY_STAPLES_FILE, 'r', encoding='utf-8') as f:
            pairs = json.load(f).get('pantry_staples', [])
        items = set()
        for pair in pairs:
            if pair.get('en'):
                items.add(pair['en'].strip().lower())
            if pair.get('no'):
                items.add(pair['no'].strip().lower())
        with open(hdir / 'pantry.json', 'w', encoding='utf-8') as f:
            json.dump(sorted(items), f, ensure_ascii=False, indent=2)
    except Exception:
        pass


def household_dir(household_id: str) -> Path:
    """Return (creating if needed) the data directory for a household, seeded
    from the legacy global data/ files on first use."""
    hdir = HOUSEHOLDS_DIR / str(household_id)
    if not hdir.exists():
        hdir.mkdir(parents=True, exist_ok=True)
        for filename in _SEED_FILES:
            src = DATA_DIR / filename
            if src.exists():
                shutil.copy(src, hdir / filename)
        _seed_pantry(hdir)
    return hdir


def menu_file(household_id: str) -> Path:
    return household_dir(household_id) / 'weekly_menu.json'


def recipes_db_file(household_id: str) -> Path:
    return household_dir(household_id) / 'recipes_db.json'


def _removed_categories_file(household_id: str) -> Path:
    return household_dir(household_id) / 'removed_categories.json'


def load_removed_categories(household_id: str):
    """Codes of categories this household has explicitly deleted or merged
    away - a tombstone list, so the self-heal below knows the difference
    between "never had this category" (should be added) and "had it, removed
    it on purpose" (must NOT be silently re-added next time the base seed is
    re-checked)."""
    path = _removed_categories_file(household_id)
    if not path.exists():
        return set()
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return set(json.load(f))
    except Exception:
        return set()


def mark_category_removed(household_id: str, code: str):
    """Record that this household explicitly removed a category, so the
    self-heal in categories_file() never re-adds it."""
    removed = load_removed_categories(household_id)
    removed.add(code)
    path = _removed_categories_file(household_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted(removed), f, ensure_ascii=False, indent=2)


def categories_file(household_id: str) -> Path:
    """The household's categories file, self-healed to include any base
    categories (by code) it's missing - e.g. if a category was added to the
    global seed after this household was already created. Never removes or
    overwrites a category the household already has, even if they renamed or
    customized it, so household-level edits are always preserved. Categories
    the household explicitly deleted (tracked in removed_categories.json)
    are never re-added by this self-heal, even if they still exist in the
    base seed file."""
    path = household_dir(household_id) / 'categories.json'
    base_path = DATA_DIR / 'categories.json'

    if not path.exists() or not base_path.exists():
        return path

    try:
        with open(path, 'r', encoding='utf-8') as f:
            household_cats = json.load(f)
        with open(base_path, 'r', encoding='utf-8') as f:
            base_cats = json.load(f)
    except Exception:
        return path

    removed_codes = load_removed_categories(household_id)
    existing_codes = {c.get('code') for c in household_cats}
    missing = [c for c in base_cats
               if c.get('code') not in existing_codes and c.get('code') not in removed_codes]
    changed = False

    if missing:
        household_cats.extend(missing)
        existing_codes.update(c.get('code') for c in missing)
        changed = True

    # One-time cleanup: 'rask' ("Quick Dinner") and 'quick_dinners' ("Quick
    # Dinners") were accidentally added as two separate categories for the
    # same thing in an earlier fix. Drop the redundant older one if both
    # ended up present, the same way the seed file itself was corrected.
    if 'rask' in existing_codes and 'quick_dinners' in existing_codes:
        household_cats = [c for c in household_cats if c.get('code') != 'rask']
        changed = True

    # Backfill the 'imported' flag onto built-in recipe-pack categories that
    # were seeded before this flag existed, so sort order (imported packs at
    # the bottom) works for households created before this fix too.
    base_imported_codes = {c.get('code') for c in base_cats if c.get('imported')}
    for c in household_cats:
        if c.get('code') in base_imported_codes and not c.get('imported'):
            c['imported'] = True
            changed = True

    if changed:
        with open(path, 'w', encoding='utf-8') as f:
            json.dump(household_cats, f, ensure_ascii=False, indent=2)

    return path


def activity_log_file(household_id: str) -> Path:
    return household_dir(household_id) / 'activity_log.json'


def pantry_file(household_id: str) -> Path:
    return household_dir(household_id) / 'pantry.json'


def _pantry_seeded_marker(household_id: str) -> Path:
    return household_dir(household_id) / '.pantry_seeded'


def load_pantry(household_id: str):
    """List of ingredient names (lowercased) this household already has on
    hand. Self-heals households created before the pantry pre-fill existed:
    an empty pantry with no seeded-marker file gets backfilled with the
    staples list once. A marker (not just "is the list empty") distinguishes
    "never seeded" from "household deliberately removed everything" - the
    latter must stay empty, not get re-filled every time it's loaded."""
    hdir = household_dir(household_id)
    marker = _pantry_seeded_marker(household_id)
    path = pantry_file(household_id)

    if not marker.exists():
        existing = []
        if path.exists():
            try:
                with open(path, 'r', encoding='utf-8') as f:
                    existing = json.load(f)
            except Exception:
                existing = []
        if not existing:
            _seed_pantry(hdir)
        marker.touch()

    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception:
        return []


def save_pantry(household_id: str, items):
    path = pantry_file(household_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(sorted(set(items)), f, ensure_ascii=False, indent=2)


def append_activity(household_id: str, actor: str, action: str):
    """Append one entry to a household's activity log (owner-visible audit trail)."""
    from datetime import datetime

    path = activity_log_file(household_id)
    entries = []
    if path.exists():
        try:
            with open(path, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        except Exception:
            entries = []

    entries.append({
        'timestamp': datetime.now().isoformat(),
        'actor': actor,
        'action': action,
    })
    entries = entries[-200:]  # cap log size

    with open(path, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)


def load_activity(household_id: str):
    path = activity_log_file(household_id)
    if not path.exists():
        return []
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return list(reversed(json.load(f)))
    except Exception:
        return []
