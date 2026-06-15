#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

import json
import os
import logging
import secrets
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import datetime
import sys
from dotenv import load_dotenv

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / '.env')

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

# Certificate paths (relative to pi-deployment dir where the service runs from)
CERT_FILE = Path(__file__).parent / 'cert.pem'
KEY_FILE = Path(__file__).parent / 'key.pem'

app = Flask(__name__,
    template_folder=str(Path(__file__).parent.parent / 'frontend/templates'),
    static_folder=str(Path(__file__).parent.parent / 'frontend/static'))

app.config['JSON_SORT_KEYS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = True
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))
app.config['SESSION_COOKIE_SECURE'] = True
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'
app.jinja_env.cache = None

logger.info(f"Flask templates: {app.template_folder}")
logger.info(f"Flask static: {app.static_folder}")

# ── Context Processors ───────────────────────────────────────────────────────

@app.context_processor
def inject_config():
    """Inject configuration into all templates"""
    return {
        'household_name': os.getenv('HOUSEHOLD_NAME', '{Family_Name}'),
        'creator': 'nobody174',
        'github_url': 'https://github.com/nobody174/Pi-Menu-Public',
        'patreon_url': 'https://www.patreon.com/c/Nobody174'
    }

# ── Helpers ──────────────────────────────────────────────────────────────────

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

def _redirect_uri():
    return os.getenv("AZURE_REDIRECT_URI", "http://pi-menu.local:5000/callback")

# ── Page routes ───────────────────────────────────────────────────────────────

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

    if recipe_dir.exists():
        metadata_file = recipe_dir / 'metadata.json'
        if metadata_file.exists():
            try:
                with open(metadata_file, 'r', encoding='utf-8') as f:
                    recipe = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

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
    return render_template('shopping.html', shopping_list=menu['shopping_list'])

@app.route('/add-recipe')
def add_recipe_page():
    return render_template('add-recipe.html')

@app.route('/all-recipes')
def all_recipes_page():
    recipes = load_recipes_db()
    return render_template('all-recipes.html', recipes=recipes)

@app.route('/settings')
def settings_page():
    return render_template('settings.html')

# ── Auth routes ───────────────────────────────────────────────────────────────

@app.route('/login')
def login():
    from auth import build_msal_app, get_auth_url
    msal_app = build_msal_app(_redirect_uri())
    flow = get_auth_url(msal_app, _redirect_uri())
    session['auth_flow'] = flow
    logger.info("User redirecting to Microsoft login")
    return redirect(flow['auth_uri'])

@app.route('/callback')
def callback():
    from auth import build_msal_app, acquire_token_by_auth_code_flow, get_user_info
    try:
        flow = session.get('auth_flow')
        if not flow:
            return render_template('error.html', message='Session expired. Please try logging in again.'), 400

        msal_app = build_msal_app(_redirect_uri())
        result = acquire_token_by_auth_code_flow(msal_app, flow, request.args.to_dict())

        if 'error' in result:
            err = result.get('error_description', result.get('error', 'Unknown error'))
            logger.error(f"Auth callback error: {err}")
            return render_template('error.html', message=f'Innlogging feilet: {err}'), 400

        session['access_token'] = result['access_token']
        session.pop('auth_flow', None)

        try:
            user = get_user_info(result['access_token'])
            session['user_name'] = user.get('displayName', user.get('userPrincipalName', 'Bruker'))
            session['user_email'] = user.get('userPrincipalName', '')
        except Exception:
            session['user_name'] = 'Bruker'
            session['user_email'] = ''

        logger.info(f"User authenticated: {session.get('user_email')}")
        return redirect('/')

    except Exception as e:
        logger.error(f"Callback exception: {e}")
        return render_template('error.html', message=f'Autentiseringsfeil: {str(e)}'), 500

@app.route('/logout')
def logout():
    session.clear()
    logger.info("User logged out")
    return redirect('/')

@app.route('/api/user')
def api_user():
    from auth import is_authorised
    return jsonify({'authenticated': is_authorised()})

@app.route('/api/debug-token')
def debug_token():
    """Decode the JWT token header to see account type — remove this route after debugging."""
    if 'access_token' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    import base64, json as _json
    token = session['access_token']
    try:
        parts = token.split('.')
        # Pad and decode the payload (part 1)
        payload_b64 = parts[1] + '=='
        payload = _json.loads(base64.urlsafe_b64decode(payload_b64))
        return jsonify({
            'tid': payload.get('tid'),          # tenant id — 9188... = personal MSA
            'aud': payload.get('aud'),
            'scp': payload.get('scp'),          # scopes granted
            'upn': payload.get('upn'),
            'email': payload.get('email'),
            'unique_name': payload.get('unique_name'),
            'idp': payload.get('idp'),          # identity provider
        })
    except Exception as e:
        return jsonify({'error': str(e), 'token_prefix': token[:40]})

# ── API routes ────────────────────────────────────────────────────────────────

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
        data = request.get_json() or {}
        selected_categories = data.get('categories') or data.get('selected_categories') or ['Populære', 'Familie', 'Rask Middag']
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
    """Get all available categories from categories.json"""
    categories_file = Path(__file__).parent.parent / 'data' / 'categories.json'
    categories = []
    if categories_file.exists():
        try:
            with open(categories_file, 'r', encoding='utf-8') as f:
                categories = json.load(f)
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
    return jsonify({'categories': categories})

@app.route('/api/sync-shopping-list', methods=['POST'])
def api_sync_shopping_list():
    """Sync selected shopping items to Microsoft To Do using the stored refresh token."""
    try:
        from auth import get_access_token, sync_shopping_list_to_todo

        # Try cached token first, fall back to session token (set during /callback)
        token = get_access_token() or session.get('access_token')

        if not token:
            return jsonify({
                'status': 'error',
                'message': 'Pi-Menu er ikke koblet til Microsoft To Do ennå. Be Vartdal om å logge inn én gang via /login.',
                'requiresAuth': True,
                'loginUrl': '/login',
            }), 401

        data = request.get_json() or {}
        full_shopping_list = data.get('shopping_list', {})
        selected_items = data.get('items', [])

        if not selected_items:
            return jsonify({'status': 'error', 'message': 'Ingen elementer valgt'}), 400

        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [i for i in items if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set]
            if kept:
                filtered[category] = kept

        result = sync_shopping_list_to_todo(token, filtered)

        logger.info(f"Synced {result['added']} items to To Do, errors: {result['errors']}")
        msg = f"Sendt {result['added']} elementer til To Do ✓"
        if result['errors']:
            msg += f" ({len(result['errors'])} feil)"
        return jsonify({'status': 'success', 'message': msg})

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/add-recipe', methods=['POST'])
def api_add_recipe():
    """Add a manually created recipe to recipes_db.json and backup the form"""
    try:
        import uuid
        from datetime import datetime
        data = request.get_json() or {}

        recipe = {
            'id': str(uuid.uuid4())[:8],
            'title': data.get('title', ''),
            'description': data.get('description', ''),
            'difficulty': data.get('difficulty', 'Enkel'),
            'time_minutes': data.get('time_minutes', 30),
            'category': data.get('category', 'HomeMade'),
            'ingredients': data.get('ingredients', []),
            'instructions': data.get('instructions', []),
            'comment': data.get('comment', ''),
            'source': 'manual',
        }

        if not recipe['title'] or not recipe['ingredients']:
            return jsonify({'status': 'error', 'message': 'Tittel og ingredienser er påkrevd'}), 400

        # Backup the form submission
        backup_dir = Path('data/sendt_forms')
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_title = recipe['title'].replace(' ', '_').replace('/', '_').replace('\\', '_')
        backup_file = backup_dir / f"form_{safe_title}.json"
        with open(backup_file, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Backed up form to: {backup_file}")

        # Save to recipes database
        recipes = load_recipes_db()
        recipes.append(recipe)

        recipes_file = RECIPES_DB_FILE
        with open(recipes_file, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)

        logger.info(f"Added recipe: {recipe['title']} (ID: {recipe['id']})")
        return jsonify({'status': 'success', 'message': f"✅ {recipe['title']} lagret!", 'recipe_id': recipe['id']})

    except Exception as e:
        logger.error(f"Error adding recipe: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/swap-recipe', methods=['POST'])
def api_swap_recipe():
    """Swap a recipe for a specific weekday in the current menu"""
    try:
        data = request.get_json() or {}
        recipe_id = data.get('recipe_id')
        day = data.get('day')

        if not recipe_id or not day:
            return jsonify({'status': 'error', 'message': 'Recipe ID and day required'}), 400

        menu = load_menu()
        if not menu:
            return jsonify({'status': 'error', 'message': 'No menu generated yet'}), 404

        # Find the dinner for this day and replace it
        updated = False
        for dinner in menu.get('dinners', []):
            if dinner['day'] == day:
                # Find the new recipe
                recipe = find_recipe(recipe_id)
                if not recipe:
                    return jsonify({'status': 'error', 'message': 'Recipe not found'}), 404

                # Replace the dinner
                dinner['recipe_id'] = recipe['id']
                dinner['title'] = recipe['title']
                dinner['time_minutes'] = recipe.get('time_minutes', 0)
                dinner['difficulty'] = recipe.get('difficulty', '')
                updated = True
                break

        if not updated:
            return jsonify({'status': 'error', 'message': f'Day {day} not found in menu'}), 404

        # Save the updated menu
        with open(MENU_FILE, 'w', encoding='utf-8') as f:
            json.dump(menu, f, ensure_ascii=False, indent=2)

        logger.info(f"Swapped recipe for {day}: {recipe['title']}")
        return jsonify({'status': 'success', 'message': f'Recipe swapped for {day}'})

    except Exception as e:
        logger.error(f"Error swapping recipe: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/health')
def health_check():
    return jsonify({
        'status': 'healthy',
        'timestamp': datetime.now().isoformat(),
        'menu_available': MENU_FILE.exists(),
        'recipes_available': RECIPES_DB_FILE.exists(),
        'https': CERT_FILE.exists(),
    })

# ── Theme gallery ─────────────────────────────────────────────────────────────

@app.route('/themes')
def theme_gallery():
    import os as _os
    preview_dir = Path(__file__).parent.parent / 'frontend/static/theme-previews'
    files = sorted([f for f in _os.listdir(preview_dir) if f.endswith('.html')])
    themes = [{'file': f, 'name': f.replace('theme-', '').replace('.html', '').replace('-', ' ').title()} for f in files]
    return render_template('theme_gallery.html', themes=themes)

@app.route('/themes/<filename>')
def theme_preview(filename):
    from flask import send_from_directory
    preview_dir = Path(__file__).parent.parent / 'frontend/static/theme-previews'
    return send_from_directory(preview_dir, filename)

# ── Error handlers ────────────────────────────────────────────────────────────

@app.errorhandler(404)
def not_found(error):
    return render_template('error.html', message='Page not found'), 404

@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template('error.html', message='Server error'), 500

# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == '__main__':
    logger.info("=== STARTING FLASK APP WITH HTTPS ===")
    logger.info(f"Running from: {__file__}")

    # HTTP only — local home network use, no "Not Secure" warning
    app.run(host='0.0.0.0', port=5000, debug=False)
