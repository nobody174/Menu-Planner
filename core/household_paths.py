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
    return hdir


def menu_file(household_id: str) -> Path:
    return household_dir(household_id) / 'weekly_menu.json'


def recipes_db_file(household_id: str) -> Path:
    return household_dir(household_id) / 'recipes_db.json'


def categories_file(household_id: str) -> Path:
    return household_dir(household_id) / 'categories.json'


def activity_log_file(household_id: str) -> Path:
    return household_dir(household_id) / 'activity_log.json'


def pantry_file(household_id: str) -> Path:
    return household_dir(household_id) / 'pantry.json'


def load_pantry(household_id: str):
    """List of ingredient names (lowercased) this household already has on hand."""
    path = pantry_file(household_id)
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
