"""
Recipe CRUD and lookup routes (B57, audit 2026-07-07): recipe detail/edit
pages, the add/delete/edit/search/export/import API. Moved out of the
former single flask_app.py verbatim - route bodies are unchanged. None of
these routes are referenced via url_for() anywhere (recipe URLs are built
as raw JS template strings client-side, and the API routes are called as
fetch() paths).
"""

import json
from pathlib import Path

from flask import render_template, jsonify, request

from deployment.app_core import (
    logger,
    CACHE_DIR,
    SEED_DIR,
    _get_lang,
    _normalize_recipe,
    _normalize_difficulty,
    find_recipe,
    load_recipes_db,
    save_recipes_db,
    load_menu,
    save_menu,
    log_activity,
    acting_role_can_edit,
)


def register(bp):
    @bp.route("/recipe/<recipe_id>")
    def recipe_detail(recipe_id):
        recipe = None
        recipe_dir = CACHE_DIR / recipe_id

        if recipe_dir.exists():
            metadata_file = recipe_dir / "metadata.json"
            if metadata_file.exists():
                try:
                    with open(metadata_file, "r", encoding="utf-8") as f:
                        recipe = json.load(f)
                except Exception as e:
                    logger.error(f"Failed to load metadata: {e}")

        if not recipe:
            recipe = find_recipe(recipe_id)

        if not recipe:
            return (
                render_template("error.html", message=f"Recipe not found: {recipe_id}"),
                404,
            )

        lang = _get_lang()
        recipe = _normalize_recipe(recipe, lang)
        logger.info(f"Recipe detail accessed: {recipe_id}")
        return render_template("recipe.html", recipe=recipe)

    @bp.route("/edit-recipe/<recipe_id>")
    def edit_recipe(recipe_id):
        recipe = find_recipe(recipe_id)
        if not recipe:
            return (
                render_template("error.html", message=f"Recipe not found: {recipe_id}"),
                404,
            )

        lang = _get_lang()
        recipe = _normalize_recipe(recipe, lang)

        # Format ingredients as one readable line per ingredient, using the same
        # "name, quantity, unit" format documented in the Add/Edit Recipe hint
        # text (see B39) - so re-saving without touching a line round-trips
        # correctly instead of silently losing quantity/unit on every edit.
        ingredients_list = recipe.get(
            "ingredients_included", recipe.get("ingredients", [])
        )
        ingredient_lines = []
        for ing in ingredients_list:
            if isinstance(ing, dict):
                qty = ing.get("quantity", "")
                unit = ing.get("unit", "")
                name = ing.get("name", "")
                if qty or unit:
                    ingredient_lines.append(
                        ", ".join(str(p) for p in (name, qty, unit) if p)
                    )
                else:
                    ingredient_lines.append(name)
            else:
                ingredient_lines.append(str(ing))
        ingredients_text = "\n".join(ingredient_lines)

        # Format instructions - _normalize_recipe() above already flattened these
        # to a list of {'step': N, 'description': '...'} dicts, so pull out the
        # plain text rather than str()-ing the dicts themselves (which used to
        # dump raw Python dict literals like "{'step': 1, 'description': '...'}"
        # straight into the textarea).
        instructions = recipe.get("instructions", [])
        lines = []
        for i, step in enumerate(instructions):
            if isinstance(step, dict):
                lines.append(str(step.get("description", "")))
            else:
                lines.append(str(step))
        instructions_text = "\n".join(lines)

        logger.info(f"Edit recipe page accessed: {recipe_id}")
        return render_template(
            "edit_recipe.html",
            recipe=recipe,
            ingredients_text=ingredients_text,
            instructions_text=instructions_text,
        )

    @bp.route("/api/add-recipe", methods=["POST"])
    def api_add_recipe():
        """Add a manually created recipe to recipes_db.json and backup the form"""
        if not acting_role_can_edit():
            return (
                jsonify({"status": "error", "message": "Viewers cannot add recipes"}),
                403,
            )
        try:
            import uuid

            data = request.get_json() or {}

            recipe = {
                "id": str(uuid.uuid4())[:8],
                "title": data.get("title", ""),
                "description": data.get("description", ""),
                "difficulty": _normalize_difficulty(data.get("difficulty", "Easy")),
                "time_minutes": data.get("time_minutes", 30),
                "category": data.get("category", "HomeMade"),
                "ingredients": data.get("ingredients", []),
                "instructions": data.get("instructions", []),
                "comment": data.get("comment", ""),
                "source": "manual",
            }

            if not recipe["title"] or not recipe["ingredients"]:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Title and ingredients are required",
                        }
                    ),
                    400,
                )

            # Backup the form submission
            backup_dir = Path("data/sendt_forms")
            backup_dir.mkdir(parents=True, exist_ok=True)
            safe_title = (
                recipe["title"].replace(" ", "_").replace("/", "_").replace("\\", "_")
            )
            backup_file = backup_dir / f"form_{safe_title}.json"
            with open(backup_file, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Backed up form to: {backup_file}")

            # Save to recipes database
            recipes = load_recipes_db()
            recipes.append(recipe)
            save_recipes_db(recipes)

            log_activity(f"Added recipe '{recipe['title']}'")

            logger.info(f"Added recipe: {recipe['title']} (ID: {recipe['id']})")
            return jsonify(
                {
                    "status": "success",
                    "message": f"✅ {recipe['title']} saved!",
                    "recipe_id": recipe["id"],
                }
            )

        except Exception as e:
            logger.error(f"Error adding recipe: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/delete-recipe", methods=["POST"])
    def api_delete_recipe():
        """Delete a recipe from recipes_db.json by ID."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"status": "error", "message": "Viewers cannot delete recipes"}
                ),
                403,
            )
        try:
            data = request.get_json() or {}
            recipe_id = data.get("recipe_id")
            if not recipe_id:
                return (
                    jsonify({"status": "error", "message": "recipe_id is required"}),
                    400,
                )

            recipes = load_recipes_db()
            original_count = len(recipes)
            recipes = [r for r in recipes if r.get("id") != recipe_id]

            if len(recipes) == original_count:
                return (
                    jsonify(
                        {"status": "error", "message": f"Recipe {recipe_id} not found"}
                    ),
                    404,
                )

            save_recipes_db(recipes)

            # B36: deleting a recipe that's still on the current weekly menu used
            # to leave the day pointing at a now-missing recipe_id - the
            # dashboard kept showing its stale title/time/difficulty, and
            # clicking into it 404'd ("Recipe not found"). Clear any day that
            # referenced this recipe so it shows as an empty slot instead of a
            # dangling reference.
            menu = load_menu()
            if menu and menu.get("dinners"):
                menu_changed = False
                for dinner in menu["dinners"]:
                    if dinner.get("recipe_id") == recipe_id:
                        dinner["recipe_id"] = ""
                        dinner["title"] = ""
                        dinner["title_no"] = ""
                        dinner["title_en"] = ""
                        dinner["subtitle"] = ""
                        dinner["subtitle_no"] = ""
                        dinner["subtitle_en"] = ""
                        dinner["image_url"] = ""
                        dinner["protein"] = ""
                        dinner["difficulty"] = ""
                        # Keep this numeric (not '') - index.html's weekly-summary
                        # widget does `menu.dinners | sum(attribute='time_minutes')`,
                        # which throws if any entry is a string instead of a number.
                        dinner["time_minutes"] = 0
                        menu_changed = True
                if menu_changed:
                    save_menu(menu)

            log_activity(f"Deleted recipe '{recipe_id}'")

            logger.info(f"Deleted recipe: {recipe_id}")
            return jsonify(
                {"status": "success", "message": f"Recipe {recipe_id} deleted"}
            )
        except Exception as e:
            logger.error(f"Delete recipe error: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/edit-recipe", methods=["POST"])
    def api_edit_recipe():
        """Edit an existing recipe in recipes_db.json by ID"""
        if not acting_role_can_edit():
            return (
                jsonify({"status": "error", "message": "Viewers cannot edit recipes"}),
                403,
            )
        try:
            data = request.get_json() or {}
            recipe_id = data.get("recipe_id")

            if not recipe_id:
                return (
                    jsonify({"status": "error", "message": "recipe_id is required"}),
                    400,
                )

            # Validate required fields
            title = data.get("title", "").strip()
            ingredients = data.get("ingredients", [])

            if not title or not ingredients:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "Title and ingredients are required",
                        }
                    ),
                    400,
                )

            recipes = load_recipes_db()
            recipe_found = False

            # Find and update the recipe
            for i, recipe in enumerate(recipes):
                if recipe.get("id") == recipe_id:
                    # Update all provided fields
                    recipes[i]["title"] = title
                    recipes[i]["description"] = data.get("description", "")
                    recipes[i]["difficulty"] = _normalize_difficulty(
                        data.get("difficulty", "Easy")
                    )
                    recipes[i]["time_minutes"] = data.get("time_minutes", 30)
                    recipes[i]["category"] = data.get(
                        "category", recipe.get("category", "HomeMade")
                    )
                    recipes[i]["ingredients"] = ingredients
                    recipes[i]["instructions"] = data.get("instructions", [])
                    recipes[i]["comment"] = data.get("comment", "")
                    recipe_found = True
                    break

            if not recipe_found:
                return (
                    jsonify(
                        {"status": "error", "message": f"Recipe {recipe_id} not found"}
                    ),
                    404,
                )

            # Save updated recipes
            save_recipes_db(recipes)

            log_activity(f"Edited recipe '{title}'")

            logger.info(f"Updated recipe: {title} (ID: {recipe_id})")
            return jsonify(
                {
                    "status": "success",
                    "message": f"✅ {title} updated!",
                    "recipe_id": recipe_id,
                }
            )

        except Exception as e:
            logger.error(f"Error editing recipe: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/recipes/search")
    def api_recipes_search():
        """Search this household's recipe library by title, for the "search and
        pick a specific recipe for this day" dashboard control (B/feature request
        from user testing, 2026-07). Returns a small flat list (id/title/category/
        time) rather than full recipe records - this feeds a search dropdown, not
        a detail view, so keep the payload light."""
        query = (request.args.get("q") or "").strip().lower()
        if len(query) < 2:
            return jsonify({"status": "success", "recipes": []})

        all_recipes = load_recipes_db()
        sample_path = SEED_DIR / "sample_recipes.json"
        if sample_path.exists():
            try:
                with open(sample_path, "r", encoding="utf-8") as f:
                    all_recipes = all_recipes + json.load(f)
            except Exception:
                pass

        seen_ids = set()
        results = []
        for recipe in all_recipes:
            recipe_id = recipe.get("id")
            if not recipe_id or recipe_id in seen_ids:
                continue
            title = recipe.get("title")
            if isinstance(title, dict):
                title_en = title.get("en", "")
                title_no = title.get("no", "")
            else:
                title_en = recipe.get("title_en", title or "")
                title_no = recipe.get("title_no", title or "")
            haystack = f"{title_en} {title_no}".strip().lower()
            if query not in haystack:
                continue
            seen_ids.add(recipe_id)
            results.append(
                {
                    "id": recipe_id,
                    "title_en": title_en,
                    "title_no": title_no,
                    "category": recipe.get("category", ""),
                    "time_minutes": recipe.get("time_minutes")
                    or recipe.get("cookTimeMinutes")
                    or 0,
                }
            )
            if len(results) >= 25:
                break

        return jsonify({"status": "success", "recipes": results})

    @bp.route("/api/recipes/export")
    def api_recipes_export():
        """Export all user recipes as JSON"""
        try:
            recipes = load_recipes_db()
            return jsonify({"success": True, "recipes": recipes, "count": len(recipes)})
        except Exception as e:
            logger.error(f"Export error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500

    @bp.route("/api/recipes/import", methods=["POST"])
    def api_recipes_import():
        """Import recipes from user-provided JSON file"""
        if not acting_role_can_edit():
            return (
                jsonify({"success": False, "message": "Viewers cannot import recipes"}),
                403,
            )
        try:
            data = request.get_json()
            recipes_to_import = data.get("recipes", [])

            if not recipes_to_import:
                return (
                    jsonify({"success": False, "message": "No recipes provided"}),
                    400,
                )

            # Validate recipe structure
            for recipe in recipes_to_import:
                if not recipe.get("id") or not recipe.get("title"):
                    return (
                        jsonify(
                            {"success": False, "message": "Invalid recipe structure"}
                        ),
                        400,
                    )

            # Load existing recipes
            existing_recipes = load_recipes_db()
            existing_ids = {r["id"] for r in existing_recipes}

            # Import non-duplicate recipes
            imported_count = 0
            for recipe in recipes_to_import:
                if recipe["id"] not in existing_ids:
                    existing_recipes.append(recipe)
                    imported_count += 1

            # Save updated database
            save_recipes_db(existing_recipes)

            log_activity(f"Imported {imported_count} recipes from file")

            logger.info(f"Imported {imported_count} recipes from user file")
            return jsonify(
                {
                    "success": True,
                    "imported_count": imported_count,
                    "message": f"Imported {imported_count} recipes",
                }
            )

        except Exception as e:
            logger.error(f"Recipe import error: {e}")
            return jsonify({"success": False, "message": str(e)}), 500
