#!/usr/bin/env python3
"""Verify core modules import."""
try:
    from core import menu_generator, ingredient_deduplicator
    print("✓ Core modules import successfully")
except Exception as e:
    print(f"✗ Core module import failed: {e}")
    exit(1)
