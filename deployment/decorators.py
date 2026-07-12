"""
Shared route decorators (LO2, 2026-07-12).

login_required() centralizes the hand-rolled
`if not session.get("user_id"): return redirect(...)` guard that was
duplicated across deployment/flask_app.py and deployment/routes/*.py.
It only covers the plain guard - routes where the login check is combined
with additional logic (role/admin checks, JSON 401 responses, etc.) are left
hand-rolled on purpose, per the audit that introduced this decorator.
"""

from functools import wraps

from flask import session, redirect, url_for


def login_required(view):
    """Redirect to the login page if there's no user_id in the session.

    Mirrors the exact behavior of the plain
    `if not session.get("user_id"): return redirect(url_for("auth.login_page"))`
    pattern used throughout the app - same redirect target, same (302)
    status code, no additional checks.
    """

    @wraps(view)
    def wrapped(*args, **kwargs):
        if not session.get("user_id"):
            return redirect(url_for("auth.login_page"))
        return view(*args, **kwargs)

    return wrapped
