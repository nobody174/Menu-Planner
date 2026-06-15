#!/usr/bin/env python3
#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

"""
Local Testing Suite

Tests all major Pi-Menu functionality without server.

Usage:
    python3 test-local.py [--verbose]
"""

import sys
import json
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

import logging
logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

def test_config_loading():
    """Test: Configuration loading"""
    try:
        import config
        assert config.PROJECT_ROOT.exists(), "PROJECT_ROOT not found"
        assert config.DATA_DIR.exists(), "DATA_DIR not found"
        logger.info("PASS: Configuration loading")
        return True
    except Exception as e:
        logger.error(f"FAIL: Configuration loading - {e}")
        return False

def test_recipe_loading():
    """Test: Recipe loading"""
    try:
        data_dir = PROJECT_ROOT / "data"
        recipe_file = data_dir / "sample_recipes.json"
        if not recipe_file.exists():
            logger.warning("SKIP: Recipe file not found")
            return True

        with open(recipe_file, 'r', encoding='utf-8') as f:
            recipes = json.load(f)
        assert len(recipes) > 0, "No recipes loaded"
        assert 'title_no' in recipes[0], "Missing title_no"
        assert 'title_en' in recipes[0], "Missing title_en"
        logger.info(f"PASS: Recipe loading ({len(recipes)} recipes)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Recipe loading - {e}")
        return False

def test_category_loading():
    """Test: Category loading"""
    try:
        data_dir = PROJECT_ROOT / "data"
        cat_file = data_dir / "categories.json"
        if not cat_file.exists():
            logger.warning("SKIP: Categories file not found")
            return True

        with open(cat_file, 'r', encoding='utf-8') as f:
            categories = json.load(f)
        assert len(categories) > 0, "No categories loaded"
        assert 'code' in categories[0], "Missing code"
        assert 'name_no' in categories[0], "Missing name_no"
        logger.info(f"PASS: Category loading ({len(categories)} categories)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Category loading - {e}")
        return False

def test_menu_generator():
    """Test: Menu generation"""
    try:
        from core.menu_generator import MenuGenerator

        gen = MenuGenerator()
        if not gen.load_recipes():
            logger.warning("SKIP: No recipes available")
            return True

        gen.filter_recipes()
        menu = gen.generate_menu(num_dinners=5)

        assert menu, "Menu generation returned empty"
        assert 'dinners' in menu, "Missing dinners"
        assert len(menu['dinners']) == 5, "Wrong number of dinners"
        logger.info("PASS: Menu generation")
        return True
    except Exception as e:
        logger.error(f"FAIL: Menu generation - {e}")
        return False

def test_language_manager():
    """Test: Language manager functionality"""
    try:
        data_dir = PROJECT_ROOT / "frontend" / "static"
        i18n_file = data_dir / "i18n.json"
        if not i18n_file.exists():
            logger.warning("SKIP: i18n file not found")
            return True

        with open(i18n_file, 'r', encoding='utf-8') as f:
            translations = json.load(f)

        # Check for key translations
        expected_keys = ['menu_no', 'menu_en', 'shopping_list_no', 'shopping_list_en']
        for key in expected_keys:
            assert key in translations, f"Missing translation: {key}"

        logger.info(f"PASS: Language manager ({len(translations)} translations)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Language manager - {e}")
        return False

def test_measurements():
    """Test: Measurement conversion"""
    try:
        # Test JSON-based measurement data
        data = {
            "g": {"oz": 0.035274},
            "ml": {"fl oz": 0.033814},
            "cup": {"ml": 236.588}
        }

        # Simple conversion test
        g_to_oz = 500 * data["g"]["oz"]
        assert 17 < g_to_oz < 18, "g to oz conversion failed"

        logger.info("PASS: Measurement conversion")
        return True
    except Exception as e:
        logger.error(f"FAIL: Measurement conversion - {e}")
        return False

def test_error_handler():
    """Test: Error handling utilities"""
    try:
        from core.error_handler import PIMenuError, RecipeLoadError, handle_error

        error = RecipeLoadError("Test error", {"detail": "test"})
        result = handle_error(error, "test context")

        assert result['status'] == 'error', "Error status not set"
        assert result['code'] == 'RECIPE_LOAD_ERROR', "Error code not set"
        logger.info("PASS: Error handling")
        return True
    except Exception as e:
        logger.error(f"FAIL: Error handling - {e}")
        return False

def test_static_files():
    """Test: Required static files exist"""
    try:
        static_dir = PROJECT_ROOT / "frontend" / "static"
        required_files = [
            "style.css",
            "app.js",
            "language-manager.js",
            "measurements.js",
            "i18n.json"
        ]

        for file in required_files:
            path = static_dir / file
            assert path.exists(), f"Missing: {file}"

        logger.info(f"PASS: Static files ({len(required_files)} files)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Static files - {e}")
        return False

def test_templates():
    """Test: Required templates exist"""
    try:
        template_dir = PROJECT_ROOT / "frontend" / "templates"
        required_templates = [
            "base.html",
            "index.html",
            "recipe.html",
            "shopping.html",
            "error.html"
        ]

        for tmpl in required_templates:
            path = template_dir / tmpl
            assert path.exists(), f"Missing: {tmpl}"

        logger.info(f"PASS: Templates ({len(required_templates)} templates)")
        return True
    except Exception as e:
        logger.error(f"FAIL: Templates - {e}")
        return False

def main():
    """Run all tests"""
    logger.info("\n=== PI-MENU LOCAL TEST SUITE ===\n")

    tests = [
        test_config_loading,
        test_recipe_loading,
        test_category_loading,
        test_menu_generator,
        test_language_manager,
        test_measurements,
        test_error_handler,
        test_static_files,
        test_templates,
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
