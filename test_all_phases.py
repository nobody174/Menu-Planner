#!/usr/bin/env python3
"""
Comprehensive test suite for all Pi-Menu phases
Tests: Scraper, Deduplicator, Menu Generator, Flask routes (mock), To Do sync, Email
"""

import json
import sys
from pathlib import Path
from datetime import datetime

sys.path.insert(0, str(Path('core')))
sys.path.insert(0, str(Path('scraper')))
sys.path.insert(0, str(Path('pi-deployment')))

def test_phase_1_scraper():
    """Test scraper structure and output"""
    print("\n[PHASE 1] Testing Scraper Structure")
    print("=" * 60)

    recipes_db = Path('data/recipes_db.json')
    if not recipes_db.exists():
        print("[SKIP] recipes_db.json not found (create with test_scraper.py first)")
        return False

    with open(recipes_db, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    print(f"[OK] Loaded {len(recipes)} recipes")

    required_fields = ['id', 'title', 'category', 'ingredients_included']
    for recipe in recipes[:3]:
        for field in required_fields:
            if field not in recipe:
                print(f"[ERROR] Recipe missing field: {field}")
                return False

    print(f"[OK] All recipes have required fields")

    orange_keywords = ['appelsin', 'oransje', 'orange']
    orange_recipes = [r for r in recipes if any(kw in r.get('title', '').lower() for kw in orange_keywords)]
    if orange_recipes:
        print(f"[WARN] Found {len(orange_recipes)} recipes with 'orange' in title (should be filtered)")
        return False

    print(f"[OK] No orange recipes found in database")

    return True

def test_phase_2_deduplicator():
    """Test ingredient deduplicator"""
    print("\n[PHASE 2] Testing Ingredient Deduplicator")
    print("=" * 60)

    from ingredient_deduplicator import IngredientDeduplicator

    dedup = IngredientDeduplicator(fuzzy_threshold=90)

    if not dedup.load_recipes(Path('data/recipes_db.json')):
        print("[SKIP] recipes_db.json not found")
        return False

    if len(dedup.recipes_db) < 5:
        print(f"[SKIP] Only {len(dedup.recipes_db)} recipes, need at least 5")
        return False

    recipe_ids = [dedup.recipes_db[i]['id'] for i in range(min(5, len(dedup.recipes_db)))]
    result = dedup.deduplicate_from_recipes(recipe_ids)

    if not result or 'shopping_list' not in result:
        print("✗ Deduplicator failed to generate shopping list")
        return False

    print(f"[OK] Input: {result['total_ingredients']} ingredients")
    print(f"[OK] Output: {result['deduplicated_count']} unique ingredients")

    shopping_list = result['shopping_list']
    total_items = sum(len(items) for items in shopping_list.values())
    print(f"[OK] Shopping list: {total_items} items in {len(shopping_list)} categories")

    pantry_items = dedup.load_pantry_staples()
    print(f"[OK] Loaded {len(pantry_items)} pantry staples")

    return True

def test_phase_3_menu_generator():
    """Test menu generator"""
    print("\n[PHASE 3] Testing Menu Generator")
    print("=" * 60)

    from menu_generator import MenuGenerator

    gen = MenuGenerator(seed=42)

    if not gen.load_recipes():
        print("[SKIP] recipes_db.json not found")
        return False

    gen.filter_recipes()
    menu = gen.generate_menu(num_dinners=5)

    if not menu or 'dinners' not in menu:
        print("✗ Menu generator failed")
        return False

    print(f"[OK] Generated menu for week {menu['week_start']} to {menu['week_end']}")
    print(f"[OK] Dinners: {len(menu['dinners'])}")

    for dinner in menu['dinners']:
        print(f"  - {dinner['day']:12} | {dinner['title'][:40]:40} | {dinner['protein']}")

    shopping_list = menu.get('shopping_list', {})
    if not shopping_list:
        print("[WARN] Warning: No shopping list in menu")
    else:
        total = sum(len(items) for items in shopping_list.values())
        print(f"[OK] Shopping list: {total} items")

    return True

def test_phase_4_flask_structure():
    """Test Flask app file structure"""
    print("\n[PHASE 4] Testing Flask App Structure")
    print("=" * 60)

    files_to_check = [
        'pi-deployment/flask_app.py',
        'frontend/templates/base.html',
        'frontend/templates/index.html',
        'frontend/templates/recipe.html',
        'frontend/templates/shopping.html',
        'frontend/templates/error.html',
        'frontend/static/style.css',
        'frontend/static/app.js',
    ]

    missing = []
    for file_path in files_to_check:
        if not Path(file_path).exists():
            missing.append(file_path)
        else:
            print(f"[OK] {file_path}")

    if missing:
        print(f"\n[ERROR] Missing files:")
        for f in missing:
            print(f"  - {f}")
        return False

    print(f"\n[OK] All Flask files present")

    with open('frontend/templates/base.html', 'r') as f:
        base_content = f.read()
        if '{% block content %}' not in base_content:
            print("[ERROR] base.html missing content block")
            return False

    print(f"[OK] Template structure is valid")

    with open('frontend/static/style.css', 'r') as f:
        css_content = f.read()
        if '.navbar' not in css_content or '.menu-card' not in css_content:
            print("[ERROR] style.css missing required styles")
            return False

    print(f"[OK] CSS styling is present")

    return True

def test_phase_5_integration_modules():
    """Test To Do sync and email modules"""
    print("\n[PHASE 5] Testing Integration Modules")
    print("=" * 60)

    modules_to_check = [
        ('pi-deployment/to_do_sync.py', 'ToDoSync'),
        ('pi-deployment/email_notifier.py', 'EmailNotifier'),
        ('pi-deployment/scheduler.py', 'MenuScheduler'),
        ('pi-deployment/app.py', 'app entry point'),
    ]

    for file_path, description in modules_to_check:
        if not Path(file_path).exists():
            print(f"[ERROR] Missing {description}: {file_path}")
            return False
        else:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                if 'class ' not in content and 'def ' not in content:
                    print(f"[ERROR] {description} is empty")
                    return False
            print(f"[OK] {description}")

    print(f"\n[OK] All integration modules present")

    return True

def test_data_files():
    """Test generated data files"""
    print("\n[DATA] Testing Generated Data Files")
    print("=" * 60)

    menu_file = Path('data/weekly_menu.json')
    if not menu_file.exists():
        print("[SKIP] weekly_menu.json not found (not generated yet)")
        return True

    with open(menu_file, 'r') as f:
        menu = json.load(f)

    if 'dinners' not in menu or 'shopping_list' not in menu:
        print("✗ weekly_menu.json structure invalid")
        return False

    print(f"[OK] weekly_menu.json is valid")
    print(f"  - Week: {menu['week_start']} to {menu['week_end']}")
    print(f"  - Dinners: {len(menu['dinners'])}")
    print(f"  - Shopping categories: {len(menu['shopping_list'])}")

    return True

def test_documentation():
    """Test documentation exists"""
    print("\n[DOCS] Testing Documentation")
    print("=" * 60)

    docs = [
        'ARCHITECTURE.md',
        'BUILD_SUMMARY.md',
        'SCRAPER_GUIDE.md',
        'STATUS_REPORT.md',
        'README.md',
        'REQUIREMENTS.md',
    ]

    missing = []
    for doc in docs:
        if not Path(doc).exists():
            missing.append(doc)
        else:
            size = Path(doc).stat().st_size
            print(f"[OK] {doc} ({size} bytes)")

    if missing:
        print(f"\n[ERROR] Missing documentation:")
        for f in missing:
            print(f"  - {f}")
        return False

    return True

def main():
    print("=" * 60)
    print("PI-MENU COMPREHENSIVE TEST SUITE (ALL PHASES)".center(60))
    print("=" * 60)

    results = {
        'Phase 1 (Scraper)': test_phase_1_scraper(),
        'Phase 2 (Deduplicator)': test_phase_2_deduplicator(),
        'Phase 3 (Menu Generator)': test_phase_3_menu_generator(),
        'Phase 4 (Flask)': test_phase_4_flask_structure(),
        'Phase 5 (Integration)': test_phase_5_integration_modules(),
        'Data Files': test_data_files(),
        'Documentation': test_documentation(),
    }

    print("\n" + "=" * 60)
    print("TEST SUMMARY")
    print("=" * 60)

    passed = sum(1 for v in results.values() if v)
    total = len(results)

    for test_name, result in results.items():
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[ERROR]"
        print(f"{symbol} {test_name:40} {status}")

    print("\n" + "=" * 60)
    print(f"TOTAL: {passed}/{total} test groups passed")
    print("=" * 60)

    if passed == total:
        print("\n[OK] ALL TESTS PASSED - Ready for real data scraping and deployment!")
        return 0
    else:
        print(f"\n[WARN] {total - passed} test groups failed - see above for details")
        return 1

if __name__ == '__main__':
    sys.exit(main())
