"""
B59 (audit 2026-07-07): /api/categories/* had zero test coverage. These
tests exercise add/rename/remove/merge behavior for real, including the
owner-only permission gate (stricter than the general "can edit" gate used
by pantry/menu routes - an editor is explicitly NOT allowed here) and the
recipe-reassignment side effect of deleting/merging a category, plus M2's
category-tombstone persistence (a deleted category must not resurrect on
reload).
"""

import shutil
from pathlib import Path

import pytest
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household, add_household_member


@pytest.fixture(autouse=True)
def _cleanup_sendt_forms_backup():
    """/api/add-recipe backs up every submitted form to the real
    data/sendt_forms/ directory in the project (not a test-isolated tmp
    path) - clean up whatever a test run creates there so tests don't leave
    stray files in the actual working tree."""
    yield
    backup_dir = Path("data/sendt_forms")
    if backup_dir.exists():
        shutil.rmtree(backup_dir, ignore_errors=True)


@pytest.fixture
def owner_session(client):
    _, user, _ = create_user("cat-owner@example.com", "CatOwner123")
    confirm_email(user.email_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Category Test Household")

    with client.session_transaction() as sess:
        sess["user_id"] = str(user.id)
        sess["user_email"] = user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return user, household_id


@pytest.fixture
def editor_session(client, owner_session):
    """A second user added as 'editor' - can edit recipes/menu, but must NOT
    be able to manage categories (owner-only, stricter than acting_role_can_edit())."""
    owner, household_id = owner_session
    _, editor_user, _ = create_user("cat-editor@example.com", "CatEditor123")
    confirm_email(editor_user.email_confirmation_token)
    add_household_member(household_id, editor_user.email, "editor")

    with client.session_transaction() as sess:
        sess["user_id"] = str(editor_user.id)
        sess["user_email"] = editor_user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return editor_user, household_id


class TestAddCategory:
    def test_add_category_appears_in_list(self, client, owner_session):
        resp = client.post("/api/categories/add", json={"name": "Desserts"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["success"] is True
        assert any(c["code"] == "desserts" for c in data["categories"])

    def test_add_duplicate_category_rejected(self, client, owner_session):
        client.post("/api/categories/add", json={"name": "Desserts"})
        resp = client.post("/api/categories/add", json={"name": "Desserts"})
        assert resp.status_code == 400
        assert resp.get_json()["success"] is False

    def test_editor_cannot_add_category(self, client, editor_session):
        resp = client.post("/api/categories/add", json={"name": "Desserts"})
        assert resp.status_code == 403


class TestRenameCategory:
    def test_rename_category_updates_name(self, client, owner_session):
        client.post("/api/categories/add", json={"name": "Deserts"})
        resp = client.post(
            "/api/categories/rename", json={"code": "deserts", "name": "Desserts"}
        )
        assert resp.status_code == 200
        data = resp.get_json()
        renamed = next(c for c in data["categories"] if c["code"] == "deserts")
        assert renamed["name_en"] == "Desserts"

    def test_rename_unknown_category_404s(self, client, owner_session):
        resp = client.post(
            "/api/categories/rename", json={"code": "nonexistent", "name": "New Name"}
        )
        assert resp.status_code == 404

    def test_editor_cannot_rename_category(self, client, editor_session):
        resp = client.post(
            "/api/categories/rename", json={"code": "chicken", "name": "New Name"}
        )
        assert resp.status_code == 403


class TestRemoveCategory:
    def test_remove_category_moves_recipes_to_uncategorized(self, client, owner_session):
        owner, household_id = owner_session
        client.post("/api/categories/add", json={"name": "Desserts"})
        client.post(
            "/api/add-recipe",
            json={
                "title": "Chocolate Cake",
                "category": "Desserts",
                "ingredients": [{"name": "Flour", "quantity": 1, "unit": "kg"}],
                "instructions": [],
            },
        )

        resp = client.post("/api/categories/remove", json={"code": "desserts"})
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["recipes_moved"] == 1
        assert not any(c["code"] == "desserts" for c in data["categories"])

    def test_removed_category_does_not_resurrect_on_reload(self, client, owner_session):
        """M2: the tombstone must persist, so a category the owner
        explicitly deleted never comes back via the base-category self-heal."""
        client.post("/api/categories/add", json={"name": "Desserts"})
        client.post("/api/categories/remove", json={"code": "desserts"})

        resp = client.get("/api/categories")
        assert resp.status_code == 200
        # GET /api/categories returns a bare list, unlike the add/remove/
        # merge routes which wrap it in {"categories": [...]}.
        codes = {c["code"] for c in resp.get_json()}
        assert "desserts" not in codes

    def test_editor_cannot_remove_category(self, client, editor_session):
        resp = client.post("/api/categories/remove", json={"code": "chicken"})
        assert resp.status_code == 403


class TestMergeCategory:
    def test_merge_moves_recipes_and_removes_source_category(self, client, owner_session):
        client.post("/api/categories/add", json={"name": "Deserts"})
        client.post("/api/categories/add", json={"name": "Desserts"})
        client.post(
            "/api/add-recipe",
            json={
                "title": "Typo'd Cake",
                "category": "Deserts",
                "ingredients": [{"name": "Flour", "quantity": 1, "unit": "kg"}],
                "instructions": [],
            },
        )

        resp = client.post(
            "/api/categories/merge",
            json={"from_code": "deserts", "into_code": "desserts"},
        )
        assert resp.status_code == 200
        data = resp.get_json()
        assert data["moved"] == 1
        assert not any(c["code"] == "deserts" for c in data["categories"])

    def test_merge_into_self_rejected(self, client, owner_session):
        client.post("/api/categories/add", json={"name": "Desserts"})
        resp = client.post(
            "/api/categories/merge",
            json={"from_code": "desserts", "into_code": "desserts"},
        )
        assert resp.status_code == 400

    def test_editor_cannot_merge_category(self, client, editor_session):
        resp = client.post(
            "/api/categories/merge", json={"from_code": "chicken", "into_code": "pork"}
        )
        assert resp.status_code == 403
