#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import os
import json
import msal
import requests
from pathlib import Path
from dotenv import load_dotenv
import sys

sys.path.insert(0, str(Path(__file__).parent.parent))

# Load .env files - try both locations
root_env = Path(__file__).parent.parent / '.env'
local_env = Path(__file__).parent / '.env'

# Load local first, then root (root wins if both exist)
if local_env.exists():
    load_dotenv(local_env, override=False)
if root_env.exists():
    load_dotenv(root_env, override=True)

# Get credentials from environment
AZURE_CLIENT_ID = os.getenv("AZURE_CLIENT_ID", "").strip()
AZURE_CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET", "").strip()
AZURE_TENANT_ID = os.getenv("AZURE_TENANT_ID", "").strip()

GRAPH_ENDPOINT = "https://graph.microsoft.com/v1.0"
SCOPES = ["https://graph.microsoft.com/Tasks.ReadWrite", "User.Read"]

# Token cache file — persists refresh token between Flask restarts
TOKEN_CACHE_FILE = Path(__file__).parent.parent / "data" / "token_cache.json"

# Category emojis for shopping list items
CATEGORY_EMOJI = {
    "Proteins": "🥩",
    "Vegetables": "🥬",
    "Dairy": "🧀",
    "Pantry": "🥫",
    "Herbs & Spices": "🧂",
    "Other": "🛒",
}

# Ingredient-specific emojis for smart matching
INGREDIENT_EMOJI = {
    # Oils & condiments
    "olje": "🫒",
    "oil": "🫒",
    "olivenolje": "🫒",
    "trøffelolje": "🫒",
    "majones": "🛒",
    "mayo": "🛒",

    # Vegetables
    "tomat": "🍅",
    "tomate": "🍅",
    "agurk": "🥒",
    "cucumber": "🥒",
    "løk": "🧅",
    "onion": "🧅",
    "hvitløk": "🧄",
    "garlic": "🧄",
    "mais": "🌽",
    "corn": "🌽",
    "paprika": "🫑",
    "bell pepper": "🫑",
    "gulrot": "🥕",
    "carrot": "🥕",
    "potets": "🥔",
    "potato": "🥔",
    "søtpotet": "🍠",
    "sweet potato": "🍠",
    "spinat": "🥬",
    "spinach": "🥬",
    "salat": "🥬",
    "salad": "🥬",
    "kål": "🥬",
    "cabbage": "🥬",
    "pak choi": "🥬",
    "brokkoli": "🥦",
    "broccoli": "🥦",
    "sopp": "🍄",
    "mushroom": "🍄",
    "sjampinjong": "🍄",

    # Legumes
    "bønner": "🫘",
    "beans": "🫘",
    "sesam": "🛒",
    "sesam frø": "🛒",

    # Nuts
    "peanøtter": "🥜",
    "peanuts": "🥜",
    "jordnøtter": "🥜",
    "nøtter": "🥜",
    "nut": "🥜",

    # Proteins
    "melk": "🥛",
    "milk": "🥛",
    "ost": "🧀",
    "cheese": "🧀",
    "rømme": "🥣",
    "sour cream": "🥣",
    "fløte": "🥣",
    "cream": "🥣",
    "egg": "🥚",
    "laks": "🐟",
    "salmon": "🐟",
    "ørret": "🐟",
    "trout": "🐟",
    "fisk": "🐟",
    "fish": "🐟",
    "reker": "🦐",
    "shrimp": "🦐",
    "kylling": "🍗",
    "chicken": "🍗",
    "kjøtt": "🥩",
    "meat": "🥩",
    "beef": "🥩",
    "svin": "🥓",
    "pork": "🥓",
    "bacon": "🥓",
    "skinke": "🥓",
    "ham": "🥓",
    "smør": "🧈",
    "butter": "🧈",

    # Starches
    "ris": "🍚",
    "rice": "🍚",
    "pasta": "🍝",
    "spaghetti": "🍝",
    "brød": "🍞",
    "bread": "🍞",
    "kjeks": "🍪",
    "biscuit": "🍪",

    # Fruits
    "frukt": "🍎",
    "fruit": "🍎",
    "eple": "🍎",
    "apple": "🍎",
    "banan": "🍌",
    "banana": "🍌",
    "appelsin": "🍊",
    "orange": "🍊",
    "sitron": "🍋",
    "lemon": "🍋",
    "sitrusfrukt": "🍋",
    "mango": "🥭",
    "avocado": "🥑",
    "jordbær": "🍓",
    "strawberry": "🍓",
    "blåbær": "🫐",
    "blueberry": "🫐",
    "druer": "🍇",
    "grapes": "🍇",
    "melon": "🍈",
    "vannmelon": "🍉",
    "watermelon": "🍉",

    # Seasonings & misc
    "salt": "🛒",
    "sugar": "🍬",
    "sukker": "🍬",
    "ingefær": "🫚",
    "ginger": "🫚",
    "vann": "💧",
    "water": "💧",
    "sjokolade": "🍫",
    "chocolate": "🍫",
    "honey": "🍯",
    "honning": "🍯",
}


def _load_cache() -> msal.SerializableTokenCache:
    cache = msal.SerializableTokenCache()
    if TOKEN_CACHE_FILE.exists():
        cache.deserialize(TOKEN_CACHE_FILE.read_text(encoding="utf-8"))
    return cache


def _save_cache(cache: msal.SerializableTokenCache):
    if cache.has_state_changed:
        TOKEN_CACHE_FILE.parent.mkdir(parents=True, exist_ok=True)
        TOKEN_CACHE_FILE.write_text(cache.serialize(), encoding="utf-8")


def _build_app(cache: msal.SerializableTokenCache = None) -> msal.ConfidentialClientApplication:
    return msal.ConfidentialClientApplication(
        client_id=AZURE_CLIENT_ID,
        client_credential=AZURE_CLIENT_SECRET,
        authority="https://login.microsoftonline.com/consumers",
        token_cache=cache,
    )


# ── Public API ────────────────────────────────────────────────────────────────

def get_access_token() -> str | None:
    """Return a valid access token, silently refreshing if needed. Returns None if not yet authorised."""
    cache = _load_cache()
    app = _build_app(cache)
    accounts = app.get_accounts()
    if not accounts:
        return None
    result = app.acquire_token_silent(SCOPES, account=accounts[0])
    _save_cache(cache)
    if result and "access_token" in result:
        return result["access_token"]
    return None


def is_authorised() -> bool:
    return get_access_token() is not None


def build_msal_app(redirect_uri: str) -> msal.ConfidentialClientApplication:
    cache = _load_cache()
    return _build_app(cache)


def get_auth_url(msal_app, redirect_uri: str, state: str = None) -> dict:
    return msal_app.initiate_auth_code_flow(
        scopes=SCOPES,
        redirect_uri=redirect_uri,
        state=state,
    )


def acquire_token_by_auth_code_flow(msal_app, flow: dict, auth_response: dict) -> dict:
    result = msal_app.acquire_token_by_auth_code_flow(flow, auth_response)
    # Save the cache (which now holds the refresh token) after first login
    _save_cache(msal_app.token_cache)
    return result


def get_user_info(access_token: str) -> dict:
    resp = requests.get(
        f"{GRAPH_ENDPOINT}/me",
        headers={"Authorization": f"Bearer {access_token}"},
        timeout=10,
    )
    resp.raise_for_status()
    return resp.json()


def sync_shopping_list_to_todo(access_token: str, items_by_category: dict, list_name: str = "Menu Planner Shopping") -> dict:
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Content-Type": "application/json",
    }

    # Get or create "Handleliste" list, clear old tasks first
    resp = requests.get(f"{GRAPH_ENDPOINT}/me/todo/lists", headers=headers, timeout=10)
    resp.raise_for_status()
    todo_lists = resp.json().get("value", [])

    list_id = None
    for lst in todo_lists:
        if lst.get("displayName") == list_name:
            list_id = lst["id"]
            break

    if list_id:
        # Delete the whole list and recreate it — guaranteed clean slate
        requests.delete(f"{GRAPH_ENDPOINT}/me/todo/lists/{list_id}", headers=headers, timeout=10)

    r = requests.post(f"{GRAPH_ENDPOINT}/me/todo/lists", headers=headers,
                      json={"displayName": list_name}, timeout=10)
    r.raise_for_status()
    list_id = r.json()["id"]

    added = 0
    errors = []
    for category, items in items_by_category.items():
        for item in items:
            ingredient = str(item.get("ingredient") or "")
            quantity = str(item.get("quantity") or "")
            unit = str(item.get("unit") or "")
            title = " ".join(p for p in [ingredient, quantity, unit] if p)

            # Try to find ingredient-specific emoji, fall back to category emoji
            emoji = "🛒"
            ing_lower = ingredient.lower()
            for ing_key, ing_emoji in INGREDIENT_EMOJI.items():
                if ing_key in ing_lower:
                    emoji = ing_emoji
                    break
            if emoji == "🛒":
                emoji = CATEGORY_EMOJI.get(category, "🛒")

            title = f"{emoji} {title}"
            r = requests.post(
                f"{GRAPH_ENDPOINT}/me/todo/lists/{list_id}/tasks",
                headers=headers,
                json={"title": title},
                timeout=10,
            )
            if r.status_code == 201:
                added += 1
            else:
                errors.append(f"{ingredient}: {r.status_code}")

    return {"added": added, "errors": errors, "list_name": list_name}
