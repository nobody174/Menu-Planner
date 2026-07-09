# Backlog — Active

Last updated: 2026-07-08

This file holds only what's still genuinely open. Anything fixed, verified,
built, or decided has been moved to `CHANGELOG.md` (full history) or
`FEATURE_ROADMAP.md` (planned features, Now/Next/Later). A "Recently
resolved" section near the bottom gives one-line pointers into the
changelog for anything closed in the last couple of sessions, so you don't
have to go spelunking for what happened to an ID you remember seeing here
before.

---

## 🚨 LAUNCH BLOCKERS — must resolve before public + paid launch (do NOT skip)

Flagged 2026-07-05 during a legal/compliance check ahead of the planned public launch + paid Patreon tier (69 kr/mo, 7-10 day trial). None of this blocks the current friends-and-family soft launch — this is specifically gating the move to (a) truly public signups and (b) turning on the paywall.

### L1. No privacy policy or terms of service exist anywhere (repo or live site)
- Required before any paid or public launch. You're the data controller (Norway/EEA, GDPR applies); Neon + Resend are both EU-hosted per your confirmation, which simplifies this.
- Needs to cover: what data is collected (email, password hash, household member names/avatars, referral codes, activity log, pantry/recipe data), why (contract/legitimate interest for core functionality), how to request deletion (Danger Zone already covers this, and M1's cascade fix now makes that promise actually true) or access, and that household members' data is entered by the account owner.
- Claude offered to draft both in plain language — not done yet as of this writing.

### L2. Trial-to-paid conversion needs an explicit pre-charge notice
- Norway's Forbrukertilsynet actively enforces against subscriptions that silently convert a free/trial period into a paid one (negative option billing, markedsføringsloven §11).
- Needs: a clear email/in-app reminder before the 7-10 day trial converts to the 69 kr/month charge, not just a UI countdown.

### L3. Cancellation must be self-serve and as easy as signup
- Not yet built (no paywall exists yet). When built, cancellation must live in Settings, not "email us to cancel."

### L4. 14-day right of withdrawal (angrerettloven) for EEA consumers
- Applies to the paid subscription once launched. Needs clear disclosure at signup/payment.

### L5. Tax / business registration timing undecided
- Currently running as an individual (no enkeltpersonforetak). Not a blocker for friends-and-family, but recurring subscription income is taxable from day one regardless of registration status. Decide a real trigger point (e.g. before X paying users or €X/month) rather than leaving it open-ended.

### L6. Confirm Patreon's own creator/refund terms don't conflict with your stated "69 kr/month" terms
- Patreon acts as payment processor and imposes its own refund/payout rules on you as a creator — read these once before publishing your own subscription terms.

**Also discussed, not yet decided:** whether Patreon is the right payment path at all vs. Stripe or another processor (Lemon Squeezy/Paddle also discussed as merchant-of-record options that absorb EU VAT complexity) — worth revisiting once ready to build the actual paywall.

---

## OPEN — technical debt / cleanup (from the 2026-07-07 audit)

**M3. Deployment definition split-brain: Railway-era Docker vs. Render Procfile**
- `docker-entrypoint.sh` (4 gunicorn workers, runs migrations) and `Procfile` (1 worker, no migration step) contradict each other, and code comments bake in single-worker assumptions (PIN lockout, in-memory rate limiter) that the Docker path would silently violate. Decide which one is actually live on Render, delete/demote the other, document where migrations run.
- Re-confirmed still open 2026-07-08: both definitions still exist unchanged.

**B61. Two full parallel storage implementations**
- JSONB-in-Postgres vs. legacy per-household flat-file storage, both live throughout `core/household_paths.py`. This dual-path shape is exactly what produced the swap-day JSONB `flag_modified()` bug fixed 2026-07-06 - every future menu-write feature has to get both paths right, or the JSONB path right and silently leave the file-fallback path stale. Worth confirming whether any production household still uses the file path at all, then deleting it if not.
- Category-tombstone JSONB persistence (M2) is now fixed as of 2026-07-07, but that only closed one specific gap in this dual-path shape - the consolidation itself hasn't happened. `feedback.json`'s status (a real-user-email file outside the DB/backups, flagged alongside B61 in the original audit) hasn't been re-checked either.

**B57 follow-up: near-duplicate `api_swap_recipe`/`api_reroll_recipe`**
- The 2026-07-07 audit flagged these two routes (~225 and ~190 lines) as near-duplicate giants worth extracting once the blueprint split (B57, now done) landed. Not separately verified/addressed - worth a look next time either function is touched.

**B58. Firefox-only rendering bug: white block at bottom of page — STILL UNRESOLVED**
- Reported by user 2026-07-06: a white block covers the bottom of the page in Firefox; switching to Edge, the page renders correctly. Tested all 4 key pages (dashboard, shopping list, all-recipes, add-recipe) in a real Firefox engine via Playwright MCP at default desktop viewport, a shortened viewport (`100vh` hypothesis), and with the settings dropdown open (`backdrop-filter` hypothesis) - could not reproduce in any of these. Genuinely still open. Next step: whoever saw it originally needs to note the *exact* page, browser window size, and ideally a screenshot - or it surfaces on its own via the Playwright CI suite (B62, shipped) if it's still present and gets hit by one of the 7 test environments on a future push.

**LO2. No `@login_required`-style decorator**
- Every route hand-rolls its own auth gate; safety currently rests on every data helper resolving through household scoping. Worth a small decorator, adopted incrementally.

**LO3. Dead Pi-era modules and stale config**
- `deployment/scheduler.py`, `email_notifier.py`, `to_do_sync.py` confirmed still imported nowhere (re-checked 2026-07-08). `config.py` still has the stale `MENU_DAYS = 5` (real list is 6-day) and the `HOUSEHPLD SETTINGS` typo, both confirmed still present. An afternoon of deletion.

**LO4. Alembic filename/revision mismatch**
- `alembic/versions/a1b2c3d4e5f6_add_password_reset_to_users.py`'s actual `revision` is `g6h7i8j9k0l1`, not `a1b2c3d4e5f6` (that prefix belongs to a different file, `..._add_profile_support_to_household_members.py`). Chain itself is valid, this is a pure future-confusion trap - rename the file to match its real revision id.

**LO5. `datetime.utcnow` throughout models/helpers**
- Deprecated since Python 3.12; future debt only at the current 3.11.9/3.12 pin.

**LO6. Confirmation/reset tokens stored in plaintext**
- Reset tokens expire in 1h (fine), confirmation tokens never expire. Low priority at this threat model; hash at rest eventually.

**LO7. `/health` doesn't touch the DB; deploy gate can false-pass**
- Returns healthy unconditionally, and CI's health poll can catch the *old* instance still answering healthy mid-rolling-deploy. Add a cheap `SELECT 1`.

**LO8 (remainder). Possible `households/None/` path on unauthenticated fallback writes**
- In `save_menu`/`_save_pantry_db`'s file-fallback path when there's no household id at all. Not touched - needs its own look rather than a one-line fix. (The other 2 of 3 LO8 items - duplicate import, dead household-cleanup code, meaningless `/health` field - are resolved, see below.)

---

## OPEN BUGS

### B17. Intermittent relogin / "Oops!" errors — fix shipped, still monitoring
- Fix (persistent 30-day sessions + Postgres `pool_pre_ping`/`pool_recycle`) shipped 2026-07-03. Re-verified at the code level 2026-07-06 (single centralized login point, pool settings correct) - no code-level gaps found, but a live recurrence check needs actual Render log access or more time passing, neither of which is available from here. Still just monitoring.

---

## TESTING CHECKLIST — still open

- [ ] Manual (non-automated) click-test of pantry add/remove on a real device, to fully close out B38 (automated browser control couldn't reliably reproduce the original report either way).
- [ ] Reproduce and fix the Firefox-only white block at the bottom of the page (B58 above) - needs a real Firefox session and exact repro steps from whoever saw it.

---

## Recently resolved (pointers into CHANGELOG.md - not duplicated here)

**2026-07-07 (2) — comprehensive audit + same-day fix pass:** C1 (shopping export broken in prod), H1 (SECRET_KEY fallback), H2 (rate limiting), H3 (`/themes` 500), M1 (account deletion cascades), M2 (category tombstone JSONB), M4 (silent write-failure swallowing), M5 (HTML errors to JSON clients), M6 (per-request caching), M7 (login enumeration), LO1 (body size cap), LO8 (2 of 3 items), B56 (missing DB indexes), B57 (blueprint split), B59 (route test coverage), B60 (dead code).

**2026-07-07 (1) — QA/production-readiness pass:** B53 (silent partial menu generation), B54 (CI vuln scan not gating), B55 (All Recipes empty search state), B60 (dead code, same fix as above), B63 (SQLite concurrency bug, live-affecting), B65 (All Recipes mobile layout never collapsed), B66 (Import Recipe Packs wrong link), B67 (auto-tags missing GitHub Releases), B68 (non-deterministic e2e seed data). B62 (Playwright MCP + CI suite) shipped same session. B64 (marketing videos) decided against, kept originals.

**2026-07-08 (1) — Security Hardening PR:** M8 (missing CSP header - the one real gap left after H2/M7/LO1 were found already done).

**2026-07-08 (2) — bookkeeping cleanup:** this file renamed from `BACKLOG_2026-07-01.md` → `BACKLOG.md` (it's a living document, not a dated snapshot); backfilled two missing CHANGELOG entries for 2026-07-07's work, which had never been written up there; trimmed this file down to open items only, per its own stated contract.

**Process note:** the prior two sessions' write-ups lived entirely in this file as inline "RESOLVED" notes and were never actually moved to `CHANGELOG.md` or trimmed out here, despite this file's own header saying that's the contract. If you're picking this file up cold, trust the code over any status text you find - grep for the actual function/pattern before assuming a note is current.
