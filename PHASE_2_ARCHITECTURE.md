# Phase 2 Architecture & Setup Guide

**For:** Claude instance starting Phase 2 (PostgreSQL migration)
**Read this before asking clarifying questions about Task 1**

---

## 🗄️ Database Architecture

### Current State (Phase 1)
- **Storage:** JSON files in `data/` folder
- **Files:**
  - `recipes_db.json` - All recipes (10-20 recipes, growing)
  - `sample_recipes.json` - Fallback/sample recipes
  - `weekly_menu.json` - Generated weekly menu (1 per week)
  - `pantry_staples.json` - Ingredient pantry list (235 items)

### Target State (Phase 2)
- **Database:** PostgreSQL (cloud-hosted on Railway)
- **ORM:** SQLAlchemy 2.x (declarative models, type-hinting)
- **Migrations:** Alembic (for version control + rollback)

### Why This Stack?
- **PostgreSQL:** Industry standard, free tier on Railway, scales easily
- **SQLAlchemy:** Type-safe, ORM handles relationships, supports complex queries
- **Alembic:** Auto-generates migration files, tracks schema history, easy rollback

---

## 🏗️ Database Schema (Proposed)

### Core Tables

#### `users`
```sql
id (PK)
email (UNIQUE)
password_hash
created_at
updated_at
```

#### `households`
```sql
id (PK)
name
owner_id (FK → users)
created_at
updated_at
```

#### `household_members`
```sql
id (PK)
household_id (FK → households)
user_id (FK → users)
role (owner|editor|viewer)
joined_at
```

#### `recipes`
```sql
id (PK, UUID)
household_id (FK → households)
title
description
difficulty
time_minutes
category
instructions (JSON or TEXT)
comment
created_at
updated_at
created_by (FK → users)
```

#### `recipe_ingredients`
```sql
id (PK)
recipe_id (FK → recipes)
name
quantity
unit
allergens (JSON array)
```

#### `weekly_menus`
```sql
id (PK, UUID)
household_id (FK → households)
week_start (DATE)
week_end (DATE)
dinners (JSON array of {day, recipe_id})
created_at
```

#### `shopping_lists`
```sql
id (PK, UUID)
household_id (FK → households)
menu_id (FK → weekly_menus)
data (JSON - full shopping list)
created_at
updated_at
```

---

## 🔐 Environment Variables (Database)

### Local Development
Create `.env` file (copy from `.env.example`):
```env
DATABASE_URL=postgresql://postgres:password@localhost:5432/menu_planner_dev
SECRET_KEY=dev-secret-key-change-in-production
FLASK_ENV=development
```

### Railway Production
Set in Railway dashboard (DO NOT commit to repo):
```env
DATABASE_URL=postgresql://user:password@host:5432/menu_planner_prod
SECRET_KEY=<randomly-generated-secret-key>
FLASK_ENV=production
```

**How to get Railway DATABASE_URL:**
1. Create PostgreSQL plugin in Railway
2. Copy "Database URL" from plugin details
3. Paste into Railway environment variables

---

## 🔄 Migration Strategy: Alembic vs Manual

### RECOMMENDATION: Use Alembic

**Why:**
- Auto-generates migration files from model changes
- Tracks migration history (can see what changed when)
- Easy rollback if something breaks
- Industry standard for Flask/SQLAlchemy projects

### Setup (One-Time)
```bash
pip install alembic
alembic init alembic
```

### Create Migration
```bash
# After modifying models.py:
alembic revision --autogenerate -m "Add recipes table"
# Review the generated migration file
alembic upgrade head  # Apply migration
```

### Rollback (If Needed)
```bash
alembic downgrade -1  # Rollback to previous version
```

### For Railway (Production)
```bash
# Before deploying, run:
alembic upgrade head
```

---

## 🌱 Data Seeding Strategy

### Phase 2 Task 1 Requires:
1. Create database schema (via Alembic migrations)
2. Import existing recipes from `recipes_db.json` into database
3. Verify all Phase 1 features still work with DB backend

### Seeding Script (To Create)
```python
# scripts/seed_recipes.py

from pi_deployment.flask_app import app, db
from database.models import Recipe, RecipeIngredient
import json

def seed_recipes():
    with app.app_context():
        # Load recipes_db.json
        with open('data/recipes_db.json', 'r') as f:
            recipes = json.load(f)

        # Create Recipe objects
        for recipe_data in recipes:
            recipe = Recipe(
                id=recipe_data['id'],
                title=recipe_data['title'],
                description=recipe_data.get('description', ''),
                difficulty=recipe_data.get('difficulty', 'Medium'),
                time_minutes=recipe_data.get('time_minutes', 30),
                category=recipe_data.get('category', 'General'),
                instructions=recipe_data.get('instructions', []),
                comment=recipe_data.get('comment', ''),
                household_id=None  # Public recipes (no household owner)
            )
            db.session.add(recipe)

            # Add ingredients
            for ing in recipe_data.get('ingredients', []):
                ingredient = RecipeIngredient(
                    recipe_id=recipe['id'],
                    name=ing.get('name'),
                    quantity=ing.get('quantity', 0),
                    unit=ing.get('unit', '')
                )
                db.session.add(ingredient)

        db.session.commit()
        print(f"Seeded {len(recipes)} recipes")

if __name__ == '__main__':
    seed_recipes()
```

**Run after migration:**
```bash
python scripts/seed_recipes.py
```

---

## 🧪 Testing During Migration

### Phase 1 Features to Test (Must Still Work With DB)

1. **Pantry Filter**
   - Generate menu → check shopping list
   - Verify salt, pepper, garlic, oregano NOT in list
   - Check `logs/deduplicator.log` for filter matches

2. **Recipe Edit**
   - Edit a recipe (change title/ingredients)
   - Save changes
   - Reload recipe page → changes persisted

3. **Checkbox Persistence**
   - Check item in shopping list
   - Refresh page → checkbox still checked
   - Navigate away & back → still checked

4. **Menu Generation**
   - Generate new menu
   - Verify 5 recipes selected (Mon-Fri)
   - Verify shopping list populated
   - No errors in Flask logs

### Test Script (To Create)
```python
# tests/test_phase1_migration.py

import pytest
from pi_deployment.flask_app import app, db
from database.models import Recipe, Household

@pytest.fixture
def client():
    app.config['TESTING'] = True
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()

def test_pantry_filter(client):
    """A0: Pantry items filtered from shopping list"""
    response = client.get('/shopping')
    assert response.status_code == 200
    # Assert salt/pepper/garlic NOT in response
    assert 'salt' not in response.get_data(as_text=True).lower()

def test_recipe_edit(client):
    """A1: Recipe edit endpoint works"""
    response = client.post('/api/edit-recipe', json={
        'recipe_id': 'recipe_001',
        'title': 'New Title',
        'ingredients': []
    })
    assert response.status_code == 200

def test_menu_generation(client):
    """Menu generation still works with DB"""
    response = client.post('/api/generate-menu')
    assert response.status_code == 200
    data = response.get_json()
    assert 'dinners' in data
    assert len(data['dinners']) == 5  # Mon-Fri
```

---

## 📁 File Structure After Migration

```
Menu-Planner/
├── alembic/                    # NEW: Migration files
│   ├── env.py
│   ├── script.py.template
│   └── versions/
│       ├── 001_initial_schema.py
│       ├── 002_add_households.py
│       └── ...
├── database/                   # NEW: Database layer
│   ├── __init__.py
│   ├── models.py              # SQLAlchemy models
│   ├── database.py            # DB connection & session
│   └── seed.py                # Data seeding script
├── scripts/                    # NEW: Utility scripts
│   ├── seed_recipes.py
│   └── backup_json.py
├── pi-deployment/
│   └── flask_app.py           # MODIFIED: Use ORM instead of JSON
├── core/
│   ├── ingredient_deduplicator.py
│   └── recipe_loader.py       # MODIFIED: Load from DB
├── frontend/
│   ├── templates/
│   └── static/
├── data/                       # Still here (for reference/backup)
│   ├── recipes_db.json
│   ├── sample_recipes.json
│   └── pantry_staples.json
├── tests/                      # NEW: Unit tests
│   ├── conftest.py
│   ├── test_phase1_migration.py
│   └── test_auth.py           # For Phase 2 Task 2
├── alembic.ini                # NEW: Alembic config
├── .env.example               # MODIFIED: Add DATABASE_URL
├── requirements.txt           # MODIFIED: Add SQLAlchemy, Alembic
├── PHASE_2_ARCHITECTURE.md    # THIS FILE
└── HANDOFF_PHASE_1_COMPLETE.md
```

---

## 🚀 PostgreSQL Setup (Local Development)

### Option 1: Install PostgreSQL Locally
```bash
# Windows: Download from https://www.postgresql.org/download/windows/
# During install, remember the password for 'postgres' user
psql -U postgres -c "CREATE DATABASE menu_planner_dev;"
```

### Option 2: Use Docker (Easier)
```bash
docker run --name postgres-menu-planner \
  -e POSTGRES_PASSWORD=password \
  -p 5432:5432 \
  -d postgres:15-alpine

# Connect with:
DATABASE_URL=postgresql://postgres:password@localhost:5432/postgres
```

### Verify Connection
```bash
psql $DATABASE_URL -c "\dt"  # Should return empty table list (first time)
```

---

## 🔑 Secret Key Management

### Development
```env
SECRET_KEY=dev-secret-key-change-in-production
```

### Production (Railway)
```bash
# Generate secure secret key:
python -c "import secrets; print(secrets.token_hex(32))"
# Output: a1b2c3d4e5f6... (copy this)
# Paste into Railway environment variable: SECRET_KEY=a1b2c3d4e5f6...
```

**Why?** Flask uses SECRET_KEY for:
- Session signing (prevents tampering)
- CSRF token generation
- Password reset tokens (Phase 2)

---

## 📊 Summary: What Phase 2 Task 1 Does

1. **Create SQLAlchemy models** (`database/models.py`)
   - User, Household, Recipe, RecipeIngredient, etc.
   - Define relationships (User → Household, Recipe → Ingredients)

2. **Set up Alembic** (`alembic/`)
   - Initialize Alembic
   - Create initial migration (creates all tables)

3. **Migrate existing recipes** (`scripts/seed_recipes.py`)
   - Read recipes_db.json
   - Insert into PostgreSQL
   - Verify count matches

4. **Update Flask routes** (`pi-deployment/flask_app.py`)
   - Replace JSON file reads with ORM queries
   - Example: `Recipe.query.all()` instead of `json.load(f)`

5. **Test Phase 1 features** (`tests/test_phase1_migration.py`)
   - Pantry filter still works
   - Menu generation still works
   - Recipes still editable
   - Checkboxes still persist

---

## ✅ Acceptance Criteria for Phase 2 Task 1

- ✅ PostgreSQL running locally (or Docker)
- ✅ SQLAlchemy models created & documented
- ✅ Alembic migrations working (can upgrade/downgrade)
- ✅ Recipes imported from JSON into database
- ✅ All Phase 1 tests pass with DB backend
- ✅ No JSON file reads in Flask routes (all use ORM)
- ✅ `.env.example` includes DATABASE_URL example
- ✅ `requirements.txt` includes sqlalchemy, alembic, psycopg2

---

## 📖 Reference Docs

**For the new Claude instance, read in this order:**

1. `PHASE_2_CATCHUP_PROMPT.md` — Overview of all 5 Phase 2 tasks
2. `PHASE_2_ARCHITECTURE.md` — THIS FILE (detailed architecture)
3. `HANDOFF_PHASE_1_COMPLETE.md` — What Phase 1 built
4. `README.md` — Project overview
5. `00_START_HERE.md` — Getting started guide

---

**Phase 2 Task 1 is ready to go. No more questions needed—just follow this architecture! 🚀**
