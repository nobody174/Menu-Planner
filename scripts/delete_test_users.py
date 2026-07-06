#!/usr/bin/env python3
"""
Delete all test users from the database.

Usage:
  Render (PostgreSQL):
    Run via the Render Shell for this service, or locally with the
    production DATABASE_URL set:
      DATABASE_URL=<production-url> python scripts/delete_test_users.py

  Or, from the Render Postgres dashboard's Query console:
    Run the SQL commands in scripts/delete_test_users.sql

WARNING: This is destructive and cannot be undone. Use only when intentional.
"""

import os
import sys
import psycopg2
from urllib.parse import urlparse

def get_connection():
    """Get database connection from environment."""
    db_url = os.getenv('DATABASE_URL')

    if not db_url:
        print("ERROR: DATABASE_URL not set")
        print("  - For Render: run via the Render Shell, or set DATABASE_URL locally to the production value")
        print("  - Alternatively, use the Render Postgres dashboard's Query console to run scripts/delete_test_users.sql")
        sys.exit(1)

    # Parse PostgreSQL URL (postgresql://user:pass@host:port/dbname)
    # We pass SSL required since Render uses encrypted connections
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

        print("Deleting household_members...")
        cursor.execute("DELETE FROM household_members")
        rows = cursor.rowcount
        print(f"  Deleted {rows} rows")

        print("Deleting households...")
        cursor.execute("DELETE FROM households")
        rows = cursor.rowcount
        print(f"  Deleted {rows} rows")

        print("Deleting users...")
        cursor.execute("DELETE FROM users")
        rows = cursor.rowcount
        print(f"  Deleted {rows} rows")

        # Verify
        cursor.execute("SELECT COUNT(*) FROM users")
        remaining = cursor.fetchone()[0]

        conn.commit()
        cursor.close()
        conn.close()

        print(f"\n✓ Done! Remaining users: {remaining}")

    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main()
