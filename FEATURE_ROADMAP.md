# Menu Planner — Feature Roadmap

Last updated: 2026-07-04

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

---

## 🚧 Active Backlog (see BACKLOG_2026-07-01.md)

### Bugs
- **B17:** Intermittent relogin/"Oops!" errors — fix shipped, monitoring for recurrence
- **B28:** Two recipes have broken combined-ingredient units, need manual splitting
- Activity log may be silently dropping some entries (detached-session bug) — needs audit

### Upcoming Features
| # | Feature | Notes |
|---|---------|-------|
| F1 | Themes full rework | Design-language themes, not just colour swaps |
| F2 | Dessert + Drinks browsing | 90 desserts stashed, needs UI |
| F3 | Avatar upgrade (DiceBear) | Replace emoji picker with generated pixel art |
| F5 | Around the World recipe pack | 1-2 iconic dishes per country, bilingual |
| F6 | Future ideas page | 💡 page for family/friends to see what's coming |
| F8 | Sides stash feature | Browse + pick sides to go with weekly menu |
| F9 | Dessert system on dinner planner | Pick dessert days, separate shopping list section |
| F11 | Family-of-4 portion note | Recipes don't indicate default serving size anywhere |

---

## 💡 Long-Term Ideas

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

---

## Decision Framework

When prioritising new features:
1. **Does it help families plan meals more easily?** (core mission)
2. **How many users benefit?** (family/friends testing phase first)
3. **How much complexity does it add?** (keep it simple)
4. **Does anything else depend on it?** (unblock other features first)
