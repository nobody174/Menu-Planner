# Railway Database Operations Guide

Quick reference for managing your Menu-Planner production database on Railway.

## Option 1: Web Console (Easiest)

**Go to:**
1. [railway.app](https://railway.app) → Your **Menu-Planner** project
2. Click **PostgreSQL** plugin
3. Click **Data** tab (top navigation)

**Run SQL queries:**

In the query editor, paste each command and click **Execute**:

```sql
DELETE FROM household_members;
```

```sql
DELETE FROM households;
```

```sql
DELETE FROM users;
```

Verify with:
```sql
SELECT COUNT(*) FROM users;
```

Should return `0` if successful.

---

## Option 2: Python Script (Command Line)

For scripted/automated operations:

```powershell
cd d:\Claude AI Projects\projects\GitHub\Menu-Planner
railway run --service "Menu-Planner" python scripts/delete_test_users.py
```

**Requirements:**
- Railway CLI installed (`npm install -g @railway/cli`)
- Linked to project (`railway link --project "zoological-reverence"`)

---

## Common Tasks

### Delete All Test Users

Web Console (copy-paste in order):
```sql
DELETE FROM household_members;
DELETE FROM households;
DELETE FROM users;
SELECT COUNT(*) FROM users;
```

### Backfill Email Confirmation (Grandfathering)

If deploying email confirmation and want to preserve existing user access:

```sql
UPDATE users SET email_confirmed_at = NOW() WHERE email_confirmed_at IS NULL;
SELECT COUNT(*) FROM users WHERE email_confirmed_at IS NOT NULL;
```

### Quick Checks

**Count users:**
```sql
SELECT COUNT(*) FROM users;
```

**List all users (with email & confirmation status):**
```sql
SELECT id, email, email_confirmed_at FROM users LIMIT 20;
```

**Find unconfirmed users:**
```sql
SELECT email FROM users WHERE email_confirmed_at IS NULL;
```

---

## Notes

- **Web Console is recommended** for one-off operations and testing
- **Python scripts** are better for CI/CD pipelines and complex workflows
- All SQL commands are in `scripts/` for reference
- Always verify with a `SELECT COUNT(*)` after deletes
- Deletes are **permanent and cannot be undone** — double-check before running!
