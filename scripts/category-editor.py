#!/usr/bin/env python3
#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

"""
Interactive Category Editor

Manage Menu Planner recipe categories from command line.

Usage:
    python3 category-editor.py [--list|--add|--remove|--backup]

Commands:
    --list           - Show all categories
    --add            - Add new category
    --remove         - Remove category
    --backup         - Backup current categories
    --restore        - Restore from backup
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
CATEGORIES_FILE = PROJECT_ROOT / "data" / "categories.json"
BACKUP_DIR = PROJECT_ROOT / "data" / ".backups"

def load_categories():
    """Load categories"""
    if not CATEGORIES_FILE.exists():
        logger.error("categories.json not found")
        return []
    with open(CATEGORIES_FILE, 'r', encoding='utf-8') as f:
        return json.load(f)

def save_categories(categories):
    """Save categories"""
    with open(CATEGORIES_FILE, 'w', encoding='utf-8') as f:
        json.dump(categories, f, ensure_ascii=False, indent=2)
    logger.info(f"Saved {len(categories)} categories")

def list_categories():
    """List all categories"""
    cats = load_categories()
    if not cats:
        logger.info("No categories found")
        return

    logger.info(f"\n{len(cats)} categories:\n")
    for i, cat in enumerate(cats, 1):
        code = cat.get('code', 'unknown')
        name_no = cat.get('name_no', 'Unknown')
        name_en = cat.get('name_en', 'Unknown')
        icon = cat.get('icon', '')
        logger.info(f"  {i}. {icon} {code}")
        logger.info(f"     NO: {name_no}")
        logger.info(f"     EN: {name_en}")

def add_category():
    """Add new category"""
    cats = load_categories()

    logger.info("\nAdd New Category")
    logger.info("-" * 40)

    code = input("Code (e.g., 'pizza'): ").strip().lower()
    if not code:
        logger.error("Code is required")
        return

    # Check if exists
    if any(c['code'] == code for c in cats):
        logger.error(f"Category '{code}' already exists")
        return

    name_no = input("Norwegian name: ").strip()
    name_en = input("English name: ").strip()
    icon = input("Emoji icon (optional): ").strip()
    color = input("Hex color (optional, e.g., #FF6B6B): ").strip()

    new_cat = {
        "code": code,
        "name_no": name_no or code,
        "name_en": name_en or code,
        "description_no": f"Oppskrifter i {name_no} kategori",
        "description_en": f"Recipes in {name_en} category",
        "icon": icon or "🍽️",
        "color": color or "#999999"
    }

    cats.append(new_cat)
    save_categories(cats)
    logger.info(f"Added category: {code}")

def remove_category():
    """Remove category"""
    cats = load_categories()
    list_categories()

    code = input("\nEnter code to remove: ").strip().lower()

    for cat in cats:
        if cat['code'] == code:
            cats.remove(cat)
            save_categories(cats)
            logger.info(f"Removed category: {code}")
            return

    logger.error(f"Category not found: {code}")

def backup_categories():
    """Backup categories"""
    BACKUP_DIR.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = BACKUP_DIR / f"categories_{timestamp}.json"

    cats = load_categories()
    with open(backup_file, 'w', encoding='utf-8') as f:
        json.dump(cats, f, ensure_ascii=False, indent=2)

    logger.info(f"Backed up to: {backup_file}")

def restore_categories():
    """Restore from backup"""
    if not BACKUP_DIR.exists():
        logger.error("No backups found")
        return

    backups = sorted(BACKUP_DIR.glob("categories_*.json"), reverse=True)
    if not backups:
        logger.error("No backups found")
        return

    logger.info("Available backups:\n")
    for i, backup in enumerate(backups[:5], 1):
        logger.info(f"  {i}. {backup.name}")

    choice = input("\nSelect backup number (1-5): ").strip()
    try:
        idx = int(choice) - 1
        if 0 <= idx < len(backups):
            with open(backups[idx], 'r', encoding='utf-8') as f:
                cats = json.load(f)
            save_categories(cats)
            logger.info(f"Restored from: {backups[idx].name}")
        else:
            logger.error("Invalid choice")
    except ValueError:
        logger.error("Invalid input")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    action = sys.argv[1]

    if action == "--list":
        list_categories()
    elif action == "--add":
        add_category()
    elif action == "--remove":
        remove_category()
    elif action == "--backup":
        backup_categories()
    elif action == "--restore":
        restore_categories()
    else:
        print(__doc__)

if __name__ == '__main__':
    main()
