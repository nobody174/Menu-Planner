"""
B61 (2026-07-09): /shopping had two direct, unconditional calls to
core.household_paths file functions instead of the DB-backed equivalents
every other route already uses - not the "if not household: fall back to
file" pattern traced elsewhere in B61, these ran unconditionally regardless
of DB state:

1. load_pantry(household_id) - not just a reader, it also seeds/writes a
   fresh default-staples pantry.json file on every call. The shopping
   list's "already have this" pantry match compared against that freshly
   reseeded file, not the household's actual customized DB pantry (items
   added/removed via /api/pantry were silently ignored on this one page).
2. recipes_db_file(household_id) - read directly instead of load_recipes_db(),
   so imported/custom recipes' ingredients never contributed a Norwegian
   name to the shopping list's language rebuild (they're stored in the DB,
   not that file, for any real household).
"""

import pytest
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household


@pytest.fixture
def owner_session(client):
    _, user, _ = create_user("shopping-owner@example.com", "ShoppingOwner123")
    confirm_email(user.raw_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Shopping Test Household")

    with client.session_transaction() as sess:
        sess["user_id"] = str(user.id)
        sess["user_email"] = user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return user, household_id


class TestShoppingListUsesDbPantry:
    def test_shopping_list_loads_after_custom_pantry_add(self, client, owner_session):
        """Basic sanity: the route still works end-to-end after the fix
        (swapping load_pantry() for _load_pantry_db()) and a customized
        pantry persists correctly through the normal /api/pantry/add path
        the route now actually reads from."""
        add_resp = client.post(
            "/api/pantry/add", json={"item": "unusual-custom-pantry-item"}
        )
        assert add_resp.status_code == 200

        gen_resp = client.post("/api/regenerate", json={})
        assert gen_resp.status_code == 200

        resp = client.get("/shopping")
        assert resp.status_code == 200

        pantry_resp = client.get("/api/pantry")
        assert pantry_resp.status_code == 200
        assert "unusual-custom-pantry-item" in pantry_resp.get_json()["pantry"]

    def test_shopping_list_no_longer_creates_household_file_directory(
        self, client, owner_session
    ):
        """The old load_pantry() call seeded/wrote a per-household file as a
        side effect of every single /shopping page view - confirms that's
        gone."""
        from core.household_paths import HOUSEHOLDS_DIR

        _, household_id = owner_session
        hdir = HOUSEHOLDS_DIR / str(household_id)

        client.post("/api/regenerate", json={})
        assert not hdir.exists()

        resp = client.get("/shopping")
        assert resp.status_code == 200
        assert not hdir.exists(), (
            "/shopping must read pantry from the DB directly, "
            "not seed a per-household file as a side effect"
        )
