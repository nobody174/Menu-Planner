"""
B61 follow-up (2026-07-09): imported recipe-pack display metadata (name/
icon/color, shown on "Manage Recipe Packs") was never actually wired to
the imported_packs DB column that exists for it - the only implementation
was file-based, unlike every other data type, and since this Render
service has no persistent Disk, it silently reset on every deploy. Fixed
to use the DB column directly. These tests confirm the metadata now
genuinely persists across a fresh DB session (not just within one request/
one household object still held in memory) and that recipes/metadata are
both removed together.
"""

import pytest
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household


@pytest.fixture
def owner_session(client):
    _, user, _ = create_user("packs-owner@example.com", "PacksOwner123")
    confirm_email(user.raw_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Packs Test Household")

    with client.session_transaction() as sess:
        sess["user_id"] = str(user.id)
        sess["user_email"] = user.email
        sess["auth_type"] = "local"
        sess["current_household_id"] = household_id

    return user, household_id


class TestImportedPackMetadataPersistsInDb:
    def test_imported_pack_metadata_survives_a_fresh_db_session(
        self, client, owner_session
    ):
        _, household_id = owner_session

        resp = client.post(
            "/api/recipe-packs/import", json={"packIds": ["pack_chicken"]}
        )
        assert resp.status_code == 200
        assert resp.get_json()["success"] is True

        # Confirm it's actually in the DB column, not just readable within
        # the same request/session that wrote it - open an entirely fresh
        # session and read the column directly, mirroring what a real
        # redeploy (new process, new DB session) would see.
        from database.database import SessionLocal
        from database.models import Household

        db = SessionLocal()
        try:
            household = db.query(Household).filter(Household.id == household_id).first()
            assert household.imported_packs is not None
            assert "pack_chicken" in household.imported_packs
            meta = household.imported_packs["pack_chicken"]
            assert meta["display_name"]
            assert meta["icon"]
        finally:
            db.close()

        # And the read route reflects it correctly too.
        resp = client.get("/api/recipe-packs/imported")
        assert resp.status_code == 200
        packs = resp.get_json()["packs"]
        assert any(p["pack_id"] == "pack_chicken" for p in packs)
        chicken_pack = next(p for p in packs if p["pack_id"] == "pack_chicken")
        assert chicken_pack["icon"] != "📦"  # real icon, not the "unknown" fallback

    def test_removing_pack_clears_both_recipes_and_metadata(
        self, client, owner_session
    ):
        _, household_id = owner_session

        client.post("/api/recipe-packs/import", json={"packIds": ["pack_chicken"]})
        resp = client.post(
            "/api/recipe-packs/remove", json={"pack_id": "pack_chicken"}
        )
        assert resp.status_code == 200
        assert resp.get_json()["removed_count"] > 0

        from database.database import SessionLocal
        from database.models import Household

        db = SessionLocal()
        try:
            household = db.query(Household).filter(Household.id == household_id).first()
            assert "pack_chicken" not in (household.imported_packs or {})
        finally:
            db.close()

        resp = client.get("/api/recipe-packs/imported")
        assert resp.status_code == 200
        assert not any(
            p["pack_id"] == "pack_chicken" for p in resp.get_json()["packs"]
        )
