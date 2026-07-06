# Menu Planner — Developer Guide

Last updated: 2026-07-02

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
│   ├── flask_app.py               # ALL routes, API endpoints, helpers
│   ├── email_notifier.py          # Resend email sending
│   ├── scheduler.py               # APScheduler background jobs
│   └── to_do_sync.py              # Microsoft To Do integration (optional)
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
├── tests/
│   ├── test_auth.py
│   ├── test_core_modules.py
│   └── test_household.py
├── docs/                          # All documentation (guides, backlog,
│                                   # roadmap, architecture, about)
├── requirements.txt
├── Procfile                       # Render start command
├── runtime.txt                    # Python version (3.11.9)
├── CHANGELOG.md                   # Full project history
├── CLAUDE.md                      # Working instructions / deploy flow
└── new_chat_fresh_menu_planner.md # Context file for new Claude sessions
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
python deployment/flask_app.py
```

Open http://localhost:5000

### With PostgreSQL Locally

```bash
# Set DATABASE_URL before running
$env:DATABASE_URL="postgresql://user:pass@host/dbname"
alembic upgrade head
python deployment/flask_app.py
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

All routes live in `deployment/flask_app.py`. Add your route near related routes.

```python
@app.route('/api/my-feature', methods=['POST'])
def my_feature():
    if not session.get('user_id'):
        return jsonify({'success': False}), 401
    # ... your logic
    return jsonify({'success': True})
```

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

```bash
pytest tests/ -v
```

---

## CI/CD

A single staged pipeline (`.github/workflows/ci.yml`) runs on every push to
`main` and on every pull request into `public-release-v1`: lint/format and
data/frontend validation first, then tests/security/build once those pass,
then a production deploy (only on a merge into `public-release-v1`). See
[docs/CI_CD_PIPELINE.md](CI_CD_PIPELINE.md) for the full pipeline diagram
and branch model.
