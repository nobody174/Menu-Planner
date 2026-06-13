#!/usr/bin/env python3
"""
Test script to verify scraper structure works without full scraping.
This creates a few dummy recipes to test the deduplicator and menu generator.
"""

import json
from pathlib import Path
from datetime import datetime

DATA_DIR = Path('data')
DB_FILE = DATA_DIR / 'recipes_db.json'

DATA_DIR.mkdir(parents=True, exist_ok=True)

dummy_recipes = [
    {
        "id": "test-1-laks",
        "title": "Stekt laks og gulrot med ris",
        "subtitle": "med sitron og hvitløk",
        "category": "Familie",
        "url": "https://example.com/1",
        "rating": 4.5,
        "rating_count": 100,
        "time_minutes": 25,
        "difficulty": "Enkel",
        "tags": ["RASK"],
        "allergens": ["Fisk"],
        "description": "Enkel og rask fiskret med frisk sitron.",
        "ingredients_included": [
            {"quantity": 400, "unit": "g", "name": "Laksefilet", "allergens": ["Fisk"]},
            {"quantity": 300, "unit": "g", "name": "Gulrot", "allergens": []},
            {"quantity": 200, "unit": "g", "name": "Hvitløk", "allergens": []},
            {"quantity": 1, "unit": "stk", "name": "Sitron", "allergens": []},
        ],
        "ingredients_not_included": [
            {"quantity": 0, "unit": "", "name": "Salt til koking", "allergens": []},
            {"quantity": 0, "unit": "", "name": "Olje", "allergens": []},
        ],
        "instructions": [],
        "scraped_at": datetime.now().isoformat()
    },
    {
        "id": "test-2-kjottes",
        "title": "Kjøttboller i tomatsaus",
        "subtitle": "med potet og salat",
        "category": "Familie",
        "url": "https://example.com/2",
        "rating": 4.3,
        "rating_count": 150,
        "time_minutes": 30,
        "difficulty": "Enkel",
        "tags": [],
        "allergens": ["Gluten", "Hvete"],
        "description": "Klassisk kjøttbollerett med hjemmelaget tomatsaus.",
        "ingredients_included": [
            {"quantity": 500, "unit": "g", "name": "Kjøttdeig", "allergens": []},
            {"quantity": 600, "unit": "g", "name": "Potet", "allergens": []},
            {"quantity": 400, "unit": "g", "name": "Gulrot", "allergens": []},
            {"quantity": 200, "unit": "ml", "name": "Melk", "allergens": ["Melk"]},
        ],
        "ingredients_not_included": [
            {"quantity": 0, "unit": "", "name": "Salt", "allergens": []},
            {"quantity": 0, "unit": "", "name": "Pepper", "allergens": []},
        ],
        "instructions": [],
        "scraped_at": datetime.now().isoformat()
    },
    {
        "id": "test-3-kylling",
        "title": "Grillet kylling med paprika og mais",
        "subtitle": "servert med couscous",
        "category": "Rask Middag",
        "url": "https://example.com/3",
        "rating": 4.6,
        "rating_count": 200,
        "time_minutes": 20,
        "difficulty": "Enkel",
        "tags": ["RASK"],
        "allergens": ["Gluten"],
        "description": "Rask og enkel middag perfekt for travle hverdager.",
        "ingredients_included": [
            {"quantity": 600, "unit": "g", "name": "Kyllingbryst", "allergens": []},
            {"quantity": 200, "unit": "g", "name": "Paprika", "allergens": []},
            {"quantity": 150, "unit": "g", "name": "Mais", "allergens": []},
            {"quantity": 150, "unit": "g", "name": "Couscous", "allergens": ["Gluten"]},
        ],
        "ingredients_not_included": [
            {"quantity": 0, "unit": "", "name": "Olje", "allergens": []},
        ],
        "instructions": [],
        "scraped_at": datetime.now().isoformat()
    },
    {
        "id": "test-4-torsk",
        "title": "Bakt torsk med sitron og dill",
        "subtitle": "med søtpotet og spinat",
        "category": "Familie",
        "url": "https://example.com/4",
        "rating": 4.7,
        "rating_count": 120,
        "time_minutes": 25,
        "difficulty": "Enkel",
        "tags": [],
        "allergens": ["Fisk"],
        "description": "Lett og næringsfull fiskret med gode tilbehør.",
        "ingredients_included": [
            {"quantity": 450, "unit": "g", "name": "Torskfilet", "allergens": ["Fisk"]},
            {"quantity": 400, "unit": "g", "name": "Søtpotet", "allergens": []},
            {"quantity": 200, "unit": "g", "name": "Spinat", "allergens": []},
            {"quantity": 1, "unit": "stk", "name": "Sitron", "allergens": []},
        ],
        "ingredients_not_included": [
            {"quantity": 0, "unit": "", "name": "Dill", "allergens": []},
        ],
        "instructions": [],
        "scraped_at": datetime.now().isoformat()
    },
    {
        "id": "test-5-tofu",
        "title": "Stekt tofu med grønnsaker og soya",
        "subtitle": "servert med ris",
        "category": "Familie",
        "url": "https://example.com/5",
        "rating": 4.2,
        "rating_count": 80,
        "time_minutes": 22,
        "difficulty": "Enkel",
        "tags": ["RASK"],
        "allergens": ["Soja"],
        "description": "Vegetarvenlig middag med proteinrik tofu.",
        "ingredients_included": [
            {"quantity": 300, "unit": "g", "name": "Tofu", "allergens": []},
            {"quantity": 300, "unit": "g", "name": "Løk", "allergens": []},
            {"quantity": 200, "unit": "g", "name": "Paprika", "allergens": []},
            {"quantity": 100, "unit": "ml", "name": "Soyasaus", "allergens": ["Soja"]},
        ],
        "ingredients_not_included": [
            {"quantity": 0, "unit": "", "name": "Riseolje", "allergens": []},
        ],
        "instructions": [],
        "scraped_at": datetime.now().isoformat()
    }
]

with open(DB_FILE, 'w', encoding='utf-8') as f:
    json.dump(dummy_recipes, f, ensure_ascii=False, indent=2)

print(f"[OK] Created {len(dummy_recipes)} test recipes in {DB_FILE}")
print("\nNow run:")
print("  python -m core.menu_generator")
print("  python -m core.ingredient_deduplicator")
