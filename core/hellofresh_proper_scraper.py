import json
import logging
import sys
import re
import asyncio
from pathlib import Path
from typing import List, Dict
from datetime import datetime

from playwright.async_api import async_playwright

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCRAPER_RATE_LIMIT,
    RECIPE_CATEGORIES,
    RECIPES_DB_PATH,
    LOGS_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class HelloFreshScraper:
    def __init__(self):
        self.recipes = []

    async def scrape_category(self, category_name: str, url: str) -> List[Dict]:
        """Scrape recipes from a Hello Fresh category page"""
        logger.info(f"Scraping {category_name} from {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                logger.info(f"  Page loaded, waiting for content...")
                await page.wait_for_timeout(2000)  # Wait for JS to render

                # Get all page text
                all_text = await page.inner_text('body')
                if not all_text:
                    logger.warning(f"  No text content found on page")
                    await browser.close()
                    return []

                # Parse recipes from the text content
                recipes = self._parse_recipes_from_text(all_text, category_name, url)
                logger.info(f"  Extracted {len(recipes)} recipes from {category_name}")

                await browser.close()
                return recipes

            except Exception as e:
                logger.error(f"  Failed to scrape {url}: {e}")
                try:
                    await browser.close()
                except:
                    pass
                return []

    def _parse_recipes_from_text(self, text: str, category: str, page_url: str) -> List[Dict]:
        """Parse recipes from page text content"""
        recipes = []
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            # Look for recipe title pattern (usually followed by subtitle and time info)
            # Skip navigation/header elements
            if self._is_likely_recipe_title(line, i, lines):
                try:
                    recipe = self._extract_recipe(line, i, lines, category)
                    if recipe:
                        recipes.append(recipe)
                        logger.debug(f"    Found: {recipe['title']}")
                        i += 3  # Skip ahead to avoid duplicates
                    else:
                        i += 1
                except:
                    i += 1
            else:
                i += 1

        return recipes

    def _is_likely_recipe_title(self, line: str, idx: int, lines: List[str]) -> bool:
        """Check if a line looks like a recipe title"""
        # Skip if too short
        if len(line) < 5 or len(line) > 150:
            return False

        # Skip known non-recipe lines
        non_recipe_keywords = [
            'Skip to main', 'V�re', 'Slik', 'S�k', 'Logg', 'Oppskrift', 'Alle',
            'mest popul', 'utforsk', 'spar', 'matkasse', 'gavekort', 'ingrediens',
            'leveringsomr', 'leverand', 'b�rekraft', 'planlegger', 'kassene'
        ]

        for keyword in non_recipe_keywords:
            if keyword.lower() in line.lower():
                return False

        # Check if next line looks like a subtitle (shorter, descriptive)
        if idx + 1 < len(lines):
            next_line = lines[idx + 1].strip()
            if 'med ' in next_line.lower() or len(next_line) < 100 and len(next_line) > 5:
                # Check if line after that has time info
                if idx + 2 < len(lines):
                    time_line = lines[idx + 2].strip()
                    if self._has_time_info(time_line):
                        return True

        return False

    def _has_time_info(self, line: str) -> bool:
        """Check if a line contains cooking time info"""
        return bool(re.search(r'\d+\s*(min|minutter|time)', line.lower()))

    def _extract_recipe(self, title: str, idx: int, lines: List[str], category: str) -> Dict:
        """Extract a complete recipe from title and following lines"""
        if idx + 2 >= len(lines):
            return None

        subtitle = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        time_line = lines[idx + 2].strip() if idx + 2 < len(lines) else ""

        # Extract time
        time_match = re.search(r'(\d+)\s*(min|minutter)', time_line.lower())
        time_minutes = int(time_match.group(1)) if time_match else 0

        # Extract difficulty
        difficulty = "Enkel"
        if "medium" in time_line.lower():
            difficulty = "Medium"
        elif "vanskelig" in time_line.lower() or "hard" in time_line.lower():
            difficulty = "Vanskelig"

        # Create recipe ID from title
        recipe_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        recipe_id = f'hf-{recipe_id[:40]}'

        recipe = {
            'id': recipe_id,
            'title': title,
            'subtitle': subtitle,
            'category': category,
            'url': '',  # We could parse links but content-based is safer
            'rating': 0,
            'rating_count': 0,
            'time_minutes': time_minutes,
            'difficulty': difficulty,
            'tags': ["RASK"] if time_minutes < 25 else [],
            'allergens': [],
            'description': subtitle,
            'ingredients_included': [],
            'ingredients_not_included': [],
            'instructions': [],
            'scraped_at': datetime.now().isoformat()
        }

        return recipe

    async def scrape_all_categories(self) -> List[Dict]:
        """Scrape recipes from all configured categories"""
        logger.info("=" * 60)
        logger.info("STARTING HELLO FRESH SCRAPER")
        logger.info("=" * 60)

        all_recipes = []
        for category_name, url in RECIPE_CATEGORIES.items():
            recipes = await self.scrape_category(category_name, url)
            all_recipes.extend(recipes)
            logger.info(f"Category {category_name}: {len(recipes)} recipes")

        logger.info(f"\nTotal recipes scraped: {len(all_recipes)}")
        return all_recipes

    def save_recipes(self, recipes: List[Dict]) -> bool:
        """Save recipes to the recipes database"""
        try:
            # Load existing recipes
            existing = []
            if RECIPES_DB_PATH.exists():
                with open(RECIPES_DB_PATH, 'r', encoding='utf-8') as f:
                    existing = json.load(f)

            # Merge with new recipes (avoid duplicates by ID)
            existing_ids = {r['id'] for r in existing}
            new_recipes = [r for r in recipes if r['id'] not in existing_ids]

            merged = existing + new_recipes

            # Save merged recipes
            RECIPES_DB_PATH.parent.mkdir(parents=True, exist_ok=True)
            with open(RECIPES_DB_PATH, 'w', encoding='utf-8') as f:
                json.dump(merged, f, ensure_ascii=False, indent=2)

            logger.info(f"Saved {len(merged)} total recipes ({len(new_recipes)} new from Hello Fresh)")
            return True
        except Exception as e:
            logger.error(f"Failed to save recipes: {e}")
            return False

    async def run(self, save: bool = True) -> List[Dict]:
        """Run the complete scraper"""
        recipes = await self.scrape_all_categories()

        if save:
            self.save_recipes(recipes)

        logger.info("=" * 60)
        logger.info(f"SCRAPER COMPLETE: {len(recipes)} new recipes")
        logger.info("=" * 60)

        return recipes


async def test_scraper():
    scraper = HelloFreshScraper()
    recipes = await scraper.run(save=True)
    return recipes


if __name__ == '__main__':
    asyncio.run(test_scraper())
