# Menu Planner — Project Changelog

A complete history of all work done on the project, organised by date and type.
Latest entries at the top.

---

## 2026-07-02

### 📁 Documentation Cleanup
- Deleted outdated files: `DEPLOYMENT.md`, `DEPLOYMENT_STATUS.md`, `RAILWAY_DATABASE_GUIDE.md`, `RECIPE_AUDIT_REPORT_2026-06-30.md`, `BACKLOG_2026-06-30.md`, `docs/SETUP_GUIDE.md`, `docs/FAQ.md`, `docs/EXCEL_GUIDE.md`
- Created `docs/RECIPE_PACK_FORMAT.md` — developer cheatsheet for writing recipe packs (replaces Excel guide)
- Created `CHANGELOG.md` (this file) — unified history of all project work
- Updated `README.md`, `SYSTEM_ARCHITECTURE.md`, `FEATURE_ROADMAP.md`, `BACKLOG_2026-07-01.md`, `new_chat_fresh_menu_planner.md` to reflect Render+Neon deployment

### 📖 In-App Help System
- Added `❓` button in nav bar → opens Quick Start Guide modal
- Quick Start modal rewritten to be warm and welcoming ("No more staring into the fridge...")
- Created `/help/advanced` route + bilingual template (Advanced Guide)
- Created `/help/tips` route + bilingual template (Tips & Tricks)
- All 3 guides fully bilingual — auto-detect language from `pi_language` cookie
- Help section added to ⚙️ settings dropdown
- Advanced Guide: fixed "Kyllingmiddager" → "Chicken Dinners" language mix
- Settings table in USER_GUIDE.md: "Basisvarer" → "Pantry"

### 🌍 User-Facing Guides (docs/)
- Created `docs/USER_GUIDE.md` — beginner guide (English)
- Created `docs/ADVANCED_USER_GUIDE.md` — advanced guide (English)
- Created `docs/TIPS_AND_TRICKS.md` — power user tips (English)

### 🐛 Bug Fixes
- Pantry remove not persisting on Render — was loading/saving from file instead of database
- Settings page was reading pantry and categories from file, bypassing database
- `db.merge()` pattern unreliable for JSONB saves — replaced with fresh query per save
- Menu generator was saving to file — updated to save to `Household.weekly_menu` JSONB
- Menu generator was loading household recipes from file — updated to load from `Household.recipes_db` JSONB
- Sample recipes had `cookTimeMinutes` field but generator was reading `time_minutes` → showed "0 min"
- `_load_pantry_db()` now seeds from file into database on first load (one-time migration)

### ✨ New Features
- "Reset to defaults" button in pantry settings (uses themed `pmConfirm` popup)
- `POST /api/pantry/reset` endpoint — restores full staples list from `pantry_staples.json`
- Real avatar shown in settings dropdown (was showing initials only)
- All 5 unthemed browser `alert()`/`confirm()` popups replaced with `pmAlert`/`pmConfirm`
- Norwegian translation: "Mitt Forråd" → "Basisvarer"

### 🥗 Recipe Changes
- Moved to `sides-stash.json`: Rekesalat, Potet-og-Agurk Salat, Italiensk Salat, Potetsalat, Medisterpølse
- Enhanced Kjøttkaker recipe: added brown gravy, potatoes, carrots, lingonberry as full meal ingredients + step-by-step instructions in NO and EN

---

## 2026-07-01

### 🚀 F4 Hosting Migration — Railway → Render + Neon (COMPLETE)

#### Infrastructure
- Created Neon.tech account (free PostgreSQL 3GB tier)
- Created Render.com web service (free tier, GitHub auto-deploy)
- Domain `menuplanner.no` pointed to Render (A record + CNAME via Cloudflare)
- All environment variables migrated from Railway to Render
- Railway services deleted

#### Database Schema (Phase 1-2)
- Added 7 JSONB columns to `Household` model: `recipes_db`, `pantry`, `weekly_menu`, `categories`, `activity_log`, `removed_categories`, `imported_packs`
- Alembic migration: `f6a7b8c9d0e1_add_jsonb_columns_to_households.py`
- Fixed Alembic multiple heads error (F4 migration was pointing to wrong parent revision)

#### Data Layer (Phase 3-4)
- Added 8 `load_*_from_db()` functions in `core/household_paths.py`
- Added 8 `save_*_to_db()` functions in `core/household_paths.py`
- Created `scripts/backfill_household_data.py` — migrates JSON files → PostgreSQL JSONB

#### Flask Route Refactoring (Phase 5)
- Added `current_household()` helper to get Household ORM object per request
- Added `_load_pantry_db()` / `_save_pantry_db()` wrappers
- All pantry API routes updated to use database
- Menu and recipe loading updated to use database
- Categories loading/saving updated to use database

#### Deployment Fixes (Phase 7)
- Fixed Python 3.14 vs 3.11 conflict (Render defaulted to 3.14, SQLAlchemy incompatible)
- Fixed PATH issue — gunicorn installed to `/opt/render/.local/bin` not on PATH
- Fixed start command to use `python3.11 -m gunicorn`
- Fixed Alembic "multiple heads" error blocking build
- Final working build/start commands documented in `DEPLOYMENT_F4.md`

### 🐛 Bug Fixes
- Admin panel security: profiles could access `/admin` — fixed by checking `active_profile_id`
- Generate menu not redirecting to home page after generation
- Category dropdown in "Add Recipe" page was hardcoded, not dynamic
- CSS selector `option[value!=""]` invalid — changed to `option:not([value=""])`
- API field name mismatch: JS was reading `cat.name_en` but API returns `cat.name`
- Empty categories generating full 6-day menu — now returns 400 error
- Recipe moved to Uncategorized when its category is deleted
- SSL certificate issue on `menuplanner.no` via Cloudflare (DNS + redirect rules fixed)

### ✨ New Features
- v1.1.0 release: all above fixes and F4 migration complete

### 🥗 Recipe Changes
- Moved side dishes out of dinner pool into `sides-stash.json` (running total: 21 sides)
- Recipe quality: 3 recipes with multi-sentence instruction steps fixed

---

## 2026-06-29 / 2026-06-30

### 🏗️ Core App Features Built
- Email confirmation system (signup → email → confirm link → login)
- Password reset via email (forgot password flow)
- Delete own account (Settings danger zone, password confirmation required)
- Admin panel (`/admin`, gated by `ADMIN_EMAIL`, lists and deletes users)
- Unified Favourites system across all pages
- Pantry items shown in collapsible "Already have these" section on shopping list
- Removed servings scaling (users edit recipe ingredient quantities directly instead)
- Netflix-style family profiles (profile picker, avatar, role-based access)
- PIN support for quick profile switching on shared devices
- Referral system (code generation, link sharing, signup attribution)
- Household member management (invite, role assignment, viewer/editor/owner)
- Category management (add, rename, merge, delete with Uncategorized fallback)
- Activity log per household (timestamped, capped at 200, owner-only)

### 🏗️ Infrastructure
- Railway deployment with PostgreSQL
- Alembic migrations (SQLAlchemy ORM)
- SQLite for local dev, PostgreSQL for production
- Cloudflare DNS + SSL for `menuplanner.no`
- Resend email integration (confirmation + password reset)
- GitHub Actions CI/CD (tests, lint, security, build, data validation)
- GitHub Actions auto-sync to Pi (legacy, pre-Render)

### 🥗 Recipe Packs
- 12 dish-type recipe packs live (replaced 5 geographic packs)
- 90 desserts stashed in `dessert-stash.json`
- 4 drinks stashed in `drinks-stash.json`
- 16+ sides stashed in `sides-stash.json`
- 4 new Tex-Mex recipes written (Beef Tacos, Enchiladas, Nachos, Quesadillas)
- Quick Dinners category: 108 recipes tagged `quick`
- Cuisine tags added to all recipes (`cuisine:norwegian`, `cuisine:italian` etc.)
- Sample recipes (`sample_recipes.json`) fully rewritten — old version had wrong ingredients and instructions

### 🎨 UI / UX
- 8 themes (1 hardcoded + 7 registry) — theme switcher in settings dropdown
- Bilingual support (Norwegian + English) with cookie-based language detection
- PWA manifest + service worker (installable on mobile)
- Atomic writes for `recipes_db` (prevents corrupt JSON on crash)
- Pack import upserts (re-importing updates stale data, no duplicates)
- Pack-name pseudo-categories removed from all dropdowns
- Button sizing fixed globally (`btn-primary` no longer forces `width:100%`)
- Second "menu ready" popup removed after regeneration (page reload is enough)

### 🐛 Bug Fixes
- Railway volume freezing static seed data — fixed with `SEED_DIR` separation
- Favorites + category filter bug — now uses union (OR) not intersection (AND)
- Recipe instruction quality: multiple recipes had wrong instructions (copy/paste errors from original writing)

---

## Project Start

- Project started as a Raspberry Pi local meal planner
- Migrated to full web app with user accounts, households, cloud hosting
- Open source at `github.com/nobody174/Menu-Planner`
