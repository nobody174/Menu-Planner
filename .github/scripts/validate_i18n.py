#!/usr/bin/env python3
"""Validate i18n translation completeness."""
import json

with open("frontend/static/i18n.json", encoding="utf-8") as f:
    i18n = json.load(f)

    english_keys = [k for k in i18n.keys() if k.endswith("_en")]
    norwegian_keys = [k for k in i18n.keys() if k.endswith("_no")]

    print(f"[OK] i18n.json has {len(english_keys)} English strings")
    print(f"[OK] i18n.json has {len(norwegian_keys)} Norwegian strings")

    if len(english_keys) != len(norwegian_keys):
        print("[WARN] Warning: English and Norwegian translation counts differ")
