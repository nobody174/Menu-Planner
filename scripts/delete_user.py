#!/usr/bin/env python3
"""
Delete a user and all their associated data cleanly.

Usage:
  Run via the Render Shell for this service, or locally with the
  production DATABASE_URL set:
    DATABASE_URL=<production-url> python scripts/delete_user.py user@email.com

Deletes in the correct order to respect foreign key constraints:
  household_members -> households -> users
"""
import os, sys
import psycopg2

email = sys.argv[1] if len(sys.argv) > 1 else None
if not email:
    print("Usage: python scripts/delete_user.py user@email.com")
    sys.exit(1)

db_url = os.getenv('DATABASE_URL')
if not db_url:
    print("ERROR: DATABASE_URL not set")
    sys.exit(1)

conn = psycopg2.connect(db_url, sslmode='require')
cur = conn.cursor()

cur.execute("SELECT id, email FROM users WHERE email = %s", (email.lower(),))
user = cur.fetchone()
if not user:
    print(f"No user found with email: {email}")
    sys.exit(1)

user_id, user_email = user
print(f"Found user: {user_email} (id: {user_id})")

# Delete in correct order
cur.execute("DELETE FROM household_members WHERE user_id = %s", (user_id,))
print(f"Deleted household_members: {cur.rowcount} rows")

cur.execute("DELETE FROM household_members WHERE household_id IN (SELECT id FROM households WHERE owner_id = %s)", (user_id,))
print(f"Deleted household_members (owned households): {cur.rowcount} rows")

cur.execute("DELETE FROM households WHERE owner_id = %s", (user_id,))
print(f"Deleted households: {cur.rowcount} rows")

cur.execute("DELETE FROM users WHERE id = %s", (user_id,))
print(f"Deleted user: {cur.rowcount} rows")

conn.commit()
print(f"\nDone. User {user_email} fully deleted.")
cur.close()
conn.close()
