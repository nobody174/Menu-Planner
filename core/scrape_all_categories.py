import asyncio
import json
import logging
import re
from pathlib import Path
from datetime import datetime
from typing import Dict, List

from playwright.async_api import async_playwright

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import LOGS_DIR

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'full_scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

MENUS_DIR = Path(__file__).parent.parent / 'data' / 'menus'


class FullHelloFreshScraper:
    def __init__(self):
        self.categories = {}

    async def find_all_categories(self) -> Dict[str, str]:
        """Find all recipe categories available on Hello Fresh"""
        logger.info("Finding all Hello Fresh categories...")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto("https://www.hellofresh.no/recipes", wait_until="domcontentloaded")
                await page.wait_for_timeout(2000)

                # Get all recipe category links
                category_links = await page.query_selector_all('a[href*="/recipes/"]')

                categories = {}
                for link in category_links:
                    href = await link.get_attribute('href')
                    text = await link.inner_text()

                    if href and '/recipes/' in href and text.strip():
                        # Skip the main /recipes page and pagination links
                        if href == '/recipes' or href.endswith('#') or 'page=' in href:
                            continue

                        # Clean up the category name - remove newlines and extra whitespace
                        category_name = ' '.join(text.strip().split())

                        # Filter out sub-categories (ingredient-based filters like "oppskrifter med X")
                        # Only keep main categories
                        if ('/vegetar-oppskrifter/' in href or
                            '?sort=' in href or
                            'oppskrifter med ' in category_name.lower() or
                            'oppskrifter:' in category_name.lower()):
                            continue

                        if len(category_name) > 3 and len(category_name) < 80:
                            full_url = f'https://www.hellofresh.no{href}' if href.startswith('/') else href
                            categories[category_name] = full_url

                logger.info(f"Found {len(categories)} categories")
                for name, url in sorted(categories.items()):
                    logger.info(f"  - {name}: {url}")

                await browser.close()
                return categories

            except Exception as e:
                logger.error(f"Failed to find categories: {e}")
                await browser.close()
                return {}

    async def scrape_category(self, category_name: str, url: str) -> List[Dict]:
        """Scrape all recipes from a category"""
        logger.info(f"Scraping: {category_name}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await page.wait_for_timeout(2000)

                # Get all text content
                all_text = await page.inner_text('body')
                recipes = self._parse_recipes_from_text(all_text)

                logger.info(f"  Extracted {len(recipes)} recipes")
                await browser.close()
                return recipes

            except Exception as e:
                logger.error(f"  Failed to scrape {category_name}: {e}")
                try:
                    await browser.close()
                except:
                    pass
                return []

    def _parse_recipes_from_text(self, text: str) -> List[Dict]:
        """Parse recipes from page text"""
        recipes = []
        lines = text.split('\n')

        i = 0
        while i < len(lines):
            line = lines[i].strip()

            if self._is_likely_recipe_title(line, i, lines):
                try:
                    recipe = self._extract_recipe(line, i, lines)
                    if recipe:
                        recipes.append(recipe)
                        i += 3
                    else:
                        i += 1
                except:
                    i += 1
            else:
                i += 1

        return recipes

    def _is_likely_recipe_title(self, line: str, idx: int, lines: List[str]) -> bool:
        """Check if line is a recipe title"""
        if len(line) < 5 or len(line) > 150:
            return False

        non_recipe_keywords = [
            'Skip', 'Våre', 'Slik', 'Søk', 'Logg', 'Oppskrift', 'Alle', 'populær',
            'utforsk', 'spar', 'matkasse', 'gavekort', 'ingrediens', 'leveringsomr',
            'leverandør', 'bærekraft', 'planlegger', 'kassene', 'meny', 'vegansk'
        ]

        for keyword in non_recipe_keywords:
            if keyword.lower() in line.lower():
                return False

        if idx + 2 < len(lines):
            next_line = lines[idx + 1].strip()
            time_line = lines[idx + 2].strip()
            if 'med ' in next_line.lower() and self._has_time_info(time_line):
                return True

        return False

    def _has_time_info(self, line: str) -> bool:
        """Check if line has time info"""
        return bool(re.search(r'\d+\s*(min|minutter|time)', line.lower()))

    def _extract_recipe(self, title: str, idx: int, lines: List[str]) -> Dict:
        """Extract recipe from title and following lines"""
        if idx + 2 >= len(lines):
            return None

        subtitle = lines[idx + 1].strip() if idx + 1 < len(lines) else ""
        time_line = lines[idx + 2].strip() if idx + 2 < len(lines) else ""

        time_match = re.search(r'(\d+)\s*(min|minutter)', time_line.lower())
        time_minutes = int(time_match.group(1)) if time_match else 0

        difficulty = "Enkel"
        if "medium" in time_line.lower():
            difficulty = "Medium"
        elif "vanskelig" in time_line.lower():
            difficulty = "Vanskelig"

        recipe_id = re.sub(r'[^a-z0-9]+', '-', title.lower()).strip('-')
        recipe_id = f'hf-{recipe_id[:40]}'

        return {
            'id': recipe_id,
            'title': title,
            'subtitle': subtitle,
            'time_minutes': time_minutes,
            'difficulty': difficulty,
            'tags': ["RASK"] if time_minutes < 25 else [],
            'description': subtitle,
            'scraped_at': datetime.now().isoformat()
        }

    async def run(self):
        """Run complete scraper"""
        logger.info("=" * 70)
        logger.info("FULL HELLO FRESH SCRAPER - SCRAPING ALL CATEGORIES")
        logger.info("=" * 70)

        # Find all categories
        categories = await self.find_all_categories()

        if not categories:
            logger.error("No categories found!")
            return

        # Scrape each category
        MENUS_DIR.mkdir(parents=True, exist_ok=True)

        total_recipes = 0
        for category_name, url in sorted(categories.items()):
            recipes = await self.scrape_category(category_name, url)

            if recipes:
                # Save recipes for this category
                category_dir = MENUS_DIR / category_name.replace('/', '_').replace('\\', '_')
                category_dir.mkdir(parents=True, exist_ok=True)

                recipes_file = category_dir / 'recipes.json'
                with open(recipes_file, 'w', encoding='utf-8') as f:
                    json.dump(recipes, f, ensure_ascii=False, indent=2)

                logger.info(f"  Saved to: {recipes_file}")
                total_recipes += len(recipes)

        logger.info("=" * 70)
        logger.info(f"COMPLETE: {len(categories)} categories, {total_recipes} total recipes")
        logger.info(f"Recipes stored in: {MENUS_DIR}")
        logger.info("=" * 70)


async def main():
    scraper = FullHelloFreshScraper()
    await scraper.run()


if __name__ == '__main__':
    asyncio.run(main())
