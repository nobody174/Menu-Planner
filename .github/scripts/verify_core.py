#!/usr/bin/env python3
"""Verify core modules import."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent.parent))

try:
    from core import menu_generator, ingredient_deduplicator
    print("[OK] Core modules import successfully")
except Exception as e:
    print(f"[FAIL] Core module import failed: {e}")
    exit(1)
