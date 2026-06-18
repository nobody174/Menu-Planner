#!/usr/bin/env python3
"""Check required data files exist and are valid JSON."""
import json
import os

files = ["data/sample_recipes.json", "data/categories.json", "frontend/static/i18n.json"]
for f in files:
    if os.path.exists(f):
        try:
            with open(f, encoding="utf-8") as file:
                json.load(file)
            print(f"[OK] {f} is valid JSON")
        except json.JSONDecodeError as e:
            print(f"[FAIL] {f} has JSON error: {e}")
            exit(1)
    else:
        print(f"[FAIL] {f} missing")
        exit(1)
