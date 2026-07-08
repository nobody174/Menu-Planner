"""
B59 (audit 2026-07-07): /api/regenerate, /api/swap-recipe, and
/api/reroll-recipe had zero test coverage despite being the most complex,
highest-risk mutation routes in the app (row-locked via locked_household(),
history of real production bugs - B53's silent shortfall, B63's SQLite
concurrency corruption, the swap-day flag_modified() bug). These tests
exercise real menu generation/mutation against the shared base
sample_recipes.json (10 recipes across exactly the 3 categories these routes
default to), not a fully custom household recipe set.
"""

import pytest
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household, add_household_member


@pytest.fixture
def owner_session(client):
    _, user, _ = create_user("menu-owner@example.com", "MenuOwner123")
    confirm_email(user.email_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Menu Test Household")

    with client.session_transaction() as sess:
        sess["user_id"] = str(user.id)
        sess["user_email"] = user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return user, household_id


@pytest.fixture
def viewer_session(client, owner_session):
    owner, household_id = owner_session
    _, viewer_user, _ = create_user("menu-viewer@example.com", "MenuViewer123")
    confirm_email(viewer_user.email_confirmation_token)
    add_household_member(household_id, viewer_user.email, "viewer")

    with client.session_transaction() as sess:
        sess["user_id"] = str(viewer_user.id)
        sess["user_email"] = viewer_user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return viewer_user, household_id


class TestRegenerate:
    def test_regenerate_creates_menu_with_dinners(self, client, owner_session):
        resp = client.post("/api/regenerate", json={})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["status"] == "success"
        assert len(data["menu"]["dinners"]) > 0

    def test_regenerated_menu_is_persisted(self, client, owner_session):
        client.post("/api/regenerate", json={})
        resp = client.get("/api/menu")
        assert resp.status_code == 200
        assert len(resp.get_json()["dinners"]) > 0

    def test_regenerate_respects_num_dinners(self, client, owner_session):
        resp = client.post("/api/regenerate", json={"num_dinners": 3})
        assert resp.status_code == 200
        data = resp.get_json()
        assert len(data["menu"]["dinners"]) <= 3

    def test_regenerate_no_recipes_for_category_fails_cleanly(self, client, owner_session):
        resp = client.post(
            "/api/regenerate", json={"categories": ["Some Category With No Recipes"]}
        )
        assert resp.status_code == 400
        data = resp.get_json()
        assert data["status"] == "error"

    def test_viewer_cannot_regenerate(self, client, viewer_session):
        resp = client.post("/api/regenerate", json={})
        assert resp.status_code == 403


class TestSwapRecipe:
    def test_swap_moves_recipe_to_target_day(self, client, owner_session):
        client.post("/api/regenerate", json={})
        menu = client.get("/api/menu").get_json()
        dinners = menu["dinners"]
        assert len(dinners) >= 2

        recipe_id = dinners[0]["recipe_id"]
        target_day = dinners[1]["day"]

        resp = client.post(
            "/api/swap-recipe", json={"recipe_id": recipe_id, "day": target_day}
        )
        assert resp.status_code == 200

        updated_menu = client.get("/api/menu").get_json()
        target_dinner = next(d for d in updated_menu["dinners"] if d["day"] == target_day)
        assert target_dinner["recipe_id"] == recipe_id

    def test_swap_missing_fields_rejected(self, client, owner_session):
        client.post("/api/regenerate", json={})
        resp = client.post("/api/swap-recipe", json={})
        assert resp.status_code == 400

    def test_swap_with_no_menu_yet_404s(self, client, owner_session):
        resp = client.post(
            "/api/swap-recipe", json={"recipe_id": "some-id", "day": "Monday"}
        )
        assert resp.status_code == 404

    def test_viewer_cannot_swap(self, client, viewer_session):
        """The role check happens before the menu is even loaded, so this
        doesn't need a real menu to exist first (same pattern as the
        pantry/category permission tests)."""
        resp = client.post(
            "/api/swap-recipe", json={"recipe_id": "some-id", "day": "Monday"}
        )
        assert resp.status_code == 403


class TestRerollRecipe:
    def test_reroll_replaces_only_target_day(self, client, owner_session):
        client.post("/api/regenerate", json={})
        menu = client.get("/api/menu").get_json()
        dinners = menu["dinners"]
        target_day = dinners[0]["day"]
        other_days_before = {
            d["day"]: d["recipe_id"] for d in dinners if d["day"] != target_day
        }

        resp = client.post("/api/reroll-recipe", json={"day": target_day})
        assert resp.status_code == 200

        updated_menu = client.get("/api/menu").get_json()
        other_days_after = {
            d["day"]: d["recipe_id"]
            for d in updated_menu["dinners"]
            if d["day"] != target_day
        }
        assert other_days_before == other_days_after

    def test_reroll_missing_day_rejected(self, client, owner_session):
        client.post("/api/regenerate", json={})
        resp = client.post("/api/reroll-recipe", json={})
        assert resp.status_code == 400

    def test_reroll_unknown_day_404s(self, client, owner_session):
        client.post("/api/regenerate", json={})
        resp = client.post("/api/reroll-recipe", json={"day": "NotARealDay"})
        assert resp.status_code == 404

    def test_reroll_with_no_menu_yet_404s(self, client, owner_session):
        resp = client.post("/api/reroll-recipe", json={"day": "Monday"})
        assert resp.status_code == 404

    def test_viewer_cannot_reroll(self, client, viewer_session):
        resp = client.post("/api/reroll-recipe", json={"day": "Monday"})
        assert resp.status_code == 403
