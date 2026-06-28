# Handoff — Referral Feature + Pending Testing (2026-06-28)

**Read this first in a new chat to pick up exactly where the last session left off.**

## Project paths
- Repo root: `d:\Claude AI Projects\projects\GitHub\Menu-Planner`
- Flask app: `pi-deployment\flask_app.py` (main route file, large)
- DB models: `database\models.py`
- DB helpers: `core\household_helpers.py`, `core\auth_helpers.py`
- Templates: `frontend\templates\` (Jinja2)
- Migrations: `alembic\versions\` (NOT auto-run on local dev DB — see gotcha below)
- Local dev DB: `menu_planner.db` (SQLite, at repo root)
- Live deployment: Railway (Postgres), originally built for self-hosted Raspberry Pi, now cloud-hosted SaaS-in-progress
- Background docs that exist but are **partially stale** — treat as historical context, not current truth: `PROJECT_CONTEXT.md`, `FEATURE_ROADMAP.md` (both still describe "Phase 2 in progress"; Phases 2 and 3 are actually complete and deployed as of this session)

## Where this project is headed (big picture)
Menu-Planner started as a single-user, JSON-file-backed weekly meal planner for a Raspberry Pi, and has been evolving into a multi-tenant household-based SaaS:
- **Phase 1** (done): core meal planning, shopping list, JSON storage, single user.
- **Phase 2** (done, deployed on Railway): Postgres + SQLAlchemy + Alembic, email/password auth, household/role model (owner/editor/viewer).
- **Phase 3** (done): Netflix-style lightweight "profiles" so family members don't need their own login/password — just tap a tile after the real account holder logs in.
- **This session's work** (see below): fixed a critical permission bug, added profile rename/avatars, co-owner role, profile cap, and a referral/attribution system — explicitly as a low-cost, no-payment-yet stand-in for eventually monetizing the app.
- **Where it's going next**: the user is thinking about this becoming a **paid product** eventually. Decisions this session (co-owner role instead of email-invite, referral tracked-but-not-rewarded-yet) were explicitly made with that future in mind — don't undo them without re-reading the reasoning below.

## What changed this session (uncommitted — see Git status below)

### 1. Critical permission bug fix
`acting_role_is_owner()` (in `flask_app.py`) was added because the old `user_is_household_owner()` check was keyed to the **account**, not the **active profile** — meaning any family member profile (e.g. "Kid") inherited full owner rights to Settings/Household pages just by being logged in under the owner's account. Fixed by checking the active profile's own role when one is selected, falling back to the account role only when no profile is active.

### 2. Owner password gate
Selecting "Owner" from the profile picker now requires re-entering the account password (reuses existing `authenticate_user`, no new secret introduced).

### 3. Profile management UX
- Rename button for profiles and the owner's own display name (`/api/household/rename-member`)
- Emoji avatar picker (`/api/profile/set-avatar`) — stand-in for a "cartoon avatar library" since no image assets exist in the project
- Activity log visibility bug fixed (was hidden entirely when empty, now shows an empty-state message)
- "Create Household" button relabeled to "Create Another Household" to stop it being confused with the (separate, working) "Rename Household" button

### 4. Co-owner role (new this session)
Added `'co-owner'` as a selectable role when creating a profile (owner-only dropdown option). Treated as fully owner-equivalent in `acting_role_is_owner()`. This exists so a spouse/partner can get full household rights **without** a separate email/login — replacing the old "invite by email into my household" use case for that scenario.

### 5. Max profile cap
`MAX_PROFILES_PER_HOUSEHOLD = 6` (constant in `flask_app.py`), enforced server-side in `add_household_profile()`, shown as a `(count/6)` indicator in the UI.

### 6. Referral/attribution system (new this session)
Built per a researched design plan: **"track now, reward later"** — no discounts/credits/payment logic exists yet, intentionally deferred until a paid tier is designed.
- **Migration**: `alembic\versions\b2c3d4e5f6a7_add_referral_fields_to_users.py` adds to `users`: `referral_code` (unique, 8-char, NOT NULL, backfilled), `referred_by_user_id` (nullable FK), `referred_by_code` (raw string, survives referrer deletion)
- **Code gen**: `core/auth_helpers.py` — `_generate_referral_code()`, `get_user_by_referral_code()`, `create_user()` now accepts `referred_by_code`
- **UI**: Settings page (`frontend/templates/settings.html`) shows a "Refer a Friend" section with a shareable link (`/signup?ref=CODE`) and copy button
- **Signup capture**: `GET /signup` passes `?ref=` through as a hidden form field; `POST /signup` resolves it and links the referrer on account creation
- **Why this exists**: the old "Add Member by Email" feature let a friend/neighbour join the household directly, *sharing the same weekly menu and shopping list* — wrong behavior for a referral/recruiting use case. The referral link replaces that role: a friend signs up into their **own** separate household, with attribution preserved for whenever there's a paid tier to attach a reward to.

### 7. Old "Add Member by Email" feature — REMOVED
Per explicit user decision ("Remove it entirely"), the `/household/add-member` Flask route and its UI section in `household-settings.html` were deleted. The underlying `core.household_helpers.add_household_member()` Python function was **kept** because the test suite (`tests/test_household.py`) still uses it as a fixture helper to set up multi-member households for permission tests — it's no longer reachable from the UI, but still imported by tests.

### 8. Data isolation fix (CORRECTION to this doc — verified in follow-up session)
The "Known gotcha" / outstanding test item #1 below originally flagged recipes/menu/shopping-list/pantry as still being global flat files. That's now **out of date**: `core/household_paths.py` (the untracked file noted in Git status) implements true per-household data directories (`data/households/<household_id>/{weekly_menu,recipes_db,categories,pantry,activity_log}.json`), seeded from the legacy global `data/` files on first use per household. `core/menu_generator.py`'s modifications wire `MenuGenerator` to accept a `household_id` and load/save from that household's folder instead of the shared global files. `pi-deployment/flask_app.py` calls into `household_paths` for menu, recipes, pantry, and activity log, all keyed off `current_household_id()`. **This was intentional work from this same uncommitted session, not a stray leftover** — confirmed by reading the diff and grepping `flask_app.py` for `household_paths` usage (extensive, consistent). Still needs the manual two-household isolation test (item #1 below) to confirm it actually behaves correctly end-to-end, but the code is real and wired in, not orphaned.

## Known gotcha (saved to Claude memory too, but repeating here for the new chat)
The local dev SQLite DB (`menu_planner.db`) was originally created via `Base.metadata.create_all()`, **not** through Alembic — it had no `alembic_version` table at all even though it already matched a newer schema than its stamp implied. Running `alembic upgrade head` cold failed with "table already exists." Fixed locally by running `alembic stamp a1b2c3d4e5f6` (the revision matching its actual prior state) before `alembic upgrade head`. **Production (Railway/Postgres) was not checked for the same issue** — worth verifying its Alembic stamp is correct before running the new migration there.

## Git status as of end of session
Branch: `public-release-v1`, up to date with `github/public-release-v1`. **Nothing was committed this session** — all of the above is uncommitted working-tree changes:
```
modified:   core/auth_helpers.py
modified:   core/household_helpers.py
modified:   core/menu_generator.py        <- NOT touched by this session's work, check if pre-existing/unrelated
modified:   database/models.py
modified:   frontend/templates/base.html
modified:   frontend/templates/household-settings.html
modified:   frontend/templates/profile-picker.html
modified:   frontend/templates/settings.html
modified:   frontend/templates/signup.html
modified:   pi-deployment/flask_app.py
untracked:  alembic/versions/b2c3d4e5f6a7_add_referral_fields_to_users.py
untracked:  core/household_paths.py
```
**Update**: `core/menu_generator.py` and `core/household_paths.py` were confirmed (see item 8 above) to be intentional, wired-in data-isolation work from this same session, not orphaned leftovers. **Action needed in next session**: decide whether to commit this work.

## What the user needs to test next (manual, in-browser)
Carried over from the original testing pass, still outstanding:
1. **Data isolation** — create a second real account/household, make changes, confirm recipes/menu/shopping-list don't leak between households. (Flagged as a known gap — see Claude memory `menu-planner-data-isolation-gap` — recipes/menu/shopping-list may still be global flat files rather than per-household despite the DB schema supporting isolation. Worth re-verifying this is actually fixed before relying on it.)
2. **Pantry** — same, needs a second account to confirm per-household isolation.

New from this session, not yet tested at all:
3. **Co-owner profile** — create a profile with role "Co-Owner," confirm it gets full Settings/Household access (equivalent to Owner), confirm a "Viewer"/"Editor" profile still correctly gets blocked.
4. **Owner password gate** — log out of "acting as a profile," select "Owner" from the profile picker, confirm the password prompt appears and an incorrect password is rejected.
5. **Profile cap** — try adding a 7th profile to a household that already has 6, confirm it's blocked with a clear message.
6. **Rename** — rename both a family profile and the owner's own display name, confirm it updates everywhere (nav avatar tooltip, settings "Signed in as," household member list).
7. **Avatar picker** — set an emoji avatar for a profile and for the owner; confirm it persists and shows correctly in the nav bar, settings page, and household member table.
8. **Activity log** — confirm it now shows an empty-state message (not a vanished section) on a household with no logged activity yet, and shows entries once some activity exists.
9. **Referral link** — copy the link from Settings, open it in an incognito window, sign up with it, then check the new user's `referred_by_user_id`/`referred_by_code` got set correctly in the DB (no UI surfaces this yet — would need a DB query or a future admin view).
10. **Old Add Member button is gone** — confirm there's no trace of "Add Member by Email" left in Household Settings, and that nothing else links to the now-deleted `/household/add-member` route.

## Suggested first message in the new chat
> "Continuing from HANDOFF_REFERRAL_AND_TESTING_2026-06-28.md in the Menu-Planner repo — pick up from there."
