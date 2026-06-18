#!/usr/bin/env python3
"""Validate recipe and category data structure."""
import json

# Check sample recipes
with open("data/sample_recipes.json", encoding="utf-8") as f:
    recipes = json.load(f)
    print(f"[OK] Found {len(recipes)} sample recipes")

    # Accept either 'id' or 'recipe_id', and 'title' or 'title_en'
    for recipe in recipes:
        if not ("id" in recipe or "recipe_id" in recipe):
            print("[FAIL] Recipe missing id/recipe_id")
            exit(1)
        if not any(k in recipe for k in ["title", "title_en", "title_no"]):
            print("[FAIL] Recipe missing title field")
            exit(1)
    print("[OK] All sample recipes have required fields")

# Check categories
with open("data/categories.json", encoding="utf-8") as f:
    categories = json.load(f)
    print(f"[OK] Found {len(categories)} categories")

    for cat in categories:
        if "code" not in cat or "name_en" not in cat or "name_no" not in cat:
            print(f"[FAIL] Category {cat} missing fields")
            exit(1)
    print("[OK] All categories have required fields")

# Check pantry staples
with open("pantry_staples.json", encoding="utf-8") as f:
    pantry = json.load(f)
    if "pantry_staples_english" in pantry and "pantry_staples_norwegian" in pantry:
        print(
            f"[OK] Pantry staples has {len(pantry['pantry_staples_english'])} English items"
        )
        print(
            f"[OK] Pantry staples has {len(pantry['pantry_staples_norwegian'])} Norwegian items"
        )
    else:
        print("[FAIL] Pantry staples missing language sections")
        exit(1)
