"""
Authentication routes (B57, audit 2026-07-07): login, signup, email
confirmation, password reset, logout, and account self-deletion. Moved out
of the former single flask_app.py verbatim - route bodies are unchanged.

register(bp, limiter) attaches every route to the given Blueprint rather
than decorating at import time, because the rate-limit decorators need the
app's actual Limiter instance, which only exists once deployment.app_core's
create_app() has run - blueprint modules are imported before that, so
`@limiter.limit(...)` can't be a bare module-level decorator here the way it
was in the old single-file flask_app.py.
"""

from flask import render_template, jsonify, request, session, redirect, url_for

from deployment.app_core import (
    logger,
    current_household_id,
    _send_confirmation_email,
    _send_password_reset_email,
)

bp_name = "auth"


def register(bp, limiter):
    @bp.route("/login-page")
    def login_page():
        """Render login page."""
        error = request.args.get("error")
        return render_template(
            "login.html", error=error, email=request.args.get("email", "")
        )

    @bp.route("/login", methods=["POST"])
    @limiter.limit("10 per minute")
    def login_local():
        """Handle local email/password login."""
        from core.auth_helpers import authenticate_user

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")

        if not email or not password:
            return (
                render_template(
                    "login.html", error="Email and password required", email=email
                ),
                400,
            )

        success, result = authenticate_user(email, password)
        if not success:
            if result == "EMAIL_NOT_CONFIRMED":
                return (
                    render_template(
                        "login.html",
                        email=email,
                        unconfirmed_email=email,
                        error="Please confirm your email before logging in.",
                    ),
                    401,
                )
            return render_template("login.html", error=result, email=email), 401

        user = result
        session.permanent = True
        session["user_id"] = str(user.id)
        session["user_email"] = user.email
        session["auth_type"] = "local"
        session.pop("active_profile_id", None)
        # Clear any household id left over from a previous login in this same
        # browser session - current_household_id() now independently verifies
        # membership too, but clearing it here as well means a fresh login
        # always starts from a clean slate rather than relying on that check.
        session.pop("current_household_id", None)
        logger.info(f"User logged in (local): {user.email}")
        return redirect(url_for("household.profile_picker"))

    @bp.route("/confirm-email/<token>")
    def confirm_email_route(token):
        """Land here from the link in the confirmation email. One-time use -
        the token is cleared on success, so a second click just shows the
        already-confirmed case rather than erroring."""
        from core.auth_helpers import confirm_email

        success, result = confirm_email(token)
        if success:
            return render_template(
                "login.html",
                success="✓ Email confirmed! You can now log in.",
                email=result.email,
            )
        elif result == "Invalid or expired confirmation link":
            return (
                render_template(
                    "login.html",
                    error="Email confirmation failed: link expired or incorrect token. You can still log in if your email was confirmed.",
                ),
                400,
            )
        else:
            return render_template("login.html", error=result), 400

    @bp.route("/resend-confirmation", methods=["POST"])
    @limiter.limit("5 per hour")
    def resend_confirmation():
        """Re-send the confirmation email with a fresh token - the fallback for
        a tester whose first email landed in spam or was sent to a typo'd
        address they've since corrected via a new signup.

        Always shows the same generic success message regardless of whether the
        email exists, is already confirmed, or genuinely got a fresh token sent
        (M7, 2026-07 security pass) - the old per-case error text ("User not
        found" / "Email already confirmed") let anyone probe which addresses are
        registered, the same enumeration issue already fixed on /login and
        /forgot-password."""
        from core.auth_helpers import regenerate_confirmation_token

        email = request.form.get("email", "").strip()
        if not email:
            return render_template("login.html", error="Email required"), 400

        success, result = regenerate_confirmation_token(email)
        if success:
            _send_confirmation_email(result)
            logger.info(f"Resent confirmation email to {result.email}")

        return render_template(
            "login.html",
            success="If that email is registered and not yet confirmed, a new confirmation link is on its way.",
            email=email,
        )

    @bp.route("/forgot-password")
    def forgot_password_page():
        return render_template(
            "forgot_password.html",
            error=request.args.get("error"),
            success=request.args.get("success"),
        )

    @bp.route("/forgot-password", methods=["POST"])
    @limiter.limit("5 per hour")
    def forgot_password():
        from core.auth_helpers import request_password_reset

        email = request.form.get("email", "").strip()
        if not email:
            return redirect(
                url_for("auth.forgot_password_page", error="Email required")
            )
        success, user = request_password_reset(email)
        if user:
            _send_password_reset_email(user)
            logger.info(f"Password reset email sent to {user.email}")
        # Always show the same message regardless of whether email exists
        return redirect(
            url_for(
                "auth.forgot_password_page",
                success="If that email is registered, a reset link is on its way.",
            )
        )

    @bp.route("/reset-password/<token>")
    def reset_password_page(token):
        return render_template(
            "reset_password.html", token=token, error=request.args.get("error")
        )

    @bp.route("/reset-password/<token>", methods=["POST"])
    def reset_password_submit(token):
        from core.auth_helpers import reset_password

        new_password = request.form.get("password", "")
        confirm = request.form.get("password_confirm", "")
        if new_password != confirm:
            return render_template(
                "reset_password.html", token=token, error="Passwords do not match"
            )
        success, msg = reset_password(token, new_password)
        if not success:
            return render_template("reset_password.html", token=token, error=msg)
        return redirect(
            url_for("auth.login_page", success="Password updated — you can now log in.")
        )

    @bp.route("/account/delete", methods=["POST"])
    def delete_own_account():
        """User deletes their own account. Requires password confirmation."""
        user_id = session.get("user_id")
        if not user_id:
            return redirect(url_for("auth.login_page"))
        from core.auth_helpers import (
            delete_user_account,
            get_user_by_email,
            verify_password,
        )

        password = request.form.get("password", "")
        user_email = session.get("user_email", "")
        user = get_user_by_email(user_email)
        if not user or not verify_password(user.password_hash, password):
            return redirect(
                url_for(
                    "settings_page",
                    error="Incorrect password — account not deleted",
                )
            )
        # LO8 (audit 2026-07-07): household_id must be captured *before*
        # delete_user_account() runs - it deletes the user's own row, and
        # current_household_id() resolves via a DB lookup keyed on that row, so
        # calling it afterward always returned None and this folder cleanup was
        # silently dead code (the file-storage fallback tree never actually got
        # cleaned up on self-deletion). Also removed a duplicate import of
        # delete_user_account - it was already imported above.
        household_id = current_household_id()

        user_id_str = str(user_id)
        success, msg = delete_user_account(user_id_str)
        if not success:
            return redirect(
                url_for(
                    "settings_page",
                    error=f"Could not delete account: {msg}",
                )
            )
        # Clean up the household folder if it exists
        from core.household_paths import HOUSEHOLDS_DIR
        import shutil

        if household_id:
            hdir = HOUSEHOLDS_DIR / str(household_id)
            if hdir.exists():
                shutil.rmtree(hdir, ignore_errors=True)
        session.clear()
        logger.info(f"Account deleted: {user_email}")
        return redirect(
            url_for(
                "auth.login_page",
                success="Your account has been permanently deleted.",
            )
        )

    @bp.route("/welcome")
    def welcome():
        """Promo/demo landing page shown to referral-link visitors before they hit the signup form."""
        return render_template("welcome.html", ref=request.args.get("ref", ""))

    @bp.route("/signup")
    def signup():
        """Render signup page."""
        error = request.args.get("error")
        ref = request.args.get("ref", "")
        if ref and not request.args.get("from_welcome"):
            return redirect(url_for("auth.welcome", ref=ref))
        return render_template(
            "signup.html", error=error, email=request.args.get("email", ""), ref=ref
        )

    @bp.route("/signup", methods=["POST"])
    @limiter.limit("10 per hour")
    def signup_local():
        """Handle local user registration."""
        from core.auth_helpers import create_user

        email = request.form.get("email", "").strip()
        password = request.form.get("password", "")
        password_confirm = request.form.get("password_confirm", "")
        ref = request.form.get("ref", "").strip()

        if not email or not password or not password_confirm:
            return (
                render_template(
                    "signup.html", error="All fields required", email=email, ref=ref
                ),
                400,
            )

        if password != password_confirm:
            return (
                render_template(
                    "signup.html", error="Passwords do not match", email=email, ref=ref
                ),
                400,
            )

        success, result, user_id = create_user(
            email, password, referred_by_code=ref or None
        )
        if not success:
            return (
                render_template("signup.html", error=result, email=email, ref=ref),
                400,
            )

        user = result
        logger.info(f"New user registered (pending email confirmation): {user.email}")
        _send_confirmation_email(user)
        return render_template(
            "signup.html", email=email, ref=ref, confirmation_sent=True
        )

    @bp.route("/login")
    def login():
        """Redirect to login page (for backward compatibility)."""
        return redirect(url_for("auth.login_page"))

    @bp.route("/logout")
    def logout():
        """Log out the current user."""
        user_email = session.get("user_email", "User")
        auth_type = session.get("auth_type", "unknown")
        session.clear()
        logger.info(f"User logged out ({auth_type}): {user_email}")
        return redirect("/")

    @bp.route("/api/user")
    def api_user():
        """Get current user info."""
        user_id = session.get("user_id")
        user_email = session.get("user_email")
        auth_type = session.get("auth_type")

        if user_id and user_email:
            return jsonify(
                {
                    "authenticated": True,
                    "user_id": user_id,
                    "email": user_email,
                    "auth_type": auth_type or "unknown",
                }
            )

        return jsonify({"authenticated": False})
