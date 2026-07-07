# Menu Planner

A web application for families to plan weekly dinners, manage recipes, and generate shopping lists — available at **[menuplanner.no](https://menuplanner.no)**.

**Created by:** [nobody174](https://github.com/nobody174)
**License:** MIT
**Support:** [Patreon](https://www.patreon.com/Nobody174/posts/menu-planner-161473082)

---

## Features

✅ **Recipe Management** — Add your own recipes via web form or import recipe packs
✅ **Weekly Menu Generation** — Auto-generate 6 dinners per week from your recipe collection
✅ **Shopping Lists** — Auto-deduplicated ingredient list for the whole week
✅ **Pantry Tracking** — Mark ingredients you already have; they're greyed out on the shopping list
✅ **Recipe Packs** — 12+ curated packs (Norwegian, Italian, Tex-Mex, Grills, Salads and more)
✅ **Bilingual** — Full Norwegian & English support, one-click language toggle
✅ **Household Management** — Multiple users, roles (owner/editor/viewer), family profiles
✅ **Categories** — Fully customisable (add, rename, merge, delete)
✅ **Multiple Themes** — 8+ themes to choose from
✅ **Favourites** — Star recipes, generate menus from favourites only
✅ **Activity Log** — See who added/changed what in the household
✅ **Email Confirmation & Password Reset** — via Resend
✅ **Responsive Design** — Works on desktop, tablet and mobile
✅ **PWA** — Installable on mobile home screen
✅ **Open Source** — Free to self-host

---

## Live App

**[menuplanner.no](https://menuplanner.no)**

Hosted on Render.com (web) + Neon.tech (PostgreSQL).

---

## Self-Hosting

### Prerequisites

- Python 3.11+
- PostgreSQL database (or Neon free tier)
- Git

### Setup

```bash
# 1. Clone
git clone https://github.com/nobody174/Menu-Planner.git
cd Menu-Planner

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure environment variables
cp .env.template .env
# Edit .env: set DATABASE_URL, SECRET_KEY, FLASK_ENV

# 5. Run database migrations
alembic upgrade head

# 6. Start
gunicorn -b 0.0.0.0:5000 deployment.flask_app:app
```

### Required Environment Variables

| Variable | Description |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `SECRET_KEY` | Flask session secret (generate with `openssl rand -hex 32`) |
| `FLASK_ENV` | `production` or `development` |
| `RESEND_API_KEY` | For email confirmation + password reset ([resend.com](https://resend.com)) |
| `RESEND_FROM_EMAIL` | Sending address (e.g. `noreply@yourdomain.no`) |
| `ADMIN_EMAIL` | Your email — grants access to `/admin` panel |

---

## Documentation

| Document | Purpose |
|---|---|
| [User Guide](docs/USER_GUIDE.md) | Getting started for new users |
| [Advanced Guide](docs/ADVANCED_USER_GUIDE.md) | How the system works under the hood |
| [Tips & Tricks](docs/TIPS_AND_TRICKS.md) | Power user tips |
| [Recipe Pack Format](docs/RECIPE_PACK_FORMAT.md) | How to write new recipe packs (developer) |
| [Developer Guide](docs/DEVELOPER_GUIDE.md) | Project structure and contribution guide |
| [System Architecture](docs/SYSTEM_ARCHITECTURE.md) | Render + Neon infrastructure overview |
| [CI/CD Pipeline](docs/CI_CD_PIPELINE.md) | Branch model, pipeline stages, rollback |
| [Changelog](CHANGELOG.md) | Full history of all work done |
| [Feature Roadmap](docs/FEATURE_ROADMAP.md) | Planned features |
| [Backlog](docs/BACKLOG_2026-07-01.md) | Open tasks |
| [About](docs/ABOUT.md) | Project story |

---

## Tech Stack

| Layer | Technology |
|---|---|
| Backend | Python 3.11, Flask 3.0 |
| Database | PostgreSQL (Neon) + SQLAlchemy + Alembic |
| Frontend | Vanilla JS, CSS custom properties, Jinja2 templates |
| Hosting | Render.com (web) |
| Email | Resend |
| DNS / SSL | Cloudflare |
| CI/CD | GitHub Actions |

---

## License

MIT License — see [LICENSE](LICENSE)

## Credits

Built with [Flask](https://flask.palletsprojects.com/) and [Claude Code](https://claude.com/claude-code).
