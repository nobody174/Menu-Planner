# F4 Hosting Migration: Deployment Guide

**Target**: Render.com (web) + Neon.tech (PostgreSQL database)
**Timeline**: 26 days until Railway trial expires (~2026-07-27)
**Current Date**: 2026-07-01
**Phases 1-6**: ✅ Complete (schema, migration, refactoring, tests)

---

## Phase 7: Production Deployment

### Step 1: Create Neon.tech Account (Database)

1. Go to **https://neon.tech**
2. Sign up (email or GitHub OAuth)
3. Create a new project:
   - Project name: `menu-planner`
   - Region: Europe (closest to users)
4. Note your **connection string**:
   ```
   postgresql://[user]:[password]@[host].neon.tech/[database]?sslmode=require
   ```
5. Save this to a secure location (we'll use it in Render environment variables)

**Database Quota**: 3GB free tier (sufficient for testing phase with family/friends)

---

### Step 2: Create Render.com Account (Web)

1. Go to **https://render.com**
2. Sign up with **GitHub OAuth** (Render connects to GitHub for auto-deployments)
3. Authorize the connection to your `Menu-Planner` repository

**Why GitHub OAuth?**
- Automatic deployments: push to main → Render redeploys instantly
- Environment secrets: store Neon connection string safely
- No manual FTP/SSH needed
- Easy rollback: revert commit → Render deploys previous version

---

### Step 3: Create Web Service on Render

1. In Render dashboard, click **"+ New"** → **"Web Service"**
2. Configure:
   - **Name**: `menu-planner`
   - **Git Repo**: Select your Menu-Planner GitHub repo
   - **Branch**: `public-release-v1` (or current branch)
   - **Runtime**: Python 3.11
   - **Build Command**:
     ```
     pip install -r requirements.txt && alembic upgrade head
     ```
   - **Start Command**:
     ```
     gunicorn -b 0.0.0.0:$PORT deployment.flask_app:app
     ```

3. Set environment variables:
   - **DATABASE_URL**: Paste Neon connection string
   - **FLASK_ENV**: `production`
   - **SECRET_KEY**: Generate a strong random string (keep secret!)
   - Any other env vars from your `.env` (OAuth tokens, etc.)

4. Click **"Create Web Service"**

**First Deploy**: Render will:
- Clone your repo
- Install Python dependencies
- Run `alembic upgrade head` (applies all migrations including F4)
- Start Flask with gunicorn
- Assign a URL: `https://menu-planner.onrender.com`

---

### Step 4: Run Backfill Script on Render

Once the web service is running, SSH into it and run the backfill:

```bash
# In Render dashboard, click web service → "Shell"
python scripts/backfill_household_data.py
```

This will:
1. Read existing JSON files from `/app/data/households/<id>/`
2. Write data to PostgreSQL JSONB columns
3. Report migration stats (recipes, pantry items, etc.)

**Dry Run First**:
```bash
python scripts/backfill_household_data.py --dry-run
```

---

### Step 5: Verify Deployment

1. **Check web service status**:
   - Render dashboard → Web Service → check "Events" tab
   - Should show "Build succeeded" and "Deploy succeeded"

2. **Test the app**:
   - Navigate to `https://menu-planner.onrender.com`
   - Log in with test account
   - Generate a menu
   - Add recipes
   - Check pantry → data should persist

3. **Monitor logs**:
   - Render dashboard → "Logs" tab
   - Watch for any errors (database connection, Alembic issues, etc.)

4. **Verify database**:
   - Connect to Neon PostgreSQL:
     ```bash
     psql postgresql://[user]:[password]@[host].neon.tech/menu-planner
     ```
   - Check household data:
     ```sql
     SELECT id, name, recipes_db, pantry, categories FROM households LIMIT 1;
     ```

---

### Step 6: Test with Family/Friends (48-72 hours)

1. **Create test accounts** on Render instance
2. **Invite 2-3 people** to test:
   - Sign up
   - Add recipes
   - Generate menus
   - Check pantry persistence
   - Test across devices/browsers

3. **Monitor for issues**:
   - Cold starts? (expected with Render free tier, ~5-10s first request after idle)
   - Data loss? (check Neon logs if issues)
   - Errors in Render logs?

4. **Gather feedback**:
   - Is the app stable?
   - Any feature bugs?
   - Performance acceptable?

---

### Step 7: Validation Checklist (48 hours post-deploy)

- [ ] Web service shows "Live" status
- [ ] Database connected (Alembic migrations ran)
- [ ] Backfill completed successfully (check script output)
- [ ] Can log in with test account
- [ ] Can add/view recipes
- [ ] Can generate menus
- [ ] Pantry persists across sessions
- [ ] Activity log appears in household admin
- [ ] Categories load correctly
- [ ] Menu appears on dashboard
- [ ] No database connection errors in logs
- [ ] No 500 errors in app
- [ ] 3+ test users can use simultaneously

---

## Rollback Plan (If Issues Arise)

If something goes wrong:

1. **Stop deploy**: Pause deployment in Render dashboard
2. **Check logs**: Render → Logs tab (what's the error?)
3. **Rollback**:
   - Git: revert the problematic commit
   - Push to GitHub: `git push`
   - Render auto-redeploys from previous commit
4. **Debug**:
   - Read Render logs
   - SSH into Render shell and inspect database
   - Run `alembic current` to see migration state
   - Run backfill script with `--dry-run` to diagnose

---

## Monitoring (Ongoing)

### Render Logs
- Check weekly for errors
- Monitor for cold start complaints (expected, not a bug)
- Watch for database connection timeouts

### Database
- Neon provides usage metrics in dashboard
- Monitor storage growth (recipes, activity log, etc.)
- Should use <500MB during testing phase

### Upgrades When Needed
- **Render**: Free tier → Paid ($7/mo) when launching to real users
- **Neon**: Free (3GB) → Paid ($14/mo for production guarantees) later
- Or switch to Hetzner VPS (~€3.79/mo) for everything after testing

---

## Next Steps After Validation

1. **If successful**: Release v1.2.0 with database migration
2. **Invite family/friends** to production instance
3. **Monitor for 1+ week** with real usage
4. **Decide**:
   - Keep free tier (Render + Neon free)
   - Upgrade to paid tiers
   - Switch to Hetzner VPS (~€4/mo)

---

## Emergency Contacts

- **Neon Support**: https://neon.tech/docs/support
- **Render Support**: https://render.com/docs
- **App Issues**: Check logs first, debug locally if needed

---

## Timeline Summary

- **Today (2026-07-01)**: Phase 7 begins
- **This week**: Deploy to Render+Neon
- **Week 2**: Test with family/friends (48-72 hours validation)
- **Week 3+**: Production monitoring and feedback
- **2026-07-27**: Railway trial expires (no longer needed!)
