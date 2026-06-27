# Phase 2 Task 1 Complete: Database Layer Setup

**Status:** ✅ COMPLETE
**Date:** 2026-06-27
**Commit:** 5f3eb54

---

## Summary

Phase 2 Task 1 establishes the database foundation for multi-user SaaS development. The app now has SQLAlchemy models, Alembic migrations, and database infrastructure ready for authentication and household management tasks.

**Key Achievement:** Database layer is decoupled from recipe I/O, allowing Phase 2 features (auth, households, multi-tenancy) to be built independently of recipe data migration.

---

## What Was Built

### 1. SQLAlchemy Models (`database/models.py`)

Created 7 models for multi-user functionality:

| Model | Purpose |
|-------|---------|
| `User` | User account with email & password hash |
| `Household` | Team/household owned by a user |
| `HouseholdMember` | Member of a household with role (owner/editor/viewer) |
| `Recipe` | Recipe scoped to household (NULL = public) |
| `RecipeIngredient` | Ingredients for each recipe |
| `WeeklyMenu` | Generated weekly menu per household |
| `ShoppingList` | Shopping list per household/menu |

**Key Features:**
- All IDs use String(36) for SQLite/PostgreSQL compatibility
- UUIDs auto-generated on insert
- Foreign key relationships properly scoped
- JSON columns for flexible data (instructions, allergens, dinners)
- Timestamps on all tables (created_at, updated_at)

### 2. Database Layer (`database/database.py`)

Singleton Database class with:
- SQLAlchemy engine + SessionLocal factory
- Support for both SQLite (dev) and PostgreSQL (prod)
- `create_all()` and `drop_all()` for easy schema management
- Environment variable-based configuration

### 3. Alembic Migrations (`alembic/`)

- Initialized Alembic with `generic` template
- Created initial migration: `d0d40b4db7ac_initial_schema_users_households_recipes_menus`
- Configured `alembic/env.py` to use SQLAlchemy models for autogenerate
- Database URL read from `DATABASE_URL` env var or defaults to SQLite

**How to Use:**
```bash
# After modifying models.py, generate migration:
alembic revision --autogenerate -m "Your description"

# Apply migration:
alembic upgrade head

# Rollback (if needed):
alembic downgrade -1
```

### 4. Environment Configuration (`.env`)

```env
FLASK_ENV=development
FLASK_SECRET_KEY=dev-secret-key-change-in-production
DATABASE_URL=sqlite:///menu_planner.db
```

### 5. Dependencies (`requirements.txt`)

Added:
- `sqlalchemy==2.0.23` - ORM with type hints
- `psycopg2-binary==2.9.9` - PostgreSQL driver
- `alembic==1.13.1` - Migration tool
- `flask-login==0.6.3` - User session management
- `werkzeug==3.0.1` - Password hashing + security

---

## Current State

### ✅ What Works

- Flask app initializes database on startup
- Alembic migrations can be created/applied
- All 7 models defined and schema-ready
- SQLite database (`menu_planner.db`) created on first run
- Schema supports multi-user features (users, households, roles)

### ⏳ What's Deferred

**Recipe Migration to Database**
- Currently recipes still live in `data/recipes_db.json`
- Flask app still reads/writes recipes from JSON (Phase 1 compatible)
- Recipe migration script (`scripts/seed_recipes.py`) exists but deferred
- Reason: Recipes have complex bilingual structure + existing code handles this well. Will migrate after Phase 2 Task 2 (auth) so we can assign recipes to households/users properly.

### Phase 1 Features Status

- ✅ Pantry filter - **Still works** (uses JSON recipes)
- ✅ Recipe editing - **Still works** (JSON-backed)
- ✅ Checkbox persistence - **Still works** (localStorage)
- ✅ Menu generation - **Still works** (generates from JSON recipes)

---

## Architecture Decision: Phased Migration

Instead of migrating all data at once, we're doing a **phased approach**:

**Phase 2 Task 1 (Now):**
- ✅ Create database models & schema
- ✅ Keep recipes in JSON (no disruption)
- ✅ Database ready for user/household data

**Phase 2 Task 2 (Next):**
- Add user authentication (login/signup)
- Create household management UI
- Database stores users + households only

**Phase 2 Task 3:**
- Scope recipes to households
- Migrate recipes from JSON → Database
- Update menu generation to use household recipes

**Benefits:**
- Lower risk: Don't break Phase 1 while adding auth
- Clearer separation: Auth & households first, then data scoping
- Easier testing: Can test each feature independently

---

## Testing Performed

### ✅ Syntax & Import Tests
- Flask app syntax valid (no parse errors)
- Database models import cleanly
- Alembic env.py configured correctly

### ✅ Migration Tests
- `alembic revision --autogenerate` creates migration
- `alembic upgrade head` applies all migrations
- SQLite database created successfully
- Schema includes all 9 tables (7 models + relationships)

### ✅ Flask Integration
- Database initializes on Flask app startup
- No import errors during app init
- `.env` file loaded correctly

---

## File Structure After Task 1

```
Menu-Planner/
├── alembic/                    # NEW: Migration tracking
│   ├── env.py                  # Database connection config
│   ├── versions/
│   │   └── d0d40b4db7ac_*.py   # Initial schema
│   └── script.py.mako
├── database/                   # NEW: ORM layer
│   ├── __init__.py
│   ├── database.py             # SQLAlchemy + session management
│   └── models.py               # 7 SQLAlchemy models
├── scripts/                    # NEW: Utility scripts
│   └── seed_recipes.py         # Recipe → DB migration (deferred)
├── pi-deployment/
│   └── flask_app.py            # MODIFIED: Initialize db on startup
├── data/                       # UNCHANGED: Still uses JSON
│   ├── recipes_db.json
│   ├── weekly_menu.json
│   └── pantry_staples.json
├── alembic.ini                 # NEW: Alembic config
├── .env                        # NEW: Environment variables
├── requirements.txt            # MODIFIED: Added DB dependencies
└── .gitignore                  # UNCHANGED
```

---

## Next Steps: Phase 2 Task 2

Phase 2 Task 2 will:
1. Add Flask-Login middleware for session management
2. Create User model (already exists, needs routes)
3. Create login/signup pages & routes
4. Add password hashing with werkzeug
5. Implement `@login_required` decorators
6. Create household creation UI

**Ready to Start?** All database infrastructure is in place. Task 2 can now focus entirely on auth logic without worrying about database setup.

---

## Troubleshooting

### "ModuleNotFoundError: No module named 'database'"
**Solution:** Run from project root, ensure dependencies installed:
```bash
pip install -r requirements.txt
```

### Alembic migration fails
**Solution:** Ensure `DATABASE_URL` env var is set correctly:
```bash
# For SQLite:
export DATABASE_URL=sqlite:///menu_planner.db

# For PostgreSQL:
export DATABASE_URL=postgresql://user:password@localhost/menu_planner_dev
```

### Database tables not created
**Solution:** Migrations were skipped. Run:
```bash
alembic upgrade head
```

---

## Git Commit Reference

```bash
git show 5f3eb54  # View all changes made in Task 1
```

---

**Status: Ready for Phase 2 Task 2 (User Authentication)** 🚀
