#!/usr/bin/env python3
"""Verify Flask app imports."""
try:
    from deployment.flask_app import app
    print("[OK] Flask app imports successfully")
except Exception as e:
    print(f"[FAIL] Flask app import failed: {e}")
    exit(1)
