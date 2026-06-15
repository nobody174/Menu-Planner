#!/usr/bin/env python3
#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

"""
Pi-Menu Command-Line Interface

Utility commands for managing Pi-Menu without the web interface.

Usage:
    python3 pi-menu-cli.py <command> [options]

Commands:
    recipes         - Manage recipes
    categories      - Manage categories
    menu            - Generate and manage menus
    validate        - Validate configuration

Examples:
    python3 pi-menu-cli.py recipes list
    python3 pi-menu-cli.py recipes count
    python3 pi-menu-cli.py categories list
    python3 pi-menu-cli.py menu generate
    python3 pi-menu-cli.py validate
"""

import json
import sys
from pathlib import Path
from datetime import datetime
import logging

logging.basicConfig(level=logging.INFO, format='%(message)s')
logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).parent.parent
DATA_DIR = PROJECT_ROOT / "data"

def load_recipes():
    """Load recipes from JSON"""
    recipe_file = DATA_DIR / "sample_recipes.json"
    if not recipe_file.exists():
        logger.error("Recipe file not found")
        return []
    with open(recipe_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def load_categories():
    """Load categories from JSON"""
    cat_file = DATA_DIR / "categories.json"
    if not cat_file.exists():
        logger.error("Categories file not found")
        return []
    with open(cat_file, 'r', encoding='utf-8') as f:
        return json.load(f)

def recipes_command(action):
    """Handle recipe commands"""
    recipes = load_recipes()

    if action == "list":
        if not recipes:
            logger.info("No recipes found")
            return
        logger.info(f"Found {len(recipes)} recipes:\n")
        for recipe in recipes[:10]:
            title = recipe.get('title_no', 'Unknown')
            cat = recipe.get('category', 'Unknown')
            time = recipe.get('time_minutes', '?')
            logger.info(f"  • {title} ({cat}, {time}m)")
        if len(recipes) > 10:
            logger.info(f"  ... and {len(recipes) - 10} more")

    elif action == "count":
        logger.info(f"Total recipes: {len(recipes)}")
        categories = {}
        for recipe in recipes:
            cat = recipe.get('category', 'Unknown')
            categories[cat] = categories.get(cat, 0) + 1
        logger.info("\nBy category:")
        for cat, count in sorted(categories.items()):
            logger.info(f"  {cat}: {count}")

    elif action == "validate":
        errors = []
        for i, recipe in enumerate(recipes):
            if not recipe.get('title_no'):
                errors.append(f"Recipe {i}: Missing Norwegian title")
            if not recipe.get('title_en'):
                errors.append(f"Recipe {i}: Missing English title")
            if not recipe.get('category'):
                errors.append(f"Recipe {i}: Missing category")
        if errors:
            logger.info(f"Found {len(errors)} validation errors:")
            for err in errors[:10]:
                logger.info(f"  ! {err}")
            if len(errors) > 10:
                logger.info(f"  ... and {len(errors) - 10} more")
        else:
            logger.info("All recipes valid!")

def categories_command(action):
    """Handle category commands"""
    categories = load_categories()

    if action == "list":
        if not categories:
            logger.info("No categories found")
            return
        logger.info(f"Found {len(categories)} categories:\n")
        for cat in categories:
            code = cat.get('code', 'unknown')
            name_no = cat.get('name_no', 'Unknown')
            name_en = cat.get('name_en', 'Unknown')
            logger.info(f"  {code}: {name_no} / {name_en}")

    elif action == "count":
        logger.info(f"Total categories: {len(categories)}")

def menu_command(action):
    """Handle menu commands"""
    if action == "generate":
        try:
            sys.path.insert(0, str(PROJECT_ROOT))
            from core.menu_generator import MenuGenerator

            gen = MenuGenerator()
            if gen.load_recipes():
                gen.filter_recipes()
                if gen.generate_menu():
                    logger.info("Menu generated successfully!")
                    logger.info(f"Week: {gen.menu['week_start']} to {gen.menu['week_end']}")
                else:
                    logger.error("Failed to generate menu")
            else:
                logger.error("Failed to load recipes")
        except Exception as e:
            logger.error(f"Error: {e}")

def validate_command():
    """Validate configuration"""
    logger.info("Validating Pi-Menu configuration...\n")

    checks = {
        "config.py": PROJECT_ROOT / "config.py",
        "categories.json": DATA_DIR / "categories.json",
        "recipes.json": DATA_DIR / "sample_recipes.json",
        ".env.template": PROJECT_ROOT / ".env.template",
        "README.md": PROJECT_ROOT / "README.md",
    }

    valid = 0
    for name, path in checks.items():
        if path.exists():
            logger.info(f"✓ {name}")
            valid += 1
        else:
            logger.info(f"✗ {name} - NOT FOUND")

    logger.info(f"\nValidation: {valid}/{len(checks)} checks passed")

def main():
    if len(sys.argv) < 2:
        print(__doc__)
        return

    command = sys.argv[1]
    action = sys.argv[2] if len(sys.argv) > 2 else None

    if command == "recipes":
        action = action or "list"
        recipes_command(action)
    elif command == "categories":
        action = action or "list"
        categories_command(action)
    elif command == "menu":
        action = action or "generate"
        menu_command(action)
    elif command == "validate":
        validate_command()
    else:
        logger.error(f"Unknown command: {command}")
        print(__doc__)

if __name__ == '__main__':
    main()
