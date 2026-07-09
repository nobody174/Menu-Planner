# Menu Planner — System Architecture

Last updated: 2026-07-08

---

## System Overview

Menu Planner is a multi-household meal planning web app that:
1. Manages recipe collections per household (add manually or import recipe packs)
2. Generates 6-dinner weekly menus from selected categories
3. Deduplicates ingredients and produces a shopping list
4. Tracks pantry items to grey out items already at home
5. Sends confirmation and password reset emails

---

## Infrastructure

```
User (browser)
    ↓
Cloudflare (DNS + SSL for menuplanner.no)
    ↓
Render.com (web service — Flask + gunicorn)
    ↓
Neon.tech (PostgreSQL — all household data)
    ↓
Resend.com (transactional email — confirmation + password reset)
```

---

## Database — PostgreSQL (Neon)

SQLAlchemy ORM + Alembic migrations.

### Key Tables

| Table | Purpose |
|---|---|
| `users` | Accounts (email, password hash, referral, PIN, email confirmation) |
| `households` | Family workspaces + all JSONB data columns |
| `household_members` | User ↔ Household roles (owner/editor/viewer) + family profiles |
| `recipes` | Individual recipe rows (currently unused — recipes stored in JSONB) |
| `recipe_ingredients` | Ingredient rows (currently unused — stored in JSONB) |
| `weekly_menus` | Menu rows (currently unused — stored in JSONB) |
| `shopping_lists` | Shopping list rows (currently unused — stored in JSONB) |

### Household JSONB Columns

All active household data lives in JSONB columns on the `households` table:

| Column | Contains |
|---|---|
| `recipes_db` | All household recipes (imported + manually added) |
| `categories` | Category list with codes, names, icons, imported flag |
| `weekly_menu` | Current week's generated menu and shopping list |
| `pantry` | Pantry items as lowercase strings (bilingual) |
| `activity_log` | Timestamped audit entries (capped at 200) |
| `removed_categories` | Tombstone list of deleted category codes |
| `imported_packs` | Display metadata for imported recipe packs |

---

## Backend — Flask (`deployment/`)

App-factory + Flask blueprints (split from a single ~4,700-line
`flask_app.py` during the B57 blueprint split, 2026-07-07): `app_core.py`
holds `create_app()`, shared helpers, and app-wide config (CSRF, rate
limiter, security headers, error handlers); `flask_app.py` is now just the
entry point + blueprint registration; route bodies live in
`deployment/routes/*.py`, one module per area (auth, admin, household,
pantry_category, menu, recipe, recipe_pack).

### Key Route Groups

| Routes | Purpose |
|---|---|
| `/`, `/shopping` | Main pages (menu, shopping list) |
| `/api/regenerate` | Generate new weekly menu |
| `/api/recipe-packs/*` | Import / remove recipe packs |
| `/api/pantry/*` | Add, remove, reset pantry items |
| `/api/categories/*` | Add, rename, merge, delete categories |
| `/api/add-recipe`, `/api/edit-recipe`, `/api/delete-recipe` | Recipe CRUD |
| `/help/advanced`, `/help/tips` | In-app help guides |
| `/login`, `/signup`, `/logout`, `/confirm-email`, `/reset-password` | Auth flows |
| `/settings`, `/household-settings` | Settings pages |
| `/admin` | Admin panel (ADMIN_EMAIL gated) |

### Key Helpers

| Function | Purpose |
|---|---|
| `current_household_id()` | Resolves active household from session |
| `current_household()` | Returns Household ORM object from DB |
| `_load_pantry_db()` | Loads pantry from JSONB (seeds from file first time) |
| `_save_pantry_db()` | Saves pantry to JSONB via fresh DB session |
| `_load_household_categories()` | Loads categories from JSONB |
| `_save_household_categories()` | Saves categories to JSONB |
| `load_menu()` | Loads weekly menu from JSONB |
| `load_recipes_db()` | Loads recipes from JSONB |
| `save_recipes_db()` | Saves recipes to JSONB |

---

## Core Modules

### `core/menu_generator.py`
- Loads recipes from household JSONB + shared `sample_recipes.json`
- Filters by selected categories
- Deduplicates recently served recipes (avoids repeats)
- Balances protein types across the week
- Picks 6 recipes randomly from filtered pool
- Saves generated menu to `Household.weekly_menu` JSONB

### `core/household_paths.py`
- Database-backed load/save functions for all JSONB columns
- File-based fallbacks for local dev
- Self-heal logic for categories (adds new base categories, never re-adds deleted ones)
- Bilingual pantry pairing (`pantry_staples.json` translations)
- `removed_categories` tombstone system

### `core/ingredient_deduplicator.py`
- Fuzzy-matches ingredient names across recipes (90%+ similarity)
- Aggregates quantities
- Categorises by type (proteins, veg, dairy etc.)
- Produces structured shopping list

### `core/auth_helpers.py`
- User creation, authentication, email confirmation
- Password reset token generation
- PIN hashing (bcrypt)
- Account deletion (cascades through household, members, data)

---

## Frontend

### Static files (`frontend/static/`)

| File | Purpose |
|---|---|
| `app.js` | Main application logic (menu generation, recipe management, UI interactions) |
| `style.css` | Base styles |
| `i18n.json` | All translations (NO + EN, keyed as `key_no` / `key_en`) |
| `language-manager.js` | Language detection + switching via cookie |
| `measurements.js` | Metric ↔ imperial conversion |
| `themes/` | 8 themes (CSS custom properties) + theme switcher |
| `manifest.json` | PWA manifest |
| `sw.js` | Service worker (offline support) |

### Templates (`frontend/templates/`)

Jinja2 HTML templates. `base.html` contains the nav bar, settings dropdown, help modal, and all shared JS.

---

## Recipe Data

### Recipe Packs (`data/recipe-packs/`)
12 JSON packs, imported on demand per household. Each pack has `pack_id`, `display_name`, `icon`, `color`, and a `recipes` array.

### Stashed Recipes (not in menus)
| File | Contents |
|---|---|
| `data/sides-stash.json` | 21 side dishes (potatoes, salads, breads etc.) |
| `data/dessert-stash.json` | 90 dessert recipes |
| `data/drinks-stash.json` | 4 drink recipes |

### Seed Data (`data-seed/` or `data/`)
| File | Purpose |
|---|---|
| `sample_recipes.json` | 10 shared base recipes visible to all households |
| `categories.json` | Base category list (self-healed into households) |
| `pantry_staples.json` | ~100 bilingual EN↔NO staple pairs |

---

## Authentication & Security

- Passwords hashed with `pbkdf2:sha256` (werkzeug)
- Email confirmation required before login
- Password reset via one-time token (1 hour expiry)
- Session cookies with `SECRET_KEY`
- Role-based access: owner / editor / viewer
- Profile picker with optional PIN (prevents accidental changes by kids etc.)
- Admin panel gated by `ADMIN_EMAIL` env var

---

## Email — Resend

Transactional emails only:
- **Signup confirmation** — user must click link to activate account
- **Password reset** — one-time link, expires in 1 hour

No marketing emails, no scheduled emails.

---

## CI/CD — GitHub Actions

| Workflow | Runs on | Checks |
|---|---|---|
| `tests.yml` | Push / PR | Unit tests |
| `lint.yml` | Push / PR | Black, flake8, pylint, isort |
| `security.yml` | Push / PR | Bandit, Safety, CodeQL |
| `build.yml` | Push / PR | Cross-platform dependency install |
| `frontend-checks.yml` | Push / PR | HTML, CSS, i18n coverage |
| `data-validation.yml` | Push / PR | JSON validity, recipe structure |
| `release.yml` | Version tags | Release creation |

Auto-deploy to Render triggers on every push to `public-release-v1` branch via GitHub webhook.

---

## Local Development

```bash
# Uses SQLite automatically when DATABASE_URL is not set
python -m flask --app deployment.flask_app run --debug
```

SQLite DB: `menu_planner.db` in project root.
Alembic migrations apply to both SQLite (dev) and PostgreSQL (prod).
