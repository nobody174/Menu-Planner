import json
import logging
import sys
from pathlib import Path
from typing import List, Dict
from datetime import datetime
import asyncio

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

class HelloFreshPlaywrightScraper:
    def __init__(self):
        self.recipes = []

    async def scrape_category(self, category_name: str, url: str) -> List[Dict]:
        """Scrape recipes from a Hello Fresh category page using Playwright"""
        logger.info(f"Scraping {category_name} from {url}")

        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()

            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                logger.info(f"  Page loaded successfully")

                # Wait for recipe cards to load
                try:
                    await page.wait_for_selector('a[href*="/recipes/"]', timeout=10000)
                except:
                    logger.warning(f"  No recipe cards found on page")
                    await browser.close()
                    return []

                # Get all recipe cards
                recipe_cards = await page.query_selector_all('a[href*="/recipes/"]')
                logger.info(f"  Found {len(recipe_cards)} recipe card links")

                recipes = []
                seen_urls = set()

                for i, card in enumerate(recipe_cards):
                    try:
                        # Get the href
                        href = await card.get_attribute('href')
                        if not href or href in seen_urls:
                            continue

                        seen_urls.add(href)

                        # Skip category links (they end with #)
                        if href.endswith('#'):
                            continue

                        # Get the text content
                        text = await card.inner_text()
                        if not text or len(text.strip()) < 3:
                            continue

                        # Extract recipe ID from URL
                        recipe_id = href.strip('/').split('/')[-1]
                        if not recipe_id or recipe_id == 'recipes':
                            continue

                        # Create recipe entry
                        recipe = {
                            'id': f'hf-{recipe_id}',
                            'title': text.strip(),
                            'subtitle': '',
                            'category': category_name,
                            'url': f'https://www.hellofresh.no{href}' if href.startswith('/') else href,
                            'rating': 0,
                            'rating_count': 0,
                            'time_minutes': 0,
                            'difficulty': 'Enkel',
                            'tags': [],
                            'allergens': [],
                            'description': '',
                            'ingredients_included': [],
                            'ingredients_not_included': [],
                            'instructions': [],
                            'scraped_at': datetime.now().isoformat()
                        }

                        recipes.append(recipe)
                        logger.info(f"    [{i+1}] {text.strip()}")

                    except Exception as e:
                        logger.debug(f"  Error parsing card: {e}")
                        continue

                logger.info(f"  Successfully scraped {len(recipes)} recipes from {category_name}")
                await browser.close()
                return recipes

            except Exception as e:
                logger.error(f"  Failed to scrape {url}: {e}")
                await browser.close()
                return []

    async def scrape_all_categories(self) -> List[Dict]:
        """Scrape recipes from all configured categories"""
        logger.info("=" * 60)
        logger.info("STARTING HELLO FRESH PLAYWRIGHT SCRAPER")
        logger.info("=" * 60)

        all_recipes = []
        for category_name, url in RECIPE_CATEGORIES.items():
            recipes = await self.scrape_category(category_name, url)
            all_recipes.extend(recipes)
            logger.info(f"Category {category_name}: {len(recipes)} recipes\n")

        logger.info(f"Total recipes scraped: {len(all_recipes)}")
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
        logger.info(f"SCRAPER COMPLETE: {len(recipes)} new recipes from Hello Fresh")
        logger.info("=" * 60)

        return recipes


async def test_scraper():
    """Test the scraper"""
    scraper = HelloFreshPlaywrightScraper()
    recipes = await scraper.run(save=True)
    return recipes


if __name__ == '__main__':
    asyncio.run(test_scraper())
