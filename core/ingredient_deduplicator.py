#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import json
import logging
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

try:
    from fuzzywuzzy import fuzz
except ImportError:
    fuzz = None
    logging.warning("fuzzywuzzy not installed. Install with: pip install fuzzywuzzy python-Levenshtein")

logger = logging.getLogger(__name__)

# Setup logging with safe directory creation
log_dir = Path(__file__).parent.parent / 'logs'
try:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'deduplicator.log')
    file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
    logger.addHandler(file_handler)
except Exception:
    pass  # If logs dir can't be created, just use console output
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

DATA_DIR = Path(__file__).parent.parent / 'data'
PANTRY_FILE = DATA_DIR / 'pantry_staples.json'

UNIT_CONVERSIONS = {
    'g': {'to_base': 1, 'base': 'g'},
    'gram': {'to_base': 1, 'base': 'g'},
    'kg': {'to_base': 1000, 'base': 'g'},
    'kilo': {'to_base': 1000, 'base': 'g'},
    'mg': {'to_base': 0.001, 'base': 'g'},
    'dl': {'to_base': 100, 'base': 'ml'},
    'ml': {'to_base': 1, 'base': 'ml'},
    'l': {'to_base': 1000, 'base': 'ml'},
    'liter': {'to_base': 1000, 'base': 'ml'},
    'cup': {'to_base': 237, 'base': 'ml'},
    'tbsp': {'to_base': 15, 'base': 'ml'},
    'tsp': {'to_base': 5, 'base': 'ml'},
    'stk': {'to_base': 1, 'base': 'stk'},
    'piece': {'to_base': 1, 'base': 'stk'},
    'clove': {'to_base': 1, 'base': 'stk'},
    'slice': {'to_base': 1, 'base': 'stk'},
}

INGREDIENT_CATEGORIES = {
    'Proteins': ['kj øtt', 'beef', 'chicken', 'fish', 'salmon', 'laks', 'cod', 'torsk',
                 'shrimp', 'reke', 'tofu', 'turkey', 'kalkun', 'pork', 'svin', 'lam',
                 'lamb', 'vegetarian', 'vegan', 'egg', 'steak', 'brisket'],
    'Vegetables': ['potet', 'potato', 'gulrot', 'carrot', 'løk', 'onion', 'tomat',
                   'tomato', 'salat', 'lettuce', 'spinat', 'spinach', 'brokkoli',
                   'broccoli', 'cauliflower', 'blomkål', 'paprika', 'bell pepper',
                   'sopp', 'mushroom', 'aubergine', 'eggplant', 'courgette', 'zucchini',
                   'agurk', 'cucumber', 'mais', 'corn', 'ris', 'pea', 'ert', 'artichoke'],
    'Dairy': ['melk', 'milk', 'ost', 'cheese', 'yogurt', 'yoghurt', 'fløte', 'cream',
              'smørfløte', 'creme fraiche', 'sour cream', 'rømme', 'feta', 'mozzarella',
              'parmesan', 'ricotta', 'mascarpone'],
    'Pantry': ['ris', 'rice', 'pasta', 'nudler', 'noodles', 'risotto', 'polenta',
               'bønner', 'beans', 'linser', 'lentils', 'kikert', 'chickpea', 'korn',
               'grain', 'havregryn', 'oats', 'mel', 'flour', 'bakepulver', 'baking powder',
               'gjær', 'yeast', 'brød', 'bread', 'pitabrød', 'pita', 'tortilla'],
    'Herbs & Spices': ['oregano', 'thyme', 'basilikum', 'basil', 'koriander', 'cilantro',
                       'parsley', 'persille', 'dill', 'paprika', 'paprikapulver', 'chili',
                       'kurkuma', 'turmeric', 'krydder', 'spices', 'curry'],
}


class IngredientDeduplicator:
    def __init__(self, fuzzy_threshold: int = 90):
        self.fuzzy_threshold = fuzzy_threshold
        self.pantry_staples = self.load_pantry_staples()
        self.recipes_db = []
        self.ingredient_map = {}

    def load_pantry_staples(self) -> List[str]:
        if PANTRY_FILE.exists():
            with open(PANTRY_FILE, 'r', encoding='utf-8') as f:
                data = json.load(f)
                staples = [s.lower().strip() for s in data.get('pantry_staples', [])]
                logger.info(f"Loaded {len(staples)} pantry staples")
                return staples
        else:
            logger.warning(f"Pantry staples file not found: {PANTRY_FILE}")
            return []

    def load_recipes(self, db_file: Path) -> bool:
        if not db_file.exists():
            logger.error(f"Recipes database not found: {db_file}")
            return False

        with open(db_file, 'r', encoding='utf-8') as f:
            self.recipes_db = json.load(f)
        logger.info(f"Loaded {len(self.recipes_db)} recipes")
        return True

    def fuzzy_match(self, ingredient: str, reference_list: List[str]) -> Tuple[str, int]:
        ingredient_clean = ingredient.lower().strip()

        if not fuzz:
            if ingredient_clean in reference_list:
                return ingredient_clean, 100
            return ingredient_clean, 0

        best_match = ingredient_clean
        best_score = 0

        for ref in reference_list:
            score = fuzz.token_sort_ratio(ingredient_clean, ref.lower())
            if score > best_score:
                best_score = score
                best_match = ref

        return best_match, best_score

    def is_pantry_staple(self, ingredient_name: str) -> bool:
        ingredient_lower = ingredient_name.lower().strip()

        for staple in self.pantry_staples:
            match, score = self.fuzzy_match(ingredient_lower, [staple])
            if score >= self.fuzzy_threshold:
                logger.debug(f"Matched '{ingredient_name}' to pantry staple '{staple}' (score: {score})")
                return True

        return False

    def normalize_unit(self, quantity: float, unit: str) -> Tuple[float, str]:
        unit_clean = unit.lower().strip() if unit else 'stk'

        if unit_clean in UNIT_CONVERSIONS:
            conversion = UNIT_CONVERSIONS[unit_clean]
            return quantity * conversion['to_base'], conversion['base']

        return quantity, unit_clean

    def deduplicate_ingredients(self, ingredient_list: List[Dict]) -> List[Dict]:
        ingredient_groups = defaultdict(lambda: {'quantities': [], 'units': [], 'allergens': set()})

        for ingredient in ingredient_list:
            if not ingredient.get('name'):
                continue

            name = ingredient['name'].strip()

            if self.is_pantry_staple(name):
                logger.debug(f"Filtering out pantry staple: {name}")
                continue

            name_lower = name.lower()

            best_key = name_lower
            best_score = 100

            if not fuzz:
                ingredient_groups[best_key]['quantities'].append(ingredient.get('quantity', 0))
                ingredient_groups[best_key]['units'].append(ingredient.get('unit', ''))
                if ingredient.get('allergens'):
                    ingredient_groups[best_key]['allergens'].update(ingredient['allergens'])
                continue

            for existing_key in ingredient_groups.keys():
                score = fuzz.token_sort_ratio(name_lower, existing_key)
                if score > best_score:
                    best_score = score
                    best_key = existing_key

            if best_score < self.fuzzy_threshold:
                best_key = name_lower

            ingredient_groups[best_key]['quantities'].append(ingredient.get('quantity', 0))
            ingredient_groups[best_key]['units'].append(ingredient.get('unit', ''))
            if ingredient.get('allergens'):
                ingredient_groups[best_key]['allergens'].update(ingredient['allergens'])

        deduplicated = []
        for ingredient_key, data in ingredient_groups.items():
            quantities = data['quantities']
            units = data['units']

            if quantities and units:
                normalized_quantities = []
                for q, u in zip(quantities, units):
                    norm_q, _ = self.normalize_unit(q, u)
                    normalized_quantities.append(norm_q)

                total_quantity = sum(normalized_quantities)

                primary_unit = units[0] if units else 'stk'
                for q, u in zip(quantities, units):
                    if q == max(quantities):
                        primary_unit = u
                        break

                if primary_unit.lower() in ['g', 'gram', 'kg', 'kilo', 'mg']:
                    primary_unit = 'g'
                    if total_quantity >= 1000:
                        total_quantity /= 1000
                        primary_unit = 'kg'
                elif primary_unit.lower() in ['ml', 'l', 'liter', 'dl']:
                    primary_unit = 'ml'
                    if total_quantity >= 1000:
                        total_quantity /= 1000
                        primary_unit = 'l'

                if total_quantity > 0:
                    deduplicated.append({
                        'ingredient': ingredient_key.title(),
                        'quantity': round(total_quantity, 2),
                        'unit': primary_unit,
                        'allergens': list(data['allergens'])
                    })

        return sorted(deduplicated, key=lambda x: x['ingredient'])

    def categorize_ingredients(self, ingredients: List[Dict]) -> Dict[str, List[Dict]]:
        categorized = {
            'Proteins': [],
            'Vegetables': [],
            'Dairy': [],
            'Pantry': [],
            'Herbs & Spices': [],
            'Other': []
        }

        for ingredient in ingredients:
            ing_name = ingredient['ingredient'].lower()
            assigned = False

            for category, keywords in INGREDIENT_CATEGORIES.items():
                if any(keyword in ing_name for keyword in keywords):
                    categorized[category].append(ingredient)
                    assigned = True
                    break

            if not assigned:
                categorized['Other'].append(ingredient)

        return categorized

    def _normalize_ingredients(self, ingredients: List[Dict]) -> List[Dict]:
        """Convert recipe pack format to standard format."""
        normalized = []
        for ing in ingredients:
            if not ing:
                continue
            name = ing.get('name', '')
            if isinstance(name, dict):
                name = name.get('en') or name.get('no') or ''
            unit = ing.get('unit', '')
            if isinstance(unit, dict):
                unit = unit.get('en') or unit.get('no') or ''
            normalized.append({
                'name': name,
                'quantity': ing.get('amount', 0),
                'unit': unit,
                'category': ing.get('category', 'Other')
            })
        return normalized

    def deduplicate_from_recipes(self, recipe_ids: List[str]) -> Dict:
        all_ingredients = []

        for recipe_id in recipe_ids:
            recipe = next((r for r in self.recipes_db if r['id'] == recipe_id), None)
            if recipe:
                ingredients = recipe.get('ingredients_included', [])
                if not ingredients:
                    ingredients = self._normalize_ingredients(recipe.get('ingredients', []))
                all_ingredients.extend(ingredients)

        deduplicated = self.deduplicate_ingredients(all_ingredients)
        categorized = self.categorize_ingredients(deduplicated)

        return {
            'total_ingredients': len(all_ingredients),
            'deduplicated_count': len(deduplicated),
            'shopping_list': categorized
        }


def test_deduplicator():
    logger.info("Testing deduplicator with sample recipes...")

    deduplicator = IngredientDeduplicator(fuzzy_threshold=90)

    if not deduplicator.load_recipes(DATA_DIR / 'recipes_db.json'):
        logger.warning("No recipes database found. Skipping integration test.")
        return

    if len(deduplicator.recipes_db) < 5:
        logger.info(f"Only {len(deduplicator.recipes_db)} recipes available. Testing with all.")
        recipe_ids = [r['id'] for r in deduplicator.recipes_db[:5]]
    else:
        recipe_ids = [deduplicator.recipes_db[i]['id'] for i in range(5)]

    result = deduplicator.deduplicate_from_recipes(recipe_ids)

    logger.info(f"\n=== DEDUPLICATION TEST ===")
    logger.info(f"Input ingredients: {result['total_ingredients']}")
    logger.info(f"Deduplicated: {result['deduplicated_count']}")
    logger.info(f"\nShopping list by category:")

    for category, items in result['shopping_list'].items():
        if items:
            logger.info(f"\n{category}:")
            for item in items:
                logger.info(f"  - {item['ingredient']}: {item['quantity']} {item['unit']}")

    return result


if __name__ == '__main__':
    test_deduplicator()
