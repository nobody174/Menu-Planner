"""
Household and profile management routes (B57, audit 2026-07-07):
household settings/create/update/delete, the "who's using this" profile
picker and profile selection, adding lightweight member profiles, and the
household member management API (remove/rename/avatar/role). Moved out of
the former single flask_app.py verbatim - route bodies are unchanged.
"""

from flask import render_template, jsonify, request, session, redirect, url_for

from deployment.app_core import (
    current_household_id,
    acting_role_is_owner,
    MAX_PROFILES_PER_HOUSEHOLD,
    AVATAR_EMOJI_CHOICES,
    PROFILE_COOKIE_MAX_AGE,
)
from deployment.decorators import login_required


def register(bp):
    @bp.route("/household-settings")
    @login_required
    def household_settings():
        """View and manage household settings. Owner-only: this is a dinner-planning app,
        not a playground, so non-owner members have no business here even to look."""
        user_id = session.get("user_id")

        from core.household_helpers import (
            get_user_households,
            get_household_members,
            get_household,
        )

        # Resolve the active household through current_household_id(), which
        # re-validates that it actually belongs to the CURRENT user before
        # trusting it (see B50) - previously this route read the raw session
        # value directly into a household_id and rendered it with no ownership
        # check at all, the same shape of bug as B50.
        active_household_id = current_household_id()
        if active_household_id and not acting_role_is_owner():
            return redirect(
                url_for(
                    "settings_page",
                    error="Only the household owner can access household settings",
                )
            )

        # Get all user's households
        all_households = get_user_households(user_id)

        current_household = (
            get_household(active_household_id) if active_household_id else None
        )

        if not current_household and all_households:
            current_household = all_households[0]
            session["current_household_id"] = str(current_household.id)

        error = request.args.get("error")
        success = request.args.get("success")

        members = []
        owner_email = ""
        can_manage = False
        is_owner = False
        other_households = []

        if current_household:
            members = get_household_members(str(current_household.id))

            # Find owner email
            for member in members:
                if member["role"] == "owner":
                    owner_email = member["email"]
                    break

            # Check permissions - keyed off the ACTING identity, not just the account,
            # so a co-owner profile gets the same management rights as the owner.
            is_owner = acting_role_is_owner()
            user_member = next((m for m in members if m["user_id"] == user_id), None)
            can_manage = is_owner or (user_member and user_member["role"] == "editor")

            # Get other households
            other_households = [
                h for h in all_households if str(h.id) != str(current_household.id)
            ]

        profile_count = sum(1 for m in members if m["is_profile"])

        return render_template(
            "household-settings.html",
            current_household=current_household,
            members=members,
            owner_email=owner_email,
            can_manage=can_manage,
            is_owner=is_owner,
            other_households=other_households,
            profile_count=profile_count,
            max_profiles=MAX_PROFILES_PER_HOUSEHOLD,
            error=error,
            success=success,
        )

    @bp.route("/household/create", methods=["POST"])
    @login_required
    def create_household_handler():
        """Create a new household."""
        user_id = session.get("user_id")

        from core.household_helpers import create_household

        household_name = request.form.get("household_name", "").strip()
        success, result, household_id = create_household(user_id, household_name)

        if success:
            session["current_household_id"] = household_id
            return redirect(
                url_for(
                    "household.household_settings",
                    success="Household created successfully",
                )
            )
        else:
            return redirect(url_for("household.household_settings", error=result))

    @bp.route("/household/set-current", methods=["POST"])
    @login_required
    def set_current_household():
        """Switch to a different household."""
        user_id = session.get("user_id")

        household_id = request.form.get("household_id")

        from core.household_helpers import user_can_access_household

        if user_can_access_household(user_id, household_id):
            session["current_household_id"] = household_id
            return redirect(
                url_for("household.household_settings", success="Switched household")
            )
        else:
            return redirect(
                url_for("household.household_settings", error="Access denied")
            )

    @bp.route("/household/update", methods=["POST"])
    @login_required
    def update_household_handler():
        """Update household details."""
        household_id = current_household_id()
        if not household_id:
            return redirect(
                url_for("household.household_settings", error="No household selected")
            )

        from core.household_helpers import update_household

        if not acting_role_is_owner():
            return redirect(
                url_for("household.household_settings", error="Permission denied")
            )

        household_name = request.form.get("household_name", "").strip()

        name_to_update = household_name if household_name else None
        success, result = update_household(household_id, name=name_to_update)

        if success:
            return redirect(
                url_for("household.household_settings", success="Household updated")
            )
        else:
            return redirect(url_for("household.household_settings", error=result))

    @bp.route("/household/delete", methods=["POST"])
    @login_required
    def delete_household_handler():
        """Delete household (owner only)."""
        user_id = session.get("user_id")

        household_id = current_household_id()
        if not household_id:
            return redirect(
                url_for("household.household_settings", error="No household selected")
            )

        from core.household_helpers import delete_household

        success, result = delete_household(household_id, user_id)

        if success:
            session.pop("current_household_id", None)
            return redirect(
                url_for("household.household_settings", success="Household deleted")
            )
        else:
            return redirect(url_for("household.household_settings", error=result))

    @bp.route("/profile-picker")
    @login_required
    def profile_picker():
        """Show 'who's using this' profile picker if the current household has profiles."""
        user_id = session.get("user_id")

        from core.household_helpers import get_user_households, get_household_members

        all_households = get_user_households(user_id)
        active_household_id = current_household_id()
        current_household = None

        if active_household_id:
            from core.household_helpers import get_household

            current_household = get_household(active_household_id)

        if not current_household and all_households:
            current_household = all_households[0]
            session["current_household_id"] = str(current_household.id)

        if not current_household:
            return redirect(
                url_for(
                    "household.household_settings",
                    error="Create a household to get started",
                )
            )

        members = get_household_members(str(current_household.id))

        if not any(m["is_profile"] for m in members):
            return redirect("/")

        owner_password_error = request.args.get("owner_password_error")
        from core.auth_helpers import get_user_by_email

        owner_account = get_user_by_email(session.get("user_email", ""))
        owner_has_pin = bool(owner_account and owner_account.pin_hash)
        return render_template(
            "profile-picker.html",
            household=current_household,
            members=members,
            owner_password_error=owner_password_error,
            owner_has_pin=owner_has_pin,
        )

    @bp.route("/profile-picker/select", methods=["POST"])
    @login_required
    def select_profile():
        """Set the active profile for this session after picking from the picker."""
        user_id = session.get("user_id")

        member_id = request.form.get("member_id")
        is_account_holder = request.form.get("is_account_holder")

        if is_account_holder:
            from core.auth_helpers import (
                get_user_by_email,
                verify_pin,
                authenticate_user,
            )

            user = get_user_by_email(session.get("user_email", ""))

            if user and user.pin_hash:
                pin = request.form.get("owner_pin", "")
                if not verify_pin(user_id, pin):
                    return redirect(
                        url_for(
                            "household.profile_picker",
                            owner_password_error="Incorrect PIN",
                        )
                    )
            else:
                password = request.form.get("owner_password", "")
                success, _ = authenticate_user(session.get("user_email", ""), password)
                if not success:
                    return redirect(
                        url_for(
                            "household.profile_picker",
                            owner_password_error="Incorrect password",
                        )
                    )

            household_id = current_household_id()
            from core.household_helpers import get_household_members

            owner_name = session.get("user_email")
            if household_id:
                owner_member = next(
                    (
                        m
                        for m in get_household_members(household_id)
                        if m["user_id"] == user_id
                    ),
                    None,
                )
                if owner_member:
                    owner_name = owner_member["display_name"]

            session.pop("active_profile_id", None)
            session["active_profile_name"] = owner_name
            response = redirect("/")
            response.delete_cookie("remembered_profile_id")
            return response

        household_id = current_household_id()
        from core.household_helpers import get_member_by_id

        member = get_member_by_id(member_id, household_id)

        if not member or not member.is_profile:
            return redirect(
                url_for("household.profile_picker", error="Profile not found")
            )

        session["active_profile_id"] = str(member.id)
        session["active_profile_name"] = member.display_name

        response = redirect("/")
        response.set_cookie(
            "remembered_profile_id",
            str(member.id),
            max_age=PROFILE_COOKIE_MAX_AGE,
            httponly=True,
            samesite="Lax",
        )
        return response

    @bp.route("/household/add-profile", methods=["POST"])
    @login_required
    def add_household_profile():
        """Add a lightweight member profile (no login of its own) to the household."""
        household_id = current_household_id()
        if not household_id:
            return redirect(
                url_for("household.household_settings", error="No household selected")
            )

        from core.household_helpers import create_profile, get_profiles

        if not acting_role_is_owner():
            return redirect(
                url_for("household.household_settings", error="Permission denied")
            )

        if len(get_profiles(household_id)) >= MAX_PROFILES_PER_HOUSEHOLD:
            return redirect(
                url_for(
                    "household.household_settings",
                    error=f"This household already has the maximum of {MAX_PROFILES_PER_HOUSEHOLD} profiles",
                )
            )

        display_name = request.form.get("display_name", "").strip()
        role = request.form.get("role", "viewer")

        success, result, member_id = create_profile(household_id, display_name, role)

        if success:
            return redirect(url_for("household.household_settings", success=result))
        else:
            return redirect(url_for("household.household_settings", error=result))

    # API routes for household management
    @bp.route("/api/household/remove-member", methods=["POST"])
    def api_remove_household_member():
        """API: Remove household member."""
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        household_id = current_household_id()
        member_id = request.form.get("member_id")

        from core.household_helpers import remove_household_member

        if not acting_role_is_owner():
            return jsonify({"error": "Permission denied"}), 403

        success, message = remove_household_member(household_id, member_id, user_id)

        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": message}), 400

    @bp.route("/api/profile/set-avatar", methods=["POST"])
    def api_set_avatar():
        """Set an emoji avatar for a member. Allowed for: the owner managing any member,
        or the currently active identity setting its own avatar (low-stakes, no permission gate needed).
        """
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        household_id = current_household_id()
        member_id = request.form.get("member_id")
        emoji = request.form.get("emoji", "")

        if emoji not in AVATAR_EMOJI_CHOICES:
            return jsonify({"error": "Invalid avatar choice"}), 400

        is_own_active_identity = member_id == session.get("active_profile_id")
        if not is_own_active_identity and not acting_role_is_owner():
            return jsonify({"error": "Permission denied"}), 403

        from core.household_helpers import set_member_avatar

        success, message = set_member_avatar(member_id, household_id, emoji)

        if success:
            return jsonify({"success": True, "avatar": emoji})
        else:
            return jsonify({"error": message}), 400

    @bp.route("/api/household/rename-member", methods=["POST"])
    def api_rename_member():
        """API: Rename a household member (profile or the owner's own display name)."""
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        if not acting_role_is_owner():
            return jsonify({"error": "Permission denied"}), 403

        household_id = current_household_id()
        member_id = request.form.get("member_id")
        display_name = request.form.get("display_name", "")

        from core.household_helpers import rename_member, get_member_by_id

        success, message = rename_member(member_id, household_id, display_name)

        if success:
            member = get_member_by_id(member_id, household_id)
            if (
                member
                and member.is_profile
                and session.get("active_profile_id") == str(member.id)
            ):
                session["active_profile_name"] = member.display_name
            elif member and not member.is_profile and member.user_id == user_id:
                session["active_profile_name"] = member.display_name
            return redirect(url_for("household.household_settings", success="Renamed"))
        else:
            return redirect(url_for("household.household_settings", error=message))

    @bp.route("/api/household/update-member-role", methods=["POST"])
    def api_update_member_role():
        """API: Update member role."""
        user_id = session.get("user_id")
        if not user_id:
            return jsonify({"error": "Not authenticated"}), 401

        household_id = current_household_id()
        member_id = request.form.get("member_id")
        new_role = request.form.get("role")

        from core.household_helpers import update_member_role

        success, message = update_member_role(
            household_id, member_id, new_role, user_id
        )

        if success:
            return jsonify({"success": True, "message": message})
        else:
            return jsonify({"error": message}), 403
