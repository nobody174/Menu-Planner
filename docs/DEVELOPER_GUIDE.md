# Menu Planner — Developer Guide

Last updated: 2026-07-08

For the complete technical architecture, see `SYSTEM_ARCHITECTURE.md`.
For the recipe pack JSON format, see `RECIPE_PACK_FORMAT.md`.

---

## Project Structure

```
Menu-Planner/
├── core/                          # Core logic
│   ├── menu_generator.py          # Menu generation algorithm
│   ├── ingredient_deduplicator.py # Shopping list deduplication
│   ├── household_paths.py         # JSONB load/save functions
│   ├── household_helpers.py       # Household/member queries
│   ├── auth_helpers.py            # Auth: create user, login, reset, delete
│   └── error_handler.py           # Centralised error handling
├── database/
│   ├── models.py                  # SQLAlchemy models (User, Household, HouseholdMember)
│   └── database.py                # DB engine + SessionLocal
├── alembic/
│   └── versions/                  # Migration scripts (add new ones here)
├── deployment/
│   ├── flask_app.py               # Entry point + blueprint registration only
│   ├── app_core.py                # App factory (create_app), shared helpers,
│   │                               # FEATURE_FLAGS, security headers, error handlers
│   ├── routes/                    # Flask blueprints, one module per area
│   │   ├── auth_routes.py         # Login, signup, password reset, account delete
│   │   ├── admin_routes.py
│   │   ├── household_routes.py
│   │   ├── pantry_category_routes.py
│   │   ├── menu_routes.py
│   │   ├── recipe_routes.py
│   │   └── recipe_pack_routes.py
│   ├── shopping_integrations.py   # CSV/ICS export, Apple Reminders sync
│   ├── email_notifier.py          # Resend email sending
│   ├── scheduler.py                 ┐ Dead Pi-era modules (LO3, docs/BACKLOG.md) -
│   └── to_do_sync.py                ┘ imported nowhere, kept only pending cleanup
├── frontend/
│   ├── static/
│   │   ├── app.js                 # Main UI logic
│   │   ├── style.css              # Base styles
│   │   ├── i18n.json              # ALL translations (key_no / key_en)
│   │   ├── language-manager.js    # Language switching
│   │   ├── measurements.js        # Metric ↔ imperial conversion
│   │   ├── manifest.json          # PWA manifest
│   │   ├── sw.js                  # Service worker
│   │   └── themes/                # CSS theme files + registry
│   └── templates/                 # Jinja2 HTML templates
│       ├── base.html              # Nav, settings dropdown, help modal
│       ├── settings.html          # User settings page
│       ├── household-settings.html
│       ├── help_advanced.html     # Advanced guide (bilingual)
│       └── help_tips.html         # Tips & tricks (bilingual)
├── data/
│   ├── recipe-packs/              # 12 importable recipe packs
│   ├── sample_recipes.json        # 10 shared base recipes
│   ├── categories.json            # Base category seed
│   ├── pantry_staples.json        # ~100 bilingual EN↔NO staples
│   ├── sides-stash.json           # 21 side dishes (not in menus)
│   ├── dessert-stash.json         # 90 desserts (not in menus)
│   └── drinks-stash.json          # 4 drinks (not in menus)
├── scripts/
│   ├── delete_user.py             # Admin: delete a user + their data
│   ├── delete_test_users.py       # Admin: bulk-delete test accounts
│   └── archive/                   # One-time migration scripts, already run
├── e2e/                            # Playwright cross-browser/visual-regression suite
├── tests/                          # pytest suite (route smoke tests, auth,
│                                    # household, category/pantry/menu-mutation
│                                    # routes, CSRF, security headers, caching)
├── docs/                          # All documentation (guides, backlog,
│                                   # roadmap, architecture, about)
├── requirements.txt
├── Procfile                       # Render start command (gunicorn) - the
│                                   # only deployment definition (M3, 2026-07-09:
│                                   # deleted the unused Railway-era
│                                   # Dockerfile/docker-compose.yml/
│                                   # docker-entrypoint.sh - Render never ran them)
├── runtime.txt                    # Python version (3.11.9)
├── CHANGELOG.md                   # Full project history
└── CLAUDE.md                      # Working instructions / deploy flow
```

---

## Local Development Setup

### Prerequisites
- Python 3.11+
- Git

### Setup

```bash
git clone https://github.com/nobody174/Menu-Planner.git
cd Menu-Planner

python -m venv venv
venv\Scripts\activate       # Windows
# source venv/bin/activate  # Mac/Linux

pip install -r requirements.txt

# Run without DATABASE_URL to use local SQLite
# NOTE: deployment/ is a real package (deployment.app_core, deployment.routes.*)
# as of the B57 blueprint split (2026-07-07) - "python deployment/flask_app.py"
# no longer works (ModuleNotFoundError: No module named 'deployment'), since
# running a file directly as a script doesn't put the project root on
# sys.path the way "python -m" does. Must run as a module instead:
set FLASK_DEBUG=1
python -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000
```

Or just run `RUN_LOCAL.bat` (Windows) / `RUN_LOCAL.ps1`, which do the same
thing plus venv/`.env` bootstrapping.

Open http://localhost:5000

### With PostgreSQL Locally

```bash
# Set DATABASE_URL before running
$env:DATABASE_URL="postgresql://user:pass@host/dbname"
alembic upgrade head
python -m flask --app deployment.flask_app run --host=0.0.0.0 --port=5000
```

---

## Adding a Database Migration

1. Edit `database/models.py` with your changes
2. Create a new migration file in `alembic/versions/`
3. Set `down_revision` to the current head (`python -m alembic heads`)
4. Write `upgrade()` and `downgrade()` functions
5. Test: `alembic upgrade head` and `alembic downgrade -1`

Example migration:
```python
revision = 'abc123def456'
down_revision = 'previous_revision_id'

def upgrade():
    op.add_column('households', sa.Column('new_field', sa.JSON(), nullable=True))

def downgrade():
    op.drop_column('households', 'new_field')
```

---

## Adding a New Route

Routes live in `deployment/routes/*.py`, one blueprint module per area (auth,
admin, household, pantry_category, menu, recipe, recipe_pack) - add your
route to whichever module it belongs with, or create a new blueprint module
for a genuinely new area. `deployment/flask_app.py` itself only registers
blueprints; it shouldn't gain new route bodies directly.

```python
# inside the relevant deployment/routes/*.py's register(bp, limiter) function
@bp.route('/api/my-feature', methods=['POST'])
def my_feature():
    if not session.get('user_id'):
        return jsonify({'success': False}), 401
    # ... your logic
    return jsonify({'success': True})
```

If your route needs rate limiting, use the `limiter` argument
`register(bp, limiter)` receives: `@limiter.limit("10 per minute")` - it
can't be a bare module-level decorator here, since the real `Limiter`
instance doesn't exist until `deployment/app_core.py`'s `create_app()` runs,
which happens after blueprint modules are imported.

---

## Adding Translations

All UI strings go in `frontend/static/i18n.json` as paired keys:

```json
"my_new_key_no": "Norsk tekst",
"my_new_key_en": "English text"
```

In templates: `{{ t.get('my_new_key', 'Fallback') }}`
In JS: keys are passed via `STR = { ... }` blocks in templates.

---

## JSONB Save Pattern

**Always use a fresh session — never db.merge() on detached objects:**

```python
from database.database import SessionLocal
from database.models import Household

db = SessionLocal()
try:
    household = db.query(Household).filter(Household.id == household_id).first()
    if household:
        household.pantry = sorted(new_items)
        db.commit()
except Exception as e:
    db.rollback()
    print(f"Error: {e}")
finally:
    db.close()
```

---

## Deployment

Push to `public-release-v1` → Render auto-deploys.

**Build command (Render):**
```
python3.11 -m pip install --break-system-packages -r requirements.txt && python3.11 -m alembic upgrade head
```

**Start command (Render):**
```
python3.11 -m gunicorn -b 0.0.0.0:$PORT deployment.flask_app:app
```

See [SYSTEM_ARCHITECTURE.md](SYSTEM_ARCHITECTURE.md) for the current
Render + Neon infrastructure, and
[CI_CD_PIPELINE.md](CI_CD_PIPELINE.md) for how a deploy actually happens.

---

## Running Tests

Run against a dedicated test database, never the real local dev DB - the
suite drops and recreates all tables before every single test
(`tests/conftest.py` refuses to run at all if `DATABASE_URL` looks like it
might be `menu_planner.db`):

```bash
DATABASE_URL=sqlite:///test.db pytest tests/ -v      # bash
$env:DATABASE_URL='sqlite:///test.db'; pytest tests/ -v   # PowerShell
```

Also run the Playwright visual-regression suite after any
template/HTML/CSS change - see "Cross-browser/cross-device visual testing"
in `CLAUDE.md` for the exact commands.

---

## CI/CD

A single staged pipeline (`.github/workflows/ci.yml`) runs on every push to
`main` and on every pull request into `public-release-v1`: lint/format and
data/frontend validation first, then tests/security/build once those pass,
then a production deploy (only on a merge into `public-release-v1`). See
[docs/CI_CD_PIPELINE.md](CI_CD_PIPELINE.md) for the full pipeline diagram
and branch model.
