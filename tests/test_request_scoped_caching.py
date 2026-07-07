"""
M6 (audit 2026-07-07): current_household_id() ran a full DB query
(get_user_households) on every call, and a single request calls it many
times over (the context processor, the route handler, several helpers each
route calls). These tests confirm it's now only queried once per request
(cached on flask.g) and that the cache never leaks between separate
requests - a stale cross-request cache would be a real correctness bug, not
just a missed optimization, since it could serve a different logged-in
user's cached household id.
"""

from unittest.mock import patch
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household


def _confirmed_user_with_household(email):
    _, user, _ = create_user(email, "TestPassword123")
    confirm_email(user.email_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Test Household")
    return user, household_id


def test_current_household_id_only_queries_once_per_request(test_app):
    from deployment.flask_app import current_household_id
    import core.household_helpers as hh

    user, household_id = _confirmed_user_with_household("cache-test@example.com")

    with test_app.test_request_context("/"):
        from flask import session

        session["user_id"] = str(user.id)

        with patch.object(
            hh, "get_user_households", wraps=hh.get_user_households
        ) as spy:
            first = current_household_id()
            second = current_household_id()
            third = current_household_id()

            assert first == second == third == household_id
            assert spy.call_count == 1, (
                "current_household_id() should only query the database once "
                "per request, regardless of how many times it's called"
            )


def test_household_id_cache_does_not_leak_between_requests(test_app):
    """Two different users, each with their own household, in two separate
    request contexts - the second request must resolve its OWN user's
    household, never the first request's cached value."""
    from deployment.flask_app import current_household_id

    user_a, household_a = _confirmed_user_with_household("cache-user-a@example.com")
    user_b, household_b = _confirmed_user_with_household("cache-user-b@example.com")

    with test_app.test_request_context("/"):
        from flask import session

        session["user_id"] = str(user_a.id)
        resolved_a = current_household_id()

    with test_app.test_request_context("/"):
        from flask import session

        session["user_id"] = str(user_b.id)
        resolved_b = current_household_id()

    assert resolved_a == household_a
    assert resolved_b == household_b
    assert resolved_a != resolved_b


class TestI18nCaching:
    """M6 (audit 2026-07-07): _load_i18n() used to unconditionally re-read
    and re-parse the ~29KB i18n.json on every single request. These tests
    confirm it now only re-reads the file when its mtime has actually
    changed, while still picking up a real edit immediately (no restart
    needed) - the exact behavior the original "reload on every request to
    catch updates" comment was protecting, just without paying for it on
    every request where nothing changed."""

    def test_repeated_calls_return_cached_object_without_reparsing(self):
        # B57 moved _load_i18n() (and every other shared app helper) into
        # app_core.py's create_app() factory module - flask_app.py now only
        # imports the specific names its own routes call directly
        # (_get_lang, _make_t), not this one.
        from deployment import app_core

        first = app_core._load_i18n()
        second = app_core._load_i18n()
        assert first is second, (
            "a second call with no file change should return the exact same "
            "cached dict, not a freshly-parsed one"
        )

    def test_real_file_edit_is_picked_up_without_restart(self):
        """Exercises the real _load_i18n() against the real i18n.json - a
        temporary marker key is added, confirmed picked up, then the file is
        restored to its exact original content in a try/finally so this
        test can't leave the real app data file mutated even if an
        assertion fails partway through."""
        import json
        import time
        from pathlib import Path
        from deployment import app_core

        i18n_path = (
            Path(app_core.__file__).parent.parent / "frontend" / "static" / "i18n.json"
        )
        original_content = i18n_path.read_text(encoding="utf-8")
        try:
            baseline = app_core._load_i18n()
            assert "__m6_test_marker__" not in baseline

            parsed = json.loads(original_content)
            parsed["__m6_test_marker__"] = "present"
            time.sleep(0.05)  # ensure a distinct, newer mtime
            i18n_path.write_text(json.dumps(parsed), encoding="utf-8")

            updated = app_core._load_i18n()
            assert updated.get("__m6_test_marker__") == "present"
        finally:
            i18n_path.write_text(original_content, encoding="utf-8")
            # Force a re-read so the process-global cache doesn't keep
            # serving the test's marker-containing dict to anything else
            # that calls _load_i18n() later in this same test session.
            app_core._I18N_CACHE["mtime"] = None
            app_core._load_i18n()
