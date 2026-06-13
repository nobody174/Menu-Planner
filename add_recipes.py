import json

recipes_to_add = [
    ("test-10-tacos", "Mexicanske tacos", "med kjøttstoff", "Familie", 22, "Enkel"),
    ("test-11-buddha", "Buddha bowl", "med kikertboller", "Rask Middag", 18, "Enkel"),
    ("test-12-risotto", "Svamprisotto", "med parmigiano", "Familie", 30, "Medium"),
    ("test-13-falafel", "Falafel wrap", "med hummus og salat", "Rask Middag", 25, "Enkel"),
    ("test-14-ramen", "Ramen suppe", "med kylling", "Populære", 28, "Medium"),
    ("test-15-curry", "Kylling tikka masala", "med ris", "Familie", 35, "Medium"),
    ("test-16-fajitas", "Kylling fajitas", "med paprika og løk", "Populære", 20, "Enkel"),
    ("test-17-stew", "Kjøttstuing", "med rotgrønnsaker", "Familie", 45, "Medium"),
    ("test-18-pad-thai", "Pad Thai", "med rejer", "Populære", 25, "Medium"),
    ("test-19-chili", "Chili con carne", "med bønner", "Familie", 40, "Enkel"),
]

with open('data/recipes_db.json', 'r', encoding='utf-8') as f:
    data = json.load(f)

for i, (id, title, subtitle, category, time, difficulty) in enumerate(recipes_to_add):
    recipe = {
        "id": id,
        "title": title,
        "subtitle": subtitle,
        "category": category,
        "url": f"https://example.com/{10+i}",
        "rating": 4.0 + (i % 8) * 0.1,
        "rating_count": 100 + i * 10,
        "time_minutes": time,
        "difficulty": difficulty,
        "tags": ["RASK"] if time < 25 else [],
        "allergens": [],
        "description": f"Lekker {category.lower()} oppskrift.",
        "ingredients_included": [
            {"quantity": 400 + i*50, "unit": "g", "name": f"Ingrediens {i+1}", "allergens": []},
            {"quantity": 200, "unit": "g", "name": f"Ingrediens {i+2}", "allergens": []},
        ],
        "ingredients_not_included": [],
        "instructions": [],
        "scraped_at": "2026-06-13T22:43:00"
    }
    data.append(recipe)

with open('data/recipes_db.json', 'w', encoding='utf-8') as f:
    json.dump(data, f, ensure_ascii=False, indent=2)

print(f'Now have {len(data)} recipes')
