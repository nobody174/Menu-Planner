import os
import json
import time
import re
import logging
from pathlib import Path
from urllib.parse import urljoin, urlparse
from datetime import datetime
from typing import List, Dict, Optional

import requests
from bs4 import BeautifulSoup
from PIL import Image
from io import BytesIO

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

ORANGE_KEYWORDS = [
    'appelsin', 'oransje', 'orange', 'orange juice',
    'orange zest', 'orange marmelade', 'oransjemost'
]

BASE_URL = 'https://www.hellofresh.no'
RECIPE_CATEGORIES = {
    'Populære': 'https://www.hellofresh.no/recipes/mest-populaere-oppskrifter',
    'Familie': 'https://www.hellofresh.no/recipes/familie',
    'Rask Middag': 'https://www.hellofresh.no/recipes/rask-mat'
}

DATA_DIR = Path('data')
CACHE_DIR = DATA_DIR / 'recipes_cache'
DB_FILE = DATA_DIR / 'recipes_db.json'

CACHE_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)


class HelloFreshScraper:
    def __init__(self, request_delay: float = 2.0):
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
        self.request_delay = request_delay
        self.recipes_db = []
        self.skipped_recipes = []
        self.failed_recipes = []

    def fetch_url(self, url: str) -> Optional[str]:
        try:
            time.sleep(self.request_delay)
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.text
        except Exception as e:
            logger.error(f"Failed to fetch {url}: {e}")
            return None

    def fetch_image(self, url: str) -> Optional[bytes]:
        try:
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            return response.content
        except Exception as e:
            logger.error(f"Failed to fetch image {url}: {e}")
            return None

    def contains_orange(self, text: str) -> bool:
        if not text:
            return False
        text_lower = text.lower()
        return any(keyword in text_lower for keyword in ORANGE_KEYWORDS)

    def extract_recipe_links(self, listing_page: str, category_name: str) -> List[str]:
        soup = BeautifulSoup(listing_page, 'html.parser')
        recipe_links = []

        for link in soup.find_all('a', href=True):
            href = link.get('href')
            if href and '/recipes/' in href and 'mest-populaere' not in href and 'familie' not in href and 'rask-mat' not in href:
                if not href.startswith('http'):
                    href = urljoin(BASE_URL, href)
                if href not in recipe_links:
                    recipe_links.append(href)

        logger.info(f"Found {len(recipe_links)} recipe links in {category_name}")
        return recipe_links

    def download_image(self, url: str, recipe_id: str, step_num: int) -> Optional[str]:
        image_data = self.fetch_image(url)
        if not image_data:
            return None

        try:
            img = Image.open(BytesIO(image_data))
            recipe_cache = CACHE_DIR / recipe_id
            recipe_cache.mkdir(parents=True, exist_ok=True)

            image_path = recipe_cache / f'step-{step_num}.jpg'
            img.save(str(image_path), 'JPEG', quality=85)

            return str(image_path)
        except Exception as e:
            logger.error(f"Failed to process image {url}: {e}")
            return None

    def parse_recipe(self, recipe_html: str, recipe_url: str, category: str) -> Optional[Dict]:
        soup = BeautifulSoup(recipe_html, 'html.parser')

        try:
            recipe_id = recipe_url.split('/')[-1] or 'recipe'

            title_elem = soup.find('h1')
            title = title_elem.get_text(strip=True) if title_elem else 'Unknown'

            if self.contains_orange(title):
                logger.info(f"Skipped (orange): {title}")
                self.skipped_recipes.append({'id': recipe_id, 'reason': 'contains_orange', 'title': title})
                return None

            subtitle_elem = soup.find('h2')
            subtitle = subtitle_elem.get_text(strip=True) if subtitle_elem else ''

            rating = 0.0
            rating_count = 0
            rating_elem = soup.find(class_=re.compile(r'rating|stars'))
            if rating_elem:
                rating_text = rating_elem.get_text()
                numbers = re.findall(r'\d+\.?\d*', rating_text)
                if numbers:
                    rating = float(numbers[0]) if '.' in numbers[0] or len(numbers[0]) > 1 else int(numbers[0])
                if len(numbers) > 1:
                    rating_count = int(numbers[1].replace(',', ''))

            time_elem = soup.find(string=re.compile(r'\d+\s*(min|minutter)', re.I))
            time_minutes = 0
            if time_elem:
                time_match = re.search(r'(\d+)\s*(?:min|minutter)', str(time_elem), re.I)
                if time_match:
                    time_minutes = int(time_match.group(1))

            difficulty = 'Enkel'
            difficulty_elem = soup.find(string=re.compile(r'Enkel|Middels|Vanskelig'))
            if difficulty_elem:
                difficulty = difficulty_elem.strip()

            tags = []
            if time_minutes <= 25:
                tags.append('RASK')

            allergens = []
            allergen_elems = soup.find_all(class_=re.compile(r'allergen'))
            for elem in allergen_elems:
                allergen = elem.get_text(strip=True)
                if allergen and allergen not in allergens:
                    allergens.append(allergen)

            description = ''
            desc_elem = soup.find(class_=re.compile(r'description|intro'))
            if desc_elem:
                description = desc_elem.get_text(strip=True)

            if self.contains_orange(description):
                logger.info(f"Skipped (orange in description): {title}")
                self.skipped_recipes.append({'id': recipe_id, 'reason': 'orange_in_description', 'title': title})
                return None

            ingredients_included = []
            ingredients_not_included = []

            ingredient_elems = soup.find_all(class_=re.compile(r'ingredient'))
            for elem in ingredient_elems:
                ingredient_text = elem.get_text(strip=True)

                if self.contains_orange(ingredient_text):
                    logger.info(f"Skipped (orange ingredient): {title}")
                    self.skipped_recipes.append({'id': recipe_id, 'reason': 'orange_ingredient', 'title': title})
                    return None

                quantity_match = re.search(r'(\d+(?:,\d+)?)\s*([a-zæøå\s]+)?', ingredient_text, re.I)
                quantity = 0
                unit = ''
                name = ingredient_text

                if quantity_match:
                    quantity = float(quantity_match.group(1).replace(',', '.'))
                    unit = quantity_match.group(2).strip() if quantity_match.group(2) else ''
                    name = re.sub(r'^\d+(?:,\d+)?\s*[a-zæøå\s]*', '', ingredient_text, flags=re.I).strip()

                ingredient = {
                    'quantity': quantity,
                    'unit': unit,
                    'name': name,
                    'allergens': allergens if name else []
                }

                if quantity > 0:
                    ingredients_included.append(ingredient)
                else:
                    ingredients_not_included.append(ingredient)

            instructions = []
            step_counter = 1
            step_elems = soup.find_all(class_=re.compile(r'step|instruction'))
            for elem in step_elems:
                step_title = elem.find(class_=re.compile(r'title|heading'))
                step_title = step_title.get_text(strip=True) if step_title else f'Step {step_counter}'

                step_desc = elem.find(class_=re.compile(r'description|text'))
                step_desc = step_desc.get_text(strip=True) if step_desc else ''

                image_elem = elem.find('img')
                image_path = None
                if image_elem:
                    img_url = image_elem.get('src')
                    if img_url:
                        if not img_url.startswith('http'):
                            img_url = urljoin(BASE_URL, img_url)
                        image_path = self.download_image(img_url, recipe_id, step_counter)

                instruction = {
                    'step': step_counter,
                    'title': step_title,
                    'description': step_desc,
                    'image_path': image_path
                }
                instructions.append(instruction)
                step_counter += 1

            recipe = {
                'id': recipe_id,
                'title': title,
                'subtitle': subtitle,
                'category': category,
                'url': recipe_url,
                'rating': rating,
                'rating_count': rating_count,
                'time_minutes': time_minutes,
                'difficulty': difficulty,
                'tags': tags,
                'allergens': allergens,
                'description': description,
                'ingredients_included': ingredients_included,
                'ingredients_not_included': ingredients_not_included,
                'instructions': instructions,
                'scraped_at': datetime.now().isoformat()
            }

            logger.info(f"Parsed recipe: {title} ({recipe_id})")
            return recipe

        except Exception as e:
            logger.error(f"Error parsing recipe {recipe_url}: {e}")
            self.failed_recipes.append({'url': recipe_url, 'error': str(e)})
            return None

    def save_recipe_cache(self, recipe: Dict) -> None:
        recipe_id = recipe['id']
        recipe_dir = CACHE_DIR / recipe_id
        recipe_dir.mkdir(parents=True, exist_ok=True)

        recipe_copy = recipe.copy()
        recipe_copy.pop('instructions', None)

        metadata_file = recipe_dir / 'metadata.json'
        with open(metadata_file, 'w', encoding='utf-8') as f:
            json.dump(recipe_copy, f, ensure_ascii=False, indent=2)

        logger.debug(f"Saved metadata for {recipe_id}")

    def scrape_category(self, category_name: str, category_url: str, max_recipes: int = 100) -> int:
        logger.info(f"\nScraping {category_name} from {category_url}")

        listing_page = self.fetch_url(category_url)
        if not listing_page:
            logger.error(f"Failed to fetch listing page for {category_name}")
            return 0

        recipe_links = self.extract_recipe_links(listing_page, category_name)
        recipe_links = recipe_links[:max_recipes]

        scraped_count = 0
        for i, recipe_url in enumerate(recipe_links, 1):
            logger.info(f"\n[{category_name}] Scraping recipe {i}/{len(recipe_links)}: {recipe_url}")

            recipe_html = self.fetch_url(recipe_url)
            if not recipe_html:
                continue

            recipe = self.parse_recipe(recipe_html, recipe_url, category_name)
            if recipe:
                self.recipes_db.append(recipe)
                self.save_recipe_cache(recipe)
                scraped_count += 1

        logger.info(f"\nCompleted {category_name}: {scraped_count}/{len(recipe_links)} recipes")
        return scraped_count

    def save_database(self) -> None:
        with open(DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(self.recipes_db, f, ensure_ascii=False, indent=2)
        logger.info(f"\nSaved {len(self.recipes_db)} recipes to {DB_FILE}")

    def generate_report(self) -> None:
        report = {
            'timestamp': datetime.now().isoformat(),
            'total_recipes_scraped': len(self.recipes_db),
            'total_skipped': len(self.skipped_recipes),
            'total_failed': len(self.failed_recipes),
            'skipped_recipes': self.skipped_recipes,
            'failed_recipes': self.failed_recipes
        }

        report_file = Path('logs/scraper_report.json')
        report_file.parent.mkdir(parents=True, exist_ok=True)

        with open(report_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)

        logger.info(f"\n=== SCRAPER REPORT ===")
        logger.info(f"Total recipes scraped: {len(self.recipes_db)}")
        logger.info(f"Total skipped (orange): {len(self.skipped_recipes)}")
        logger.info(f"Total failed: {len(self.failed_recipes)}")
        logger.info(f"Report saved to {report_file}")

    def run(self, max_recipes_per_category: int = 100) -> None:
        logger.info("Starting HelloFresh scraper")
        logger.info(f"Cache directory: {CACHE_DIR}")

        total_scraped = 0
        for category_name, category_url in RECIPE_CATEGORIES.items():
            count = self.scrape_category(category_name, category_url, max_recipes_per_category)
            total_scraped += count

        self.save_database()
        self.generate_report()

        logger.info(f"\n✅ Scraping complete! {total_scraped} recipes in database.")


if __name__ == '__main__':
    scraper = HelloFreshScraper()
    scraper.run(max_recipes_per_category=100)
