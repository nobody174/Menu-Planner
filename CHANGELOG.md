# Menu Planner — Project Changelog

Complete history of all work done on the project, newest first.
See `BACKLOG.md` for open tasks and `FEATURE_ROADMAP.md` for planned features.

---

## 2026-07-09 (4)

### CI: fixed two real pipeline problems found while shipping M3/B61's PR

**1. Branch protection required a check that no longer exists.**
`public-release-v1`'s required status checks still listed "Stage 2: Build
Docker Image" - deleted from `ci.yml` as part of M3, but never removed from
GitHub's branch protection settings. Every PR merge attempt was blocked
indefinitely waiting for a check that would never report. Updated the
required-checks list via the GitHub API to match the actual workflow (8
checks now, not 9) - also added "Stage 2: Visual Regression (Playwright)",
which turned out to have never actually been added as required despite
existing in the workflow since 2026-07-07.

**2. Every push to `main` while a PR was open fired two full pipeline runs
for the same commit** - one for the `push` event, one for the PR's
`synchronize` event - doubling real GitHub Actions job load and queue time
on every single push. Added a `concurrency` block to `ci.yml`
(`group: ${{ github.workflow }}-${{ github.head_ref || github.ref }}`,
`cancel-in-progress: true`) so the older, now-redundant run for the same
branch gets cancelled instead of piling up. Doesn't affect deploy safety -
Stage 3 only runs on a real push to `public-release-v1`, which has no open
PR pointed at it by the time that push happens.

Both found live, mid-session, while merging PR #6 (M3 + B61) - the PR
itself was correctly green throughout; these were pre-existing pipeline
configuration problems the merge attempt exposed, not caused by that PR's
code changes.

---

## 2026-07-09 (3)

### B61 fully resolved: production verified clean without Shell access, every dead file-fallback branch deleted, two real bugs found and fixed along the way

Follow-up to the "(2)" entry below, once a way to verify production without
paid Render Shell/Disk access was found. Owner ran `SELECT id FROM
households;` directly in Neon's own SQL console (Neon hosts the Postgres
DB, separately from Render): exactly 3 households, all real DB rows.
Separately confirmed via the Render dashboard that this service has never
had a persistent Disk attached (it's a paid add-on, and the Disks tab shows
an upsell rather than an existing disk) - meaning the filesystem resets on
every deploy, so a file-only household could not have survived any deploy
to exist today. That combination was enough to proceed with full confidence
- no need to actually run `scripts/verify_no_file_only_households.py`
against production after all (kept in the repo anyway as a general
diagnostic).

**Traced every direct caller of the file-based functions across the whole
codebase**, not just the `"if not household"` pattern originally scoped -
this surfaced two genuinely active bugs, not dead fallback code:

- **`/shopping` called `core.household_paths.load_pantry()` directly and
  unconditionally** (not inside any fallback branch). That function both
  reads *and* reseeds a fresh default-staples `pantry.json` file on every
  call - so the shopping list's "already have this" pantry match was
  silently comparing against a stale reseeded default pantry, not the
  household's actual customized DB pantry (anything added/removed via
  `/api/pantry` was ignored on this one page). Fixed to use
  `_load_pantry_db()`, the same DB-backed function `/api/pantry` itself
  already used.
- **Same route also read `recipes_db_file()` directly** for the Norwegian
  ingredient-name rebuild - a file real households never write to (their
  imported/custom recipes live in `household.recipes_db`, the DB column) -
  so those recipes' ingredients silently never contributed a Norwegian name
  here. Fixed to use `load_recipes_db()` instead.

**Also found `core/menu_generator.py`'s constructor unconditionally created
a household's file directory on every single menu generation** - via eager
`recipes_db_file()`/`categories_file()`/`menu_file()` calls, which trigger
`household_dir()`'s side effect (creates `data/households/<id>/`, copies
seed files) - even though those paths were only ever actually read inside
genuine DB-exception fallback branches. Made all three lazy (computed only
if a real DB failure reaches the fallback code, not in `__init__`). Also
deleted `load_categories()`/`self.categories` entirely: tracing showed the
result was assigned and never read by anything else in the class - pure
dead weight, unrelated to the DB/file question, just found along the way.

**Deleted 11 now-fully-dead functions** from `core/household_paths.py`
(`categories_file`, `mark_category_removed`, `load_removed_categories`,
`_removed_categories_file`, `activity_log_file`, `append_activity`,
`load_activity`, `pantry_file`, `_pantry_seeded_marker`, `load_pantry`,
`save_pantry`) after confirming zero real callers remained anywhere.
Removed every `"if not household: fall back to file"` branch in
`deployment/app_core.py` (`load_menu`, `save_menu`, `load_recipes_db`,
`save_recipes_db`, `_load_household_categories`,
`_save_household_categories`, `_mark_category_removed`, `log_activity`)
and `deployment/routes/menu_routes.py` (regenerate, swap-recipe,
reroll-recipe - 5 occurrences total). Kept `household_dir()`/`menu_file()`/
`recipes_db_file()` themselves - still genuinely used as the last-resort
inside `menu_generator.py`'s real DB-exception fallback, not dead.

**New finding, deliberately NOT fixed this session:**
`load_imported_packs`/`save_imported_pack_metadata`/
`remove_imported_pack_metadata` (a recipe pack's display name/icon/color on
"Manage Recipe Packs") turned out to be the *only* implementation for that
feature - unlike every other data type traced, it was never actually wired
to the `imported_packs` DB column that exists for exactly this purpose
(`load_imported_packs_from_db`/`save_imported_packs_to_db` are defined but
have zero real callers anywhere in the app). Given no persistent Disk, this
metadata likely doesn't survive a redeploy today. The packs' actual
recipes are safe (properly DB-backed) - only this cosmetic display
metadata is at risk. Left untouched - this needs a real fix (wiring
`deployment/routes/recipe_pack_routes.py` to the DB functions), not a
delete-dead-code pass, and deserves its own careful session. Added as a
new item in `docs/BACKLOG.md`.

**Verified:** 4 new tests (`tests/test_pantry_routes.py::TestPantrySeedNoFileIO`
x2, `tests/test_shopping_list_db_paths.py` x2) plus a live manual smoke
test against the real local dev server as an existing real user
(login → dashboard → `/api/pantry` → `/shopping` → `/api/categories`, all
200, zero errors in the server log across the whole session). Full suite
green: 270/270. `python -m flake8 ... --select=E9,F63,F7,F82` (CI's actual
blocking lint check) clean.

`docs/BACKLOG.md`'s B61 entry marked resolved; new imported-packs item added.

---

## 2026-07-09 (2)

### B61 investigated in full: one real fix landed, rest genuinely needs production verification

Traced all 7 JSONB household data types (`recipes_db`, `pantry`,
`weekly_menu`, `categories`, `activity_log`, `removed_categories`,
`imported_packs`) to find out what the backlog's "confirm whether any
production household still uses the file path" actually meant in practice
- turned out narrower than expected. `recipes_db`/`weekly_menu`/
`activity_log`/`imported_packs`'s DB loaders have no file fallback at all -
a `None` column just correctly means "empty." `categories` self-heals
directly from the static seed file, no per-household file involved. Only
`pantry` and `removed_categories` actually touched per-household files on
read.

**Fixed: pantry's redundant per-household file round-trip.**
`_load_pantry_db()` (`deployment/app_core.py`) used to seed a fresh
household's `pantry` column by calling `core.household_paths.load_pantry()`
- which wrote a per-household `pantry.json` + `.pantry_seeded` marker file
purely to hold the same static staples content every household gets, real
disk I/O for data that was never actually household-specific at seed time.
Added `default_pantry_staples()` in `core/household_paths.py` (pure read of
the static seed file, zero household-specific I/O) and switched
`_load_pantry_db()` to seed directly from it. A brand-new household's very
first pantry read no longer touches disk at all.

Verified: 2 new tests
(`tests/test_pantry_routes.py::TestPantrySeedNoFileIO`) confirm a fresh
household's first `/api/pantry` read seeds correctly with the full staples
list and creates zero household directory on disk. Full suite green
(268/268, up from 266).

**Left alone, deliberately:** the `"if not household: fall back to file"`
branches scattered across `load_menu`/`save_menu`/`load_recipes_db`/
`save_recipes_db`/`_load_household_categories`/`_save_household_categories`/
`_mark_category_removed`, and `removed_categories`'s one-time file-tombstone
migration-compat read. Every household gets a DB row at creation today, so
these should be unreachable dead code - but "should be, per reading the
code" isn't the same as "confirmed against real production data," and I
don't have production DB access to check. Deleting them without that
verification would be the actually risky move here, not leaving them.
Added `scripts/verify_no_file_only_households.py` - a read-only script
(run via Render Shell against production) that diffs `data/households/`
directories against real `households` table rows. Once that comes back
clean, the remaining fallback branches can be deleted with real confidence.

`docs/BACKLOG.md`'s B61 entry updated with the full trace and next step.

---

## 2026-07-09 (1)

### M3 resolved: deleted the dead Railway-era Docker deployment path

Confirmed which of the two contradictory deployment definitions this repo
carried was actually live: `docs/DEVELOPER_GUIDE.md`'s documented Render
Build/Start commands (`pip install ... && alembic upgrade head` /
`gunicorn -b 0.0.0.0:$PORT deployment.flask_app:app`) match `Procfile`'s
single-worker invocation exactly - that's the native Python buildpack, not
Docker. `docker-entrypoint.sh` explicitly referenced Railway persistent
volumes throughout (a different, no-longer-used hosting platform), and no
`render.yaml` or any Docker-based Render config existed anywhere in the
repo. Render never ran the Dockerfile at all.

Deleted `Dockerfile`, `docker-compose.yml`, `docker-entrypoint.sh`, and the
now-orphaned `.dockerignore` outright, along with the CI "Build Docker
Image" job (`.github/workflows/ci.yml`) and its slot in the `deploy` job's
`needs:` list - it was one of the 9 required status checks gating merges
into `public-release-v1`, now 8. Chose full deletion over keeping the
Dockerfile as a buildable-only smoke test, per explicit owner preference.

Also fixed two comments this cleanup surfaced: `deployment/app_core.py`'s
`SEED_DIR` used to describe pointing at `/app/data-seed`, a directory only
the (now-deleted) Dockerfile ever created - since Render never ran that
Dockerfile, this was already always silently falling through to the
`DATA_DIR` fallback in the real deployment, every time; simplified to just
`SEED_DIR = DATA_DIR` directly rather than keeping dead existence-check
logic around. And `deployment/flask_app.py`'s B57 entry-point comment no
longer lists Docker among what actually runs `gunicorn deployment.flask_app:app`.

Verified: full pytest suite green (266/266) after the code changes; YAML
syntax-validated `ci.yml` after the job removal.

`docs/BACKLOG.md`, `docs/FEATURE_ROADMAP.md`, `docs/CI_CD_PIPELINE.md`,
`docs/DEVELOPER_GUIDE.md`, and `CLAUDE.md` updated to drop every reference
to the deleted Docker path and the now-8 (not 9) required checks.

---

## 2026-07-08 (2)

### Bookkeeping cleanup: renamed backlog file, backfilled the missing 2026-07-07 changelog entries

The prior session (2026-07-07: comprehensive audit + B57 blueprint split +
QA pass B53-B68) did a large amount of real, verified work but never wrote
any of it up here - `CHANGELOG.md` jumped straight from `2026-07-06 (13)`
to this file's own `2026-07-08` entry with nothing in between, and
`docs/BACKLOG_2026-07-01.md` (see rename below) still listed roughly a
dozen items as open that were already fixed that same day. Caught only
because the user asked "are you sure everything's actually reflected here"
after spotting the file's own header contradicting its filename.

Fixes, in order:
1. Re-audited every open backlog item against the actual code (not the
   backlog's own prior text) - found M1, M2, M4, M5, M6, B56, B57, and B59
   were all already resolved 2026-07-07 and never marked as such.
2. Renamed `docs/BACKLOG_2026-07-01.md` → `docs/BACKLOG.md`. The file is a
   living, continuously-edited document, not a dated snapshot (unlike
   `docs/AUDIT_2026-07-07.md`, which correctly *is* one) - a date baked
   into the filename of something that changes every session is
   guaranteed to go stale the first time anyone updates it without also
   renaming the file, which is exactly what happened here. Dates that
   matter now live inside the file's own entries instead. Updated every
   reference across the repo (`CLAUDE.md`, `README.md`,
   `docs/FEATURE_ROADMAP.md`, `docs/AUDIT_2026-07-07.md`,
   `deployment/app_core.py`, `deployment/flask_app.py`, this file).
3. Backfilled the two missing 2026-07-07 entries below, covering the
   audit/hardening/blueprint-split pass and the separate QA pass (B53-B68)
   that also went unlogged.
4. Trimmed `docs/BACKLOG.md`'s resolved-item entries down to short
   pointers back to these changelog entries, restoring the file's own
   stated contract ("this file holds only what's still genuinely open").

---

## 2026-07-08 (1)

### Security Hardening PR: closed the M8 CSP gap, added missing test coverage (H2, M7, LO1, M8)

Scoped audit of the four items together (H2 rate limiting, M7 account
enumeration, M8 security headers, LO1 body size cap). Found H2, M7, and
LO1 were already fully implemented and (for H2/M7) already tested as of
the 2026-07-07 audit session - verified each against the actual code
(`deployment/app_core.py`, `core/auth_helpers.py`,
`deployment/routes/auth_routes.py`) rather than trusting the backlog
text alone.

M8 was only partially done: `X-Frame-Options`, `X-Content-Type-Options`,
`Referrer-Policy`, and HSTS were live, but no `Content-Security-Policy`
header existed at all, despite a comment claiming it was "intentionally
deferred." Added a permissive-but-real CSP (`deployment/app_core.py`) -
`object-src 'none'`, `frame-ancestors 'none'`, `base-uri 'self'`,
`form-action 'self'`, restricted `frame-src`/`img-src`/`font-src`/
`style-src` - rather than a strict nonce-based policy, since the app
relies on inline `<script>`/`<style>` throughout its templates and a real
nonce audit is a separate, larger effort (unchanged conclusion from the
original audit). Confirmed via `grep` this covers the app's entire actual
external surface: Google Fonts `@import`s and two YouTube iframe embeds,
no external `fetch()`/XHR calls anywhere.

Added `tests/test_security_headers.py` (3 tests: headers present on a
normal response, HSTS absent outside production, oversized request body
rejected with 413) - M8 and LO1 had zero test coverage before this.
Full suite verified: 266/266 passing.

Also verified live against the local dev server, and in doing so found
the launch command in scratch/session notes was stale - `deployment/`
became a real package during the B57 blueprint split (2026-07-07), so
`python deployment/flask_app.py` no longer works
(`ModuleNotFoundError: No module named 'deployment'`, by design - see the
comment left at the old entry-point site in `flask_app.py`). Correct
command is `python -m flask --app deployment.flask_app run --host=0.0.0.0
--port=5000` (matches `RUN_LOCAL.bat`/`RUN_LOCAL.ps1`, already updated for
this in the same prior session).

**No further code changes needed for H2/M7/LO1** - confirmed correct as
built. `docs/BACKLOG.md` updated to reflect all four items resolved.

---

## 2026-07-07 (2)

### Comprehensive read-only audit → same-day fix pass: C1, H1-H3, M1-M2, M4-M7, LO1, LO8, B56, B57, B59, B60

Ran a full read-only architecture/security/QA audit (`docs/AUDIT_2026-07-07.md`,
verified against a clean `main`) ahead of the planned public + paid launch,
then fixed everything it found the same day except M3 (deployment
split-brain) and B61 (dual storage path consolidation), both left as
deliberate technical debt for a dedicated pass later.

**Critical**
- **C1 — shopping-list export/sync likely broken in production.** Both
  `/api/export-shopping-list` and the Apple Reminders sync path used a bare
  `from shopping_integrations import ...`, which only resolves when
  `flask_app.py` is run as a standalone script (auto-adds its own
  directory to `sys.path`) - not under gunicorn's `deployment.flask_app:app`
  invocation, which is what production actually runs. The route's own
  try/except silently swallowed the resulting `ImportError` and 500'd.
  Fixed to `from deployment.shopping_integrations import ...`; live-tested
  CSV export end-to-end to confirm.

**High**
- **H1 — `SECRET_KEY` silently fell back to a random per-process value.**
  Owner confirmed `FLASK_SECRET_KEY` genuinely is set on Render, so this
  wasn't B17's root cause after all - fixed anyway as insurance: now
  raises `RuntimeError` at boot if the key is missing *and*
  `FLASK_ENV=production`, instead of silently minting a key that would
  invalidate every session on every restart.
- **H2 — no rate limiting on `/login`, `/signup`, `/forgot-password`.**
  Added `flask-limiter` (in-process memory store, fine at the current
  single-worker Render deployment): `/login` 10/min, `/signup` 10/hour,
  `/forgot-password` and `/resend-confirmation` 5/hour each.
- **H3 — `/themes` gallery route 500'd.** Listed a directory
  (`frontend/static/theme-previews/`) that never existed - dead route from
  the theme refactor era, no nav link anywhere pointed to it. Deleted both
  `/themes` routes; `theme_gallery.html` was left orphaned this session
  (sandbox couldn't delete it) and removed in a later pass.

**Medium**
- **M1 — account deletion could fail or leave dangling references.**
  `delete_user_account()` never touched legacy relational `Recipe`/
  `WeeklyMenu`/`ShoppingList` rows (superseded by JSONB columns but still
  FK-constrained in Postgres) or nulled `referred_by_user_id` for accounts
  this user had referred - either could roll back the whole deletion on a
  real FK violation, undermining the GDPR erasure promise the not-yet-written
  privacy policy (L1) will make. Now clears both defensively.
- **M2 — category-deletion tombstones only ever wrote to the filesystem**,
  never to the `removed_categories` JSONB column that exists for exactly
  this purpose - a disk loss on Render would have silently resurrected
  every category a household had deleted. Added the DB-writing path
  (`flag_modified()` + `removed_categories` column), file path kept only
  for genuinely un-migrated households.
- **M4 — silent write-failure swallowing.** `save_recipes_db()` and
  `_save_pantry_db()` caught DB commit exceptions, `print()`'d them, and
  returned normally - routes reported success on a lost write, the same
  "200 success, nothing saved" class of bug as B53/B63. Now propagates the
  real exception instead.
- **M5 — API 500s/404s/CSRF errors returned HTML to JSON clients.** Added
  branching in all three global error handlers: a JSON response for any
  `/api/*` path, the existing HTML error page for everything else. This is
  exactly why B63's frontend error handling previously had to guess at a
  non-JSON response instead of reading a real error message.
- **M6 — `current_household_id()` re-queried the DB on every single call**
  (46 call sites, several per request). Now cached on `flask.g`, one query
  per request; verified no cross-request leakage via a dedicated test
  (`tests/test_request_scoped_caching.py`).
- **M7 — login/resend-confirmation leaked which emails were registered**,
  plus a timing oracle (no-such-user skipped the password hash entirely).
  `authenticate_user()` now returns one generic error for both cases and
  runs a dummy hash comparison on the no-such-user path so timing doesn't
  give it away either. `/resend-confirmation` returns one generic message
  regardless of account state.

**Low**
- **LO1 — no request body size limit.** Set `MAX_CONTENT_LENGTH` to 5MB.
- **LO8 — misc cosmetics.** Removed a duplicate import in
  `delete_own_account`; fixed household-folder cleanup on self-deletion
  actually running (it captured `current_household_id()` *after* the user
  row was already gone, so it always silently no-op'd); removed a
  meaningless `"https"` field from `/health`.

**B56 — missing DB indexes.** Added indexes on `households.owner_id`,
`household_members.household_id`/`user_id`, `recipes.household_id`,
`weekly_menus.household_id`, `shopping_lists.household_id`
(`alembic/versions/d7ad4d9fa3eb_add_missing_indexes_b56.py`).

**B57 — the big one: split `flask_app.py` (~4,700 lines, ~80 routes, one
module scope) into an app-factory + blueprints.** New `deployment/app_core.py`
holds `create_app()` (config, CSRF, rate limiter, security headers, error
handlers, i18n, jinja globals) plus every shared helper function, unchanged
from its original `flask_app.py` version except where it needed wrapping
inside `create_app()` to access `app` directly. Seven new
`deployment/routes/*.py` blueprint modules (auth, admin, household,
pantry_category, menu, recipe, recipe_pack) hold the actual route bodies,
moved verbatim. `flask_app.py` itself is now just the entry point + blueprint
registration (731 lines). Rate-limit decorators needed a `register(bp,
limiter)` pattern per blueprint module rather than bare `@limiter.limit(...)`
at import time, since the real `Limiter` instance doesn't exist until
`create_app()` runs. **Breaking change for local dev:** `deployment/` is now
a real package with absolute imports, so `python deployment/flask_app.py`
no longer works (doesn't put the project root on `sys.path`) -
`RUN_LOCAL.bat`/`RUN_LOCAL.ps1` updated to `python -m flask --app
deployment.flask_app run --host=0.0.0.0 --port=5000` instead.

**B59 — zero route-level test coverage.** Added the recommended smoke-test
starter (`tests/test_routes_smoke.py`: hits every registered route both
logged-in and logged-out, asserts none 500) plus real coverage on the
previously-untested high-complexity routes: `tests/test_menu_mutation_routes.py`
(swap/reroll/regenerate), `tests/test_pantry_routes.py`,
`tests/test_category_routes.py`, `tests/test_api_error_handlers.py`,
`tests/test_login_signup_csrf.py` (also the first tests to actually
exercise CSRF protection at all, rather than disabling it for every test).

**B60 — dead code housekeeping.** Removed a pointless f-string with no
interpolation and a leftover `if __name__ == "__main__":` self-test block
in `core/menu_generator.py` (confirmed unused first).

Full pytest suite green throughout. `docs/AUDIT_2026-07-07.md` has the
full findings detail this summary condenses.

---

## 2026-07-07 (1)

### QA / production-readiness pass: B53-B55, B60, B63, B65-B68 fixed; B58 investigated (still open); B64 decided against

Full code + live-functional review following up on the 2026-07-06 QA
session's findings (see that date's entries for the session itself).

- **B53 — silent partial/degraded menu generation.** A household with
  fewer eligible recipes than the requested day count got a `200 success`
  with a shorter menu and no indication why. `generate_menu()` now records
  the requested vs. actual day count; `/api/regenerate` surfaces a
  structured warning the frontend shows as a one-time dismissible banner
  on dashboard load.
- **B54 — CI's dependency vulnerability scan didn't gate anything.**
  `safety check || true` never failed the build even on a real finding,
  and modern `safety` (v3.x) requires a hosted-platform login just to run,
  so it may have been silently failing to even authenticate. Ran
  `pip-audit` (free, offline) directly, found 13 real CVEs across 5
  packages, bumped all 5 pins to patched versions, switched CI's security
  scan job to `pip-audit` with the `|| true` removed entirely.
- **B55 — All Recipes search had no "no results" empty state.** Searching
  a nonsense term correctly hid every card but left a blank page with no
  message and a heading still showing the unfiltered total. Added a live
  result count and a "No recipes found" empty state.
- **B60 — dead code**: pointless f-string, leftover self-test block in
  `menu_generator.py` (see also the 2026-07-07 (2) entry above, same fix).
- **B63 — SQLite concurrency bug, genuinely affecting live usage, not just
  CI.** The 🎲 reroll and recipe-search swap buttons intermittently failed
  with a blank client-side error. Root cause: SQLAlchemy's `StaticPool`
  forced every thread onto one shared raw sqlite3 connection, and Flask's
  threaded dev server corrupted that connection's cursor state under real
  overlapping requests. Two fix attempts made things worse first (a global
  connection lock deadlocked the whole app on any request dying mid-flight;
  `threaded=False` choked on a real browser's multiple simultaneous
  connections per page load) before landing on the actual fix: SQLite's own
  WAL journal mode + a 5s `busy_timeout`, with `StaticPool` switched back to
  a normal per-thread pool (WAL needs separate connections per thread to
  work). Verified with 24 concurrent requests, 0 failures. Production
  (gunicorn + Postgres) was never affected.
- **B65 — All Recipes never collapsed to a mobile layout.** An inline
  `style="display: grid; grid-template-columns: 280px 1fr"` attribute
  always wins over any CSS rule regardless of selector specificity, so the
  mobile media query trying to override it could never fire - the sidebar
  took its full 280px on every viewport, pushing content almost entirely
  off-screen on phones. Moved the layout into a real `.all-recipes-layout`
  class so the existing (already-correct) media queries could finally apply.
- **B66 — "Import Recipe Packs" on All Recipes linked to the wrong page**
  (a management page with no actual import control). Moved the import
  modal's markup/CSS/JS out of `settings.html` into the shared `base.html`
  so any page can open it directly; All Recipes' button now opens it in
  place.
- **B67 — auto-tagged versions never got a GitHub Release.** The CI
  deploy job's auto-tag push used `GITHUB_TOKEN`, which GitHub deliberately
  blocks from triggering other workflows (anti-loop protection) - so
  `release.yml`'s tag-push trigger never fired for any auto-tag, ever,
  despite the tags genuinely existing. Fixed by creating the Release
  directly inside the same deploy job instead of relying on a second
  workflow to catch the tag push.
- **B68 — Playwright e2e seed data was non-deterministic**, causing a real
  CI flake on a push that touched no template/CSS/JS at all -
  `e2e/seed_test_data.py` never passed a `seed=` to `MenuGenerator`, so
  every run produced a different random weekly menu, which any committed
  visual-regression baseline could only ever match by chance. Fixed with a
  fixed `seed=42`; regenerated every affected baseline.
- **B58 — Firefox-only white block at the bottom of the page — still
  unresolved.** Tested all 4 key pages in a real Firefox engine via the
  new Playwright MCP at default viewport, a shortened viewport (`100vh`
  hypothesis), and with the settings dropdown open (`backdrop-filter`
  hypothesis) - could not reproduce in any of these. Genuinely still open;
  needs the exact page/window-size/screenshot from whoever saw it, or it
  surfaces on its own via the new Playwright CI suite.
- **B64 — welcome-page marketing videos — decided to keep the originals.**
  Built two automated candidate replacement videos (Playwright screen
  recording + moviepy trimming/captions/fades + a generated original
  soundtrack, since no free-music source had a clean unauthenticated
  download path). Neither captured everything wanted, and the UI is still
  changing fast enough that re-recording now would likely need redoing
  soon anyway - kept the live videos, owner plans to record new ones once
  the UI settles.
- **B62 — Playwright MCP + CI suite shipped** (researched and written up
  2026-07-06, actually installed and wired up this session): MCP
  registered for interactive Firefox/Chromium/WebKit checks during
  development; a 7-project Playwright test suite (3 desktop browsers + 4
  device viewports) with `toHaveScreenshot()` visual-regression checks
  added to CI, gating Stage 2 - a rendering regression on any of the 7
  environments now blocks deploy automatically.

---

## 2026-07-06 (13)

### Researched: automated cross-browser/cross-device testing (no more manual DevTools swapping)

Prompted by hitting real friction this session: manually testing responsive layouts required a human to open DevTools, pick a device preset from a dropdown, and tell Claude which one was selected each time - and a genuine Firefox-only bug (white block at the bottom of a page, not reproducible in Chrome or Edge) couldn't be diagnosed at all without a real Firefox engine, which this sandbox can't run (outbound access to Playwright's browser-binary CDN is blocked by the sandbox's network allowlist).

Dispatched two research subagents to find a genuinely free, unattended solution rather than guessing. Verified conclusion: install Playwright MCP (`microsoft/playwright-mcp`, confirmed actively maintained) for live interactive checks during development (`claude mcp add playwright npx @playwright/mcp@latest`), plus a Playwright test suite added to CI (`.github/workflows/ci.yml`) covering chromium/firefox/webkit x several device viewports, with `toHaveScreenshot()` visual-regression diffing to catch exactly this class of Firefox-only rendering bug automatically on every push. Confirmed fully free (GitHub Actions minutes free/unlimited on a public repo, Playwright's snapshot diffing is self-hosted). Cloud device farms (BrowserStack/Sauce Labs/LambdaTest) were checked and ruled out - their current free tiers are thin, time-limited trials, not worth it for this bug class.

Written up in full in `docs/BACKLOG_2026-07-01.md` (B62). Not yet implemented - next step is for Claude Code (running locally, with real unrestricted internet access) to actually install and wire this up.

---

## 2026-07-06 (12)

### Nav cleanup: moved What's New/Planned into Help, reordered Add Recipe / All Recipes

More feedback from a friend testing the app: "What's New" and "What's
Planned" sat as top-level items in the ⚙️ settings menu, right next to
"All Recipes" and "+ Add Recipe" — he read "What's Planned" as "what's
planned for my weekly menu" rather than what it actually is (the app's
own feature roadmap), which is a reasonable misread given where it was
sitting.

Moved both links (`frontend/templates/base.html`) into the existing
collapsed "Help" submenu, alongside Quick Start Guide / Advanced Guide /
Tips & Tricks — all app-level info, not menu-planning actions, so grouping
them together should remove the ambiguity without needing to rename
anything.

Also swapped the order of "+ Add Recipe" and "All Recipes" per his
preference (Add Recipe now listed first).

---

## 2026-07-06 (11)

### Added: reroll-one-recipe and search-and-pick-a-recipe dashboard controls

Feedback from a friend testing the app: swapping out just one day's dinner
required going to All Recipes and using its per-recipe "Swap Day" dropdown,
which wasn't discoverable from the dashboard itself, and there was no way
to just get a different random suggestion for one day without regenerating
the whole week.

Added two small buttons under each day card on the dashboard (both the
standard and rich/terracotta layouts):

- 🎲 **Reroll** — `POST /api/reroll-recipe {day}` (new,
  `deployment/flask_app.py`). Picks a different random recipe for that day
  only, staying within the current recipe's category where possible (falls
  back to any unused recipe if the category has nothing left), and never
  picks a recipe already used elsewhere in the week — same no-duplicates
  guarantee as a full menu regeneration, just scoped to one day.
- 🔍 **Search and pick** — opens a modal with a live-search text box
  (`GET /api/recipes/search?q=`, new) that matches recipe titles in either
  language, then assigns the chosen recipe via the existing
  `/api/swap-recipe` endpoint (no new swap logic needed there).

Both reuse the exact field-derivation logic `/api/swap-recipe` already has
(title/subtitle bilingual fields, protein type, image) so a rerolled or
picked recipe displays correctly everywhere the dashboard reads dinner
fields from, not just `recipe_id`.

Bug caught during testing: the search-result click handler was built by
concatenating an `onclick="pickSearchedRecipe('id', ...)"` HTML attribute
string with `JSON.stringify(title)`, which uses double quotes — colliding
with the surrounding double-quoted HTML attribute for any and (eventually)
breaking silently on titles containing a quote or apostrophe. Fixed by
building the result rows as real DOM nodes with `addEventListener` instead
of inline `onclick` string concatenation, so recipe titles can never break
out of an HTML attribute.

Verified live against the running local dev server via Claude in Chrome
(not just the automated test client): rerolled Wednesday from "Grilled
Salmon with Asparagus" to "Ceviche" and confirmed it survived a full page
reload; searched "tikka", picked "Chicken Tikka Masala" for Friday, and
confirmed the swap persisted the same way.

Also added new i18n keys (`reroll_recipe`, `pick_recipe`,
`pick_recipe_modal_title`, `search_recipe_placeholder`,
`no_recipes_found`, `rerolled_title`) in both English and Norwegian.

---

## 2026-07-06 (10)

### Fixed: swap-recipe/assign-to-day silently not saving (JSONB mutation-tracking gap)

A friend testing the app reported that swapping a recipe onto a day (or
swapping two days' recipes) sometimes did nothing, or put the recipe on
the wrong day, even though the request came back as a success. Reproduced
directly against the API (assign a new recipe to Monday, then swap Monday
with Wednesday) and confirmed: the response said "success" and the
in-memory menu really was correct, but a follow-up read of `/api/menu`
showed the old, un-swapped menu — the change never reached the database.

Root cause: `load_weekly_menu_from_db()` hands back the household's
`weekly_menu` JSONB column value directly (not a copy). `/api/swap-recipe`
mutates a nested dict inside that same object in place, then passes that
identical object back into `save_weekly_menu_to_db()`. Because it's
literally the same Python object SQLAlchemy already has loaded, plain
attribute reassignment doesn't register as a change — there's no "before"
distinguishable from "after" — so SQLAlchemy silently omitted the column
from the UPDATE. This wasn't a permissions/read-only-user issue as
initially suspected; it reproduced identically for a full read/write user.

Fix: added `flag_modified(household, "<column>")` (from
`sqlalchemy.orm.attributes`) to all six `save_*_to_db` functions in
`core/household_paths.py` (`recipes_db`, `pantry`, `categories`,
`weekly_menu`, `activity_log`, `imported_packs`) — a blanket fix for this
whole class of bug, not just today's specific symptom, since every one of
these functions had the same in-place-mutation exposure. Verified via
direct API reproduction (both "assign new recipe to a day" and "swap two
existing days" now persist correctly across a follow-up read) and the full
test suite (49 passed, 1 pre-existing unrelated failure in
`test_json_files_valid` referencing an already-deleted root
`pantry_staples.json`).

---

## 2026-07-06 (9)

### Project cleanup: removed stale files, consolidated docs

Full audit of the repo for obsolete/duplicate/stale files (see chat for
the full proposal). Deleted: a root-level `pantry_staples.json` that
duplicated `data/pantry_staples.json` in an older schema and was never
actually read by any code; `data/recipe-pack-experiments/` (30 JSON
files across 5 sub-folders, confirmed unreferenced anywhere — leftover
iteration snapshots from an earlier recipe-pack reorg); `summary.md` (a
disposable single-session status report, superseded by this file);
`deployment/.env` and `deployment/.env.template` (real leftover
Pi-era config referencing Azure/Todoist/Trello/Notion sync — all
already-removed features, and not even loaded by the app, which only
reads the root `.env`); `scripts/test-api.py`, `test-local.py`,
`pi-menu-cli.py`, `category-editor.py` (confirmed to operate on flat
JSON files directly rather than the household/Postgres model the app
has used since the JSONB migration - genuinely obsolete, not just
old-looking). Archived (moved to `scripts/archive/`, not deleted, since
a from-scratch fresh-install scenario might still need them):
`seed_recipes.py`, `backfill_household_data.py`,
`backfill_email_confirmed.py` (+ its `.sql` pair) - all one-time
migration scripts already run against production. Merged
`DEPLOYMENT_F4.md` (the original Railway→Render/Neon migration runbook)
into this changelog as history (see the 2026-07-01 entry below) and its
still-relevant rollback plan into `docs/CI_CD_PIPELINE.md`; deleted the
standalone file. Deleted `.github/workflows/README.md` (duplicated
`docs/CI_CD_PIPELINE.md` almost entirely; kept the doc with the diagram).
Moved `ABOUT.md`, `BACKLOG_2026-07-01.md`, `FEATURE_ROADMAP.md`, and
`SYSTEM_ARCHITECTURE.md` from the repo root into `docs/` for a cleaner
root directory; updated every cross-reference. Fixed `config.py`'s
`PANTRY_STAPLES_PATH`, which pointed at a `core/pantry_staples.json`
that has never existed in this repo (dead constant, unrelated to the
file deletions above - the app actually resolves the real pantry
staples path through `SEED_DIR`/`core/household_paths.py`, not this
constant).

## 2026-07-06 (8)

### Deploy tooling: tried a one-click script, reverted in favor of Claude Code

Briefly added `DEPLOY.bat` (a guarded test-then-commit-then-push-then-watch-CI script) as a workaround for Cowork not holding push credentials to this repo. Owner discussed it with Claude Code and decided to keep deploys there instead, since it already runs on the owner's own machine with full git/gh access and the established commit-message conventions for this project - removed `DEPLOY.bat` and its supporting `NEXT_COMMIT_MSG.txt` mechanism again the same day.

---

## 2026-07-06 (7)

### Added "Import Recipe Packs" button to the All Recipes page

`docs/USER_GUIDE.md` already documented "Go to All Recipes → Import Pack" as the fastest way to get started, but that button never actually existed there - only in Settings. Added it (linking to the existing `/recipe-packs/manage` page, reusing the existing `import_recipe_packs` i18n key rather than adding a duplicate). Verified live on the local instance via browser.

Also verified, in response to questions about live vs. local state: the local instance's All Recipes page shows 277 recipes (267 pack recipes + 10 starter samples) exactly matching the expected math, "Light Meals" renders correctly in the category dropdown, and a search for "tikka" surfaces "Chicken Tikka Masala 🌍" from the Around the World pack filed correctly under Chicken - confirming the app-side logic has no bug. The category dropdown intentionally has no "Around the World" entry, since it's a themed pack spanning multiple existing dish categories rather than a category itself.

Also discovered: nothing from this session (security pass, bug fixes, concurrency lock, today's recipe audit) had been pushed to git except one earlier commit for the Around the World pack + feature flags - explaining why the live site didn't reflect most of today's changes. Owner opted to commit and push everything; hit a filesystem cache-coherence issue with the mounted drive during `git add` (`.git/index.lock` reported as both present and absent within the same shell), so handed off exact commit/push commands for the owner to run directly rather than risk corrupting the repo via an unreliable mount.

---

## 2026-07-06 (6)

### Follow-up on the dinner-suitability audit

- **Merged duplicate Greek Salads** (`eu_095`/"Horiatiki" + `sum_001`) into one recipe at `eu_095`, keeping the more precise weight-based ingredient amounts and folding in the "great as a summer dinner or starter" serving note.
- **Merged all 3 Bouillabaisse recipes** (`eu_003`, `eu_029`, `sum_099`) into one at `eu_029`: kept the technically correct staggered-cooking method (build the broth first, add firm fish before delicate shellfish so nothing overcooks), added the traditional bread + rouille serving note, and fixed a real data error along the way - `sum_099` called for 10g of saffron, which is wildly overpriced/inedible in that quantity; corrected to a realistic pinch.
- **Renamed the "Sides & Light Meals" category to "Light Meals"** everywhere (`data/categories.json`, every recipe's `category` field across all packs, the pack's own display name/description, `docs/RECIPE_PACK_FORMAT.md`, and two code comments in `flask_app.py`) - done specifically so the name doesn't clash with the planned F8 sides/appetizer feature later. Note: this only touched the seed data and code; four existing per-household `data/households/*/categories.json` snapshots on disk still say the old name and weren't touched (out of scope - those are live household data, not seed content).
- Explained the 397 vs. 270 recipe-count discrepancy the owner flagged: 397 total recipe entries across everything = 270 in real importable dinner packs + 117 in the hidden dessert/drinks/sides stashes (which have no import path into "All Recipes" at all) + 10 default starter samples. The live count of 270 lines up exactly with the importable-pack total - nothing was missing.
- Hit this session's known file-truncation quirk again (this time as stray null-byte injection, not truncation) while editing two code comments in `flask_app.py` - caught immediately via `py_compile` returning a null-byte error, fixed by stripping the null bytes from the otherwise-correct-length file and diffing against the last verified backup to confirm only the intended lines changed.
- Full 50-test suite passing throughout; 384 unique recipe IDs remain (397 minus the 3 recipes removed by the two merges), zero duplicates, all touched JSON files validated.

---

## 2026-07-06 (5)

### 🍽️ Dinner-suitability audit and cleanup

Reviewed all 398 recipes across every pack and stash for whether they actually work as a dinner main for 4 (vs. side/appetizer/dessert/snack/condiment). Delivered as a spreadsheet (`recipe_dinner_audit.xlsx`) with per-recipe classification, flag, reason and suggested role. 62 flagged; owner reviewed each bucket and decided:

- **Moved out of dinner packs entirely**: Pancakes and Christmas Rice Porridge → `dessert-stash.json` (genuine desserts); Black Pudding → `sides-stash.json` (breakfast/side component, not sweet enough for dessert-stash); Liver Paste and Thai Green Curry Paste → `sides-stash.json` (condiments/spreads, not standalone dinners - the curry paste in particular was a flavor base with no protein/rice, not a finished dish).
- **Deleted**: `no_032` "Cured Salmon" - an exact-title duplicate of `nd_021` in the same pack, with a broken `cookTimeMinutes: 0` (vs. `nd_021`'s correct 30 min).
- **Recategorized to "Sides & Light Meals"** (kept in their original pack files, just given the accurate category so they're easy to filter/uncheck): 29 recipes spanning starters (gravlax, satay, cured sausage, hummus platters), sides (Boxty, Jansson's Temptation, Rösti-adjacent salads), and sandwich/snack items previously mis-filed under Chicken, Fish & Seafood, Grill, Ground Meat & Sausages, Other, Salads, Soups & Stews and Taco & Tex-Mex.
- **Explicitly kept as dinner mains** despite reading "appetizer-ish" on paper: Greek Salad (both copies), Caprese Salad, and Crab Salad - confirmed as real family dinner dishes, especially in summer.
- **Left untouched**: 10 "light dinner" borderline items (Spanakopita, Gado-Gado, Greek Gemista, various grilled-chicken/halloumi salads, Potato Soup, etc.) - owner confirmed these work as legitimate light summer dinners as-is.

Verified after every step: JSON validity + `recipeCount` matching actual list length on every touched file, zero duplicate recipe IDs across all 397 remaining recipes (398 minus the one deletion), and the full 50-test suite passing.

Also surfaced (not yet acted on): several near-duplicate recipes across packs worth a future dedup pass (Bouillabaisse ×3, Chicken Enchiladas ×2, two Cheese Fondues, and a cluster of "cured meat" recipes with a broken `cookTimeMinutes: 0` instead of a real cure time - Cured Leg, Cured Roe, Cured Ham, Cured Meat Platter). A future F8 ("Appetizers & Sides") feature was discussed as the eventual real home for the starter-style recipes currently just parked under "Sides & Light Meals".

---

## 2026-07-06 (4)

### 🧱 Hidden foundation for dessert/drinks browsing (F2) and side stash (F8)

- New `core/stash_library.py`: isolated, read-only loaders for `data/dessert-stash.json`, `data/drinks-stash.json`, `data/sides-stash.json` (87/4/21 recipes respectively - previously unused data sitting in the repo since 2026-06-30 with no code reading them). Deliberately kept separate from the recipe-pack/menu code per the "keep future work modular" ticket, plus a `suggest_dessert_for_menu()` stub as the documented (but not yet wired-in) hook point for a future F9 dinner-planner integration.
- Four new routes, all gated behind the feature flags added earlier today and 404ing outright when off (not just hidden from nav): `/desserts-drinks` + `/api/desserts-drinks/list` (`desserts_drinks` flag), `/sides-stash` + `/api/sides-stash/list` (`side_stash` flag). Two new minimal templates (`desserts-drinks.html`, `sides-stash.html`), clearly marked as dev-only, not linked from any public nav.
- Public UI/behavior is completely unchanged - verified via a Flask test client: with flags at their default (off), all four routes 404; with `FEATURE_DESSERTS_DRINKS=true`/`FEATURE_SIDE_STASH=true` set, all four return 200 with the real stash data. Full 50-test suite still passes.
- Recovered again mid-edit from this session's file-truncation quirk - this time the corruption cut off well past both today's edits (inside an unrelated, untouched route further down the file), and a routine backup-refresh accidentally overwrote the last known-good copy with the broken one. Fixed by splicing the intact prefix of the current (truncated) file with the corresponding unmodified tail from `git show HEAD` (verified nothing between the splice point and EOF had changed this session), rather than trusting either copy alone. Backup now only refreshed *after* a file is confirmed compiling and test-passing, not before.

---

## 2026-07-06 (3)

### 🚩 Local-only feature flags added

- Added `FEATURE_FLAGS` (env-var-backed, default OFF) to `deployment/flask_app.py` right after `IS_PRODUCTION`: `FEATURE_DESSERTS_DRINKS` (F2), `FEATURE_SIDE_STASH` (F8), `FEATURE_DESSERT_PLANNER` (F9). Exposed to routes via `feature_enabled(name)` and to all templates via `feature_flags` in `inject_config()`.
- Logs a loud warning at startup if any flag is ever truthy while `FLASK_ENV=production` - belt-and-suspenders, since Render's env never sets these.
- Documented in new `docs/FEATURE_FLAGS.md`; `.env.example` updated with commented-out examples.
- Recovered mid-edit from this session's known file-truncation quirk (see earlier entries) by restoring from a `/tmp` safe copy and reapplying both today's edits in one pass - verified via `py_compile` and the full 50-test suite (all passing) before moving on.

---

## 2026-07-06 (2)

### 🌍 New import pack: "Around the World"

- Added `data/recipe-packs/pack_around_the_world.json` — 16 recipes, one iconic dish per country (Italy, France, Spain, Greece, India, Thailand, Japan, China, Mexico, USA, Morocco, Turkey, Germany, Vietnam, Lebanon, Brazil), fully bilingual (title/subtitle/ingredients/instructions in `no`/`en`), matching the existing pack schema documented in `docs/RECIPE_PACK_FORMAT.md`.
- All recipes are original write-ups of classic, traditional preparations (not copied from any specific website or publication) - no copyright-restricted content included. New ID prefix `wld_` added to the format doc's ID convention table.
- Verified: JSON validates, all 16 IDs are unique against the other 260 existing recipe IDs across all packs, and the pack is correctly picked up by the existing pack-discovery logic (`get_available_recipe_packs()` globs `pack_*.json` - no registry/allowlist changes needed) - simulated the `/api/recipe-packs/list` response and confirmed it appears alongside the other 12 packs with correct name, description, icon, and recipe count.

---

## 2026-07-06

Design-critique pass on the live site, followed by a round of bug-hunting the critique surfaced along the way, closing out the remaining scope of B46, and a proactive fix for a menu-write concurrency gap ahead of scaling up.

### 🎨 Design critique fixes

- **All Recipes sidebar showed `[object Object]` for every day.** `/api/menu` only resolved bilingual `{en, no}` recipe titles into plain strings when a day-translation map existed (Norwegian only) - in English, the raw dict was sent straight to the sidebar JS and stringified as `[object Object]`. Now always resolved regardless of language.
- **Stale "0 MIN" recipe times** (e.g. a holiday-pack recipe that only ever carried `cookTimeMinutes`, not `time_minutes`) baked into old saved menus. Dashboard and `/api/menu` now self-heal by looking the recipe back up when `time_minutes` is falsy.
- **Day-card headers rendered navy instead of each theme's own color.** Root cause: base `style.css`'s `.card-header`/`.hero` set an opaque gradient via the `background` shorthand; four theme overrides (Nordic Pantry and Pop Art Diner's card-header, Pop Art Diner and Chalkboard Bistro's hero) only set `background-color`, which the shorthand's `background-image` silently painted over. Fixed all four to use the `background` shorthand like every other theme already does.
- Added a small colored difficulty dot (green/amber/red) next to difficulty text on dashboard and All Recipes cards.
- "Export & Sync" → "Export" (button + modal heading) now that Todo/Todoist/TickTick sync is gone.
- Settings page: added subtle "Preferences" / "Advanced" group labels to separate everyday settings from power-user ones.

### 🐛 Bugs found while investigating the above

- **Activity log showed raw Python dict reprs** (e.g. `Swapped Tuesday's dinner to '{'no': '...', 'en': '...'}'`) for "true swap" actions (exchanging two days' recipes) - `recipe_title` was pulled from the post-swap `target['title']`, which can still be the unresolved bilingual dict. Now resolves to a plain string the same way the direct-assign branch already did.
- **Duplicate recipe on two different days** (both Tuesday and Wednesday showing the same recipe) - investigated via the activity log and 300 simulated regenerations against the household's actual data; the generator itself can't produce this. Concluded it was a household member deliberately picking the same recipe for two days via two manual swaps, which the app correctly allows - not a bug.

### ✅ B46 fully closed (category tags, ingredient names, allergen tags)

- **Category tags** ("Quick Dinners", "Fish & Seafood", etc.) stayed in English regardless of language. The Norwegian names already existed in `data/categories.json` - the dashboard's translation map was hand-maintained and simply missing three categories (Pork, Beef & Red Meat, Sides & Light Meals), and nowhere else (All Recipes cards, recipe detail page) translated categories at all. Replaced with a shared `_translate_category_name()` helper backed directly by `categories.json`, applied everywhere a category is shown.
- Updated "Quick Dinners" Norwegian name to "Raske Middager" per an explicit wording preference (was "Rask Middag").
- **Ingredient names** (Carrot/Potato/Parsley/Turnip etc.) - investigated and found these already have correct Norwegian translations in the data (Gulrot/Potet/Persille/Nepe); live-checked the shopping list in Norwegian and every item rendered correctly. Whatever prompted the original observation no longer reproduces - closing this scope of B46 rather than inventing translations that already exist.
- **Allergen tags** ("fisk" vs "fish", etc.) - root cause: no bilingual structure at all (unlike title/ingredients). The 10 built-in sample recipes stored raw Norwegian allergen strings ('fisk', 'melk', 'soya'), while imported recipe packs stored raw English strings ('fish', 'dairy', 'soy', etc.), so whichever language a recipe happened to be authored in is what displayed, regardless of site language. Added a canonical `_translate_allergen()` table covering every raw spelling found in the data, applied to both the recipe detail page's allergen badges and the shopping list's per-item allergen tags.

### 🔍 B17 re-verified (not newly reproduced)

- Re-checked the 2026-07-03 fix (persistent 30-day sessions, Postgres `pool_pre_ping`/`pool_recycle`) at the code level: confirmed there's a single centralized login point that sets `session.permanent = True` (no path skips it), and the DB pool settings are correctly wired. Couldn't force a live reproduction without access to Render's actual logs/idle behavior - still just monitoring for recurrence.

### 🔒 Menu-write concurrency fixed (built proactively ahead of scaling up)

- Not an active bug today (gunicorn runs a single sync worker, so there's no real request-level concurrency yet) - but since the goal is to grow, this was fixed now rather than left for a future incident. Added `locked_household()`, a context manager that opens one DB session and locks the current household's row (`SELECT ... FOR UPDATE`) for the whole read-modify-write, so a concurrent request touching the same household blocks until the first one commits instead of both working from stale data. Refactored `/api/swap-recipe` and `/api/regenerate` to do their entire read + mutate + save inside this one locked transaction instead of two separate sessions. Verified with the full test suite (50/50 passing) plus a direct functional test of regenerate → swap → re-read through a live test client, confirming menu state and activity log entries are correct end-to-end.

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
