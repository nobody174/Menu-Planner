#
# Pi-Menu - Hello Fresh Scraper v4
# Uses JSON-LD structured data (reliable, no CSS class hacks)
# Doubles ingredient quantities for 4 persons (JSON-LD always gives 2P data)
# Cleans instruction text to show 4P values from [2P | 4P] format
#

import asyncio
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional
import sys
import html

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import RECIPES_DB_PATH, LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'scraper_v4.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

from playwright.async_api import async_playwright


CATEGORY_PAGES = {
    "Familie": "https://www.hellofresh.no/recipes/familie",
    "Populære": "https://www.hellofresh.no/recipes/mest-populaere-oppskrifter",
    "Rask Middag": "https://www.hellofresh.no/recipes/rask-mat",
    "Pasta": "https://www.hellofresh.no/recipes/pasta-oppskrifter",
    "Japansk": "https://www.hellofresh.no/recipes/japanske-oppskrifter",
    "Fisk": "https://www.hellofresh.no/recipes/fiske-oppskrifter",
    "Lavkarbo": "https://www.hellofresh.no/recipes/lavkarbo-oppskrifter",
    "Vegetar": "https://www.hellofresh.no/recipes/vegetar-oppskrifter",
    "Vegansk": "https://www.hellofresh.no/recipes/veganske-oppskrifter",
    "Enkelt": "https://www.hellofresh.no/recipes/enkle-oppskrifter",
}

UNIT_PATTERN = r'(g|ml|stk|ts|ss|dl|l|pakke|pk|boks|pose|neve|klype|strimler?|skive[r]?|plate[r]?)'
FRACTION_MAP = {'½': 0.5, '¼': 0.25, '¾': 0.75, '⅓': 0.333, '⅔': 0.667}


def generate_id(title: str) -> str:
    rid = title.lower()
    for c, r in [('æ', 'ae'), ('ø', 'oe'), ('å', 'aa')]:
        rid = rid.replace(c, r)
    rid = re.sub(r'[^a-z0-9\s-]', '', rid)
    rid = re.sub(r'\s+', '-', rid.strip())
    return f"hf-{rid[:60]}"


def parse_quantity(qty_str: str) -> float:
    """Parse quantity string like '250', '1/2', '½', '1.5' into float"""
    qty_str = qty_str.strip()
    # Fraction characters
    for char, val in FRACTION_MAP.items():
        if char in qty_str:
            # Handle mixed like "1½"
            parts = qty_str.split(char)
            whole = float(parts[0]) if parts[0].strip() else 0
            return whole + val

    # Fraction notation like 1/2
    if '/' in qty_str:
        parts = qty_str.split('/')
        try:
            return float(parts[0]) / float(parts[1])
        except:
            return 0

    try:
        return float(qty_str.replace(',', '.'))
    except:
        return 0


def double_quantity(qty: float) -> float:
    """Double a quantity for 4 persons, keeping clean numbers"""
    result = qty * 2
    if result == int(result):
        return int(result)
    return round(result, 1)


def format_quantity(qty) -> str:
    """Format quantity for display"""
    if qty == int(qty):
        return str(int(qty))
    return str(qty)


def parse_ingredient_string(ing_str: str) -> Dict:
    """
    Parse ingredient string like:
    '250 g Kjøttdeig av storfe'
    '1 pakke Spaghetti'
    '½ stk Squash'
    '1 stk Egg (steg 2)'  <- not included in kit
    'Salt (steg 2)'       <- not included, no quantity
    """
    # Remove annotations like (steg X) and trailing whitespace
    text = re.sub(r'\s*\(steg\s*\d+\)\s*', '', ing_str).strip()

    # Detect "not included" items - those with (steg N) are pantry items
    is_pantry = bool(re.search(r'\(steg\s*\d+\)', ing_str))

    # Try to parse: QUANTITY UNIT NAME
    match = re.match(
        r'^([\d.,/½¼¾⅓⅔]+)\s+' + UNIT_PATTERN + r'\s+(.+)$',
        text,
        re.IGNORECASE
    )

    if match:
        raw_qty = match.group(1)
        unit = match.group(2)
        name = match.group(3).strip()
        quantity = parse_quantity(raw_qty)
        return {
            'quantity': quantity,
            'unit': unit,
            'name': name,
            'allergens': [],
            'is_pantry': is_pantry
        }

    # Try: QUANTITY (no unit) NAME — e.g. "2 Hvitløk"
    match2 = re.match(r'^([\d.,/½¼¾⅓⅔]+)\s+(.+)$', text, re.IGNORECASE)
    if match2:
        raw_qty = match2.group(1)
        name = match2.group(2).strip()
        # If name starts with a unit word, it was matched wrong - skip
        quantity = parse_quantity(raw_qty)
        return {
            'quantity': quantity,
            'unit': 'stk',
            'name': name,
            'allergens': [],
            'is_pantry': is_pantry
        }

    # No quantity found - just a name
    return {
        'quantity': 0,
        'unit': '',
        'name': text,
        'allergens': [],
        'is_pantry': is_pantry
    }


def clean_instruction_for_4p(text: str) -> str:
    """
    Replace 2P/4P markers with 4P values:
    '[1/2 stk, 2P]' -> '[1 stk]'  (double the 2P value)
    '[value | 4P-value]' -> '4P-value'
    '[1 dl | 2 dl]' -> '2 dl'
    """
    # Strip HTML tags and decode HTML entities
    text = re.sub(r'<[^>]+>', '\n', text)
    text = html.unescape(text)

    # Replace [2P-value | 4P-value] -> 4P-value
    # e.g. [1 ss | 2 ss] -> 2 ss
    def replace_pipe(m):
        parts = m.group(1).split('|')
        if len(parts) == 2:
            return parts[1].strip()
        return m.group(0)

    text = re.sub(r'\[([^\]]+\|[^\]]+)\]', replace_pipe, text)

    # Remove remaining markers like [1/2 stk, 2P] - these are 2-person labels
    # We double them for 4P display
    def replace_2p_marker(m):
        content = m.group(1)
        # Remove ", 2P" suffix
        content = re.sub(r',?\s*2P\s*$', '', content, flags=re.IGNORECASE).strip()
        return f"[{content}]"  # Keep the quantity but remove the 2P tag

    text = re.sub(r'\[([^\]]+,\s*2P)\]', replace_2p_marker, text, flags=re.IGNORECASE)

    # Clean up extra whitespace and empty lines
    lines = [line.strip() for line in text.split('\n')]
    lines = [line for line in lines if line]
    return '\n'.join(lines)


def extract_recipe_from_ld(ld_data: dict, url: str, category: str) -> Optional[Dict]:
    """Extract recipe from JSON-LD Recipe object"""
    try:
        title = ld_data.get('name', '').strip()
        if not title:
            return None

        # Clean encoding issues
        title = html.unescape(title)

        subtitle = html.unescape(ld_data.get('description', '') or '')
        if len(subtitle) > 250:
            subtitle = subtitle[:250]

        # Time - ISO 8601 duration PT30M
        total_time = ld_data.get('totalTime', '') or ''
        time_minutes = 0
        m = re.search(r'(\d+)M', total_time)
        if m:
            time_minutes = int(m.group(1))

        # recipeYield - usually "2" meaning 2 persons
        recipe_yield = int(ld_data.get('recipeYield', 2) or 2)
        multiplier = 4 / recipe_yield  # Scale factor to reach 4 portions

        # Difficulty - not in JSON-LD, extract from page HTML
        difficulty = "Enkel"

        # Ingredients - parse and scale to 4 persons
        ingredients_included = []
        ingredients_not_included = []

        for ing_str in ld_data.get('recipeIngredient', []):
            ing_str = html.unescape(ing_str)
            ing = parse_ingredient_string(ing_str)

            # Scale quantity
            if ing['quantity'] > 0:
                scaled = ing['quantity'] * multiplier
                if scaled == int(scaled):
                    ing['quantity'] = int(scaled)
                else:
                    ing['quantity'] = round(scaled, 1)

            ing_out = {
                'quantity': ing['quantity'],
                'unit': ing['unit'],
                'name': ing['name'],
                'allergens': ing['allergens']
            }

            if ing['is_pantry']:
                ingredients_not_included.append(ing_out)
            else:
                ingredients_included.append(ing_out)

        # Instructions - clean HTML and 4P values
        instructions = []
        for i, step in enumerate(ld_data.get('recipeInstructions', []), 1):
            step_text = step.get('text', '') or step.get('description', '')
            step_name = step.get('name', '') or f"Steg {i}"
            step_name = html.unescape(step_name)

            if step_text:
                cleaned = clean_instruction_for_4p(step_text)
                if cleaned:
                    instructions.append({
                        'step': i,
                        'title': step_name,
                        'description': cleaned,
                        'image_path': None
                    })

        # Nutrition
        nutrition = ld_data.get('nutrition', {}) or {}
        calories_str = nutrition.get('calories', '') or ''
        calories = 0
        m = re.search(r'(\d+)', calories_str)
        if m:
            calories = int(m.group(1))

        # Rating
        rating_data = ld_data.get('aggregateRating', {}) or {}
        rating = float(rating_data.get('ratingValue', 0) or 0)
        rating_count = int(rating_data.get('reviewCount', 0) or 0)

        return {
            'id': generate_id(title),
            'title': title,
            'subtitle': subtitle,
            'category': category,
            'url': url,
            'rating': rating,
            'rating_count': rating_count,
            'time_minutes': time_minutes,
            'difficulty': difficulty,
            'calories': calories,
            'protein': nutrition.get('proteinContent', '0g'),
            'tags': [],
            'allergens': [],
            'description': subtitle,
            'ingredients_included': ingredients_included,
            'ingredients_not_included': ingredients_not_included,
            'instructions': instructions,
            'scraped_at': datetime.now().isoformat()
        }

    except Exception as e:
        logger.error(f"Error parsing JSON-LD: {e}", exc_info=True)
        return None


async def scrape_recipe(page, url: str, category: str) -> Optional[Dict]:
    """Scrape a single recipe page via JSON-LD"""
    try:
        logger.info(f"Loading: {url.split('/')[-1][:55]}")
        await page.goto(url, wait_until='networkidle', timeout=30000)
        await page.wait_for_timeout(1500)

        # Get all JSON-LD script tags
        ld_scripts = await page.evaluate('''() => {
            const scripts = document.querySelectorAll('script[type="application/ld+json"]');
            return Array.from(scripts).map(s => s.textContent);
        }''')

        # Also try to get difficulty from page (not in JSON-LD)
        difficulty = await page.evaluate('''() => {
            const text = document.body.innerText;
            if (text.includes('Vanskelig')) return 'Vanskelig';
            if (text.includes('Middels')) return 'Middels';
            return 'Enkel';
        }''')

        # Also get tags from page
        tags = await page.evaluate('''() => {
            const tagWords = ['RASK', 'SUPERRASK', 'VEGETAR', 'PLANTEBASERT', 'MELKEFRI', 'LAVKARBO', 'BARNEVENNLIG', 'GLUTENFRI', 'HVETEFRI'];
            const text = document.body.innerText.toUpperCase();
            return tagWords.filter(t => text.includes(t));
        }''')

        # Also get allergens from page (more complete than JSON-LD)
        allergens = await page.evaluate('''() => {
            const allergenWords = ['Gluten', 'Hvete', 'Melk', 'Egg', 'Fisk', 'Skalldyr', 'Nødder', 'Peanøtter', 'Sennep', 'Sesam', 'Soya', 'Lupiner', 'Bløtdyr'];
            const text = document.body.innerText;
            return allergenWords.filter(a => text.includes(a));
        }''')

        for ld_text in ld_scripts:
            try:
                ld_data = json.loads(ld_text)
                if ld_data.get('@type') == 'Recipe':
                    recipe = extract_recipe_from_ld(ld_data, url, category)
                    if recipe:
                        recipe['difficulty'] = difficulty
                        recipe['tags'] = tags
                        recipe['allergens'] = allergens
                        logger.info(f"OK: {recipe['title'][:45]} | {len(recipe['ingredients_included'])} ing | {len(recipe['instructions'])} steps")
                        return recipe
            except json.JSONDecodeError:
                continue

        logger.warning(f"No Recipe JSON-LD found at: {url}")
        return None

    except Exception as e:
        logger.error(f"Error scraping {url}: {e}")
        return None


async def gather_recipe_urls(page, category_url: str) -> List[str]:
    """Gather recipe URLs from category page, scrolling to load lazy content"""
    logger.info(f"Loading category: {category_url}")
    await page.goto(category_url, wait_until='networkidle', timeout=30000)
    await page.wait_for_timeout(3000)

    # Scroll aggressively to trigger lazy-loading of recipe cards
    prev_count = 0
    for scroll_round in range(20):
        await page.evaluate('window.scrollBy(0, 700)')
        await page.wait_for_timeout(700)

        # Check if we're finding more recipes each round
        if scroll_round % 4 == 3:
            links = await page.query_selector_all('a[href]')
            count = 0
            for link in links:
                href = await link.get_attribute('href') or ''
                if re.search(r'/recipes/[a-z0-9-]+-[0-9a-f]{8,}', href):
                    count += 1
            if count > 0 and count == prev_count:
                break  # No new recipes loading, stop
            prev_count = count

    await page.wait_for_timeout(1000)

    urls = set()
    links = await page.query_selector_all('a[href]')
    for link in links:
        href = await link.get_attribute('href')
        if not href:
            continue
        if href.startswith('/'):
            href = f"https://www.hellofresh.no{href}"
        # Recipe pages have a 8+ hex char ID at the end (some have shorter IDs)
        if re.search(r'/recipes/[a-z0-9-]+-[0-9a-f]{8,}', href):
            urls.add(href)

    logger.info(f"Found {len(urls)} recipe URLs")
    return list(urls)


async def test_known_urls():
    """Test with 4 known URLs"""
    test_urls = [
        ("https://www.hellofresh.no/recipes/kremet-spaghetti-og-kjottboller-66bb32afa68bc448dd44e5fa", "Familie"),
        ("https://www.hellofresh.no/recipes/kremet-mais-og-bacon-chowder-6706433802cdf0b40ec38724", "Familie"),
        ("https://www.hellofresh.no/recipes/succotash-kidneybonnebowl-670f9842285f0d4d63559bb5", "Rask Middag"),
        ("https://www.hellofresh.no/recipes/kremet-toscansk-laks-og-gratinerte-tomater-68ac60317e1f6c64ca6822e4", "Familie"),
    ]

    recipes = []
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)
        for url, category in test_urls:
            page = await browser.new_page()
            try:
                recipe = await scrape_recipe(page, url, category)
                if recipe:
                    recipes.append(recipe)
            finally:
                await page.close()
            await asyncio.sleep(0.5)
        await browser.close()

    return recipes


async def scrape_all_categories(max_per_category: int = 50):
    """Scrape all category pages"""
    all_recipes = []
    processed_urls = set()

    async with async_playwright() as pw:
        browser = await pw.chromium.launch(headless=True)

        for category, category_url in CATEGORY_PAGES.items():
            logger.info(f"\n{'='*60}\nCategory: {category}\n{'='*60}")

            page = await browser.new_page()
            try:
                urls = await gather_recipe_urls(page, category_url)
            finally:
                await page.close()

            count = 0
            for url in urls:
                if url in processed_urls or count >= max_per_category:
                    continue
                page = await browser.new_page()
                try:
                    recipe = await scrape_recipe(page, url, category)
                    if recipe:
                        all_recipes.append(recipe)
                        processed_urls.add(url)
                        count += 1
                finally:
                    await page.close()
                await asyncio.sleep(0.3)

            logger.info(f"Category {category}: scraped {count} recipes")

        await browser.close()

    return all_recipes


async def main():
    import argparse
    parser = argparse.ArgumentParser(description='Hello Fresh Norway scraper v4')
    parser.add_argument('--all', action='store_true', help='Scrape all categories')
    parser.add_argument('--max', type=int, default=50, help='Max recipes per category')
    parser.add_argument('--test', action='store_true', help='Test with 4 known URLs (default)')
    args = parser.parse_args()

    logger.info("="*60)
    logger.info("HELLO FRESH SCRAPER v4 (JSON-LD)")
    logger.info("="*60)

    if args.all:
        logger.info(f"Scraping ALL categories (max {args.max} each)...")
        recipes = await scrape_all_categories(max_per_category=args.max)
    else:
        logger.info("Testing with 4 known URLs...")
        recipes = await test_known_urls()

    logger.info(f"\n{'='*60}")
    logger.info(f"Total scraped: {len(recipes)} recipes")
    for r in recipes:
        logger.info(f"  {r['title'][:50]} | {len(r['ingredients_included'])} ing | {len(r['instructions'])} steps")

    if recipes:
        # Load existing recipes
        existing = []
        if RECIPES_DB_PATH.exists():
            with open(RECIPES_DB_PATH, 'r', encoding='utf-8') as f:
                existing = json.load(f)

        # Merge, avoiding duplicates by id
        existing_ids = {r['id'] for r in existing}
        new_recipes = [r for r in recipes if r['id'] not in existing_ids]

        # Replace existing with updated versions if same id
        updated = [r for r in existing if r['id'] not in {nr['id'] for nr in new_recipes}]
        all_db = updated + new_recipes + [r for r in recipes if r['id'] in existing_ids]

        # Actually: just overwrite if we have new data for the same id
        id_to_recipe = {r['id']: r for r in existing}
        for r in recipes:
            id_to_recipe[r['id']] = r  # Replace with fresh scraped

        final = list(id_to_recipe.values())

        with open(RECIPES_DB_PATH, 'w', encoding='utf-8') as f:
            json.dump(final, f, indent=2, ensure_ascii=False)

        logger.info(f"Saved {len(final)} total recipes ({len(new_recipes)} new) to {RECIPES_DB_PATH}")

if __name__ == '__main__':
    asyncio.run(main())
