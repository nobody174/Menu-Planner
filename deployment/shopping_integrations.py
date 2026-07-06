#
# Menu Planner - Shopping List Integrations
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import json
import csv
import requests
import logging
from io import StringIO
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)

# Category emojis for all integrations
CATEGORY_EMOJI = {
    "Proteins": "🥩",
    "Vegetables": "🥬",
    "Dairy": "🧀",
    "Pantry": "🥫",
    "Herbs & Spices": "🧂",
    "Other": "🛒",
}

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


def _get_emoji(ingredient: str, category: str = "Other") -> str:
    """Get emoji for ingredient with fallback to category emoji."""
    emoji = "🛒"
    ing_lower = ingredient.lower()
    for ing_key, ing_emoji in INGREDIENT_EMOJI.items():
        if ing_key in ing_lower:
            emoji = ing_emoji
            break
    if emoji == "🛒":
        emoji = CATEGORY_EMOJI.get(category, "🛒")
    return emoji


def _format_item(item: dict, category: str = "Other") -> str:
    """Format a single shopping item as a string."""
    ingredient = str(item.get("ingredient") or "")
    quantity = str(item.get("quantity") or "")
    unit = str(item.get("unit") or "")
    emoji = _get_emoji(ingredient, category)
    parts = [ingredient]
    if quantity and unit:
        parts.append(f"{quantity}{unit}")
    elif quantity:
        parts.append(quantity)
    return f"{emoji} {' '.join(parts)}".strip()


# ─────────────────────────────────────────────────────────────────────────────
# EXPORT FORMATS
# ─────────────────────────────────────────────────────────────────────────────


def export_csv(items_by_category: dict) -> str:
    """Export shopping list as CSV."""
    output = StringIO()
    writer = csv.writer(output)
    writer.writerow(["Category", "Ingredient", "Quantity", "Unit"])
    for category, items in items_by_category.items():
        for item in items:
            writer.writerow(
                [
                    category,
                    item.get("ingredient", ""),
                    item.get("quantity", ""),
                    item.get("unit", ""),
                ]
            )
    return output.getvalue()


def export_json(items_by_category: dict) -> str:
    """Export shopping list as JSON."""
    return json.dumps(
        {"exported_at": datetime.now().isoformat(), "shopping_list": items_by_category},
        indent=2,
        ensure_ascii=False,
    )


def export_todoist_format(items_by_category: dict) -> str:
    """Export in Todoist-compatible format (one item per line with category)."""
    lines = []
    for category, items in items_by_category.items():
        lines.append(f"# {category}")
        for item in items:
            formatted = _format_item(item, category)
            lines.append(f"  - {formatted}")
    return "\n".join(lines)


def export_plain_text(items_by_category: dict) -> str:
    """Export as plain text with categories and emojis."""
    lines = []
    for category, items in items_by_category.items():
        lines.append(f"\n{CATEGORY_EMOJI.get(category, '🛒')} {category}")
        lines.append("=" * 40)
        for item in items:
            formatted = _format_item(item, category)
            lines.append(formatted)
    return "\n".join(lines).strip()


def export_ics(items_by_category: dict) -> str:
    """Export as ICS file for Apple Reminders (as separate reminders)."""
    import uuid

    lines = [
        "BEGIN:VCALENDAR",
        "VERSION:2.0",
        "PRODID:-//Menu-Planner//Shopping List//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for category, items in items_by_category.items():
        for item in items:
            event_id = str(uuid.uuid4())
            formatted = _format_item(item, category)
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")

            lines.extend(
                [
                    "BEGIN:VTODO",
                    f"UID:{event_id}@pimenu.local",
                    f"DTSTAMP:{timestamp}",
                    f"SUMMARY:{formatted}",
                    f"CATEGORIES:{category}",
                    "STATUS:NEEDS-ACTION",
                    "END:VTODO",
                ]
            )

    lines.append("END:VCALENDAR")
    return "\n".join(lines)


def export_microsoft_todo_format(items_by_category: dict) -> str:
    """Export in Microsoft To Do format (JSON for API)."""
    tasks = []
    for category, items in items_by_category.items():
        for item in items:
            formatted = _format_item(item, category)
            tasks.append({"title": formatted, "categories": [category]})
    return json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False)


# ─────────────────────────────────────────────────────────────────────────────
# API INTEGRATIONS
# ─────────────────────────────────────────────────────────────────────────────


def sync_todoist(
    items_by_category: dict, api_token: str, project_name: str = "Menu Planner Shopping"
) -> dict:
    """
    Sync shopping list to Todoist.

    Required API token from user's Todoist settings:
    - Get from: https://todoist.com/app/settings/integrations/developer
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        base_url = "https://api.todoist.com/api/v1"

        # Get or create project
        resp = requests.get(f"{base_url}/projects", headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error(f"Todoist API error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        data = resp.json()
        # Handle Todoist API v1 response format with 'results' key
        projects = data.get("results", []) if isinstance(data, dict) else data

        project_id = None
        for proj in projects:
            if isinstance(proj, dict) and proj.get("name") == project_name:
                project_id = proj["id"]
                break

        if not project_id:
            resp = requests.post(
                f"{base_url}/projects",
                headers=headers,
                json={"name": project_name},
                timeout=10,
            )
            resp.raise_for_status()
            project_id = resp.json()["id"]

        # Clear existing tasks in the project
        resp = requests.get(
            f"{base_url}/tasks",
            headers=headers,
            params={"project_id": project_id},
            timeout=10,
        )
        if resp.status_code == 200:
            data = resp.json()
            # Handle Todoist API v1 response format with 'results' key
            tasks = data.get("results", []) if isinstance(data, dict) else data
            for task in tasks:
                try:
                    requests.delete(
                        f"{base_url}/tasks/{task['id']}", headers=headers, timeout=10
                    )
                except Exception as e:
                    logger.warning(f"Failed to delete old task: {e}")

        # Add new tasks
        added = 0
        errors = []
        for category, items in items_by_category.items():
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/tasks",
                        headers=headers,
                        json={
                            "content": formatted,
                            "project_id": project_id,
                            "labels": [category],
                        },
                        timeout=10,
                    )
                    if resp.status_code == 200:
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"Todoist sync error: {e}")
        return {"success": False, "error": str(e)}


def sync_ticktick(
    items_by_category: dict, api_token: str, list_name: str = "Menu Planner Shopping"
) -> dict:
    """
    Sync shopping list to TickTick.

    Required API token from user's TickTick account:
    - Get from: https://ticktick.com/webapp/#q/all/completed?modalType=settings
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
        }
        base_url = "https://api.ticktick.com/open/v1"

        # Get or create project (list)
        resp = requests.get(f"{base_url}/project", headers=headers, timeout=10)
        if resp.status_code != 200:
            logger.error(f"TickTick API error: {resp.status_code} - {resp.text}")
        resp.raise_for_status()
        projects = (
            resp.json()
            if isinstance(resp.json(), list)
            else resp.json().get("data", [])
        )

        project_id = None
        for proj in projects:
            if proj.get("name") == list_name:
                project_id = proj["id"]
                break

        if not project_id:
            resp = requests.post(
                f"{base_url}/project",
                headers=headers,
                json={"name": list_name, "kind": "TASK"},
                timeout=10,
            )
            resp.raise_for_status()
            project_id = resp.json().get("id") or resp.json().get("data", {}).get("id")

        # Delete existing tasks for this project (deduplication)
        resp = requests.get(
            f"{base_url}/task",
            params={"projectId": project_id},
            headers=headers,
            timeout=10,
        )
        if resp.status_code == 200:
            existing_tasks = (
                resp.json()
                if isinstance(resp.json(), list)
                else resp.json().get("data", [])
            )
            for task in existing_tasks:
                requests.delete(
                    f"{base_url}/task/{task['id']}", headers=headers, timeout=10
                )

        # Add tasks
        added = 0
        errors = []
        for category, items in items_by_category.items():
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/task",
                        headers=headers,
                        json={
                            "title": formatted,
                            "projectId": project_id,
                            "tags": [category],
                        },
                        timeout=10,
                    )
                    if resp.status_code in (200, 201):
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"TickTick sync error: {e}")
        return {"success": False, "error": str(e)}
