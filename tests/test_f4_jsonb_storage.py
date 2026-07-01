"""
F4 Migration Tests: Verify PostgreSQL JSONB storage works end-to-end.

Tests the database-backed data loading/saving for household data that
previously lived in JSON files.

Run with: python -m pytest tests/test_f4_jsonb_storage.py -v
"""

import pytest
import json
from datetime import datetime
from pathlib import Path


@pytest.fixture
def test_household(db_session):
    """Create a test household with sample data."""
    from database.models import User, Household
    import uuid

    user = User(
        id=str(uuid.uuid4()),
        email='test@example.com',
        password_hash='hashed_pass',
        referral_code='TEST1234'
    )
    db_session.add(user)
    db_session.flush()

    household = Household(
        id=str(uuid.uuid4()),
        name='Test Household',
        owner_id=user.id
    )
    db_session.add(household)
    db_session.commit()

    return household


class TestRecipesDbStorage:
    """Test recipes_db JSONB column storage."""

    def test_load_empty_recipes_db(self, test_household):
        """Loading recipes from empty JSONB should return empty list."""
        from core.household_paths import load_recipes_db_from_db

        result = load_recipes_db_from_db(test_household)
        assert result == []

    def test_save_and_load_recipes(self, test_household, db_session):
        """Save recipes to JSONB and verify they load correctly."""
        from core.household_paths import save_recipes_db_to_db, load_recipes_db_from_db

        recipes = [
            {
                'id': 'recipe1',
                'title': 'Pasta Carbonara',
                'difficulty': 'Easy',
                'time_minutes': 20,
                'category': 'Pasta',
                'ingredients': []
            },
            {
                'id': 'recipe2',
                'title': 'Chicken Tikka',
                'difficulty': 'Medium',
                'time_minutes': 45,
                'category': 'Chicken',
                'ingredients': []
            }
        ]

        save_recipes_db_to_db(test_household, recipes)
        db_session.merge(test_household)
        db_session.commit()

        # Reload from database
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_recipes_db_from_db(test_household)

        assert len(loaded) == 2
        assert loaded[0]['title'] == 'Pasta Carbonara'
        assert loaded[1]['title'] == 'Chicken Tikka'


class TestCategoriesStorage:
    """Test categories JSONB column storage with self-heal logic."""

    def test_load_empty_categories(self, test_household):
        """Loading categories from empty JSONB should return empty list."""
        from core.household_paths import load_categories_from_db

        result = load_categories_from_db(test_household)
        assert isinstance(result, list)

    def test_save_and_load_categories(self, test_household, db_session):
        """Save categories to JSONB and verify they load correctly."""
        from core.household_paths import save_categories_to_db, load_categories_from_db

        categories = [
            {'code': 'pasta', 'name': 'Pasta & Noodles', 'imported': False},
            {'code': 'chicken', 'name': 'Chicken', 'imported': False}
        ]

        save_categories_to_db(test_household, categories)
        db_session.merge(test_household)
        db_session.commit()

        # Reload from database
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_categories_from_db(test_household)

        assert len(loaded) >= 2
        codes = {c.get('code') for c in loaded}
        assert 'pasta' in codes
        assert 'chicken' in codes


class TestPantryStorage:
    """Test pantry JSONB column storage."""

    def test_load_empty_pantry(self, test_household):
        """Loading pantry from empty JSONB should return empty list."""
        from core.household_paths import load_pantry_from_db

        result = load_pantry_from_db(test_household)
        assert result == []

    def test_save_and_load_pantry(self, test_household, db_session):
        """Save pantry items to JSONB and verify they load correctly."""
        from core.household_paths import save_pantry_to_db, load_pantry_from_db

        items = ['butter', 'sugar', 'flour', 'salt', 'pepper']

        save_pantry_to_db(test_household, items)
        db_session.merge(test_household)
        db_session.commit()

        # Reload from database
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_pantry_from_db(test_household)

        assert len(loaded) == 5
        assert 'butter' in loaded
        assert 'flour' in loaded


class TestActivityLogStorage:
    """Test activity_log JSONB column storage."""

    def test_load_empty_activity_log(self, test_household):
        """Loading activity log from empty JSONB should return empty list."""
        from core.household_paths import load_activity_from_db

        result = load_activity_from_db(test_household)
        assert result == []

    def test_append_activity_to_db(self, test_household, db_session):
        """Append activity entries to JSONB and verify they persist."""
        from core.household_paths import append_activity_to_db, load_activity_from_db

        append_activity_to_db(test_household, 'user1@example.com', 'Added Pasta Carbonara recipe')
        db_session.commit()

        append_activity_to_db(test_household, 'user2@example.com', 'Generated weekly menu')
        db_session.commit()

        # Reload and verify
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        activities = load_activity_from_db(test_household)

        assert len(activities) >= 2
        assert any('Pasta Carbonara' in a.get('action', '') for a in activities)
        assert any('weekly menu' in a.get('action', '') for a in activities)

    def test_activity_log_capped_at_200(self, test_household, db_session):
        """Activity log should be capped at 200 entries."""
        from core.household_paths import save_activity_to_db, load_activity_from_db

        # Create 250 entries
        entries = [
            {
                'timestamp': datetime.now().isoformat(),
                'actor': f'user{i}@example.com',
                'action': f'Action {i}'
            }
            for i in range(250)
        ]

        save_activity_to_db(test_household, entries)
        db_session.merge(test_household)
        db_session.commit()

        # Reload and verify capped at 200
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_activity_from_db(test_household)

        assert len(loaded) <= 200


class TestImportedPacksStorage:
    """Test imported_packs JSONB column storage."""

    def test_load_empty_imported_packs(self, test_household):
        """Loading imported packs from empty JSONB should return empty dict."""
        from core.household_paths import load_imported_packs_from_db

        result = load_imported_packs_from_db(test_household)
        assert result == {}

    def test_save_and_load_imported_packs(self, test_household, db_session):
        """Save imported pack metadata to JSONB and verify it loads."""
        from core.household_paths import save_imported_packs_to_db, load_imported_packs_from_db

        packs = {
            'pack-001': {
                'display_name': 'Scandinavian Classics',
                'icon': 'fork-knife',
                'color': '#FF6B6B'
            },
            'pack-002': {
                'display_name': 'Healthy Bowls',
                'icon': 'leaf',
                'color': '#51CF66'
            }
        }

        save_imported_packs_to_db(test_household, packs)
        db_session.merge(test_household)
        db_session.commit()

        # Reload from database
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_imported_packs_from_db(test_household)

        assert len(loaded) == 2
        assert loaded['pack-001']['display_name'] == 'Scandinavian Classics'
        assert loaded['pack-002']['display_name'] == 'Healthy Bowls'


class TestWeeklyMenuStorage:
    """Test weekly_menu JSONB column storage."""

    def test_load_empty_weekly_menu(self, test_household):
        """Loading weekly menu from empty JSONB should return empty dict."""
        from core.household_paths import load_weekly_menu_from_db

        result = load_weekly_menu_from_db(test_household)
        assert result == {}

    def test_save_and_load_weekly_menu(self, test_household, db_session):
        """Save weekly menu to JSONB and verify it loads."""
        from core.household_paths import save_weekly_menu_to_db, load_weekly_menu_from_db

        menu = {
            'week_start': '2026-07-01',
            'week_end': '2026-07-07',
            'dinners': [
                {'day': 'Monday', 'recipe_id': 'recipe1'},
                {'day': 'Tuesday', 'recipe_id': 'recipe2'}
            ],
            'selected_categories': ['Pasta', 'Chicken']
        }

        save_weekly_menu_to_db(test_household, menu)
        db_session.merge(test_household)
        db_session.commit()

        # Reload from database
        test_household = db_session.query(type(test_household)).filter_by(id=test_household.id).first()
        loaded = load_weekly_menu_from_db(test_household)

        assert loaded['week_start'] == '2026-07-01'
        assert len(loaded['dinners']) == 2
        assert loaded['dinners'][0]['day'] == 'Monday'
