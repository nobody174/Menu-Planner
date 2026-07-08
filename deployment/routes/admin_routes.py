"""
Admin panel routes (B57, audit 2026-07-07): the developer/site-admin-only
user list, a one-time recipe-unit normalization maintenance action, and
admin-triggered user deletion. Gated by _is_admin() (matches ADMIN_EMAIL,
not a household role) - moved out of the former single flask_app.py
verbatim, route bodies unchanged.
"""

from flask import render_template, redirect, url_for, request

from deployment.app_core import logger, _is_admin


def register(bp):
    @bp.route("/admin")
    def admin_panel():
        if not _is_admin():
            return redirect(url_for("dashboard"))
        from database.models import User as UserModel
        from database.database import SessionLocal as _SessionLocal

        db = _SessionLocal()
        try:
            users = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
            users_data = [
                {
                    "id": str(u.id),
                    "email": u.email,
                    "confirmed": bool(u.email_confirmed_at),
                    "created_at": (
                        u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
                    ),
                    "referral_code": u.referral_code,
                }
                for u in users
            ]
        finally:
            db.close()
        return render_template("admin.html", users=users_data)

    @bp.route("/admin/normalize-recipe-units", methods=["POST"])
    def admin_normalize_recipe_units():
        """One-time maintenance action: households that imported recipe packs
        before the unit-normalization fix (tbsp/tsp -> ss/ts, etc; see B20/B15)
        have that stale, already-copied-in data permanently baked into their own
        recipes_db column - fixing the seed files only helps *future* imports.
        This walks every household's already-imported recipes and re-applies the
        same normalization directly to their DB copy."""
        if not _is_admin():
            return redirect(url_for("dashboard"))

        from database.models import Household as _Household
        from database.database import SessionLocal as _SessionLocal
        from core.ingredient_deduplicator import normalize_no_unit

        db = _SessionLocal()
        households_changed = 0
        ingredients_fixed = 0
        try:
            households = db.query(_Household).all()
            for household in households:
                recipes = household.recipes_db
                if not isinstance(recipes, list):
                    continue
                changed = False
                for recipe in recipes:
                    if not isinstance(recipe, dict):
                        continue
                    for field in (
                        "ingredients",
                        "ingredients_included",
                        "ingredients_not_included",
                    ):
                        for ing in recipe.get(field, []) or []:
                            if not isinstance(ing, dict):
                                continue
                            unit = ing.get("unit")
                            new_unit = normalize_no_unit(unit)
                            if new_unit != unit:
                                ing["unit"] = new_unit
                                changed = True
                                ingredients_fixed += 1
                if changed:
                    # Reassign (not just mutate in place) so SQLAlchemy's JSONB
                    # change tracking actually notices the update.
                    household.recipes_db = recipes
                    households_changed += 1
            db.commit()
        except Exception as e:
            db.rollback()
            logger.error(f"Error normalizing recipe units: {e}")
            return redirect(
                url_for("admin.admin_panel", error=f"Normalization failed: {e}")
            )
        finally:
            db.close()

        logger.info(
            f"Admin normalized recipe units: {ingredients_fixed} ingredients across {households_changed} households"
        )
        return redirect(
            url_for(
                "admin.admin_panel",
                success=f"Normalized {ingredients_fixed} ingredient units across {households_changed} households",
            )
        )

    @bp.route("/admin/delete-user", methods=["POST"])
    def admin_delete_user():
        if not _is_admin():
            return redirect(url_for("dashboard"))
        from core.auth_helpers import delete_user_account

        user_id = request.form.get("user_id", "").strip()
        if not user_id:
            return redirect(url_for("admin.admin_panel", error="No user ID provided"))
        success, msg = delete_user_account(user_id)
        if success:
            logger.info(f"Admin deleted user {user_id}")
            return redirect(
                url_for("admin.admin_panel", success="User deleted successfully")
            )
        return redirect(url_for("admin.admin_panel", error=msg))
