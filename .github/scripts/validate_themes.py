#!/usr/bin/env python3
"""Validate theme registry and CSS files."""
import os
import json

theme_dir = "frontend/static/themes"
css_files = [f for f in os.listdir(theme_dir) if f.endswith(".css")]
print(f"✓ Found {len(css_files)} theme CSS files")

# Validate registry
with open("frontend/static/themes/previews/theme-registry.json") as f:
    registry = json.load(f)
    print(f"✓ Theme registry has {len(registry)} themes")
    for theme in registry:
        if all(k in theme for k in ["id", "name", "file", "preview_color"]):
            print(f'  ✓ {theme["name"]} registered')
        else:
            print(f"  ✗ {theme} missing fields")
            exit(1)
