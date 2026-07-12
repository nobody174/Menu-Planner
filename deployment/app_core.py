"""
Shared application core (B57, audit 2026-07-07): the Flask app factory,
security/session setup, and every helper function used across route groups
that used to all live inline in flask_app.py before its route handlers.

This module owns anything that must exist before routes can be registered
(the app/csrf/limiter objects themselves, i18n, session/household
resolution, menu/recipe/pantry load-save helpers, email senders, avatar
helpers) or that's genuinely cross-cutting (used by more than one route
blueprint). Route handler functions themselves live in
deployment/routes/*.py, each registered against the `app` object this
module's create_app() returns.

This is a straight behavior-preserving move, not a rewrite - every function
here is unchanged from its original flask_app.py version except for being
wrapped in create_app() where it depends on `app` directly (decorators,
config, jinja globals). See docs/BACKLOG.md's B57 entry for why
this was necessary: flask_app.py had grown to ~4,700 lines / ~80 routes, all
sharing one module scope with no boundaries.
"""

import json
import os
import logging
import re as _re
import secrets
import sys
import contextlib
from pathlib import Path
from datetime import timedelta

import requests
from dotenv import load_dotenv
from flask import Flask, request, session, url_for, g

# ── i18n helpers ─────────────────────────────────────────────────────────────

_I18N_CACHE = {"mtime": None, "data": {}}


def _load_i18n():
    """Load i18n translations, re-reading the file only when it has actually
    changed on disk since the last load.

    M6 (audit 2026-07-07): this used to unconditionally re-read and
    re-parse the full ~29KB i18n.json on every single request (the comment
    said "reload on every request to catch updates") - real in production,
    since editing this file doesn't require a restart, but the vast
    majority of requests happen between edits, where re-reading identical
    content from disk every time was pure waste. Checking the file's mtime
    (a single, cheap stat() call) keeps that same "an edit takes effect
    immediately, no restart needed" behavior while skipping the actual
    read+json.parse whenever the file hasn't changed since last time -
    which in production is effectively always. A process-global cache (not
    per-request) is correct here specifically because it's keyed on the
    file's own mtime, not on anything request-specific.
    """
    i18n_path = Path(__file__).parent.parent / "frontend" / "static" / "i18n.json"
    try:
        current_mtime = i18n_path.stat().st_mtime
    except OSError as e:
        logger.warning(f"Could not stat i18n.json: {e}")
        return _I18N_CACHE["data"]

    if current_mtime == _I18N_CACHE["mtime"]:
        return _I18N_CACHE["data"]

    try:
        with open(i18n_path, "r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception as e:
        logger.warning(f"Could not load i18n.json: {e}")
        return _I18N_CACHE["data"]

    _I18N_CACHE["mtime"] = current_mtime
    _I18N_CACHE["data"] = data
    return data


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


# ── Paths / constants shared across the whole app ────────────────────────────

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env from project root
load_dotenv(Path(__file__).parent.parent / ".env")

# Initialize database (import models first so Base.metadata knows about all tables)
import database.models  # noqa: F401,E402
from database.database import db  # noqa: E402

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
# is read from here instead of DATA_DIR.
#
# M3 (2026-07-09): this used to point at /app/data-seed, a directory only
# the now-deleted Dockerfile ever created (baked in at image build time so
# a Railway persistent volume's no-clobber behavior on DATA_DIR wouldn't
# shadow static content fixes). Render - the platform actually in
# production - never ran that Dockerfile at all (see Procfile / the
# Build/Start commands in docs/DEVELOPER_GUIDE.md), so /app/data-seed never
# existed there either; this always silently fell through to the DATA_DIR
# fallback below in the real deployment, every single time. Kept the
# fallback path itself (still correct, still what actually runs), removed
# only the dead Docker-creates-this-directory branch and comment.
SEED_DIR = DATA_DIR
PROFILE_COOKIE_MAX_AGE = 60 * 60 * 24 * 365  # 1 year

# Certificate paths (relative to the deployment dir where the service runs from)
CERT_FILE = Path(__file__).parent / "cert.pem"
KEY_FILE = Path(__file__).parent / "key.pem"

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


def _avatar_display(label, avatar_type=None, avatar_value=None):
    """Either the member's chosen emoji, or an upper-case initial, for circle avatars."""
    if avatar_type == "emoji" and avatar_value:
        return avatar_value
    return label[0].upper() if label else "?"


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
    # LO6 (2026-07-12): only a sha256 hash of the token is persisted to the DB
    # now, so the raw token must come from the transient raw_confirmation_token
    # attribute the caller (create_user/regenerate_confirmation_token) set on
    # this same in-memory user object - NOT from user.email_confirmation_token,
    # which is the hash and can't be turned back into a working link.
    confirm_url = url_for(
        "auth.confirm_email_route",
        token=getattr(user, "raw_confirmation_token", None),
        _external=True,
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
    # LO6 (2026-07-12): same as _send_confirmation_email above - only the hash
    # is persisted, so use the transient raw_reset_token attribute set by
    # request_password_reset().
    reset_url = url_for(
        "auth.reset_password_page",
        token=getattr(user, "raw_reset_token", None),
        _external=True,
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


def current_household_id():
    """Resolve the active household id for this request, picking the user's
    first household if none is set in session yet.

    M6 (audit 2026-07-07): this ran a full DB query (get_user_households)
    on every single call, and a single request can call it many times over
    (the context processor, the route handler itself, several helpers each
    routes call) - the same membership lookup repeated identically several
    times per request for no reason. Cached on flask.g after computing it
    once, including whatever session mutation the first call's cross-account
    guard below performs - later calls in the same request just reuse that
    result instead of re-querying and re-deriving it.

    The cache key includes the session's user_id, not just a bare "have we
    cached anything yet" flag - flask.g is documented as request-scoped, but
    that only holds when a request context is pushed fresh (which is how
    every real HTTP request under gunicorn actually works). Flask's own
    test_request_context() reuses an already-active app context's `g` if one
    is on the stack rather than starting a new one - confirmed directly: two
    sequential test_request_context() blocks nested inside one outer
    app_context() (exactly what tests/conftest.py's test_app fixture does)
    shared the same g, so an initial cache-blind implementation returned the
    FIRST request's household id for a SECOND request logged in as an
    entirely different user. Keying on user_id as well means a mismatched
    session (different user, or no user) always recomputes rather than
    trusting a cache that was never actually this request's own.
    """
    user_id = session.get("user_id")
    cached = getattr(g, "_cached_household_id", None)
    if cached is not None and cached[0] == user_id:
        return cached[1]

    household_id = _resolve_current_household_id()
    g._cached_household_id = (user_id, household_id)
    return household_id


def _resolve_current_household_id():
    """The actual resolution logic for current_household_id() above, kept
    separate so the caching wrapper doesn't have to duplicate it."""
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

    db_session = SessionLocal()
    try:
        return db_session.query(Household).filter(Household.id == household_id).first()
    finally:
        db_session.close()


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

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household)
            .filter(Household.id == household_id)
            .with_for_update()
            .first()
        )
        yield db_session, household
        db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def current_actor_name():
    """Name to attribute edits/actions to: active profile if one is picked,
    otherwise the logged-in account's email."""
    return session.get("active_profile_name") or session.get("user_email") or "Unknown"


def log_activity(action_msg):
    """Record one activity-log entry for the current household.

    This is the single correct way to log an action. Households are DB-backed
    once created, so this always opens its own fresh session, re-queries the
    household by id, appends the entry, and commits - mirroring the pattern
    already proven correct in the swap-recipe route. Using a `household`
    object obtained elsewhere (e.g. from `current_household()`) doesn't work:
    that helper closes its session before returning, so the object is
    detached and mutating it (as `append_activity_to_db` does) never
    persists.

    B61 (2026-07-09): the legacy file-based log fallback has been removed -
    confirmed via Neon that exactly 3 households exist and all are real DB
    rows, and this Render service has no persistent Disk attached, so a
    file-only household could not have survived any deploy to exist today.
    """
    household_id = current_household_id()
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import append_activity_to_db

    db_session = SessionLocal()
    try:
        db_household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if db_household:
            append_activity_to_db(db_household, current_actor_name(), action_msg)
            db_session.commit()
    finally:
        db_session.close()


def _load_pantry_db():
    """Load pantry from database, seeding fresh households with the static
    staples list directly on first read.

    M4 (audit 2026-07-07): this used to catch every exception, print() it,
    and return [] - indistinguishable from a household that genuinely has an
    empty pantry. A transient DB error (e.g. a dropped connection) silently
    looked like "you have nothing in your pantry," which then gets written
    right back out by a subsequent save, permanently erasing real pantry
    data the household never asked to clear. Letting the exception propagate
    means the caller's own error handling (or, for the routes that had none,
    the JSON error handler added for M5) reports a real failure instead.

    B61 (2026-07-09): the seed step used to call core.household_paths'
    load_pantry(), which round-trips through a per-household pantry.json +
    .pantry_seeded marker file purely to hold the exact same static staples
    content every fresh household gets - no household-specific customization
    was ever actually being read back at this point (a DB household.pantry
    column is only None once, right after creation, before its first read -
    there's no legacy "empty but already-marked" state a JSONB column can be
    in the way an old flat file could). Seeding directly from the static
    seed data means a brand-new household's very first pantry read no longer
    touches disk at all.
    """
    household_id = current_household_id()
    if not household_id:
        return []

    from database.database import SessionLocal
    from database.models import Household

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            return []

        # If pantry already in database, return it
        if household.pantry is not None:
            return household.pantry if isinstance(household.pantry, list) else []

        # First time: seed with the static staples list directly - no file I/O.
        from core.household_paths import default_pantry_staples

        household.pantry = default_pantry_staples()
        db_session.commit()
        return household.pantry
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _save_pantry_db(items):
    """Save pantry to database.

    M4 (audit 2026-07-07): this used to catch a DB commit failure, print()
    it, and then silently fall through to writing a file-based fallback
    path instead - which the DB-first read path (_load_pantry_db above)
    never looks at again once a household has a non-None `pantry` column.
    The route reported success ("Added to pantry") while the actual save
    was lost. Now: a DB-backed household's failure propagates as a real
    error, not silently swapped for a write that goes nowhere useful.

    B61 (2026-07-09): the file-fallback branch (for a household_id with no
    matching DB row) has been removed - confirmed via Neon that exactly 3
    households exist and all are real DB rows, and this Render service has
    no persistent Disk attached, so a file-only household could not have
    survived any deploy to exist today. If household_id is set but somehow
    doesn't resolve to a household, this now simply does nothing, same as
    the "no household_id at all" case already did.
    """
    household_id = current_household_id()
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if household:
            household.pantry = sorted(set(items))
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


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


def load_menu():
    """Load weekly menu from database JSONB column.

    B61 (2026-07-09): the file-fallback branch (for a household with no
    matching DB row) has been removed - confirmed via Neon that exactly 3
    households exist and all are real DB rows, and this Render service has
    no persistent Disk attached, so a file-only household could not have
    survived any deploy to exist today.
    """
    household = current_household()
    if not household:
        return None

    from core.household_paths import load_weekly_menu_from_db

    return load_weekly_menu_from_db(household)


def save_menu(menu):
    """Save the weekly menu. Opens its own fresh session and re-queries the
    household by id rather than reusing a possibly-detached object, so the
    write actually commits - mirrors the save pattern already proven correct
    in /api/swap-recipe.

    B61 (2026-07-09): the file-fallback branch has been removed, same
    reasoning as load_menu() above.
    """
    household = current_household()
    if not household:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import save_weekly_menu_to_db

    db_session = SessionLocal()
    try:
        db_household = (
            db_session.query(Household).filter(Household.id == household.id).first()
        )
        if db_household:
            save_weekly_menu_to_db(db_household, menu)
            db_session.commit()
    finally:
        db_session.close()


def load_recipes_db():
    """Load recipes from database JSONB column.

    B61 (2026-07-09): the file-fallback branch has been removed - confirmed
    via Neon that exactly 3 households exist and all are real DB rows, and
    this Render service has no persistent Disk attached, so a file-only
    household could not have survived any deploy to exist today.
    """
    household = current_household()
    if not household:
        return []

    from core.household_paths import load_recipes_db_from_db

    return load_recipes_db_from_db(household)


def save_recipes_db(recipes):
    """Save recipes to database JSONB column.

    M4 (audit 2026-07-07): the DB-backed branch used to catch a commit
    failure, print() it, and return normally - every caller (recipe add/
    edit/delete, pack import, unit normalization) reported success on a
    lost write, the same "200 success, nothing saved" class of bug as
    B53/B63. Now propagates so the caller's own error handling (or the
    JSON error handler added for M5, for the routes that had none) reports
    the real failure instead.

    B61 (2026-07-09): the file-fallback branch has been removed, same
    reasoning as load_recipes_db() above.
    """
    household = current_household()
    if not household:
        return

    from database.database import SessionLocal
    from database.models import Household as HouseholdModel

    db_session = SessionLocal()
    try:
        h = (
            db_session.query(HouseholdModel)
            .filter(HouseholdModel.id == household.id)
            .first()
        )
        if h:
            h.recipes_db = recipes
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


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


def _load_household_categories(household_id):
    """Load categories from database.

    B57 (audit 2026-07-07): kept in app_core.py rather than moved into the
    categories blueprint - settings_page() (still a main-app route, not part
    of the categories blueprint) also calls this directly for its "Manage
    Categories" section, so it's genuinely shared, not blueprint-local.

    B61 (2026-07-09): the file-fallback branch has been removed - confirmed
    via Neon that exactly 3 households exist and all are real DB rows, and
    this Render service has no persistent Disk attached, so a file-only
    household could not have survived any deploy to exist today.
    """
    household = current_household()
    if not household:
        return []

    from core.household_paths import load_categories_from_db

    return load_categories_from_db(household)


def _save_household_categories(household_id, categories):
    """Save categories to database.

    M4 (audit 2026-07-07): the DB-backed branch used to catch a commit
    failure, print() it, and then fall through to an unconditional `return`
    right after the try/finally, silently doing nothing while the caller
    believed the save succeeded. Now propagates the real failure.

    B61 (2026-07-09): the file-fallback branch has been removed, same
    reasoning as _load_household_categories() above.
    """
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if household:
            household.categories = categories
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _mark_category_removed(household_id, code):
    """Record a category-deletion tombstone in the database.

    M4 (audit 2026-07-07): had the same silent-failure shape as
    _save_household_categories above - a failed DB write printed and fell
    through to an unconditional `return`, dropping the tombstone silently.
    Now propagates.

    B61 (2026-07-09): the file-fallback branch has been removed, same
    reasoning as _load_household_categories() above.
    """
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import mark_category_removed_to_db

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if household:
            mark_category_removed_to_db(household, code)
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _load_imported_packs_db(household_id):
    """Load imported-pack display metadata (name/icon/color for "Manage
    Recipe Packs") from the database.

    B61 follow-up (2026-07-09): replaces the old file-based
    core.household_paths.load_imported_packs() - unlike every other data
    type, this one was never actually wired to the imported_packs DB column
    that exists for it. Since Render has no persistent Disk, the file
    version silently reset on every deploy - nothing to migrate, that data
    was already gone on every currently-running instance.
    """
    if not household_id:
        return {}

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import load_imported_packs_from_db

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if not household:
            return {}
        return load_imported_packs_from_db(household)
    finally:
        db_session.close()


def _save_imported_pack_metadata_db(household_id, pack_id, display_name, icon, color):
    """Record (or update) display metadata for one imported pack, directly
    in the DB JSONB column (B61 follow-up, 2026-07-09)."""
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import (
        load_imported_packs_from_db,
        save_imported_packs_to_db,
    )

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if household:
            packs = load_imported_packs_from_db(household)
            packs[pack_id] = {
                "display_name": display_name,
                "icon": icon,
                "color": color,
            }
            save_imported_packs_to_db(household, packs)
            db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _remove_imported_pack_metadata_db(household_id, pack_id):
    """Forget a pack's display metadata once its recipes have all been
    removed (B61 follow-up, 2026-07-09)."""
    if not household_id:
        return

    from database.database import SessionLocal
    from database.models import Household
    from core.household_paths import (
        load_imported_packs_from_db,
        save_imported_packs_to_db,
    )

    db_session = SessionLocal()
    try:
        household = (
            db_session.query(Household).filter(Household.id == household_id).first()
        )
        if household:
            packs = load_imported_packs_from_db(household)
            if pack_id in packs:
                del packs[pack_id]
                save_imported_packs_to_db(household, packs)
                db_session.commit()
    except Exception:
        db_session.rollback()
        raise
    finally:
        db_session.close()


def _sort_categories(categories):
    """Favorites always sorts first; everything else is alphabetical by
    display name."""

    def sort_key(c):
        if c.get("code") == "favorites":
            return (-1, "")
        return (0, c.get("name", c.get("name_en", "")).lower())

    return sorted(categories, key=sort_key)


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


def create_app():
    """Application factory (B57, audit 2026-07-07). Builds the Flask app,
    registers security middleware (CSRF, rate limiting, response headers),
    the shared context processor and template globals/filters, then
    registers every route blueprint - route handler modules import
    everything they need from this module rather than each other.
    """
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).parent.parent / "frontend/templates"),
        static_folder=str(Path(__file__).parent.parent / "frontend/static"),
    )

    app.config["JSON_SORT_KEYS"] = False
    app.config["TEMPLATES_AUTO_RELOAD"] = not IS_PRODUCTION

    app.template_filter("format_minutes")(format_minutes)

    _flask_secret_key = os.environ.get("FLASK_SECRET_KEY")
    if not _flask_secret_key:
        # H1 (audit 2026-07-07): this used to silently fall back to
        # secrets.token_hex(32) if the env var was missing. That's a trap in
        # production - every restart (every worker, under a multi-worker
        # deployment) would mint a *different* signing key, silently
        # invalidating every existing session with no error anywhere. A missing
        # production secret should crash at boot, not degrade invisibly - that's
        # exactly B17's symptom (intermittent relogin). Local/dev still gets a
        # random per-process key so `run_local.bat` keeps working with no setup.
        if IS_PRODUCTION:
            raise RuntimeError(
                "FLASK_SECRET_KEY is not set in production. Refusing to start "
                "with a random per-process key, since that silently invalidates "
                "every session on every restart (see B17/H1 in the backlog)."
            )
        _flask_secret_key = secrets.token_hex(32)
    app.config["SECRET_KEY"] = _flask_secret_key

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
    from flask_wtf.csrf import CSRFError

    csrf = CSRFProtect(app)

    # Request body size cap (LO1, audit 2026-07-07) - previously unset, so
    # routes like /api/recipes/import accepted an unbounded JSON body straight
    # into a household's JSONB column, validated only for id/title presence on
    # each item. 5MB comfortably covers a large recipe-pack export/import or a
    # big pantry list with room to spare, while still ruling out an accidental
    # or malicious multi-hundred-MB POST.
    app.config["MAX_CONTENT_LENGTH"] = 5 * 1024 * 1024

    # Rate limiting (H2, audit 2026-07-07) - /login, /signup, /forgot-password,
    # and /resend-confirmation previously accepted unlimited attempts, making
    # them scriptable for credential brute-forcing, fake-account creation, and
    # email-sending abuse. In-process storage (the default) is fine at the
    # single-worker Render deployment this app actually runs (see Procfile) -
    # revisit with a shared store (e.g. Redis) only if the app ever moves to
    # multiple gunicorn workers/processes, same caveat as the PIN lockout in
    # core/auth_helpers.py.
    from flask_limiter import Limiter
    from flask_limiter.util import get_remote_address

    limiter = Limiter(
        get_remote_address,
        app=app,
        storage_uri="memory://",
        default_limits=[],  # only the routes below are limited, not the whole app
    )

    # Disable Jinja2 cache in development for faster iteration
    if not IS_PRODUCTION:
        app.jinja_env.cache = None

    app.jinja_env.globals["avatar_color"] = _avatar_color
    app.jinja_env.globals["avatar_emoji_choices"] = AVATAR_EMOJI_CHOICES
    app.jinja_env.globals["avatar_display"] = _avatar_display

    # Permissive-but-real CSP (M8, 2026-07-08): a strict nonce-based policy
    # isn't practical yet - the app relies on inline <script>/<style>
    # throughout its templates, and auditing every one of them for nonces is
    # a separate, larger effort. This policy still closes the highest-value
    # gaps (no plugins, no framing, no foreign form targets, no base-tag
    # hijack) while allowing what the app actually, legitimately loads:
    # inline scripts/styles, Google Fonts (@import in style.css/theme CSS),
    # and the two YouTube iframe embeds on the welcome page. Verified via
    # `grep` that there are no external fetch()/XHR targets and no other
    # third-party script/style/frame sources anywhere in frontend/.
    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: https:; "
        "frame-src https://www.youtube.com; "
        "object-src 'none'; "
        "base-uri 'self'; "
        "form-action 'self'; "
        "frame-ancestors 'none'"
    )

    @app.after_request
    def _set_security_headers(response):
        """Baseline security response headers (M8, audit 2026-07-07). The app's
        own escaping discipline (see frontend/static/app.js's _esc() pattern) is
        the primary XSS defense; these headers are the backstop for a sink that
        discipline missed, plus clickjacking protection this app had zero of
        before."""
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = _CSP
        if IS_PRODUCTION:
            response.headers["Strict-Transport-Security"] = (
                "max-age=31536000; includeSubDomains"
            )
        return response

    logger.info(f"Flask templates: {app.template_folder}")
    logger.info(f"Flask static: {app.static_folder}")

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

            hh = get_household(household_id)
            if hh:
                household_name = hh.name
            if user_id:
                is_household_owner = acting_role_is_owner()
                can_edit_menu = acting_role_can_edit()

                active_profile_id = session.get("active_profile_id")
                members = get_household_members(household_id)
                active_member = None
                if active_profile_id:
                    active_member = next(
                        (
                            m
                            for m in members
                            if m["member_id"] == str(active_profile_id)
                        ),
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

    @app.errorhandler(404)
    def not_found(error):
        # M5 (audit 2026-07-07): an unmatched /api/* path (typo'd endpoint, a
        # client hitting a route that was renamed/removed) used to get the same
        # full HTML error page a browser navigation would - fetch()-based JS
        # callers then had to guess at a non-JSON response rather than parse a
        # real error, the same class of problem M5 already fixed for 500s below.
        from flask import jsonify, render_template

        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Not found"}), 404
        return render_template("error.html", message="Page not found"), 404

    @app.errorhandler(500)
    def server_error(error):
        from flask import jsonify, render_template

        logger.error(f"Server error: {error}")
        # M5 (audit 2026-07-07): every /api/* route used to fall through to this
        # same HTML error page on an unhandled exception, regardless of how the
        # route's own JSON responses were shaped - this is exactly why B63's
        # frontend error handling had to special-case "the server sent back HTML,
        # not JSON" instead of just reading a real error message. A JSON client
        # now always gets a JSON error back, even from a path this handler itself
        # didn't anticipate.
        if request.path.startswith("/api/"):
            return jsonify({"success": False, "message": "Server error"}), 500
        return render_template("error.html", message="Server error"), 500

    @app.errorhandler(CSRFError)
    def csrf_error(error):
        # M5 (audit 2026-07-07): CSRFProtect's own 400 (missing/expired token -
        # most commonly a stale page left open across a session timeout) had no
        # handler at all, so it returned Flask-WTF's default plain-text response
        # to every route including /api/* fetch() callers - the same
        # "JSON client gets something that isn't JSON" problem this whole fix is
        # for, just via a different trigger than an unhandled exception.
        from flask import jsonify, render_template

        logger.warning(f"CSRF validation failed on {request.path}: {error.description}")
        if request.path.startswith("/api/"):
            return (
                jsonify(
                    {
                        "success": False,
                        "message": "Session expired - please refresh and try again",
                    }
                ),
                400,
            )
        return (
            render_template(
                "error.html", message="Session expired - please refresh and try again"
            ),
            400,
        )

    app.extensions["csrf"] = csrf
    app.extensions["limiter"] = limiter

    # Blueprint registration. Each routes/*.py module exposes a
    # register(bp, limiter) function rather than decorating routes at
    # import time, because the rate-limit decorators (@limiter.limit(...))
    # need this specific Limiter instance, which doesn't exist until here -
    # importing route modules and calling register() only after limiter is
    # built is what makes that possible without a bare module-level
    # decorator trying to reference a limiter that doesn't exist yet.
    from flask import Blueprint
    from deployment.routes import (
        auth_routes,
        admin_routes,
        household_routes,
        pantry_category_routes,
        menu_routes,
        recipe_routes,
        recipe_pack_routes,
    )

    auth_bp = Blueprint("auth", __name__)
    auth_routes.register(auth_bp, limiter)
    app.register_blueprint(auth_bp)

    admin_bp = Blueprint("admin", __name__)
    admin_routes.register(admin_bp)
    app.register_blueprint(admin_bp)

    household_bp = Blueprint("household", __name__)
    household_routes.register(household_bp)
    app.register_blueprint(household_bp)

    pantry_category_bp = Blueprint("pantry_category", __name__)
    pantry_category_routes.register(pantry_category_bp)
    app.register_blueprint(pantry_category_bp)

    menu_bp = Blueprint("menu", __name__)
    menu_routes.register(menu_bp)
    app.register_blueprint(menu_bp)

    recipe_bp = Blueprint("recipe", __name__)
    recipe_routes.register(recipe_bp)
    app.register_blueprint(recipe_bp)

    recipe_pack_bp = Blueprint("recipe_pack", __name__)
    recipe_pack_routes.register(recipe_pack_bp)
    app.register_blueprint(recipe_pack_bp)

    return app
