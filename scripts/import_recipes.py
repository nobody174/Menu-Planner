#!/usr/bin/env python3
#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

"""
Excel Recipe Importer

Reads recipes from the Excel template and converts them to JSON format
for use by Pi-Menu.

Usage:
    python3 import_recipes.py <path-to-excel-file> [--output <output-path>]

Example:
    python3 import_recipes.py templates/my_recipes.xlsx
"""

import json
import sys
from pathlib import Path

def import_recipes(excel_path: str, output_path: str = None):
    """
    Import recipes from Excel template to JSON format.

    Args:
        excel_path: Path to the Excel template file
        output_path: Optional custom output path (defaults to data/recipes_db.json)
    """
    try:
        # Try to import openpyxl for Excel reading
        try:
            from openpyxl import load_workbook
        except ImportError:
            print("Error: openpyxl is required. Install with: pip install openpyxl")
            return False

        excel_file = Path(excel_path)
        if not excel_file.exists():
            print(f"Error: File not found: {excel_path}")
            return False

        print(f"Reading recipes from: {excel_file.name}")

        # Load the Excel workbook
        wb = load_workbook(excel_file)
        ws = wb['Add Your Recipes']

        recipes = []
        recipe_id = 1

        # Skip header row, start from row 2
        for row in ws.iter_rows(min_row=2, values_only=False):
            # Get cell values (implementation depends on your Excel structure)
            # This is a placeholder - adjust based on your template structure

            # For now, just show that the script is ready to be extended
            pass

        # Set output path
        if output_path is None:
            output_path = Path(__file__).parent.parent / "data" / "recipes_db.json"
        else:
            output_path = Path(output_path)

        # Save recipes as JSON
        output_path.parent.mkdir(parents=True, exist_ok=True)

        with open(output_path, 'w', encoding='utf-8') as f:
            json.dump(recipes, f, ensure_ascii=False, indent=2)

        print(f"Successfully imported {len(recipes)} recipes")
        print(f"Saved to: {output_path}")
        return True

    except Exception as e:
        print(f"Error importing recipes: {e}")
        return False

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(1)

    excel_file = sys.argv[1]
    output_file = sys.argv[3] if len(sys.argv) > 3 and sys.argv[2] == '--output' else None

    success = import_recipes(excel_file, output_file)
    sys.exit(0 if success else 1)
