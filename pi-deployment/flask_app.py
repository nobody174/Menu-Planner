#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
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

# ── i18n helpers ─────────────────────────────────────────────────────────────

_I18N_CACHE = None

def _load_i18n():
    global _I18N_CACHE
    if _I18N_CACHE is None:
        i18n_path = Path(__file__).parent.parent / 'frontend' / 'static' / 'i18n.json'
        try:
            with open(i18n_path, 'r', encoding='utf-8') as f:
                _I18N_CACHE = json.load(f)
        except Exception as e:
            _I18N_CACHE = {}
            print(f"WARNING: Could not load i18n.json: {e}")
    return _I18N_CACHE

def _get_lang():
    """Read language from cookie, fallback to 'en'."""
    lang = request.cookies.get('pi_language', 'en')
    return lang if lang in ('en', 'no') else 'en'

def _make_t(lang):
    """Return a dict of {key: translated_value} for the given language."""
    raw = _load_i18n()
    result = {}
    suffix = '_' + lang
    fallback_suffix = '_en'
    for full_key, value in raw.items():
        if full_key.endswith(suffix):
            base = full_key[:-len(suffix)]
            result[base] = value
    # Fill in English fallbacks for any missing keys
    for full_key, value in raw.items():
        if full_key.endswith(fallback_suffix):
            base = full_key[:-len(fallback_suffix)]
            if base not in result:
                result[base] = value
    return result

def _resolve(val, lang):
    """Resolve a bilingual dict {'no': ..., 'en': ...} or plain string to a single string."""
    if isinstance(val, dict):
        return val.get(lang) or val.get('en') or val.get('no') or ''
    return val or ''

# Difficulty normalisation map (Norwegian → English)
_DIFFICULTY_MAP = {
    'enkel': 'Easy', 'easy': 'Easy',
    'middels': 'Medium', 'medium': 'Medium',
    'vanskelig': 'Hard', 'hard': 'Hard',
}

def _normalize_difficulty(val):
    if isinstance(val, dict):
        val = val.get('en') or val.get('no') or ''
    if not val:
        return 'Easy'
    return _DIFFICULTY_MAP.get(str(val).lower(), val)

def _normalize_recipe(recipe, lang='en'):
    """Flatten all bilingual dict fields in a recipe to plain strings for the given lang."""
    r = dict(recipe)
    # Handle both formats: bilingual dict {'no': ..., 'en': ...} and separate _no/_en fields
    # Prefer language-specific _no/_en fields, fall back to dict format, then fallback to plain string
    for field in ('title', 'subtitle', 'description', 'comment'):
        # First check for _no/_en suffix fields (sample_recipes.json format)
        if r.get(f'{field}_{lang}'):
            r[field] = r[f'{field}_{lang}']
        # Then check for dict format
        elif isinstance(r.get(field), dict):
            r[field] = r[field].get(lang) or r[field].get('en') or r[field].get('no') or ''
        # Keep plain string as-is, but only if no language-specific version exists
        elif not isinstance(r.get(field), dict) and not r.get(f'{field}_{lang}'):
            # Try fallback fields if language-specific not found
            if lang != 'en' and r.get(f'{field}_en'):
                r[field] = r.get(f'{field}_en')
        # If field is missing entirely, ensure it's empty string
        if field not in r or r[field] is None:
            r[field] = ''

    # time_minutes may be stored as cookTimeMinutes in pack recipes
    if 'time_minutes' not in r or not r.get('time_minutes'):
        r['time_minutes'] = r.get('cookTimeMinutes', r.get('time_minutes', 30))

    # Difficulty: flatten + normalise
    r['difficulty'] = _normalize_difficulty(_resolve(r.get('difficulty'), lang))

    # Ingredients: support pack schema, sample_recipes _no/_en fields, and simple strings
    new_ings = []
    for ing in r.get('ingredients', []):
        if isinstance(ing, dict):
            # Try to get bilingual name: dict format, then _no/_en fields, then plain 'name'
            if isinstance(ing.get('name'), dict):
                name = _resolve(ing.get('name'), lang)
            else:
                name = ing.get(f'name_{lang}') or ing.get('name_en') or ing.get('name') or ''
            qty  = ing.get('quantity', ing.get('amount', 0))
            unit = ing.get('unit', '')
            if isinstance(unit, dict):
                unit = _resolve(unit, lang)
            new_ings.append({'name': name, 'quantity': qty, 'unit': unit})
        else:
            new_ings.append(ing)
    r['ingredients'] = new_ings
    # Also flatten ingredients_included / ingredients_not_included if present
    for field in ('ingredients_included', 'ingredients_not_included'):
        if r.get(field):
            flat = []
            for ing in r[field]:
                if isinstance(ing, dict):
                    # Try to get bilingual name: dict format, then _no/_en fields, then plain 'name'
                    if isinstance(ing.get('name'), dict):
                        name = _resolve(ing.get('name'), lang)
                    else:
                        name = ing.get(f'name_{lang}') or ing.get('name_en') or ing.get('name') or ''
                    qty  = ing.get('quantity', ing.get('amount', 0))
                    unit = ing.get('unit', '')
                    if isinstance(unit, dict):
                        unit = _resolve(unit, lang)
                    flat.append({'name': name, 'quantity': qty, 'unit': unit})
                else:
                    flat.append(ing)
            r[field] = flat

    # Instructions: support {no: [...], en: [...]} or [{step, description}] or [str]
    raw_inst = r.get('instructions', [])
    if isinstance(raw_inst, dict):
        steps = raw_inst.get(lang) or raw_inst.get('en') or []
        r['instructions'] = [{'step': i+1, 'description': s} for i, s in enumerate(steps)]
    elif isinstance(raw_inst, list) and raw_inst:
        # Already a list — normalise any dict entries
        norm = []
        for i, s in enumerate(raw_inst):
            if isinstance(s, dict):
                norm.append({'step': s.get('step', i+1), 'description': _resolve(s.get('description'), lang)})
            else:
                norm.append({'step': i+1, 'description': str(s)})
        r['instructions'] = norm

    return r

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

DATA_DIR = Path(__file__).parent.parent / 'data'
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
    """Inject configuration and i18n into all templates."""
    lang = _get_lang()
    t = _make_t(lang)
    return {
        'household_name': os.getenv('HOUSEHOLD_NAME', '{Family_Name}'),
        'creator': 'nobody174',
        'github_url': 'https://github.com/nobody174/Menu-Planner',
        'patreon_url': 'https://www.patreon.com/c/Nobody174',
        'lang': lang,
        't': t,
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
    # Search recipes_db.json first, then sample_recipes.json
    all_recipes = load_recipes_db()
    sample_path = DATA_DIR / 'sample_recipes.json'
    if sample_path.exists():
        try:
            with open(sample_path, 'r', encoding='utf-8') as f:
                all_recipes = all_recipes + json.load(f)
        except Exception:
            pass
    return next((r for r in all_recipes if r['id'] == recipe_id), None)

def _redirect_uri():
    return os.getenv("AZURE_REDIRECT_URI", "http://pi-menu.local:5000/callback")

# ── Page routes ───────────────────────────────────────────────────────────────

_DAY_TRANSLATIONS = {
    'no': {
        'Monday': 'Mandag', 'Tuesday': 'Tirsdag', 'Wednesday': 'Onsdag',
        'Thursday': 'Torsdag', 'Friday': 'Fredag', 'Saturday': 'Lørdag', 'Sunday': 'Søndag'
    }
}

@app.route('/')
def dashboard():
    menu = load_menu()
    if not menu:
        return render_template('error.html', message='No menu generated yet'), 404
    lang = _get_lang()
    # Translate day names, difficulty, and categories for the current language
    day_map = _DAY_TRANSLATIONS.get(lang, {})
    t_dict = _make_t(lang)
    diff_map = {
        'Easy': t_dict.get('easy', 'Easy'),
        'Medium': t_dict.get('medium', 'Medium'),
        'Hard': t_dict.get('hard', 'Hard'),
    }
    # Category translation map
    cat_map = {
        'Quick Dinners': t_dict.get('quick_dinners', 'Quick Dinners'),
        'Pasta & Noodles': t_dict.get('pasta_noodles', 'Pasta & Noodles'),
        'Chicken': t_dict.get('chicken', 'Chicken'),
        'Ground Meat & Sausages': t_dict.get('ground_meat', 'Ground Meat & Sausages'),
        'Fish & Seafood': t_dict.get('fish_seafood', 'Fish & Seafood'),
        'Taco & Tex-Mex': t_dict.get('taco_texmex', 'Taco & Tex-Mex'),
        'Grill': t_dict.get('grill', 'Grill'),
        'Soups & Stews': t_dict.get('soups_stews', 'Soups & Stews'),
        'Vegetarian': t_dict.get('vegetarian', 'Vegetarian'),
        'Homemade': t_dict.get('homemade', 'Homemade'),
    }
    import copy
    menu = copy.deepcopy(menu)
    # Translate categories
    if menu.get('selected_categories'):
        menu['selected_categories'] = [cat_map.get(c, c) for c in menu['selected_categories']]
    for dinner in menu.get('dinners', []):
        if dinner.get('day') in day_map:
            dinner['day'] = day_map[dinner['day']]
        # Always normalize & translate difficulty
        d = dinner.get('difficulty', '')
        d_normalized = _normalize_difficulty(d)
        dinner['difficulty'] = diff_map.get(d_normalized, d_normalized)
        # Resolve title to correct language (use _no/_en fields from menu JSON)
        dinner['title'] = dinner.get(f'title_{lang}') or dinner.get('title_en') or dinner.get('title') or ''
        # Also resolve subtitle if available
        if f'subtitle_{lang}' in dinner or 'subtitle_en' in dinner:
            dinner['subtitle'] = dinner.get(f'subtitle_{lang}') or dinner.get('subtitle_en') or dinner.get('subtitle') or ''
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
        return render_template('error.html', message=f'Recipe not found: {recipe_id}'), 404

    lang = _get_lang()
    recipe = _normalize_recipe(recipe, lang)
    logger.info(f"Recipe detail accessed: {recipe_id}")
    return render_template('recipe.html', recipe=recipe)

@app.route('/shopping')
def shopping_list():
    menu = load_menu()
    if not menu or 'shopping_list' not in menu:
        return render_template('error.html', message='No shopping list available'), 404

    lang = _get_lang()
    if lang == 'no':
        # Rebuild shopping list ingredient names in Norwegian from the recipe data
        shopping = {}
        recipe_ids = [d['recipe_id'] for d in menu.get('dinners', [])]
        all_recipes_raw = []
        # Load from all sources: sample recipes, imported recipes, and recipe packs
        for db_path in (DATA_DIR / 'sample_recipes.json', DATA_DIR / 'recipes_db.json'):
            if db_path.exists():
                try:
                    with open(db_path, 'r', encoding='utf-8') as f:
                        all_recipes_raw.extend(json.load(f))
                except Exception:
                    pass
        # Also load from recipe packs (which have bilingual data)
        packs_dir = DATA_DIR / 'recipe-packs'
        if packs_dir.exists():
            for pack_file in packs_dir.glob('*.json'):
                try:
                    with open(pack_file, 'r', encoding='utf-8') as f:
                        pack = json.load(f)
                        all_recipes_raw.extend(pack.get('recipes', []))
                except Exception:
                    pass
        recipes_by_id = {r['id']: r for r in all_recipes_raw}
        en_shopping = menu['shopping_list']
        # Build a name map: english_name_lower -> norwegian_name
        name_map = {}
        for rid in recipe_ids:
            r = recipes_by_id.get(rid)
            if not r:
                continue
            # Check all possible ingredient fields
            for field in ('ingredients', 'ingredients_included', 'ingredients_not_included'):
                for ing in r.get(field, []):
                    en = ''
                    no = ''
                    # Check for bilingual dict format (pack recipes)
                    if isinstance(ing.get('name'), dict):
                        en = (ing['name'].get('en') or '').strip().lower()
                        no = (ing['name'].get('no') or '').strip()
                    # Check for _no/_en suffix fields (sample_recipes format)
                    elif ing.get('name_en'):
                        en = (ing.get('name_en') or '').strip().lower()
                        no = (ing.get('name_no') or '').strip()
                    if en and no:
                        name_map[en] = no
        # Translate shopping list ingredient names
        for category, items in en_shopping.items():
            new_items = []
            for item in items:
                new_item = dict(item)
                en_name = item.get('ingredient', '').strip().lower()
                if en_name in name_map:
                    new_item['ingredient'] = name_map[en_name]
                new_items.append(new_item)
            shopping[category] = new_items
    else:
        shopping = menu['shopping_list']

    return render_template('shopping.html', shopping_list=shopping)

@app.route('/add-recipe')
def add_recipe_page():
    return render_template('add-recipe.html')

@app.route('/all-recipes')
def all_recipes_page():
    lang = _get_lang()
    recipes = [_normalize_recipe(r, lang) for r in load_recipes_db()]
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
            return render_template('error.html', message=f'Login failed: {err}'), 400

        session['access_token'] = result['access_token']
        session.pop('auth_flow', None)

        try:
            user = get_user_info(result['access_token'])
            session['user_name'] = user.get('displayName', user.get('userPrincipalName', 'User'))
            session['user_email'] = user.get('userPrincipalName', '')
        except Exception:
            session['user_name'] = 'User'
            session['user_email'] = ''

        logger.info(f"User authenticated: {session.get('user_email')}")
        return redirect('/')

    except Exception as e:
        logger.error(f"Callback exception: {e}")
        return render_template('error.html', message=f'Authentication error: {str(e)}'), 500

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
    lang = _get_lang()
    day_map = _DAY_TRANSLATIONS.get(lang, {})
    if day_map:
        import copy
        menu = copy.deepcopy(menu)
        for dinner in menu.get('dinners', []):
            if dinner.get('day') in day_map:
                dinner['day'] = day_map[dinner['day']]
            dinner['title'] = _resolve(dinner.get('title'), lang)
    logger.info("API menu endpoint accessed")
    return jsonify(menu)

@app.route('/api/regenerate', methods=['POST'])
def api_regenerate():
    try:
        from core.menu_generator import MenuGenerator
        data = request.get_json() or {}
        selected_categories = data.get('categories') or data.get('selected_categories') or ['Quick Dinners', 'Fish & Seafood', 'Vegetarian']
        logger.info(f"Generating menu with categories: {selected_categories}")
        generator = MenuGenerator(selected_categories=selected_categories)
        menu = generator.run(num_dinners=6, save=True)
        logger.info("Menu regenerated via API")
        return jsonify({'status': 'success', 'menu': menu})
    except Exception as e:
        import traceback
        logger.error(f"Menu regeneration failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/categories')
def get_categories():
    """Get all available categories from categories.json, translated to current language"""
    lang = _get_lang()
    categories_file = Path(__file__).parent.parent / 'data' / 'categories.json'
    categories = []
    if categories_file.exists():
        try:
            with open(categories_file, 'r', encoding='utf-8') as f:
                raw_cats = json.load(f)
                # Translate to current language
                for cat in raw_cats:
                    translated = dict(cat)
                    # Add 'name' field with the translated category name
                    translated['name'] = cat.get(f'name_{lang}') or cat.get('name_en') or cat.get('code')
                    categories.append(translated)
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
    return jsonify(categories)

@app.route('/api/export-shopping-list', methods=['POST'])
def api_export_shopping_list():
    """Export shopping list in various formats."""
    try:
        from shopping_integrations import (
            export_csv, export_json, export_todoist_format,
            export_plain_text, export_ics, export_microsoft_todo_format
        )

        data = request.get_json() or {}
        fmt = data.get('format', 'txt').lower()
        full_shopping_list = data.get('shopping_list', {})
        selected_items = data.get('items', [])

        if not selected_items:
            return jsonify({'success': False, 'error': 'No items to export'}), 400

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [i for i in items if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set]
            if kept:
                filtered[category] = kept

        # Generate export
        if fmt == 'csv':
            content = export_csv(filtered)
            mime_type = 'text/csv'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.csv'
        elif fmt == 'json':
            content = export_json(filtered)
            mime_type = 'application/json'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        elif fmt == 'todoist':
            content = export_todoist_format(filtered)
            mime_type = 'text/plain'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'
        elif fmt == 'ics':
            content = export_ics(filtered)
            mime_type = 'text/calendar'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'
        elif fmt == 'todo':
            content = export_microsoft_todo_format(filtered)
            mime_type = 'application/json'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        else:  # txt
            content = export_plain_text(filtered)
            mime_type = 'text/plain'
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'

        return jsonify({
            'success': True,
            'content': content,
            'filename': filename,
            'mime_type': mime_type
        })

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

@app.route('/api/sync-shopping-list', methods=['POST'])
def api_sync_shopping_list():
    """Universal shopping list sync endpoint for all services."""
    try:
        from shopping_integrations import (
            sync_todoist, sync_ticktick
        )
        from auth import get_access_token, sync_shopping_list_to_todo

        data = request.get_json() or {}
        service = data.get('service', 'microsoft').lower()
        full_shopping_list = data.get('shopping_list', {})
        selected_items = data.get('items', [])

        if not selected_items:
            return jsonify({'success': False, 'error': 'No items to sync'}), 400

        logger.info(f"Sync request: service={service}, items={len(selected_items)}, categories={len(full_shopping_list)}")

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [i for i in items if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set]
            if kept:
                filtered[category] = kept

        logger.info(f"Filtered: {len(filtered)} categories, total items: {sum(len(v) for v in filtered.values())}")

        # Route to appropriate service
        if service == 'microsoft':
            token = get_access_token() or session.get('access_token')
            if not token:
                return jsonify({
                    'success': False,
                    'requires_config': True,
                    'message': 'Microsoft To Do not configured. Follow the setup guide: Read docs/INTEGRATION_SETUP_GUIDE.md section "Microsoft To Do" and add AZURE_CLIENT_ID, AZURE_CLIENT_SECRET, and AZURE_TENANT_ID to your .env file, then restart Flask.'
                }), 401
            result = sync_shopping_list_to_todo(token, filtered)
            return jsonify({
                'success': True,
                'message': f"Synced {result.get('added', 0)} items to Microsoft To Do ✓"
            })

        elif service == 'todoist':
            api_token = os.getenv('TODOIST_API_TOKEN') or ''
            if not api_token:
                return jsonify({
                    'success': False,
                    'requires_config': True,
                    'message': 'Todoist API token not configured. Get it from: https://todoist.com/app/settings/integrations/developer'
                }), 401
            result = sync_todoist(filtered, api_token)
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f"Synced {result.get('added', 0)} items to Todoist ✓"
                })
            else:
                return jsonify({
                    'success': False,
                    'error': result.get('error', 'Unknown error'),
                    'requires_config': True,
                    'message': 'Todoist sync failed. Check API token.'
                }), 500

        elif service == 'ticktick':
            api_token = os.getenv('TICKTICK_API_TOKEN') or ''
            if not api_token:
                return jsonify({
                    'success': False,
                    'requires_config': True,
                    'message': 'TickTick API token not configured. Get it from: https://ticktick.com/user/myprofile'
                }), 401
            result = sync_ticktick(filtered, api_token)
            if result.get('success'):
                return jsonify({
                    'success': True,
                    'message': f"Synced {result.get('added', 0)} items to TickTick ✓"
                })
            else:
                return jsonify({'success': False, 'error': result.get('error'), 'requires_config': True, 'message': 'TickTick sync failed. Verify your API token is correct.'}), 500

        elif service == 'reminders':
            # Return ICS file for Apple Reminders as direct download
            from shopping_integrations import export_ics
            from flask import send_file
            import io

            content = export_ics(filtered)
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'

            # Create file-like object
            ics_file = io.BytesIO(content.encode('utf-8'))

            return send_file(
                ics_file,
                mimetype='text/calendar',
                as_attachment=True,
                download_name=filename
            )

        else:
            return jsonify({'success': False, 'error': f'Unknown service: {service}'}), 400

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({'success': False, 'error': str(e)}), 500

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
            'difficulty': _normalize_difficulty(data.get('difficulty', 'Easy')),
            'time_minutes': data.get('time_minutes', 30),
            'category': data.get('category', 'HomeMade'),
            'ingredients': data.get('ingredients', []),
            'instructions': data.get('instructions', []),
            'comment': data.get('comment', ''),
            'source': 'manual',
        }

        if not recipe['title'] or not recipe['ingredients']:
            return jsonify({'status': 'error', 'message': 'Title and ingredients are required'}), 400

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
        return jsonify({'status': 'success', 'message': f"✅ {recipe['title']} saved!", 'recipe_id': recipe['id']})

    except Exception as e:
        logger.error(f"Error adding recipe: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/delete-recipe', methods=['POST'])
def api_delete_recipe():
    """Delete a recipe from recipes_db.json by ID."""
    try:
        data = request.get_json() or {}
        recipe_id = data.get('recipe_id')
        if not recipe_id:
            return jsonify({'status': 'error', 'message': 'recipe_id is required'}), 400

        recipes = load_recipes_db()
        original_count = len(recipes)
        recipes = [r for r in recipes if r.get('id') != recipe_id]

        if len(recipes) == original_count:
            return jsonify({'status': 'error', 'message': f'Recipe {recipe_id} not found'}), 404

        with open(RECIPES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)

        logger.info(f"Deleted recipe: {recipe_id}")
        return jsonify({'status': 'success', 'message': f'Recipe {recipe_id} deleted'})
    except Exception as e:
        logger.error(f"Delete recipe error: {e}")
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

# ── Recipe Packs API ──────────────────────────────────────────────────────────

def get_available_recipe_packs():
    """Load all available recipe packs from data/recipe-packs/"""
    packs_dir = DATA_DIR / 'recipe-packs'
    packs = []

    if not packs_dir.exists():
        logger.warning(f"Recipe packs directory not found: {packs_dir}")
        return packs

    for pack_file in sorted(packs_dir.glob('pack_*.json')):
        try:
            with open(pack_file, 'r', encoding='utf-8') as f:
                pack = json.load(f)
                packs.append(pack)
        except Exception as e:
            logger.error(f"Error loading pack {pack_file}: {e}")

    return packs

@app.route('/api/recipe-packs/list')
def api_recipe_packs_list():
    """Get list of available recipe packs"""
    packs = get_available_recipe_packs()
    # Return pack metadata only (not full recipes)
    simplified = []
    for pack in packs:
        simplified.append({
            'packId': pack['packId'],
            'packName': pack['packName'],
            'packDescription': pack['packDescription'],
            'packIcon': pack.get('packImage', '📦'),
            'packColor': pack.get('packColor', '#999999'),
            'recipeCount': pack['recipeCount'],
            'estimatedCookTime': pack['estimatedCookTime'],
            'difficulty': pack['difficulty']
        })
    return jsonify(simplified)

@app.route('/api/recipe-packs/import', methods=['POST'])
def api_recipe_packs_import():
    """Import selected recipe packs into user's recipe database"""
    try:
        data = request.get_json()
        pack_ids = data.get('packIds', [])

        if not pack_ids:
            return jsonify({'success': False, 'message': 'No packs selected'}), 400

        # Load all packs
        all_packs = get_available_recipe_packs()
        recipes_to_import = []

        # Collect recipes from selected packs, keeping bilingual fields intact
        new_categories = {}  # Changed from set to dict to store pack metadata
        for pack in all_packs:
            if pack['packId'] in pack_ids:
                # Use pack name as the category for all recipes in this pack
                pack_category = pack.get('packName', {})
                if isinstance(pack_category, dict):
                    pack_category_name = pack_category.get('en') or pack_category.get('no') or 'Imported Pack'
                else:
                    pack_category_name = str(pack_category)
                # Store pack metadata along with category name
                new_categories[pack_category_name] = {
                    'icon': pack.get('packImage', '📦'),
                    'color': pack.get('packColor', '#999999')
                }

                for recipe in pack['recipes']:
                    # Normalize only non-bilingual technical fields, keep titles/descriptions as bilingual dicts
                    r = dict(recipe)
                    # Override category with pack name
                    r['category'] = pack_category_name
                    # Store pack icon for display
                    r['packIcon'] = pack.get('packImage', '📦')
                    # Normalize difficulty if it's a bilingual dict
                    if isinstance(r.get('difficulty'), dict):
                        r['difficulty'] = r['difficulty'].get('en') or r['difficulty'].get('no') or 'Easy'
                    # Ensure time_minutes is set (may be cookTimeMinutes in pack)
                    if 'time_minutes' not in r or not r.get('time_minutes'):
                        r['time_minutes'] = r.get('cookTimeMinutes', 30)
                    recipes_to_import.append(r)

        # Load existing recipes database
        existing_recipes = load_recipes_db()
        existing_ids = {r['id'] for r in existing_recipes}

        # Add new recipes (avoid duplicates)
        imported_count = 0
        for recipe in recipes_to_import:
            if recipe['id'] not in existing_ids:
                existing_recipes.append(recipe)
                imported_count += 1

        # Save updated database
        with open(RECIPES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_recipes, f, ensure_ascii=False, indent=2)

        # Add new categories to categories.json if they don't exist
        if new_categories:
            categories_file = DATA_DIR / 'categories.json'
            existing_cats = []
            if categories_file.exists():
                try:
                    with open(categories_file, 'r', encoding='utf-8') as f:
                        existing_cats = json.load(f)
                except Exception:
                    pass
            existing_cat_codes = {c.get('code', '').lower() for c in existing_cats}
            for cat_name, cat_meta in new_categories.items():
                cat_code = cat_name.lower().replace(' ', '_').replace('&', 'and')
                if cat_code not in existing_cat_codes:
                    existing_cats.append({
                        'code': cat_code,
                        'name_no': cat_name,
                        'name_en': cat_name,
                        'description_no': cat_name,
                        'description_en': cat_name,
                        'icon': cat_meta.get('icon', '📦'),
                        'color': cat_meta.get('color', '#999999')
                    })
                    existing_cat_codes.add(cat_code)
            with open(categories_file, 'w', encoding='utf-8') as f:
                json.dump(existing_cats, f, ensure_ascii=False, indent=2)

        logger.info(f"Imported {imported_count} recipes from {len(pack_ids)} packs")
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'message': f'Imported {imported_count} recipes',
            'new_categories': list(new_categories.keys())
        })

    except Exception as e:
        logger.error(f"Recipe pack import error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipe-packs/imported', methods=['GET'])
def api_get_imported_packs():
    """Get list of imported packs (detected by their categories in recipes_db.json)"""
    try:
        imported_packs = {}
        recipes_db_file = DATA_DIR / 'recipes_db.json'
        if recipes_db_file.exists():
            with open(recipes_db_file, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                for recipe in recipes:
                    cat = recipe.get('category', '')
                    if cat and cat not in imported_packs:
                        imported_packs[cat] = {
                            'category_name': cat,
                            'recipe_count': 0,
                            'icon': recipe.get('packIcon', '📦')
                        }
                    if cat in imported_packs:
                        imported_packs[cat]['recipe_count'] += 1

        return jsonify({
            'success': True,
            'packs': list(imported_packs.values())
        })
    except Exception as e:
        logger.error(f"Error getting imported packs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipe-packs/remove', methods=['POST'])
def api_remove_imported_pack():
    """Remove an imported pack (all recipes with that category)"""
    try:
        data = request.get_json()
        pack_category = data.get('category', '')

        if not pack_category:
            return jsonify({'success': False, 'message': 'No category specified'}), 400

        recipes_db_file = DATA_DIR / 'recipes_db.json'
        removed_count = 0

        if recipes_db_file.exists():
            with open(recipes_db_file, 'r', encoding='utf-8') as f:
                recipes = json.load(f)

            # Filter out recipes from this category
            filtered_recipes = [r for r in recipes if r.get('category', '') != pack_category]
            removed_count = len(recipes) - len(filtered_recipes)

            # Save updated recipes
            with open(recipes_db_file, 'w', encoding='utf-8') as f:
                json.dump(filtered_recipes, f, ensure_ascii=False, indent=2)

            logger.info(f"Removed {removed_count} recipes from pack category '{pack_category}'")

        # Remove category from categories.json if it matches the pack name
        categories_file = DATA_DIR / 'categories.json'
        if categories_file.exists():
            try:
                with open(categories_file, 'r', encoding='utf-8') as f:
                    categories = json.load(f)

                # Filter out categories that match the pack name
                filtered_categories = [c for c in categories if c.get('name_en', '') != pack_category]

                # Save updated categories
                with open(categories_file, 'w', encoding='utf-8') as f:
                    json.dump(filtered_categories, f, ensure_ascii=False, indent=2)

                logger.info(f"Removed category '{pack_category}' from categories.json")
            except Exception as e:
                logger.warning(f"Could not clean up category: {e}")

        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Removed {removed_count} recipes from {pack_category}'
        })

    except Exception as e:
        logger.error(f"Recipe pack removal error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/recipe-packs/manage')
def manage_recipe_packs():
    """Page to manage imported recipe packs"""
    lang = _get_lang()
    recipes = [_normalize_recipe(r, lang) for r in load_recipes_db()]
    return render_template('recipe-packs-manage.html', recipes=recipes)

# ── Personal Recipe Arsenal API ───────────────────────────────────────────────

@app.route('/api/recipes/export')
def api_recipes_export():
    """Export all user recipes as JSON"""
    try:
        recipes = load_recipes_db()
        return jsonify({
            'success': True,
            'recipes': recipes,
            'count': len(recipes)
        })
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipes/import', methods=['POST'])
def api_recipes_import():
    """Import recipes from user-provided JSON file"""
    try:
        data = request.get_json()
        recipes_to_import = data.get('recipes', [])

        if not recipes_to_import:
            return jsonify({'success': False, 'message': 'No recipes provided'}), 400

        # Validate recipe structure
        for recipe in recipes_to_import:
            if not recipe.get('id') or not recipe.get('title'):
                return jsonify({'success': False, 'message': 'Invalid recipe structure'}), 400

        # Load existing recipes
        existing_recipes = load_recipes_db()
        existing_ids = {r['id'] for r in existing_recipes}

        # Import non-duplicate recipes
        imported_count = 0
        for recipe in recipes_to_import:
            if recipe['id'] not in existing_ids:
                existing_recipes.append(recipe)
                imported_count += 1

        # Save updated database
        with open(RECIPES_DB_FILE, 'w', encoding='utf-8') as f:
            json.dump(existing_recipes, f, ensure_ascii=False, indent=2)

        logger.info(f"Imported {imported_count} recipes from user file")
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'message': f'Imported {imported_count} recipes'
        })

    except Exception as e:
        logger.error(f"Recipe import error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

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
