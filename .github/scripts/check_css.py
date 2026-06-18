#!/usr/bin/env python3
"""Check required CSS files exist."""
import os

required_css = [
    "frontend/static/style.css",
    "frontend/static/themes/theme-switcher.css",
    "frontend/static/themes/previews/theme-registry.json",
]

for f in required_css:
    if os.path.exists(f):
        print(f"[OK] {f} exists")
    else:
        print(f"[FAIL] {f} missing")
        exit(1)
