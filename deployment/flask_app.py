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
from flask import (
    Flask,
    render_template,
    jsonify,
    request,
    session,
    redirect,
    url_for,
    abort,
)
from datetime import datetime, timedelta
import sys
from dotenv import load_dotenv

# ── i18n helpers ─────────────────────────────────────────────────────────────


def _load_i18n():
    """Load i18n translations (reload on every request to catch updates)."""
    i18n_path = Path(__file__).parent.parent / "frontend" / "static" / "i18n.json"
    try:
        with open(i18n_path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print(f"WARNING: Could not load i18n.json: {e}")
        return {}


def _get_lang():
    """Read language from cookie, fallback to 'en'."""
    lang = request.cookies.get("pi_language", "en")
    return lang if lang in ("en", "no") else "en"


def _make_t(lang):
    """Return a dict of {key: translated_value} for the given language."""
    raw = _load_i18n()
    result = {}
    suffix = "_" + lang
    fallback_suffix = "_en"
    for full_key, value in raw.items():
        if full_key.endswith(suffix):
            base = full_key[: -len(suffix)]
            result[base] = value
    # Fill in English fallbacks for any missing keys
    for full_key, value in raw.items():
        if full_key.endswith(fallback_suffix):
            base = full_key[: -len(fallback_suffix)]
            if base not in result:
                result[base] = value
    return result


def _resolve(val, lang):
    """Resolve a bilingual dict {'no': ..., 'en': ...} or plain string to a single string."""
    if isinstance(val, dict):
        return val.get(lang) or val.get("en") or val.get("no") or ""
    return val or ""


_BASE_CATEGORY_TRANSLATIONS = None


def _translate_category_name(category_en, lang):
    """Translate a recipe's category (always stored in English, e.g.
    'Fish & Seafood') to the current language, using data/categories.json as
    the source of truth (it already has correct name_no values for every
    built-in category - Fisk & Sjømat, Biff & Rødt Kjøtt, Svin, Lette
    Måltider, etc.). Previously only the dashboard route translated
    categories, via a hand-maintained dict that was missing several
    categories (Pork, Beef & Red Meat, Light Meals) - and nowhere
    else (All Recipes cards, recipe detail page) translated categories at
    all, which is why category tags stayed in English regardless of
    language (B46). A household's own custom categories won't have a
    translation here and pass through unchanged, which is correct - they
    were typed in whatever language the user typed them in.
    Deliberately does NOT touch the 'category' field itself, only returns a
    display string - filtering/matching logic elsewhere compares against the
    raw English category value and must keep working unchanged."""
    global _BASE_CATEGORY_TRANSLATIONS
    if lang == "en" or not category_en:
        return category_en or ""
    if _BASE_CATEGORY_TRANSLATIONS is None:
        _BASE_CATEGORY_TRANSLATIONS = {}
        base_file = Path(__file__).parent.parent / "data" / "categories.json"
        try:
            with open(base_file, "r", encoding="utf-8") as f:
                for cat in json.load(f):
                    name_en = cat.get("name_en")
                    name_no = cat.get("name_no")
                    if name_en and name_no:
                        _BASE_CATEGORY_TRANSLATIONS[name_en] = name_no
        except Exception as e:
            print(f"WARNING: Could not load base categories.json for translation: {e}")
    return _BASE_CATEGORY_TRANSLATIONS.get(category_en, category_en)


# Canonical allergen translations (B46 remaining scope). Different recipe
# sources authored allergen tags in different languages with no bilingual
# dict structure at all (unlike title/ingredients): the 10 built-in sample
# recipes store raw Norwegian strings ('fisk', 'melk', 'soya'), while
# imported recipe packs store raw English strings ('fish', 'dairy', 'soy',
# 'eggs', 'wheat', 'nuts', etc.) - so the same allergen showed up in
# whichever language it happened to be authored in, regardless of the
# site's current language. Keyed by every raw spelling seen in the data,
# mapping to a single canonical {'en':..., 'no':...} pair.
_ALLERGEN_TRANSLATIONS = {}


def _register_allergen(display_en, display_no, *raw_keys):
    entry = {"en": display_en, "no": display_no}
    for k in raw_keys:
        _ALLERGEN_TRANSLATIONS[k.lower()] = entry


_register_allergen("Gluten", "Gluten", "gluten")
_register_allergen("Dairy", "Melk", "dairy", "melk", "milk")
_register_allergen("Fish", "Fisk", "fish", "fisk")
_register_allergen("Meat", "Kjøtt", "meat", "kjøtt", "kjott")
_register_allergen("Shellfish", "Skalldyr", "shellfish", "skalldyr")
_register_allergen("Egg", "Egg", "egg", "eggs")
_register_allergen("Wheat", "Hvete", "wheat", "hvete")
_register_allergen("Nuts", "Nøtter", "nuts", "nøtter", "notter")
_register_allergen("Saffron", "Safran", "saffron", "safran")
_register_allergen("Sesame", "Sesam", "sesame", "sesam")
_register_allergen("Alcohol", "Alkohol", "alcohol", "alkohol")
_register_allergen("Mustard", "Sennep", "mustard", "sennep")
_register_allergen("Soy", "Soya", "soy", "soya")
_register_allergen("Grains", "Korn", "grains", "korn")
_register_allergen("Wine", "Vin", "wine", "vin")


def _translate_allergen(raw, lang):
    """Translate a single allergen tag to the current language, regardless
    of which language it happens to be stored in. Falls back to the raw
    value, capitalized, for anything not in the canonical list above (an
    unrecognized custom allergen someone typed in, for example) - same
    graceful-degradation approach as _translate_category_name()."""
    if not raw:
        return raw or ""
    entry = _ALLERGEN_TRANSLATIONS.get(str(raw).strip().lower())
    if entry:
        return entry.get(lang) or entry.get("en") or raw
    return str(raw).strip().capitalize()


import re as _re

_STEP_PREFIX_RE = _re.compile(r"^\s*\d+\s*[\.\):]\s*")


def _strip_step_prefix(text):
    """Strip a leading '1.'/'1)'/'1:' style step number from an instruction
    string. Recipe data commonly has the step number baked into the text
    itself, and the recipe page also renders its own auto-generated "Step N"
    heading - without this, both show up together (B40)."""
    if not isinstance(text, str):
        return text
    return _STEP_PREFIX_RE.sub("", text, count=1)


# Difficulty normalisation map (Norwegian → English)
_DIFFICULTY_MAP = {
    "enkel": "Easy",
    "easy": "Easy",
    "middels": "Medium",
    "medium": "Medium",
    "vanskelig": "Hard",
    "hard": "Hard",
}


def _normalize_difficulty(val):
    if isinstance(val, dict):
        val = val.get("en") or val.get("no") or ""
    if not val:
        return "Easy"
    return _DIFFICULTY_MAP.get(str(val).lower(), val)


def _split_broken_combined_ingredients(recipe):
    """B28: two shipped recipes (eu_096, eu_083) bundle multiple ingredients into
    a single line sharing one nonsensical combined unit (e.g. "ml/100g/50g"),
    which can't be displayed, deduplicated, or summed sensibly. The recipe-pack
    source files have since been corrected, but any household that already
    imported the old data before that fix still has the broken combined line
    stored in its own recipes_db. Rather than risk a direct data migration,
    split those two known-broken lines into their real separate ingredients
    here at read time, so every place recipes are read (detail page, edit,
    shopping list) sees the corrected data regardless of when it was imported."""
    if recipe.get("id") not in ("eu_096", "eu_083"):
        return recipe
    ings = recipe.get("ingredients", [])
    for i, ing in enumerate(ings):
        name = ing.get("name") if isinstance(ing, dict) else None
        name_en = name.get("en", "") if isinstance(name, dict) else ""
        if recipe["id"] == "eu_096" and "chamel" in name_en:
            recipe = dict(recipe)
            recipe["ingredients"] = (
                ings[:i]
                + [
                    {
                        "name": {
                            "no": "Melk (til béchamel)",
                            "en": "Milk (for béchamel)",
                        },
                        "amount": 600,
                        "unit": {"no": "ml", "en": "ml"},
                    },
                    {
                        "name": {
                            "no": "Smør (til béchamel)",
                            "en": "Butter (for béchamel)",
                        },
                        "amount": 100,
                        "unit": {"no": "gram", "en": "g"},
                    },
                    {
                        "name": {
                            "no": "Mel (til béchamel)",
                            "en": "Flour (for béchamel)",
                        },
                        "amount": 50,
                        "unit": {"no": "gram", "en": "g"},
                    },
                ]
                + ings[i + 1 :]
            )
            break
        if recipe["id"] == "eu_083" and "Butter and milk" in name_en:
            recipe = dict(recipe)
            recipe["ingredients"] = (
                ings[:i]
                + [
                    {
                        "name": {
                            "no": "Smør (til potetmos)",
                            "en": "Butter (for mash)",
                        },
                        "amount": 50,
                        "unit": {"no": "gram", "en": "g"},
                    },
                    {
                        "name": {"no": "Melk (til potetmos)", "en": "Milk (for mash)"},
                        "amount": 100,
                        "unit": {"no": "ml", "en": "ml"},
                    },
                ]
                + ings[i + 1 :]
            )
            break
    return recipe


def _normalize_recipe(recipe, lang="en"):
    """Flatten all bilingual dict fields in a recipe to plain strings for the given lang."""
    recipe = _split_broken_combined_ingredients(recipe)
    r = dict(recipe)
    # Handle both formats: bilingual dict {'no': ..., 'en': ...} and separate _no/_en fields
    # Prefer language-specific _no/_en fields, fall back to dict format, then fallback to plain string
    for field in ("title", "subtitle", "description", "comment"):
        # First check for _no/_en suffix fields (sample_recipes.json format)
        if r.get(f"{field}_{lang}"):
            r[field] = r[f"{field}_{lang}"]
        # Then check for dict format
        elif isinstance(r.get(field), dict):
            r[field] = (
                r[field].get(lang) or r[field].get("en") or r[field].get("no") or ""
            )
        # Keep plain string as-is, but only if no language-specific version exists
        elif not isinstance(r.get(field), dict) and not r.get(f"{field}_{lang}"):
            # Try fallback fields if language-specific not found
            if lang != "en" and r.get(f"{field}_en"):
                r[field] = r.get(f"{field}_en")
        # If field is missing entirely, ensure it's empty string
        if field not in r or r[field] is None:
            r[field] = ""

    # time_minutes may be stored as cookTimeMinutes in pack recipes
    if "time_minutes" not in r or not r.get("time_minutes"):
        r["time_minutes"] = r.get("cookTimeMinutes", r.get("time_minutes", 30))

    # Difficulty: flatten + normalise
    r["difficulty"] = _normalize_difficulty(_resolve(r.get("difficulty"), lang))

    # Translated display name for the category tag (B46) - keep r['category']
    # itself untouched in English, since filter/search logic depends on it.
    r["category_display"] = _translate_category_name(r.get("category", ""), lang)

    # Translated allergen tags (B46) - see _translate_allergen() above for why
    # this was inconsistent (sample recipes stored Norwegian, packs stored
    # English, with no per-language field at all).
    if r.get("allergens"):
        r["allergens"] = [_translate_allergen(a, lang) for a in r["allergens"]]

    # Ingredients: support pack schema, sample_recipes _no/_en fields, and simple strings
    new_ings = []
    for ing in r.get("ingredients", []):
        if isinstance(ing, dict):
            # Try to get bilingual name: dict format, then _no/_en fields, then plain 'name'
            if isinstance(ing.get("name"), dict):
                name = _resolve(ing.get("name"), lang)
            else:
                name = (
                    ing.get(f"name_{lang}")
                    or ing.get("name_en")
                    or ing.get("name")
                    or ""
                )
            qty = ing.get("quantity", ing.get("amount", 0))
            unit = ing.get("unit", "")
            if isinstance(unit, dict):
                unit = _resolve(unit, lang)
            new_ings.append({"name": name, "quantity": qty, "unit": unit})
        else:
            new_ings.append(ing)
    r["ingredients"] = new_ings
    # Also flatten ingredients_included / ingredients_not_included if present
    for field in ("ingredients_included", "ingredients_not_included"):
        if r.get(field):
            flat = []
            for ing in r[field]:
                if isinstance(ing, dict):
                    # Try to get bilingual name: dict format, then _no/_en fields, then plain 'name'
                    if isinstance(ing.get("name"), dict):
                        name = _resolve(ing.get("name"), lang)
                    else:
                        name = (
                            ing.get(f"name_{lang}")
                            or ing.get("name_en")
                            or ing.get("name")
                            or ""
                        )
                    qty = ing.get("quantity", ing.get("amount", 0))
                    unit = ing.get("unit", "")
                    if isinstance(unit, dict):
                        unit = _resolve(unit, lang)
                    flat.append({"name": name, "quantity": qty, "unit": unit})
                else:
                    flat.append(ing)
            r[field] = flat

    # Instructions: support {no: [...], en: [...]} or [{step, description}] or [str]
    raw_inst = r.get("instructions", [])
    if isinstance(raw_inst, dict):
        steps = raw_inst.get(lang) or raw_inst.get("en") or []
        r["instructions"] = [
            {"step": i + 1, "description": _strip_step_prefix(s)}
            for i, s in enumerate(steps)
        ]
    elif isinstance(raw_inst, list) and raw_inst:
        # Already a list — normalise any dict entries
        norm = []
        for i, s in enumerate(raw_inst):
            if isinstance(s, dict):
                norm.append(
                    {
                        "step": s.get("step", i + 1),
                        "description": _strip_step_prefix(
                            _resolve(s.get("description"), lang)
                        ),
                    }
                )
            else:
                norm.append({"step": i + 1, "description": _strip_step_prefix(str(s))})
        r["instructions"] = norm

    return r


sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Initialize database (import models first so Base.metadata knows about all tables)
import database.models  # noqa: F401
from database.database import db

db.create_all()

logger = logging.getLogger(__name__)

# Setup logging with safe directory creation
log_dir = Path(__file__).parent.parent / "logs"
try:
    log_dir.mkdir(parents=True, exist_ok=True)
    file_handler = logging.FileHandler(log_dir / "flask_app.log")
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s - %(levelname)s - %(message)s")
    )
    logger.addHandler(file_handler)
except Exception:
    pass
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

DATA_DIR = Path(__file__).parent.parent / "data"
CACHE_DIR = DATA_DIR / "recipes_cache"

# Static recipe/category seed content (sample_recipes.json, recipe-packs/,
# the base categories.json, pantry_staples.json, dessert/drinks stashes)
# is read from here instead of DATA_DIR. On Render, DATA_DIR sits on a
# persistent disk that's deliberately never overwritten on redeploy (so
# real household data survives across deploys) - but that also means any
# fix to these static seed files would silently never reach production,
# since the disk's stale copy from whenever it was first created always
# wins. SEED_DIR points at a pristine, always-fresh-from-the-image copy the
# Dockerfile bakes in at /app/data-seed specifically so static content isn't
# subject to the volume's no-clobber protection. Falls back to DATA_DIR
# itself when data-seed doesn't exist (e.g. local dev, where there's no
# volume shadowing to worry about).
SEED_DIR = Path(__file__).parent.parent / "data-seed"
if not SEED_DIR.exists():
    SEED_DIR = DATA_DIR
PROFILE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

# Certificate paths (relative to the deployment dir where the service runs from)
CERT_FILE = Path(__file__).parent / "cert.pem"
KEY_FILE = Path(__file__).parent / "key.pem"

app = Flask(
    __name__,
    template_folder=str(Path(__file__).parent.parent / "frontend/templates"),
    static_folder=str(Path(__file__).parent.parent / "frontend/static"),
)

# Configuration
FLASK_ENV = os.environ.get("FLASK_ENV", "development")
IS_PRODUCTION = FLASK_ENV == "production"


# --- Local-only feature flags -----------------------------------------
# Hidden, developer-only switches for in-progress features (dessert/drink
# browsing, side stash, dessert planner integration) that aren't ready for
# public users yet. ALL flags default to OFF - nothing here changes what a
# public user sees unless the matching env var is explicitly set in a local
# .env file. Never set any of these in the production Render environment.
# See docs/FEATURE_FLAGS.md for the full list and how to enable one locally.
def _flag_enabled(env_var):
    return os.environ.get(env_var, "").strip().lower() in ("1", "true", "yes", "on")


FEATURE_FLAGS = {
    # F2: Dessert + drink browsing
    "desserts_drinks": _flag_enabled("FEATURE_DESSERTS_DRINKS"),
    # F8: Side stash feature
    "side_stash": _flag_enabled("FEATURE_SIDE_STASH"),
    # F9: Dessert system in the dinner planner
    "dessert_planner": _flag_enabled("FEATURE_DESSERT_PLANNER"),
}
if IS_PRODUCTION and any(FEATURE_FLAGS.values()):
    # Belt-and-suspenders: these are meant for local testing only. If one
    # somehow ends up set in the production environment, log it loudly
    # rather than silently exposing an unfinished feature to real users.
    logging.getLogger(__name__).warning(
        "One or more hidden feature flags are enabled in a PRODUCTION "
        "environment: %s - this is unexpected, these are for local dev "
        "testing only.",
        [k for k, v in FEATURE_FLAGS.items() if v],
    )


def feature_enabled(name):
    """Check whether a hidden/local-only feature flag is on. Use this in
    routes and templates instead of reading FEATURE_FLAGS directly, so
    there's one place to change the lookup logic later (e.g. per-household
    overrides) without touching every call site."""
    return FEATURE_FLAGS.get(name, False)


# The app's own developer/admin - NOT a household owner. Gates the in-app
# feedback list specifically to this one account, regardless of which
# household(s) it owns or what role it holds in any of them.
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL", "").strip().lower()

app.config["JSON_SORT_KEYS"] = False
app.config["TEMPLATES_AUTO_RELOAD"] = not IS_PRODUCTION


@app.template_filter("format_minutes")
def format_minutes(value):
    """Render a recipe's time_minutes as human-friendly duration text.

    Plain "1440 min" for a cook time that's actually 24 hours (e.g. a cured/
    marinated dish like Gravlax) reads as a typo or a bug, not a real prep
    time. Past 60 minutes, switch to hours (plus leftover minutes when they
    don't divide evenly), matching how a person would actually say it.
    """
    try:
        minutes = int(value)
    except (TypeError, ValueError):
        return value
    if minutes < 60:
        return f"{minutes} min"
    hours, mins = divmod(minutes, 60)
    if mins == 0:
        return f"{hours} h"
    return f"{hours} h {mins} min"


app.config["SECRET_KEY"] = os.environ.get("FLASK_SECRET_KEY", secrets.token_hex(32))

# Security: Use secure cookies in production
app.config["SESSION_COOKIE_SECURE"] = IS_PRODUCTION
app.config["SESSION_COOKIE_HTTPONLY"] = True
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"

# Sessions default to browser-session-only cookies, which get dropped when an
# installed PWA is fully closed (common on mobile), forcing a relogin every
# time. Login routes set session.permanent = True to opt into this lifetime.
app.config["PERMANENT_SESSION_LIFETIME"] = timedelta(days=30)

# CSRF protection (added 2026-07-05 engineering security pass) - previously
# every state-changing POST route (recipe CRUD, pantry, household/member
# management, account deletion, admin actions) had no CSRF defense at all,
# meaning any of them could be triggered cross-site while a user was logged
# in, just by getting them to load a malicious page. Traditional <form
# method="post"> submissions carry a hidden csrf_token field (see
# frontend/templates); fetch()-based JSON requests send it via the
# X-CSRFToken header, added automatically by the fetch wrapper in app.js.
from flask_wtf import CSRFProtect

csrf = CSRFProtect(app)

# Disable Jinja2 cache in development for faster iteration
if not IS_PRODUCTION:
    app.jinja_env.cache = None

logger.info(f"Flask templates: {app.template_folder}")
logger.info(f"Flask static: {app.static_folder}")

# ── Context Processors ───────────────────────────────────────────────────────


def _send_confirmation_email(user):
    """Email the user a confirmation link via Resend. Same fail-safe pattern
    as _notify_admin_of_feedback below: if RESEND_API_KEY isn't configured,
    log and skip rather than block signup - but note that without an actual
    key set, NO ONE can confirm their email and therefore no one can log in,
    so this must be configured before real users sign up against this build."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            f"RESEND_API_KEY not set - cannot send confirmation email to {user.email}. "
            f"This user cannot log in until email confirmation is sent some other way."
        )
        return False

    from_addr = os.getenv("RESEND_FROM_EMAIL", "feedback@menuplanner.app").strip()
    confirm_url = url_for(
        "confirm_email_route", token=user.email_confirmation_token, _external=True
    )
    body = (
        f"Welcome to Menu Planner!\n\n"
        f"Please confirm your email address to activate your account:\n\n"
        f"{confirm_url}\n\n"
        f"If you didn't sign up for Menu Planner, you can ignore this email."
    )
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [user.email],
                "subject": "Confirm your Menu Planner account",
                "text": body,
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            logger.error(
                f"Resend confirmation email failed: {resp.status_code} {resp.text}"
            )
            return False
        logger.info(
            f"Confirmation email sent to {user.email} (Resend id: {resp.json().get('id')})"
        )
        return True
    except Exception as e:
        logger.error(f"Resend confirmation email exception: {e}")
        return False


def _send_password_reset_email(user):
    """Email the user a password reset link via Resend."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.warning(
            f"RESEND_API_KEY not set - cannot send password reset email to {user.email}"
        )
        return False
    from_addr = os.getenv("RESEND_FROM_EMAIL", "onboarding@resend.dev").strip()
    reset_url = url_for(
        "reset_password_page", token=user.password_reset_token, _external=True
    )
    body = (
        f"You requested a password reset for your Menu Planner account.\n\n"
        f"Click the link below to set a new password (link expires in 1 hour):\n\n"
        f"{reset_url}\n\n"
        f"If you didn't request this, you can ignore this email — your password has not changed."
    )
    try:
        resp = requests.post(
            "https://api.resend.com/emails",
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
            json={
                "from": from_addr,
                "to": [user.email],
                "subject": "Reset your Menu Planner password",
                "text": body,
            },
            timeout=10,
        )
        if resp.status_code >= 300:
            logger.error(
                f"Resend password reset email failed: {resp.status_code} {resp.text}"
            )
            return False
        logger.info(f"Password reset email sent to {user.email}")
        return True
    except Exception as e:
        logger.error(f"Resend password reset email exception: {e}")
        return False


def _notify_admin_of_feedback(entry):
    """Email ADMIN_EMAIL via Resend when new feedback is submitted, so the
    developer doesn't have to manually check data/feedback.json or dig
    through Render's dashboard to notice a new tester report. No-ops
    silently (just logs) if RESEND_API_KEY isn't configured yet - this must
    never block or break the actual feedback submission."""
    api_key = os.getenv("RESEND_API_KEY", "").strip()
    if not api_key:
        logger.info("RESEND_API_KEY not set - skipping feedback email notification")
        return

    from_addr = os.getenv("RESEND_FROM_EMAIL", "feedback@menuplanner.app").strip()
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
        "https://api.resend.com/emails",
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        json={
            "from": from_addr,
            "to": [ADMIN_EMAIL],
            "subject": f"New feedback: {entry['title']}",
            "text": body,
        },
        timeout=10,
    )
    if resp.status_code >= 300:
        logger.error(
            f"Resend feedback notification failed: {resp.status_code} {resp.text}"
        )
    else:
        logger.info(
            f"Feedback notification emailed to {ADMIN_EMAIL} (Resend id: {resp.json().get('id')})"
        )


_AVATAR_PALETTE = [
    "#F87171",
    "#FB923C",
    "#FBBF24",
    "#A3E635",
    "#34D399",
    "#22D3EE",
    "#60A5FA",
    "#A78BFA",
    "#F472B6",
    "#94A3B8",
]


def _avatar_color(label):
    """Deterministic background color for an initial-circle avatar from a name/email."""
    if not label:
        return _AVATAR_PALETTE[0]
    return _AVATAR_PALETTE[sum(ord(c) for c in label) % len(_AVATAR_PALETTE)]


app.jinja_env.globals["avatar_color"] = _avatar_color

MAX_PROFILES_PER_HOUSEHOLD = 6

AVATAR_EMOJI_CHOICES = [
    "🧑",
    "👩",
    "👨",
    "👧",
    "👦",
    "🧓",
    "👴",
    "👵",
    "🧑‍🍳",
    "🦸",
    "🦸‍♀️",
    "🧙",
    "🐶",
    "🐱",
    "🦊",
    "🐻",
    "🐼",
    "🐨",
    "🦁",
    "🐸",
    "🐧",
    "🦄",
    "🐙",
    "🍕",
]

app.jinja_env.globals["avatar_emoji_choices"] = AVATAR_EMOJI_CHOICES


def _avatar_display(label, avatar_type=None, avatar_value=None):
    """Either the member's chosen emoji, or an upper-case initial, for circle avatars."""
    if avatar_type == "emoji" and avatar_value:
        return avatar_value
    return label[0].upper() if label else "?"


app.jinja_env.globals["avatar_display"] = _avatar_display


@app.before_request
def _restore_remembered_profile():
    """If this device previously picked a profile and the session lost it
    (new login, expired session), silently restore it from the device cookie
    instead of forcing the picker again."""
    if session.get("user_id") and not session.get("active_profile_id"):
        remembered_id = request.cookies.get("remembered_profile_id")
        if remembered_id:
            household_id = current_household_id()
            if household_id:
                from core.household_helpers import get_member_by_id

                member = get_member_by_id(remembered_id, household_id)
                if member and member.is_profile:
                    session["active_profile_id"] = str(member.id)
                    session["active_profile_name"] = member.display_name


def current_household_id():
    """Resolve the active household id for this request, picking the user's
    first household if none is set in session yet."""
    user_id = session.get("user_id")
    if not user_id:
        return None

    from core.household_helpers import get_user_households

    households = get_user_households(user_id)
    household_id = session.get("current_household_id")

    if household_id:
        # Cross-account leak guard: `current_household_id` lives in the
        # session cookie, and login only ever popped `active_profile_id` -
        # not this key. On a shared browser (or anywhere sessions persist
        # across logins), logging in as a second account reused the first
        # account's still-set household id verbatim, with nothing checking
        # that the *new* user_id actually belongs to it. That let one
        # account transparently read and write another account's entire
        # household (menu, recipes, pantry, activity log) just by logging
        # in on the same browser afterward. Only trust the session's
        # household id if the current user is actually a member of it.
        if any(str(h.id) == str(household_id) for h in households):
            return household_id
        session.pop("current_household_id", None)

    if households:
        household_id = str(households[0].id)
        session["current_household_id"] = household_id
        return household_id

    return None


def current_household():
    """Get the current household ORM object from the database."""
    household_id = current_household_id()
    if not household_id:
        return None
    from database.database import SessionLocal
    from database.models import Household

    db = SessionLocal()
    try:
        return db.query(Household).filter(Household.id == household_id).first()
    finally:
        db.close()


import contextlib


@contextlib.contextmanager
def locked_household():
    """Open one DB session and lock the current household's row with
    SELECT ... FOR UPDATE for the lifetime of the `with` block, so a
    concurrent request touching the same household (e.g. two menu swaps,
    or a swap racing a regenerate) blocks until this one commits, instead
    of both reading stale data and one silently overwriting the other's
    change on save. Only a real risk once the app runs with more than one
    gunicorn worker/thread (it doesn't today), but this closes the gap
    before that becomes an actual bug rather than after.

    Yields (db_session, household) - household is None if there's no
    DB-backed household for this request (e.g. file-storage fallback,
    which doesn't need locking - there's no concurrent access to a single
    Pi's local file). Callers must do ALL of their read + mutate + save
    for this household inside the `with` block, using the yielded
    `household` object (NOT `current_household()`, which returns a
    detached object from an already-closed session)."""
    household_id = current_household_id()
    if not household_id:
        yield None, None
        return
    from database.database import SessionLocal
    from database.models import Household

    db = SessionLocal()
    try:
        household = (
            db.query(Household)
            .filter(Household.id == household_id)
            .with_for_update()
            .first()
        )
        yield db, household
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()


def log_activity(action_msg):
    """Record one activity-log entry for the current household.

    This is the single correct way to log an action. Households are DB-backed
    once created, so this always opens its own fresh session, re-queries the
    household by id, appends the entry, and commits - mirroring the pattern
    already proven correct in the swap-recipe route. Using a `household`
    object obtained elsewhere (e.g. from `current_household()`) doesn't work:
    that helper closes its session before returning, so the object is
    detached and mutating it (as `append_activity_to_db` does) never
    persists. Falls back to the legacy file-based log only if there's no
    database-backed household yet (pre-migration period).
    """
    household_id = current_household_id()
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import append_activity_to_db, append_activity

    db = SessionLocal()
    try:
        db_household = db.query(Household).filter(Household.id == household_id).first()
        if db_household:
            append_activity_to_db(db_household, current_actor_name(), action_msg)
            db.commit()
        else:
            append_activity(household_id, current_actor_name(), action_msg)
    finally:
        db.close()


def _load_pantry_db():
    """Load pantry from database. If not yet migrated, seed from file into DB."""
    household_id = current_household_id()
    if not household_id:
        return []

    from database.database import SessionLocal
    from database.models import Household

    db = SessionLocal()
    try:
        household = db.query(Household).filter(Household.id == household_id).first()
        if not household:
            return []

        # If pantry already in database, return it
        if household.pantry is not None:
            return household.pantry if isinstance(household.pantry, list) else []

        # First time: seed from file into database
        from core.household_paths import load_pantry

        file_pantry = load_pantry(household_id)
        household.pantry = sorted(set(file_pantry)) if file_pantry else []
        db.commit()
        return household.pantry
    except Exception as e:
        print(f"Error loading pantry from database: {e}")
        return []
    finally:
        db.close()


def _save_pantry_db(items):
    """Save pantry to database (with fallback to file)."""
    household_id = current_household_id()
    if household_id:
        from database.database import SessionLocal
        from database.models import Household

        db = SessionLocal()
        try:
            household = db.query(Household).filter(Household.id == household_id).first()
            if household:
                household.pantry = sorted(set(items))
                db.commit()
                return
        except Exception as e:
            db.rollback()
            print(f"Error saving pantry to database: {e}")
        finally:
            db.close()

    # Fallback to file-based for migration period
    from core.household_paths import save_pantry

    save_pantry(household_id, items)


def current_actor_name():
    """Name to attribute edits/actions to: active profile if one is picked,
    otherwise the logged-in account's email."""
    return session.get("active_profile_name") or session.get("user_email") or "Unknown"


def acting_role_is_owner():
    """True only if the CURRENTLY ACTING identity is the owner. If a non-owner
    profile is active (e.g. 'Wife', 'Kid'), this is False even though the underlying
    account is the owner - profiles must explicitly re-select 'Owner' (with a password
    check) to act with owner privileges."""
    user_id = session.get("user_id")
    if not user_id:
        return False

    household_id = current_household_id()
    if not household_id:
        return False

    active_profile_id = session.get("active_profile_id")
    if active_profile_id:
        from core.household_helpers import get_profile_role

        return get_profile_role(active_profile_id, household_id) in (
            "owner",
            "co-owner",
        )

    from core.household_helpers import user_is_household_owner

    return user_is_household_owner(user_id, household_id)


def acting_role_can_edit():
    """True if the CURRENTLY ACTING identity can make changes (regenerate the menu,
    add/edit recipes, etc.) - i.e. anything other than 'viewer'. A 'viewer' profile
    (e.g. a kid) can look at the menu but shouldn't be able to wipe it out by
    regenerating, since that overwrites what the household already shopped for."""
    user_id = session.get("user_id")
    if not user_id:
        return False

    household_id = current_household_id()
    if not household_id:
        return False

    active_profile_id = session.get("active_profile_id")
    if active_profile_id:
        from core.household_helpers import get_profile_role

        role = get_profile_role(active_profile_id, household_id)
    else:
        from core.household_helpers import get_account_holder_role

        role = get_account_holder_role(user_id, household_id)

    return role in ("owner", "co-owner", "editor")


@app.context_processor
def inject_config():
    """Inject configuration and i18n into all templates."""
    lang = _get_lang()
    t = _make_t(lang)

    # Get current user info
    user_email = session.get("user_email")
    user_id = session.get("user_id")
    auth_type = session.get("auth_type")
    is_authenticated = bool(user_id and user_email)

    household_name = os.getenv("HOUSEHOLD_NAME", "Menu Planner")
    household_id = current_household_id()
    is_household_owner = False
    can_edit_menu = True
    is_app_admin = _is_admin()
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

            active_profile_id = session.get("active_profile_id")
            members = get_household_members(household_id)
            active_member = None
            if active_profile_id:
                active_member = next(
                    (m for m in members if m["member_id"] == str(active_profile_id)),
                    None,
                )
            else:
                active_member = next(
                    (m for m in members if m["user_id"] == str(user_id)), None
                )
            if active_member:
                active_avatar_type = active_member["avatar_type"]
                active_avatar_value = active_member["avatar_value"]

    return {
        "household_name": household_name,
        "creator": "nobody174",
        "github_url": "https://github.com/nobody174/Menu-Planner",
        "patreon_url": "https://www.patreon.com/c/Nobody174",
        "lang": lang,
        "t": t,
        "is_authenticated": is_authenticated,
        "user_email": user_email,
        "user_id": user_id,
        "auth_type": auth_type,
        "active_profile_name": session.get("active_profile_name"),
        "is_household_owner": is_household_owner,
        "can_edit_menu": can_edit_menu,
        "is_app_admin": is_app_admin,
        "active_avatar_type": active_avatar_type,
        "active_avatar_value": active_avatar_value,
        "feature_flags": FEATURE_FLAGS,
    }


# ── Helpers ──────────────────────────────────────────────────────────────────


def load_menu():
    """Load weekly menu from database JSONB column."""
    household = current_household()
    if not household:
        # Fallback to file-based for migration period
        from core.household_paths import menu_file

        household_id = current_household_id()
        if not household_id:
            return None
        path = menu_file(household_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return None

    from core.household_paths import load_weekly_menu_from_db

    return load_weekly_menu_from_db(household)


def save_menu(menu):
    """Save the weekly menu, DB-backed households first, file as fallback.
    Mirrors the save pattern already proven correct in /api/swap-recipe:
    opens its own fresh session and re-queries the household by id rather
    than reusing a possibly-detached object, so the write actually commits."""
    household_id = current_household_id()
    household = current_household()
    if household:
        from database.database import SessionLocal
        from database.models import Household
        from core.household_paths import save_weekly_menu_to_db

        db = SessionLocal()
        try:
            db_household = (
                db.query(Household).filter(Household.id == household.id).first()
            )
            if db_household:
                save_weekly_menu_to_db(db_household, menu)
                db.commit()
        finally:
            db.close()
    else:
        from core.household_paths import menu_file

        with open(menu_file(household_id), "w", encoding="utf-8") as f:
            json.dump(menu, f, ensure_ascii=False, indent=2)


def load_recipes_db():
    """Load recipes from database JSONB column."""
    household = current_household()
    if not household:
        # Fallback to file-based for migration period
        from core.household_paths import recipes_db_file

        household_id = current_household_id()
        if not household_id:
            return []
        path = recipes_db_file(household_id)
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
        return []

    from core.household_paths import load_recipes_db_from_db

    return load_recipes_db_from_db(household)


def save_recipes_db(recipes):
    """Save recipes to database JSONB column."""
    household = current_household()
    if not household:
        # Fallback to file-based for migration period
        from core.household_paths import recipes_db_file
        import tempfile, os

        household_id = current_household_id()
        path = recipes_db_file(household_id)
        dir_ = path.parent
        with tempfile.NamedTemporaryFile(
            "w", encoding="utf-8", dir=dir_, delete=False, suffix=".tmp"
        ) as tf:
            json.dump(recipes, tf, ensure_ascii=False, indent=2)
            tf.write("\n")
            tmp_path = tf.name
        os.replace(tmp_path, path)
        return

    from database.database import SessionLocal
    from database.models import Household as HouseholdModel

    db = SessionLocal()
    try:
        h = db.query(HouseholdModel).filter(HouseholdModel.id == household.id).first()
        if h:
            h.recipes_db = recipes
            db.commit()
    except Exception as e:
        db.rollback()
        print(f"Error saving recipes to database: {e}")
    finally:
        db.close()


def find_recipe(recipe_id):
    # Search household recipes_db.json first, then global sample_recipes.json
    all_recipes = load_recipes_db()
    sample_path = SEED_DIR / "sample_recipes.json"
    if sample_path.exists():
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                all_recipes = all_recipes + json.load(f)
        except Exception:
            pass
    return next((r for r in all_recipes if r["id"] == recipe_id), None)


# ── Page routes ───────────────────────────────────────────────────────────────

_DAY_TRANSLATIONS = {
    "no": {
        "Monday": "Mandag",
        "Tuesday": "Tirsdag",
        "Wednesday": "Onsdag",
        "Thursday": "Torsdag",
        "Friday": "Fredag",
        "Saturday": "Lørdag",
        "Sunday": "Søndag",
    }
}


@app.route("/")
def dashboard():
    if not session.get("user_id"):
        return redirect(url_for("welcome"))

    menu = load_menu()
    if not menu:
        # This isn't a real error - it's simply what a brand-new household's
        # very first visit looks like, before they've generated their first
        # menu. Rendering the generic "Oops!" error page here (as if
        # something had gone wrong) was a rough first impression for every
        # new household. Show a friendly welcome + a direct "Generate Menu"
        # button instead - no HTTP error status either, since nothing failed.
        return render_template("empty_dashboard.html")
    lang = _get_lang()
    # Translate day names, difficulty, and categories for the current language
    day_map = _DAY_TRANSLATIONS.get(lang, {})
    t_dict = _make_t(lang)
    diff_map = {
        "Easy": t_dict.get("easy", "Easy"),
        "Medium": t_dict.get("medium", "Medium"),
        "Hard": t_dict.get("hard", "Hard"),
    }
    import copy

    menu = copy.deepcopy(menu)
    # Translate categories - uses the shared _translate_category_name() helper
    # (backed by data/categories.json) instead of a hand-maintained dict, so
    # every built-in category translates correctly, not just the ones
    # someone remembered to list here (this previously missed Pork, Beef &
    # Red Meat, and Light Meals entirely - B46).
    if menu.get("selected_categories"):
        menu["selected_categories"] = [
            _translate_category_name(c, lang) for c in menu["selected_categories"]
        ]
    for dinner in menu.get("dinners", []):
        if dinner.get("day") in day_map:
            dinner["day"] = day_map[dinner["day"]]
        # Always normalize & translate difficulty
        d = dinner.get("difficulty", "")
        d_normalized = _normalize_difficulty(d)
        # Keep the normalized (English, lowercase) level around separately for
        # the difficulty color-dot indicator, since dinner['difficulty'] below
        # gets overwritten with the translated display string.
        dinner["difficulty_level"] = d_normalized.lower()
        dinner["difficulty"] = diff_map.get(d_normalized, d_normalized)
        # Resolve title to correct language (use _no/_en fields from menu JSON)
        dinner["title"] = (
            dinner.get(f"title_{lang}")
            or dinner.get("title_en")
            or dinner.get("title")
            or ""
        )
        # Also resolve subtitle if available
        if f"subtitle_{lang}" in dinner or "subtitle_en" in dinner:
            dinner["subtitle"] = (
                dinner.get(f"subtitle_{lang}")
                or dinner.get("subtitle_en")
                or dinner.get("subtitle")
                or ""
            )
        # Self-heal stale "0 MIN" entries saved before recipes consistently
        # carried a time_minutes field (some pack recipes only ever had
        # cookTimeMinutes) - look the recipe back up rather than leaving a
        # 0 baked into the saved menu forever.
        if not dinner.get("time_minutes"):
            source_recipe = find_recipe(dinner.get("recipe_id"))
            if source_recipe:
                dinner["time_minutes"] = (
                    source_recipe.get("time_minutes")
                    or source_recipe.get("cookTimeMinutes")
                    or 0
                )
    logger.info("Dashboard accessed")
    return render_template("index.html", menu=menu)


@app.route("/recipe/<recipe_id>")
def recipe_detail(recipe_id):
    recipe = None
    recipe_dir = CACHE_DIR / recipe_id

    if recipe_dir.exists():
        metadata_file = recipe_dir / "metadata.json"
        if metadata_file.exists():
            try:
                with open(metadata_file, "r", encoding="utf-8") as f:
                    recipe = json.load(f)
            except Exception as e:
                logger.error(f"Failed to load metadata: {e}")

    if not recipe:
        recipe = find_recipe(recipe_id)

    if not recipe:
        return (
            render_template("error.html", message=f"Recipe not found: {recipe_id}"),
            404,
        )

    lang = _get_lang()
    recipe = _normalize_recipe(recipe, lang)
    logger.info(f"Recipe detail accessed: {recipe_id}")
    return render_template("recipe.html", recipe=recipe)


@app.route("/edit-recipe/<recipe_id>")
def edit_recipe(recipe_id):
    recipe = find_recipe(recipe_id)
    if not recipe:
        return (
            render_template("error.html", message=f"Recipe not found: {recipe_id}"),
            404,
        )

    lang = _get_lang()
    recipe = _normalize_recipe(recipe, lang)

    # Format ingredients as one readable line per ingredient, using the same
    # "name, quantity, unit" format documented in the Add/Edit Recipe hint
    # text (see B39) - so re-saving without touching a line round-trips
    # correctly instead of silently losing quantity/unit on every edit.
    ingredients_list = recipe.get("ingredients_included", recipe.get("ingredients", []))
    ingredient_lines = []
    for ing in ingredients_list:
        if isinstance(ing, dict):
            qty = ing.get("quantity", "")
            unit = ing.get("unit", "")
            name = ing.get("name", "")
            if qty or unit:
                ingredient_lines.append(
                    ", ".join(str(p) for p in (name, qty, unit) if p)
                )
            else:
                ingredient_lines.append(name)
        else:
            ingredient_lines.append(str(ing))
    ingredients_text = "\n".join(ingredient_lines)

    # Format instructions - _normalize_recipe() above already flattened these
    # to a list of {'step': N, 'description': '...'} dicts, so pull out the
    # plain text rather than str()-ing the dicts themselves (which used to
    # dump raw Python dict literals like "{'step': 1, 'description': '...'}"
    # straight into the textarea).
    instructions = recipe.get("instructions", [])
    lines = []
    for i, step in enumerate(instructions):
        if isinstance(step, dict):
            lines.append(str(step.get("description", "")))
        else:
            lines.append(str(step))
    instructions_text = "\n".join(lines)

    logger.info(f"Edit recipe page accessed: {recipe_id}")
    return render_template(
        "edit_recipe.html",
        recipe=recipe,
        ingredients_text=ingredients_text,
        instructions_text=instructions_text,
    )


@app.route("/shopping")
def shopping_list():
    menu = load_menu()
    if not menu or "shopping_list" not in menu:
        return render_template("error.html", message="No shopping list available"), 404

    from core.ingredient_deduplicator import strip_prep_descriptors, normalize_no_unit

    lang = _get_lang()
    if lang == "no":
        # Rebuild shopping list ingredient names in Norwegian from the recipe data
        shopping = {}
        recipe_ids = [d["recipe_id"] for d in menu.get("dinners", [])]
        from core.household_paths import recipes_db_file

        all_recipes_raw = []
        # Load from all sources: sample recipes, imported recipes, and recipe packs
        for db_path in (
            SEED_DIR / "sample_recipes.json",
            recipes_db_file(current_household_id()),
        ):
            if db_path.exists():
                try:
                    with open(db_path, "r", encoding="utf-8") as f:
                        all_recipes_raw.extend(json.load(f))
                except Exception:
                    pass
        # Also load from recipe packs (which have bilingual data)
        packs_dir = SEED_DIR / "recipe-packs"
        if packs_dir.exists():
            for pack_file in packs_dir.glob("*.json"):
                try:
                    with open(pack_file, "r", encoding="utf-8") as f:
                        pack = json.load(f)
                        all_recipes_raw.extend(pack.get("recipes", []))
                except Exception:
                    pass
        recipes_by_id = {r["id"]: r for r in all_recipes_raw}
        en_shopping = menu["shopping_list"]
        # Build a name map: english_name_lower -> norwegian_name
        name_map = {}
        for rid in recipe_ids:
            r = recipes_by_id.get(rid)
            if not r:
                continue
            # Check all possible ingredient fields
            for field in (
                "ingredients",
                "ingredients_included",
                "ingredients_not_included",
            ):
                for ing in r.get(field, []):
                    en = ""
                    no = ""
                    # Check for bilingual dict format (pack recipes)
                    if isinstance(ing.get("name"), dict):
                        en = (ing["name"].get("en") or "").strip().lower()
                        no = (ing["name"].get("no") or "").strip()
                    # Check for _no/_en suffix fields (sample_recipes format)
                    elif ing.get("name_en"):
                        en = (ing.get("name_en") or "").strip().lower()
                        no = (ing.get("name_no") or "").strip()
                    # Strip prep/cutting descriptors ("i skiver", "(sliced)", etc)
                    # so this matches the equally-stripped keys the shopping
                    # list was deduplicated under, and so the Norwegian name
                    # itself doesn't leak the same prep text either.
                    en = strip_prep_descriptors(en).lower()
                    no = strip_prep_descriptors(no)
                    if en and no:
                        name_map[en] = no
        # Translate shopping list ingredient names and units. Units go through
        # the same normalize_no_unit()/UNIT_MAP_NO used for recipe ingredients
        # (see B15/B20/B45) - this route used to have its own much smaller,
        # separate unit map here (only pieces/piece/pcs -> stk), which is why
        # tbsp/tsp/bunch etc. kept showing up in English even after those
        # earlier fixes: this was a different code path that never got the
        # same mapping applied.
        for category, items in en_shopping.items():
            new_items = []
            for item in items:
                new_item = dict(item)
                en_name = (
                    strip_prep_descriptors(item.get("ingredient", "")).strip().lower()
                )
                if en_name in name_map:
                    new_item["ingredient"] = name_map[en_name]
                else:
                    new_item["ingredient"] = strip_prep_descriptors(
                        item.get("ingredient", "")
                    )
                new_item["unit"] = normalize_no_unit(item.get("unit", ""))
                new_items.append(new_item)
            shopping[category] = new_items
    else:
        shopping = menu["shopping_list"]

    from core.household_paths import load_pantry

    pantry = set(load_pantry(current_household_id()))
    for category, items in shopping.items():
        for item in items:
            item["in_pantry"] = item.get("ingredient", "").strip().lower() in pantry
            # Same allergen-tag translation as _normalize_recipe() (B46) -
            # shopping list items aggregate per-ingredient allergens from
            # whichever recipes contributed them, in whatever language each
            # one happened to be authored in.
            if item.get("allergens"):
                item["allergens"] = [
                    _translate_allergen(a, lang) for a in item["allergens"]
                ]

    return render_template(
        "shopping.html", shopping_list=shopping, pantry=sorted(pantry)
    )


@app.route("/api/pantry", methods=["GET"])
def api_get_pantry():
    """Pantry items in the CURRENT display language only - items that exist
    in both languages identically (e.g. 'salt') always show; items unique to
    the other language are hidden, even though they're still stored (adding
    'lemon' in English also silently stores 'sitron' so it's there if the
    household switches to Norwegian later)."""
    from core.household_paths import pantry_item_language

    lang = _get_lang()
    pantry = _load_pantry_db()
    visible = [p for p in pantry if pantry_item_language(p) in (lang, "both")]
    return jsonify({"success": True, "pantry": sorted(visible)})


@app.route("/api/pantry/add", methods=["POST"])
def api_add_pantry_item():
    """Adding a known staple also adds its translation in the other language
    (e.g. adding 'lemon' silently also stores 'sitron'), so the pantry stays
    in sync no matter which language the household views it in later. Items
    with no known translation (anything custom the household typed) are just
    stored as-is."""
    if not acting_role_can_edit():
        return (
            jsonify({"success": False, "message": "Viewers cannot edit the pantry"}),
            403,
        )
    from core.household_paths import pantry_item_translation, pantry_item_language

    data = request.get_json() or {}
    item = (data.get("item") or "").strip().lower()
    if not item:
        return jsonify({"success": False, "message": "No item provided"}), 400

    pantry = list(_load_pantry_db())
    added = False
    if item not in pantry:
        pantry.append(item)
        added = True
    translation = pantry_item_translation(item)
    if translation and translation not in pantry:
        pantry.append(translation)
        added = True
    if added:
        _save_pantry_db(pantry)
        log_activity(f"Added '{item}' to pantry")

    lang = _get_lang()
    visible = [p for p in pantry if pantry_item_language(p) in (lang, "both")]
    return jsonify({"success": True, "pantry": sorted(visible)})


@app.route("/api/pantry/reset", methods=["POST"])
def api_reset_pantry():
    """Reset pantry to default staples from pantry_staples.json seed file."""
    from core.household_paths import SEED_DIR
    import json as _json

    household_id = current_household_id()
    if not household_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401
    if not acting_role_can_edit():
        return (
            jsonify({"success": False, "message": "Viewers cannot edit the pantry"}),
            403,
        )

    staples_path = SEED_DIR / "pantry_staples.json"
    if not staples_path.exists():
        return (
            jsonify({"success": False, "message": "No default staples file found"}),
            404,
        )

    try:
        with open(staples_path, "r", encoding="utf-8") as f:
            pairs = _json.load(f).get("pantry_staples", [])
        items = set()
        for pair in pairs:
            if pair.get("en"):
                items.add(pair["en"].strip().lower())
            if pair.get("no"):
                items.add(pair["no"].strip().lower())
        _save_pantry_db(sorted(items))

        from core.household_paths import pantry_item_language

        lang = _get_lang()
        visible = sorted(p for p in items if pantry_item_language(p) in (lang, "both"))
        return jsonify({"success": True, "pantry": visible})
    except Exception as e:
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/pantry/remove", methods=["POST"])
def api_remove_pantry_item():
    """Removing a known staple also removes its translation in the other
    language, so e.g. removing 'sugar' also removes 'sukker'."""
    if not acting_role_can_edit():
        return (
            jsonify({"success": False, "message": "Viewers cannot edit the pantry"}),
            403,
        )
    from core.household_paths import pantry_item_translation, pantry_item_language

    data = request.get_json() or {}
    item = (data.get("item") or "").strip().lower()
    if not item:
        return jsonify({"success": False, "message": "No item provided"}), 400

    translation = pantry_item_translation(item)
    to_remove = {item}
    if translation:
        to_remove.add(translation)
    pantry = [p for p in _load_pantry_db() if p not in to_remove]
    _save_pantry_db(pantry)
    log_activity(f"Removed '{item}' from pantry")

    lang = _get_lang()
    visible = [p for p in pantry if pantry_item_language(p) in (lang, "both")]
    return jsonify({"success": True, "pantry": sorted(visible)})


def _load_household_categories(household_id):
    """Load categories from database (with fallback to file)."""
    household = current_household()
    if household:
        from core.household_paths import load_categories_from_db

        return load_categories_from_db(household)

    # Fallback to file-based for migration period
    from core.household_paths import categories_file

    path = categories_file(household_id)
    if not path.exists():
        return []
    with open(path, "r", encoding="utf-8") as f:
        return json.load(f)


def _save_household_categories(household_id, categories):
    """Save categories to database (with fallback to file)."""
    if household_id:
        from database.database import SessionLocal
        from database.models import Household

        db = SessionLocal()
        try:
            household = db.query(Household).filter(Household.id == household_id).first()
            if household:
                household.categories = categories
                db.commit()
                return
        except Exception as e:
            db.rollback()
            print(f"Error saving categories to database: {e}")
        finally:
            db.close()
        return

    # Fallback to file-based for migration period
    from core.household_paths import categories_file

    path = categories_file(household_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)


@app.route("/api/categories/add", methods=["POST"])
def api_add_category():
    """Owner-only: add a custom category to this household's category list."""
    if not acting_role_is_owner():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({"success": False, "message": "No household selected"}), 400

    data = request.get_json() or {}
    name = (data.get("name") or "").strip()
    icon = (data.get("icon") or "🍽️").strip()
    if not name:
        return jsonify({"success": False, "message": "Category name required"}), 400

    categories = _load_household_categories(household_id)
    code = name.lower().replace(" ", "_")
    if any(c.get("code") == code for c in categories):
        return jsonify({"success": False, "message": "Category already exists"}), 400

    categories.append(
        {
            "code": code,
            "name_no": name,
            "name_en": name,
            "description_no": "",
            "description_en": "",
            "icon": icon,
            "color": "#999999",
        }
    )
    _save_household_categories(household_id, categories)
    log_activity(f"Added category '{name}'")

    return jsonify({"success": True, "categories": _sort_categories(categories)})


@app.route("/api/categories/rename", methods=["POST"])
def api_rename_category():
    """Owner-only: rename a category in this household's category list."""
    if not acting_role_is_owner():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({"success": False, "message": "No household selected"}), 400

    data = request.get_json() or {}
    code = (data.get("code") or "").strip()
    new_name = (data.get("name") or "").strip()
    if not code or not new_name:
        return (
            jsonify(
                {"success": False, "message": "Category code and new name required"}
            ),
            400,
        )

    categories = _load_household_categories(household_id)
    found = False
    for c in categories:
        if c.get("code") == code:
            c["name_no"] = new_name
            c["name_en"] = new_name
            found = True
            break

    if not found:
        return jsonify({"success": False, "message": "Category not found"}), 404

    _save_household_categories(household_id, categories)
    log_activity(f"Renamed category to '{new_name}'")

    return jsonify({"success": True, "categories": _sort_categories(categories)})


@app.route("/api/categories/remove", methods=["POST"])
def api_remove_category():
    """Owner-only: remove a category from this household's category list.
    Moves all recipes in the deleted category to 'Uncategorized'."""
    if not acting_role_is_owner():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({"success": False, "message": "No household selected"}), 400

    data = request.get_json() or {}
    code = (data.get("code") or "").strip()
    if not code:
        return jsonify({"success": False, "message": "Category code required"}), 400

    categories = _load_household_categories(household_id)
    cat_to_delete = next((c for c in categories if c.get("code") == code), None)
    if not cat_to_delete:
        return jsonify({"success": False, "message": "Category not found"}), 404

    cat_names_to_move = {
        cat_to_delete.get("name_en", ""),
        cat_to_delete.get("name_no", ""),
    }

    uncategorized = next(
        (c for c in categories if c.get("code") == "uncategorized"), None
    )
    if not uncategorized:
        uncategorized = {
            "code": "uncategorized",
            "name_en": "Uncategorized",
            "name_no": "Ukategorisert",
        }
        categories.append(uncategorized)

    uncategorized_name = uncategorized.get(f"name_{_get_lang()}") or uncategorized.get(
        "name_en", "Uncategorized"
    )

    recipes = load_recipes_db()
    moved = 0
    for r in recipes:
        if r.get("category") in cat_names_to_move:
            r["category"] = uncategorized_name
            moved += 1
    if moved:
        save_recipes_db(recipes)

    remaining = [c for c in categories if c.get("code") != code]
    _save_household_categories(household_id, remaining)
    from core.household_paths import mark_category_removed

    mark_category_removed(household_id, code)
    msg = f"Removed category '{code}'"
    if moved:
        msg += f" ({moved} recipes moved to Uncategorized)"
    log_activity(msg)

    return jsonify(
        {
            "success": True,
            "categories": _sort_categories(remaining),
            "recipes_moved": moved,
        }
    )


@app.route("/api/categories/merge", methods=["POST"])
def api_merge_category():
    """Owner-only: move any recipes tagged with `from_code` over to
    `into_code`'s name (in whichever language each recipe's category string
    happens to be in), then remove the now-empty `from_code` category."""
    if not acting_role_is_owner():
        return jsonify({"success": False, "message": "Permission denied"}), 403

    household_id = current_household_id()
    if not household_id:
        return jsonify({"success": False, "message": "No household selected"}), 400

    data = request.get_json() or {}
    from_code = (data.get("from_code") or "").strip()
    into_code = (data.get("into_code") or "").strip()
    if not from_code or not into_code:
        return jsonify({"success": False, "message": "Both categories required"}), 400
    if from_code == into_code:
        return (
            jsonify(
                {"success": False, "message": "Cannot merge a category into itself"}
            ),
            400,
        )

    categories = _load_household_categories(household_id)
    from_cat = next((c for c in categories if c.get("code") == from_code), None)
    into_cat = next((c for c in categories if c.get("code") == into_code), None)
    if not from_cat or not into_cat:
        return jsonify({"success": False, "message": "Category not found"}), 404

    from_names = {from_cat.get("name_en", ""), from_cat.get("name_no", "")}
    target_lang = _get_lang()
    target_name = (
        into_cat.get(f"name_{target_lang}")
        or into_cat.get("name_en")
        or into_cat["code"]
    )

    recipes = load_recipes_db()
    moved = 0
    for r in recipes:
        if r.get("category") in from_names:
            r["category"] = target_name
            moved += 1
    if moved:
        save_recipes_db(recipes)

    remaining = [c for c in categories if c.get("code") != from_code]
    _save_household_categories(household_id, remaining)
    from core.household_paths import mark_category_removed

    mark_category_removed(household_id, from_code)
    log_activity(
        f"Merged category '{from_cat.get('name_en')}' into '{into_cat.get('name_en')}' ({moved} recipe(s) moved)"
    )

    return jsonify(
        {"success": True, "categories": _sort_categories(remaining), "moved": moved}
    )


@app.route("/about")
def about_page():
    lang = _get_lang()
    return render_template("about.html", lang=lang)


@app.route("/whats-new")
def whats_new():
    lang = _get_lang()
    return render_template("whats_new.html", lang=lang)


@app.route("/whats-planned")
def whats_planned():
    lang = _get_lang()
    return render_template("whats_planned.html", lang=lang)


@app.route("/help/advanced")
def help_advanced():
    lang = _get_lang()
    return render_template("help_advanced.html", lang=lang)


@app.route("/help/tips")
def help_tips():
    lang = _get_lang()
    return render_template("help_tips.html", lang=lang)


@app.route("/feedback")
def feedback_page():
    """Simple feedback form for trial testers - any logged-in user can report."""
    if not session.get("user_id"):
        return redirect(url_for("login_page"))
    return render_template("feedback.html", success=request.args.get("success"))


@app.route("/api/feedback", methods=["POST"])
def api_submit_feedback():
    """Save feedback to a single append-only JSON file - simple enough for a
    handful of trial testers; not meant to scale past that without revisiting."""
    if not session.get("user_id"):
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json() or {}
    feedback_type = (data.get("type") or "other").strip()
    title = (data.get("title") or "").strip()
    description = (data.get("description") or "").strip()
    if not title or not description:
        return (
            jsonify({"success": False, "message": "Title and description required"}),
            400,
        )

    from datetime import datetime

    entry = {
        "timestamp": datetime.now().isoformat(),
        "type": feedback_type,
        "title": title,
        "description": description,
        "submitted_by": session.get("user_email", "unknown"),
        "household_id": current_household_id(),
    }

    feedback_file = DATA_DIR / "feedback.json"
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.append(entry)
    with open(feedback_file, "w", encoding="utf-8") as f:
        json.dump(entries, f, ensure_ascii=False, indent=2)

    if ADMIN_EMAIL:
        try:
            _notify_admin_of_feedback(entry)
        except Exception as e:
            logger.error(f"Feedback admin notification failed: {e}")

    return jsonify({"success": True})


@app.route("/feedback/list")
def feedback_list_page():
    """App-developer-only view of all submitted feedback, newest first. Gated
    by ADMIN_EMAIL specifically - NOT the same thing as being a household
    owner, which is a per-household role any signed-up user can hold."""
    user_email = (session.get("user_email") or "").strip().lower()
    if not ADMIN_EMAIL or user_email != ADMIN_EMAIL:
        return render_template("error.html", message="Not authorized"), 403

    feedback_file = DATA_DIR / "feedback.json"
    entries = []
    if feedback_file.exists():
        try:
            with open(feedback_file, "r", encoding="utf-8") as f:
                entries = json.load(f)
        except Exception:
            entries = []
    entries.reverse()  # newest first
    return render_template("feedback_list.html", entries=entries)


@app.route("/add-recipe")
def add_recipe_page():
    return render_template("add-recipe.html")


@app.route("/all-recipes")
def all_recipes_page():
    lang = _get_lang()
    # Load both household recipes AND shared sample recipes (same as MenuGenerator does)
    all_recipes = []
    sample_recipes_path = SEED_DIR / "sample_recipes.json"
    if sample_recipes_path.exists():
        try:
            with open(sample_recipes_path, "r", encoding="utf-8") as f:
                all_recipes.extend(json.load(f))
        except Exception:
            pass
    all_recipes.extend(load_recipes_db())
    recipes = [_normalize_recipe(r, lang) for r in all_recipes]
    return render_template("all-recipes.html", recipes=recipes)


@app.route("/settings")
def settings_page():
    """Owner-only: account/referral details and the activity log live here, so
    non-owner profiles (kids, viewers, editors) have no business seeing this page."""
    household_id_for_check = current_household_id()
    if household_id_for_check and not acting_role_is_owner():
        return redirect(url_for("dashboard"))

    activity_log = []
    household_id = current_household_id()
    if household_id and session.get("user_id") and acting_role_is_owner():
        from database.database import SessionLocal
        from database.models import Household as _H

        _db = SessionLocal()
        try:
            _hh = _db.query(_H).filter(_H.id == household_id).first()
            if _hh and _hh.activity_log:
                activity_log = list(reversed(_hh.activity_log))[:50]
        finally:
            _db.close()

    referral_code = None
    user_id = session.get("user_id")
    if user_id:
        from core.auth_helpers import get_user_by_email

        user = get_user_by_email(session.get("user_email", ""))
        if user:
            referral_code = user.referral_code

    categories = []
    if household_id:
        raw_cats = _load_household_categories(household_id)
        if raw_cats:
            lang = _get_lang()
            # Skip pack-name pseudo-categories (imported: true) here too -
            # same reasoning as /api/categories: recipes never carry one of
            # these as their actual category anymore (see B4b), so showing
            # them in the manage-categories list would let an owner try to
            # rename/merge/delete something that was never a real category.
            for cat in raw_cats:
                if cat.get("imported"):
                    continue
                translated = dict(cat)
                translated["name"] = (
                    cat.get(f"name_{lang}") or cat.get("name_en") or cat.get("code")
                )
                categories.append(translated)
            categories = _sort_categories(categories)

    has_pin = False
    if user_id:
        from core.auth_helpers import get_user_by_email as _get_user_by_email

        _user = _get_user_by_email(session.get("user_email", ""))
        has_pin = bool(_user and _user.pin_hash)

    pantry = []
    if household_id:
        from core.household_paths import pantry_item_language

        lang = _get_lang()
        pantry = sorted(
            p for p in _load_pantry_db() if pantry_item_language(p) in (lang, "both")
        )

    return render_template(
        "settings.html",
        activity_log=activity_log,
        referral_code=referral_code,
        categories=categories,
        has_pin=has_pin,
        pantry=pantry,
    )


@app.route("/api/account/set-pin", methods=["POST"])
def api_set_pin():
    """Owner-only: set or change the shared-device PIN used by the profile picker."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    data = request.get_json() or {}
    pin = (data.get("pin") or "").strip()

    from core.auth_helpers import set_pin

    success, message = set_pin(user_id, pin)
    status = 200 if success else 400
    return jsonify({"success": success, "message": message}), status


@app.route("/api/account/clear-pin", methods=["POST"])
def api_clear_pin():
    """Owner-only: remove the PIN, falling back to the full account password."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"success": False, "message": "Not authenticated"}), 401

    from core.auth_helpers import clear_pin

    success, message = clear_pin(user_id)
    return jsonify({"success": success, "message": message})


# ── Household/Team Management Routes ──────────────────────────────────────────


@app.route("/household-settings")
def household_settings():
    """View and manage household settings. Owner-only: this is a dinner-planning app,
    not a playground, so non-owner members have no business here even to look."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    from core.household_helpers import (
        get_user_households,
        get_household_members,
        get_household,
    )

    # Resolve the active household through current_household_id(), which
    # re-validates that it actually belongs to the CURRENT user before
    # trusting it (see B50) - previously this route read the raw session
    # value directly into a household_id and rendered it with no ownership
    # check at all, the same shape of bug as B50.
    active_household_id = current_household_id()
    if active_household_id and not acting_role_is_owner():
        return redirect(
            url_for(
                "settings_page",
                error="Only the household owner can access household settings",
            )
        )

    # Get all user's households
    all_households = get_user_households(user_id)

    current_household = (
        get_household(active_household_id) if active_household_id else None
    )

    if not current_household and all_households:
        current_household = all_households[0]
        session["current_household_id"] = str(current_household.id)

    error = request.args.get("error")
    success = request.args.get("success")

    members = []
    owner_email = ""
    can_manage = False
    is_owner = False
    other_households = []

    if current_household:
        members = get_household_members(str(current_household.id))

        # Find owner email
        for member in members:
            if member["role"] == "owner":
                owner_email = member["email"]
                break

        # Check permissions - keyed off the ACTING identity, not just the account,
        # so a co-owner profile gets the same management rights as the owner.
        is_owner = acting_role_is_owner()
        user_member = next((m for m in members if m["user_id"] == user_id), None)
        can_manage = is_owner or (user_member and user_member["role"] == "editor")

        # Get other households
        other_households = [
            h for h in all_households if str(h.id) != str(current_household.id)
        ]

    profile_count = sum(1 for m in members if m["is_profile"])

    return render_template(
        "household-settings.html",
        current_household=current_household,
        members=members,
        owner_email=owner_email,
        can_manage=can_manage,
        is_owner=is_owner,
        other_households=other_households,
        profile_count=profile_count,
        max_profiles=MAX_PROFILES_PER_HOUSEHOLD,
        error=error,
        success=success,
    )


@app.route("/household/create", methods=["POST"])
def create_household_handler():
    """Create a new household."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    from core.household_helpers import create_household

    household_name = request.form.get("household_name", "").strip()
    success, result, household_id = create_household(user_id, household_name)

    if success:
        session["current_household_id"] = household_id
        return redirect(
            url_for("household_settings", success="Household created successfully")
        )
    else:
        return redirect(url_for("household_settings", error=result))


@app.route("/household/set-current", methods=["POST"])
def set_current_household():
    """Switch to a different household."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    household_id = request.form.get("household_id")

    from core.household_helpers import user_can_access_household

    if user_can_access_household(user_id, household_id):
        session["current_household_id"] = household_id
        return redirect(url_for("household_settings", success="Switched household"))
    else:
        return redirect(url_for("household_settings", error="Access denied"))


@app.route("/household/update", methods=["POST"])
def update_household_handler():
    """Update household details."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    household_id = current_household_id()
    if not household_id:
        return redirect(url_for("household_settings", error="No household selected"))

    from core.household_helpers import update_household

    if not acting_role_is_owner():
        return redirect(url_for("household_settings", error="Permission denied"))

    household_name = request.form.get("household_name", "").strip()

    name_to_update = household_name if household_name else None
    success, result = update_household(household_id, name=name_to_update)

    if success:
        return redirect(url_for("household_settings", success="Household updated"))
    else:
        return redirect(url_for("household_settings", error=result))


@app.route("/household/delete", methods=["POST"])
def delete_household_handler():
    """Delete household (owner only)."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    household_id = current_household_id()
    if not household_id:
        return redirect(url_for("household_settings", error="No household selected"))

    from core.household_helpers import delete_household

    success, result = delete_household(household_id, user_id)

    if success:
        session.pop("current_household_id", None)
        return redirect(url_for("household_settings", success="Household deleted"))
    else:
        return redirect(url_for("household_settings", error=result))


@app.route("/profile-picker")
def profile_picker():
    """Show 'who's using this' profile picker if the current household has profiles."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    from core.household_helpers import get_user_households, get_household_members

    all_households = get_user_households(user_id)
    active_household_id = current_household_id()
    current_household = None

    if active_household_id:
        from core.household_helpers import get_household

        current_household = get_household(active_household_id)

    if not current_household and all_households:
        current_household = all_households[0]
        session["current_household_id"] = str(current_household.id)

    if not current_household:
        return redirect(
            url_for("household_settings", error="Create a household to get started")
        )

    members = get_household_members(str(current_household.id))

    if not any(m["is_profile"] for m in members):
        return redirect("/")

    owner_password_error = request.args.get("owner_password_error")
    from core.auth_helpers import get_user_by_email

    owner_account = get_user_by_email(session.get("user_email", ""))
    owner_has_pin = bool(owner_account and owner_account.pin_hash)
    return render_template(
        "profile-picker.html",
        household=current_household,
        members=members,
        owner_password_error=owner_password_error,
        owner_has_pin=owner_has_pin,
    )


@app.route("/profile-picker/select", methods=["POST"])
def select_profile():
    """Set the active profile for this session after picking from the picker."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    member_id = request.form.get("member_id")
    is_account_holder = request.form.get("is_account_holder")

    if is_account_holder:
        from core.auth_helpers import get_user_by_email, verify_pin, authenticate_user

        user = get_user_by_email(session.get("user_email", ""))

        if user and user.pin_hash:
            pin = request.form.get("owner_pin", "")
            if not verify_pin(user_id, pin):
                return redirect(
                    url_for("profile_picker", owner_password_error="Incorrect PIN")
                )
        else:
            password = request.form.get("owner_password", "")
            success, _ = authenticate_user(session.get("user_email", ""), password)
            if not success:
                return redirect(
                    url_for("profile_picker", owner_password_error="Incorrect password")
                )

        household_id = current_household_id()
        from core.household_helpers import get_household_members

        owner_name = session.get("user_email")
        if household_id:
            owner_member = next(
                (
                    m
                    for m in get_household_members(household_id)
                    if m["user_id"] == user_id
                ),
                None,
            )
            if owner_member:
                owner_name = owner_member["display_name"]

        session.pop("active_profile_id", None)
        session["active_profile_name"] = owner_name
        response = redirect("/")
        response.delete_cookie("remembered_profile_id")
        return response

    household_id = current_household_id()
    from core.household_helpers import get_member_by_id

    member = get_member_by_id(member_id, household_id)

    if not member or not member.is_profile:
        return redirect(url_for("profile_picker", error="Profile not found"))

    session["active_profile_id"] = str(member.id)
    session["active_profile_name"] = member.display_name

    response = redirect("/")
    response.set_cookie(
        "remembered_profile_id",
        str(member.id),
        max_age=PROFILE_COOKIE_MAX_AGE,
        httponly=True,
        samesite="Lax",
    )
    return response


@app.route("/household/add-profile", methods=["POST"])
def add_household_profile():
    """Add a lightweight member profile (no login of its own) to the household."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))

    household_id = current_household_id()
    if not household_id:
        return redirect(url_for("household_settings", error="No household selected"))

    from core.household_helpers import create_profile, get_profiles

    if not acting_role_is_owner():
        return redirect(url_for("household_settings", error="Permission denied"))

    if len(get_profiles(household_id)) >= MAX_PROFILES_PER_HOUSEHOLD:
        return redirect(
            url_for(
                "household_settings",
                error=f"This household already has the maximum of {MAX_PROFILES_PER_HOUSEHOLD} profiles",
            )
        )

    display_name = request.form.get("display_name", "").strip()
    role = request.form.get("role", "viewer")

    success, result, member_id = create_profile(household_id, display_name, role)

    if success:
        return redirect(url_for("household_settings", success=result))
    else:
        return redirect(url_for("household_settings", error=result))


# API routes for household management
@app.route("/api/household/remove-member", methods=["POST"])
def api_remove_household_member():
    """API: Remove household member."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    household_id = current_household_id()
    member_id = request.form.get("member_id")

    from core.household_helpers import remove_household_member

    if not acting_role_is_owner():
        return jsonify({"error": "Permission denied"}), 403

    success, message = remove_household_member(household_id, member_id, user_id)

    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"error": message}), 400


@app.route("/api/profile/set-avatar", methods=["POST"])
def api_set_avatar():
    """Set an emoji avatar for a member. Allowed for: the owner managing any member,
    or the currently active identity setting its own avatar (low-stakes, no permission gate needed).
    """
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    household_id = current_household_id()
    member_id = request.form.get("member_id")
    emoji = request.form.get("emoji", "")

    if emoji not in AVATAR_EMOJI_CHOICES:
        return jsonify({"error": "Invalid avatar choice"}), 400

    is_own_active_identity = member_id == session.get("active_profile_id")
    if not is_own_active_identity and not acting_role_is_owner():
        return jsonify({"error": "Permission denied"}), 403

    from core.household_helpers import set_member_avatar

    success, message = set_member_avatar(member_id, household_id, emoji)

    if success:
        return jsonify({"success": True, "avatar": emoji})
    else:
        return jsonify({"error": message}), 400


@app.route("/api/household/rename-member", methods=["POST"])
def api_rename_member():
    """API: Rename a household member (profile or the owner's own display name)."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    if not acting_role_is_owner():
        return jsonify({"error": "Permission denied"}), 403

    household_id = current_household_id()
    member_id = request.form.get("member_id")
    display_name = request.form.get("display_name", "")

    from core.household_helpers import rename_member, get_member_by_id

    success, message = rename_member(member_id, household_id, display_name)

    if success:
        member = get_member_by_id(member_id, household_id)
        if (
            member
            and member.is_profile
            and session.get("active_profile_id") == str(member.id)
        ):
            session["active_profile_name"] = member.display_name
        elif member and not member.is_profile and member.user_id == user_id:
            session["active_profile_name"] = member.display_name
        return redirect(url_for("household_settings", success="Renamed"))
    else:
        return redirect(url_for("household_settings", error=message))


@app.route("/api/household/update-member-role", methods=["POST"])
def api_update_member_role():
    """API: Update member role."""
    user_id = session.get("user_id")
    if not user_id:
        return jsonify({"error": "Not authenticated"}), 401

    household_id = current_household_id()
    member_id = request.form.get("member_id")
    new_role = request.form.get("role")

    from core.household_helpers import update_member_role

    success, message = update_member_role(household_id, member_id, new_role, user_id)

    if success:
        return jsonify({"success": True, "message": message})
    else:
        return jsonify({"error": message}), 403


# ── Auth routes ───────────────────────────────────────────────────────────────


# Email/Password Authentication Routes
@app.route("/login-page")
def login_page():
    """Render login page."""
    error = request.args.get("error")
    return render_template(
        "login.html", error=error, email=request.args.get("email", "")
    )


@app.route("/login", methods=["POST"])
def login_local():
    """Handle local email/password login."""
    from core.auth_helpers import authenticate_user

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")

    if not email or not password:
        return (
            render_template(
                "login.html", error="Email and password required", email=email
            ),
            400,
        )

    success, result = authenticate_user(email, password)
    if not success:
        if result == "EMAIL_NOT_CONFIRMED":
            return (
                render_template(
                    "login.html",
                    email=email,
                    unconfirmed_email=email,
                    error="Please confirm your email before logging in.",
                ),
                401,
            )
        return render_template("login.html", error=result, email=email), 401

    user = result
    session.permanent = True
    session["user_id"] = str(user.id)
    session["user_email"] = user.email
    session["auth_type"] = "local"
    session.pop("active_profile_id", None)
    # Clear any household id left over from a previous login in this same
    # browser session - current_household_id() now independently verifies
    # membership too, but clearing it here as well means a fresh login
    # always starts from a clean slate rather than relying on that check.
    session.pop("current_household_id", None)
    logger.info(f"User logged in (local): {user.email}")
    return redirect(url_for("profile_picker"))


@app.route("/confirm-email/<token>")
def confirm_email_route(token):
    """Land here from the link in the confirmation email. One-time use -
    the token is cleared on success, so a second click just shows the
    already-confirmed case rather than erroring."""
    from core.auth_helpers import confirm_email

    success, result = confirm_email(token)
    if success:
        return render_template(
            "login.html",
            success="✓ Email confirmed! You can now log in.",
            email=result.email,
        )
    elif result == "Invalid or expired confirmation link":
        return (
            render_template(
                "login.html",
                error="Email confirmation failed: link expired or incorrect token. You can still log in if your email was confirmed.",
            ),
            400,
        )
    else:
        return render_template("login.html", error=result), 400


@app.route("/resend-confirmation", methods=["POST"])
def resend_confirmation():
    """Re-send the confirmation email with a fresh token - the fallback for
    a tester whose first email landed in spam or was sent to a typo'd
    address they've since corrected via a new signup."""
    from core.auth_helpers import regenerate_confirmation_token

    email = request.form.get("email", "").strip()
    if not email:
        return render_template("login.html", error="Email required"), 400

    success, result = regenerate_confirmation_token(email)
    if not success:
        return render_template("login.html", error=result, email=email), 400

    _send_confirmation_email(result)
    logger.info(f"Resent confirmation email to {result.email}")
    return render_template(
        "login.html",
        success="Confirmation email resent - please check your inbox.",
        email=email,
    )


@app.route("/forgot-password")
def forgot_password_page():
    return render_template(
        "forgot_password.html",
        error=request.args.get("error"),
        success=request.args.get("success"),
    )


@app.route("/forgot-password", methods=["POST"])
def forgot_password():
    from core.auth_helpers import request_password_reset

    email = request.form.get("email", "").strip()
    if not email:
        return redirect(url_for("forgot_password_page", error="Email required"))
    success, user = request_password_reset(email)
    if user:
        _send_password_reset_email(user)
        logger.info(f"Password reset email sent to {user.email}")
    # Always show the same message regardless of whether email exists
    return redirect(
        url_for(
            "forgot_password_page",
            success="If that email is registered, a reset link is on its way.",
        )
    )


@app.route("/reset-password/<token>")
def reset_password_page(token):
    return render_template(
        "reset_password.html", token=token, error=request.args.get("error")
    )


@app.route("/reset-password/<token>", methods=["POST"])
def reset_password_submit(token):
    from core.auth_helpers import reset_password

    new_password = request.form.get("password", "")
    confirm = request.form.get("password_confirm", "")
    if new_password != confirm:
        return render_template(
            "reset_password.html", token=token, error="Passwords do not match"
        )
    success, msg = reset_password(token, new_password)
    if not success:
        return render_template("reset_password.html", token=token, error=msg)
    return redirect(
        url_for("login_page", success="Password updated — you can now log in.")
    )


@app.route("/account/delete", methods=["POST"])
def delete_own_account():
    """User deletes their own account. Requires password confirmation."""
    user_id = session.get("user_id")
    if not user_id:
        return redirect(url_for("login_page"))
    from core.auth_helpers import (
        delete_user_account,
        get_user_by_email,
        verify_password,
    )

    password = request.form.get("password", "")
    user_email = session.get("user_email", "")
    user = get_user_by_email(user_email)
    if not user or not verify_password(user.password_hash, password):
        return redirect(
            url_for("settings_page", error="Incorrect password — account not deleted")
        )
    # Clean up household data on disk too
    user_id_str = str(user_id)
    from core.auth_helpers import delete_user_account

    success, msg = delete_user_account(user_id_str)
    if not success:
        return redirect(
            url_for("settings_page", error=f"Could not delete account: {msg}")
        )
    # Clean up the household folder if it exists
    from core.household_paths import HOUSEHOLDS_DIR
    import shutil

    household_id = current_household_id()
    if household_id:
        hdir = HOUSEHOLDS_DIR / str(household_id)
        if hdir.exists():
            shutil.rmtree(hdir, ignore_errors=True)
    session.clear()
    logger.info(f"Account deleted: {user_email}")
    return redirect(
        url_for("login_page", success="Your account has been permanently deleted.")
    )


# ── Admin panel ───────────────────────────────────────────────────────────────


def _is_admin():
    """Check if the currently logged-in user is the site admin.
    Must match ADMIN_EMAIL AND not be acting as a family member profile."""
    admin_email = os.getenv("ADMIN_EMAIL", "").strip().lower()
    if not admin_email:
        return False
    if session.get("user_email", "").lower() != admin_email:
        return False
    if session.get("active_profile_id"):
        return False
    return True


@app.route("/admin")
def admin_panel():
    if not _is_admin():
        return redirect(url_for("dashboard"))
    from database.models import User as UserModel
    from database.database import SessionLocal as _SessionLocal

    db = _SessionLocal()
    try:
        users = db.query(UserModel).order_by(UserModel.created_at.desc()).all()
        users_data = [
            {
                "id": str(u.id),
                "email": u.email,
                "confirmed": bool(u.email_confirmed_at),
                "created_at": (
                    u.created_at.strftime("%Y-%m-%d %H:%M") if u.created_at else ""
                ),
                "referral_code": u.referral_code,
            }
            for u in users
        ]
    finally:
        db.close()
    return render_template("admin.html", users=users_data)


@app.route("/admin/normalize-recipe-units", methods=["POST"])
def admin_normalize_recipe_units():
    """One-time maintenance action: households that imported recipe packs
    before the unit-normalization fix (tbsp/tsp -> ss/ts, etc; see B20/B15)
    have that stale, already-copied-in data permanently baked into their own
    recipes_db column - fixing the seed files only helps *future* imports.
    This walks every household's already-imported recipes and re-applies the
    same normalization directly to their DB copy."""
    if not _is_admin():
        return redirect(url_for("dashboard"))

    from database.models import Household as _Household
    from database.database import SessionLocal as _SessionLocal
    from core.ingredient_deduplicator import normalize_no_unit

    db = _SessionLocal()
    households_changed = 0
    ingredients_fixed = 0
    try:
        households = db.query(_Household).all()
        for household in households:
            recipes = household.recipes_db
            if not isinstance(recipes, list):
                continue
            changed = False
            for recipe in recipes:
                if not isinstance(recipe, dict):
                    continue
                for field in (
                    "ingredients",
                    "ingredients_included",
                    "ingredients_not_included",
                ):
                    for ing in recipe.get(field, []) or []:
                        if not isinstance(ing, dict):
                            continue
                        unit = ing.get("unit")
                        new_unit = normalize_no_unit(unit)
                        if new_unit != unit:
                            ing["unit"] = new_unit
                            changed = True
                            ingredients_fixed += 1
            if changed:
                # Reassign (not just mutate in place) so SQLAlchemy's JSONB
                # change tracking actually notices the update.
                household.recipes_db = recipes
                households_changed += 1
        db.commit()
    except Exception as e:
        db.rollback()
        logger.error(f"Error normalizing recipe units: {e}")
        return redirect(url_for("admin_panel", error=f"Normalization failed: {e}"))
    finally:
        db.close()

    logger.info(
        f"Admin normalized recipe units: {ingredients_fixed} ingredients across {households_changed} households"
    )
    return redirect(
        url_for(
            "admin_panel",
            success=f"Normalized {ingredients_fixed} ingredient units across {households_changed} households",
        )
    )


@app.route("/admin/delete-user", methods=["POST"])
def admin_delete_user():
    if not _is_admin():
        return redirect(url_for("dashboard"))
    from core.auth_helpers import delete_user_account

    user_id = request.form.get("user_id", "").strip()
    if not user_id:
        return redirect(url_for("admin_panel", error="No user ID provided"))
    success, msg = delete_user_account(user_id)
    if success:
        logger.info(f"Admin deleted user {user_id}")
        return redirect(url_for("admin_panel", success=f"User deleted successfully"))
    return redirect(url_for("admin_panel", error=msg))


@app.route("/welcome")
def welcome():
    """Promo/demo landing page shown to referral-link visitors before they hit the signup form."""
    return render_template("welcome.html", ref=request.args.get("ref", ""))


@app.route("/signup")
def signup():
    """Render signup page."""
    error = request.args.get("error")
    ref = request.args.get("ref", "")
    if ref and not request.args.get("from_welcome"):
        return redirect(url_for("welcome", ref=ref))
    return render_template(
        "signup.html", error=error, email=request.args.get("email", ""), ref=ref
    )


@app.route("/signup", methods=["POST"])
def signup_local():
    """Handle local user registration."""
    from core.auth_helpers import create_user

    email = request.form.get("email", "").strip()
    password = request.form.get("password", "")
    password_confirm = request.form.get("password_confirm", "")
    ref = request.form.get("ref", "").strip()

    if not email or not password or not password_confirm:
        return (
            render_template(
                "signup.html", error="All fields required", email=email, ref=ref
            ),
            400,
        )

    if password != password_confirm:
        return (
            render_template(
                "signup.html", error="Passwords do not match", email=email, ref=ref
            ),
            400,
        )

    success, result, user_id = create_user(
        email, password, referred_by_code=ref or None
    )
    if not success:
        return render_template("signup.html", error=result, email=email, ref=ref), 400

    user = result
    logger.info(f"New user registered (pending email confirmation): {user.email}")
    _send_confirmation_email(user)
    return render_template("signup.html", email=email, ref=ref, confirmation_sent=True)


@app.route("/login")
def login():
    """Redirect to login page (for backward compatibility)."""
    return redirect(url_for("login_page"))


@app.route("/logout")
def logout():
    """Log out the current user."""
    user_email = session.get("user_email", "User")
    auth_type = session.get("auth_type", "unknown")
    session.clear()
    logger.info(f"User logged out ({auth_type}): {user_email}")
    return redirect("/")


@app.route("/api/user")
def api_user():
    """Get current user info."""
    user_id = session.get("user_id")
    user_email = session.get("user_email")
    auth_type = session.get("auth_type")

    if user_id and user_email:
        return jsonify(
            {
                "authenticated": True,
                "user_id": user_id,
                "email": user_email,
                "auth_type": auth_type or "unknown",
            }
        )

    return jsonify({"authenticated": False})


# NOTE: /api/debug-token was removed 2026-07-05 security pass - it decoded
# and returned the logged-in user's Azure JWT claims to anyone with an
# authenticated session, left in from earlier debugging despite its own
# docstring saying to remove it.

# ── API routes ────────────────────────────────────────────────────────────────


@app.route("/api/menu")
def api_menu():
    menu = load_menu()
    if not menu:
        return jsonify({"error": "No menu generated yet"}), 404
    lang = _get_lang()
    day_map = _DAY_TRANSLATIONS.get(lang, {})
    import copy

    menu = copy.deepcopy(menu)
    for dinner in menu.get("dinners", []):
        if dinner.get("day") in day_map:
            dinner["day"] = day_map[dinner["day"]]
        # Always resolve the title to a plain string for this language -
        # titles are stored as bilingual {'en':..., 'no':...} dicts, and
        # skipping this (previously only done when a day_map existed, i.e.
        # Norwegian) left the raw dict in place for English, which the
        # sidebar JS then stringified as "[object Object]".
        dinner["title"] = _resolve(dinner.get("title"), lang)
        # Same stale-"0 MIN" self-heal as the dashboard route.
        if not dinner.get("time_minutes"):
            source_recipe = find_recipe(dinner.get("recipe_id"))
            if source_recipe:
                dinner["time_minutes"] = (
                    source_recipe.get("time_minutes")
                    or source_recipe.get("cookTimeMinutes")
                    or 0
                )
    logger.info("API menu endpoint accessed")
    return jsonify(menu)


@app.route("/api/regenerate", methods=["POST"])
def api_regenerate():
    """Build a fresh weekly menu from the selected categories/favorites and
    save it, replacing whatever menu existed before.

    The save happens inside locked_household() (row-locked via
    SELECT ... FOR UPDATE) rather than through MenuGenerator's own separate
    save session, so a regenerate can't land in between a concurrent
    swap-recipe's read and write and get silently overwritten (or overwrite
    it) - both now go through the same lock on this household's row."""
    if not acting_role_can_edit():
        return (
            jsonify(
                {"status": "error", "message": "Viewers cannot regenerate the menu"}
            ),
            403,
        )

    try:
        from core.menu_generator import MenuGenerator

        data = request.get_json() or {}
        selected_categories = (
            data.get("categories")
            or data.get("selected_categories")
            or ["Quick Dinners", "Fish & Seafood", "Vegetarian"]
        )
        favorite_recipe_ids = data.get("favorite_recipe_ids", [])
        try:
            num_dinners = int(data.get("num_dinners", 6))
        except (TypeError, ValueError):
            num_dinners = 6
        num_dinners = max(1, min(6, num_dinners))
        logger.info(
            f"Generating menu with categories: {selected_categories}, favorites: {len(favorite_recipe_ids)}, num_dinners: {num_dinners}"
        )
        generator = MenuGenerator(
            selected_categories=selected_categories,
            household_id=current_household_id(),
            favorite_recipe_ids=favorite_recipe_ids,
        )
        # save=False: persistence now happens below, inside locked_household(),
        # instead of through the generator's own separate save session.
        menu = generator.run(num_dinners=num_dinners, save=False)

        if not menu or not menu.get("dinners"):
            return (
                jsonify(
                    {
                        "status": "error",
                        "message": "No recipes available for selected categories. Please select different categories or add recipes.",
                    }
                ),
                400,
            )

        with locked_household() as (db, household):
            if household:
                from core.household_paths import (
                    save_weekly_menu_to_db,
                    append_activity_to_db,
                )

                save_weekly_menu_to_db(household, menu)
                append_activity_to_db(
                    household, current_actor_name(), "Regenerated the weekly menu"
                )
            else:
                # No DB-backed household (file-storage fallback) - fall back
                # to the generator's own file-based save path.
                generator.save_menu(menu)
                log_activity("Regenerated the weekly menu")

        logger.info("Menu regenerated via API")
        return jsonify({"status": "success", "menu": menu})
    except Exception as e:
        import traceback

        logger.error(f"Menu regeneration failed: {e}")
        logger.error(traceback.format_exc())
        return jsonify({"status": "error", "message": str(e)}), 500


def _sort_categories(categories):
    """Favorites always sorts first; everything else is alphabetical by
    display name."""

    def sort_key(c):
        if c.get("code") == "favorites":
            return (-1, "")
        return (0, c.get("name", c.get("name_en", "")).lower())

    return sorted(categories, key=sort_key)


@app.route("/api/categories")
def get_categories():
    """Get all available categories for this household, translated to current language.

    Previously read this household's categories.json file directly - but
    add/rename/remove/merge all write through _load_household_categories()/
    _save_household_categories(), which are DB-backed (with file as a
    migration-period fallback only). For any household that's already
    DB-backed, that meant categories added/renamed/removed via the API were
    saved correctly, but this listing endpoint (which drives the category
    filter dropdown, Add Recipe's category select, etc.) never reflected any
    of it - it kept reading the stale, untouched flat file. Fixed to use the
    same DB-aware loader as the rest of the category routes."""
    lang = _get_lang()
    household_id = current_household_id()
    categories = []

    # Add Favorites as a special first category (client-side only, stored in localStorage)
    favorites_name = "Favorites" if lang == "en" else "Favoritter"
    categories.append(
        {
            "code": "favorites",
            "name": favorites_name,  # This is what gets passed back as the category value
            "icon": "⭐",
        }
    )

    if household_id:
        raw_cats = _load_household_categories(household_id)
    else:
        # No household selected (rare/edge case) - fall back to the base
        # default category list rather than a per-household file.
        raw_cats = []
        base_file = Path(__file__).parent.parent / "data" / "categories.json"
        if base_file.exists():
            try:
                with open(base_file, "r", encoding="utf-8") as f:
                    raw_cats = json.load(f)
            except Exception as e:
                logger.error(f"Error loading base categories: {e}")

    # Translate to current language. Skip pack-name pseudo-categories
    # (imported: true) - recipes now keep their own real dish-type
    # category through import (see B4b), so a recipe can never have
    # one of these as its category anymore. Selecting one in the
    # dropdown would always show an empty list, which is confusing -
    # better to not offer it at all than show a dead-end option.
    for cat in raw_cats:
        if not isinstance(cat, dict) or cat.get("imported"):
            continue
        translated = dict(cat)
        translated["name"] = (
            cat.get(f"name_{lang}") or cat.get("name_en") or cat.get("code")
        )
        categories.append(translated)

    return jsonify(_sort_categories(categories))


@app.route("/api/export-shopping-list", methods=["POST"])
def api_export_shopping_list():
    """Export shopping list in various formats."""
    try:
        from shopping_integrations import (
            export_csv,
            export_json,
            export_todoist_format,
            export_plain_text,
            export_ics,
            export_microsoft_todo_format,
        )

        data = request.get_json() or {}
        fmt = data.get("format", "txt").lower()
        full_shopping_list = data.get("shopping_list", {})
        selected_items = data.get("items", [])

        if not selected_items:
            return jsonify({"success": False, "error": "No items to export"}), 400

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [
                i
                for i in items
                if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set
            ]
            if kept:
                filtered[category] = kept

        # Generate export
        if fmt == "csv":
            content = export_csv(filtered)
            mime_type = "text/csv"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.csv'
        elif fmt == "json":
            content = export_json(filtered)
            mime_type = "application/json"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        elif fmt == "todoist":
            content = export_todoist_format(filtered)
            mime_type = "text/plain"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'
        elif fmt == "ics":
            content = export_ics(filtered)
            mime_type = "text/calendar"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'
        elif fmt == "todo":
            content = export_microsoft_todo_format(filtered)
            mime_type = "application/json"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.json'
        else:  # txt
            content = export_plain_text(filtered)
            mime_type = "text/plain"
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.txt'

        return jsonify(
            {
                "success": True,
                "content": content,
                "filename": filename,
                "mime_type": mime_type,
            }
        )

    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/sync-shopping-list", methods=["POST"])
def api_sync_shopping_list():
    """Shopping list sync endpoint. Only Apple Reminders (plain ICS download,
    no account/token needed) is supported. Microsoft To Do, Todoist, and
    TickTick sync were removed 2026-07-05 - they required each user to obtain
    and paste their own API token/Azure credentials, which is real setup
    friction and support burden for a friends-and-family/public audience.
    See docs/BACKLOG_2026-07-01.md for the note to re-add if users actually ask."""
    try:
        data = request.get_json() or {}
        service = data.get("service", "reminders").lower()
        full_shopping_list = data.get("shopping_list", {})
        selected_items = data.get("items", [])

        if not selected_items:
            return jsonify({"success": False, "error": "No items to sync"}), 400

        logger.info(
            f"Sync request: service={service}, items={len(selected_items)}, categories={len(full_shopping_list)}"
        )

        # Filter to selected items only
        selected_set = {
            f"{item['ingredient']}-{item['quantity']}-{item['unit']}"
            for item in selected_items
        }
        filtered = {}
        for category, items in full_shopping_list.items():
            kept = [
                i
                for i in items
                if f"{i['ingredient']}-{i['quantity']}-{i['unit']}" in selected_set
            ]
            if kept:
                filtered[category] = kept

        logger.info(
            f"Filtered: {len(filtered)} categories, total items: {sum(len(v) for v in filtered.values())}"
        )

        if service == "reminders":
            # Return ICS file for Apple Reminders as direct download
            from shopping_integrations import export_ics
            from flask import send_file
            import io

            content = export_ics(filtered)
            filename = f'shopping-list-{datetime.now().strftime("%Y%m%d")}.ics'

            # Create file-like object
            ics_file = io.BytesIO(content.encode("utf-8"))

            return send_file(
                ics_file,
                mimetype="text/calendar",
                as_attachment=True,
                download_name=filename,
            )

        else:
            return (
                jsonify({"success": False, "error": f"Unknown service: {service}"}),
                400,
            )

    except Exception as e:
        logger.error(f"Sync error: {e}")
        return jsonify({"success": False, "error": str(e)}), 500


@app.route("/api/add-recipe", methods=["POST"])
def api_add_recipe():
    """Add a manually created recipe to recipes_db.json and backup the form"""
    if not acting_role_can_edit():
        return (
            jsonify({"status": "error", "message": "Viewers cannot add recipes"}),
            403,
        )
    try:
        import uuid
        from datetime import datetime

        data = request.get_json() or {}

        recipe = {
            "id": str(uuid.uuid4())[:8],
            "title": data.get("title", ""),
            "description": data.get("description", ""),
            "difficulty": _normalize_difficulty(data.get("difficulty", "Easy")),
            "time_minutes": data.get("time_minutes", 30),
            "category": data.get("category", "HomeMade"),
            "ingredients": data.get("ingredients", []),
            "instructions": data.get("instructions", []),
            "comment": data.get("comment", ""),
            "source": "manual",
        }

        if not recipe["title"] or not recipe["ingredients"]:
            return (
                jsonify(
                    {"status": "error", "message": "Title and ingredients are required"}
                ),
                400,
            )

        # Backup the form submission
        backup_dir = Path("data/sendt_forms")
        backup_dir.mkdir(parents=True, exist_ok=True)
        safe_title = (
            recipe["title"].replace(" ", "_").replace("/", "_").replace("\\", "_")
        )
        backup_file = backup_dir / f"form_{safe_title}.json"
        with open(backup_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        logger.info(f"Backed up form to: {backup_file}")

        # Save to recipes database
        recipes = load_recipes_db()
        recipes.append(recipe)
        save_recipes_db(recipes)

        log_activity(f"Added recipe '{recipe['title']}'")

        logger.info(f"Added recipe: {recipe['title']} (ID: {recipe['id']})")
        return jsonify(
            {
                "status": "success",
                "message": f"✅ {recipe['title']} saved!",
                "recipe_id": recipe["id"],
            }
        )

    except Exception as e:
        logger.error(f"Error adding recipe: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/delete-recipe", methods=["POST"])
def api_delete_recipe():
    """Delete a recipe from recipes_db.json by ID."""
    if not acting_role_can_edit():
        return (
            jsonify({"status": "error", "message": "Viewers cannot delete recipes"}),
            403,
        )
    try:
        data = request.get_json() or {}
        recipe_id = data.get("recipe_id")
        if not recipe_id:
            return jsonify({"status": "error", "message": "recipe_id is required"}), 400

        recipes = load_recipes_db()
        original_count = len(recipes)
        recipes = [r for r in recipes if r.get("id") != recipe_id]

        if len(recipes) == original_count:
            return (
                jsonify(
                    {"status": "error", "message": f"Recipe {recipe_id} not found"}
                ),
                404,
            )

        save_recipes_db(recipes)

        # B36: deleting a recipe that's still on the current weekly menu used
        # to leave the day pointing at a now-missing recipe_id - the
        # dashboard kept showing its stale title/time/difficulty, and
        # clicking into it 404'd ("Recipe not found"). Clear any day that
        # referenced this recipe so it shows as an empty slot instead of a
        # dangling reference.
        menu = load_menu()
        if menu and menu.get("dinners"):
            menu_changed = False
            for dinner in menu["dinners"]:
                if dinner.get("recipe_id") == recipe_id:
                    dinner["recipe_id"] = ""
                    dinner["title"] = ""
                    dinner["title_no"] = ""
                    dinner["title_en"] = ""
                    dinner["subtitle"] = ""
                    dinner["subtitle_no"] = ""
                    dinner["subtitle_en"] = ""
                    dinner["image_url"] = ""
                    dinner["protein"] = ""
                    dinner["difficulty"] = ""
                    # Keep this numeric (not '') - index.html's weekly-summary
                    # widget does `menu.dinners | sum(attribute='time_minutes')`,
                    # which throws if any entry is a string instead of a number.
                    dinner["time_minutes"] = 0
                    menu_changed = True
            if menu_changed:
                save_menu(menu)

        log_activity(f"Deleted recipe '{recipe_id}'")

        logger.info(f"Deleted recipe: {recipe_id}")
        return jsonify({"status": "success", "message": f"Recipe {recipe_id} deleted"})
    except Exception as e:
        logger.error(f"Delete recipe error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/edit-recipe", methods=["POST"])
def api_edit_recipe():
    """Edit an existing recipe in recipes_db.json by ID"""
    if not acting_role_can_edit():
        return (
            jsonify({"status": "error", "message": "Viewers cannot edit recipes"}),
            403,
        )
    try:
        data = request.get_json() or {}
        recipe_id = data.get("recipe_id")

        if not recipe_id:
            return jsonify({"status": "error", "message": "recipe_id is required"}), 400

        # Validate required fields
        title = data.get("title", "").strip()
        ingredients = data.get("ingredients", [])

        if not title or not ingredients:
            return (
                jsonify(
                    {"status": "error", "message": "Title and ingredients are required"}
                ),
                400,
            )

        recipes = load_recipes_db()
        recipe_found = False

        # Find and update the recipe
        for i, recipe in enumerate(recipes):
            if recipe.get("id") == recipe_id:
                # Update all provided fields
                recipes[i]["title"] = title
                recipes[i]["description"] = data.get("description", "")
                recipes[i]["difficulty"] = _normalize_difficulty(
                    data.get("difficulty", "Easy")
                )
                recipes[i]["time_minutes"] = data.get("time_minutes", 30)
                recipes[i]["category"] = data.get(
                    "category", recipe.get("category", "HomeMade")
                )
                recipes[i]["ingredients"] = ingredients
                recipes[i]["instructions"] = data.get("instructions", [])
                recipes[i]["comment"] = data.get("comment", "")
                recipe_found = True
                break

        if not recipe_found:
            return (
                jsonify(
                    {"status": "error", "message": f"Recipe {recipe_id} not found"}
                ),
                404,
            )

        # Save updated recipes
        save_recipes_db(recipes)

        log_activity(f"Edited recipe '{title}'")

        logger.info(f"Updated recipe: {title} (ID: {recipe_id})")
        return jsonify(
            {
                "status": "success",
                "message": f"✅ {title} updated!",
                "recipe_id": recipe_id,
            }
        )

    except Exception as e:
        logger.error(f"Error editing recipe: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/swap-recipe", methods=["POST"])
def api_swap_recipe():
    """Move a recipe to a chosen weekday in the current menu.

    If the recipe is already planned for a different day this week, the two
    days trade places entirely (a true swap - nothing is lost or
    duplicated). If the recipe isn't currently in this week's menu at all
    (e.g. picking a brand-new recipe from the catalog), it's simply inserted
    into the target day, replacing whatever was already planned there.

    Read + mutate + save all happen inside one locked_household() session
    (row-locked via SELECT ... FOR UPDATE) rather than a separate read
    session followed by a separate write session - the old pattern had a
    real read-modify-write race window between the two, where a concurrent
    request touching the same household could silently lose this swap on
    save."""
    if not acting_role_can_edit():
        return (
            jsonify({"status": "error", "message": "Viewers cannot change the menu"}),
            403,
        )
    try:
        data = request.get_json() or {}
        recipe_id = data.get("recipe_id")
        day = data.get("day")

        if not recipe_id or not day:
            return (
                jsonify({"status": "error", "message": "Recipe ID and day required"}),
                400,
            )

        household_id = current_household_id()

        with locked_household() as (db, household):
            if household:
                from core.household_paths import (
                    load_weekly_menu_from_db,
                    save_weekly_menu_to_db,
                    append_activity_to_db,
                )

                menu = load_weekly_menu_from_db(household)
            else:
                # No DB-backed household (file-storage fallback) - no
                # locking needed, there's no concurrent access to a single
                # Pi's local file.
                menu = load_menu()

            if not menu:
                return (
                    jsonify({"status": "error", "message": "No menu generated yet"}),
                    404,
                )

            dinners = menu.get("dinners", [])
            target = next((d for d in dinners if d["day"] == day), None)
            if not target:
                return (
                    jsonify(
                        {"status": "error", "message": f"Day {day} not found in menu"}
                    ),
                    404,
                )

            source = next(
                (
                    d
                    for d in dinners
                    if d.get("recipe_id") == recipe_id and d is not target
                ),
                None,
            )
            swapped_with_day = None

            if source:
                # True swap - exchange everything except the 'day' field itself.
                source_day, target_day = source["day"], target["day"]
                source_copy, target_copy = dict(source), dict(target)
                source.clear()
                source.update(target_copy)
                source["day"] = source_day
                target.clear()
                target.update(source_copy)
                target["day"] = target_day
                swapped_with_day = source_day
                # Resolve to a plain string for the activity log - target['title']
                # can still be the raw bilingual {'en':..., 'no':...} dict after
                # the swap above, which previously got embedded into the log
                # message as Python's dict repr (e.g. "{'no': '...', 'en': '...'}")
                # instead of the actual recipe name.
                _swap_title = target.get("title")
                recipe_title = (
                    target.get("title_en")
                    or target.get("title_no")
                    or (_swap_title if isinstance(_swap_title, str) else "")
                    or "Recipe"
                )
            else:
                recipe = find_recipe(recipe_id)
                if not recipe:
                    return (
                        jsonify({"status": "error", "message": "Recipe not found"}),
                        404,
                    )

                # Mirror MenuGenerator.generate_menu()'s field derivation exactly -
                # this used to only set recipe_id/title/time_minutes/difficulty,
                # leaving title_no/title_en/subtitle_no/subtitle_en/protein/
                # image_url stale from whatever recipe used to be on this day.
                # The dashboard prefers title_en/title_no over the raw 'title'
                # field when resolving what to display, so it kept silently
                # showing the OLD recipe's name even though the swap "worked".
                from core.menu_generator import MenuGenerator, PROTEIN_IMAGES

                title = recipe.get("title")
                if isinstance(title, dict):
                    title_en = title.get("en", "")
                    title_no = title.get("no", "")
                else:
                    title_en = recipe.get("title_en", title or "")
                    title_no = recipe.get("title_no", title or "")

                subtitle = recipe.get("subtitle")
                if isinstance(subtitle, dict):
                    subtitle_en = subtitle.get("en", "")
                    subtitle_no = subtitle.get("no", "")
                else:
                    subtitle_en = recipe.get("subtitle_en", subtitle or "")
                    subtitle_no = recipe.get("subtitle_no", subtitle or "")

                protein_type = MenuGenerator().get_protein_type(
                    title_en or title_no or "",
                    subtitle_en or subtitle_no or "",
                    recipe.get("category", ""),
                )

                target["recipe_id"] = recipe["id"]
                target["title"] = recipe["title"]
                target["title_no"] = title_no
                target["title_en"] = title_en
                target["time_minutes"] = (
                    recipe.get("time_minutes") or recipe.get("cookTimeMinutes") or 0
                )
                target["difficulty"] = recipe.get("difficulty", "")
                target["protein"] = protein_type
                target["subtitle_no"] = subtitle_no
                target["subtitle_en"] = subtitle_en
                target["image_url"] = PROTEIN_IMAGES.get(
                    protein_type, PROTEIN_IMAGES.get("vegetarian")
                )
                recipe_title = title_en or title_no or "Recipe"

            activity_msg = (
                f"Swapped {day} and {swapped_with_day}"
                if swapped_with_day
                else f"Swapped {day}'s dinner to '{recipe_title}'"
            )

            # Save the updated menu. Menus live in the household's DB row, not
            # the flat file, once a household exists - writing only to the file
            # here silently discarded the swap (menu kept loading the old DB
            # copy on every subsequent page view).
            if household:
                save_weekly_menu_to_db(household, menu)
                append_activity_to_db(household, current_actor_name(), activity_msg)
            else:
                from core.household_paths import menu_file, append_activity

                with open(menu_file(household_id), "w", encoding="utf-8") as f:
                    json.dump(menu, f, ensure_ascii=False, indent=2)
                append_activity(household_id, current_actor_name(), activity_msg)

        logger.info(activity_msg)
        return jsonify(
            {
                "status": "success",
                "message": activity_msg,
                "swapped_with_day": swapped_with_day,
            }
        )

    except Exception as e:
        logger.error(f"Error swapping recipe: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/recipes/search")
def api_recipes_search():
    """Search this household's recipe library by title, for the "search and
    pick a specific recipe for this day" dashboard control (B/feature request
    from user testing, 2026-07). Returns a small flat list (id/title/category/
    time) rather than full recipe records - this feeds a search dropdown, not
    a detail view, so keep the payload light."""
    query = (request.args.get("q") or "").strip().lower()
    if len(query) < 2:
        return jsonify({"status": "success", "recipes": []})

    all_recipes = load_recipes_db()
    sample_path = SEED_DIR / "sample_recipes.json"
    if sample_path.exists():
        try:
            with open(sample_path, "r", encoding="utf-8") as f:
                all_recipes = all_recipes + json.load(f)
        except Exception:
            pass

    seen_ids = set()
    results = []
    for recipe in all_recipes:
        recipe_id = recipe.get("id")
        if not recipe_id or recipe_id in seen_ids:
            continue
        title = recipe.get("title")
        if isinstance(title, dict):
            title_en = title.get("en", "")
            title_no = title.get("no", "")
        else:
            title_en = recipe.get("title_en", title or "")
            title_no = recipe.get("title_no", title or "")
        haystack = f"{title_en} {title_no}".strip().lower()
        if query not in haystack:
            continue
        seen_ids.add(recipe_id)
        results.append(
            {
                "id": recipe_id,
                "title_en": title_en,
                "title_no": title_no,
                "category": recipe.get("category", ""),
                "time_minutes": recipe.get("time_minutes")
                or recipe.get("cookTimeMinutes")
                or 0,
            }
        )
        if len(results) >= 25:
            break

    return jsonify({"status": "success", "recipes": results})


@app.route("/api/reroll-recipe", methods=["POST"])
def api_reroll_recipe():
    """Replace a single day's recipe with a different random one, without
    touching the rest of the week (B/feature request from user testing,
    2026-07: "just wanna reroll that 1 menu" instead of regenerating all 6).

    Stays within the current recipe's own category where possible (so a
    reroll on a "Fish & Seafood" day doesn't suddenly hand back a dessert),
    and never picks a recipe already used elsewhere in this week's menu -
    same no-duplicates guarantee MenuGenerator gives a fresh menu."""
    if not acting_role_can_edit():
        return (
            jsonify({"status": "error", "message": "Viewers cannot change the menu"}),
            403,
        )
    try:
        import random

        data = request.get_json() or {}
        day = data.get("day")
        if not day:
            return jsonify({"status": "error", "message": "Day required"}), 400

        household_id = current_household_id()

        with locked_household() as (db, household):
            if household:
                from core.household_paths import (
                    load_weekly_menu_from_db,
                    save_weekly_menu_to_db,
                    append_activity_to_db,
                )

                menu = load_weekly_menu_from_db(household)
            else:
                menu = load_menu()

            if not menu:
                return (
                    jsonify({"status": "error", "message": "No menu generated yet"}),
                    404,
                )

            dinners = menu.get("dinners", [])
            target = next((d for d in dinners if d["day"] == day), None)
            if not target:
                return (
                    jsonify(
                        {"status": "error", "message": f"Day {day} not found in menu"}
                    ),
                    404,
                )

            used_recipe_ids = {d.get("recipe_id") for d in dinners if d.get("recipe_id")}

            current_recipe = find_recipe(target.get("recipe_id"))
            current_category = (
                current_recipe.get("category", "") if current_recipe else ""
            )

            all_recipes = load_recipes_db()
            sample_path = SEED_DIR / "sample_recipes.json"
            if sample_path.exists():
                try:
                    with open(sample_path, "r", encoding="utf-8") as f:
                        all_recipes = all_recipes + json.load(f)
                except Exception:
                    pass

            # Prefer same-category candidates; if none are left (small/edge-
            # case libraries), fall back to any unused recipe at all rather
            # than failing outright.
            candidates = [
                r
                for r in all_recipes
                if r.get("id") not in used_recipe_ids
                and (not current_category or r.get("category", "") == current_category)
            ]
            if not candidates:
                candidates = [
                    r for r in all_recipes if r.get("id") not in used_recipe_ids
                ]
            if not candidates:
                return (
                    jsonify(
                        {
                            "status": "error",
                            "message": "No other recipes available to reroll to",
                        }
                    ),
                    404,
                )

            new_recipe = random.choice(candidates)

            from core.menu_generator import MenuGenerator, PROTEIN_IMAGES

            title = new_recipe.get("title")
            if isinstance(title, dict):
                title_en = title.get("en", "")
                title_no = title.get("no", "")
            else:
                title_en = new_recipe.get("title_en", title or "")
                title_no = new_recipe.get("title_no", title or "")

            subtitle = new_recipe.get("subtitle")
            if isinstance(subtitle, dict):
                subtitle_en = subtitle.get("en", "")
                subtitle_no = subtitle.get("no", "")
            else:
                subtitle_en = new_recipe.get("subtitle_en", subtitle or "")
                subtitle_no = new_recipe.get("subtitle_no", subtitle or "")

            protein_type = MenuGenerator().get_protein_type(
                title_en or title_no or "",
                subtitle_en or subtitle_no or "",
                new_recipe.get("category", ""),
            )

            target["recipe_id"] = new_recipe["id"]
            target["title"] = new_recipe.get("title")
            target["title_no"] = title_no
            target["title_en"] = title_en
            target["time_minutes"] = (
                new_recipe.get("time_minutes") or new_recipe.get("cookTimeMinutes") or 0
            )
            target["difficulty"] = new_recipe.get("difficulty", "")
            target["protein"] = protein_type
            target["subtitle_no"] = subtitle_no
            target["subtitle_en"] = subtitle_en
            target["image_url"] = PROTEIN_IMAGES.get(
                protein_type, PROTEIN_IMAGES.get("vegetarian")
            )

            recipe_title = title_en or title_no or "Recipe"
            activity_msg = f"Rerolled {day}'s dinner to '{recipe_title}'"

            if household:
                save_weekly_menu_to_db(household, menu)
                append_activity_to_db(household, current_actor_name(), activity_msg)
            else:
                from core.household_paths import menu_file, append_activity

                with open(menu_file(household_id), "w", encoding="utf-8") as f:
                    json.dump(menu, f, ensure_ascii=False, indent=2)
                append_activity(household_id, current_actor_name(), activity_msg)

        logger.info(activity_msg)
        return jsonify(
            {
                "status": "success",
                "message": activity_msg,
                "recipe_id": new_recipe["id"],
                "title_en": title_en,
                "title_no": title_no,
            }
        )

    except Exception as e:
        logger.error(f"Error rerolling recipe: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/health")
def health_check():
    return jsonify(
        {
            "status": "healthy",
            "timestamp": datetime.now().isoformat(),
            "https": CERT_FILE.exists(),
        }
    )


# ── Theme gallery ─────────────────────────────────────────────────────────────


@app.route("/themes")
def theme_gallery():
    import os as _os

    preview_dir = Path(__file__).parent.parent / "frontend/static/theme-previews"
    files = sorted([f for f in _os.listdir(preview_dir) if f.endswith(".html")])
    themes = [
        {
            "file": f,
            "name": f.replace("theme-", "")
            .replace(".html", "")
            .replace("-", " ")
            .title(),
        }
        for f in files
    ]
    return render_template("theme_gallery.html", themes=themes)


@app.route("/themes/<filename>")
def theme_preview(filename):
    from flask import send_from_directory

    preview_dir = Path(__file__).parent.parent / "frontend/static/theme-previews"
    return send_from_directory(preview_dir, filename)


# ── Recipe Packs API ──────────────────────────────────────────────────────────


def get_available_recipe_packs():
    """Load all available recipe packs from data/recipe-packs/"""
    packs_dir = SEED_DIR / "recipe-packs"
    packs = []

    if not packs_dir.exists():
        logger.warning(f"Recipe packs directory not found: {packs_dir}")
        return packs

    for pack_file in sorted(packs_dir.glob("pack_*.json")):
        try:
            with open(pack_file, "r", encoding="utf-8") as f:
                pack = json.load(f)
                packs.append(pack)
        except Exception as e:
            logger.error(f"Error loading pack {pack_file}: {e}")

    return packs


@app.route("/api/recipe-packs/list")
def api_recipe_packs_list():
    """Get list of available recipe packs, flagging which ones this
    household has already imported (by source_pack on its own recipes)."""
    packs = get_available_recipe_packs()

    imported_pack_ids = set()
    household_id = current_household_id()
    if household_id:
        for r in load_recipes_db():
            if r.get("source_pack"):
                imported_pack_ids.add(r["source_pack"])

    simplified = []
    for pack in packs:
        simplified.append(
            {
                "packId": pack["packId"],
                "packName": pack["packName"],
                "packDescription": pack["packDescription"],
                "packIcon": pack.get("packImage", "📦"),
                "packColor": pack.get("packColor", "#999999"),
                "recipeCount": pack["recipeCount"],
                "estimatedCookTime": pack["estimatedCookTime"],
                "difficulty": pack["difficulty"],
                "alreadyImported": pack["packId"] in imported_pack_ids,
            }
        )
    return jsonify(simplified)


@app.route("/api/recipe-packs/import", methods=["POST"])
def api_recipe_packs_import():
    """Import selected recipe packs into user's recipe database"""
    if not acting_role_can_edit():
        return (
            jsonify(
                {"success": False, "message": "Viewers cannot import recipe packs"}
            ),
            403,
        )
    try:
        data = request.get_json()
        pack_ids = data.get("packIds", [])

        if not pack_ids:
            return jsonify({"success": False, "message": "No packs selected"}), 400

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
        pack_metadata = (
            {}
        )  # source_pack code -> display info, for categories.json bookkeeping
        for pack in all_packs:
            if pack["packId"] in pack_ids:
                pack_name_field = pack.get("packName", {})
                if isinstance(pack_name_field, dict):
                    pack_display_name = (
                        pack_name_field.get("en")
                        or pack_name_field.get("no")
                        or "Imported Pack"
                    )
                else:
                    pack_display_name = str(pack_name_field)

                pack_metadata[pack["packId"]] = {
                    "display_name": pack_display_name,
                    "icon": pack.get("packImage", "📦"),
                    "color": pack.get("packColor", "#999999"),
                }

                for recipe in pack["recipes"]:
                    # Normalize only non-bilingual technical fields, keep titles/descriptions as bilingual dicts
                    r = dict(recipe)
                    # Track pack origin separately - do NOT touch r['category']
                    r["source_pack"] = pack["packId"]
                    # Store pack icon for display
                    r["packIcon"] = pack.get("packImage", "📦")
                    # Normalize difficulty if it's a bilingual dict
                    if isinstance(r.get("difficulty"), dict):
                        r["difficulty"] = (
                            r["difficulty"].get("en")
                            or r["difficulty"].get("no")
                            or "Easy"
                        )
                    # Ensure time_minutes is set (may be cookTimeMinutes in pack)
                    if "time_minutes" not in r or not r.get("time_minutes"):
                        r["time_minutes"] = r.get("cookTimeMinutes", 30)
                    # Normalize ingredient units to Norwegian canonical form
                    # (tbsp -> ss, bunch -> bunt, etc; see B15/B20) at import
                    # time, not just via the one-off admin backfill route -
                    # otherwise packs imported after that backfill keep raw
                    # English units forever (B45).
                    from core.ingredient_deduplicator import normalize_no_unit

                    for ing_field in (
                        "ingredients",
                        "ingredients_included",
                        "ingredients_not_included",
                    ):
                        for ing in r.get(ing_field, []) or []:
                            if isinstance(ing, dict) and "unit" in ing:
                                ing["unit"] = normalize_no_unit(ing["unit"])
                    recipes_to_import.append(r)

        # Load existing recipes database.
        # Upsert: overwrite any recipe whose ID already exists (so re-importing
        # a pack after a category restructure gets the fresh categories, not the
        # stale ones from the previous import).
        existing_recipes = load_recipes_db()
        import_ids = {r["id"] for r in recipes_to_import}
        kept = [r for r in existing_recipes if r["id"] not in import_ids]
        imported_count = len(recipes_to_import)
        existing_recipes = kept + recipes_to_import

        # Save updated database
        save_recipes_db(existing_recipes)

        from core.household_paths import save_imported_pack_metadata

        log_activity(f"Imported {imported_count} recipes from {len(pack_ids)} pack(s)")

        # No categories.json bookkeeping needed here anymore - imported recipes
        # keep their own real dish-type category (Chicken, Salads, etc.), which
        # already exists in the household's category list. There's nothing
        # new to register; a recipe is just findable under its existing
        # category right away. Pack display metadata (for "Manage Recipe
        # Packs") is tracked separately instead.
        for pack_id, meta in pack_metadata.items():
            save_imported_pack_metadata(
                current_household_id(),
                pack_id,
                meta["display_name"],
                meta["icon"],
                meta["color"],
            )

        logger.info(f"Imported {imported_count} recipes from {len(pack_ids)} packs")
        return jsonify(
            {
                "success": True,
                "imported_count": imported_count,
                "message": f"Imported {imported_count} recipes",
            }
        )

    except Exception as e:
        logger.error(f"Recipe pack import error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/recipe-packs/imported", methods=["GET"])
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
            pack_id = recipe.get("source_pack", "")
            if pack_id:
                recipe_counts[pack_id] = recipe_counts.get(pack_id, 0) + 1

        packs = []
        for pack_id, count in recipe_counts.items():
            meta = pack_meta.get(pack_id, {})
            packs.append(
                {
                    "pack_id": pack_id,
                    "category_name": meta.get("display_name", pack_id),
                    "recipe_count": count,
                    "icon": meta.get("icon", "📦"),
                }
            )

        return jsonify({"success": True, "packs": packs})
    except Exception as e:
        logger.error(f"Error getting imported packs: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/recipe-packs/remove", methods=["POST"])
def api_remove_imported_pack():
    """Remove an imported pack (all recipes with that source_pack). Does NOT
    touch categories.json - a recipe's dish-type category is its own, not
    tied to which pack it came from, so removing a pack never needs to
    remove a category."""
    if not acting_role_can_edit():
        return (
            jsonify(
                {"success": False, "message": "Viewers cannot remove recipe packs"}
            ),
            403,
        )
    try:
        data = request.get_json()
        pack_id = data.get("pack_id", "")

        if not pack_id:
            return jsonify({"success": False, "message": "No pack specified"}), 400

        recipes = load_recipes_db()
        removed_count = 0

        if recipes:
            filtered_recipes = [
                r for r in recipes if r.get("source_pack", "") != pack_id
            ]
            removed_count = len(recipes) - len(filtered_recipes)

            save_recipes_db(filtered_recipes)

            from core.household_paths import remove_imported_pack_metadata

            log_activity(f"Removed pack '{pack_id}' ({removed_count} recipes)")
            remove_imported_pack_metadata(current_household_id(), pack_id)

            logger.info(f"Removed {removed_count} recipes from pack '{pack_id}'")

        return jsonify(
            {
                "success": True,
                "removed_count": removed_count,
                "message": f"Removed {removed_count} recipes",
            }
        )

    except Exception as e:
        logger.error(f"Recipe pack removal error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/recipe-packs/manage")
def manage_recipe_packs():
    """Page to manage imported recipe packs"""
    lang = _get_lang()
    recipes = [_normalize_recipe(r, lang) for r in load_recipes_db()]
    return render_template("recipe-packs-manage.html", recipes=recipes)


# ── Hidden feature foundation: dessert/drinks browsing (F2), side stash (F8) ─
# Gated behind FEATURE_FLAGS (see the block right after IS_PRODUCTION, and
# docs/FEATURE_FLAGS.md). Every route below 404s outright when its flag is
# off, so the public build behaves exactly as if these routes don't exist -
# this is deliberate over hiding a nav link, since a stray direct URL guess
# shouldn't reveal in-progress functionality either. Data loading lives in
# core/stash_library.py, kept isolated from the recipe-pack/menu code so
# this can be reshaped later without touching anything public-facing.


@app.route("/desserts-drinks")
def desserts_drinks_page():
    """Hidden dev-only browser for the dessert + drinks stash (F2 foundation)."""
    if not feature_enabled("desserts_drinks"):
        abort(404)
    from core.stash_library import load_dessert_stash, load_drinks_stash

    lang = _get_lang()
    desserts = [_normalize_recipe(r, lang) for r in load_dessert_stash()]
    drinks = [_normalize_recipe(r, lang) for r in load_drinks_stash()]
    return render_template("desserts-drinks.html", desserts=desserts, drinks=drinks)


@app.route("/api/desserts-drinks/list")
def api_desserts_drinks_list():
    if not feature_enabled("desserts_drinks"):
        abort(404)
    from core.stash_library import load_dessert_stash, load_drinks_stash

    lang = _get_lang()
    return jsonify(
        {
            "desserts": [_normalize_recipe(r, lang) for r in load_dessert_stash()],
            "drinks": [_normalize_recipe(r, lang) for r in load_drinks_stash()],
        }
    )


@app.route("/sides-stash")
def sides_stash_page():
    """Hidden dev-only browser for the side-dish stash (F8 foundation)."""
    if not feature_enabled("side_stash"):
        abort(404)
    from core.stash_library import load_sides_stash

    lang = _get_lang()
    sides = [_normalize_recipe(r, lang) for r in load_sides_stash()]
    return render_template("sides-stash.html", sides=sides)


@app.route("/api/sides-stash/list")
def api_sides_stash_list():
    if not feature_enabled("side_stash"):
        abort(404)
    from core.stash_library import load_sides_stash

    lang = _get_lang()
    return jsonify({"sides": [_normalize_recipe(r, lang) for r in load_sides_stash()]})


# ── Personal Recipe Arsenal API ───────────────────────────────────────────────


@app.route("/api/recipes/export")
def api_recipes_export():
    """Export all user recipes as JSON"""
    try:
        recipes = load_recipes_db()
        return jsonify({"success": True, "recipes": recipes, "count": len(recipes)})
    except Exception as e:
        logger.error(f"Export error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


@app.route("/api/recipes/import", methods=["POST"])
def api_recipes_import():
    """Import recipes from user-provided JSON file"""
    if not acting_role_can_edit():
        return (
            jsonify({"success": False, "message": "Viewers cannot import recipes"}),
            403,
        )
    try:
        data = request.get_json()
        recipes_to_import = data.get("recipes", [])

        if not recipes_to_import:
            return jsonify({"success": False, "message": "No recipes provided"}), 400

        # Validate recipe structure
        for recipe in recipes_to_import:
            if not recipe.get("id") or not recipe.get("title"):
                return (
                    jsonify({"success": False, "message": "Invalid recipe structure"}),
                    400,
                )

        # Load existing recipes
        existing_recipes = load_recipes_db()
        existing_ids = {r["id"] for r in existing_recipes}

        # Import non-duplicate recipes
        imported_count = 0
        for recipe in recipes_to_import:
            if recipe["id"] not in existing_ids:
                existing_recipes.append(recipe)
                imported_count += 1

        # Save updated database
        save_recipes_db(existing_recipes)

        log_activity(f"Imported {imported_count} recipes from file")

        logger.info(f"Imported {imported_count} recipes from user file")
        return jsonify(
            {
                "success": True,
                "imported_count": imported_count,
                "message": f"Imported {imported_count} recipes",
            }
        )

    except Exception as e:
        logger.error(f"Recipe import error: {e}")
        return jsonify({"success": False, "message": str(e)}), 500


# ── Error handlers ────────────────────────────────────────────────────────────


@app.errorhandler(404)
def not_found(error):
    return render_template("error.html", message="Page not found"), 404


@app.errorhandler(500)
def server_error(error):
    logger.error(f"Server error: {error}")
    return render_template("error.html", message="Server error"), 500


# ── Entry point ───────────────────────────────────────────────────────────────

if __name__ == "__main__":
    logger.info("=== STARTING FLASK APP WITH HTTPS ===")
    logger.info(f"Running from: {__file__}")

    # HTTP only — local home network use, no "Not Secure" warning.
    # debug=True is local-dev-only: production runs via gunicorn (see
    # Dockerfile/requirements.txt), which never executes this block.
    app.run(host="0.0.0.0", port=5000, debug=True)  # nosec B201
