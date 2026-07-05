# Menu Planner — Feature Roadmap

Last updated: 2026-07-05

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

---

## 🎯 Now — before public + paid launch

See `BACKLOG_2026-07-01.md` for full detail and live status on all of these.

- **Legal/compliance:** privacy policy + terms of service (none exist yet), trial-to-paid pre-charge notice, self-serve cancellation, 14-day right-of-withdrawal disclosure, tax/business registration timing, confirm Patreon's creator terms
- **B46 (remaining):** data-level i18n pass across the recipe database — category tags, ingredient names, and allergen text still inconsistently translated
- **B17:** watching for recurrence of the intermittent relogin/"Oops!" issue a few more days before calling it closed

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
