"""
Pytest configuration and fixtures for Menu-Planner tests.
"""

import pytest
import os
from pathlib import Path
import sys

# Add project root to path so 'deployment' (and 'core', 'database') import
# as normal packages - this used to need a workaround when the folder was
# named 'pi-deployment' (a hyphen isn't valid in a Python package name).
sys.path.insert(0, str(Path(__file__).parent.parent))

from deployment.flask_app import app
from database.database import db, SessionLocal, DATABASE_URL
from database.models import Base


def _refuse_if_real_dev_database():
    """The test suite wipes its database before every single test (see
    _clean_database below) - if that ever ran against the real local
    menu_planner.db (e.g. someone runs `pytest` without setting DATABASE_URL,
    so database.py silently falls back to .env's real dev database), it
    would permanently destroy real local data with zero warning. Fail loudly
    and refuse to run at all rather than risk that, even once."""
    db_url = DATABASE_URL.lower()
    if 'menu_planner.db' in db_url or (db_url.startswith('sqlite') and ':memory:' not in db_url and 'test' not in db_url):
        raise RuntimeError(
            f"\n\nRefusing to run tests against DATABASE_URL={DATABASE_URL!r} - "
            "this looks like it could be the real local dev database, and the "
            "test suite wipes its database before every test.\n"
            "Set DATABASE_URL to a dedicated test database first, e.g.:\n"
            "  export DATABASE_URL=sqlite:///test.db   (bash)\n"
            "  $env:DATABASE_URL='sqlite:///test.db'    (PowerShell)\n"
        )


_refuse_if_real_dev_database()


@pytest.fixture(autouse=True)
def _clean_database():
    """Several tests (e.g. test_household.py's test_users fixture) call core
    helpers like create_user() directly, with no dependency on the test_app
    fixture below - meaning the schema was never guaranteed to exist (failed
    outright in CI, where tests.yml has no DATABASE_URL/migrations step), and
    even once it does exist, every test was inserting the SAME hardcoded
    emails (owner@example.com etc.) into the SAME persistent SQLite file with
    no cleanup between tests - so only the first test in a run ever passed,
    every later one hit "User already exists". Dropping and recreating all
    tables before EVERY test (not just once per session) fixes both: the
    schema always exists, and each test starts from a guaranteed-empty
    database regardless of what an earlier test inserted."""
    db.drop_all()
    db.create_all()
    yield


@pytest.fixture
def test_app():
    """Create and configure a test Flask app."""
    app.config['TESTING'] = True
    app.config['SQLALCHEMY_ECHO'] = False
    app.config['WTF_CSRF_ENABLED'] = False

    # Use test database
    app.config['DATABASE_URL'] = os.getenv(
        'DATABASE_URL',
        'sqlite:///:memory:'
    )

    with app.app_context():
        # Create all tables
        db.create_all()
        yield app
        # Clean up
        db.session.remove()
        db.drop_all()


@pytest.fixture
def client(test_app):
    """Create a test client."""
    return test_app.test_client()


@pytest.fixture
def runner(test_app):
    """Create a CLI runner."""
    return test_app.test_cli_runner()


@pytest.fixture
def session(test_app):
    """Create a database session."""
    connection = db.engine.connect()
    transaction = connection.begin()
    session = SessionLocal(bind=connection)

    yield session

    session.close()
    transaction.rollback()
    connection.close()
