#!/usr/bin/env python3
"""Validate all JSON files in the project."""
import json
import os
import glob

json_files = glob.glob("**/*.json", recursive=True)
json_files = [f for f in json_files if ".github" not in f and "node_modules" not in f]

for file in json_files:
    try:
        with open(file, encoding="utf-8") as f:
            json.load(f)
        print(f"[OK] {file} is valid JSON")
    except json.JSONDecodeError as e:
        print(f"[FAIL] {file} has JSON syntax error: {e}")
        exit(1)
    except Exception as e:
        print(f"[FAIL] {file} error: {e}")
        exit(1)

print(f"\n[OK] All {len(json_files)} JSON files are valid")
