#!/usr/bin/env python3
"""
Seed recipes from JSON into PostgreSQL database.
Run after: alembic upgrade head
"""

import json
import sys
import uuid
from pathlib import Path

# Add parent directory to path so we can import database modules
sys.path.insert(0, str(Path(__file__).parent.parent))

from database.database import SessionLocal
from database.models import Recipe, RecipeIngredient

def seed_recipes():
    """Load recipes_db.json and insert into database."""
    recipes_path = Path(__file__).parent.parent / 'data' / 'recipes_db.json'

    if not recipes_path.exists():
        print(f"❌ recipes_db.json not found at {recipes_path}")
        return False

    try:
        with open(recipes_path, 'r', encoding='utf-8') as f:
            recipes_data = json.load(f)
    except Exception as e:
        print(f"❌ Error reading recipes_db.json: {e}")
        return False

    if not isinstance(recipes_data, list):
        print("❌ recipes_db.json must be an array of recipes")
        return False

    session = SessionLocal()
    try:
        existing_count = session.query(Recipe).count()
        if existing_count > 0:
            print(f"⚠️  Database already has {existing_count} recipes. Skipping seed.")
            return True

        inserted = 0
        for recipe_data in recipes_data:
            try:
                # Use existing id if present, otherwise generate UUID
                recipe_id = recipe_data.get('id')
                if not recipe_id:
                    recipe_id = str(uuid.uuid4())
                elif not isinstance(recipe_id, str):
                    recipe_id = str(recipe_id)

                # Handle different instruction formats
                instructions = recipe_data.get('instructions', [])
                if isinstance(instructions, dict):
                    # Keep dict as-is for JSON storage
                    instructions = instructions
                elif isinstance(instructions, str):
                    instructions = [instructions]
                elif not isinstance(instructions, list):
                    instructions = []

                # Allergens handling
                allergens = recipe_data.get('allergens', [])
                if isinstance(allergens, dict):
                    allergens = allergens
                elif not isinstance(allergens, list):
                    allergens = []

                recipe = Recipe(
                    id=recipe_id,
                    title=str(recipe_data.get('title', 'Untitled'))[:255],
                    subtitle=str(recipe_data.get('subtitle', ''))[:255] if recipe_data.get('subtitle') else None,
                    description=str(recipe_data.get('description', '')) if recipe_data.get('description') else None,
                    difficulty=str(recipe_data.get('difficulty', 'Easy'))[:50],
                    time_minutes=int(recipe_data.get('time_minutes', 30)),
                    category=str(recipe_data.get('category', ''))[:100] if recipe_data.get('category') else None,
                    instructions=instructions,
                    comment=str(recipe_data.get('comment', '')) if recipe_data.get('comment') else None,
                    allergens=allergens,
                    household_id=None  # Public recipes (no owner)
                )
                session.add(recipe)

                # Add ingredients
                for ing in recipe_data.get('ingredients', []):
                    ingredient = RecipeIngredient(
                        recipe_id=recipe_id,
                        name=ing.get('name', 'Unknown'),
                        quantity=float(ing.get('quantity', 0)),
                        unit=ing.get('unit'),
                        allergens=ing.get('allergens')
                    )
                    session.add(ingredient)

                inserted += 1
                if inserted % 10 == 0:
                    print(f"  Inserted {inserted} recipes...")

            except Exception as e:
                print(f"⚠️  Skipped recipe {recipe_data.get('id', 'unknown')}: {e}")
                continue

        session.commit()
        print(f"[OK] Successfully seeded {inserted} recipes")
        return True

    except Exception as e:
        session.rollback()
        print(f"[ERROR] Database error: {str(e)[:200]}")
        return False
    finally:
        session.close()

if __name__ == '__main__':
    success = seed_recipes()
    sys.exit(0 if success else 1)
