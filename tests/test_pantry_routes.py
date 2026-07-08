"""
B59 (audit 2026-07-07): /api/pantry/* had zero test coverage - the smoke
test (test_routes_smoke.py) only confirms these routes don't 500, not that
they behave correctly. These tests exercise the real add/remove/reset
behavior, including the bilingual-translation side effect (adding "lemon"
also silently stores "sitron") and the viewer-role permission gate.
"""

import pytest
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household, add_household_member


@pytest.fixture
def owner_session(client):
    """Logs a fresh owner in as the test client's session, with a household
    already created (owner role, full edit rights, no profile picker
    needed)."""
    _, user, _ = create_user("pantry-owner@example.com", "PantryOwner123")
    confirm_email(user.email_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Pantry Test Household")

    with client.session_transaction() as sess:
        sess["user_id"] = str(user.id)
        sess["user_email"] = user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return user, household_id


@pytest.fixture
def viewer_session(client, owner_session):
    """A second user added as a 'viewer' to the owner's household, session
    swapped to act as that viewer."""
    owner, household_id = owner_session
    _, viewer_user, _ = create_user("pantry-viewer@example.com", "PantryViewer123")
    confirm_email(viewer_user.email_confirmation_token)
    add_household_member(household_id, viewer_user.email, "viewer")

    with client.session_transaction() as sess:
        sess["user_id"] = str(viewer_user.id)
        sess["user_email"] = viewer_user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return viewer_user, household_id


class TestAddPantryItem:
    def test_add_item_appears_in_pantry(self, client, owner_session):
        resp = client.post("/api/pantry/add", json={"item": "carrots"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "carrots" in data["pantry"]

    def test_add_known_staple_also_stores_translation(self, client, owner_session):
        """Adding a known English staple should also silently store its
        Norwegian translation, so a household that later switches display
        language still sees it."""
        resp = client.post("/api/pantry/add", json={"item": "lemon"})
        assert resp.status_code == 200

        client.set_cookie("pi_language", "no")
        resp_no = client.get("/api/pantry")
        data_no = resp_no.get_json()
        assert "sitron" in data_no["pantry"]

    def test_add_empty_item_rejected(self, client, owner_session):
        resp = client.post("/api/pantry/add", json={"item": "  "})
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_viewer_cannot_add_pantry_item(self, client, viewer_session):
        resp = client.post("/api/pantry/add", json={"item": "carrots"})
        assert resp.status_code == 403
        assert resp.get_json()["success"] is False


class TestRemovePantryItem:
    def test_remove_item_disappears_from_pantry(self, client, owner_session):
        client.post("/api/pantry/add", json={"item": "carrots"})
        resp = client.post("/api/pantry/remove", json={"item": "carrots"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert "carrots" not in data["pantry"]

    def test_remove_known_staple_also_removes_translation(self, client, owner_session):
        client.post("/api/pantry/add", json={"item": "sugar"})
        client.post("/api/pantry/remove", json={"item": "sugar"})

        client.set_cookie("pi_language", "no")
        resp = client.get("/api/pantry")
        assert "sukker" not in resp.get_json()["pantry"]

    def test_viewer_cannot_remove_pantry_item(self, client, viewer_session):
        """The role check happens before the pantry is even loaded, so this
        doesn't need a real item to exist first."""
        resp = client.post("/api/pantry/remove", json={"item": "carrots"})
        assert resp.status_code == 403


class TestResetPantry:
    def test_reset_restores_default_staples(self, client, owner_session):
        client.post("/api/pantry/add", json={"item": "something-custom"})
        resp = client.post("/api/pantry/reset")
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert "something-custom" not in data["pantry"]
        assert len(data["pantry"]) > 0

    def test_viewer_cannot_reset_pantry(self, client, viewer_session):
        resp = client.post("/api/pantry/reset")
        assert resp.status_code == 403
