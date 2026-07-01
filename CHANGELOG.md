# Menu Planner — Project Changelog

Complete history of all work done on the project, newest first.
See `BACKLOG_2026-07-01.md` for open tasks and `FEATURE_ROADMAP.md` for planned features.

---

## 2026-07-02

### 📁 Documentation Cleanup
- Deleted outdated files: `DEPLOYMENT.md`, `DEPLOYMENT_STATUS.md`, `RAILWAY_DATABASE_GUIDE.md`, `RECIPE_AUDIT_REPORT_2026-06-30.md`, `BACKLOG_2026-06-30.md`, `docs/SETUP_GUIDE.md`, `docs/FAQ.md`, `docs/EXCEL_GUIDE.md`
- Created `docs/RECIPE_PACK_FORMAT.md` — developer cheatsheet for writing recipe packs
- Created `CHANGELOG.md` (this file) — unified history of all project work
- Updated `README.md`, `SYSTEM_ARCHITECTURE.md`, `FEATURE_ROADMAP.md`, `BACKLOG_2026-07-01.md`, `new_chat_fresh_menu_planner.md`, `docs/DEVELOPER_GUIDE.md`

### 📖 In-App Help System
- Added `❓` button in nav bar → opens Quick Start Guide modal (bilingual, warm and friendly tone)
- Created `/help/advanced` and `/help/tips` routes + bilingual templates
- All 3 guides auto-detect language from `pi_language` cookie
- Help section added to ⚙️ settings dropdown
- Fixed language mixing in guides ("Kyllingmiddager" → "Chicken Dinners", "Basisvarer" → "Pantry" in English)
- Quick Start modal rewritten with warmer tone ("No more staring into the fridge...")

### 🌍 User-Facing Guides Created
- `docs/USER_GUIDE.md` — beginner guide (English)
- `docs/ADVANCED_USER_GUIDE.md` — advanced guide (English)
- `docs/TIPS_AND_TRICKS.md` — power user tips (English)

### 🐛 Bug Fixes
- Pantry remove not persisting — settings page was reading from file, bypassing database
- `db.merge()` unreliable for JSONB saves — replaced with fresh query per save in all routes
- Menu generator saving to file — updated to save to `Household.weekly_menu` JSONB
- Menu generator loading recipes from file — updated to load from `Household.recipes_db` JSONB
- Sample recipes showing "0 min" — generator read `time_minutes` but field is `cookTimeMinutes`
- `_load_pantry_db()` now seeds from file into database on first load (one-time migration trigger)

### ✨ Improvements
- "Reset to defaults" button in pantry settings
- `POST /api/pantry/reset` endpoint
- Real avatar shown in settings dropdown (was showing initials only)
- All 5 unthemed `alert()`/`confirm()` popups replaced with `pmAlert`/`pmConfirm`
- Norwegian translation: "Mitt Forråd" → "Basisvarer"

### 🥗 Recipe Changes
- Moved to `sides-stash.json`: Rekesalat, Potet-og-Agurk Salat, Italiensk Salat, Potetsalat, Medisterpølse
- Enhanced Kjøttkaker: added full meal (brown gravy, potatoes, carrots, lingonberry) with step-by-step instructions in NO + EN

---

## 2026-07-01

### 🚀 F4 Hosting Migration — Railway → Render + Neon (COMPLETE)

**Why:** Railway free trial expiring ~2026-07-27. Household data was in JSON files on Railway's ephemeral volume — every other host would lose data on deploy.

#### Infrastructure
- Created Neon.tech PostgreSQL account (free 3GB tier)
- Created Render.com web service (free tier, GitHub auto-deploy)
- Domain `menuplanner.no` pointed to Render via Cloudflare (A record + CNAME)
- All environment variables migrated from Railway to Render
- Railway services deleted

#### Database Schema
- Added 7 JSONB columns to `Household` model: `recipes_db`, `pantry`, `weekly_menu`, `categories`, `activity_log`, `removed_categories`, `imported_packs`
- Alembic migration: `f6a7b8c9d0e1_add_jsonb_columns_to_households.py`
- Fixed Alembic multiple heads error (F4 migration pointed to wrong parent)

#### Data Layer
- Added 8 `load_*_from_db()` + 8 `save_*_to_db()` functions in `core/household_paths.py`
- Created `scripts/backfill_household_data.py` — migrates JSON files → PostgreSQL JSONB
- Self-heal logic preserved for categories (never re-adds deleted categories)

#### Flask Refactoring
- Added `current_household()` helper to get Household ORM object per request
- Added `_load_pantry_db()` / `_save_pantry_db()` wrappers
- All pantry, menu, recipe, category routes updated to use database

#### Deployment Challenges Solved
- Render defaulted to Python 3.14 — SQLAlchemy 2.0.x incompatible → forced Python 3.11 via build command
- gunicorn not in PATH at runtime → used `python3.11 -m gunicorn`
- Alembic "multiple heads" blocked build → fixed migration chain
- `db.merge()` on detached objects unreliable → replaced with fresh session queries

### 🐛 Bug Fixes
- Admin panel security: family profiles could access `/admin` — fixed by checking `active_profile_id`
- Generate menu not redirecting to home page after generation
- Category dropdown in "Add Recipe" was hardcoded — made dynamic via `/api/categories`
- CSS selector `option[value!=""]` invalid — fixed to `option:not([value=""])`
- Empty categories still generating 6-day menu — now returns 400 error
- Recipe moves to Uncategorized when its category is deleted (not lost)
- SSL certificate issue on `menuplanner.no` — fixed DNS + Cloudflare redirect rules

### ✨ New Features
- v1.2.0 release tagging all above work
- Favourites + categories now use union (OR), not intersection (AND)

### 🥗 Recipe Changes
- Recipe audit: 3 recipes had multi-sentence instruction steps — all fixed
- `tex_001` (Beef Tacos), `tex_002` (Chicken Enchiladas), `sum_027` (Poke Bowl) fixed

---

## 2026-06-30

### 🥗 Recipe Pack Rework (Preload3)
- Replaced 5 geographic packs with 12 dish-type packs (Norwegian, Italian, Tex-Mex, Grill, Salads, Summer, Holiday, Fish & Seafood, Ground Meat & Sausages, Quick Dinners, Pasta & Noodles, Vegetarian)
- 4 new Tex-Mex recipes written: Beef Tacos, Chicken Enchiladas, Nachos, Quesadillas
- 90 desserts + 4 drinks + 16 sides removed from dinner pool and stashed
- Quick Dinners now a real category (108 recipes tagged `quick`)
- Pack-name pseudo-categories removed from all dropdowns
- Cuisine tags added to all recipes (`cuisine:norwegian`, `cuisine:italian` etc.)
- Pack import now upserts (re-importing updates stale data, no duplicates)

### 🐛 Bug Fixes
- Railway volume freezing static seed data — fixed with `SEED_DIR` separation
- Button sizing: `btn-primary` was forcing `width:100%` globally — fixed
- Second "menu is ready" popup removed after regeneration (page reload is enough)
- Hide cuisine/quick filter tags from UI (internal only)
- Sample recipes `sample_recipes.json` fully rewritten — original had wrong ingredients and instructions (copy/paste errors from original writing)

---

## 2026-06-29

### ✨ Features
- Email confirmation system (signup → email → confirm link → login gating)
- Unified Favourites system across all recipe pages
- Pantry items shown in collapsible "Already have these" section on shopping list
- Removed servings scaling (too confusing — users edit recipe quantities directly)
- Recipe expansion: +151 recipes across 5 packs (368 total), all bilingual

### 🐛 Bug Fixes
- Railway persistent volume permission denied error — fixed
- CI test isolation bug causing random failures — fixed
- Atomic writes for `recipes_db.json` (prevents corrupt JSON on crash)

---

## 2026-06-28

### ✨ Features
- Welcome/demo landing page for non-logged-in visitors
- Referral system (code generation, link sharing, signup attribution)
- Phase 3: Referral tracking, co-owner role, profile management, data isolation
- Avatar sync between nav bar and profile picker

### 🐛 Bug Fixes
- `debug=True` accidentally left on in production entry point — fixed
- Flask route reference error in `base.html` — fixed
- Settings page locked down for non-owners (profiles can't change household settings)

---

## 2026-06-27

### 🏗️ Phase 2 — Cloud SaaS Platform (all tasks in one day)

**Task 1 — Database layer**
- SQLAlchemy ORM + Alembic migrations set up
- SQLite (local dev) + PostgreSQL (production) both supported
- Models: `User`, `Household`, `HouseholdMember`, `Recipe`, `RecipeIngredient`, `WeeklyMenu`, `ShoppingList`

**Task 2 — User authentication**
- Email/password signup and login
- Password hashing (pbkdf2:sha256)
- Flask-Login session management

**Task 3 — Household management**
- Role-based access: owner / editor / viewer
- Multiple users per household
- Household switching in session

**Task 4 — Railway cloud deployment**
- Railway.json config
- Procfile for gunicorn
- Python 3.11 specified
- PostgreSQL plugin connected
- Healthcheck endpoint added

**Task 5 — GitHub Actions CI/CD**
- `tests.yml`, `lint.yml`, `security.yml`, `build.yml`, `frontend-checks.yml`, `data-validation.yml`, `release.yml`
- Pre-commit hooks for secret detection

**Phase 3 — Netflix-style family profiles**
- Profile picker (like Netflix — choose who's using the app)
- Avatar system (emoji + custom)
- PIN support for quick profile switching
- Alembic migration: profile fields on `HouseholdMember`
- Alembic startup loop fix (stamp pre-existing schema before upgrade)

### 🐛 Bug Fixes (day full of Railway deployment fixes)
- Duplicate `/health` route crashing gunicorn at boot — fixed
- `users` table missing in Postgres (models not imported before `create_all()`) — fixed
- Login form missing `action` attribute — fixed
- Household name showing literal `{Family_Name}` placeholder — fixed
- `fix end of file` and multiple small CI fixes

### ✨ Other
- Docker support added
- Shopping list checkboxes with localStorage persistence
- Recipe edit endpoint (`/api/edit-recipe`)
- Pantry staples filter fixed (correct JSON keys)
- Pantry staples expanded (Norwegian sugar types, powdered sugar)
- Phase 1 complete: recipe edit UI, comment field persistence, improved deduplication

---

## 2026-06-19

### 🎨 Theme Work
- 8 themes finalised (1 hardcoded + 7 registry)
- Chalkboard Bistro theme: black text enforcement fixes
- Nordic Pantry → Chalkboard → Terracotta → Warm Modern ordering
- Theme submenu toggle fixes
- Pre-commit security hooks for secret detection
- Patreon links updated to direct Menu Planner post

---

## 2026-06-17

### ✨ Features
- Shopping list integrations: Microsoft To Do, Todoist, TickTick, Apple Reminders, CSV/JSON/Text/ICS export
- Complete bilingual system overhaul
- Shopping list management features

---

## 2026-06-16

### ✨ v1.1 Features
- Recipe Pack Import UI (pack selection modal, one-click import, manage imported packs)
- 72+ bilingual recipes across 5 curated packs
- Personal Recipe Arsenal (export/import JSON packs)
- Feature roadmap added
- Default language changed to English
- Testing guide for v1.1

---

## 2026-06-15

### 🚀 v1.0 Public Release (Pi-Menu)

**The original Raspberry Pi local meal planner.**

Built in a single day across 10 phases:

| Phase | What Was Built |
|-------|---------------|
| 1 | Remove scrapers, set up clean project structure |
| 2 | Remove hardcoded credentials, create `.env` template |
| 3 | Update file headers, remove HelloFresh references |
| 4 | Replace scraped HelloFresh recipes with public sample recipes |
| 5 | Dynamic category system |
| 6 | Parameterise family name (no hardcoded references) |
| 7 | Bilingual support (Norwegian + English, persistent toggle) |
| 8 | Measurement conversion system (metric ↔ imperial) |
| 9 | Comprehensive documentation + guides |
| 10 | Final release — Pi-Menu v1.0 Public |

**Autonomous improvement passes:**
- Phase 1: Enhanced tooling + testing suite
- Phase 2: UI/UX improvements + developer documentation
- API endpoint testing suite added

---

## 2026-06-14

### 🌱 Project Start

**Initial Pi-Menu commit — core features ready for deployment.**

The project started as a local Raspberry Pi meal planner with:
- Weekly menu generation from a local recipe JSON file
- Shopping list with ingredient deduplication
- Norwegian UI (hardcoded)
- HelloFresh-scraped recipes (later replaced with public recipes)
- Single-household, single-user design
- Flask running locally on Pi at port 5000

This was the starting point. Everything above describes the journey from a Pi-only local tool to a full cloud-hosted multi-household web app at **menuplanner.no**.
