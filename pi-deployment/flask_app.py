#
# Pi-Menu
# Author:  nobody174 (nobodylearn174@gmail.com)
# Repo:    https://github.com/nobody174/Pi-Menu
# License: All rights reserved © 2025 nobody174
# "It's never too late to give up!"
#

import json
import logging
from pathlib import Path
from flask import Flask, render_template, jsonify, request
from datetime import datetime
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/flask_app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
MENU_FILE = DATA_DIR / 'weekly_menu.json'
RECIPES_DB_FILE = DATA_DIR / 'recipes_db.json'
CACHE_DIR = DATA_DIR / 'recipes_cache'

app = Flask(__name__,
    template_folder=str(Path(__file__).parent.parent / 'frontend/templates'),
    static_folder=str(Path(__file__).parent.parent / 'frontend/static'))
app.config['JSON_SORT_KEYS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.jinja_env.cache = None

logger.info(f"Flask templates: {app.template_folder}")
logger.info(f"Flask static: {app.static_folder}")

def load_menu():
    if MENU_FILE.exists():
        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_recipes_db():
    if RECIPES_DB_FILE.exists():
        with open(RECIPES_DB_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def find_recipe(recipe_id):
    recipes = load_recipes_db()
    return next((r for r in recipes if r['id'] == recipe_id), None)

@app.route('/')
def dashboard():
    menu = load_menu()
    if not menu:
        return render_template('error.html', message='No menu generated yet'), 404

    logger.info("Dashboard accessed")
    return render_template('index.html', menu=menu)

@app.route('/recipe/<recipe_id>')
def recipe_detail(recipe_id):
    recipe = None
    recipe_dir = CACHE_DIR / recipe_id

    # Try to load from metadata.json first
    if recipe_dir.exists():
        metadata_file = recipe_dir / 'metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    recipe = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

    # Fall back to recipes_db.json
    if not recipe:
        recipe = find_recipe(recipe_id)

    if not recipe:
        return render_template('error.html', message=f'Oppskrift ikke funnet: {recipe_id}'), 404

    logger.info(f"Recipe detail accessed: {recipe_id}")
    return render_template('recipe.html', recipe=recipe)

@app.route('/shopping')
def shopping_list():
    menu = load_menu()
    if not menu or 'shopping_list' not in menu:
        return render_template('error.html', message='No shopping list available'), 404

    logger.info("[SHOPPING HANDLER] Starting shopping_list() function")

    # DEBUG: Check if shopping.html file contains our test string
    shopping_file = Path(app.template_folder) / 'shopping.html'
    if shopping_file.exists():
        content = shopping_file.read_text(encoding='utf-8')
        if 'CLAUDE CODE TEST' in content:
            logger.info("[DEBUG] shopping.html contains TEST marker - file is correct!")
        else:
            logger.info("[DEBUG] shopping.html DOES NOT contain TEST marker - FILE IS WRONG!")
        logger.info(f"[DEBUG] shopping.html file size: {len(content)} bytes")
        logger.info(f"[DEBUG] shopping.html path: {shopping_file}")
    else:
        logger.error(f"[DEBUG] shopping.html NOT FOUND at {shopping_file}")

    logger.info("[SHOPPING HANDLER] About to call render_template()")
    rendered = render_template('shopping.html', shopping_list=menu['shopping_list'])
    logger.info(f"[SHOPPING HANDLER] render_template returned {len(rendered)} bytes")
    return rendered

@app.route('/api/menu')
def api_menu():
    menu = load_menu()
    if not menu:
        return jsonify({'error': 'No menu generated yet'}), 404

    logger.info("API menu endpoint accessed")
    return jsonify(menu)

@app.route('/api/regenerate', methods=['POST'])
def api_regenerate():
    try:
        from core.menu_generator import MenuGenerator

        # Get selected categories from request
        data = request.get_json() or {}
        selected_categories = data.get('selected_categories', ['Populære', 'Familie', 'Rask Middag'])

        logger.info(f"Generating menu with categories: {selected_categories}")

        generator = MenuGenerator(selected_categories=selected_categories)
        menu = generator.run(num_dinners=6, save=True)

        logger.info("Menu regenerated via API")
        return jsonify({'status': 'success', 'menu': menu})
    except Exception as e:
        logger.error(f"Menu regeneration failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Return list of all available recipe categories"""
    menus_dir = Path('../data/menus')
    categories = []

    if menus_dir.exists():
        categories = [d.name for d in menus_dir.iterdir() if d.is_dir()]

    logger.info(f"Available categories: {len(categories)}")
    return jsonify({'categories': sorted(categories)})

@app.route('/api/sync-shopping-list', methods=['POST'])
def sync_shopping_list():
    """Sync selected shopping items to Microsoft To Do"""
    try:
        from core.todo_sync import ToDoSync

        data = request.get_json()

        # Build shopping list from full list but only with checked items
        full_shopping_list = data.get('shopping_list', {})
        selected_items = data.get('items', [])

        if not selected_items:
            return jsonify({'status': 'error', 'message': 'Ingen elementer valgt'}), 400

        # Filter shopping list to only include selected items
        filtered_list = {}
        selected_item_set = {f"{item['ingredient']}-{item['quantity']}-{item['unit']}" for item in selected_items}

        for category, items in full_shopping_list.items():
            filtered_items = [item for item in items
                            if f"{item['ingredient']}-{item['quantity']}-{item['unit']}" in selected_item_set]
            if filtered_items:
                filtered_list[category] = filtered_items

        # Sync to To Do
        sync = ToDoSync()
        if sync.authenticate():
            if sync.sync_shopping_list_to_todo(filtered_list):
                logger.info(f"Synced {len(selected_items)} items to To Do")
                return jsonify({'status': 'success', 'message': f'Sendt {len(selected_items)} elementer til telefon'})
            else:
                return jsonify({'status': 'error', 'message': 'Feil ved syncing til To Do'}), 500
        else:
            return jsonify({'status': 'error', 'message': 'Kunne ikke koble til Microsoft To Do'}), 500

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    menu_exists = MENU_FILE.exists()
    recipes_exists = RECIPES_DB_FILE.exists()

    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'menu_available': menu_exists,
        'recipes_available': recipes_exists
    })

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Page not found'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template('error.html', message='Server error'), 500

if __name__ == '__main__':
    logger.info("=== STARTING FLASK APP - CLAUDE AI DEBUG VERSION 2026-06-13 ===")
    logger.info(f"Running from: {__file__}")
    app.run(host='0.0.0.0', port=5000, debug=False)
