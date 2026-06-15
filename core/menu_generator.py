#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

import json
import logging
import random
import sys
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Dict, Optional

sys.path.insert(0, str(Path(__file__).parent))
from ingredient_deduplicator import IngredientDeduplicator

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/menu_generator.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
RECIPES_DB_FILE = DATA_DIR / 'recipes_db.json'
MENU_OUTPUT_FILE = DATA_DIR / 'weekly_menu.json'

ORANGE_KEYWORDS = [
    'appelsin', 'oransje', 'orange', 'orange juice',
    'orange zest', 'orange marmelade', 'oransjemost'
]

DAYS = ['Mandag', 'Tirsdag', 'Onsdag', 'Torsdag', 'Fredag', 'Lørdag']

PROTEIN_KEYWORDS = {
    'chicken': ['kylling', 'chicken', 'høne'],
    'beef': ['kjøtt', 'beef', 'steak', 'brisket', 'entrecote'],
    'fish': ['fisk', 'fish', 'laks', 'salmon', 'torsk', 'cod', 'reke', 'shrimp'],
    'pork': ['svin', 'pork', 'bacon', 'ribbe'],
    'vegetarian': ['tofu', 'vegetar', 'vegan', 'bønner', 'beans', 'linser'],
    'lamb': ['lam', 'lamb'],
}


class MenuGenerator:
    def __init__(self, seed: Optional[int] = None, selected_categories: Optional[List[str]] = None):
        self.seed = seed
        if seed:
            random.seed(seed)
            logger.info(f"Seeded with: {seed}")

        self.selected_categories = selected_categories or ['Populære', 'Familie', 'Rask Middag']
        self.recipes_db = []
        self.deduplicator = IngredientDeduplicator()
        self.filtered_recipes = []

    def load_recipes(self) -> bool:
        """Load recipes from selected categories in menus folder"""
        self.recipes_db = []
        menus_dir = Path('data/menus')

        # Try to load from menus folder first (new structure)
        if menus_dir.exists():
            for category in self.selected_categories:
                if category == 'Favoritter':
                    # Skip Favoritter here, it's handled via localStorage on frontend
                    logger.info("Favoritter category selected (handled client-side)")
                    continue

                category_dir = menus_dir / category
                recipes_file = category_dir / 'recipes.json'

                if recipes_file.exists():
                    with open(recipes_file, 'r', encoding='utf-8') as f:
                        recipes = json.load(f)
                        self.recipes_db.extend(recipes)
                        logger.info(f"Loaded {len(recipes)} recipes from {category}")
                else:
                    logger.warning(f"No recipes found for category: {category}")
        else:
            # Fallback to old recipes_db.json if menus folder doesn't exist
            if not RECIPES_DB_FILE.exists():
                logger.error(f"Recipes database not found: {RECIPES_DB_FILE}")
                return False

            with open(RECIPES_DB_FILE, 'r', encoding='utf-8') as f:
                all_recipes = json.load(f)

            # Filter by selected categories (skip Favoritter, it's client-side)
            for recipe in all_recipes:
                if recipe.get('category') in self.selected_categories or recipe.get('category') in [cat for cat in self.selected_categories if cat != 'Favoritter']:
                    self.recipes_db.append(recipe)

            logger.info(f"Loaded {len(self.recipes_db)} recipes from recipes_db.json (filtered by {self.selected_categories})")

        logger.info(f"Total recipes loaded: {len(self.recipes_db)}")
        return len(self.recipes_db) > 0

    def contains_orange(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ORANGE_KEYWORDS)

    def filter_recipes(self) -> int:
        self.filtered_recipes = []

        for recipe in self.recipes_db:
            title = recipe.get('title', '')
            subtitle = recipe.get('subtitle', '')
            description = recipe.get('description', '')
            allergens = recipe.get('allergens', [])

            if self.contains_orange(title) or self.contains_orange(subtitle) or self.contains_orange(description):
                logger.debug(f"Filtered out (orange): {title}")
                continue

            ingredients = recipe.get('ingredients_included', [])
            has_orange = False
            for ing in ingredients:
                if self.contains_orange(ing.get('name', '')):
                    has_orange = True
                    break

            if has_orange:
                logger.debug(f"Filtered out (orange ingredient): {title}")
                continue

            self.filtered_recipes.append(recipe)

        logger.info(f"Filtered recipes: {len(self.filtered_recipes)} (removed {len(self.recipes_db) - len(self.filtered_recipes)} with orange)")
        return len(self.filtered_recipes)

    def get_protein_type(self, recipe_title: str) -> str:
        title_lower = recipe_title.lower()

        for protein_type, keywords in PROTEIN_KEYWORDS.items():
            if any(keyword in title_lower for keyword in keywords):
                return protein_type

        return 'other'

    def generate_menu(self, num_dinners: int = 6) -> Dict:
        if not self.filtered_recipes:
            logger.error("No recipes available. Run filter_recipes() first.")
            return {}

        if len(self.filtered_recipes) < num_dinners:
            logger.warning(f"Only {len(self.filtered_recipes)} recipes available, need {num_dinners}")
            num_dinners = len(self.filtered_recipes)

        selected_recipes = []
        available_recipes = self.filtered_recipes.copy()
        last_protein = None

        for i in range(num_dinners):
            best_recipe = None
            best_protein = None

            random.shuffle(available_recipes)

            for recipe in available_recipes:
                protein = self.get_protein_type(recipe['title'])

                if last_protein and protein == last_protein:
                    continue

                best_recipe = recipe
                best_protein = protein
                break

            if not best_recipe:
                best_recipe = available_recipes[0]
                best_protein = self.get_protein_type(best_recipe['title'])

            selected_recipes.append(best_recipe)
            available_recipes.remove(best_recipe)
            last_protein = best_protein

            logger.info(f"Selected for {DAYS[i]}: {best_recipe['title']} ({best_protein})")

        recipe_ids = [r['id'] for r in selected_recipes]
        shopping_list = self.deduplicator.deduplicate_from_recipes(recipe_ids)['shopping_list']

        week_start = self.get_next_monday()
        week_end = week_start + timedelta(days=5)  # Monday to Saturday = 5 days difference

        menu = {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'selected_categories': self.selected_categories,
            'dinners': [
                {
                    'day': DAYS[i],
                    'recipe_id': recipe['id'],
                    'title': recipe['title'],
                    'time_minutes': recipe.get('time_minutes', 0),
                    'difficulty': recipe.get('difficulty', ''),
                    'protein': self.get_protein_type(recipe['title'])
                }
                for i, recipe in enumerate(selected_recipes)
            ],
            'shopping_list': shopping_list
        }

        return menu

    def get_next_monday(self) -> datetime:
        today = datetime.now()
        days_until_monday = (7 - today.weekday()) % 7
        if days_until_monday == 0 and today.weekday() == 0:
            days_until_monday = 0
        else:
            days_until_monday = (7 - today.weekday()) % 7 or 7

        return (today + timedelta(days=days_until_monday)).replace(hour=0, minute=0, second=0, microsecond=0)

    def save_menu(self, menu: Dict) -> bool:
        if not menu:
            logger.error("Menu is empty. Cannot save.")
            return False

        DATA_DIR.mkdir(parents=True, exist_ok=True)

        with open(MENU_OUTPUT_FILE, 'w', encoding='utf-8') as f:
            json.dump(menu, f, ensure_ascii=False, indent=2)

        logger.info(f"Menu saved to {MENU_OUTPUT_FILE}")
        return True

    def run(self, num_dinners: int = 6, save: bool = True) -> Dict:
        logger.info("Starting menu generator")

        if not self.load_recipes():
            return {}

        if not self.deduplicator.load_recipes(RECIPES_DB_FILE):
            logger.warning("Deduplicator could not load recipes")

        self.filter_recipes()

        menu = self.generate_menu(num_dinners)

        if save:
            self.save_menu(menu)

        self.print_menu(menu)

        return menu

    def print_menu(self, menu: Dict) -> None:
        if not menu or 'dinners' not in menu:
            logger.info("No menu to print")
            return

        logger.info(f"\n=== WEEKLY MENU ({menu['week_start']} to {menu['week_end']}) ===\n")

        for dinner in menu['dinners']:
            logger.info(f"{dinner['day']:12} | {dinner['title']:50} | {dinner['time_minutes']} min | {dinner['difficulty']}")

        logger.info(f"\n=== SHOPPING LIST ===\n")

        shopping_list = menu.get('shopping_list', {})
        for category, items in shopping_list.items():
            if items:
                logger.info(f"{category}:")
                for item in items:
                    logger.info(f"  ☐ {item['ingredient']:30} | {item['quantity']} {item['unit']}")
                logger.info("")

        logger.info(f"✅ Menu generation complete!")


def test_menu_generator():
    logger.info("Testing menu generator...")

    generator = MenuGenerator(seed=42)
    menu = generator.run(num_dinners=6, save=True)

    return menu


if __name__ == '__main__':
    test_menu_generator()
