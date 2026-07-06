#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import copy
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

DATA_DIR = Path(__file__).parent.parent / 'data'

# Static seed content reads from here instead of DATA_DIR - see the matching
# comment in deployment/flask_app.py for why (Render's persistent disk
# at DATA_DIR never overwrites existing files, so static seed data shipped
# in the image needs a separate, always-fresh path to actually take effect).
SEED_DIR = Path(__file__).parent.parent / 'data-seed'
if not SEED_DIR.exists():
    SEED_DIR = DATA_DIR

RECIPES_DB_FILE = SEED_DIR / 'sample_recipes.json'
RECIPES_IMPORTED_FILE = DATA_DIR / 'recipes_db.json'
CATEGORIES_FILE = SEED_DIR / 'categories.json'
MENU_OUTPUT_FILE = DATA_DIR / 'weekly_menu.json'

ORANGE_KEYWORDS = [
    'appelsin', 'oransje', 'orange', 'orange juice',
    'orange zest', 'orange marmelade', 'oransjemost'
]

DAYS = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']

PROTEIN_KEYWORDS = {
    'chicken': ['kylling', 'chicken', 'høne', 'poultry'],
    'beef': ['kjøtt', 'beef', 'steak', 'brisket', 'entrecote', 'ground beef', 'minced beef'],
    'fish': ['fisk', 'fish', 'laks', 'salmon', 'torsk', 'cod', 'reke', 'shrimp', 'tuna', 'trout', 'halibut', 'haddock', 'seafood'],
    'pork': ['svin', 'pork', 'bacon', 'ribbe', 'ham', 'sausage'],
    'vegetarian': ['tofu', 'vegetar', 'vegan', 'bønner', 'beans', 'linser', 'lentil', 'chickpea', 'hummus', 'falafel'],
    'lamb': ['lam', 'lamb'],
    'soup': ['soup', 'suppe', 'stew', 'broth', 'bisque', 'chowder'],
}

PROTEIN_IMAGES = {
    'chicken': '/static/images/meal-chicken.jpg',
    'beef': '/static/images/meal-beef.jpg',
    'fish': '/static/images/meal-fish.jpg',
    'pork': '/static/images/meal-pork.jpg',
    'vegetarian': '/static/images/meal-vegetarian.jpg',
    'lamb': '/static/images/meal-lamb.jpg',
    'soup': '/static/images/meal-soup.jpg',
}

# Fallback when no title/subtitle keyword matches (B42): imported-pack and
# custom recipes often have titles that don't literally contain a protein
# word (e.g. "Gravlax" is fish, but doesn't contain "fish"/"salmon"), so they
# fell back to the generic plate icon even when their category clearly
# indicates the protein. Only the unambiguous categories are mapped here -
# categories that mix proteins (Pasta & Noodles, Salads, Quick Dinners, Grill,
# Sides, Tex-Mex) are deliberately left unmapped rather than guessed.
CATEGORY_PROTEIN_FALLBACK = {
    'Chicken': 'chicken',
    'Beef & Red Meat': 'beef',
    'Ground Meat & Sausages': 'beef',
    'Fish & Seafood': 'fish',
    'Pork': 'pork',
    'Vegetarian': 'vegetarian',
    'Soups & Stews': 'soup',
}


class MenuGenerator:
    def __init__(self, seed: Optional[int] = None, selected_categories: Optional[List[str]] = None,
                 household_id: Optional[str] = None, favorite_recipe_ids: Optional[List[str]] = None):
        self.seed = seed
        if seed:
            random.seed(seed)
            logger.info(f"Seeded with: {seed}")

        self.household_id = household_id
        if household_id:
            from core.household_paths import recipes_db_file, categories_file, menu_file
            self.recipes_imported_file = recipes_db_file(household_id)
            self.categories_file = categories_file(household_id)
            self.menu_output_file = menu_file(household_id)
        else:
            self.recipes_imported_file = RECIPES_IMPORTED_FILE
            self.categories_file = CATEGORIES_FILE
            self.menu_output_file = MENU_OUTPUT_FILE

        self.categories = self.load_categories()
        self.selected_categories = selected_categories or ['Fish & Seafood', 'Soups & Stews', 'Beef & Red Meat', 'Chicken', 'Pasta & Noodles']
        self.favorite_recipe_ids = favorite_recipe_ids or []
        self.recipes_db = []
        self.deduplicator = IngredientDeduplicator()
        self.filtered_recipes = []

    def load_categories(self) -> List[Dict]:
        """Load categories from JSON file"""
        if self.categories_file.exists():
            try:
                with open(self.categories_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                logger.warning(f"Could not load categories: {e}")
                return []
        return []

    def load_recipes(self) -> bool:
        """Load recipes from the shared base sample_recipes.json plus this household's imported recipes, filter by selected categories or favorites."""
        self.recipes_db = []
        all_recipes = []

        # Load base sample recipes (shared starter content across all households)
        if RECIPES_DB_FILE.exists():
            try:
                with open(RECIPES_DB_FILE, 'r', encoding='utf-8') as f:
                    all_recipes.extend(json.load(f))
            except Exception as e:
                logger.error(f"Error loading {RECIPES_DB_FILE}: {e}")

        # Load household's imported recipes from database (primary) or file (fallback)
        if self.household_id:
            try:
                from database.database import SessionLocal
                from database.models import Household
                db = SessionLocal()
                try:
                    household = db.query(Household).filter(Household.id == self.household_id).first()
                    if household and household.recipes_db:
                        all_recipes.extend(household.recipes_db)
                        logger.info(f"Loaded {len(household.recipes_db)} recipes from database")
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Failed to load recipes from database: {e}, trying file fallback")
                if self.recipes_imported_file.exists():
                    try:
                        with open(self.recipes_imported_file, 'r', encoding='utf-8') as f:
                            all_recipes.extend(json.load(f))
                    except Exception as fe:
                        logger.error(f"Error loading {self.recipes_imported_file}: {fe}")
        elif self.recipes_imported_file.exists():
            try:
                with open(self.recipes_imported_file, 'r', encoding='utf-8') as f:
                    all_recipes.extend(json.load(f))
            except Exception as e:
                logger.error(f"Error loading {self.recipes_imported_file}: {e}")

        if not all_recipes:
            logger.error("No recipes found in any database file.")
            return False

        # Check if Favorites is selected (supports both English and Norwegian)
        has_favorites = any(cat for cat in self.selected_categories if cat.lower() in ('favorites', 'favoritter'))
        other_categories = [c for c in self.selected_categories if c.lower() not in ('favorites', 'favoritter')]

        # If Favorites is the ONLY thing selected, restrict to just favorites
        # and return early - no other category to union with.
        if has_favorites and not other_categories:
            if not self.favorite_recipe_ids:
                logger.info("Favorites selected but no recipes marked as favorites - returning empty")
                return True
            favorite_recipes = [r for r in all_recipes if r.get('id') in self.favorite_recipe_ids]
            seen_ids = set()
            for recipe in favorite_recipes:
                rid = recipe.get('id', '')
                if rid in seen_ids:
                    continue
                seen_ids.add(rid)
                recipe_copy = copy.deepcopy(recipe)
                for field in ('title', 'subtitle', 'description', 'comment'):
                    val = recipe_copy.get(field)
                    if isinstance(val, dict):
                        recipe_copy[f'_filter_{field}'] = val.get('en') or val.get('no') or ''
                self.recipes_db.append(recipe_copy)
            logger.info(f"Loaded {len(self.recipes_db)} favorite recipes")
            return len(self.recipes_db) > 0

        # Favorites + other categories both selected: treat Favorites as an
        # ADDITION (union), not a filter - otherwise checking Favorites
        # alongside every other category would shrink the pool down to just
        # the favorited recipes instead of adding them on top.
        favorite_recipes_to_add = []
        if has_favorites and self.favorite_recipe_ids:
            favorite_recipes_to_add = [r for r in all_recipes if r.get('id') in self.favorite_recipe_ids]

        # Filter by other selected categories (case-insensitive) if present
        selected_lower = [c.lower() for c in other_categories]
        seen_ids = set()
        for recipe in favorite_recipes_to_add:
            rid = recipe.get('id', '')
            if rid not in seen_ids:
                seen_ids.add(rid)
                recipe_copy = copy.deepcopy(recipe)
                for field in ('title', 'subtitle', 'description', 'comment'):
                    val = recipe_copy.get(field)
                    if isinstance(val, dict):
                        recipe_copy[f'_filter_{field}'] = val.get('en') or val.get('no') or ''
                self.recipes_db.append(recipe_copy)
        # "Quick Dinners" isn't a real category any recipe carries - it's
        # powered by the same 'quick' tag used for the (currently hidden)
        # quick-only filter on All Recipes. Match it the same way category
        # matching works, just against tags instead of the category field.
        wants_quick_dinners = 'quick dinners' in selected_lower
        selected_lower_without_quick = [c for c in selected_lower if c != 'quick dinners']
        # True "no categories selected at all" only when the original list was
        # empty - selecting ONLY Quick Dinners must not fall back to "include everything".
        no_categories_selected = not other_categories

        for recipe in all_recipes:
            rid = recipe.get('id', '')
            if rid in seen_ids:
                continue
            seen_ids.add(rid)
            category = recipe.get('category', '').lower()
            is_quick = 'quick' in [str(t).lower() for t in recipe.get('tags', [])]
            # Include if: nothing was selected at all, OR category matches a
            # selected (non-Quick-Dinners) category, OR Quick Dinners was
            # selected and this recipe carries the quick tag.
            if no_categories_selected or category in selected_lower_without_quick or (wants_quick_dinners and is_quick):
                # Deep copy to preserve original bilingual data
                recipe_copy = copy.deepcopy(recipe)
                # For filtering, add flattened versions of text fields
                # Keep originals intact for bilingual support
                for field in ('title', 'subtitle', 'description', 'comment'):
                    val = recipe_copy.get(field)
                    if isinstance(val, dict):
                        # Store flattened English version in a temporary field for filtering
                        recipe_copy[f'_filter_{field}'] = val.get('en') or val.get('no') or ''
                self.recipes_db.append(recipe_copy)

        logger.info(f"Loaded {len(self.recipes_db)} recipes (filtered by {self.selected_categories})")

        if len(self.recipes_db) == 0 and self.selected_categories:
            logger.warning(f"No recipes found for selected categories: {self.selected_categories}")

        return len(self.recipes_db) > 0

    def contains_orange(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ORANGE_KEYWORDS)

    def filter_recipes(self) -> int:
        self.filtered_recipes = []

        for recipe in self.recipes_db:
            # Use flattened filter fields if available, otherwise use original fields
            title = recipe.get('_filter_title', '')
            if not title and isinstance(recipe.get('title'), dict):
                title = recipe['title'].get('en') or recipe['title'].get('no') or ''
            elif not title:
                title = recipe.get('title', '')

            subtitle = recipe.get('_filter_subtitle', '')
            if not subtitle and isinstance(recipe.get('subtitle'), dict):
                subtitle = recipe['subtitle'].get('en') or recipe['subtitle'].get('no') or ''
            elif not subtitle:
                subtitle = recipe.get('subtitle', '')

            description = recipe.get('_filter_description', '')
            if not description and isinstance(recipe.get('description'), dict):
                description = recipe['description'].get('en') or recipe['description'].get('no') or ''
            elif not description:
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

    def get_protein_type(self, recipe_title: str, recipe_subtitle: str = '', category: str = '') -> str:
        combined_text = (recipe_title + ' ' + recipe_subtitle).lower()

        for protein_type, keywords in PROTEIN_KEYWORDS.items():
            if any(keyword in combined_text for keyword in keywords):
                return protein_type

        # B42: title/subtitle keyword matching often misses imported/custom
        # recipes whose name doesn't literally contain a protein word (e.g.
        # "Gravlax"). Fall back to the recipe's own category when it
        # unambiguously implies one, before giving up to 'other'.
        if category in CATEGORY_PROTEIN_FALLBACK:
            return CATEGORY_PROTEIN_FALLBACK[category]

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
                title = recipe.get('title')
                if isinstance(title, dict):
                    title_str = title.get('en') or title.get('no') or ''
                else:
                    title_str = title or ''
                subtitle = recipe.get('subtitle')
                if isinstance(subtitle, dict):
                    subtitle_str = subtitle.get('en') or subtitle.get('no') or ''
                else:
                    subtitle_str = subtitle or ''
                protein = self.get_protein_type(title_str, subtitle_str, recipe.get('category', ''))

                if last_protein and protein == last_protein:
                    continue

                best_recipe = recipe
                best_protein = protein
                break

            if not best_recipe:
                best_recipe = available_recipes[0]
                title = best_recipe.get('title')
                if isinstance(title, dict):
                    title_str = title.get('en') or title.get('no') or ''
                else:
                    title_str = title or ''
                subtitle = best_recipe.get('subtitle')
                if isinstance(subtitle, dict):
                    subtitle_str = subtitle.get('en') or subtitle.get('no') or ''
                else:
                    subtitle_str = subtitle or ''
                best_protein = self.get_protein_type(title_str, subtitle_str, best_recipe.get('category', ''))

            selected_recipes.append(best_recipe)
            available_recipes.remove(best_recipe)
            last_protein = best_protein

            title = best_recipe.get('title')
            if isinstance(title, dict):
                title_str = title.get('en') or title.get('no') or ''
            else:
                title_str = title or ''
            logger.info(f"Selected for {DAYS[i]}: {title_str} ({best_protein})")

        recipe_ids = [r['id'] for r in selected_recipes]
        shopping_list = self.deduplicator.deduplicate_from_recipes(recipe_ids)['shopping_list']

        week_start = self.get_next_monday()
        # week_end should reflect however many dinners actually got generated
        # (F10: user-selectable day count), not always assume Mon-Sat.
        week_end = week_start + timedelta(days=max(0, len(selected_recipes) - 1))

        dinners = []
        for i, recipe in enumerate(selected_recipes):
            title = recipe.get('title')
            if isinstance(title, dict):
                title_en = title.get('en', '')
                title_no = title.get('no', '')
            else:
                title_en = recipe.get('title_en', title or '')
                title_no = recipe.get('title_no', title or '')

            subtitle = recipe.get('subtitle')
            if isinstance(subtitle, dict):
                subtitle_en = subtitle.get('en', '')
                subtitle_no = subtitle.get('no', '')
            else:
                subtitle_en = recipe.get('subtitle_en', subtitle or '')
                subtitle_no = recipe.get('subtitle_no', subtitle or '')

            # Use English title and subtitle for protein detection
            protein_title = title_en or title_no or ''
            protein_subtitle = subtitle_en or subtitle_no or ''

            protein_type = self.get_protein_type(protein_title, protein_subtitle, recipe.get('category', ''))
            dinners.append({
                'day': DAYS[i],
                'recipe_id': recipe['id'],
                'title': recipe['title'],
                'title_no': title_no,
                'title_en': title_en,
                'time_minutes': recipe.get('time_minutes') or recipe.get('cookTimeMinutes') or 0,
                'difficulty': recipe.get('difficulty', ''),
                'protein': protein_type,
                'subtitle_no': subtitle_no,
                'subtitle_en': subtitle_en,
                'image_url': PROTEIN_IMAGES.get(protein_type, PROTEIN_IMAGES.get('vegetarian'))
            })

        menu = {
            'week_start': week_start.strftime('%Y-%m-%d'),
            'week_end': week_end.strftime('%Y-%m-%d'),
            'generated_at': datetime.now().isoformat(),
            'selected_categories': self.selected_categories,
            'dinners': dinners,
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

        # Save to database if household_id is set
        if self.household_id:
            try:
                from database.database import SessionLocal
                from database.models import Household
                from core.household_paths import save_weekly_menu_to_db

                db = SessionLocal()
                try:
                    household = db.query(Household).filter(Household.id == self.household_id).first()
                    if household:
                        save_weekly_menu_to_db(household, menu)
                        db.commit()
                        logger.info(f"Menu saved to database for household {self.household_id}")
                        return True
                finally:
                    db.close()
            except Exception as e:
                logger.error(f"Failed to save menu to database: {e}, falling back to file")

        # Fallback to file-based storage
        self.menu_output_file.parent.mkdir(parents=True, exist_ok=True)
        with open(self.menu_output_file, 'w', encoding='utf-8') as f:
            json.dump(menu, f, ensure_ascii=False, indent=2)

        logger.info(f"Menu saved to {self.menu_output_file}")
        return True

    def run(self, num_dinners: int = 6, save: bool = True) -> Dict:
        logger.info("Starting menu generator")

        if not self.load_recipes():
            return {}

        # Pass all loaded recipes directly to deduplicator
        if self.recipes_db:
            self.deduplicator.recipes_db = self.recipes_db
        elif not self.deduplicator.load_recipes(RECIPES_DB_FILE):
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
            title = dinner.get('title')
            if isinstance(title, dict):
                title_str = title.get('en') or title.get('no') or ''
            else:
                title_str = title or ''
            logger.info(f"{dinner['day']:12} | {title_str:50} | {dinner['time_minutes']} min | {dinner['difficulty']}")

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
