# Menu-Planner Cloud Deployment Guide

**Phase 2 Task 4: Railway Cloud Deployment**

This guide explains how to deploy Menu-Planner to Railway (a cloud platform for deploying apps).

---

## Prerequisites

1. **GitHub Account** - Required to link your repository to Railway
2. **Railway Account** - Free tier available at https://railway.app
3. **PostgreSQL Database** - Railway provides this as a plugin

---

## Deployment Steps

### Step 1: Create Railway Project

1. Go to https://railway.app
2. Sign in or create account
3. Create a new project: **New Project** → **Deploy from GitHub repo**
4. Select your Menu-Planner GitHub repository
5. Authorize Railway to access your repo

### Step 2: Add PostgreSQL Database

1. In Railway project dashboard, click **+ Add Service**
2. Select **Database** → **PostgreSQL**
3. Railway will create a PostgreSQL instance automatically
4. Note the `DATABASE_URL` connection string (auto-injected into environment)

### Step 3: Configure Environment Variables

In Railway dashboard, set these environment variables:

| Variable | Value | Required |
|----------|-------|----------|
| `FLASK_ENV` | `production` | Yes |
| `FLASK_SECRET_KEY` | Generate: `python -c "import secrets; print(secrets.token_hex(32))"` | Yes |
| `DATABASE_URL` | Auto-provided by PostgreSQL plugin | Auto |
| `HOUSEHOLD_NAME` | Your family/household name | No (default: Family) |
| `AZURE_CLIENT_ID` | Your Azure app ID (if using MSAL) | No |
| `AZURE_CLIENT_SECRET` | Your Azure app secret | No |
| `AZURE_TENANT_ID` | Your Azure tenant ID | No |
| `AZURE_REDIRECT_URI` | `https://your-railway-domain.com/callback` | No |

**Tip:** Railway automatically generates `DATABASE_URL` from the PostgreSQL plugin. You only need to set `FLASK_SECRET_KEY` and `FLASK_ENV`.

### Step 4: Deploy

1. Railway automatically deploys when you push to GitHub (if GitHub integration enabled)
2. Or manually trigger: Click **Deploy** in Railway dashboard
3. Watch logs in Railway dashboard to verify deployment succeeds
4. Once healthy, get your public URL from Railway dashboard

### Step 5: Initial Setup

After first deployment:

1. Open your Railway URL in browser
2. You'll be redirected to login page (since no users exist yet)
3. Click **Sign Up** to create first user
4. Create a household
5. Start using Menu-Planner!

---

## Post-Deployment Tasks

### Database Migrations

The Flask app automatically runs migrations on startup via Alembic. The `DATABASE_URL` is used automatically.

If migrations fail:
1. Check Railway logs: **Logs** tab in dashboard
2. Verify `DATABASE_URL` is correct
3. Manually run: `alembic upgrade head` (if SSH access available)

### Custom Domain (Optional)

1. In Railway project settings, add **Custom Domain**
2. Point your domain's DNS to Railway's nameservers
3. Update `AZURE_REDIRECT_URI` if using MSAL

### Monitoring & Logs

1. **Railway Dashboard** → **Logs** tab
2. See real-time Flask logs
3. Look for errors, warnings, startup issues

### Scaling

Railway free tier includes:
- 500 MB RAM per service
- 1 GB database storage
- Shared CPU

For production scale:
1. Upgrade Railway plan
2. Increase worker count in `Procfile` or `railway.toml`
3. Scale PostgreSQL as needed

---

## Troubleshooting

### App crashes on startup

**Check logs:** Railway dashboard → Logs tab

**Common issues:**
- `DATABASE_URL` not set → Add to Railway environment variables
- `FLASK_SECRET_KEY` missing → Generate and set in environment
- Port binding failed → Railway handles PORT env var automatically

### Database connection fails

**Solutions:**
1. Verify `DATABASE_URL` in Railway environment
2. Check PostgreSQL plugin is running (green status)
3. Restart app: Railway dashboard → **Restart** button
4. Run migrations manually if needed

### Login not working

**Check:**
1. Database has users table (run migrations)
2. Sessions are working (check cookies in browser)
3. `FLASK_SECRET_KEY` is set and consistent (don't change after deploy)

### MSAL/Azure login not working

**Verify:**
1. `AZURE_REDIRECT_URI` points to your Railway domain
2. Azure app registration has correct redirect URI
3. `AZURE_CLIENT_ID`, `AZURE_CLIENT_SECRET`, `AZURE_TENANT_ID` all set

---

## Local Development vs Production

| Aspect | Local | Production |
|--------|-------|-----------|
| Database | SQLite (default) | PostgreSQL |
| Environment | `development` | `production` |
| Secret Key | Auto-generated | Set explicitly |
| Cookies | Non-secure | Secure (HTTPS) |
| Debug | True (dev) | False |
| Workers | 1 (Flask dev) | 4 (Gunicorn) |

### Running locally before deploy:

```bash
# Install dependencies
pip install -r requirements.txt

# Set up .env
cp .env.example .env
# Edit .env with local PostgreSQL URL or leave SQLite default

# Run migrations
alembic upgrade head

# Start Flask dev server
python pi-deployment/flask_app.py

# Or run with Gunicorn (mimics production):
gunicorn --workers 1 --bind 0.0.0.0:5000 pi_deployment.flask_app:app
```

---

## Docker Alternative (Local Testing)

Test your Dockerfile locally before deploying:

```bash
# Build image
docker build -t menu-planner:latest .

# Run container with env vars
docker run -p 5000:5000 \
  -e DATABASE_URL="postgresql://..." \
  -e FLASK_SECRET_KEY="your-key" \
  -e FLASK_ENV=production \
  menu-planner:latest

# Access at http://localhost:5000
```

---

## Rollback & Troubleshooting

### Rollback deployment

If something breaks after deploy:

1. Railway dashboard → **Deployments** tab
2. Find previous working deployment
3. Click **Redeploy** next to it
4. Railway will re-deploy that version

### Check deployment status

1. **Railway dashboard** → **Deployments** tab
2. Green = successful, Red = failed
3. Click deployment to see logs

### Reset database (⚠️ WARNING)

**This deletes all data.** Only do this for testing:

1. Railway dashboard → PostgreSQL plugin → **Delete**
2. Click **+ Add Service** → **Database** → **PostgreSQL**
3. Deploy again (migrations will recreate schema)
4. Recreate test users/households

---

## Security Checklist

Before going live:

- ✅ `FLASK_SECRET_KEY` is strong and random
- ✅ `FLASK_ENV=production` is set
- ✅ `DATABASE_URL` uses PostgreSQL (not SQLite)
- ✅ HTTPS is enabled (Railway provides by default)
- ✅ Cookies are secure (`SESSION_COOKIE_SECURE=True` in production)
- ✅ Azure redirect URI matches your domain (if using MSAL)
- ✅ No `.env` file committed to Git
- ✅ Regular backups of PostgreSQL data

---

## Getting Help

- **Railway docs:** https://docs.railway.app
- **Flask deployment:** https://flask.palletsprojects.com/en/2.3.x/deploying/
- **PostgreSQL:** https://www.postgresql.org
- **GitHub issues:** Report bugs in your repo

---

**Deployment Ready! 🚀**
