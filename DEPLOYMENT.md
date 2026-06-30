# Deployment & Database Management

This document covers Railway deployment, database maintenance, and common operational tasks.

## Prerequisites

### Railway CLI

Install and authenticate once:

```powershell
npm install -g @railway/cli
railway login
cd d:\Claude AI Projects\projects\GitHub\Menu-Planner
railway link --project "zoological-reverence"
```

Verify you're linked:
```powershell
railway status
```

## Database Operations

All database scripts are in `scripts/` and designed to run via `railway run`.

### Delete All Test Users

**Use when:** Starting fresh testing, cleaning up test accounts before a release.

**Command:**
```powershell
railway run python scripts/delete_test_users.py
```

**What it does:**
- Deletes all household_members
- Deletes all households
- Deletes all users
- Verifies the database is now empty

**Warning:** This is **destructive and permanent**. Only run when intentional.

---

### Backfill Email Confirmation (Grandfathering)

**Use when:** Deploying the email confirmation feature without blocking existing users.

**Command:**
```powershell
railway run python scripts/backfill_email_confirmed.py
```

**What it does:**
- Marks all unconfirmed users as confirmed
- Sets `email_confirmed_at = NOW()` for any user where it's NULL

**Warning:** Run this BEFORE pushing if you want to preserve access for existing users.

---

## Deployment Checklist

Before pushing to Railway:

- [ ] All local tests pass (unit tests + manual feature testing)
- [ ] Database migrations are in place and valid
- [ ] Decide: delete test users OR backfill email_confirmed?
- [ ] Run the chosen script above
- [ ] Verify with: `railway run python scripts/delete_test_users.py` (dry run, or check manually after)
- [ ] Commit and push to GitHub
- [ ] Monitor Railway logs: `railway logs`

## Environment Variables

Set these in Railway's **Variables** tab:

- `RESEND_API_KEY` — Email sending (optional for local testing)
- `DATABASE_URL` — Auto-set by Railway PostgreSQL plugin

Verify variables are loaded:
```powershell
railway run printenv | grep -E "RESEND|DATABASE"
```

---

## Debugging

### Check Railway Status

```powershell
railway status
railway logs --tail 50
```

### Check Database Connection

```powershell
railway run python -c "import os; print(os.getenv('DATABASE_URL')[:50])"
```

### Run Interactive psql

```powershell
railway run psql
# Then type SQL queries directly
# Type \q to exit
```

---

## Notes

- Python-based scripts are preferred because they work without extra dependencies.
- All scripts connect via `DATABASE_URL` environment variable, which Railway sets automatically.
