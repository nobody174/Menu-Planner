import json
from pathlib import Path

# Load existing recipes from recipes_db.json
recipes_db_path = Path('data/recipes_db.json')
menus_dir = Path('data/menus')

if recipes_db_path.exists():
    with open(recipes_db_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)

    print(f"Migrating {len(recipes)} recipes to menus folder structure...")

    # Group recipes by category
    by_category = {}
    for recipe in recipes:
        cat = recipe.get('category', 'Uncategorized')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(recipe)

    # Write to respective folders
    for category, cat_recipes in by_category.items():
        cat_dir = menus_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)

        recipes_file = cat_dir / 'recipes.json'

        # Merge with existing if category folder already has recipes
        existing = []
        if recipes_file.exists():
            with open(recipes_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        # Avoid duplicates by ID
        existing_ids = {r['id'] for r in existing}
        new_recipes = [r for r in cat_recipes if r['id'] not in existing_ids]

        merged = existing + new_recipes

        with open(recipes_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)

        print(f"  {category}: {len(merged)} total recipes ({len(new_recipes)} new)")

    print(f"Migration complete!")
else:
    print("recipes_db.json not found")
