# Menu Planner — Feature Roadmap

Last updated: 2026-07-08

---

## ✅ Completed (v1.0 → v1.2)

### Core App
- Recipe management (add, edit, delete via web form)
- Weekly menu generation (6 dinners, category-based)
- Shopping list with ingredient deduplication
- Pantry tracking (items greyed out on shopping list)
- Bilingual support (Norwegian + English, cookie-based)
- Category system (add, rename, merge, delete)
- 12 recipe packs (Norwegian, Italian, Tex-Mex, Grill, Salads, Summer, Holiday, and more)
- Favourites system (star recipes, generate menus from favourites)
- Sides stash (21 side dishes parked for future Sides feature)
- Dessert stash (90 desserts parked for future Dessert feature)

### Users & Households
- User accounts (email confirmation, password reset)
- Households with multi-user support
- Roles: owner / editor / viewer
- Netflix-style family profiles (profile picker, avatar, PIN)
- Referral system (code + link attribution)
- Activity log per household (last 200 entries)
- Admin panel (`/admin`, owner-only)
- Delete own account (full data cleanup)

### Infrastructure
- PostgreSQL (Neon free tier) — all data in JSONB columns
- Render.com hosting (free tier, auto-deploy from GitHub)
- Cloudflare DNS + SSL for `menuplanner.no`
- Resend email (confirmation + password reset)
- GitHub Actions CI/CD (tests, lint, security, build, data validation)
- F4 migration: file-based storage → PostgreSQL JSONB (complete)

### UI / UX
- 8 themes
- Responsive design (mobile + desktop)
- PWA (installable on mobile)
- In-app help system (Quick Start modal, Advanced Guide, Tips & Tricks) — bilingual
- Reset pantry to defaults button
- All popups use themed `pmAlert`/`pmConfirm` (no browser defaults)
- Selectable number of menu days (1-6) when generating (F10)
- "Change day" and "Delete recipe" available from inside the recipe detail page (F12)
- Nav avatar clickable → switch profile/user
- Mobile testing pass (2026-07-03/04): fixed household settings overflow, shopping list unit/translation issues, settings dropdown cutoff, PIN autofocus, swap-recipe persistence, empty categories list, and a service worker bug that permanently cached stale pages — see `CHANGELOG.md`

### Infrastructure (cont'd)
- Render deploy is now actually automatic on push to `public-release-v1` (the previous GitHub Actions deploy step was silently dead — gated on a `main` branch that doesn't exist in this repo)
- Admin panel maintenance action to backfill measurement-unit fixes into already-imported household recipe data

### Round 6 (2026-07-05) — see `CHANGELOG.md` for full detail
- Fixed a critical cross-account household data leak (B50) and a broken first-visit dashboard for new households (B51)
- Engineering security pass: role checks on all write endpoints, CSRF protection app-wide, PIN brute-force lockout, closed several session-validation gaps in the same shape as B50
- Removed Microsoft To Do/Todoist/TickTick shopping-list sync and the broken "Login with Microsoft" feature (both real setup/support burden for little benefit)
- F16: settings dropdown reorganized into collapsible groups
- F14: user-facing "What's New" page
- F6 / F15: user-facing "What's Planned" page
- F13: per-page "← Back" button using real browser history
- F11 (partial): Quick Start Guide now notes recipes are sized for a family of 4
- A full mobile viewport pass, a Claude-in-Chrome automated QA pass, and multi-household/multi-user isolation testing — all clean or fixed, see changelog

### Round 7 (2026-07-06) — see `CHANGELOG.md` for full detail
- Design-critique pass on the live site: fixed the All Recipes `[object Object]` bug, stale "0 MIN" recipe times, day-card headers rendering the wrong theme color, added a difficulty color indicator, and several copy/UX refinements
- Found and fixed a related activity-log bug (raw dict reprs shown for swap actions)
- B46 fully closed same day (category tags, ingredient names, and allergen tags all translate correctly now)
- Re-verified B17 at the code level; investigated a potential menu-write race condition and confirmed it's not currently exploitable (single gunicorn worker, no real concurrency yet)

### Round 8 (2026-07-07) — see `CHANGELOG.md` for full detail
- Comprehensive read-only audit (`docs/AUDIT_2026-07-07.md`), then fixed nearly everything it found the same day: a shopping-list export bug that was likely broken in production (C1), a `SECRET_KEY` fail-hard guard (H1), rate limiting + login-enumeration hardening (H2/M7), a dead `/themes` route (H3), account-deletion data-integrity fixes (M1/M2), silent write-failure and HTML-error-to-JSON-client bugs (M4/M5), per-request DB-query caching (M6), missing DB indexes (B56), and route-level test coverage (B59)
- The big one: split `deployment/flask_app.py` (~4,700 lines) into an app-factory (`deployment/app_core.py`) + 7 Flask blueprints (`deployment/routes/*.py`) - B57, long-planned
- Separately, a QA/production-readiness pass fixed silent partial menu generation (B53), a CI vulnerability scan that wasn't actually gating anything (B54), a missing "no results" search state (B55), a real SQLite concurrency bug affecting live usage not just tests (B63), a broken mobile layout on All Recipes (B65), a wrong-page link (B66), missing GitHub Releases on auto-tagged versions (B67), and flaky visual-regression tests (B68) - plus shipped the Playwright MCP + CI visual-regression suite (B62)
- The Firefox-only white-block bug (B58) that motivated B62 is still unreproduced and still open

### Round 9 (2026-07-08) — see `CHANGELOG.md` for full detail
- Security Hardening PR: found rate limiting, login-enumeration protection, and the body-size cap (H2/M7/LO1) were already done from Round 8; closed the one real remaining gap, a missing Content-Security-Policy header (M8)
- Bookkeeping cleanup: renamed `BACKLOG_2026-07-01.md` → `BACKLOG.md` (a living file shouldn't have a date baked into its name), and backfilled the Round 8 CHANGELOG entries that never got written the day of

---

## 🎯 Now — before public + paid launch

See `BACKLOG.md` for full detail and live status on all of these.

- **Legal/compliance:** privacy policy + terms of service (none exist yet), trial-to-paid pre-charge notice, self-serve cancellation, 14-day right-of-withdrawal disclosure, tax/business registration timing, confirm Patreon's creator terms
- **M3:** deployment definition split-brain (Railway-era Docker vs. Render Procfile) - decide which is actually live, delete/demote the other
- **B61:** dual storage path (JSONB vs. legacy per-household files) consolidation
- **B58:** Firefox-only white-block rendering bug, still unreproduced
- **B17:** watching for recurrence of the intermittent relogin/"Oops!" issue before calling it closed

## 🔜 Next — planned features, no fixed order yet

| # | Feature | Notes |
|---|---------|-------|
| F1 | Themes full rework | Design-language themes, not just colour swaps |
| F2 | Dessert + Drinks browsing | 90 desserts stashed, needs UI |
| F3 | Avatar upgrade (DiceBear) | Replace emoji picker with generated pixel art |
| F5 | Around the World recipe pack | 1-2 iconic dishes per country, bilingual |
| F8 | Sides stash feature | Browse + pick sides to go with weekly menu |
| F9 | Dessert system on dinner planner | Pick dessert days, separate shopping list section (needs F2 first) |
| F11 | Family-of-4 portion note (full version) | Guide note added 2026-07-05; a persistent note directly on recipe cards/detail pages would be more reliable than the guide alone |

## 💡 Someday / Long-Term Ideas

- Swap individual recipes on the menu (drag + replace)
- Lock specific recipes to specific days
- Menu history (view past weeks)
- Shopping list checkboxes (tick off while shopping)
- Export shopping list as PDF
- Nutrition info per recipe (calories, protein, carbs)
- "Use up what you have" recipe suggestions based on pantry
- Seasonal category suggestions (Grill in summer, Supper in winter)
- Community recipe sharing (optional, privacy-first)
- Mobile app (iOS / Android)
- Re-add Microsoft To Do/Todoist/TickTick shopping-list sync, but only if users actually ask for it (removed 2026-07-05 due to setup/support burden — see `CHANGELOG.md`)

---

## Decision Framework

When prioritising new features:
1. **Does it help families plan meals more easily?** (core mission)
2. **How many users benefit?** (family/friends testing phase first)
3. **How much complexity does it add?** (keep it simple)
4. **Does anything else depend on it?** (unblock other features first)
