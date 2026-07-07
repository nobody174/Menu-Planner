"""
M4 (audit 2026-07-07): several DB-backed storage helpers in flask_app.py used
to catch a commit failure, print() it, and return normally (or fall through
to a file-based fallback the read path never looks at again) - the caller
believed the save succeeded when it hadn't. These tests simulate a DB commit
failure and confirm the exception now propagates instead of being silently
swallowed, for every function the audit named.
"""

import pytest
from unittest.mock import patch
from core.auth_helpers import create_user, confirm_email
from core.household_helpers import create_household


@pytest.fixture
def household_id():
    _, user, _ = create_user("storage-test@example.com", "StorageTest123")
    confirm_email(user.email_confirmation_token)
    _, household, household_id = create_household(str(user.id), "Storage Test Household")
    return household_id


def _mock_session_that_fails_commit():
    """A SessionLocal() stand-in whose .commit() always raises - simulates a
    dropped DB connection or constraint violation mid-write."""
    from unittest.mock import MagicMock
    from database.database import SessionLocal
    from database.models import Household

    real_session = SessionLocal()
    mock_session = MagicMock(wraps=real_session)
    mock_session.query = real_session.query
    mock_session.commit.side_effect = RuntimeError("simulated DB failure")
    return mock_session


class TestSaveRecipesDbPropagatesFailure:
    def test_save_recipes_db_raises_on_commit_failure(self, household_id):
        from deployment.flask_app import save_recipes_db, current_household

        with patch("deployment.flask_app.current_household") as mock_current_household:
            from database.database import SessionLocal
            from database.models import Household

            db = SessionLocal()
            household = db.query(Household).filter(Household.id == household_id).first()
            mock_current_household.return_value = household
            db.close()

            with patch("database.database.SessionLocal") as mock_session_local:
                mock_session_local.return_value = _mock_session_that_fails_commit()
                with pytest.raises(RuntimeError, match="simulated DB failure"):
                    save_recipes_db([{"id": "1", "title": "Test"}])


class TestSavePantryDbPropagatesFailure:
    def test_save_pantry_db_raises_on_commit_failure(self, household_id):
        from deployment.flask_app import _save_pantry_db

        with patch("deployment.flask_app.current_household_id") as mock_hid:
            mock_hid.return_value = household_id
            with patch("database.database.SessionLocal") as mock_session_local:
                mock_session_local.return_value = _mock_session_that_fails_commit()
                with pytest.raises(RuntimeError, match="simulated DB failure"):
                    _save_pantry_db(["salt", "pepper"])


class TestLoadPantryDbPropagatesFailure:
    def test_load_pantry_db_raises_on_query_failure(self, household_id):
        from deployment.flask_app import _load_pantry_db

        with patch("deployment.flask_app.current_household_id") as mock_hid:
            mock_hid.return_value = household_id
            with patch("database.database.SessionLocal") as mock_session_local:
                mock_session = _mock_session_that_fails_commit()
                mock_session.query.side_effect = RuntimeError("simulated DB failure")
                mock_session_local.return_value = mock_session
                with pytest.raises(RuntimeError, match="simulated DB failure"):
                    _load_pantry_db()
