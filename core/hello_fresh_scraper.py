import json
import logging
import time
import sys
from pathlib import Path
from typing import List, Dict, Optional
from datetime import datetime

import requests
from bs4 import BeautifulSoup

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    SCRAPER_RATE_LIMIT,
    SCRAPER_TIMEOUT,
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
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.recipes = []

    def scrape_category(self, category_name: str, url: str) -> List[Dict]:
        """Scrape recipes from a Hello Fresh category page"""
        logger.info(f"Scraping {category_name} from {url}")

        try:
            response = self.session.get(url, timeout=SCRAPER_TIMEOUT)
            response.raise_for_status()
            time.sleep(SCRAPER_RATE_LIMIT)  # Respect server
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return []

        soup = BeautifulSoup(response.content, 'html.parser')
        recipes = []

        # Find recipe cards - Hello Fresh uses specific structure
        recipe_cards = soup.find_all('a', {'data-testid': 'recipe-card-link'})

        if not recipe_cards:
            logger.warning(f"No recipes found on {url}")
            return []

        for i, card in enumerate(recipe_cards):
            try:
                recipe = self._parse_recipe_card(card, category_name)
                if recipe:
                    recipes.append(recipe)
                    logger.info(f"  [{i+1}] {recipe['title']}")
            except Exception as e:
                logger.debug(f"Error parsing recipe card: {e}")
                continue

        logger.info(f"Found {len(recipes)} recipes in {category_name}")
        return recipes

    def _parse_recipe_card(self, card, category: str) -> Optional[Dict]:
        """Parse a single recipe card from Hello Fresh"""
        try:
            # Extract recipe link
            recipe_url = card.get('href', '')
            if not recipe_url:
                return None

            # Extract recipe ID from URL
            recipe_id = recipe_url.strip('/').split('/')[-1]

            # Find recipe title
            title_elem = card.find('h3', {'data-testid': 'recipe-card-title'})
            title = title_elem.text.strip() if title_elem else 'Unknown'

            # Find difficulty
            difficulty_elem = card.find('span', {'data-testid': 'recipe-card-difficulty'})
            difficulty = difficulty_elem.text.strip() if difficulty_elem else 'Enkel'

            # Find time
            time_elem = card.find('span', {'data-testid': 'recipe-card-time'})
            time_minutes = 0
            if time_elem:
                time_text = time_elem.text.strip()
                # Extract numbers from "25 min" format
                import re
                match = re.search(r'(\d+)', time_text)
                if match:
                    time_minutes = int(match.group(1))

            # Find rating
            rating_elem = card.find('span', {'data-testid': 'recipe-card-rating'})
            rating = 0
            if rating_elem:
                import re
                match = re.search(r'(\d+\.?\d*)', rating_elem.text)
                if match:
                    rating = float(match.group(1))

            recipe = {
                'id': f'hellofresh-{recipe_id}',
                'title': title,
                'subtitle': '',
                'category': category,
                'url': f'https://www.hellofresh.no{recipe_url}' if recipe_url.startswith('/') else recipe_url,
                'rating': rating,
                'rating_count': 0,
                'time_minutes': time_minutes,
                'difficulty': difficulty,
                'tags': [],
                'allergens': [],
                'description': '',
                'ingredients_included': [],
                'ingredients_not_included': [],
                'instructions': [],
                'scraped_at': datetime.now().isoformat()
            }

            return recipe
        except Exception as e:
            logger.debug(f"Error parsing recipe card: {e}")
            return None

    def scrape_all_categories(self) -> List[Dict]:
        """Scrape recipes from all configured categories"""
        logger.info("=" * 60)
        logger.info("STARTING HELLO FRESH SCRAPER")
        logger.info("=" * 60)

        all_recipes = []
        for category_name, url in RECIPE_CATEGORIES.items():
            recipes = self.scrape_category(category_name, url)
            all_recipes.extend(recipes)
            logger.info(f"Category {category_name}: {len(recipes)} recipes")

        logger.info(f"\nTotal recipes scraped: {len(all_recipes)}")
        return all_recipes

    def save_recipes(self, recipes: List[Dict]) -> bool:
        """Save recipes to the recipes database"""
        try:
            # Load existing recipes to avoid duplicates
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

            logger.info(f"Saved {len(merged)} total recipes ({len(new_recipes)} new)")
            return True
        except Exception as e:
            logger.error(f"Failed to save recipes: {e}")
            return False

    def run(self, save: bool = True) -> List[Dict]:
        """Run the complete scraper"""
        recipes = self.scrape_all_categories()

        if save:
            self.save_recipes(recipes)

        logger.info("=" * 60)
        logger.info(f"SCRAPER COMPLETE: {len(recipes)} new recipes")
        logger.info("=" * 60)

        return recipes


def test_scraper():
    """Test the scraper"""
    scraper = HelloFreshScraper()
    recipes = scraper.run(save=True)
    return recipes


if __name__ == '__main__':
    test_scraper()
