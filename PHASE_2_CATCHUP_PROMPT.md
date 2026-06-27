# Phase 2 Catch-Up Prompt (Use This to Start Next Session)

Copy & paste this into a new Claude Code chat to resume the Menu-Planner project for Phase 2:

---

## 🎯 Context & Status

I'm picking up the **Menu-Planner** project for **Phase 2** (Cloud Edition - multi-user SaaS development).

**Current Status:** Phase 1 complete. All tests passing:
- ✅ Pantry filter working
- ✅ Recipe editing with comments
- ✅ Checkbox persistence in shopping list
- ✅ Docker containerization complete

**Project Repo:** `d:\Claude AI Projects\projects\GitHub\Menu-Planner`

### 📚 IMPORTANT: Read These Docs First

Read in this order **before asking any questions:**

1. **`PROJECT_CONTEXT.md`** ⭐ **START HERE** — Complete project overview
   - What is Menu-Planner and how does it work?
   - Architecture, data model, core features
   - How each feature is implemented
   - Project structure and file guide

2. **`HANDOFF_PHASE_1_COMPLETE.md`** — What Phase 1 built and tested
   - Summary of all 4 Phase 1 tasks (A0-A3)
   - Code changes made
   - Local development setup

3. **`PHASE_2_ARCHITECTURE.md`** — Detailed Task 1 architecture (if working on database)
   - PostgreSQL schema design
   - Alembic migration strategy
   - Data seeding approach
   - Environment variables & secrets
   - Testing during migration

---

## 📋 Phase 2 Overview

**Goal:** Transform Menu-Planner into a **multi-user SaaS app** deployable to the cloud (Railway).

**Key Changes:**
- 🗄️ JSON files → PostgreSQL database + SQLAlchemy ORM
- 🔐 Single user → User authentication (Flask-Login + optional MSAL)
- 👥 Single household → Multi-user households/teams
- 🚀 Local server → Cloud deployment (Railway)
- ✅ Manual testing → GitHub Actions CI/CD

**Timeline:** 5 weeks (start: immediately; end: ~5 weeks)

---

## 🛠️ Phase 2 Tasks (In Order)

### Task 1: PostgreSQL + SQLAlchemy Migration (Week 1)
**What:** Migrate data layer from JSON files to PostgreSQL database
**Deliverables:**
- SQLAlchemy models for: Recipe, ShoppingList, Menu, User, Household
- Database migrations (Alembic or manual SQL)
- ORM queries replace all JSON file I/O
- Data seeding (import existing recipes_db.json into database)
- Testing: All existing features still work with DB backend

**Files to Create/Modify:**
- `database/models.py` - New SQLAlchemy models
- `database/database.py` - New DB connection & session management
- `core/recipe_loader.py` - Refactor to load from DB instead of JSON
- `pi-deployment/flask_app.py` - Update all routes to use ORM queries

**Acceptance Criteria:**
- ✅ All Phase 1 features work with PostgreSQL backend
- ✅ Existing recipes loaded into database
- ✅ Shopping list, menu generation, pantry filter all work

---

### Task 2: Flask-Login User Authentication (Week 1-2)
**What:** Add user login system (email/password)
**Deliverables:**
- User model with password hashing (werkzeug)
- Login/logout/signup routes
- Session management (Flask-Login)
- User-specific data (recipes, menus, shopping lists tied to users)
- Optional: MSAL integration for Azure login
- Testing: Create test users, verify authentication flow

**Files to Create/Modify:**
- `database/models.py` - Add User model
- `frontend/templates/login.html` - New login form
- `frontend/templates/signup.html` - New signup form
- `pi-deployment/flask_app.py` - Add auth routes + login_required decorators
- Existing templates - Add "Logout" button, username display

**Acceptance Criteria:**
- ✅ Can sign up with email/password
- ✅ Can log in/log out
- ✅ Unauthenticated users redirected to login
- ✅ User-specific data isolation (can't see other users' recipes)

---

### Task 3: Household/Team Management (Week 2)
**What:** Allow users to create & manage households (share recipes, menus, shopping lists)
**Deliverables:**
- Household model (name, members, owner)
- Household member roles (owner, editor, viewer)
- Invite system (email invites to join household)
- UI: Create household, invite members, view members
- Data scoping: Recipes/menus scoped to household
- Testing: Create household, add members, verify access control

**Files to Create/Modify:**
- `database/models.py` - Add Household, HouseholdMember models
- `frontend/templates/household-settings.html` - New household management UI
- `pi-deployment/flask_app.py` - Add household routes + permission checks
- All recipe/menu routes - Check household membership before returning data

**Acceptance Criteria:**
- ✅ User can create household
- ✅ User can invite other users to household
- ✅ Invited users can accept/decline
- ✅ Multiple members can view/edit same data
- ✅ Non-members cannot access household data

---

### Task 4: Railway Cloud Deployment (Week 3-4)
**What:** Deploy app to Railway (cloud platform)
**Deliverables:**
- Railway account created + project set up
- PostgreSQL database on Railway
- Environment variables configured (DATABASE_URL, SECRET_KEY, etc.)
- GitHub integration (auto-deploy on push)
- Health checks & monitoring
- Custom domain (optional)
- Testing: Smoke test all endpoints on production URL

**Files to Create/Modify:**
- `Procfile` - Web server startup config for Railway
- `.env.example` - Update with Railway config examples
- Documentation: Deployment steps in README

**Acceptance Criteria:**
- ✅ App deployed on Railway
- ✅ Accessible via public URL
- ✅ Database persists data
- ✅ Can sign up → create household → add recipes → generate menus
- ✅ No errors in production logs

---

### Task 5: GitHub Actions CI/CD (Week 4-5)
**What:** Automate testing & deployment
**Deliverables:**
- GitHub Actions workflow for testing
- Linting (flake8 or ruff)
- Unit tests for core modules
- Auto-deployment to Railway on main branch push
- Testing: Push commit → workflow runs → app deploys

**Files to Create:**
- `.github/workflows/ci.yml` - Test & deploy workflow
- `tests/test_*.py` - Unit tests for recipes, shopping lists, auth
- `conftest.py` - Pytest configuration

**Acceptance Criteria:**
- ✅ GitHub Actions workflow passes tests
- ✅ Push to main → auto-deploys to Railway
- ✅ Failed tests block deployment
- ✅ Code coverage >70%

---

## 📚 Key Technologies for Phase 2

| Component | Library | Version |
|-----------|---------|---------|
| Database | PostgreSQL | Latest |
| ORM | SQLAlchemy | 2.x |
| Auth | Flask-Login + werkzeug | Latest |
| Migration | Alembic | 1.x (or manual SQL) |
| Cloud | Railway | N/A |
| CI/CD | GitHub Actions | N/A |
| Testing | pytest | Latest |
| Linting | flake8 / ruff | Latest |

---

## 🔗 Important Files & References

**Phase 1 Handoff:**
`HANDOFF_PHASE_1_COMPLETE.md` — Read this first

**Architecture Docs:**
- `README.md` — Project overview
- `00_START_HERE.md` — Getting started guide
- (Create) `PHASE_2_ARCHITECTURE.md` — DB schema, auth flow, deployment plan

**Local Development:**
```bash
cd "d:\Claude AI Projects\projects\GitHub\Menu-Planner"
.\RUN_LOCAL.ps1        # Start Flask app locally
# App runs on http://localhost:5000
```

**Docker (Alternative):**
```bash
docker build -t menu-planner:latest .
docker run -p 5000:5000 menu-planner:latest
```

---

## ✅ Pre-Phase-2 Checklist

Before starting Phase 2, confirm:
- ✅ Have you read `HANDOFF_PHASE_1_COMPLETE.md`?
- ✅ Can you run the app locally (`.\RUN_LOCAL.ps1` or Docker)?
- ✅ Do you have Python 3.11+, Docker, and Git installed?
- ✅ Is the project in a clean git state (no uncommitted changes)?
- ✅ Do you want to deploy to Railway? (Need free Railway account)

---

## 🎯 What NOT to Do in Phase 2

- ❌ Don't re-test Phase 1 features (they're already working)
- ❌ Don't refactor Phase 1 code unless Phase 2 breaks it
- ❌ Don't add new features beyond the 5 Phase 2 tasks
- ❌ Don't change the HTML/CSS significantly (focus on backend)
- ❌ Don't deploy to production until all 5 tasks are complete

---

## 📞 Questions Before Starting?

If unclear about any Phase 2 task:
1. Ask Claude (me) in the chat
2. Check the handoff document for context
3. Review git log to see what changed in Phase 1
4. Look at existing code structure for patterns

---

## 🚀 Ready to Start?

Once you're ready to begin Phase 2:

**Say:** "Let's start Phase 2. Begin with Task 1: PostgreSQL migration."

I'll:
1. Verify the project state
2. Create the database schema
3. Build SQLAlchemy models
4. Migrate existing recipes to the database
5. Test that all Phase 1 features still work

---

**Good luck with Phase 2! 🎉**
