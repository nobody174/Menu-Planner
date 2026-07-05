# Menu Planner — Project Changelog

Complete history of all work done on the project, newest first.
See `BACKLOG_2026-07-01.md` for open tasks and `FEATURE_ROADMAP.md` for planned features.

---

## 2026-07-05

Full punch-list pass, multi-user/multi-household testing, a Claude-in-Chrome QA sweep, a legal/compliance check ahead of public launch, an engineering security pass, and removal of the Microsoft To Do/Todoist/TickTick sync and the "Login with Microsoft" feature. This was a big day - kept in full detail here since it's the day most of the pre-public-launch groundwork got done.

### 🔴 Critical fixes

- **B50 — cross-account household data leak:** logging in as a second account on the same browser silently inherited the first account's entire household (menu, recipes, pantry), and writes made as the second account actually landed in the first account's real data. **Cause:** `current_household_id()` stored the active household in the session cookie and trusted it unconditionally on every request, never checking that the *currently logged-in* user was actually a member of it; `login_local()` never cleared this key on a fresh login. **Fix:** `current_household_id()` now cross-checks the session's household id against the current user's actual households and discards it if it doesn't belong to them; `login_local()` also clears it on every login as a second independent layer. Verified live with testuser1/testuser2 - isolation confirmed, no data crossed over.
- **B51 — brand-new households hit a generic "Oops!" error page** on their very first dashboard visit, before ever generating a menu. Replaced with `empty_dashboard.html`, a friendly welcome screen with a working "Generate Menu" button, served with a normal 200 status instead of a 404 error page.

### ✅ Engineering security pass (prompted by reviewing the code around the B50 fix)

- **Missing role checks on write endpoints:** `/api/add-recipe`, `/api/delete-recipe`, `/api/edit-recipe`, `/api/swap-recipe`, `/api/pantry/add`, `/api/pantry/remove`, `/api/pantry/reset`, `/api/recipe-packs/import`, `/api/recipe-packs/remove`, `/api/recipes/import` all skipped the `acting_role_can_edit()` gate already used correctly by `/api/regenerate` and `/api/categories/*` - a viewer-role profile (e.g. a kid's account) could edit the menu, delete recipes, and modify pantry/recipe-pack data. Fixed all 10 endpoints and verified live with a test client (viewer blocked with 403, owner still allowed).
- **B50-shaped raw session reads:** ~17 call sites across `flask_app.py` read `session.get('current_household_id')` directly instead of the `current_household_id()` helper that re-validates membership against the *current* user. Most notably, `household_settings()` fetched and rendered a household straight from the raw session value with zero re-check before display - structurally the same bug as B50 itself, just not yet triggered. All replaced with the helper.
- **No CSRF protection anywhere:** added `flask-wtf`'s `CSRFProtect`. Traditional forms (login, signup, household-settings, admin, etc.) now carry a hidden `csrf_token` field; all `fetch()`-based JSON requests get an `X-CSRFToken` header automatically via a wrapper added to `app.js`, so existing fetch calls across the codebase didn't need individual edits. Verified: an unauthenticated POST without the token now correctly gets rejected ("The CSRF token is missing").
- **PIN brute-force:** the 4-digit owner PIN (10,000 combinations) had no rate-limiting. Added an in-memory lockout in `core/auth_helpers.py` (5 wrong attempts -> 5 minute lockout, per-process - acceptable at this scale, worth revisiting with Redis if this ever runs multi-worker under real attack traffic).
- **Removed `/api/debug-token`:** left-over debugging route that returned any logged-in user's decoded Azure JWT claims; its own docstring said to remove it.
- Full test suite (50 tests) verified passing after all of the above; app boots and renders cleanly.

### 🗑️ Removed — "Login with Microsoft" (Azure/MSAL), entirely

- Found while auditing the B50 fix's surrounding code: `callback()` (the Azure/MSAL login handler) set `session['access_token']`/`user_email`/`auth_type` but never `session['user_id']` - the key every household/menu-editing check gates on. So anyone using "Login with Microsoft" could apparently authenticate but couldn't actually access their household, generate a menu, or edit anything (B52).
- Decision: it likely was only ever added to support the old Microsoft To Do sync (removed the same day, see below), and you weren't even aware it existed. Rather than build the deeper fix this would've needed (creating/linking a database `User` record for Azure logins), removed it entirely: the Microsoft sign-in button, `/login-azure` and `/callback` routes, `/api/check-azure-creds`, `_has_azure_creds()`, the `access_token` fallback in `is_authenticated`, `deployment/auth.py` (MSAL-only, deleted outright), the `azure-identity`/`msgraph-core` dependencies, and leftover dead CSS (`.btn-microsoft`, `.divider`).
- Local email/password login with the email-confirmation link is now the only sign-in method. Verified: the removed routes correctly 404; login/signup render clean; full test suite still passes.

### 🗑️ Removed — Microsoft To Do / Todoist / TickTick shopping-list sync

- Removed from the shopping list "Export & Sync" modal and the `/api/sync-shopping-list` backend. Reason: each requires the user to obtain and paste their own API token (Todoist/TickTick) or set up an Azure app registration (Microsoft) - real setup friction and support burden for a friends-and-family/public, non-technical audience. The Microsoft To Do integration's Graph auth (`client_credentials` grant against `/me/todo/lists`) was also likely broken as written, since `/me/` requires a signed-in user context, not app-only auth.
- CSV/JSON/TXT export, ICS calendar download, clipboard copy, and Apple Reminders (also just an ICS download, no account needed) all still work and need zero setup - kept as-is per your call.
- Not deleted from git history, just disconnected from the live UI/route - `deployment/to_do_sync.py` and `deployment/scheduler.py` (an old unused Raspberry-Pi-era cron script, not wired into the live app at all) still contain the old code if it's ever worth reviving on user request.

### 🐛 Bug fixes — confirmed and verified

- **B49:** `GET /api/categories` read this household's `categories.json` **file** directly while every category-management route was DB-backed - so any category you added/renamed/removed through the UI never actually showed up anywhere, permanently stale. Genuinely significant, previously-undiscovered. Fixed to use the same DB-backed helper as the other category routes; verified an added test category appeared correctly in both the API and the All Recipes filter dropdown, then confirmed removed from both.
- **B36:** deleting a recipe still referenced on the current weekly menu left a dangling reference (dashboard still showed its name, clicking in 404'd). Delete now also clears any day still referencing the deleted recipe; the dashboard falls back to "No recipe assigned" instead of a dead link. (An early version of the fix set `time_minutes` to `''` instead of `0`, which broke the weekly-summary sum and caused a real dashboard crash - caught during verification and corrected.)
- **B37:** Quick Start/Advanced Guide pointed to the wrong location for recipe pack import/management (said All Recipes, actually lives at Settings → Recipe Packs). Corrected in both languages, both guides.
- **B38:** pantry add/remove in Settings - re-tested and could not reproduce; both actions work correctly (200s, list re-renders, persists). The original report was very likely a browser-automation focus glitch (also independently observed once during this same re-test), not an app bug. No code fix needed.
- **B39:** custom recipe ingredients typed in the documented "name, quantity, unit" format weren't being parsed into structured data - `add-recipe.html`'s submit handler hardcoded every ingredient to raw text. Added `parseIngredientLine()` (mirrored in `edit_recipe.html`, which had the same bug) and fixed the edit-page textarea reconstruction to round-trip through the same format. Verified with mixed formats ("Lasagna sheets, 250, g" / "Salt" / "Onion, 1") rendering and round-tripping correctly.
- **B40:** every recipe's instructions showed duplicated step numbering ("Step 1 / 1. Preheat oven..."). Added `_strip_step_prefix()` to strip a leading numeric prefix from each instruction before rendering. Verified across sample and custom recipes.
- **B41:** delete-recipe confirmation dialog showed a raw `&#39;` HTML entity instead of an apostrophe - Jinja's autoescaping doesn't get decoded inside `<script>` tags. Fixed with `|tojson`. Verified with a title containing an apostrophe rendering cleanly. A follow-up sweep the same day (see below) caught and fixed 14 more instances of the identical pattern across `settings.html`, `all-recipes.html`, `recipe.html`, and `feedback.html`.
- **B42:** imported/custom recipes showed a generic plate icon instead of their category icon, because the icon is driven by keyword-matching the title/subtitle text for a protein word, and many real dish names (e.g. "Gravlax") don't contain their protein as a literal word. Added a category-to-protein fallback map for the unambiguous categories (Chicken, Beef & Red Meat, Fish & Seafood, Pork, etc.), deliberately left mixed-protein categories unmapped. Verified "Gravlax", "Sour Herring", "Roast Cornish Hen" now show correct icons; ambiguous categories still correctly show the generic icon rather than a guess.
- **B43:** Activity Log wasn't recording most of the actions it claimed to track (only "Swapped [day]" ever appeared). Two causes: a detached-ORM-session bug in the pantry code path, and ~12 other call sites writing to a legacy JSON file the Activity Log page never reads once a household is DB-backed. Added a shared `log_activity()` helper (mirroring the one code path that was already correct) and replaced all the broken call sites. Verified add/delete/swap/pantry actions all now log correctly with the right actor and message.
- **B44:** viewer-role profiles could see (though not successfully use, server correctly 404'd) Add/Delete recipe controls with no feedback on failure. Wrapped the controls in the existing `can_edit_menu` template check - no backend change needed, server-side enforcement was already correct. Verified 0 delete/add controls render for a Viewer profile vs. 10/1 for Owner.
- **B45:** shopping list still showed English units ("tsp"/"tbsp"/"bunch") in Norwegian mode despite B15/B20's earlier fix. Two separate causes: recipe-pack import never called the normalization function (fixed), and the shopping list route had its own separate, much smaller hardcoded unit map instead of reusing the shared one (the real bug). Fixed both, plus added a few missing `UNIT_MAP_NO` entries ("to taste", plural tablespoons/teaspoons, clove/cloves). Verified across two different generated menus.
- **B46 (partial):** added the missing i18n keys for several Settings page sections that were silently falling back to English (signed-in-as, Owner PIN, Refer a Friend, Activity Log, Danger Zone). Verified live in Norwegian. **Still open** (moved to backlog): category tags, shopping-list ingredient *names*, and allergen language remain untranslated in places - a larger, separate data-level i18n project across the recipe database itself.
- **B47:** mobile horizontal overflow at narrow widths, two real causes - fixed-position decorative "orb" elements bleeding off-canvas (not clipped by parent overflow), and the Terracotta theme's recipe-card grid forcing a 300px minimum with no override below that. Fixed both (`overflow-x: hidden` + a narrow-viewport grid override); verified no overflow at 320px/375px across the dashboard and All Recipes in both themes.
- **B48:** two broken static image references (dead links, falls back to emoji fine) - closed as won't-fix, no user-visible impact.
- **B41-adjacent apostrophe sweep:** swept `settings.html`, `all-recipes.html`, `recipe.html`, `feedback.html` for the same pattern that caused B41 and fixed all 14 remaining instances.
- **B28:** recipes `eu_096` (béchamel) and `eu_083` (butter/milk) had nonsensical combined-ingredient units bundling multiple ingredients into one line. Fixed the source pack files, plus added a read-time correction in `flask_app.py` for households that already imported the old broken data (so it displays correctly everywhere without a risky direct database migration).
- Cosmetic batch: Add Recipe's time dropdown expanded from 5 to 11 options; profile-picker browser-tab title corrected to match its heading; Household Settings "Joined" dates now show as "Jul 05, 2026" instead of raw ISO timestamps; owner's row no longer shows their email twice; Tips & Tricks corrected a stale button reference ("Add to menu" → "Swap Day"); long prep times (e.g. 1440 min curing recipes) now show as "24 h" via a new `format_minutes` filter, applied everywhere a recipe's time is shown.
- Activity log detached-session bug (originally logged separately after investigating B21) - resolved as part of the B43 fix above.

### 🔁 Re-tested and reconfirmed (no regressions)

B35 (dashboard stale recipe after swap - real cause found: the plain-insert branch of swap-recipe wasn't setting all display fields the way `MenuGenerator` does, mirrored to match), B31 (true day-swap, no more silent duplication), B32 (delete button removed from inside the recipe detail page, stays only on All Recipes), B33 (language indicator arrow + nav flag), B34 (bfcache restoring an open settings dropdown / focused PIN field after Back - fixed with a `pageshow` listener), B29 (settings dropdown clamped when the cogwheel sits near the left edge), B30 (Quick Start Guide reordered to reflect actual intended usage - own recipes first, packs last as a template option), B25 (service worker rewritten network-first for page navigations).

### 🧪 Testing passes

- Full mobile viewport pass (320px/375px) across 10 pages in both themes - clean, no overflow or error pages.
- Claude-in-Chrome automated QA pass (text/DOM-only) across recipe/menu management, shopping list, pantry, household/profiles, settings, and NO/EN localization - JS console clean throughout. Confirmed working with no action needed: login, adding a custom recipe, generating menus at all day-counts, true day-swap, importing a recipe pack, pantry-based dedup, theme switching, profile creation/switching/removal, and server-side role enforcement.
- Multi-household/multi-user testing (testuser2/testuser3) - this is what surfaced B50 and B51 above. Household-scoped data is otherwise correctly isolated once B50's fix is in place.

### ✨ Features shipped

- **F16:** reorganized the settings (⚙️) dropdown into collapsible groups (Household, Theme, Help, Feedback), reordered to Language → What's New → What's Planned → All Recipes → Add Recipe → Household → Theme → Help → Feedback → Logout.
- **F14:** added a user-facing "What's New" page (`/whats-new`), curated in plain language from this changelog, linked from the settings dropdown.
- **F6 / F15:** added a user-facing "What's Planned" page (`/whats-planned`) listing plain-language roadmap ideas, linking to the existing feedback form for reactions.
- **F13:** added a per-page "← Back" button using real browser history, hidden on the dashboard and unauthenticated pages.
- **F11 (partial):** added a note to the Quick Start Guide that imported recipes are sized for a family of 4.

### 📋 Legal/compliance check (ahead of planned public + paid launch)

Ran a compliance check given the plan to eventually open the app to the public worldwide and add a paid Patreon tier (99 kr/month, 7-10 day trial). Flagged real gaps to close before that specific move (friends-and-family soft launch is unaffected) - see "LAUNCH BLOCKERS" in `BACKLOG_2026-07-01.md` for the still-open items (privacy policy/ToS, trial-to-paid notice, cancellation, right-of-withdrawal disclosure, tax/business registration timing, Patreon terms check).

---

## 2026-07-03 to 2026-07-04

Mobile testing pass plus follow-up user feedback rounds. Most items below were found on live mobile testing, fixed, deployed, and confirmed fixed by re-testing on the live site.

### 🐛 Bug Fixes — confirmed
- **B12:** Second "menu ready" popup after generation removed — only the initial confirmation remains
- **B13:** Household settings page overflowed horizontally on mobile portrait — stacked the members table into cards, fixed text wrapping
- **B14 / B20:** Shopping list and recipe ingredient units had cutting/prep descriptors leaking in ("Gulrot, i skiver" instead of "Gulrot") and inconsistent/English units in Norwegian recipes ("tbsp"/"tsp" instead of "ss"/"ts", "pcs" instead of "stk", plus several other variants). Fixed the seed recipe data (214 units normalized across 13 files) and added an admin "Normalize Recipe Units for All Households" action to backfill already-imported household data (370 units fixed across 2 households)
- **B16:** Shopping list now converts small ml quantities to dl for more natural units (300 ml → 3 dl)
- **B18 / B22:** Settings (cogwheel) dropdown was cut off at the bottom on short mobile screens; fixed to dynamically size to actual available viewport space instead of a fixed guess
- **B19:** Mobile keyboard was popping open on a hidden PIN box when entering Household/Settings — removed a redundant `autofocus` attribute
- **B21:** "Change day" (swap recipe) on the All Recipes page reported success but never actually changed anything — it was writing to an abandoned flat file instead of the household's database row
- **B23:** Pop-Art Diner theme's "?" quick-start button was invisible against its red navbar (the emoji glyph itself is red) — added a contrast backdrop
- **B24:** Settings → Manage Categories list was permanently empty for some households due to a logic bug skipping the base-category merge
- **B25:** The service worker cached every page cache-first forever — the first time any page loaded on a device, it froze that HTML snapshot and never refetched, so any server-side change (swapped day, deletion, etc.) silently never appeared again on already-visited pages. Rewrote to network-first for page navigations, cache-first only for static assets
- **B26:** "Add Family Profile" and "Create Another Household" sections on household settings showed in English regardless of selected language — several translation keys were missing from `i18n.json` entirely

### 🐛 Bug Fixes — shipped, still monitoring
- **B17:** App required relogin after being away / installed as a PWA, plus intermittent "Oops!" server errors. Added persistent 30-day sessions and `pool_pre_ping`/`pool_recycle` on the Postgres connection (stale connections after Render idles out were the likely cause of the Oops errors). Recurrence should be watched over a few more days of normal use.

### 🔧 Infrastructure
- GitHub Actions deploy step was silently dead — it only ran `if: github.ref == 'refs/heads/main'`, but this repo has no `main` branch (only `public-release-v1`), so it had never fired. Replaced with a Render deploy hook triggered on every push to `public-release-v1` that passes tests, so deploys are now actually automatic

### ✨ Improvements / Features
- **F10:** Menu generation now supports a user-selectable number of days (1-6) via a dropdown in the Categories nav panel, instead of always generating 6 dinners
- **F12:** Recipe detail page now has "Change day" and "Delete recipe" (with confirmation) actions, matching what All Recipes already had; button layout fixed to wrap onto its own row instead of overflowing off-screen
- Nav avatar is now clickable, linking to the profile picker to switch users/profiles
- **B27:** Removed "Create Another Household" — it created a second household under the same account, which overlapped confusingly with refer-a-friend and wasn't a supported use case

---

## 2026-07-02

### 📁 Documentation Cleanup
- Deleted outdated files: `DEPLOYMENT.md`, `DEPLOYMENT_STATUS.md`, `RAILWAY_DATABASE_GUIDE.md`, `RECIPE_AUDIT_REPORT_2026-06-30.md`, `BACKLOG_2026-06-30.md`, `docs/SETUP_GUIDE.md`, `docs/FAQ.md`, `docs/EXCEL_GUIDE.md`
- Created `docs/RECIPE_PACK_FORMAT.md` — developer cheatsheet for writing recipe packs
- Created `CHANGELOG.md` (this file) — unified history of all project work
- Updated `README.md`, `SYSTEM_ARCHITECTURE.md`, `FEATURE_ROADMAP.md`, `BACKLOG_2026-07-01.md`, `new_chat_fresh_menu_planner.md`, `docs/DEVELOPER_GUIDE.md`

### 📖 In-App Help System
- Added `❓` button in nav bar → opens Quick Start Guide modal (bilingual, warm and friendly tone)
- Created `/help/advanced` and `/help/tips` routes + bilingual templates
- All 3 guides auto-detect language from `pi_language` cookie
- Help section added to ⚙️ settings dropdown
- Fixed language mixing in guides ("Kyllingmiddager" → "Chicken Dinners", "Basisvarer" → "Pantry" in English)
- Quick Start modal rewritten with warmer tone ("No more staring into the fridge...")

### 🌍 User-Facing Guides Created
- `docs/USER_GUIDE.md` — beginner guide (English)
- `docs/ADVANCED_USER_GUIDE.md` — advanced guide (English)
- `docs/TIPS_AND_TRICKS.md` — power user tips (English)

### 🐛 Bug Fixes
- Pantry remove not persisting — settings page was reading from file, bypassing database
- `db.merge()` unreliable for JSONB saves — replaced with fresh query per save in all routes
- Menu generator saving to file — updated to save to `Household.weekly_menu` JSONB
- Menu generator loading recipes from file — updated to load from `Household.recipes_db` JSONB
- Sample recipes showing "0 min" — generator read `time_minutes` but field is `cookTimeMinutes`
- `_load_pantry_db()` now seeds from file into database on first load (one-time migration trigger)

### ✨ Improvements
- "Reset to defaults" button in pantry settings
- `POST /api/pantry/reset` endpoint
- Real avatar shown in settings dropdown (was showing initials only)
- All 5 unthemed `alert()`/`confirm()` popups replaced with `pmAlert`/`pmConfirm`
- Norwegian translation: "Mitt Forråd" → "Basisvarer"

### 🥗 Recipe Changes
- Moved to `sides-stash.json`: Rekesalat, Potet-og-Agurk Salat, Italiensk Salat, Potetsalat, Medisterpølse
- Enhanced Kjøttkaker: added full meal (brown gravy, potatoes, carrots, lingonberry) with step-by-step instructions in NO + EN

---

## 2026-07-01

### 🚀 F4 Hosting Migration — Railway → Render + Neon (COMPLETE)

**Why:** Railway free trial expiring ~2026-07-27. Household data was in JSON files on Railway's ephemeral volume — every other host would lose data on deploy.

#### Infrastructure
- Created Neon.tech PostgreSQL account (free 3GB tier)
- Created Render.com web service (free tier, GitHub auto-deploy)
- Domain `menuplanner.no` pointed to Render via Cloudflare (A record + CNAME)
- All environment variables migrated from Railway to Render
- Railway services deleted

#### Database Schema
- Added 7 JSONB columns to `Household` model: `recipes_db`, `pantry`, `weekly_menu`, `categories`, `activity_log`, `removed_categories`, `imported_packs`
- Alembic migration: `f6a7b8c9d0e1_add_jsonb_columns_to_households.py`
- Fixed Alembic multiple heads error (F4 migration pointed to wrong parent)

#### Data Layer
- Added 8 `load_*_from_db()` + 8 `save_*_to_db()` functions in `core/household_paths.py`
- Created `scripts/backfill_household_data.py` — migrates JSON files → PostgreSQL JSONB
- Self-heal logic preserved for categories (never re-adds deleted categories)

#### Flask Refactoring
- Added `current_household()` helper to get Household ORM object per request
- Added `_load_pantry_db()` / `_save_pantry_db()` wrappers
- All pantry, menu, recipe, category routes updated to use database

#### Deployment Challenges Solved
- Render defaulted to Python 3.14 — SQLAlchemy 2.0.x incompatible → forced Python 3.11 via build command
- gunicorn not in PATH at runtime → used `python3.11 -m gunicorn`
- Alembic "multiple heads" blocked build → fixed migration chain
- `db.merge()` on detached objects unreliable → replaced with fresh session queries

### 🐛 Bug Fixes
- Admin panel security: family profiles could access `/admin` — fixed by checking `active_profile_id`
- Generate menu not redirecting to home page after generation
- Category dropdown in "Add Recipe" was hardcoded — made dynamic via `/api/categories`
- CSS selector `option[value!=""]` invalid — fixed to `option:not([value=""])`
- Empty categories still generating 6-day menu — now returns 400 error
- Recipe moves to Uncategorized when its category is deleted (not lost)
- SSL certificate issue on `menuplanner.no` — fixed DNS + Cloudflare redirect rules

### ✨ New Features
- v1.2.0 release tagging all above work
- Favourites + categories now use union (OR), not intersection (AND)

### 🥗 Recipe Changes
- Recipe audit: 3 recipes had multi-sentence instruction steps — all fixed
- `tex_001` (Beef Tacos), `tex_002` (Chicken Enchiladas), `sum_027` (Poke Bowl) fixed

---

## 2026-06-30

### 🥗 Recipe Pack Rework (Preload3)
- Replaced 5 geographic packs with 12 dish-type packs (Norwegian, Italian, Tex-Mex, Grill, Salads, Summer, Holiday, Fish & Seafood, Ground Meat & Sausages, Quick Dinners, Pasta & Noodles, Vegetarian)
- 4 new Tex-Mex recipes written: Beef Tacos, Chicken Enchiladas, Nachos, Quesadillas
- 90 desserts + 4 drinks + 16 sides removed from dinner pool and stashed
- Quick Dinners now a real category (108 recipes tagged `quick`)
- Pack-name pseudo-categories removed from all dropdowns
- Cuisine tags added to all recipes (`cuisine:norwegian`, `cuisine:italian` etc.)
- Pack import now upserts (re-importing updates stale data, no duplicates)

### 🐛 Bug Fixes
- Railway volume freezing static seed data — fixed with `SEED_DIR` separation
- Button sizing: `btn-primary` was forcing `width:100%` globally — fixed
- Second "menu is ready" popup removed after regeneration (page reload is enough)
- Hide cuisine/quick filter tags from UI (internal only)
- Sample recipes `sample_recipes.json` fully rewritten — original had wrong ingredients and instructions (copy/paste errors from original writing)

---

## 2026-06-29

### ✨ Features
- Email confirmation system (signup → email → confirm link → login gating)
- Unified Favourites system across all recipe pages
- Pantry items shown in collapsible "Already have these" section on shopping list
- Removed servings scaling (too confusing — users edit recipe quantities directly)
- Recipe expansion: +151 recipes across 5 packs (368 total), all bilingual

### 🐛 Bug Fixes
- Railway persistent volume permission denied error — fixed
- CI test isolation bug causing random failures — fixed
- Atomic writes for `recipes_db.json` (prevents corrupt JSON on crash)

---

## 2026-06-28

### ✨ Features
- Welcome/demo landing page for non-logged-in visitors
- Referral system (code generation, link sharing, signup attribution)
- Phase 3: Referral tracking, co-owner role, profile management, data isolation
- Avatar sync between nav bar and profile picker

### 🐛 Bug Fixes
- `debug=True` accidentally left on in production entry point — fixed
- Flask route reference error in `base.html` — fixed
- Settings page locked down for non-owners (profiles can't change household settings)

---

## 2026-06-27

### 🏗️ Phase 2 — Cloud SaaS Platform (all tasks in one day)

**Task 1 — Database layer**
- SQLAlchemy ORM + Alembic migrations set up
- SQLite (local dev) + PostgreSQL (production) both supported
- Models: `User`, `Household`, `HouseholdMember`, `Recipe`, `RecipeIngredient`, `WeeklyMenu`, `ShoppingList`

**Task 2 — User authentication**
- Email/password signup and login
- Password hashing (pbkdf2:sha256)
- Flask-Login session management

**Task 3 — Household management**
- Role-based access: owner / editor / viewer
- Multiple users per household
- Household switching in session

**Task 4 — Railway cloud deployment**
- Railway.json config
- Procfile for gunicorn
- Python 3.11 specified
- PostgreSQL plugin connected
- Healthcheck endpoint added

**Task 5 — GitHub Actions CI/CD**
- `tests.yml`, `lint.yml`, `security.yml`, `build.yml`, `frontend-checks.yml`, `data-validation.yml`, `release.yml`
- Pre-commit hooks for secret detection

**Phase 3 — Netflix-style family profiles**
- Profile picker (like Netflix — choose who's using the app)
- Avatar system (emoji + custom)
- PIN support for quick profile switching
- Alembic migration: profile fields on `HouseholdMember`
- Alembic startup loop fix (stamp pre-existing schema before upgrade)

### 🐛 Bug Fixes (day full of Railway deployment fixes)
- Duplicate `/health` route crashing gunicorn at boot — fixed
- `users` table missing in Postgres (models not imported before `create_all()`) — fixed
- Login form missing `action` attribute — fixed
- Household name showing literal `{Family_Name}` placeholder — fixed
- `fix end of file` and multiple small CI fixes

### ✨ Other
- Docker support added
- Shopping list checkboxes with localStorage persistence
- Recipe edit endpoint (`/api/edit-recipe`)
- Pantry staples filter fixed (correct JSON keys)
- Pantry staples expanded (Norwegian sugar types, powdered sugar)
- Phase 1 complete: recipe edit UI, comment field persistence, improved deduplication

---

## 2026-06-19

### 🎨 Theme Work
- 8 themes finalised (1 hardcoded + 7 registry)
- Chalkboard Bistro theme: black text enforcement fixes
- Nordic Pantry → Chalkboard → Terracotta → Warm Modern ordering
- Theme submenu toggle fixes
- Pre-commit security hooks for secret detection
- Patreon links updated to direct Menu Planner post

---

## 2026-06-17

### ✨ Features
- Shopping list integrations: Microsoft To Do, Todoist, TickTick, Apple Reminders, CSV/JSON/Text/ICS export
- Complete bilingual system overhaul
- Shopping list management features

---

## 2026-06-16

### ✨ v1.1 Features
- Recipe Pack Import UI (pack selection modal, one-click import, manage imported packs)
- 72+ bilingual recipes across 5 curated packs
- Personal Recipe Arsenal (export/import JSON packs)
- Feature roadmap added
- Default language changed to English
- Testing guide for v1.1

---

## 2026-06-15

### 🚀 v1.0 Public Release (Pi-Menu)

**The original Raspberry Pi local meal planner.**

Built in a single day across 10 phases:

| Phase | What Was Built |
|-------|---------------|
| 1 | Clean up project structure and remove early prototype code |
| 2 | Remove hardcoded credentials, create `.env` template |
| 3 | Clean up file headers and references |
| 4 | Replace initial recipes with proper public sample recipes |
| 5 | Dynamic category system |
| 6 | Parameterise family name (no hardcoded references) |
| 7 | Bilingual support (Norwegian + English, persistent toggle) |
| 8 | Measurement conversion system (metric ↔ imperial) |
| 9 | Comprehensive documentation + guides |
| 10 | Final release — Pi-Menu v1.0 Public |

**Autonomous improvement passes:**
- Phase 1: Enhanced tooling + testing suite
- Phase 2: UI/UX improvements + developer documentation
- API endpoint testing suite added

---

## 2026-06-14

### 🌱 Project Start

**Initial Pi-Menu commit — core features ready for deployment.**

The project started as a personal Raspberry Pi meal planner built for my own family:
- Weekly menu generation from a local recipe JSON file
- Shopping list with ingredient deduplication
- Norwegian UI
- Single-household, single-user design
- Flask running locally on the Pi at port 5000

What started as a tool just for us quickly showed potential for other families too. Everything above describes the journey from a Pi-only local tool to a full cloud-hosted multi-household web app at **menuplanner.no**.
