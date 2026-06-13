#!/usr/bin/env python3
"""
Integration test: Verify scraper, deduplicator, and menu generator work together.
This tests with real dummy data to ensure all modules integrate correctly.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path('core')))
sys.path.insert(0, str(Path('scraper')))

from core.ingredient_deduplicator import IngredientDeduplicator
from core.menu_generator import MenuGenerator

DATA_DIR = Path('data')
RECIPES_DB = DATA_DIR / 'recipes_db.json'

def test_scraper_output():
    """Verify scraper creates valid JSON structure"""
    if not RECIPES_DB.exists():
        print("[SKIP] recipes_db.json not found - run test_scraper.py first")
        return False

    with open(RECIPES_DB, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    print(f"[OK] Scraper output loaded: {len(recipes)} recipes")

    required_fields = ['id', 'title', 'category', 'ingredients_included', 'ingredients_not_included']
    for recipe in recipes:
        for field in required_fields:
            if field not in recipe:
                print(f"[ERROR] Recipe {recipe.get('id')} missing field: {field}")
                return False

    print(f"[OK] All recipes have required fields")
    return True

def test_deduplicator():
    """Verify deduplicator processes recipes correctly"""
    deduplicator = IngredientDeduplicator(fuzzy_threshold=90)

    if not deduplicator.load_recipes(RECIPES_DB):
        print("[ERROR] Deduplicator failed to load recipes")
        return False

    if len(deduplicator.recipes_db) < 5:
        print(f"[WARNING] Only {len(deduplicator.recipes_db)} recipes available")
        recipe_ids = [r['id'] for r in deduplicator.recipes_db]
    else:
        recipe_ids = [deduplicator.recipes_db[i]['id'] for i in range(5)]

    result = deduplicator.deduplicate_from_recipes(recipe_ids)

    if not result or 'shopping_list' not in result:
        print("[ERROR] Deduplicator failed to generate shopping list")
        return False

    print(f"[OK] Deduplicator works:")
    print(f"     Input: {result['total_ingredients']} ingredients")
    print(f"     Output: {result['deduplicated_count']} unique ingredients")

    shopping_list = result['shopping_list']
    total_items = sum(len(items) for items in shopping_list.values())
    print(f"     Shopping list: {total_items} items across {len(shopping_list)} categories")

    return True

def test_menu_generator():
    """Verify menu generator creates valid menus"""
    generator = MenuGenerator(seed=42)

    if not generator.load_recipes():
        print("[ERROR] Menu generator failed to load recipes")
        return False

    generator.filter_recipes()
    menu = generator.generate_menu(num_dinners=5)

    if not menu or 'dinners' not in menu:
        print("[ERROR] Menu generator failed to generate menu")
        return False

    print(f"[OK] Menu generator works:")
    print(f"     Recipes: {len(generator.filtered_recipes)} (orange filter: {len(generator.recipes_db) - len(generator.filtered_recipes)} removed)")
    print(f"     Dinners: {len(menu['dinners'])}")
    print(f"     Shopping list: {sum(len(items) for items in menu['shopping_list'].values())} items")

    proteins = [d['protein'] for d in menu['dinners']]
    unique_proteins = set(proteins)
    print(f"     Protein variety: {unique_proteins}")

    if len(unique_proteins) < 3:
        print("[WARNING] Low protein variety (expected 3+)")

    return True

def test_orange_filter():
    """Verify orange allergen is filtered correctly"""
    generator = MenuGenerator()
    if not generator.load_recipes():
        return False

    orange_count = 0
    for recipe in generator.recipes_db:
        if generator.contains_orange(recipe.get('title', '')):
            orange_count += 1

    generator.filter_recipes()
    orange_in_filtered = 0
    for recipe in generator.filtered_recipes:
        if generator.contains_orange(recipe.get('title', '')):
            orange_in_filtered += 1

    print(f"[OK] Orange filter works:")
    print(f"     Total recipes with 'orange': {orange_count}")
    print(f"     After filtering: {orange_in_filtered}")
    print(f"     Removed: {orange_count - orange_in_filtered}")

    return orange_in_filtered == 0

def main():
    print("=" * 60)
    print("Pi-Menu Integration Test Suite")
    print("=" * 60)

    tests = [
        ("Scraper Output", test_scraper_output),
        ("Ingredient Deduplicator", test_deduplicator),
        ("Menu Generator", test_menu_generator),
        ("Orange Filter", test_orange_filter),
    ]

    results = []
    for test_name, test_func in tests:
        print(f"\n[TEST] {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
        except Exception as e:
            print(f"[ERROR] {test_name}: {e}")
            results.append((test_name, False))

    print("\n" + "=" * 60)
    print("Test Summary")
    print("=" * 60)

    passed = sum(1 for _, result in results if result)
    total = len(results)

    for test_name, result in results:
        status = "PASS" if result else "FAIL"
        symbol = "[OK]" if result else "[XX]"
        print(f"{symbol} {test_name}: {status}")

    print(f"\nTotal: {passed}/{total} tests passed")

    if passed == total:
        print("\n[OK] All integration tests passed! Ready for real data.")
        return 0
    else:
        print("\n[ERROR] Some tests failed. Check above for details.")
        return 1

if __name__ == '__main__':
    sys.exit(main())
