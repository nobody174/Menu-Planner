"""
Recipe pack and stash routes (B57, audit 2026-07-07): browsing/importing/
removing recipe packs, the "Manage Recipe Packs" page, and the hidden
dev-only dessert/drinks and sides stash browsers (behind FEATURE_FLAGS).
Moved out of the former single flask_app.py verbatim - route bodies are
unchanged. None of these routes are referenced via url_for() anywhere.
"""

import json

from flask import render_template, jsonify, request, abort

from deployment.app_core import (
    logger,
    SEED_DIR,
    _get_lang,
    _normalize_recipe,
    feature_enabled,
    current_household_id,
    acting_role_can_edit,
    load_recipes_db,
    save_recipes_db,
    log_activity,
    _load_imported_packs_db,
    _save_imported_pack_metadata_db,
    _remove_imported_pack_metadata_db,
)


def get_available_recipe_packs():
    """Load all available recipe packs from data/recipe-packs/"""
    packs_dir = SEED_DIR / "recipe-packs"
    packs = []

    if not packs_dir.exists():
        logger.warning(f"Recipe packs directory not found: {packs_dir}")
        return packs

    for pack_file in sorted(packs_dir.glob("pack_*.json")):
        try:
            with open(pack_file, "r", encoding="utf-8") as f:
                pack = json.load(f)
                packs.append(pack)
        except Exception as e:
            logger.error(f"Error loading pack {pack_file}: {e}")

    return packs


def register(bp):
    @bp.route("/api/recipe-packs/list")
    def api_recipe_packs_list():
        """Get list of available recipe packs, flagging which ones this
        household has already imported (by source_pack on its own recipes)."""
        packs = get_available_recipe_packs()

        imported_pack_ids = set()
        household_id = current_household_id()
        if household_id:
            for r in load_recipes_db():
                if r.get("source_pack"):
                    imported_pack_ids.add(r["source_pack"])

        simplified = []
        for pack in packs:
            simplified.append(
                {
                    "packId": pack["packId"],
                    "packName": pack["packName"],
                    "packDescription": pack["packDescription"],
                    "packIcon": pack.get("packImage", "📦"),
                    "packColor": pack.get("packColor", "#999999"),
                    "recipeCount": pack["recipeCount"],
                    "estimatedCookTime": pack["estimatedCookTime"],
                    "difficulty": pack["difficulty"],
                    "alreadyImported": pack["packId"] in imported_pack_ids,
                }
            )
        return jsonify(simplified)

    @bp.route("/api/recipe-packs/import", methods=["POST"])
    def api_recipe_packs_import():
        """Import selected recipe packs into user's recipe database"""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"success": False, "message": "Viewers cannot import recipe packs"}
                ),
                403,
            )
        try:
            data = request.get_json()
            pack_ids = data.get("packIds", [])

            if not pack_ids:
                return jsonify({"success": False, "message": "No packs selected"}), 400

            # Load all packs
            all_packs = get_available_recipe_packs()
            recipes_to_import = []

            # Collect recipes from selected packs, keeping bilingual fields intact.
            # The recipe's own dish-type category (Chicken, Salads, etc.) is kept
            # as-is - it's what drives normal category-dropdown filtering and menu
            # generation. Which pack a recipe came from is tracked separately via
            # source_pack, purely for "Manage Recipe Packs" bookkeeping (grouping/
            # removing everything imported from one pack) - it must NOT be used
            # as the dish-type category, or imported recipes can only ever be
            # found under their pack name instead of e.g. "Chicken" or "Salads".
            pack_metadata = (
                {}
            )  # source_pack code -> display info, for categories.json bookkeeping
            for pack in all_packs:
                if pack["packId"] in pack_ids:
                    pack_name_field = pack.get("packName", {})
                    if isinstance(pack_name_field, dict):
                        pack_display_name = (
                            pack_name_field.get("en")
                            or pack_name_field.get("no")
                            or "Imported Pack"
                        )
                    else:
                        pack_display_name = str(pack_name_field)

                    pack_metadata[pack["packId"]] = {
                        "display_name": pack_display_name,
                        "icon": pack.get("packImage", "📦"),
                        "color": pack.get("packColor", "#999999"),
                    }

                    for recipe in pack["recipes"]:
                        # Normalize only non-bilingual technical fields, keep titles/descriptions as bilingual dicts
                        r = dict(recipe)
                        # Track pack origin separately - do NOT touch r['category']
                        r["source_pack"] = pack["packId"]
                        # Store pack icon for display
                        r["packIcon"] = pack.get("packImage", "📦")
                        # Normalize difficulty if it's a bilingual dict
                        if isinstance(r.get("difficulty"), dict):
                            r["difficulty"] = (
                                r["difficulty"].get("en")
                                or r["difficulty"].get("no")
                                or "Easy"
                            )
                        # Ensure time_minutes is set (may be cookTimeMinutes in pack)
                        if "time_minutes" not in r or not r.get("time_minutes"):
                            r["time_minutes"] = r.get("cookTimeMinutes", 30)
                        # Normalize ingredient units to Norwegian canonical form
                        # (tbsp -> ss, bunch -> bunt, etc; see B15/B20) at import
                        # time, not just via the one-off admin backfill route -
                        # otherwise packs imported after that backfill keep raw
                        # English units forever (B45).
                        from core.ingredient_deduplicator import normalize_no_unit

                        for ing_field in (
                            "ingredients",
                            "ingredients_included",
                            "ingredients_not_included",
                        ):
                            for ing in r.get(ing_field, []) or []:
                                if isinstance(ing, dict) and "unit" in ing:
                                    ing["unit"] = normalize_no_unit(ing["unit"])
                        recipes_to_import.append(r)

            # Load existing recipes database.
            # Upsert: overwrite any recipe whose ID already exists (so re-importing
            # a pack after a category restructure gets the fresh categories, not the
            # stale ones from the previous import).
            existing_recipes = load_recipes_db()
            import_ids = {r["id"] for r in recipes_to_import}
            kept = [r for r in existing_recipes if r["id"] not in import_ids]
            imported_count = len(recipes_to_import)
            existing_recipes = kept + recipes_to_import

            # Save updated database
            save_recipes_db(existing_recipes)

            log_activity(
                f"Imported {imported_count} recipes from {len(pack_ids)} pack(s)"
            )

            # No categories.json bookkeeping needed here anymore - imported recipes
            # keep their own real dish-type category (Chicken, Salads, etc.), which
            # already exists in the household's category list. There's nothing
            # new to register; a recipe is just findable under its existing
            # category right away. Pack display metadata (for "Manage Recipe
            # Packs") is tracked separately instead.
            for pack_id, meta in pack_metadata.items():
                _save_imported_pack_metadata_db(
                    current_household_id(),
                    pack_id,
                    meta["display_name"],
                    meta["icon"],
                    meta["color"],
                )

            logger.info(f"Imported {imported_count} recipes from {len(pack_ids)} packs")
            return jsonify(
                {
                    "success": True,
                    "imported_count": imported_count,
                    "message": f"Imported {imported_count} recipes",
                }
            )

        except Exception as e:
            logger.error(f"Recipe pack import error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/api/recipe-packs/imported", methods=["GET"])
    def api_get_imported_packs():
        """Get list of imported packs, grouped by source_pack (not by category -
        a recipe's category is its own dish-type, e.g. Chicken/Salads, kept
        separate from which pack it came from)."""
        try:
            pack_meta = _load_imported_packs_db(current_household_id())

            recipe_counts = {}
            recipes = load_recipes_db()
            for recipe in recipes:
                pack_id = recipe.get("source_pack", "")
                if pack_id:
                    recipe_counts[pack_id] = recipe_counts.get(pack_id, 0) + 1

            packs = []
            for pack_id, count in recipe_counts.items():
                meta = pack_meta.get(pack_id, {})
                packs.append(
                    {
                        "pack_id": pack_id,
                        "category_name": meta.get("display_name", pack_id),
                        "recipe_count": count,
                        "icon": meta.get("icon", "📦"),
                    }
                )

            return jsonify({"success": True, "packs": packs})
        except Exception as e:
            logger.error(f"Error getting imported packs: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/api/recipe-packs/remove", methods=["POST"])
    def api_remove_imported_pack():
        """Remove an imported pack (all recipes with that source_pack). Does NOT
        touch categories.json - a recipe's dish-type category is its own, not
        tied to which pack it came from, so removing a pack never needs to
        remove a category."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"success": False, "message": "Viewers cannot remove recipe packs"}
                ),
                403,
            )
        try:
            data = request.get_json()
            pack_id = data.get("pack_id", "")

            if not pack_id:
                return jsonify({"success": False, "message": "No pack specified"}), 400

            recipes = load_recipes_db()
            removed_count = 0

            if recipes:
                filtered_recipes = [
                    r for r in recipes if r.get("source_pack", "") != pack_id
                ]
                removed_count = len(recipes) - len(filtered_recipes)

                save_recipes_db(filtered_recipes)

                log_activity(f"Removed pack '{pack_id}' ({removed_count} recipes)")
                _remove_imported_pack_metadata_db(current_household_id(), pack_id)

                logger.info(f"Removed {removed_count} recipes from pack '{pack_id}'")

            return jsonify(
                {
                    "success": True,
                    "removed_count": removed_count,
                    "message": f"Removed {removed_count} recipes",
                }
            )

        except Exception as e:
            logger.error(f"Recipe pack removal error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/recipe-packs/manage")
    def manage_recipe_packs():
        """Page to manage imported recipe packs"""
        lang = _get_lang()
        recipes = [_normalize_recipe(r, lang) for r in load_recipes_db()]
        return render_template("recipe-packs-manage.html", recipes=recipes)

    # ── Hidden feature foundation: dessert/drinks browsing (F2), side stash (F8) ─
    # Gated behind FEATURE_FLAGS (see the block right after IS_PRODUCTION, and
    # docs/FEATURE_FLAGS.md). Every route below 404s outright when its flag is
    # off, so the public build behaves exactly as if these routes don't exist -
    # this is deliberate over hiding a nav link, since a stray direct URL guess
    # shouldn't reveal in-progress functionality either. Data loading lives in
    # core/stash_library.py, kept isolated from the recipe-pack/menu code so
    # this can be reshaped later without touching anything public-facing.

    @bp.route("/desserts-drinks")
    def desserts_drinks_page():
        """Hidden dev-only browser for the dessert + drinks stash (F2 foundation)."""
        if not feature_enabled("desserts_drinks"):
            abort(404)
        from core.stash_library import load_dessert_stash, load_drinks_stash

        lang = _get_lang()
        desserts = [_normalize_recipe(r, lang) for r in load_dessert_stash()]
        drinks = [_normalize_recipe(r, lang) for r in load_drinks_stash()]
        return render_template("desserts-drinks.html", desserts=desserts, drinks=drinks)

    @bp.route("/api/desserts-drinks/list")
    def api_desserts_drinks_list():
        if not feature_enabled("desserts_drinks"):
            abort(404)
        from core.stash_library import load_dessert_stash, load_drinks_stash

        lang = _get_lang()
        return jsonify(
            {
                "desserts": [_normalize_recipe(r, lang) for r in load_dessert_stash()],
                "drinks": [_normalize_recipe(r, lang) for r in load_drinks_stash()],
            }
        )

    @bp.route("/sides-stash")
    def sides_stash_page():
        """Hidden dev-only browser for the side-dish stash (F8 foundation)."""
        if not feature_enabled("side_stash"):
            abort(404)
        from core.stash_library import load_sides_stash

        lang = _get_lang()
        sides = [_normalize_recipe(r, lang) for r in load_sides_stash()]
        return render_template("sides-stash.html", sides=sides)

    @bp.route("/api/sides-stash/list")
    def api_sides_stash_list():
        if not feature_enabled("side_stash"):
            abort(404)
        from core.stash_library import load_sides_stash

        lang = _get_lang()
        return jsonify(
            {"sides": [_normalize_recipe(r, lang) for r in load_sides_stash()]}
        )
