#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import json
import logging
import re
from pathlib import Path
from typing import List, Dict, Tuple
from collections import defaultdict

try:
    from rapidfuzz import distance
    # Wrapper to match old fuzzywuzzy API
    class FuzzWrapper:
        @staticmethod
        def token_sort_ratio(a, b):
            return distance.Levenshtein.normalized_similarity(a, b) * 100
    fuzz = FuzzWrapper()
except ImportError:
    fuzz = None
    logging.warning("rapidfuzz not installed. Install with: pip install rapidfuzz")

logger = logging.getLogger(__name__)

# Setup logging with safe directory creation
log_dir = Path(__file__).parent.parent / "logs"
try:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "deduplicator.log")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
except Exception:
    pass
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
    'pieces': {'to_base': 1, 'base': 'stk'},
    'pcs': {'to_base': 1, 'base': 'stk'},
    'clove': {'to_base': 1, 'base': 'stk'},
    'slice': {'to_base': 1, 'base': 'stk'},
}

# Cutting/prep descriptors that show up appended to ingredient names in recipe
# data (e.g. "Gulrot, i skiver" / "Carrot, sliced") - these describe how to
# prepare the ingredient for the recipe, not something you can buy pre-made,
# so they need to be stripped before the name reaches the shopping list.
PREP_DESCRIPTOR_WORDS = [
    # Norwegian
    'i skiver', 'tynne skiver', 'skiver', 'i biter', 'biter', 'i terninger',
    'terninger', 'strimler', 'i strimler', 'revet', 'raspet', 'hakket',
    'fint hakket', 'grovhakket', 'knust', 'moset', 'skåret', 'kuttet', 'tynt',
    # English
    'thin slices', 'thinly sliced', 'sliced', 'slices', 'diced', 'chopped',
    'finely chopped', 'roughly chopped', 'grated', 'shredded', 'minced',
    'cubed', 'crushed', 'mashed', 'cut',
]

_PREP_PAREN_RE = re.compile(
    r'\(\s*(?:' + '|'.join(re.escape(w) for w in PREP_DESCRIPTOR_WORDS) + r')\s*\)',
    re.IGNORECASE,
)
_PREP_SUFFIX_RE = re.compile(
    r',\s*(?:' + '|'.join(re.escape(w) for w in PREP_DESCRIPTOR_WORDS) + r')\s*$',
    re.IGNORECASE,
)


# Canonical Norwegian unit strings for the messy/English variants that show
# up in imported recipe data. Keys are lowercased for matching; values are
# the exact string to normalize to.
UNIT_MAP_NO = {
    'tbsp': 'ss',
    'tsp': 'ts',
    'spiseskjeer': 'ss',
    'spiseskje': 'ss',
    'teskje': 'ts',
    'teskjeer': 'ts',
    'tsk': 'ts',
    'spsk': 'ss',
    'after taste': 'etter smak',
    'to taste': 'etter smak',
    'efter smak': 'etter smak',
    'tablespoons': 'ss',
    'teaspoons': 'ts',
    'tablespoon': 'ss',
    'teaspoon': 'ts',
    'medium': 'middels',
    'small': 'liten',
    'large': 'stor',
    'bunch': 'bunt',
    'skivor': 'skiver',
    'pcs': 'stk',
    'piece': 'stk',
    'pieces': 'stk',
    'clove': 'fedd',
    'cloves': 'fedd',
}


def normalize_no_unit(unit) -> object:
    """Normalize a recipe ingredient's Norwegian unit string to a canonical
    form (e.g. "tbsp" -> "ss"). Works on both the bilingual dict shape
    ({'no': ..., 'en': ...}) and a plain string; returns the same shape it
    was given. Non-string/dict input is returned unchanged."""
    if isinstance(unit, dict):
        no_val = (unit.get('no') or '').strip()
        mapped = UNIT_MAP_NO.get(no_val.lower())
        if mapped and no_val != mapped:
            unit = dict(unit)
            unit['no'] = mapped
        return unit
    if isinstance(unit, str):
        mapped = UNIT_MAP_NO.get(unit.strip().lower())
        return mapped if mapped else unit
    return unit


def strip_prep_descriptors(name: str) -> str:
    """Remove cutting/prep instructions from an ingredient name, e.g.
    "Gulrot, i skiver" -> "Gulrot", "Cucumber (thin slices)" -> "Cucumber".
    Leaves names without a recognized prep descriptor untouched."""
    if not name:
        return name
    cleaned = _PREP_PAREN_RE.sub('', name)
    cleaned = _PREP_SUFFIX_RE.sub('', cleaned)
    return cleaned.strip().rstrip(',').strip()

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
                # Load from both English and Norwegian pantry lists
                en_staples = data.get('pantry_staples_english', [])
                no_staples = data.get('pantry_staples_norwegian', [])
                staples = [s.lower().strip() for s in en_staples + no_staples]
                logger.info(f"Loaded {len(staples)} pantry staples (EN: {len(en_staples)}, NO: {len(no_staples)})")
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

        # Quick exact match first
        if ingredient_lower in self.pantry_staples:
            logger.info(f"✓ EXACT MATCH: '{ingredient_name}' is pantry staple")
            return True

        # Remove parenthetical notes like "(fresh or dried)" or "(optional)"
        ingredient_clean = ingredient_lower.split('(')[0].strip()
        if ingredient_clean in self.pantry_staples:
            logger.info(f"✓ MATCH (cleaned): '{ingredient_name}' → '{ingredient_clean}' (pantry staple)")
            return True

        # For multi-part ingredients like "Salt and pepper", check if ANY part matches
        # Split by common separators and check each part
        parts = ingredient_clean.replace(' and ', '|').replace(', ', '|').split('|')
        for part in parts:
            part_clean = part.strip()
            if part_clean in self.pantry_staples:
                logger.info(f"✓ PARTIAL MATCH: '{ingredient_name}' contains '{part_clean}' (pantry staple)")
                return True

        # Fuzzy match for close variants (threshold 70)
        for staple in self.pantry_staples:
            match, score = self.fuzzy_match(ingredient_clean, [staple])
            if score >= 70:
                logger.info(f"✓ FUZZY MATCH: '{ingredient_name}' → '{staple}' (score: {score})")
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
        logger.info(f"deduplicate_ingredients called with {len(ingredient_list)} ingredients")

        for ingredient in ingredient_list:
            if not ingredient.get('name'):
                continue

            name = strip_prep_descriptors(ingredient['name'].strip())
            logger.info(f"  Checking ingredient: '{name}'")

            if self.is_pantry_staple(name):
                logger.info(f"  ✗ Filtered out pantry staple: {name}")
                continue

            name_lower = name.lower()

            best_key = name_lower
            best_score = 0

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

            # Use lower threshold (70) to catch singular/plural variants
            if best_score < 70:
                best_key = name_lower
            else:
                logger.info(f"  ✓ Merged '{name}' with existing '{best_key}' (score: {best_score})")

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
                    elif total_quantity >= 100:
                        # More natural for cooking/shopping than a raw ml count
                        # (e.g. 300 ml milk -> 3 dl milk).
                        total_quantity /= 100
                        primary_unit = 'dl'
                elif primary_unit.lower() in ['stk', 'piece', 'pieces', 'pcs']:
                    primary_unit = 'pieces'

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
        """Build a shopping list from recipes as written - no serving-size
        scaling. Users can edit a recipe's own ingredient list directly if
        they want to adjust quantities for their household size."""
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
