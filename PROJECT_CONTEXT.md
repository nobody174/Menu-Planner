# Menu-Planner: Complete Project Context

**READ THIS FIRST** before starting any work or asking questions.

This document provides complete context about what the Menu-Planner project is, how it works, and what's been done so far.

---

## 🎯 What Is Menu-Planner?

A **weekly meal planning web application** built with Flask that helps households plan meals for the week and generate shopping lists.

**Current Status:** Phase 1 complete (working locally), Phase 2 in progress (cloud migration)

**Users:** Currently single-user (anonymous), will become multi-user SaaS in Phase 2

---

## 🏗️ Architecture Overview

### Frontend
- **Framework:** Flask + Jinja2 templates
- **Styling:** Custom CSS with theme switching (8 themes)
- **Language:** English & Norwegian (i18n)
- **Special Features:**
  - PWA (Progressive Web App) with service workers
  - localStorage for client-side state
  - Theme management (warm, cool, terracotta, etc.)

### Backend
- **Framework:** Flask (Python)
- **Language Detection:** Based on browser/query param
- **Data Storage (Phase 1):** JSON files in `data/`
- **Data Storage (Phase 2):** PostgreSQL + SQLAlchemy ORM
- **Core Features:**
  - Recipe database management
  - Menu generation algorithm (5 recipes/week with protein variety)
  - Shopping list deduplication + pantry filtering
  - Ingredient fuzzy matching

### Database (Current)
- **Type:** JSON files (single-tenant)
- **Files:**
  - `recipes_db.json` - All recipes (15-20 recipes)
  - `sample_recipes.json` - Fallback recipes
  - `weekly_menu.json` - Latest generated menu
  - `pantry_staples.json` - Pantry items (235 items, EN + NO)
- **Limitations:** No user data isolation, no transactions, manual backups

### Database (Coming in Phase 2)
- **Type:** PostgreSQL (multi-tenant)
- **ORM:** SQLAlchemy 2.x
- **Migrations:** Alembic
- **Tables:** Users, Households, Recipes, RecipeIngredients, WeeklyMenus, ShoppingLists

---

## 📊 Current Data Model (Phase 1)

### Recipe Object
```json
{
  "id": "recipe_001",
  "title": "Beef Bourguignon",
  "subtitle": "French beef stew",
  "category": "Meat & Fish",
  "difficulty": "Medium",
  "time_minutes": 120,
  "description": "Classic French stew...",
  "ingredients": [
    {
      "name": "Beef roast",
      "quantity": 1,
      "unit": "kg",
      "category": "Proteins"
    }
  ],
  "instructions": [
    "Step 1: Brown beef...",
    "Step 2: Add wine..."
  ],
  "comment": "Note: Can be made ahead and reheated",
  "allergens": ["alcohol"]
}
```

### Weekly Menu Object
```json
{
  "week_start": "2026-06-23",
  "week_end": "2026-06-27",
  "dinners": [
    {
      "day": "Monday",
      "recipe_id": "recipe_001",
      "recipe": { ...recipe_object... }
    }
  ],
  "shopping_list": {
    "Proteins": [ ... ],
    "Vegetables": [ ... ],
    "Pantry": [ ... ]
  }
}
```

---

## 🛠️ How Core Features Work

### 1. Menu Generation Algorithm
**Location:** `core/menu_generator.py`

**Process:**
1. Load all recipes from `recipes_db.json`
2. Filter by selected categories (Quick Dinners, Fish & Seafood, Vegetarian)
3. Select 5 recipes for Mon-Fri with protein variety (max 2 of same type per week)
4. Save as `weekly_menu.json`
5. Generate shopping list by deduplicating ingredients

**Key Classes:**
- `MenuGenerator` - Orchestrates menu generation
- `IngredientDeduplicator` - Merges duplicate ingredients + filters pantry

### 2. Ingredient Deduplication
**Location:** `core/ingredient_deduplicator.py`

**Process:**
1. Collect all ingredients from 5 selected recipes
2. Fuzzy match similar names (e.g., "Egg" + "Eggs" → combine to "5 pieces")
3. Filter out pantry staples (salt, pepper, garlic, etc.)
4. Normalize units (g, ml, stk → standard format)
5. Categorize (Proteins, Vegetables, Dairy, etc.)
6. Sort alphabetically within categories

**Key Logic:**
- Fuzzy matching threshold: 70 (was 90, lowered in Phase 1)
- Parenthetical stripping: "Oregano (Fresh Or Dried)" → "oregano"
- Compound ingredient handling: "Salt and pepper" → split & check both

### 3. Shopping List Persistence
**Location:** `frontend/templates/shopping.html`

**Process:**
1. User checks items in shopping list
2. JavaScript saves to localStorage with week key (YYYY-WW format)
3. On page reload, localStorage restored
4. Week changes automatically each new week

**Key Features:**
- Visual feedback: checked items 50% opacity + strikethrough
- Auto-storage: saves on every checkbox change
- Auto-restore: restores on page load
- Auto-reset: storage key changes per week

### 4. Pantry Filter
**Location:** `core/ingredient_deduplicator.py` → `is_pantry_staple()`

**Process:**
1. Load English + Norwegian pantry items from `pantry_staples.json` (235 items)
2. For each ingredient in shopping list:
   - Check exact match (fastest)
   - Check without parenthetical info ("Oregano (Fresh Or Dried)" → "oregano")
   - Split by "and" & "," (e.g., "Salt and pepper" → check "salt" & "pepper" separately)
   - Fuzzy match (if no exact match)
3. Filter out matches from shopping list

**Pantry Items Examples:**
- English: salt, pepper, garlic, olive oil, butter, sugar, oregano, etc.
- Norwegian: salt, pepper, hvitløk, olivenolje, smør, sukker, oregano, etc.

---

## 📁 Project Structure

```
Menu-Planner/
├── pi-deployment/
│   ├── flask_app.py              # Main Flask app (all routes)
│   └── __init__.py
├── core/
│   ├── menu_generator.py         # Menu generation algorithm
│   ├── ingredient_deduplicator.py # Deduplication + pantry filter
│   └── __init__.py
├── frontend/
│   ├── templates/
│   │   ├── base.html             # Layout template
│   │   ├── index.html            # Dashboard
│   │   ├── recipe.html           # Recipe detail + edit button
│   │   ├── edit_recipe.html      # Recipe edit form (NEW in Phase 1)
│   │   ├── shopping.html         # Shopping list + checkboxes
│   │   ├── error.html            # Error pages
│   │   └── recipe_list.html
│   ├── static/
│   │   ├── style.css             # Global styles
│   │   ├── app.js                # Main app logic
│   │   ├── sw.js                 # Service worker
│   │   ├── manifest.json         # PWA manifest
│   │   ├── i18n.json             # Translations (EN + NO)
│   │   ├── measurements.js       # Unit conversion
│   │   ├── language-manager.js   # Language switching
│   │   ├── theme-manager.js      # Theme switching
│   │   ├── themes/               # Theme CSS files (8 themes)
│   │   └── images/               # Icons, logos
│   └── __init__.py
├── data/
│   ├── recipes_db.json           # Main recipe database
│   ├── sample_recipes.json       # Fallback recipes
│   ├── weekly_menu.json          # Latest generated menu
│   ├── pantry_staples.json       # Pantry items (EN + NO)
│   ├── categories.json           # Recipe categories
│   └── __init__.py
├── logs/                         # Application logs
│   └── deduplicator.log          # Ingredient deduplication logs
├── tests/                        # Unit tests (to be added in Phase 2)
├── scripts/                      # Utility scripts (to be added in Phase 2)
├── .github/                      # GitHub configuration (to be added in Phase 2)
│   └── workflows/
├── Dockerfile                    # Docker image definition
├── docker-compose.yml            # Docker compose config
├── .dockerignore                 # Docker ignore rules
├── requirements.txt              # Python dependencies
├── .env.example                  # Environment variables template
├── alembic.ini                   # Alembic config (to be added in Phase 2)
├── README.md                     # Project README
├── 00_START_HERE.md              # Getting started guide
├── HANDOFF_PHASE_1_COMPLETE.md   # Phase 1 handoff doc
├── PHASE_2_CATCHUP_PROMPT.md     # Phase 2 quick-start prompt
├── PHASE_2_ARCHITECTURE.md       # Phase 2 architecture guide
├── PROJECT_CONTEXT.md            # THIS FILE
├── RUN_LOCAL.bat / RUN_LOCAL.ps1 # Local dev startup scripts
└── .gitignore
```

---

## 🚀 How to Run the Project

### Local Development (Flask)
```bash
cd "d:\Claude AI Projects\projects\GitHub\Menu-Planner"
.\RUN_LOCAL.ps1        # or RUN_LOCAL.bat
# Opens on http://localhost:5000
```

### Docker (Local)
```bash
docker build -t menu-planner:latest .
docker run -p 5000:5000 menu-planner:latest
# Opens on http://localhost:5000
```

### Key Endpoints
- `GET /` - Dashboard (menu overview)
- `GET /recipe/<recipe_id>` - Recipe detail
- `GET /edit-recipe/<recipe_id>` - Recipe edit form
- `GET /shopping` - Shopping list
- `POST /api/generate-menu` - Generate new weekly menu
- `POST /api/edit-recipe` - Save recipe changes
- `GET /api/recipes` - List all recipes
- `GET /api/categories` - List recipe categories
- `GET /health` - Health check

---

## 📝 Important Files to Understand

### For Any Claude Instance Working on This Project

1. **Start with these (in order):**
   - `00_START_HERE.md` - Getting started
   - `PROJECT_CONTEXT.md` - THIS FILE (complete context)
   - `HANDOFF_PHASE_1_COMPLETE.md` - What's been done

2. **Then for specific tasks:**
   - **Phase 2 Task 1 (Database):** `PHASE_2_ARCHITECTURE.md`
   - **Phase 2 Task 2 (Auth):** (to be created)
   - **Phase 2 Task 3 (Households):** (to be created)
   - **Phase 2 Task 4 (Cloud):** (to be created)
   - **Phase 2 Task 5 (CI/CD):** (to be created)

3. **Code files to understand:**
   - `pi-deployment/flask_app.py` - All routes + Flask config
   - `core/menu_generator.py` - Menu generation logic
   - `core/ingredient_deduplicator.py` - Deduplication + pantry filter
   - `frontend/static/app.js` - Client-side logic

---

## 🎓 What Has Been Done (Phase 1)

### ✅ Completed Tasks

| Task | Status | What Was Done |
|------|--------|---------------|
| **A0 - Pantry Filter** | ✅ | Salt, pepper, garlic, oregano filtered from shopping list |
| **A1 - Recipe Edit** | ✅ | Edit button + Notes section added; comments persist |
| **A2 - Checkbox Persistence** | ✅ | Shopping list checkboxes survive refresh & navigation |
| **A3 - Docker Support** | ✅ | Docker image built (543MB), container runs, health checks pass |

### 🛠️ Improvements Made

1. **Ingredient Deduplication**
   - "Egg" + "Eggs" now merge correctly
   - "stk" (Norwegian) displays as "pieces" (English)
   - Fuzzy threshold lowered from 90 → 70

2. **Pantry Filter**
   - Parenthetical stripping: "Oregano (Fresh Or Dried)" → "oregano"
   - Compound ingredients: "Salt and pepper" → split & check both parts
   - Exact match check added (faster than fuzzy matching)

3. **UI Cleanup**
   - Removed confusing "Hold command" tip from shopping list
   - Added Edit button to recipe detail pages
   - Added editable Notes section with toggle edit

4. **Data Updates**
   - Added Norwegian sugar variants: melis, vaniljesukker, rørsukker, farin

---

## 🚀 What Comes Next (Phase 2)

### Task 1: PostgreSQL Migration
- Migrate JSON → PostgreSQL database
- Create SQLAlchemy models
- Set up Alembic migrations
- Seed existing recipes into database
- Test all Phase 1 features still work

### Task 2: User Authentication
- Add Flask-Login system
- Create login/signup pages
- Add password hashing
- Create user model

### Task 3: Household Management
- Create household/team feature
- Add member invitations
- Add permission roles (owner, editor, viewer)
- Scope data to household

### Task 4: Cloud Deployment
- Deploy to Railway
- Configure PostgreSQL on Railway
- Set up environment variables
- Configure GitHub integration

### Task 5: CI/CD Pipeline
- Create GitHub Actions workflow
- Add linting (flake8)
- Add unit tests (pytest)
- Auto-deploy on push to main

---

## 💾 Environment Setup

### Required for Local Development
- Python 3.11+
- PostgreSQL (for Phase 2) or SQLite
- Docker (optional, for containerized development)
- Git

### Python Packages (requirements.txt)
```
requests==2.31.0
flask==3.0.0
apscheduler==3.10.4
python-dotenv==1.0.0
azure-identity==1.15.0
msgraph-core==0.2.2
rapidfuzz==3.6.0
sqlalchemy==2.0.23     # Phase 2
alembic==1.13.1        # Phase 2
psycopg2-binary==2.9.9 # Phase 2
flask-login==0.6.3     # Phase 2
```

### Environment Variables (`.env`)
```env
# Phase 1
HOUSEHOLD_NAME=My Household
FLASK_ENV=development

# Phase 2 (coming)
DATABASE_URL=postgresql://user:password@localhost/menu_planner
SECRET_KEY=your-secret-key
```

---

## 🧪 Testing Approach

### Phase 1 (Already Done)
- Manual testing via browser
- All endpoints tested
- All Phase 1 features verified working

### Phase 2 (Coming)
- Unit tests with pytest
- Test database with SQLAlchemy test fixtures
- Test auth flow
- Test household permissions
- Integration tests before deployment

---

## 📊 Key Concepts to Understand

### 1. Single-Tenant → Multi-Tenant
**Now:** All data anonymous, single household
**Phase 2:** Multiple users, each with their own household(s)

### 2. JSON → PostgreSQL
**Now:** JSON files (no transactions, no concurrency)
**Phase 2:** Relational database (ACID, concurrent users)

### 3. Local → Cloud
**Now:** Runs on localhost only
**Phase 2:** Deployed to Railway (accessible worldwide)

### 4. Manual → Automated
**Now:** Manual testing & deployment
**Phase 2:** GitHub Actions CI/CD (test on push, auto-deploy)

---

## 🤔 Common Questions Answered

### Q: Where are the recipes stored?
**A:** `data/recipes_db.json` (Phase 1) or PostgreSQL table (Phase 2)

### Q: How does pantry filtering work?
**A:** See `core/ingredient_deduplicator.py` → `is_pantry_staple()` method

### Q: How does menu generation choose recipes?
**A:** See `core/menu_generator.py` → `select_recipes()` method (chooses 5 with protein variety)

### Q: How does shopping list deduplication work?
**A:** See `core/ingredient_deduplicator.py` → `deduplicate_ingredients()` method

### Q: Where are translations stored?
**A:** `frontend/static/i18n.json` (English & Norwegian)

### Q: How does theme switching work?
**A:** `frontend/static/theme-manager.js` + 8 CSS theme files in `frontend/static/themes/`

### Q: Where are the Flask routes?
**A:** All in `pi-deployment/flask_app.py` (single file, ~850 lines)

### Q: How to add a new recipe?
**A:** Edit `data/recipes_db.json` (Phase 1) or use admin UI (Phase 2)

### Q: Can users save menus?
**A:** Currently generates weekly menu, saved as `weekly_menu.json`. Phase 2 will save to database per household.

---

## 🎯 For the New Claude Instance

**Before asking ANY questions, read these files in order:**

1. This file: `PROJECT_CONTEXT.md` (complete overview)
2. `HANDOFF_PHASE_1_COMPLETE.md` (what's been done)
3. `PHASE_2_ARCHITECTURE.md` (if working on Task 1)
4. Specific task docs (created as needed)

**If you still have questions after reading these, they're probably valid clarifying questions!**

---

## 📞 Git History

View recent commits to see exactly what changed:
```bash
git log --oneline -20    # See last 20 commits
git show <commit-hash>   # See details of specific commit
git diff HEAD~1          # See changes in latest commit
```

---

## ✅ Health Check

To verify the project is in good state:

```bash
# 1. Run locally
.\RUN_LOCAL.ps1

# 2. Test endpoints
curl http://localhost:5000/health
curl http://localhost:5000/api/recipes
curl http://localhost:5000/shopping

# 3. Check logs
tail -f logs/deduplicator.log

# 4. Generate menu
# Use browser: http://localhost:5000 → click "Generer ny meny"
```

All should respond with 200 status code and valid JSON.

---

**This project is well-documented and ready for Phase 2! 🚀**
