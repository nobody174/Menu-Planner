"""
Weekly menu mutation routes (B57, audit 2026-07-07): fetching the current
menu, regenerating it from scratch, swapping a recipe to a different day,
and rerolling a single day's recipe. Moved out of the former single
flask_app.py verbatim - route bodies are unchanged.

This is the app's highest-risk mutation surface historically - B53's silent
shortfall bug, B63's SQLite concurrency corruption, and the swap-day
flag_modified() bug all lived here, which is why every write goes through
locked_household()'s row lock rather than a separate read/write session
pair. None of these routes are referenced via url_for() anywhere (the
frontend calls them as fetch() paths).
"""

import json

from flask import jsonify, request

from deployment.app_core import (
    logger,
    SEED_DIR,
    _DAY_TRANSLATIONS,
    _get_lang,
    _make_t,
    _resolve,
    _normalize_difficulty,
    current_household_id,
    acting_role_can_edit,
    locked_household,
    current_actor_name,
    format_minutes,
    load_menu,
    load_recipes_db,
    find_recipe,
)


def register(bp):
    @bp.route("/api/menu")
    def api_menu():
        menu = load_menu()
        if not menu:
            return jsonify({"error": "No menu generated yet"}), 404
        lang = _get_lang()
        day_map = _DAY_TRANSLATIONS.get(lang, {})
        import copy

        menu = copy.deepcopy(menu)
        for dinner in menu.get("dinners", []):
            if dinner.get("day") in day_map:
                dinner["day"] = day_map[dinner["day"]]
            # Always resolve the title to a plain string for this language -
            # titles are stored as bilingual {'en':..., 'no':...} dicts, and
            # skipping this (previously only done when a day_map existed, i.e.
            # Norwegian) left the raw dict in place for English, which the
            # sidebar JS then stringified as "[object Object]".
            dinner["title"] = _resolve(dinner.get("title"), lang)
            # Same stale-"0 MIN" self-heal as the dashboard route.
            if not dinner.get("time_minutes"):
                source_recipe = find_recipe(dinner.get("recipe_id"))
                if source_recipe:
                    dinner["time_minutes"] = (
                        source_recipe.get("time_minutes")
                        or source_recipe.get("cookTimeMinutes")
                        or 0
                    )
        logger.info("API menu endpoint accessed")
        return jsonify(menu)

    @bp.route("/api/regenerate", methods=["POST"])
    def api_regenerate():
        """Build a fresh weekly menu from the selected categories/favorites and
        save it, replacing whatever menu existed before.

        The save happens inside locked_household() (row-locked via
        SELECT ... FOR UPDATE) rather than through MenuGenerator's own separate
        save session, so a regenerate can't land in between a concurrent
        swap-recipe's read and write and get silently overwritten (or overwrite
        it) - both now go through the same lock on this household's row."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"status": "error", "message": "Viewers cannot regenerate the menu"}
                ),
                403,
            )

        try:
            from core.menu_generator import MenuGenerator

            data = request.get_json() or {}
            selected_categories = (
                data.get("categories")
                or data.get("selected_categories")
                or ["Quick Dinners", "Fish & Seafood", "Vegetarian"]
            )
            favorite_recipe_ids = data.get("favorite_recipe_ids", [])
            try:
                num_dinners = int(data.get("num_dinners", 6))
            except (TypeError, ValueError):
                num_dinners = 6
            num_dinners = max(1, min(6, num_dinners))
            logger.info(
                f"Generating menu with categories: {selected_categories}, favorites: {len(favorite_recipe_ids)}, num_dinners: {num_dinners}"
            )
            generator = MenuGenerator(
                selected_categories=selected_categories,
                household_id=current_household_id(),
                favorite_recipe_ids=favorite_recipe_ids,
            )
            # save=False: persistence now happens below, inside locked_household(),
            # instead of through the generator's own separate save session.
            menu = generator.run(num_dinners=num_dinners, save=False)

            if not menu or not menu.get("dinners"):
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "No recipes available for selected categories. Please select different categories or add recipes.",
                        }
                    ),
                    400,
                )

            # B61 (2026-07-09): the file-fallback branch has been removed -
            # confirmed via Neon that exactly 3 households exist and all are
            # real DB rows, and this Render service has no persistent Disk
            # attached, so a file-only household could not have survived any
            # deploy to exist today.
            with locked_household() as (db, household):
                if household:
                    from core.household_paths import (
                        save_weekly_menu_to_db,
                        append_activity_to_db,
                    )

                    save_weekly_menu_to_db(household, menu)
                    append_activity_to_db(
                        household, current_actor_name(), "Regenerated the weekly menu"
                    )

            logger.info("Menu regenerated via API")
            response = {"status": "success", "menu": menu}
            actual_dinners = len(menu.get("dinners", []))
            requested_dinners = menu.get("requested_dinners", actual_dinners)
            if actual_dinners < requested_dinners:
                # Structured, not a pre-built sentence, so the frontend can
                # localize it (see generate_shortfall_msg_no/en in i18n.json).
                response["warning"] = {
                    "actual_dinners": actual_dinners,
                    "requested_dinners": requested_dinners,
                }
            return jsonify(response)
        except Exception as e:
            import traceback

            logger.error(f"Menu regeneration failed: {e}")
            logger.error(traceback.format_exc())
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/swap-recipe", methods=["POST"])
    def api_swap_recipe():
        """Move a recipe to a chosen weekday in the current menu.

        If the recipe is already planned for a different day this week, the two
        days trade places entirely (a true swap - nothing is lost or
        duplicated). If the recipe isn't currently in this week's menu at all
        (e.g. picking a brand-new recipe from the catalog), it's simply inserted
        into the target day, replacing whatever was already planned there.

        Read + mutate + save all happen inside one locked_household() session
        (row-locked via SELECT ... FOR UPDATE) rather than a separate read
        session followed by a separate write session - the old pattern had a
        real read-modify-write race window between the two, where a concurrent
        request touching the same household could silently lose this swap on
        save."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"status": "error", "message": "Viewers cannot change the menu"}
                ),
                403,
            )
        try:
            data = request.get_json() or {}
            recipe_id = data.get("recipe_id")
            day = data.get("day")

            if not recipe_id or not day:
                return (
                    jsonify(
                        {"status": "error", "message": "Recipe ID and day required"}
                    ),
                    400,
                )

            # B61 (2026-07-09): the file-fallback branch has been removed,
            # same reasoning as the /api/regenerate route above.
            with locked_household() as (db, household):
                if household:
                    from core.household_paths import (
                        load_weekly_menu_from_db,
                        save_weekly_menu_to_db,
                        append_activity_to_db,
                    )

                    menu = load_weekly_menu_from_db(household)
                else:
                    menu = None

                if not menu:
                    return (
                        jsonify(
                            {"status": "error", "message": "No menu generated yet"}
                        ),
                        404,
                    )

                dinners = menu.get("dinners", [])
                target = next((d for d in dinners if d["day"] == day), None)
                if not target:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": f"Day {day} not found in menu",
                            }
                        ),
                        404,
                    )

                source = next(
                    (
                        d
                        for d in dinners
                        if d.get("recipe_id") == recipe_id and d is not target
                    ),
                    None,
                )
                swapped_with_day = None

                if source:
                    # True swap - exchange everything except the 'day' field itself.
                    source_day, target_day = source["day"], target["day"]
                    source_copy, target_copy = dict(source), dict(target)
                    source.clear()
                    source.update(target_copy)
                    source["day"] = source_day
                    target.clear()
                    target.update(source_copy)
                    target["day"] = target_day
                    swapped_with_day = source_day
                    # Resolve to a plain string for the activity log - target['title']
                    # can still be the raw bilingual {'en':..., 'no':...} dict after
                    # the swap above, which previously got embedded into the log
                    # message as Python's dict repr (e.g. "{'no': '...', 'en': '...'}")
                    # instead of the actual recipe name.
                    _swap_title = target.get("title")
                    recipe_title = (
                        target.get("title_en")
                        or target.get("title_no")
                        or (_swap_title if isinstance(_swap_title, str) else "")
                        or "Recipe"
                    )
                else:
                    recipe = find_recipe(recipe_id)
                    if not recipe:
                        return (
                            jsonify({"status": "error", "message": "Recipe not found"}),
                            404,
                        )

                    # Mirror MenuGenerator.generate_menu()'s field derivation exactly -
                    # this used to only set recipe_id/title/time_minutes/difficulty,
                    # leaving title_no/title_en/subtitle_no/subtitle_en/protein/
                    # image_url stale from whatever recipe used to be on this day.
                    # The dashboard prefers title_en/title_no over the raw 'title'
                    # field when resolving what to display, so it kept silently
                    # showing the OLD recipe's name even though the swap "worked".
                    from core.menu_generator import MenuGenerator, PROTEIN_IMAGES

                    title = recipe.get("title")
                    if isinstance(title, dict):
                        title_en = title.get("en", "")
                        title_no = title.get("no", "")
                    else:
                        title_en = recipe.get("title_en", title or "")
                        title_no = recipe.get("title_no", title or "")

                    subtitle = recipe.get("subtitle")
                    if isinstance(subtitle, dict):
                        subtitle_en = subtitle.get("en", "")
                        subtitle_no = subtitle.get("no", "")
                    else:
                        subtitle_en = recipe.get("subtitle_en", subtitle or "")
                        subtitle_no = recipe.get("subtitle_no", subtitle or "")

                    protein_type = MenuGenerator().get_protein_type(
                        title_en or title_no or "",
                        subtitle_en or subtitle_no or "",
                        recipe.get("category", ""),
                    )

                    target["recipe_id"] = recipe["id"]
                    target["title"] = recipe["title"]
                    target["title_no"] = title_no
                    target["title_en"] = title_en
                    target["time_minutes"] = (
                        recipe.get("time_minutes") or recipe.get("cookTimeMinutes") or 0
                    )
                    target["difficulty"] = recipe.get("difficulty", "")
                    target["protein"] = protein_type
                    target["subtitle_no"] = subtitle_no
                    target["subtitle_en"] = subtitle_en
                    target["image_url"] = PROTEIN_IMAGES.get(
                        protein_type, PROTEIN_IMAGES.get("vegetarian")
                    )
                    recipe_title = title_en or title_no or "Recipe"

                activity_msg = (
                    f"Swapped {day} and {swapped_with_day}"
                    if swapped_with_day
                    else f"Swapped {day}'s dinner to '{recipe_title}'"
                )

                # Save the updated menu. Menus live in the household's DB row.
                # B61 (2026-07-09): the file-fallback branch has been removed -
                # confirmed via Neon that exactly 3 households exist and all
                # are real DB rows, and this Render service has no persistent
                # Disk attached, so a file-only household could not have
                # survived any deploy to exist today.
                if household:
                    save_weekly_menu_to_db(household, menu)
                    append_activity_to_db(household, current_actor_name(), activity_msg)

            logger.info(activity_msg)

            # Same reasoning as /api/reroll-recipe: return everything the
            # affected card(s) need to update in place client-side, instead of
            # forcing a full page reload that can cancel another in-flight
            # request (a second click on a different day's action before this
            # one's reload fires).
            lang = _get_lang()
            t_dict = _make_t(lang)
            diff_map = {
                "Easy": t_dict.get("easy", "Easy"),
                "Medium": t_dict.get("medium", "Medium"),
                "Hard": t_dict.get("hard", "Hard"),
            }

            def _card_payload(dinner):
                d_normalized = _normalize_difficulty(dinner.get("difficulty", ""))
                time_minutes = dinner.get("time_minutes", 0)
                title_en_ = dinner.get("title_en", "")
                title_no_ = dinner.get("title_no", "")
                subtitle_en_ = dinner.get("subtitle_en", "")
                subtitle_no_ = dinner.get("subtitle_no", "")
                return {
                    "day": dinner.get("day"),
                    "recipe_id": dinner.get("recipe_id"),
                    "title": title_no_ if lang == "no" else title_en_,
                    "subtitle": subtitle_no_ if lang == "no" else subtitle_en_,
                    "time_minutes": time_minutes,
                    "time_display": format_minutes(time_minutes),
                    "difficulty_level": d_normalized.lower(),
                    "difficulty": diff_map.get(d_normalized, d_normalized),
                    "protein": dinner.get("protein", ""),
                    "image_url": dinner.get("image_url", ""),
                }

            cards = [_card_payload(target)]
            if swapped_with_day:
                cards.append(_card_payload(source))

            return jsonify(
                {
                    "status": "success",
                    "message": activity_msg,
                    "swapped_with_day": swapped_with_day,
                    "cards": cards,
                }
            )

        except Exception as e:
            logger.error(f"Error swapping recipe: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500

    @bp.route("/api/reroll-recipe", methods=["POST"])
    def api_reroll_recipe():
        """Replace a single day's recipe with a different random one, without
        touching the rest of the week (B/feature request from user testing,
        2026-07: "just wanna reroll that 1 menu" instead of regenerating all 6).

        Stays within the current recipe's own category where possible (so a
        reroll on a "Fish & Seafood" day doesn't suddenly hand back a dessert),
        and never picks a recipe already used elsewhere in this week's menu -
        same no-duplicates guarantee MenuGenerator gives a fresh menu."""
        if not acting_role_can_edit():
            return (
                jsonify(
                    {"status": "error", "message": "Viewers cannot change the menu"}
                ),
                403,
            )
        try:
            import random

            data = request.get_json() or {}
            day = data.get("day")
            if not day:
                return jsonify({"status": "error", "message": "Day required"}), 400

            # B61 (2026-07-09): the file-fallback branch has been removed,
            # same reasoning as /api/swap-recipe above.
            with locked_household() as (db, household):
                if household:
                    from core.household_paths import (
                        load_weekly_menu_from_db,
                        save_weekly_menu_to_db,
                        append_activity_to_db,
                    )

                    menu = load_weekly_menu_from_db(household)
                else:
                    menu = None

                if not menu:
                    return (
                        jsonify(
                            {"status": "error", "message": "No menu generated yet"}
                        ),
                        404,
                    )

                dinners = menu.get("dinners", [])
                target = next((d for d in dinners if d["day"] == day), None)
                if not target:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": f"Day {day} not found in menu",
                            }
                        ),
                        404,
                    )

                used_recipe_ids = {
                    d.get("recipe_id") for d in dinners if d.get("recipe_id")
                }

                current_recipe = find_recipe(target.get("recipe_id"))
                current_category = (
                    current_recipe.get("category", "") if current_recipe else ""
                )

                all_recipes = load_recipes_db()
                sample_path = SEED_DIR / "sample_recipes.json"
                if sample_path.exists():
                    try:
                        with open(sample_path, "r", encoding="utf-8") as f:
                            all_recipes = all_recipes + json.load(f)
                    except Exception:
                        pass

                # Prefer same-category candidates; if none are left (small/edge-
                # case libraries), fall back to any unused recipe at all rather
                # than failing outright.
                candidates = [
                    r
                    for r in all_recipes
                    if r.get("id") not in used_recipe_ids
                    and (
                        not current_category
                        or r.get("category", "") == current_category
                    )
                ]
                if not candidates:
                    candidates = [
                        r for r in all_recipes if r.get("id") not in used_recipe_ids
                    ]
                if not candidates:
                    return (
                        jsonify(
                            {
                                "status": "error",
                                "message": "No other recipes available to reroll to",
                            }
                        ),
                        404,
                    )

                new_recipe = random.choice(candidates)

                from core.menu_generator import MenuGenerator, PROTEIN_IMAGES

                title = new_recipe.get("title")
                if isinstance(title, dict):
                    title_en = title.get("en", "")
                    title_no = title.get("no", "")
                else:
                    title_en = new_recipe.get("title_en", title or "")
                    title_no = new_recipe.get("title_no", title or "")

                subtitle = new_recipe.get("subtitle")
                if isinstance(subtitle, dict):
                    subtitle_en = subtitle.get("en", "")
                    subtitle_no = subtitle.get("no", "")
                else:
                    subtitle_en = new_recipe.get("subtitle_en", subtitle or "")
                    subtitle_no = new_recipe.get("subtitle_no", subtitle or "")

                protein_type = MenuGenerator().get_protein_type(
                    title_en or title_no or "",
                    subtitle_en or subtitle_no or "",
                    new_recipe.get("category", ""),
                )

                target["recipe_id"] = new_recipe["id"]
                target["title"] = new_recipe.get("title")
                target["title_no"] = title_no
                target["title_en"] = title_en
                target["time_minutes"] = (
                    new_recipe.get("time_minutes")
                    or new_recipe.get("cookTimeMinutes")
                    or 0
                )
                target["difficulty"] = new_recipe.get("difficulty", "")
                target["protein"] = protein_type
                target["subtitle_no"] = subtitle_no
                target["subtitle_en"] = subtitle_en
                target["image_url"] = PROTEIN_IMAGES.get(
                    protein_type, PROTEIN_IMAGES.get("vegetarian")
                )

                recipe_title = title_en or title_no or "Recipe"
                activity_msg = f"Rerolled {day}'s dinner to '{recipe_title}'"

                if household:
                    save_weekly_menu_to_db(household, menu)
                    append_activity_to_db(household, current_actor_name(), activity_msg)

            logger.info(activity_msg)

            # Return every field the card needs to update itself in place
            # client-side, matching what a full dashboard reload would show -
            # avoids a page reload on every reroll, which used to race with a
            # second in-flight click (a reload cancels other pending requests
            # mid-flight, which could surface as a misleading CSRF error and
            # leave that day's reroll button stuck disabled).
            lang = _get_lang()
            t_dict = _make_t(lang)
            diff_map = {
                "Easy": t_dict.get("easy", "Easy"),
                "Medium": t_dict.get("medium", "Medium"),
                "Hard": t_dict.get("hard", "Hard"),
            }
            d_normalized = _normalize_difficulty(new_recipe.get("difficulty", ""))
            time_minutes = target["time_minutes"]

            return jsonify(
                {
                    "status": "success",
                    "message": activity_msg,
                    "recipe_id": new_recipe["id"],
                    "title_en": title_en,
                    "title_no": title_no,
                    "title": title_no if lang == "no" else title_en,
                    "subtitle_en": subtitle_en,
                    "subtitle_no": subtitle_no,
                    "subtitle": subtitle_no if lang == "no" else subtitle_en,
                    "time_minutes": time_minutes,
                    "time_display": format_minutes(time_minutes),
                    "difficulty_level": d_normalized.lower(),
                    "difficulty": diff_map.get(d_normalized, d_normalized),
                    "protein": protein_type,
                    "image_url": target["image_url"],
                }
            )

        except Exception as e:
            logger.error(f"Error rerolling recipe: {e}")
            return jsonify({"status": "error", "message": str(e)}), 500
