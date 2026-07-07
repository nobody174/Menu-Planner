"""
Route smoke test (B59 starter).

Not a correctness test - it hits every registered Flask route (GET routes
directly, POST routes with an empty/minimal body) both logged-out and
logged-in-with-a-household, and asserts none of them 500. This is
deliberately shallow: a 4xx (401/403/404/400) is a pass, only a genuine
5xx or an unhandled exception fails the test.

Why this exists: the 2026-07-07 audit found two bugs a test like this would
have caught immediately - a bare `from shopping_integrations import ...`
that only resolves when flask_app.py is run as a script (not under
`gunicorn deployment.flask_app:app`, which is what production actually
runs), and a `/themes` route pointing at a directory that no longer
existed. Both were silent 500s in production with all of CI green, because
zero routes had any test coverage at all (B59). This is not full coverage -
it's the cheapest possible tripwire for "this route doesn't even load
without crashing," which is exactly the class of bug that slipped through.
"""

import pytest
from database.database import SessionLocal
from database.models import Household
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household


def _all_routes():
    """(rule, methods) for every real app route, skipping Flask/static internals
    and routes with URL params (those need a real id to mean anything - see
    the dedicated parametrized tests below instead)."""
    from deployment.flask_app import app

    routes = []
    for rule in app.url_map.iter_rules():
        if rule.endpoint == "static":
            continue
        if "<" in rule.rule:
            continue
        methods = rule.methods - {"HEAD", "OPTIONS"}
        for method in methods:
            routes.append((rule.rule, method))
    return sorted(routes)


def _request(client, method, path):
    if method == "GET":
        return client.get(path)
    # POST/PUT/DELETE routes: send an empty JSON body. Real validation should
    # reject this with a 4xx - a 500 here means the route blew up before it
    # even got to validate its input (e.g. a NoneType/KeyError on missing
    # fields), which is its own real bug class distinct from "business logic
    # is wrong."
    return client.post(path, json={})


@pytest.fixture
def confirmed_user():
    success, user, user_id = create_user("smoketest@example.com", "SmokeTest123")
    assert success
    confirm_email(user.email_confirmation_token)
    return user, user_id


@pytest.fixture
def household_for_user(confirmed_user):
    _, user_id = confirmed_user
    success, household, household_id = create_household(user_id, "Smoke Household")
    assert success
    return household_id


@pytest.mark.parametrize("path,method", _all_routes())
def test_route_does_not_500_logged_out(client, path, method):
    """Every route, unauthenticated. Expect redirects/4xx, never a 500."""
    resp = _request(client, method, path)
    assert resp.status_code < 500, (
        f"{method} {path} returned {resp.status_code} logged out "
        f"(body: {resp.get_data(as_text=True)[:300]})"
    )


@pytest.mark.parametrize("path,method", _all_routes())
def test_route_does_not_500_logged_in(client, path, method, household_for_user):
    """Every route, authenticated with a real household. Expect success or a
    clean 4xx, never a 500 - this is the state most real traffic is in."""
    db = SessionLocal()
    try:
        household = db.query(Household).filter(Household.id == household_for_user).first()
        user_id = str(household.owner_id)
    finally:
        db.close()

    with client.session_transaction() as sess:
        sess["user_id"] = user_id
        sess["user_email"] = "smoketest@example.com"
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_for_user

    resp = _request(client, method, path)
    assert resp.status_code < 500, (
        f"{method} {path} returned {resp.status_code} logged in "
        f"(body: {resp.get_data(as_text=True)[:300]})"
    )


# ── Routes with URL parameters: exercise separately with a real-shaped value ──

_PARAM_ROUTES = [
    ("/recipe/does-not-exist", "GET"),
    ("/edit-recipe/does-not-exist", "GET"),
    ("/confirm-email/not-a-real-token", "GET"),
    ("/reset-password/not-a-real-token", "GET"),
    ("/reset-password/not-a-real-token", "POST"),
]


@pytest.mark.parametrize("path,method", _PARAM_ROUTES)
def test_param_route_does_not_500_logged_out(client, path, method):
    resp = _request(client, method, path)
    assert resp.status_code < 500, (
        f"{method} {path} returned {resp.status_code} logged out "
        f"(body: {resp.get_data(as_text=True)[:300]})"
    )
