#
# Pi-Menu - Shopping List Integrations
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
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
    "olje": "🫒", "oil": "🫒", "olivenolje": "🫒", "trøffelolje": "🫒",
    "majones": "🛒", "mayo": "🛒",
    # Vegetables
    "tomat": "🍅", "tomate": "🍅", "agurk": "🥒", "cucumber": "🥒",
    "løk": "🧅", "onion": "🧅", "hvitløk": "🧄", "garlic": "🧄",
    "mais": "🌽", "corn": "🌽", "paprika": "🫑", "bell pepper": "🫑",
    "gulrot": "🥕", "carrot": "🥕", "potets": "🥔", "potato": "🥔",
    "søtpotet": "🍠", "sweet potato": "🍠", "spinat": "🥬", "spinach": "🥬",
    "salat": "🥬", "salad": "🥬", "kål": "🥬", "cabbage": "🥬",
    "pak choi": "🥬", "brokkoli": "🥦", "broccoli": "🥦",
    "sopp": "🍄", "mushroom": "🍄", "sjampinjong": "🍄",
    # Legumes
    "bønner": "🫘", "beans": "🫘", "sesam": "🛒", "sesam frø": "🛒",
    # Nuts
    "peanøtter": "🥜", "peanuts": "🥜", "jordnøtter": "🥜",
    "nøtter": "🥜", "nut": "🥜",
    # Proteins
    "melk": "🥛", "milk": "🥛", "ost": "🧀", "cheese": "🧀",
    "rømme": "🥣", "sour cream": "🥣", "fløte": "🥣", "cream": "🥣",
    "egg": "🥚", "laks": "🐟", "salmon": "🐟", "ørret": "🐟", "trout": "🐟",
    "fisk": "🐟", "fish": "🐟", "reker": "🦐", "shrimp": "🦐",
    "kylling": "🍗", "chicken": "🍗", "kjøtt": "🥩", "meat": "🥩", "beef": "🥩",
    "svin": "🥓", "pork": "🥓", "bacon": "🥓", "skinke": "🥓", "ham": "🥓",
    "smør": "🧈", "butter": "🧈",
    # Starches
    "ris": "🍚", "rice": "🍚", "pasta": "🍝", "spaghetti": "🍝",
    "brød": "🍞", "bread": "🍞", "kjeks": "🍪", "biscuit": "🍪",
    # Fruits
    "frukt": "🍎", "fruit": "🍎", "eple": "🍎", "apple": "🍎",
    "banan": "🍌", "banana": "🍌", "appelsin": "🍊", "orange": "🍊",
    "sitron": "🍋", "lemon": "🍋", "sitrusfrukt": "🍋", "mango": "🥭",
    "avocado": "🥑", "jordbær": "🍓", "strawberry": "🍓",
    "blåbær": "🫐", "blueberry": "🫐", "druer": "🍇", "grapes": "🍇",
    "melon": "🍈", "vannmelon": "🍉", "watermelon": "🍉",
    # Seasonings & misc
    "salt": "🛒", "sugar": "🍬", "sukker": "🍬", "ingefær": "🫚", "ginger": "🫚",
    "vann": "💧", "water": "💧", "sjokolade": "🍫", "chocolate": "🍫",
    "honey": "🍯", "honning": "🍯",
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
            writer.writerow([
                category,
                item.get("ingredient", ""),
                item.get("quantity", ""),
                item.get("unit", "")
            ])
    return output.getvalue()

def export_json(items_by_category: dict) -> str:
    """Export shopping list as JSON."""
    return json.dumps({
        "exported_at": datetime.now().isoformat(),
        "shopping_list": items_by_category
    }, indent=2, ensure_ascii=False)

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
        "PRODID:-//Pi-Menu//Shopping List//EN",
        "CALSCALE:GREGORIAN",
        "METHOD:PUBLISH",
    ]

    for category, items in items_by_category.items():
        for item in items:
            event_id = str(uuid.uuid4())
            formatted = _format_item(item, category)
            timestamp = datetime.now().strftime("%Y%m%dT%H%M%SZ")

            lines.extend([
                "BEGIN:VTODO",
                f"UID:{event_id}@pimenu.local",
                f"DTSTAMP:{timestamp}",
                f"SUMMARY:{formatted}",
                f"CATEGORIES:{category}",
                "STATUS:NEEDS-ACTION",
                "END:VTODO",
            ])

    lines.append("END:VCALENDAR")
    return "\n".join(lines)

def export_microsoft_todo_format(items_by_category: dict) -> str:
    """Export in Microsoft To Do format (JSON for API)."""
    tasks = []
    for category, items in items_by_category.items():
        for item in items:
            formatted = _format_item(item, category)
            tasks.append({
                "title": formatted,
                "categories": [category]
            })
    return json.dumps({"tasks": tasks}, indent=2, ensure_ascii=False)

# ─────────────────────────────────────────────────────────────────────────────
# API INTEGRATIONS
# ─────────────────────────────────────────────────────────────────────────────

def sync_todoist(items_by_category: dict, api_token: str, project_name: str = "Pi-Menu Shopping") -> dict:
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
        projects = data if isinstance(data, list) else data.get("projects", [])

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
                timeout=10
            )
            resp.raise_for_status()
            project_id = resp.json()["id"]

        # Add tasks
        added = 0
        errors = []
        for category, items in items_by_category.items():
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/tasks",
                        headers=headers,
                        json={"content": formatted, "project_id": project_id, "labels": [category]},
                        timeout=10
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

def sync_ticktick(items_by_category: dict, api_token: str, list_name: str = "Pi-Menu Shopping") -> dict:
    """
    Sync shopping list to TickTick.

    Required API token from user's TickTick account:
    - Get from: https://ticktick.com/user/myprofile
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json"
        }
        base_url = "https://api.ticktick.com/v2"

        # Get or create list
        resp = requests.get(f"{base_url}/lists", headers=headers, timeout=10)
        resp.raise_for_status()
        lists = resp.json().get("resources", [])

        list_id = None
        for lst in lists:
            if lst.get("name") == list_name:
                list_id = lst["id"]
                break

        if not list_id:
            resp = requests.post(
                f"{base_url}/lists",
                headers=headers,
                json={"name": list_name},
                timeout=10
            )
            resp.raise_for_status()
            list_id = resp.json()["id"]

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
                        json={"title": formatted, "listId": list_id, "tags": [category]},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"TickTick sync error: {e}")
        return {"success": False, "error": str(e)}

def sync_anydo(items_by_category: dict, api_token: str, list_name: str = "Pi-Menu Shopping") -> dict:
    """
    Sync shopping list to Any.do.

    Required API token:
    - Get from: https://www.any.do/en/settings/account
    """
    try:
        headers = {"Authorization": f"Bearer {api_token}"}
        base_url = "https://api.any.do/v2"

        # Get or create list
        resp = requests.get(f"{base_url}/lists", headers=headers, timeout=10)
        resp.raise_for_status()
        lists = resp.json().get("lists", [])

        list_id = None
        for lst in lists:
            if lst.get("title") == list_name:
                list_id = lst["id"]
                break

        if not list_id:
            resp = requests.post(
                f"{base_url}/lists",
                headers=headers,
                json={"title": list_name},
                timeout=10
            )
            resp.raise_for_status()
            list_id = resp.json()["id"]

        # Add tasks
        added = 0
        errors = []
        for category, items in items_by_category.items():
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/tasks",
                        headers=headers,
                        json={"title": formatted, "listId": list_id, "categories": [category]},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"Any.do sync error: {e}")
        return {"success": False, "error": str(e)}

def sync_trello(items_by_category: dict, api_key: str, api_token: str, board_name: str = "Pi-Menu Shopping") -> dict:
    """
    Sync shopping list to Trello.

    Required credentials:
    - API Key: https://trello.com/app-key
    - API Token: Generate from the API Key page
    """
    try:
        base_url = "https://api.trello.com/1"

        # Get or create board
        resp = requests.get(
            f"{base_url}/members/me/boards",
            params={"key": api_key, "token": api_token},
            timeout=10
        )
        resp.raise_for_status()
        boards = resp.json()

        board_id = None
        for board in boards:
            if board.get("name") == board_name:
                board_id = board["id"]
                break

        if not board_id:
            resp = requests.post(
                f"{base_url}/boards",
                params={"key": api_key, "token": api_token},
                json={"name": board_name},
                timeout=10
            )
            resp.raise_for_status()
            board_id = resp.json()["id"]

        # Get or create lists for each category
        resp = requests.get(
            f"{base_url}/boards/{board_id}/lists",
            params={"key": api_key, "token": api_token},
            timeout=10
        )
        resp.raise_for_status()
        lists = resp.json()

        added = 0
        errors = []
        for category, items in items_by_category.items():
            list_id = None
            for lst in lists:
                if lst.get("name") == category:
                    list_id = lst["id"]
                    break

            if not list_id:
                resp = requests.post(
                    f"{base_url}/boards/{board_id}/lists",
                    params={"key": api_key, "token": api_token},
                    json={"name": category},
                    timeout=10
                )
                resp.raise_for_status()
                list_id = resp.json()["id"]

            # Add cards
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/cards",
                        params={"key": api_key, "token": api_token},
                        json={"name": formatted, "idList": list_id},
                        timeout=10
                    )
                    if resp.status_code == 200:
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"Trello sync error: {e}")
        return {"success": False, "error": str(e)}

def sync_notion(items_by_category: dict, api_token: str, database_id: str) -> dict:
    """
    Sync shopping list to Notion.

    Required credentials:
    - API Token: Create integration at https://www.notion.so/my-integrations
    - Database ID: Create a database and share it with the integration
    """
    try:
        headers = {
            "Authorization": f"Bearer {api_token}",
            "Notion-Version": "2022-06-28",
            "Content-Type": "application/json"
        }
        base_url = "https://api.notion.com/v1"

        added = 0
        errors = []
        for category, items in items_by_category.items():
            for item in items:
                formatted = _format_item(item, category)
                try:
                    resp = requests.post(
                        f"{base_url}/pages",
                        headers=headers,
                        json={
                            "parent": {"database_id": database_id},
                            "properties": {
                                "Name": {"title": [{"text": {"content": formatted}}]},
                                "Category": {"select": {"name": category}},
                                "Ingredient": {"rich_text": [{"text": {"content": item.get("ingredient", "")}}]},
                                "Quantity": {"number": float(item.get("quantity", 0)) if item.get("quantity") else None},
                                "Unit": {"rich_text": [{"text": {"content": item.get("unit", "")}}]}
                            }
                        },
                        timeout=10
                    )
                    if resp.status_code == 200:
                        added += 1
                    else:
                        errors.append(f"{item.get('ingredient')}: {resp.status_code}")
                except Exception as e:
                    errors.append(f"{item.get('ingredient')}: {str(e)}")

        return {"success": True, "added": added, "errors": errors}
    except Exception as e:
        logger.error(f"Notion sync error: {e}")
        return {"success": False, "error": str(e)}

def sync_google_keep_via_email(items_by_category: dict, email_address: str, smtp_config: dict) -> dict:
    """
    Send shopping list to Google Keep via email.

    Google Keep auto-imports emails sent to your Google Keep email address.
    Requires SMTP configuration.
    """
    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart

        # Format content
        content = export_plain_text(items_by_category)

        # Google Keep email (keep+<hash>@google.com format, but simpler approach is just CC to Gmail)
        msg = MIMEMultipart()
        msg["Subject"] = "Pi-Menu Shopping List"
        msg["From"] = smtp_config.get("from_email", "noreply@pimenu.local")
        msg["To"] = email_address

        msg.attach(MIMEText(content, "plain"))

        # Send
        smtp = smtplib.SMTP(smtp_config.get("host", "localhost"), smtp_config.get("port", 587))
        smtp.starttls()
        smtp.login(smtp_config.get("username", ""), smtp_config.get("password", ""))
        smtp.send_message(msg)
        smtp.quit()

        return {"success": True, "message": f"Shopping list sent to {email_address}"}
    except Exception as e:
        logger.error(f"Google Keep email sync error: {e}")
        return {"success": False, "error": str(e)}
