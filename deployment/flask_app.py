#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import json
import os
import logging
import secrets
import requests
from pathlib import Path
from flask import Flask, render_template, jsonify, request, session, redirect, url_for
from datetime import datetime
import sys
from dotenv import load_dotenv

# ── i18n helpers ─────────────────────────────────────────────────────────────

def _load_i18n():
    """Load i18n translations (reload on every request to catch updates)."""
    i18n_path = Path(__file__).parent.parent / 'frontend' / 'static' / 'i18n.json'
    try:
        with open(i18n_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: Could not load i18n.json: {e}")
        return {}

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

# Initialize database (import models first so Base.metadata knows about all tables)
import database.models  # noqa: F401
from database.database import db
db.create_all()

logger = logging.getLogger(__name__)

# Setup logging with safe directory creation
log_dir = Path(__file__).parent.parent / 'logs'
try:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / 'flask_app.log')
    file_handler.setFormatter(
        logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
    )
    logger.addHandler(file_handler)
except Exception:
    pass
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

DATA_DIR = Path(__file__).parent.parent / 'data'
CACHE_DIR = DATA_DIR / 'recipes_cache'

# Static recipe/category seed content (sample_recipes.json, recipe-packs/,
# the base categories.json, pantry_staples.json, dessert/drinks stashes)
# is read from here instead of DATA_DIR. On Railway, DATA_DIR sits on a
# persistent volume that's deliberately never overwritten on redeploy (so
# real household data survives across deploys) - but that also means any
# fix to these static seed files would silently never reach production,
# since the volume's stale copy from whenever it was first created always
# wins. SEED_DIR points at a pristine, always-fresh-from-the-image copy the
# Dockerfile bakes in at /app/data-seed specifically so static content isn't
# subject to the volume's no-clobber protection. Falls back to DATA_DIR
# itself when data-seed doesn't exist (e.g. local dev, where there's no
# volume shadowing to worry about).
SEED_DIR = Path(__file__).parent.parent / 'data-seed'
if not SEED_DIR.exists():
    SEED_DIR = DATA_DIR
PROFILE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

# Certificate paths (relative to the deployment dir where the service runs from)
CERT_FILE = Path(__file__).parent / 'cert.pem'
KEY_FILE = Path(__file__).parent / 'key.pem'

app = Flask(__name__,
    template_folder=str(Path(__file__).parent.parent / 'frontend/templates'),
    static_folder=str(Path(__file__).parent.parent / 'frontend/static'))

# Configuration
FLASK_ENV = os.environ.get('FLASK_ENV', 'development')
IS_PRODUCTION = FLASK_ENV == 'production'

# The app's own developer/admin - NOT a household owner. Gates the in-app
# feedback list specifically to this one account, regardless of which
# household(s) it owns or what role it holds in any of them.
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', '').strip().lower()

app.config['JSON_SORT_KEYS'] = False
app.config['TEMPLATES_AUTO_RELOAD'] = not IS_PRODUCTION
app.config['SECRET_KEY'] = os.environ.get('FLASK_SECRET_KEY', secrets.token_hex(32))

# Security: Use secure cookies in production
app.config['SESSION_COOKIE_SECURE'] = IS_PRODUCTION
app.config['SESSION_COOKIE_HTTPONLY'] = True
app.config['SESSION_COOKIE_SAMESITE'] = 'Lax'

# Disable Jinja2 cache in development for faster iteration
if not IS_PRODUCTION:
    app.jinja_env.cache = None

logger.info(f"Flask templates: {app.template_folder}")
logger.info(f"Flask static: {app.static_folder}")

# ── Context Processors ───────────────────────────────────────────────────────

def _has_azure_creds():
    """Check if Azure credentials are configured."""
    client_id = os.getenv('AZURE_CLIENT_ID', '').strip()
    client_secret = os.getenv('AZURE_CLIENT_SECRET', '').strip()
    tenant_id = os.getenv('AZURE_TENANT_ID', '').strip()
    return bool(client_id and client_secret and tenant_id)

def _send_confirmation_email(user):
    """Email the user a confirmation link via Resend. Same fail-safe pattern
    as _notify_admin_of_feedback below: if RESEND_API_KEY isn't configured,
    log and skip rather than block signup - but note that without an actual
    key set, NO ONE can confirm their email and therefore no one can log in,
    so this must be configured before real users sign up against this build."""
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    if not api_key:
        logger.warning(f"RESEND_API_KEY not set - cannot send confirmation email to {user.email}. "
                        f"This user cannot log in until email confirmation is sent some other way.")
        return False

    from_addr = os.getenv('RESEND_FROM_EMAIL', 'feedback@menuplanner.app').strip()
    confirm_url = url_for('confirm_email_route', token=user.email_confirmation_token, _external=True)
    body = (
        f"Welcome to Menu Planner!\n\n"
        f"Please confirm your email address to activate your account:\n\n"
        f"{confirm_url}\n\n"
        f"If you didn't sign up for Menu Planner, you can ignore this email."
    )
    try:
        resp = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
            json={
                'from': from_addr,
                'to': [user.email],
                'subject': 'Confirm your Menu Planner account',
                'text': body,
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            logger.error(f"Resend confirmation email failed: {resp.status_code} {resp.text}")
            return False
        logger.info(f"Confirmation email sent to {user.email} (Resend id: {resp.json().get('id')})")
        return True
    except Exception as e:
        logger.error(f"Resend confirmation email exception: {e}")
        return False

def _notify_admin_of_feedback(entry):
    """Email ADMIN_EMAIL via Resend when new feedback is submitted, so the
    developer doesn't have to manually check data/feedback.json or dig
    through Railway's dashboard to notice a new tester report. No-ops
    silently (just logs) if RESEND_API_KEY isn't configured yet - this must
    never block or break the actual feedback submission."""
    api_key = os.getenv('RESEND_API_KEY', '').strip()
    if not api_key:
        logger.info("RESEND_API_KEY not set - skipping feedback email notification")
        return

    from_addr = os.getenv('RESEND_FROM_EMAIL', 'feedback@menuplanner.app').strip()
    body = (
        f"New feedback submitted in Menu Planner:\n\n"
        f"Type: {entry['type']}\n"
        f"Title: {entry['title']}\n"
        f"Description: {entry['description']}\n\n"
        f"From: {entry['submitted_by']}\n"
        f"Household: {entry.get('household_id') or 'none'}\n"
        f"Time: {entry['timestamp']}"
    )
    resp = requests.post(
        'https://api.resend.com/emails',
        headers={'Authorization': f'Bearer {api_key}', 'Content-Type': 'application/json'},
        json={
            'from': from_addr,
            'to': [ADMIN_EMAIL],
            'subject': f"New feedback: {entry['title']}",
            'text': body,
        },
        timeout=10,
    )
    if resp.status_code >= 300:
        logger.error(f"Resend feedback notification failed: {resp.status_code} {resp.text}")
    else:
        logger.info(f"Feedback notification emailed to {ADMIN_EMAIL} (Resend id: {resp.json().get('id')})")

_AVATAR_PALETTE = [
    '#F87171', '#FB923C', '#FBBF24', '#A3E635', '#34D399',
    '#22D3EE', '#60A5FA', '#A78BFA', '#F472B6', '#94A3B8',
]

def _avatar_color(label):
    """Deterministic background color for an initial-circle avatar from a name/email."""
    if not label:
        return _AVATAR_PALETTE[0]
    return _AVATAR_PALETTE[sum(ord(c) for c in label) % len(_AVATAR_PALETTE)]

app.jinja_env.globals['avatar_color'] = _avatar_color

MAX_PROFILES_PER_HOUSEHOLD = 6

AVATAR_EMOJI_CHOICES = [
    '🧑', '👩', '👨', '👧', '👦', '🧓', '👴', '👵',
    '🧑‍🍳', '🦸', '🦸‍♀️', '🧙', '🐶', '🐱', '🦊', '🐻',
    '🐼', '🐨', '🦁', '🐸', '🐧', '🦄', '🐙', '🍕',
]

app.jinja_env.globals['avatar_emoji_choices'] = AVATAR_EMOJI_CHOICES

def _avatar_display(label, avatar_type=None, avatar_value=None):
    """Either the member's chosen emoji, or an upper-case initial, for circle avatars."""
    if avatar_type == 'emoji' and avatar_value:
        return avatar_value
    return (label[0].upper() if label else '?')

app.jinja_env.globals['avatar_display'] = _avatar_display

@app.before_request
def _restore_remembered_profile():
    """If this device previously picked a profile and the session lost it
    (new login, expired session), silently restore it from the device cookie
    instead of forcing the picker again."""
    if session.get('user_id') and not session.get('active_profile_id'):
        remembered_id = request.cookies.get('remembered_profile_id')
        if remembered_id:
            household_id = session.get('current_household_id')
            if household_id:
                from core.household_helpers import get_member_by_id
                member = get_member_by_id(remembered_id, household_id)
                if member and member.is_profile:
                    session['active_profile_id'] = str(member.id)
                    session['active_profile_name'] = member.display_name

def current_household_id():
    """Resolve the active household id for this request, picking the user's
    first household if none is set in session yet."""
    user_id = session.get('user_id')
    if not user_id:
        return None

    household_id = session.get('current_household_id')
    if household_id:
        return household_id

    from core.household_helpers import get_user_households
    households = get_user_households(user_id)
    if households:
        household_id = str(households[0].id)
        session['current_household_id'] = household_id
        return household_id

    return None

def current_actor_name():
    """Name to attribute edits/actions to: active profile if one is picked,
    otherwise the logged-in account's email."""
    return session.get('active_profile_name') or session.get('user_email') or 'Unknown'

def acting_role_is_owner():
    """True only if the CURRENTLY ACTING identity is the owner. If a non-owner
    profile is active (e.g. 'Wife', 'Kid'), this is False even though the underlying
    account is the owner - profiles must explicitly re-select 'Owner' (with a password
    check) to act with owner privileges."""
    user_id = session.get('user_id')
    if not user_id:
        return False

    household_id = session.get('current_household_id')
    if not household_id:
        return False

    active_profile_id = session.get('active_profile_id')
    if active_profile_id:
        from core.household_helpers import get_profile_role
        return get_profile_role(active_profile_id, household_id) in ('owner', 'co-owner')

    from core.household_helpers import user_is_household_owner
    return user_is_household_owner(user_id, household_id)

def acting_role_can_edit():
    """True if the CURRENTLY ACTING identity can make changes (regenerate the menu,
    add/edit recipes, etc.) - i.e. anything other than 'viewer'. A 'viewer' profile
    (e.g. a kid) can look at the menu but shouldn't be able to wipe it out by
    regenerating, since that overwrites what the household already shopped for."""
    user_id = session.get('user_id')
    if not user_id:
        return False

    household_id = session.get('current_household_id')
    if not household_id:
        return False

    active_profile_id = session.get('active_profile_id')
    if active_profile_id:
        from core.household_helpers import get_profile_role
        role = get_profile_role(active_profile_id, household_id)
    else:
        from core.household_helpers import get_account_holder_role
        role = get_account_holder_role(user_id, household_id)

    return role in ('owner', 'co-owner', 'editor')

@app.context_processor
def inject_config():
    """Inject configuration and i18n into all templates."""
    lang = _get_lang()
    t = _make_t(lang)

    # Get current user info
    user_email = session.get('user_email')
    user_id = session.get('user_id')
    auth_type = session.get('auth_type')
    is_authenticated = bool(user_id and user_email) or bool(session.get('access_token'))

    household_name = os.getenv('HOUSEHOLD_NAME', 'Menu Planner')
    household_id = session.get('current_household_id')
    is_household_owner = False
    can_edit_menu = True
    is_app_admin = bool(ADMIN_EMAIL and user_email and user_email.strip().lower() == ADMIN_EMAIL)
    active_avatar_type = None
    active_avatar_value = None
    if household_id:
        from core.household_helpers import get_household, get_household_members
        current_household = get_household(household_id)
        if current_household:
            household_name = current_household.name
        if user_id:
            is_household_owner = acting_role_is_owner()
            can_edit_menu = acting_role_can_edit()

            active_profile_id = session.get('active_profile_id')
            members = get_household_members(household_id)
            active_member = None
            if active_profile_id:
                active_member = next((m for m in members if m['member_id'] == str(active_profile_id)), None)
            else:
                active_member = next((m for m in members if m['user_id'] == str(user_id)), None)
            if active_member:
                active_avatar_type = active_member['avatar_type']
                active_avatar_value = active_member['avatar_value']

    return {
        'household_name': household_name,
        'creator': 'nobody174',
        'github_url': 'https://github.com/nobody174/Menu-Planner',
        'patreon_url': 'https://www.patreon.com/c/Nobody174',
        'lang': lang,
        't': t,
        'has_azure_creds': _has_azure_creds(),
        'is_authenticated': is_authenticated,
        'user_email': user_email,
        'user_id': user_id,
        'auth_type': auth_type,
        'active_profile_name': session.get('active_profile_name'),
        'is_household_owner': is_household_owner,
        'can_edit_menu': can_edit_menu,
        'is_app_admin': is_app_admin,
        'active_avatar_type': active_avatar_type,
        'active_avatar_value': active_avatar_value,
    }

# ── Helpers ──────────────────────────────────────────────────────────────────

def load_menu():
    from core.household_paths import menu_file
    household_id = current_household_id()
    if not household_id:
        return None
    path = menu_file(household_id)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return None

def load_recipes_db():
    from core.household_paths import recipes_db_file
    household_id = current_household_id()
    if not household_id:
        return []
    path = recipes_db_file(household_id)
    if path.exists():
        with open(path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return []

def save_recipes_db(recipes):
    from core.household_paths import recipes_db_file
    import tempfile, os
    household_id = current_household_id()
    path = recipes_db_file(household_id)
    # Write to a temp file in the same directory first, then rename atomically
    # so a crash/interrupt mid-write never leaves a partially-written (broken)
    # recipes_db.json behind.
    dir_ = path.parent
    with tempfile.NamedTemporaryFile('w', encoding='utf-8', dir=dir_, delete=False, suffix='.tmp') as tf:
        json.dump(recipes, tf, ensure_ascii=False, indent=2)
        tf.write('\n')
        tmp_path = tf.name
    os.replace(tmp_path, path)

def find_recipe(recipe_id):
    # Search household recipes_db.json first, then global sample_recipes.json
    all_recipes = load_recipes_db()
    sample_path = SEED_DIR / 'sample_recipes.json'
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

@app.route('/edit-recipe/<recipe_id>')
def edit_recipe(recipe_id):
    recipe = find_recipe(recipe_id)
    if not recipe:
        return render_template('error.html', message=f'Recipe not found: {recipe_id}'), 404

    lang = _get_lang()
    recipe = _normalize_recipe(recipe, lang)

    # Format ingredients as one readable line per ingredient (matching the
    # plain-text style Add Recipe already uses), instead of dumping the raw
    # {name, quantity, unit} structure as JSON for someone to hand-edit.
    ingredients_list = recipe.get('ingredients_included', recipe.get('ingredients', []))
    ingredient_lines = []
    for ing in ingredients_list:
        if isinstance(ing, dict):
            qty = ing.get('quantity', '')
            unit = ing.get('unit', '')
            name = ing.get('name', '')
            prefix = ' '.join(str(p) for p in (qty, unit) if p)
            ingredient_lines.append(f"{prefix} {name}".strip() if prefix else name)
        else:
            ingredient_lines.append(str(ing))
    ingredients_text = '\n'.join(ingredient_lines)

    # Format instructions - _normalize_recipe() above already flattened these
    # to a list of {'step': N, 'description': '...'} dicts, so pull out the
    # plain text rather than str()-ing the dicts themselves (which used to
    # dump raw Python dict literals like "{'step': 1, 'description': '...'}"
    # straight into the textarea).
    instructions = recipe.get('instructions', [])
    lines = []
    for i, step in enumerate(instructions):
        if isinstance(step, dict):
            lines.append(str(step.get('description', '')))
        else:
            lines.append(str(step))
    instructions_text = '\n'.join(lines)

    logger.info(f"Edit recipe page accessed: {recipe_id}")
    return render_template('edit_recipe.html', recipe=recipe, ingredients_text=ingredients_text, instructions_text=instructions_text)

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
        from core.household_paths import recipes_db_file
        all_recipes_raw = []
        # Load from all sources: sample recipes, imported recipes, and recipe packs
        for db_path in (SEED_DIR / 'sample_recipes.json', recipes_db_file(current_household_id())):
            if db_path.exists():
                try:
                    with open(db_path, 'r', encoding='utf-8') as f:
                        all_recipes_raw.extend(json.load(f))
                except Exception:
                    pass
        # Also load from recipe packs (which have bilingual data)
        packs_dir = SEED_DIR / 'recipe-packs'
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

    from core.household_paths import load_pantry
    pantry = set(load_pantry(current_household_id()))
    for category, items in shopping.items():
        for item in items:
            item['in_pantry'] = item.get('ingredient', '').strip().lower() in pantry

    return render_template('shopping.html', shopping_list=shopping, pantry=sorted(pantry))

@app.route('/api/pantry', methods=['GET'])
def api_get_pantry():
    """Pantry items in the CURRENT display language only - items that exist
    in both languages identically (e.g. 'salt') always show; items unique to
    the other language are hidden, even though they're still stored (adding
    'lemon' in English also silently stores 'sitron' so it's there if the
    household switches to Norwegian later)."""
    from core.household_paths import load_pantry, pantry_item_language
    lang = _get_lang()
    pantry = load_pantry(current_household_id())
    visible = [p for p in pantry if pantry_item_language(p) in (lang, 'both')]
    return jsonify({'success': True, 'pantry': sorted(visible)})

@app.route('/api/pantry/add', methods=['POST'])
def api_add_pantry_item():
    """Adding a known staple also adds its translation in the other language
    (e.g. adding 'lemon' silently also stores 'sitron'), so the pantry stays
    in sync no matter which language the household views it in later. Items
    with no known translation (anything custom the household typed) are just
    stored as-is."""
    from core.household_paths import load_pantry, save_pantry, append_activity, pantry_item_translation
    data = request.get_json() or {}
    item = (data.get('item') or '').strip().lower()
    if not item:
        return jsonify({'success': False, 'message': 'No item provided'}), 400

    household_id = current_household_id()
    pantry = load_pantry(household_id)
    added = False
    if item not in pantry:
        pantry.append(item)
        added = True
    translation = pantry_item_translation(item)
    if translation and translation not in pantry:
        pantry.append(translation)
        added = True
    if added:
        save_pantry(household_id, pantry)
        append_activity(household_id, current_actor_name(), f"Added '{item}' to pantry")

    lang = _get_lang()
    from core.household_paths import pantry_item_language
    visible = [p for p in pantry if pantry_item_language(p) in (lang, 'both')]
    return jsonify({'success': True, 'pantry': sorted(visible)})

@app.route('/api/pantry/remove', methods=['POST'])
def api_remove_pantry_item():
    """Removing a known staple also removes its translation in the other
    language, so e.g. removing 'sugar' also removes 'sukker'."""
    from core.household_paths import load_pantry, save_pantry, append_activity, pantry_item_translation
    data = request.get_json() or {}
    item = (data.get('item') or '').strip().lower()
    if not item:
        return jsonify({'success': False, 'message': 'No item provided'}), 400

    household_id = current_household_id()
    translation = pantry_item_translation(item)
    to_remove = {item}
    if translation:
        to_remove.add(translation)
    pantry = [p for p in load_pantry(household_id) if p not in to_remove]
    save_pantry(household_id, pantry)
    append_activity(household_id, current_actor_name(), f"Removed '{item}' from pantry")

    lang = _get_lang()
    from core.household_paths import pantry_item_language
    visible = [p for p in pantry if pantry_item_language(p) in (lang, 'both')]
    return jsonify({'success': True, 'pantry': sorted(visible)})

def _load_household_categories(household_id):
    from core.household_paths import categories_file
    path = categories_file(household_id)
    if not path.exists():
        return []
    with open(path, 'r', encoding='utf-8') as f:
        return json.load(f)

def _save_household_categories(household_id, categories):
    from core.household_paths import categories_file
    path = categories_file(household_id)
    with open(path, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)

@app.route('/api/categories/add', methods=['POST'])
def api_add_category():
    """Owner-only: add a custom category to this household's category list."""
    if not acting_role_is_owner():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({'success': False, 'message': 'No household selected'}), 400

    data = request.get_json() or {}
    name = (data.get('name') or '').strip()
    icon = (data.get('icon') or '🍽️').strip()
    if not name:
        return jsonify({'success': False, 'message': 'Category name required'}), 400

    categories = _load_household_categories(household_id)
    code = name.lower().replace(' ', '_')
    if any(c.get('code') == code for c in categories):
        return jsonify({'success': False, 'message': 'Category already exists'}), 400

    categories.append({
        'code': code,
        'name_no': name,
        'name_en': name,
        'description_no': '',
        'description_en': '',
        'icon': icon,
        'color': '#999999',
    })
    _save_household_categories(household_id, categories)
    from core.household_paths import append_activity
    append_activity(household_id, current_actor_name(), f"Added category '{name}'")

    return jsonify({'success': True, 'categories': _sort_categories(categories)})

@app.route('/api/categories/rename', methods=['POST'])
def api_rename_category():
    """Owner-only: rename a category in this household's category list."""
    if not acting_role_is_owner():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({'success': False, 'message': 'No household selected'}), 400

    data = request.get_json() or {}
    code = (data.get('code') or '').strip()
    new_name = (data.get('name') or '').strip()
    if not code or not new_name:
        return jsonify({'success': False, 'message': 'Category code and new name required'}), 400

    categories = _load_household_categories(household_id)
    found = False
    for c in categories:
        if c.get('code') == code:
            c['name_no'] = new_name
            c['name_en'] = new_name
            found = True
            break

    if not found:
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    _save_household_categories(household_id, categories)
    from core.household_paths import append_activity
    append_activity(household_id, current_actor_name(), f"Renamed category to '{new_name}'")

    return jsonify({'success': True, 'categories': _sort_categories(categories)})

@app.route('/api/categories/remove', methods=['POST'])
def api_remove_category():
    """Owner-only: remove a category from this household's category list."""
    if not acting_role_is_owner():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({'success': False, 'message': 'No household selected'}), 400

    data = request.get_json() or {}
    code = (data.get('code') or '').strip()
    if not code:
        return jsonify({'success': False, 'message': 'Category code required'}), 400

    categories = _load_household_categories(household_id)
    remaining = [c for c in categories if c.get('code') != code]
    if len(remaining) == len(categories):
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    _save_household_categories(household_id, remaining)
    from core.household_paths import append_activity, mark_category_removed
    mark_category_removed(household_id, code)
    append_activity(household_id, current_actor_name(), f"Removed category '{code}'")

    return jsonify({'success': True, 'categories': _sort_categories(remaining)})

@app.route('/api/categories/merge', methods=['POST'])
def api_merge_category():
    """Owner-only: move any recipes tagged with `from_code` over to
    `into_code`'s name (in whichever language each recipe's category string
    happens to be in), then remove the now-empty `from_code` category."""
    if not acting_role_is_owner():
        return jsonify({'success': False, 'message': 'Permission denied'}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({'success': False, 'message': 'No household selected'}), 400

    data = request.get_json() or {}
    from_code = (data.get('from_code') or '').strip()
    into_code = (data.get('into_code') or '').strip()
    if not from_code or not into_code:
        return jsonify({'success': False, 'message': 'Both categories required'}), 400
    if from_code == into_code:
        return jsonify({'success': False, 'message': 'Cannot merge a category into itself'}), 400

    categories = _load_household_categories(household_id)
    from_cat = next((c for c in categories if c.get('code') == from_code), None)
    into_cat = next((c for c in categories if c.get('code') == into_code), None)
    if not from_cat or not into_cat:
        return jsonify({'success': False, 'message': 'Category not found'}), 404

    from_names = {from_cat.get('name_en', ''), from_cat.get('name_no', '')}
    target_lang = _get_lang()
    target_name = into_cat.get(f'name_{target_lang}') or into_cat.get('name_en') or into_cat['code']

    recipes = load_recipes_db()
    moved = 0
    for r in recipes:
        if r.get('category') in from_names:
            r['category'] = target_name
            moved += 1
    if moved:
        save_recipes_db(recipes)

    remaining = [c for c in categories if c.get('code') != from_code]
    _save_household_categories(household_id, remaining)
    from core.household_paths import append_activity, mark_category_removed
    mark_category_removed(household_id, from_code)
    append_activity(household_id, current_actor_name(),
                     f"Merged category '{from_cat.get('name_en')}' into '{into_cat.get('name_en')}' ({moved} recipe(s) moved)")

    return jsonify({'success': True, 'categories': _sort_categories(remaining), 'moved': moved})

@app.route('/feedback')
def feedback_page():
    """Simple feedback form for trial testers - any logged-in user can report."""
    if not session.get('user_id'):
        return redirect(url_for('login_page'))
    return render_template('feedback.html', success=request.args.get('success'))

@app.route('/api/feedback', methods=['POST'])
def api_submit_feedback():
    """Save feedback to a single append-only JSON file - simple enough for a
    handful of trial testers; not meant to scale past that without revisiting."""
    if not session.get('user_id'):
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json() or {}
    feedback_type = (data.get('type') or 'other').strip()
    title = (data.get('title') or '').strip()
    description = (data.get('description') or '').strip()
    if not title or not description:
        return jsonify({'success': False, 'message': 'Title and description required'}), 400

    from datetime import datetime
    entry = {
        'timestamp': datetime.now().isoformat(),
        'type': feedback_type,
        'title': title,
        'description': description,
        'submitted_by': session.get('user_email', 'unknown'),
        'household_id': session.get('current_household_id'),
    }

    feedback_file = DATA_DIR / 'feedback.json'
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.append(entry)
    with open(feedback_file, 'w', encoding='utf-8') as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    if ADMIN_EMAIL:
        try:
            _notify_admin_of_feedback(entry)
        except Exception as e:
            logger.error(f"Feedback admin notification failed: {e}")

    return jsonify({'success': True})

@app.route('/feedback/list')
def feedback_list_page():
    """App-developer-only view of all submitted feedback, newest first. Gated
    by ADMIN_EMAIL specifically - NOT the same thing as being a household
    owner, which is a per-household role any signed-up user can hold."""
    user_email = (session.get('user_email') or '').strip().lower()
    if not ADMIN_EMAIL or user_email != ADMIN_EMAIL:
        return render_template('error.html', message='Not authorized'), 403

    feedback_file = DATA_DIR / 'feedback.json'
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, 'r', encoding='utf-8') as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.reverse()  # newest first
    return render_template('feedback_list.html', entries=entries)

@app.route('/add-recipe')
def add_recipe_page():
    return render_template('add-recipe.html')

@app.route('/all-recipes')
def all_recipes_page():
    lang = _get_lang()
    # Load both household recipes AND shared sample recipes (same as MenuGenerator does)
    all_recipes = []
    sample_recipes_path = SEED_DIR / 'sample_recipes.json'
    if sample_recipes_path.exists():
        try:
            with open(sample_recipes_path, 'r', encoding='utf-8') as f:
                all_recipes.extend(json.load(f))
        except Exception:
            pass
    all_recipes.extend(load_recipes_db())
    recipes = [_normalize_recipe(r, lang) for r in all_recipes]
    return render_template('all-recipes.html', recipes=recipes)

@app.route('/settings')
def settings_page():
    """Owner-only: account/referral details and the activity log live here, so
    non-owner profiles (kids, viewers, editors) have no business seeing this page."""
    household_id_for_check = session.get('current_household_id')
    if household_id_for_check and not acting_role_is_owner():
        return redirect(url_for('dashboard'))

    activity_log = []
    household_id = current_household_id()
    if household_id and session.get('user_id') and acting_role_is_owner():
        from core.household_paths import load_activity
        activity_log = load_activity(household_id)[:50]

    referral_code = None
    user_id = session.get('user_id')
    if user_id:
        from core.auth_helpers import get_user_by_email
        user = get_user_by_email(session.get('user_email', ''))
        if user:
            referral_code = user.referral_code

    categories = []
    if household_id:
        from core.household_paths import categories_file
        path = categories_file(household_id)
        if path.exists():
            with open(path, 'r', encoding='utf-8') as f:
                raw_cats = json.load(f)
            lang = _get_lang()
            # Skip pack-name pseudo-categories (imported: true) here too -
            # same reasoning as /api/categories: recipes never carry one of
            # these as their actual category anymore (see B4b), so showing
            # them in the manage-categories list would let an owner try to
            # rename/merge/delete something that was never a real category.
            for cat in raw_cats:
                if cat.get('imported'):
                    continue
                translated = dict(cat)
                translated['name'] = cat.get(f'name_{lang}') or cat.get('name_en') or cat.get('code')
                categories.append(translated)
            categories = _sort_categories(categories)

    has_pin = False
    if user_id:
        from core.auth_helpers import get_user_by_email as _get_user_by_email
        _user = _get_user_by_email(session.get('user_email', ''))
        has_pin = bool(_user and _user.pin_hash)

    pantry = []
    if household_id:
        from core.household_paths import load_pantry, pantry_item_language
        lang = _get_lang()
        pantry = sorted(p for p in load_pantry(household_id) if pantry_item_language(p) in (lang, 'both'))

    return render_template('settings.html', activity_log=activity_log, referral_code=referral_code,
                            categories=categories, has_pin=has_pin, pantry=pantry)

@app.route('/api/account/set-pin', methods=['POST'])
def api_set_pin():
    """Owner-only: set or change the shared-device PIN used by the profile picker."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    data = request.get_json() or {}
    pin = (data.get('pin') or '').strip()

    from core.auth_helpers import set_pin
    success, message = set_pin(user_id, pin)
    status = 200 if success else 400
    return jsonify({'success': success, 'message': message}), status

@app.route('/api/account/clear-pin', methods=['POST'])
def api_clear_pin():
    """Owner-only: remove the PIN, falling back to the full account password."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'success': False, 'message': 'Not authenticated'}), 401

    from core.auth_helpers import clear_pin
    success, message = clear_pin(user_id)
    return jsonify({'success': success, 'message': message})

# ── Household/Team Management Routes ──────────────────────────────────────────

@app.route('/household-settings')
def household_settings():
    """View and manage household settings. Owner-only: this is a dinner-planning app,
    not a playground, so non-owner members have no business here even to look."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    from core.household_helpers import get_user_households, get_household_members, get_household

    household_id_for_check = session.get('current_household_id')
    if household_id_for_check and not acting_role_is_owner():
        return redirect(url_for('settings_page', error='Only the household owner can access household settings'))

    # Get all user's households
    all_households = get_user_households(user_id)

    # Try to get current household (from session or first one)
    current_household_id = session.get('current_household_id')
    current_household = None

    if current_household_id:
        current_household = get_household(current_household_id)

    if not current_household and all_households:
        current_household = all_households[0]
        session['current_household_id'] = str(current_household.id)

    error = request.args.get('error')
    success = request.args.get('success')

    members = []
    owner_email = ''
    can_manage = False
    is_owner = False
    other_households = []

    if current_household:
        members = get_household_members(str(current_household.id))

        # Find owner email
        for member in members:
            if member['role'] == 'owner':
                owner_email = member['email']
                break

        # Check permissions - keyed off the ACTING identity, not just the account,
        # so a co-owner profile gets the same management rights as the owner.
        is_owner = acting_role_is_owner()
        user_member = next((m for m in members if m['user_id'] == user_id), None)
        can_manage = is_owner or (user_member and user_member['role'] == 'editor')

        # Get other households
        other_households = [h for h in all_households if str(h.id) != str(current_household.id)]

    profile_count = sum(1 for m in members if m['is_profile'])

    return render_template('household-settings.html',
                         current_household=current_household,
                         members=members,
                         owner_email=owner_email,
                         can_manage=can_manage,
                         is_owner=is_owner,
                         other_households=other_households,
                         profile_count=profile_count,
                         max_profiles=MAX_PROFILES_PER_HOUSEHOLD,
                         error=error,
                         success=success)

@app.route('/household/create', methods=['POST'])
def create_household_handler():
    """Create a new household."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    from core.household_helpers import create_household

    household_name = request.form.get('household_name', '').strip()
    success, result, household_id = create_household(user_id, household_name)

    if success:
        session['current_household_id'] = household_id
        return redirect(url_for('household_settings', success='Household created successfully'))
    else:
        return redirect(url_for('household_settings', error=result))

@app.route('/household/set-current', methods=['POST'])
def set_current_household():
    """Switch to a different household."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    household_id = request.form.get('household_id')

    from core.household_helpers import user_can_access_household

    if user_can_access_household(user_id, household_id):
        session['current_household_id'] = household_id
        return redirect(url_for('household_settings', success='Switched household'))
    else:
        return redirect(url_for('household_settings', error='Access denied'))

@app.route('/household/update', methods=['POST'])
def update_household_handler():
    """Update household details."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    household_id = session.get('current_household_id')
    if not household_id:
        return redirect(url_for('household_settings', error='No household selected'))

    from core.household_helpers import update_household

    if not acting_role_is_owner():
        return redirect(url_for('household_settings', error='Permission denied'))

    household_name = request.form.get('household_name', '').strip()

    name_to_update = household_name if household_name else None
    success, result = update_household(household_id, name=name_to_update)

    if success:
        return redirect(url_for('household_settings', success='Household updated'))
    else:
        return redirect(url_for('household_settings', error=result))

@app.route('/household/delete', methods=['POST'])
def delete_household_handler():
    """Delete household (owner only)."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    household_id = session.get('current_household_id')
    if not household_id:
        return redirect(url_for('household_settings', error='No household selected'))

    from core.household_helpers import delete_household

    success, result = delete_household(household_id, user_id)

    if success:
        session.pop('current_household_id', None)
        return redirect(url_for('household_settings', success='Household deleted'))
    else:
        return redirect(url_for('household_settings', error=result))

@app.route('/profile-picker')
def profile_picker():
    """Show 'who's using this' profile picker if the current household has profiles."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    from core.household_helpers import get_user_households, get_household_members

    all_households = get_user_households(user_id)
    current_household_id = session.get('current_household_id')
    current_household = None

    if current_household_id:
        from core.household_helpers import get_household
        current_household = get_household(current_household_id)

    if not current_household and all_households:
        current_household = all_households[0]
        session['current_household_id'] = str(current_household.id)

    if not current_household:
        return redirect(url_for('household_settings', error='Create a household to get started'))

    members = get_household_members(str(current_household.id))

    if not any(m['is_profile'] for m in members):
        return redirect('/')

    owner_password_error = request.args.get('owner_password_error')
    from core.auth_helpers import get_user_by_email
    owner_account = get_user_by_email(session.get('user_email', ''))
    owner_has_pin = bool(owner_account and owner_account.pin_hash)
    return render_template('profile-picker.html', household=current_household, members=members,
                            owner_password_error=owner_password_error, owner_has_pin=owner_has_pin)

@app.route('/profile-picker/select', methods=['POST'])
def select_profile():
    """Set the active profile for this session after picking from the picker."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    member_id = request.form.get('member_id')
    is_account_holder = request.form.get('is_account_holder')

    if is_account_holder:
        from core.auth_helpers import get_user_by_email, verify_pin, authenticate_user
        user = get_user_by_email(session.get('user_email', ''))

        if user and user.pin_hash:
            pin = request.form.get('owner_pin', '')
            if not verify_pin(user_id, pin):
                return redirect(url_for('profile_picker', owner_password_error='Incorrect PIN'))
        else:
            password = request.form.get('owner_password', '')
            success, _ = authenticate_user(session.get('user_email', ''), password)
            if not success:
                return redirect(url_for('profile_picker', owner_password_error='Incorrect password'))

        household_id = session.get('current_household_id')
        from core.household_helpers import get_household_members
        owner_name = session.get('user_email')
        if household_id:
            owner_member = next((m for m in get_household_members(household_id) if m['user_id'] == user_id), None)
            if owner_member:
                owner_name = owner_member['display_name']

        session.pop('active_profile_id', None)
        session['active_profile_name'] = owner_name
        response = redirect('/')
        response.delete_cookie('remembered_profile_id')
        return response

    household_id = session.get('current_household_id')
    from core.household_helpers import get_member_by_id
    member = get_member_by_id(member_id, household_id)

    if not member or not member.is_profile:
        return redirect(url_for('profile_picker', error='Profile not found'))

    session['active_profile_id'] = str(member.id)
    session['active_profile_name'] = member.display_name

    response = redirect('/')
    response.set_cookie('remembered_profile_id', str(member.id),
                         max_age=PROFILE_COOKIE_MAX_AGE, httponly=True, samesite='Lax')
    return response

@app.route('/household/add-profile', methods=['POST'])
def add_household_profile():
    """Add a lightweight member profile (no login of its own) to the household."""
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login_page'))

    household_id = session.get('current_household_id')
    if not household_id:
        return redirect(url_for('household_settings', error='No household selected'))

    from core.household_helpers import create_profile, get_profiles

    if not acting_role_is_owner():
        return redirect(url_for('household_settings', error='Permission denied'))

    if len(get_profiles(household_id)) >= MAX_PROFILES_PER_HOUSEHOLD:
        return redirect(url_for('household_settings', error=f'This household already has the maximum of {MAX_PROFILES_PER_HOUSEHOLD} profiles'))

    display_name = request.form.get('display_name', '').strip()
    role = request.form.get('role', 'viewer')

    success, result, member_id = create_profile(household_id, display_name, role)

    if success:
        return redirect(url_for('household_settings', success=result))
    else:
        return redirect(url_for('household_settings', error=result))

# API routes for household management
@app.route('/api/household/remove-member', methods=['POST'])
def api_remove_household_member():
    """API: Remove household member."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    household_id = session.get('current_household_id')
    member_id = request.form.get('member_id')

    from core.household_helpers import remove_household_member

    if not acting_role_is_owner():
        return jsonify({'error': 'Permission denied'}), 403

    success, message = remove_household_member(household_id, member_id, user_id)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 400

@app.route('/api/profile/set-avatar', methods=['POST'])
def api_set_avatar():
    """Set an emoji avatar for a member. Allowed for: the owner managing any member,
    or the currently active identity setting its own avatar (low-stakes, no permission gate needed)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    household_id = session.get('current_household_id')
    member_id = request.form.get('member_id')
    emoji = request.form.get('emoji', '')

    if emoji not in AVATAR_EMOJI_CHOICES:
        return jsonify({'error': 'Invalid avatar choice'}), 400

    is_own_active_identity = member_id == session.get('active_profile_id')
    if not is_own_active_identity and not acting_role_is_owner():
        return jsonify({'error': 'Permission denied'}), 403

    from core.household_helpers import set_member_avatar
    success, message = set_member_avatar(member_id, household_id, emoji)

    if success:
        return jsonify({'success': True, 'avatar': emoji})
    else:
        return jsonify({'error': message}), 400

@app.route('/api/household/rename-member', methods=['POST'])
def api_rename_member():
    """API: Rename a household member (profile or the owner's own display name)."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    if not acting_role_is_owner():
        return jsonify({'error': 'Permission denied'}), 403

    household_id = session.get('current_household_id')
    member_id = request.form.get('member_id')
    display_name = request.form.get('display_name', '')

    from core.household_helpers import rename_member, get_member_by_id
    success, message = rename_member(member_id, household_id, display_name)

    if success:
        member = get_member_by_id(member_id, household_id)
        if member and member.is_profile and session.get('active_profile_id') == str(member.id):
            session['active_profile_name'] = member.display_name
        elif member and not member.is_profile and member.user_id == user_id:
            session['active_profile_name'] = member.display_name
        return redirect(url_for('household_settings', success='Renamed'))
    else:
        return redirect(url_for('household_settings', error=message))

@app.route('/api/household/update-member-role', methods=['POST'])
def api_update_member_role():
    """API: Update member role."""
    user_id = session.get('user_id')
    if not user_id:
        return jsonify({'error': 'Not authenticated'}), 401

    household_id = session.get('current_household_id')
    member_id = request.form.get('member_id')
    new_role = request.form.get('role')

    from core.household_helpers import update_member_role

    success, message = update_member_role(household_id, member_id, new_role, user_id)

    if success:
        return jsonify({'success': True, 'message': message})
    else:
        return jsonify({'error': message}), 403

@app.route('/api/check-azure-creds')
def check_azure_creds():
    """API endpoint to check if Azure credentials are configured."""
    return jsonify({'has_creds': _has_azure_creds()})

# ── Auth routes ───────────────────────────────────────────────────────────────

# Email/Password Authentication Routes
@app.route('/login-page')
def login_page():
    """Render login page."""
    error = request.args.get('error')
    return render_template('login.html', error=error, email=request.args.get('email', ''))

@app.route('/login', methods=['POST'])
def login_local():
    """Handle local email/password login."""
    from core.auth_helpers import authenticate_user
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')

    if not email or not password:
        return render_template('login.html', error='Email and password required', email=email), 400

    success, result = authenticate_user(email, password)
    if not success:
        if result == 'EMAIL_NOT_CONFIRMED':
            return render_template('login.html', email=email, unconfirmed_email=email,
                                    error='Please confirm your email before logging in.'), 401
        return render_template('login.html', error=result, email=email), 401

    user = result
    session['user_id'] = str(user.id)
    session['user_email'] = user.email
    session['auth_type'] = 'local'
    session.pop('active_profile_id', None)
    logger.info(f"User logged in (local): {user.email}")
    return redirect(url_for('profile_picker'))

@app.route('/confirm-email/<token>')
def confirm_email_route(token):
    """Land here from the link in the confirmation email. One-time use -
    the token is cleared on success, so a second click just shows the
    already-confirmed case rather than erroring."""
    from core.auth_helpers import confirm_email
    success, result = confirm_email(token)
    if not success:
        return render_template('login.html', error=result), 400
    return render_template('login.html', success='Email confirmed! You can now log in.', email=result.email)

@app.route('/resend-confirmation', methods=['POST'])
def resend_confirmation():
    """Re-send the confirmation email with a fresh token - the fallback for
    a tester whose first email landed in spam or was sent to a typo'd
    address they've since corrected via a new signup."""
    from core.auth_helpers import regenerate_confirmation_token
    email = request.form.get('email', '').strip()
    if not email:
        return render_template('login.html', error='Email required'), 400

    success, result = regenerate_confirmation_token(email)
    if not success:
        return render_template('login.html', error=result, email=email), 400

    _send_confirmation_email(result)
    logger.info(f"Resent confirmation email to {result.email}")
    return render_template('login.html', success='Confirmation email resent - please check your inbox.', email=email)

@app.route('/welcome')
def welcome():
    """Promo/demo landing page shown to referral-link visitors before they hit the signup form."""
    return render_template('welcome.html', ref=request.args.get('ref', ''))

@app.route('/signup')
def signup():
    """Render signup page."""
    error = request.args.get('error')
    ref = request.args.get('ref', '')
    if ref and not request.args.get('from_welcome'):
        return redirect(url_for('welcome', ref=ref))
    return render_template('signup.html', error=error, email=request.args.get('email', ''), ref=ref)

@app.route('/signup', methods=['POST'])
def signup_local():
    """Handle local user registration."""
    from core.auth_helpers import create_user
    email = request.form.get('email', '').strip()
    password = request.form.get('password', '')
    password_confirm = request.form.get('password_confirm', '')
    ref = request.form.get('ref', '').strip()

    if not email or not password or not password_confirm:
        return render_template('signup.html', error='All fields required', email=email, ref=ref), 400

    if password != password_confirm:
        return render_template('signup.html', error='Passwords do not match', email=email, ref=ref), 400

    success, result, user_id = create_user(email, password, referred_by_code=ref or None)
    if not success:
        return render_template('signup.html', error=result, email=email, ref=ref), 400

    user = result
    logger.info(f"New user registered (pending email confirmation): {user.email}")
    _send_confirmation_email(user)
    return render_template('signup.html', email=email, ref=ref, confirmation_sent=True)

# Azure/MSAL Authentication Routes
@app.route('/login-azure')
def login_azure():
    """Initiate Azure/Microsoft login flow."""
    try:
        from auth import build_msal_app, get_auth_url
        msal_app = build_msal_app(_redirect_uri())
        flow = get_auth_url(msal_app, _redirect_uri())
        session['auth_flow'] = flow
        logger.info("User redirecting to Microsoft login")
        return redirect(flow['auth_uri'])
    except Exception as e:
        logger.error(f"Azure login error: {e}")
        return render_template('login.html', error='Azure login not configured'), 500

@app.route('/login')
def login():
    """Redirect to login page (for backward compatibility)."""
    return redirect(url_for('login_page'))

@app.route('/callback')
def callback():
    """Handle Azure/MSAL callback."""
    try:
        from auth import build_msal_app, acquire_token_by_auth_code_flow, get_user_info
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
        session['auth_type'] = 'azure'

        try:
            user = get_user_info(result['access_token'])
            session['user_name'] = user.get('displayName', user.get('userPrincipalName', 'User'))
            session['user_email'] = user.get('userPrincipalName', '')
        except Exception:
            session['user_name'] = 'User'
            session['user_email'] = ''

        logger.info(f"User authenticated (Azure): {session.get('user_email')}")
        return redirect('/')

    except Exception as e:
        logger.error(f"Callback exception: {e}")
        return render_template('error.html', message=f'Authentication error: {str(e)}'), 500

@app.route('/logout')
def logout():
    """Log out user (handles both local and Azure auth)."""
    user_email = session.get('user_email', 'User')
    auth_type = session.get('auth_type', 'unknown')
    session.clear()
    logger.info(f"User logged out ({auth_type}): {user_email}")
    return redirect('/')

@app.route('/api/user')
def api_user():
    """Get current user info."""
    user_id = session.get('user_id')
    user_email = session.get('user_email')
    auth_type = session.get('auth_type')

    if user_id and user_email:
        return jsonify({
            'authenticated': True,
            'user_id': user_id,
            'email': user_email,
            'auth_type': auth_type or 'unknown'
        })

    # Fallback for Azure-only sessions (legacy)
    if session.get('access_token'):
        try:
            from auth import is_authorised
            if is_authorised():
                return jsonify({
                    'authenticated': True,
                    'email': session.get('user_email', ''),
                    'auth_type': 'azure'
                })
        except Exception:
            pass

    return jsonify({'authenticated': False})

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
    if not acting_role_can_edit():
        return jsonify({'status': 'error', 'message': 'Viewers cannot regenerate the menu'}), 403

    try:
        from core.menu_generator import MenuGenerator
        data = request.get_json() or {}
        selected_categories = data.get('categories') or data.get('selected_categories') or ['Quick Dinners', 'Fish & Seafood', 'Vegetarian']
        favorite_recipe_ids = data.get('favorite_recipe_ids', [])
        logger.info(f"Generating menu with categories: {selected_categories}, favorites: {len(favorite_recipe_ids)}")
        generator = MenuGenerator(selected_categories=selected_categories, household_id=current_household_id(), favorite_recipe_ids=favorite_recipe_ids)
        menu = generator.run(num_dinners=6, save=True)

        from core.household_paths import append_activity
        append_activity(current_household_id(), current_actor_name(), "Regenerated the weekly menu")

        logger.info("Menu regenerated via API")
        return jsonify({'status': 'success', 'menu': menu})
    except Exception as e:
        import traceback
        logger.error(f"Menu regeneration failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({'status': 'error', 'message': str(e)}), 500

def _sort_categories(categories):
    """Favorites always sorts first; everything else is alphabetical by
    display name."""
    def sort_key(c):
        if c.get('code') == 'favorites':
            return (-1, '')
        return (0, c.get('name', c.get('name_en', '')).lower())
    return sorted(categories, key=sort_key)

@app.route('/api/categories')
def get_categories():
    """Get all available categories from this household's categories.json, translated to current language"""
    lang = _get_lang()
    household_id = current_household_id()
    if household_id:
        from core.household_paths import categories_file as _categories_file
        categories_file = _categories_file(household_id)
    else:
        categories_file = Path(__file__).parent.parent / 'data' / 'categories.json'
    categories = []

    # Add Favorites as a special first category (client-side only, stored in localStorage)
    favorites_name = 'Favorites' if lang == 'en' else 'Favoritter'
    categories.append({
        'code': 'favorites',
        'name': favorites_name,  # This is what gets passed back as the category value
        'icon': '⭐'
    })

    if categories_file.exists():
        try:
            with open(categories_file, 'r', encoding='utf-8') as f:
                raw_cats = json.load(f)
                # Translate to current language. Skip pack-name pseudo-categories
                # (imported: true) - recipes now keep their own real dish-type
                # category through import (see B4b), so a recipe can never have
                # one of these as its category anymore. Selecting one in the
                # dropdown would always show an empty list, which is confusing -
                # better to not offer it at all than show a dead-end option.
                for cat in raw_cats:
                    if cat.get('imported'):
                        continue
                    translated = dict(cat)
                    # Add 'name' field with the translated category name
                    translated['name'] = cat.get(f'name_{lang}') or cat.get('name_en') or cat.get('code')
                    categories.append(translated)
        except Exception as e:
            logger.error(f"Error loading categories: {e}")
    return jsonify(_sort_categories(categories))

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
        save_recipes_db(recipes)

        from core.household_paths import append_activity
        append_activity(current_household_id(), current_actor_name(), f"Added recipe '{recipe['title']}'")

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

        save_recipes_db(recipes)

        from core.household_paths import append_activity
        append_activity(current_household_id(), current_actor_name(), f"Deleted recipe '{recipe_id}'")

        logger.info(f"Deleted recipe: {recipe_id}")
        return jsonify({'status': 'success', 'message': f'Recipe {recipe_id} deleted'})
    except Exception as e:
        logger.error(f"Delete recipe error: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500

@app.route('/api/edit-recipe', methods=['POST'])
def api_edit_recipe():
    """Edit an existing recipe in recipes_db.json by ID"""
    try:
        data = request.get_json() or {}
        recipe_id = data.get('recipe_id')

        if not recipe_id:
            return jsonify({'status': 'error', 'message': 'recipe_id is required'}), 400

        # Validate required fields
        title = data.get('title', '').strip()
        ingredients = data.get('ingredients', [])

        if not title or not ingredients:
            return jsonify({'status': 'error', 'message': 'Title and ingredients are required'}), 400

        recipes = load_recipes_db()
        recipe_found = False

        # Find and update the recipe
        for i, recipe in enumerate(recipes):
            if recipe.get('id') == recipe_id:
                # Update all provided fields
                recipes[i]['title'] = title
                recipes[i]['description'] = data.get('description', '')
                recipes[i]['difficulty'] = _normalize_difficulty(data.get('difficulty', 'Easy'))
                recipes[i]['time_minutes'] = data.get('time_minutes', 30)
                recipes[i]['category'] = data.get('category', recipe.get('category', 'HomeMade'))
                recipes[i]['ingredients'] = ingredients
                recipes[i]['instructions'] = data.get('instructions', [])
                recipes[i]['comment'] = data.get('comment', '')
                recipe_found = True
                break

        if not recipe_found:
            return jsonify({'status': 'error', 'message': f'Recipe {recipe_id} not found'}), 404

        # Save updated recipes
        save_recipes_db(recipes)

        from core.household_paths import append_activity
        append_activity(current_household_id(), current_actor_name(), f"Edited recipe '{title}'")

        logger.info(f"Updated recipe: {title} (ID: {recipe_id})")
        return jsonify({'status': 'success', 'message': f"✅ {title} updated!", 'recipe_id': recipe_id})

    except Exception as e:
        logger.error(f"Error editing recipe: {e}")
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
        from core.household_paths import menu_file, append_activity
        with open(menu_file(current_household_id()), 'w', encoding='utf-8') as f:
            json.dump(menu, f, ensure_ascii=False, indent=2)

        append_activity(current_household_id(), current_actor_name(), f"Swapped {day}'s dinner to '{recipe['title']}'")

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
    packs_dir = SEED_DIR / 'recipe-packs'
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
    """Get list of available recipe packs, flagging which ones this
    household has already imported (by source_pack on its own recipes)."""
    packs = get_available_recipe_packs()

    imported_pack_ids = set()
    household_id = current_household_id()
    if household_id:
        for r in load_recipes_db():
            if r.get('source_pack'):
                imported_pack_ids.add(r['source_pack'])

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
            'difficulty': pack['difficulty'],
            'alreadyImported': pack['packId'] in imported_pack_ids
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

        # Collect recipes from selected packs, keeping bilingual fields intact.
        # The recipe's own dish-type category (Chicken, Salads, etc.) is kept
        # as-is - it's what drives normal category-dropdown filtering and menu
        # generation. Which pack a recipe came from is tracked separately via
        # source_pack, purely for "Manage Recipe Packs" bookkeeping (grouping/
        # removing everything imported from one pack) - it must NOT be used
        # as the dish-type category, or imported recipes can only ever be
        # found under their pack name instead of e.g. "Chicken" or "Salads".
        pack_metadata = {}  # source_pack code -> display info, for categories.json bookkeeping
        for pack in all_packs:
            if pack['packId'] in pack_ids:
                pack_name_field = pack.get('packName', {})
                if isinstance(pack_name_field, dict):
                    pack_display_name = pack_name_field.get('en') or pack_name_field.get('no') or 'Imported Pack'
                else:
                    pack_display_name = str(pack_name_field)

                pack_metadata[pack['packId']] = {
                    'display_name': pack_display_name,
                    'icon': pack.get('packImage', '📦'),
                    'color': pack.get('packColor', '#999999')
                }

                for recipe in pack['recipes']:
                    # Normalize only non-bilingual technical fields, keep titles/descriptions as bilingual dicts
                    r = dict(recipe)
                    # Track pack origin separately - do NOT touch r['category']
                    r['source_pack'] = pack['packId']
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
        save_recipes_db(existing_recipes)

        from core.household_paths import append_activity, save_imported_pack_metadata
        append_activity(current_household_id(), current_actor_name(), f"Imported {imported_count} recipes from {len(pack_ids)} pack(s)")

        # No categories.json bookkeeping needed here anymore - imported recipes
        # keep their own real dish-type category (Chicken, Salads, etc.), which
        # already exists in the household's category list. There's nothing
        # new to register; a recipe is just findable under its existing
        # category right away. Pack display metadata (for "Manage Recipe
        # Packs") is tracked separately instead.
        for pack_id, meta in pack_metadata.items():
            save_imported_pack_metadata(current_household_id(), pack_id, meta['display_name'], meta['icon'], meta['color'])

        logger.info(f"Imported {imported_count} recipes from {len(pack_ids)} packs")
        return jsonify({
            'success': True,
            'imported_count': imported_count,
            'message': f'Imported {imported_count} recipes'
        })

    except Exception as e:
        logger.error(f"Recipe pack import error: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipe-packs/imported', methods=['GET'])
def api_get_imported_packs():
    """Get list of imported packs, grouped by source_pack (not by category -
    a recipe's category is its own dish-type, e.g. Chicken/Salads, kept
    separate from which pack it came from)."""
    try:
        from core.household_paths import load_imported_packs
        pack_meta = load_imported_packs(current_household_id())

        recipe_counts = {}
        recipes = load_recipes_db()
        for recipe in recipes:
            pack_id = recipe.get('source_pack', '')
            if pack_id:
                recipe_counts[pack_id] = recipe_counts.get(pack_id, 0) + 1

        packs = []
        for pack_id, count in recipe_counts.items():
            meta = pack_meta.get(pack_id, {})
            packs.append({
                'pack_id': pack_id,
                'category_name': meta.get('display_name', pack_id),
                'recipe_count': count,
                'icon': meta.get('icon', '📦')
            })

        return jsonify({
            'success': True,
            'packs': packs
        })
    except Exception as e:
        logger.error(f"Error getting imported packs: {e}")
        return jsonify({'success': False, 'message': str(e)}), 500

@app.route('/api/recipe-packs/remove', methods=['POST'])
def api_remove_imported_pack():
    """Remove an imported pack (all recipes with that source_pack). Does NOT
    touch categories.json - a recipe's dish-type category is its own, not
    tied to which pack it came from, so removing a pack never needs to
    remove a category."""
    try:
        data = request.get_json()
        pack_id = data.get('pack_id', '')

        if not pack_id:
            return jsonify({'success': False, 'message': 'No pack specified'}), 400

        recipes = load_recipes_db()
        removed_count = 0

        if recipes:
            filtered_recipes = [r for r in recipes if r.get('source_pack', '') != pack_id]
            removed_count = len(recipes) - len(filtered_recipes)

            save_recipes_db(filtered_recipes)

            from core.household_paths import append_activity, remove_imported_pack_metadata
            append_activity(current_household_id(), current_actor_name(), f"Removed pack '{pack_id}' ({removed_count} recipes)")
            remove_imported_pack_metadata(current_household_id(), pack_id)

            logger.info(f"Removed {removed_count} recipes from pack '{pack_id}'")

        return jsonify({
            'success': True,
            'removed_count': removed_count,
            'message': f'Removed {removed_count} recipes'
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
        save_recipes_db(existing_recipes)

        from core.household_paths import append_activity
        append_activity(current_household_id(), current_actor_name(), f"Imported {imported_count} recipes from file")

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
