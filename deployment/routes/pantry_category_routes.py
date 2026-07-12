"""
Pantry and category management routes (B57, audit 2026-07-07): the pantry
API (get/add/remove/reset), and the category API (list/add/rename/remove/
merge). Moved out of the former single flask_app.py verbatim - route bodies
are unchanged. None of these routes are referenced via url_for() anywhere
(the frontend calls them as fetch() paths, not Jinja endpoints), so no
blueprint-prefix sweep was needed for this extraction.

_load_household_categories()/_save_household_categories()/
_mark_category_removed()/_sort_categories() stay in app_core.py rather than
living here - settings_page() (a main-app route, not part of this
blueprint) also calls them directly for its "Manage Categories" section.
"""

import json
from pathlib import Path

from flask import jsonify, request

from deployment.app_core import (
    logger,
    current_household_id,
    acting_role_can_edit,
    acting_role_is_owner,
    log_activity,
    _load_pantry_db,
    _save_pantry_db,
    _load_household_categories,
    _save_household_categories,
    _mark_category_removed,
    _sort_categories,
    load_recipes_db,
    save_recipes_db,
    _get_lang,
)


def register(bp):
    @bp.route("/api/pantry", methods=["GET"])
    def api_get_pantry():
        """Pantry items in the CURRENT display language only - items that exist
        in both languages identically (e.g. 'salt') always show; items unique to
        the other language are hidden, even though they're still stored (adding
        'lemon' in English also silently stores 'sitron' so it's there if the
        household switches to Norwegian later)."""
        from core.household_paths import pantry_item_language

        lang = _get_lang()
        pantry = _load_pantry_db()
        visible = [
            p for p in pantry if pantry_item_language(p, default=lang) in (lang, "both")
        ]
        return jsonify({"success": True, "pantry": sorted(visible)})

    @bp.route("/api/pantry/add", methods=["POST"])
    def api_add_pantry_item():
        """Adding a known staple also adds its translation in the other language
        (e.g. adding 'lemon' silently also stores 'sitron'), so the pantry stays
        in sync no matter which language the household views it in later. Items
        with no known translation (anything custom the household typed) are just
        stored as-is."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"success": False, "message": "Viewers cannot edit the pantry"}
                ),
                403,
            )
        from core.household_paths import pantry_item_translation, pantry_item_language

        data = request.get_json() or {}
        item = (data.get("item") or "").strip().lower()
        if not item:
            return jsonify({"success": False, "message": "No item provided"}), 400

        pantry = list(_load_pantry_db())
        added = False
        if item not in pantry:
            pantry.append(item)
            added = True
        translation = pantry_item_translation(item)
        if translation and translation not in pantry:
            pantry.append(translation)
            added = True
        if added:
            _save_pantry_db(pantry)
            log_activity(f"Added '{item}' to pantry")

        lang = _get_lang()
        visible = [
            p for p in pantry if pantry_item_language(p, default=lang) in (lang, "both")
        ]
        return jsonify({"success": True, "pantry": sorted(visible)})

    @bp.route("/api/pantry/reset", methods=["POST"])
    def api_reset_pantry():
        """Reset pantry to default staples from pantry_staples.json seed file."""
        from core.household_paths import SEED_DIR
        import json as _json

        household_id = current_household_id()
        if not household_id:
            return jsonify({"success": False, "message": "Not authenticated"}), 401
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"success": False, "message": "Viewers cannot edit the pantry"}
                ),
                403,
            )

        staples_path = SEED_DIR / "pantry_staples.json"
        if not staples_path.exists():
            return (
                jsonify({"success": False, "message": "No default staples file found"}),
                404,
            )

        try:
            with open(staples_path, "r", encoding="utf-8") as f:
                pairs = _json.load(f).get("pantry_staples", [])
            items = set()
            for pair in pairs:
                if pair.get("en"):
                    items.add(pair["en"].strip().lower())
                if pair.get("no"):
                    items.add(pair["no"].strip().lower())
            _save_pantry_db(sorted(items))

            from core.household_paths import pantry_item_language

            lang = _get_lang()
            visible = sorted(
                p for p in items if pantry_item_language(p) in (lang, "both")
            )
            return jsonify({"success": True, "pantry": visible})
        except Exception as e:
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/api/pantry/remove", methods=["POST"])
    def api_remove_pantry_item():
        """Removing a known staple also removes its translation in the other
        language, so e.g. removing 'sugar' also removes 'sukker'."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"success": False, "message": "Viewers cannot edit the pantry"}
                ),
                403,
            )
        from core.household_paths import pantry_item_translation, pantry_item_language

        data = request.get_json() or {}
        item = (data.get("item") or "").strip().lower()
        if not item:
            return jsonify({"success": False, "message": "No item provided"}), 400

        translation = pantry_item_translation(item)
        to_remove = {item}
        if translation:
            to_remove.add(translation)
        pantry = [p for p in _load_pantry_db() if p not in to_remove]
        _save_pantry_db(pantry)
        log_activity(f"Removed '{item}' from pantry")

        lang = _get_lang()
        visible = [p for p in pantry if pantry_item_language(p) in (lang, "both")]
        return jsonify({"success": True, "pantry": sorted(visible)})

    @bp.route("/api/categories/add", methods=["POST"])
    def api_add_category():
        """Owner-only: add a custom category to this household's category list."""
        if not acting_role_is_owner():
            return jsonify({"success": False, "message": "Permission denied"}), 403

        household_id = current_household_id()
        if not household_id:
            return jsonify({"success": False, "message": "No household selected"}), 400

        data = request.get_json() or {}
        name = (data.get("name") or "").strip()
        icon = (data.get("icon") or "🍽️").strip()
        if not name:
            return jsonify({"success": False, "message": "Category name required"}), 400

        categories = _load_household_categories(household_id)
        code = name.lower().replace(" ", "_")
        if any(c.get("code") == code for c in categories):
            return (
                jsonify({"success": False, "message": "Category already exists"}),
                400,
            )

        categories.append(
            {
                "code": code,
                "name_no": name,
                "name_en": name,
                "description_no": "",
                "description_en": "",
                "icon": icon,
                "color": "#999999",
            }
        )
        _save_household_categories(household_id, categories)
        log_activity(f"Added category '{name}'")

        return jsonify({"success": True, "categories": _sort_categories(categories)})

    @bp.route("/api/categories/rename", methods=["POST"])
    def api_rename_category():
        """Owner-only: rename a category in this household's category list."""
        if not acting_role_is_owner():
            return jsonify({"success": False, "message": "Permission denied"}), 403

        household_id = current_household_id()
        if not household_id:
            return jsonify({"success": False, "message": "No household selected"}), 400

        data = request.get_json() or {}
        code = (data.get("code") or "").strip()
        new_name = (data.get("name") or "").strip()
        if not code or not new_name:
            return (
                jsonify(
                    {"success": False, "message": "Category code and new name required"}
                ),
                400,
            )

        categories = _load_household_categories(household_id)
        found = False
        for c in categories:
            if c.get("code") == code:
                c["name_no"] = new_name
                c["name_en"] = new_name
                found = True
                break

        if not found:
            return jsonify({"success": False, "message": "Category not found"}), 404

        _save_household_categories(household_id, categories)
        log_activity(f"Renamed category to '{new_name}'")

        return jsonify({"success": True, "categories": _sort_categories(categories)})

    @bp.route("/api/categories/remove", methods=["POST"])
    def api_remove_category():
        """Owner-only: remove a category from this household's category list.
        Moves all recipes in the deleted category to 'Uncategorized'."""
        if not acting_role_is_owner():
            return jsonify({"success": False, "message": "Permission denied"}), 403

        household_id = current_household_id()
        if not household_id:
            return jsonify({"success": False, "message": "No household selected"}), 400

        data = request.get_json() or {}
        code = (data.get("code") or "").strip()
        if not code:
            return jsonify({"success": False, "message": "Category code required"}), 400

        categories = _load_household_categories(household_id)
        cat_to_delete = next((c for c in categories if c.get("code") == code), None)
        if not cat_to_delete:
            return jsonify({"success": False, "message": "Category not found"}), 404

        cat_names_to_move = {
            cat_to_delete.get("name_en", ""),
            cat_to_delete.get("name_no", ""),
        }

        uncategorized = next(
            (c for c in categories if c.get("code") == "uncategorized"), None
        )
        if not uncategorized:
            uncategorized = {
                "code": "uncategorized",
                "name_en": "Uncategorized",
                "name_no": "Ukategorisert",
            }
            categories.append(uncategorized)

        uncategorized_name = uncategorized.get(
            f"name_{_get_lang()}"
        ) or uncategorized.get("name_en", "Uncategorized")

        recipes = load_recipes_db()
        moved = 0
        for r in recipes:
            if r.get("category") in cat_names_to_move:
                r["category"] = uncategorized_name
                moved += 1
        if moved:
            save_recipes_db(recipes)

        remaining = [c for c in categories if c.get("code") != code]
        _save_household_categories(household_id, remaining)
        _mark_category_removed(household_id, code)
        msg = f"Removed category '{code}'"
        if moved:
            msg += f" ({moved} recipes moved to Uncategorized)"
        log_activity(msg)

        return jsonify(
            {
                "success": True,
                "categories": _sort_categories(remaining),
                "recipes_moved": moved,
            }
        )

    @bp.route("/api/categories/merge", methods=["POST"])
    def api_merge_category():
        """Owner-only: move any recipes tagged with `from_code` over to
        `into_code`'s name (in whichever language each recipe's category string
        happens to be in), then remove the now-empty `from_code` category."""
        if not acting_role_is_owner():
            return jsonify({"success": False, "message": "Permission denied"}), 403

        household_id = current_household_id()
        if not household_id:
            return jsonify({"success": False, "message": "No household selected"}), 400

        data = request.get_json() or {}
        from_code = (data.get("from_code") or "").strip()
        into_code = (data.get("into_code") or "").strip()
        if not from_code or not into_code:
            return (
                jsonify({"success": False, "message": "Both categories required"}),
                400,
            )
        if from_code == into_code:
            return (
                jsonify(
                    {"success": False, "message": "Cannot merge a category into itself"}
                ),
                400,
            )

        categories = _load_household_categories(household_id)
        from_cat = next((c for c in categories if c.get("code") == from_code), None)
        into_cat = next((c for c in categories if c.get("code") == into_code), None)
        if not from_cat or not into_cat:
            return jsonify({"success": False, "message": "Category not found"}), 404

        from_names = {from_cat.get("name_en", ""), from_cat.get("name_no", "")}
        target_lang = _get_lang()
        target_name = (
            into_cat.get(f"name_{target_lang}")
            or into_cat.get("name_en")
            or into_cat["code"]
        )

        recipes = load_recipes_db()
        moved = 0
        for r in recipes:
            if r.get("category") in from_names:
                r["category"] = target_name
                moved += 1
        if moved:
            save_recipes_db(recipes)

        remaining = [c for c in categories if c.get("code") != from_code]
        _save_household_categories(household_id, remaining)
        _mark_category_removed(household_id, from_code)
        log_activity(
            f"Merged category '{from_cat.get('name_en')}' into '{into_cat.get('name_en')}' ({moved} recipe(s) moved)"
        )

        return jsonify(
            {"success": True, "categories": _sort_categories(remaining), "moved": moved}
        )

    @bp.route("/api/categories")
    def get_categories():
        """Get all available categories for this household, translated to current language.

        Previously read this household's categories.json file directly - but
        add/rename/remove/merge all write through _load_household_categories()/
        _save_household_categories(), which are DB-backed (with file as a
        migration-period fallback only). For any household that's already
        DB-backed, that meant categories added/renamed/removed via the API were
        saved correctly, but this listing endpoint (which drives the category
        filter dropdown, Add Recipe's category select, etc.) never reflected any
        of it - it kept reading the stale, untouched flat file. Fixed to use the
        same DB-aware loader as the rest of the category routes."""
        lang = _get_lang()
        household_id = current_household_id()
        categories = []

        # Add Favorites as a special first category (client-side only, stored in localStorage)
        favorites_name = "Favorites" if lang == "en" else "Favoritter"
        categories.append(
            {
                "code": "favorites",
                "name": favorites_name,  # This is what gets passed back as the category value
                "icon": "⭐",
            }
        )

        if household_id:
            raw_cats = _load_household_categories(household_id)
        else:
            # No household selected (rare/edge case) - fall back to the base
            # default category list rather than a per-household file.
            raw_cats = []
            base_file = Path(__file__).parent.parent.parent / "data" / "categories.json"
            if base_file.exists():
                try:
                    with open(base_file, "r", encoding="utf-8") as f:
                        raw_cats = json.load(f)
                except Exception as e:
                    logger.error(f"Error loading base categories: {e}")

        # Translate to current language. Skip pack-name pseudo-categories
        # (imported: true) - recipes now keep their own real dish-type
        # category through import (see B4b), so a recipe can never have
        # one of these as its category anymore. Selecting one in the
        # dropdown would always show an empty list, which is confusing -
        # better to not offer it at all than show a dead-end option.
        for cat in raw_cats:
            if not isinstance(cat, dict) or cat.get("imported"):
                continue
            translated = dict(cat)
            translated["name"] = (
                cat.get(f"name_{lang}") or cat.get("name_en") or cat.get("code")
            )
            categories.append(translated)

        return jsonify(_sort_categories(categories))
