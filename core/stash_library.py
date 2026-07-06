"""Loaders for the "stash" data files - recipes that were deliberately kept
out of the dinner planner and recipe-pack system, but preserved for future
features (see BACKLOG tickets F2/F8/F9):

- data/dessert-stash.json  - desserts, cakes, cookies (future F2/F9)
- data/drinks-stash.json   - mulled wine, punch etc.  (future F2)
- data/sides-stash.json    - side dishes, not standalone dinners (future F8)

Deliberately isolated from core/household_paths.py and the recipe-pack
loading in deployment/flask_app.py: these stashes are NOT dinners, aren't
household-scoped, and aren't part of menu generation. Keeping the loading
code here (rather than bolting it onto the existing recipe/menu helpers)
means the eventual real features (a dessert browser, a side-stash picker,
a dessert step in the planner) can import exactly what they need without
pulling in unrelated menu/household logic - and this module can be deleted
outright if a future feature ends up wanting a different data shape,
without touching anything else.

Every function here is read-only. Nothing in this module is wired into the
public app yet - see deployment/flask_app.py's FEATURE_FLAGS block for the
hidden routes that use it.
"""

import json
from pathlib import Path

_DATA_DIR = Path(__file__).parent.parent / "data"

_STASH_FILES = {
    "dessert": "dessert-stash.json",
    "drinks": "drinks-stash.json",
    "sides": "sides-stash.json",
}


def _load_stash(stash_name):
    """Load one stash file and return its recipe list (empty list if the
    file is missing or malformed, so a hidden/incomplete feature never
    500s - it just shows nothing)."""
    filename = _STASH_FILES.get(stash_name)
    if not filename:
        raise ValueError(
            f"Unknown stash '{stash_name}', expected one of {list(_STASH_FILES)}"
        )
    path = _DATA_DIR / filename
    if not path.exists():
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except (json.JSONDecodeError, OSError):
        return []
    return data.get("recipes", []) if isinstance(data, dict) else []


def load_dessert_stash():
    """All recipes kept for the future dessert-browsing / dessert-planner
    features (F2, F9)."""
    return _load_stash("dessert")


def load_drinks_stash():
    """All recipes kept for the future drinks-browsing feature (F2)."""
    return _load_stash("drinks")


def load_sides_stash():
    """All recipes kept for the future side-stash feature (F8)."""
    return _load_stash("sides")


def find_in_stash(stash_name, recipe_id):
    """Look up a single recipe by id within one stash. Returns None if not
    found - used by detail views once those exist."""
    for recipe in _load_stash(stash_name):
        if recipe.get("id") == recipe_id:
            return recipe
    return None


# --- Future integration hook (F9: dessert system in the dinner planner) ----
# Not called anywhere yet - MenuGenerator (core/menu_generator.py) has no
# knowledge of desserts today, and this function is intentionally a stub
# rather than a half-wired feature. When F9 is actually built, the dinner
# planner can call this to attach a suggested dessert to a generated menu
# without any changes needed to this module's data loading above.
def suggest_dessert_for_menu(exclude_ids=None):
    """Return one dessert recipe suitable for pairing with a dinner menu,
    or None if the stash is empty. `exclude_ids` lets a future caller avoid
    repeating a dessert already used elsewhere in the same week."""
    exclude_ids = set(exclude_ids or [])
    candidates = [r for r in load_dessert_stash() if r.get("id") not in exclude_ids]
    return candidates[0] if candidates else None
