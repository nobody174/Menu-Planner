#!/usr/bin/env python3
"""
Mark all unconfirmed users as confirmed (grandfathering).

Usage:
  Railway (PostgreSQL):
    railway run --service Menu-Planner python scripts/backfill_email_confirmed.py

  Or, from Railway Postgres shell via web console:
    Run the SQL commands in scripts/backfill_email_confirmed.sql

This is useful when deploying the email confirmation feature without
blocking existing users who signed up before the feature was enabled.
"""

import os
import sys
import psycopg2
from datetime import datetime
from urllib.parse import urlparse

def get_connection():
    """Get database connection from environment."""
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        print("ERROR: DATABASE_URL not set")
        print("  - For Railway: run via 'railway run --service Menu-Planner python scripts/backfill_email_confirmed.py'")
        print("  - Alternatively, use Railway web console Data tab to run scripts/backfill_email_confirmed.sql")
        sys.exit(1)

    # Parse PostgreSQL URL (Railway format: postgresql://user:pass@host:port/dbname)
    # We pass SSL required since Railway uses encrypted connections
    if db_url.startswith('postgresql://') or db_url.startswith('postgres://'):
        try:
            conn = psycopg2.connect(db_url, sslmode='require')
            return conn
        except Exception as e:
            print(f"ERROR connecting to database: {e}")
            sys.exit(1)
    else:
        print(f"ERROR: Unsupported database URL format: {db_url[:30]}...")
        sys.exit(1)

def main():
    try:
        print("Connecting to database...")
        conn = get_connection()
        cursor = conn.cursor()

        print("Backfilling email_confirmed_at for unconfirmed users...")
        cursor.execute(
            "UPDATE users SET email_confirmed_at = NOW() WHERE email_confirmed_at IS NULL"
        )
        rows = cursor.rowcount
        print(f"  Updated {rows} users")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM users WHERE email_confirmed_at IS NOT NULL")
        confirmed = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✓ Done! Total confirmed users: {confirmed}")

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
