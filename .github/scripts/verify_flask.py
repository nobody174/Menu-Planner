#!/usr/bin/env python3
"""Verify Flask app imports."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path("pi-deployment")))
try:
    from flask_app import app
    print("[OK] Flask app imports successfully")
except Exception as e:
    print(f"[FAIL] Flask app import failed: {e}")
    exit(1)
