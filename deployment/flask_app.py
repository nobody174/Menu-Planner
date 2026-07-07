#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

"""
Route handlers for the Menu Planner app (B57, audit 2026-07-07).

All app initialization (the Flask app itself, CSRF, rate limiting, security
headers, the shared context processor, i18n, session/household resolution,
menu/recipe/pantry load-save helpers, email senders) lives in app_core.py's
create_app() factory - this module just builds the app via that factory and
defines every route against it. Route bodies are unchanged from before this
split; only where they live moved.
"""

import json
from pathlib import Path

from flask import (
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
    abort,
    g,
)
from datetime import datetime

from deployment.app_core import (
    create_app,
    logger,
    SEED_DIR,
    DATA_DIR,
    CACHE_DIR,
    CERT_FILE,
    KEY_FILE,
    IS_PRODUCTION,
    FEATURE_FLAGS,
    ADMIN_EMAIL,
    MAX_PROFILES_PER_HOUSEHOLD,
    AVATAR_EMOJI_CHOICES,
    PROFILE_COOKIE_MAX_AGE,
    _DAY_TRANSLATIONS,
    _get_lang,
    _make_t,
    _resolve,
    _translate_category_name,
    _translate_allergen,
    _strip_step_prefix,
    _normalize_difficulty,
    _normalize_recipe,
    _send_confirmation_email,
    _send_password_reset_email,
    _notify_admin_of_feedback,
    _avatar_color,
    _avatar_display,
    feature_enabled,
    format_minutes,
    current_household_id,
    current_household,
    locked_household,
    log_activity,
    _load_pantry_db,
    _save_pantry_db,
    current_actor_name,
    acting_role_is_owner,
    acting_role_can_edit,
    _is_admin,
    load_menu,
    save_menu,
    load_recipes_db,
    save_recipes_db,
    find_recipe,
    _load_household_categories,
    _sort_categories,
)

app = create_app()
csrf = app.extensions["csrf"]
limiter = app.extensions["limiter"]


@app.route("/")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("auth.welcome"))

    menu = load_menu()
    if not menu:
        # This isn't a real error - it's simply what a brand-new household's
        # very first visit looks like, before they've generated their first
        # menu. Rendering the generic "Oops!" error page here (as if
        # something had gone wrong) was a rough first impression for every
        # new household. Show a friendly welcome + a direct "Generate Menu"
        # button instead - no HTTP error status either, since nothing failed.
        return render_template("empty_dashboard.html")
    lang = _get_lang()
    # Translate day names, difficulty, and categories for the current language
    day_map = _DAY_TRANSLATIONS.get(lang, {})
    t_dict = _make_t(lang)
    diff_map = {
        "Easy": t_dict.get("easy", "Easy"),
        "Medium": t_dict.get("medium", "Medium"),
        "Hard": t_dict.get("hard", "Hard"),
    }
    import copy

    menu = copy.deepcopy(menu)
    # Translate categories - uses the shared _translate_category_name() helper
    # (backed by data/categories.json) instead of a hand-maintained dict, so
    # every built-in category translates correctly, not just the ones
    # someone remembered to list here (this previously missed Pork, Beef &
    # Red Meat, and Light Meals entirely - B46).
    if menu.get("selected_categories"):
        menu["selected_categories"] = [
            _translate_category_name(c, lang) for c in menu["selected_categories"]
        ]
    for dinner in menu.get("dinners", []):
        if dinner.get("day") in day_map:
            dinner["day"] = day_map[dinner["day"]]
        # Always normalize & translate difficulty
        d = dinner.get("difficulty", "")
        d_normalized = _normalize_difficulty(d)
        # Keep the normalized (English, lowercase) level around separately for
        # the difficulty color-dot indicator, since dinner['difficulty'] below
        # gets overwritten with the translated display string.
        dinner["difficulty_level"] = d_normalized.lower()
        dinner["difficulty"] = diff_map.get(d_normalized, d_normalized)
        # Resolve title to correct language (use _no/_en fields from menu JSON)
        dinner["title"] = (
            dinner.get(f"title_{lang}")
            or dinner.get("title_en")
            or dinner.get("title")
            or ""
        )
        # Also resolve subtitle if available
        if f"subtitle_{lang}" in dinner or "subtitle_en" in dinner:
            dinner["subtitle"] = (
                dinner.get(f"subtitle_{lang}")
                or dinner.get("subtitle_en")
                or dinner.get("subtitle")
                or ""
            )
        # Self-heal stale "0 MIN" entries saved before recipes consistently
        # carried a time_minutes field (some pack recipes only ever had
        # cookTimeMinutes) - look the recipe back up rather than leaving a
        # 0 baked into the saved menu forever.
        if not dinner.get("time_minutes"):
            source_recipe = find_recipe(dinner.get("recipe_id"))
            if source_recipe:
                dinner["time_minutes"] = (
                    source_recipe.get("time_minutes")
                    or source_recipe.get("cookTimeMinutes")
                    or 0
                )
    logger.info("Dashboard accessed")
    return render_template("index.html", menu=menu)


@app.route("/shopping")
def shopping_list():
    menu = load_menu()
    if not menu or "shopping_list" not in menu:
        return render_template("error.html", message="No shopping list available"), 404

    from core.ingredient_deduplicator import strip_prep_descriptors, normalize_no_unit

    lang = _get_lang()
    if lang == "no":
        # Rebuild shopping list ingredient names in Norwegian from the recipe data
        shopping = {}
        recipe_ids = [d["recipe_id"] for d in menu.get("dinners", [])]
        from core.household_paths import recipes_db_file

        all_recipes_raw = []
        # Load from all sources: sample recipes, imported recipes, and recipe packs
        for db_path in (
            SEED_DIR / "sample_recipes.json",
            recipes_db_file(current_household_id()),
        ):
            if db_path.exists():
                try:
                    with open(db_path, "r", encoding="utf-8") as f:
                        all_recipes_raw.extend(json.load(f))
                except Exception:
                    pass
        # Also load from recipe packs (which have bilingual data)
        packs_dir = SEED_DIR / "recipe-packs"
        if packs_dir.exists():
            for pack_file in packs_dir.glob("*.json"):
                try:
                    with open(pack_file, "r", encoding="utf-8") as f:
                        pack = json.load(f)
                        all_recipes_raw.extend(pack.get("recipes", []))
                except Exception:
                    pass
        recipes_by_id = {r["id"]: r for r in all_recipes_raw}
        en_shopping = menu["shopping_list"]
        # Build a name map: english_name_lower -> norwegian_name
        name_map = {}
        for rid in recipe_ids:
            r = recipes_by_id.get(rid)
            if not r:
                continue
            # Check all possible ingredient fields
            for field in (
                "ingredients",
                "ingredients_included",
                "ingredients_not_included",
            ):
                for ing in r.get(field, []):
                    en = ""
                    no = ""
                    # Check for bilingual dict format (pack recipes)
                    if isinstance(ing.get("name"), dict):
                        en = (ing["name"].get("en") or "").strip().lower()
                        no = (ing["name"].get("no") or "").strip()
                    # Check for _no/_en suffix fields (sample_recipes format)
                    elif ing.get("name_en"):
                        en = (ing.get("name_en") or "").strip().lower()
                        no = (ing.get("name_no") or "").strip()
                    # Strip prep/cutting descriptors ("i skiver", "(sliced)", etc)
                    # so this matches the equally-stripped keys the shopping
                    # list was deduplicated under, and so the Norwegian name
                    # itself doesn't leak the same prep text either.
                    en = strip_prep_descriptors(en).lower()
                    no = strip_prep_descriptors(no)
                    if en and no:
                        name_map[en] = no
        # Translate shopping list ingredient names and units. Units go through
        # the same normalize_no_unit()/UNIT_MAP_NO used for recipe ingredients
        # (see B15/B20/B45) - this route used to have its own much smaller,
        # separate unit map here (only pieces/piece/pcs -> stk), which is why
        # tbsp/tsp/bunch etc. kept showing up in English even after those
        # earlier fixes: this was a different code path that never got the
        # same mapping applied.
        for category, items in en_shopping.items():
            new_items = []
            for item in items:
                new_item = dict(item)
                en_name = (
                    strip_prep_descriptors(item.get("ingredient", "")).strip().lower()
                )
                if en_name in name_map:
                    new_item["ingredient"] = name_map[en_name]
                else:
                    new_item["ingredient"] = strip_prep_descriptors(
                        item.get("ingredient", "")
                    )
                new_item["unit"] = normalize_no_unit(item.get("unit", ""))
                new_items.append(new_item)
            shopping[category] = new_items
    else:
        shopping = menu["shopping_list"]

    from core.household_paths import load_pantry

    pantry = set(load_pantry(current_household_id()))
    for category, items in shopping.items():
        for item in items:
            item["in_pantry"] = item.get("ingredient", "").strip().lower() in pantry
            # Same allergen-tag translation as _normalize_recipe() (B46) -
            # shopping list items aggregate per-ingredient allergens from
            # whichever recipes contributed them, in whatever language each
            # one happened to be authored in.
            if item.get("allergens"):
                item["allergens"] = [
                    _translate_allergen(a, lang) for a in item["allergens"]
                ]

    return render_template(
        "shopping.html", shopping_list=shopping, pantry=sorted(pantry)
    )


@app.route("/about")
def about_page():
    lang = _get_lang()
    return render_template("about.html", lang=lang)


@app.route("/whats-new")
def whats_new():
    lang = _get_lang()
    return render_template("whats_new.html", lang=lang)


@app.route("/whats-planned")
def whats_planned():
    lang = _get_lang()
    return render_template("whats_planned.html", lang=lang)


@app.route("/help/advanced")
def help_advanced():
    lang = _get_lang()
    return render_template("help_advanced.html", lang=lang)


@app.route("/help/tips")
def help_tips():
    lang = _get_lang()
    return render_template("help_tips.html", lang=lang)


@app.route("/feedback")
def feedback_page():
    """Simple feedback form for trial testers - any logged-in user can report."""
    if not session.get("user_id"):
        return redirect(url_for("auth.login_page"))
    return render_template("feedback.html", success=request.args.get("success"))


@app.route("/api/feedback", methods=["POST"])
def api_submit_feedback():
    """Save feedback to a single append-only JSON file - simple enough for a
    handful of trial testers; not meant to scale past that without revisiting."""
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json() or {}
    feedback_type = (data.get("type") or "other").strip()
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not description:
        return (
            jsonify({"success": False, "message": "Title and description required"}),
            400,
        )

    from datetime import datetime

    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": feedback_type,
        "title": title,
        "description": description,
        "submitted_by": session.get("user_email", "unknown"),
        "household_id": current_household_id(),
    }

    feedback_file = DATA_DIR / "feedback.json"
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.append(entry)
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    if ADMIN_EMAIL:
        try:
            _notify_admin_of_feedback(entry)
        except Exception as e:
            logger.error(f"Feedback admin notification failed: {e}")

    return jsonify({"success": True})


@app.route("/feedback/list")
def feedback_list_page():
    """App-developer-only view of all submitted feedback, newest first. Gated
    by ADMIN_EMAIL specifically - NOT the same thing as being a household
    owner, which is a per-household role any signed-up user can hold."""
    user_email = (session.get("user_email") or "").strip().lower()
    if not ADMIN_EMAIL or user_email != ADMIN_EMAIL:
        return render_template("error.html", message="Not authorized"), 403

    feedback_file = DATA_DIR / "feedback.json"
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.reverse()  # newest first
    return render_template("feedback_list.html", entries=entries)


@app.route("/add-recipe")
def add_recipe_page():
    return render_template("add-recipe.html")


@app.route("/all-recipes")
def all_recipes_page():
    lang = _get_lang()
    # Load both household recipes AND shared sample recipes (same as MenuGenerator does)
    all_recipes = []
    sample_recipes_path = SEED_DIR / "sample_recipes.json"
    if sample_recipes_path.exists():
        try:
            with open(sample_recipes_path, "r", encoding="utf-8") as f:
                all_recipes.extend(json.load(f))
        except Exception:
            pass
    all_recipes.extend(load_recipes_db())
    recipes = [_normalize_recipe(r, lang) for r in all_recipes]
    return render_template("all-recipes.html", recipes=recipes)


@app.route("/settings")
def settings_page():
    """Owner-only: account/referral details and the activity log live here, so
    non-owner profiles (kids, viewers, editors) have no business seeing this page."""
    household_id_for_check = current_household_id()
    if household_id_for_check and not acting_role_is_owner():
        return redirect(url_for("dashboard"))

    activity_log = []
    household_id = current_household_id()
    if household_id and session.get("user_id") and acting_role_is_owner():
        from database.database import SessionLocal
        from database.models import Household as _H

        _db = SessionLocal()
        try:
            _hh = _db.query(_H).filter(_H.id == household_id).first()
            if _hh and _hh.activity_log:
                activity_log = list(reversed(_hh.activity_log))[:50]
        finally:
            _db.close()

    referral_code = None
    user_id = session.get("user_id")
    if user_id:
        from core.auth_helpers import get_user_by_email

        user = get_user_by_email(session.get("user_email", ""))
        if user:
            referral_code = user.referral_code

    categories = []
    if household_id:
        raw_cats = _load_household_categories(household_id)
        if raw_cats:
            lang = _get_lang()
            # Skip pack-name pseudo-categories (imported: true) here too -
            # same reasoning as /api/categories: recipes never carry one of
            # these as their actual category anymore (see B4b), so showing
            # them in the manage-categories list would let an owner try to
            # rename/merge/delete something that was never a real category.
            for cat in raw_cats:
                if cat.get("imported"):
                    continue
                translated = dict(cat)
                translated["name"] = (
                    cat.get(f"name_{lang}") or cat.get("name_en") or cat.get("code")
                )
                categories.append(translated)
            categories = _sort_categories(categories)

    has_pin = False
    if user_id:
        from core.auth_helpers import get_user_by_email as _get_user_by_email

        _user = _get_user_by_email(session.get("user_email", ""))
        has_pin = bool(_user and _user.pin_hash)

    pantry = []
    if household_id:
        from core.household_paths import pantry_item_language

        lang = _get_lang()
        pantry = sorted(
            p for p in _load_pantry_db() if pantry_item_language(p) in (lang, "both")
        )

    return render_template(
        "settings.html",
        activity_log=activity_log,
        referral_code=referral_code,
        categories=categories,
        has_pin=has_pin,
        pantry=pantry,
    )


@app.route("/api/account/set-pin", methods=["POST"])
def api_set_pin():
    """Owner-only: set or change the shared-device PIN used by the profile picker."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json() or {}
    pin = (data.get("pin") or "").strip()

    from core.auth_helpers import set_pin

    success, message = set_pin(user_id, pin)
    status = 200 if success else 400
    return jsonify({"success": success, "message": message}), status


@app.route("/api/account/clear-pin", methods=["POST"])
def api_clear_pin():
    """Owner-only: remove the PIN, falling back to the full account password."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    from core.auth_helpers import clear_pin

    success, message = clear_pin(user_id)
    return jsonify({"success": success, "message": message})


# ── Household/Team Management Routes ──────────────────────────────────────────


# ── Auth routes ───────────────────────────────────────────────────────────────


# Email/Password Authentication Routes


# ── Admin panel ───────────────────────────────────────────────────────────────
# _is_admin() lives in app_core.py now (also used by inject_config()'s
# context processor, which stays with the app factory) - imported above.


# NOTE: /api/debug-token was removed 2026-07-05 security pass - it decoded
# and returned the logged-in user's Azure JWT claims to anyone with an
# authenticated session, left in from earlier debugging despite its own
# docstring saying to remove it.

# ── API routes ────────────────────────────────────────────────────────────────


# _sort_categories() lives in app_core.py now (also used by settings_page())
# - imported above.


@app.route("/api/export-shopping-list", methods=["POST"])
def api_export_shopping_list():
    """Export shopping list in various formats."""
    try:
        from deployment.shopping_integrations import (
            export_csv,
            export_json,
            export_todoist_format,
            export_plain_text,
            export_ics,
            export_microsoft_todo_format,
        )

        data = request.get_json() or {}
        fmt = data.get("format", "txt").lower()
        full_shopping_list = data.get("shopping_list", {})
        selected_items = data.get("items", [])

        if not selected_items:
            return jsonify({"success": False, "error": "No items to export"}), 400

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [
                i
                for i in items
                if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set
            ]
            if kept:
                filtered[category] = kept

        # Generate export
        if fmt == "csv":
            content = export_csv(filtered)
            mime_type = "text/csv"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.csv'
        elif fmt == "json":
            content = export_json(filtered)
            mime_type = "application/json"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        elif fmt == "todoist":
            content = export_todoist_format(filtered)
            mime_type = "text/plain"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'
        elif fmt == "ics":
            content = export_ics(filtered)
            mime_type = "text/calendar"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'
        elif fmt == "todo":
            content = export_microsoft_todo_format(filtered)
            mime_type = "application/json"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        else:  # txt
            content = export_plain_text(filtered)
            mime_type = "text/plain"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'

        return jsonify(
            {
                "success": True,
                "content": content,
                "filename": filename,
                "mime_type": mime_type,
            }
        )

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sync-shopping-list", methods=["POST"])
def api_sync_shopping_list():
    """Shopping list sync endpoint. Only Apple Reminders (plain ICS download,
    no account/token needed) is supported. Microsoft To Do, Todoist, and
    TickTick sync were removed 2026-07-05 - they required each user to obtain
    and paste their own API token/Azure credentials, which is real setup
    friction and support burden for a friends-and-family/public audience.
    See docs/BACKLOG_2026-07-01.md for the note to re-add if users actually ask."""
    try:
        data = request.get_json() or {}
        service = data.get("service", "reminders").lower()
        full_shopping_list = data.get("shopping_list", {})
        selected_items = data.get("items", [])

        if not selected_items:
            return jsonify({"success": False, "error": "No items to sync"}), 400

        logger.info(
            f"Sync request: service={service}, items={len(selected_items)}, categories={len(full_shopping_list)}"
        )

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [
                i
                for i in items
                if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set
            ]
            if kept:
                filtered[category] = kept

        logger.info(
            f"Filtered: {len(filtered)} categories, total items: {sum(len(v) for v in filtered.values())}"
        )

        if service == "reminders":
            # Return ICS file for Apple Reminders as direct download
            from deployment.shopping_integrations import export_ics
            from flask import send_file
            import io

            content = export_ics(filtered)
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'

            # Create file-like object
            ics_file = io.BytesIO(content.encode("utf-8"))

            return send_file(
                ics_file,
                mimetype="text/calendar",
                as_attachment=True,
                download_name=filename,
            )

        else:
            return (
                jsonify({"success": False, "error": f"Unknown service: {service}"}),
                400,
            )

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/health")
def health_check():
    # LO8 (audit 2026-07-07): dropped the "https": CERT_FILE.exists() field -
    # a Pi-era local-HTTPS leftover (LO3) that's meaningless on Render, where
    # Cloudflare terminates TLS in front of the app entirely.
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
        }
    )


# ── Theme gallery ─────────────────────────────────────────────────────────────


# H3 (audit 2026-07-07): the old /themes and /themes/<filename> routes were
# deleted here - dead code from the theme refactor era. They listed
# frontend/static/theme-previews/, a directory that never existed (the real
# one is frontend/static/themes/previews/, which holds CSS, not the HTML
# files these routes expected), so both 500'd unconditionally. No nav link
# anywhere pointed to them - confirmed via a repo-wide search before
# deleting. frontend/templates/theme_gallery.html (the only thing that
# linked to itself) is now deleted too.

# ── Recipe Packs API ──────────────────────────────────────────────────────────


# ── Personal Recipe Arsenal API ───────────────────────────────────────────────


# B57 (2026-07): the old `if __name__ == "__main__": app.run(...)` entry
# point was removed here - flask_app.py imports from deployment/app_core.py
# now (a sibling module in the same package), which only resolves when this
# file is loaded AS a package (python -m flask --app deployment.flask_app,
# or gunicorn deployment.flask_app:app - what production/Docker/CI/
# RUN_LOCAL.bat all already used or have been updated to use). Running this
# file directly as a script (python deployment/flask_app.py) doesn't put the
# project root on sys.path the way "python -m" does, so the import fails
# with ModuleNotFoundError: No module named 'deployment' before this block
# would even run - keeping it around was actively misleading, not just
# unused. See RUN_LOCAL.bat/RUN_LOCAL.ps1 for the local dev launch command.
