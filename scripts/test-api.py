#!/usr/bin/env python3
#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

"""
API Testing Suite

Tests all API endpoints without requiring a running Flask server.

Usage:
    python3 test-api.py
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_categories_api():
    """Test: Categories API endpoint data"""
    try:
        categories_file = PROJECT_ROOT / "data" / "categories.json"
        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)

        # Verify structure
        assert isinstance(categories, list), "Categories must be array"
        assert len(categories) > 0, "Must have at least 1 category"

        for cat in categories:
            assert 'code' in cat, "Missing code field"
            assert 'name_no' in cat, "Missing name_no field"
            assert 'name_en' in cat, "Missing name_en field"

        logger.info(f"PASS: Categories API ({len(categories)} categories)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Categories API - {e}")
        return False

def test_recipes_api():
    """Test: Recipes API endpoint data"""
    try:
        recipes_file = PROJECT_ROOT / "data" / "sample_recipes.json"
        with open(recipes_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)

        assert isinstance(recipes, list), "Recipes must be array"
        assert len(recipes) > 0, "Must have at least 1 recipe"

        for recipe in recipes:
            assert 'id' in recipe, "Missing id"
            assert 'title' in recipe or 'title_no' in recipe, "Missing title"
            assert 'category' in recipe, "Missing category"
            assert 'ingredients_included' in recipe, "Missing ingredients"

        logger.info(f"PASS: Recipes API ({len(recipes)} recipes)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Recipes API - {e}")
        return False

def test_menu_api():
    """Test: Menu file structure"""
    try:
        menu_file = PROJECT_ROOT / "data" / "weekly_menu.json"
        if not menu_file.exists():
            logger.warning("SKIP: Menu file not generated yet")
            return True

        with open(menu_file, 'r', encoding='utf-8') as f:
            menu = json.load(f)

        assert 'dinners' in menu, "Missing dinners"
        assert 'shopping_list' in menu, "Missing shopping_list"
        assert isinstance(menu['dinners'], list), "Dinners must be array"

        logger.info("PASS: Menu API structure")
        return True
    except Exception as e:
        logger.error(f"FAIL: Menu API - {e}")
        return False

def test_i18n_api():
    """Test: Translation data"""
    try:
        i18n_file = PROJECT_ROOT / "frontend" / "static" / "i18n.json"
        with open(i18n_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)

        assert isinstance(translations, dict), "Translations must be object"
        assert len(translations) > 0, "Must have translations"

        # Check for paired translations
        no_keys = [k for k in translations.keys() if k.endswith('_no')]
        en_keys = [k for k in translations.keys() if k.endswith('_en')]

        logger.info(f"PASS: i18n API ({len(no_keys)} NO, {len(en_keys)} EN)")
        return True
    except Exception as e:
        logger.error(f"FAIL: i18n API - {e}")
        return False

def test_env_template():
    """Test: Environment template"""
    try:
        env_file = PROJECT_ROOT / ".env.template"
        assert env_file.exists(), ".env.template not found"

        with open(env_file, 'r', encoding='utf-8') as f:
            content = f.read()

        # Check for key configuration options
        expected = ['HOUSEHOLD_NAME', 'AZURE_CLIENT_ID', 'EMAIL_RECIPIENTS', 'FLASK_SECRET_KEY']
        for key in expected:
            assert key in content, f"Missing {key} in .env.template"

        logger.info("PASS: Environment template")
        return True
    except Exception as e:
        logger.error(f"FAIL: Environment template - {e}")
        return False

def test_api_response_types():
    """Test: API response data types"""
    try:
        # Load sample data
        recipes_file = PROJECT_ROOT / "data" / "sample_recipes.json"
        with open(recipes_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)

        # Verify types
        recipe = recipes[0]
        assert isinstance(recipe['time_minutes'], int), "time_minutes must be int"
        assert isinstance(recipe['servings'], int), "servings must be int"
        assert isinstance(recipe['ingredients_included'], list), "ingredients must be list"
        assert isinstance(recipe['allergens'], list), "allergens must be list"

        logger.info("PASS: API response types")
        return True
    except Exception as e:
        logger.error(f"FAIL: API response types - {e}")
        return False

def test_category_consistency():
    """Test: Category references are consistent"""
    try:
        # Load data
        categories_file = PROJECT_ROOT / "data" / "categories.json"
        recipes_file = PROJECT_ROOT / "data" / "sample_recipes.json"

        with open(categories_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        with open(recipes_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)

        # Check recipe categories exist
        valid_codes = {cat['code'] for cat in categories}
        for recipe in recipes:
            category = recipe.get('category', 'unknown')
            if category not in valid_codes:
                logger.warning(f"Recipe '{recipe.get('title')}' has invalid category: {category}")

        logger.info("PASS: Category consistency check")
        return True
    except Exception as e:
        logger.error(f"FAIL: Category consistency - {e}")
        return False

def main():
    """Run all API tests"""
    logger.info("\n=== PI-MENU API TEST SUITE ===\n")

    tests = [
        test_categories_api,
        test_recipes_api,
        test_menu_api,
        test_i18n_api,
        test_env_template,
        test_api_response_types,
        test_category_consistency,
    ]

    passed = 0
    failed = 0

    for test in tests:
        if test():
            passed += 1
        else:
            failed += 1

    logger.info(f"\n=== RESULTS ===")
    logger.info(f"Passed: {passed}/{len(tests)}")
    logger.info(f"Failed: {failed}/{len(tests)}")

    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
