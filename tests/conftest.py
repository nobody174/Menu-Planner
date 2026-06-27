"""
Pytest configuration and fixtures for Menu-Planner tests.
"""

import pytest
import os
from pathlib import Path
import sys

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from pi_deployment.flask_app import app
from database.database import db, SessionLocal
from database.models import Base


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
