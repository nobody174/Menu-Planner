# Summary — Full Punch-List Pass (2026-07-05, round 6)

Scope: worked through the full punch list (re-tests, remaining bugs, cosmetic
batch, mobile viewport pass, multi-user testing, settings review) at
`localhost:5000`, in the order agreed beforehand. Feature work (F1 Themes,
F2 Dessert/Drinks, F3 Avatars, F5 Recipe Pack, F8 Sides Stash, F9) was
explicitly out of scope for this round per your instruction.

## What was changed

**Re-tests (no code changes needed):** B35, B31, B32, B33, B34, B29, B30, and
B25 were all re-verified live or via code inspection and are still working
correctly - no regressions.

**B41-adjacent apostrophe risk:** swept `settings.html`, `all-recipes.html`,
`recipe.html`, and `feedback.html` for the same pattern that caused B41
(translated strings embedded in inline `<script>` blocks without `|tojson`,
which shows `&#39;` literally instead of an apostrophe). Fixed all 14
remaining instances.

**B38:** confirmed via a genuine manual-style test (real click+type+click)
that pantry add/remove works correctly. A simulated-click removal attempt
failed twice, but calling the exact same underlying function directly worked
instantly - this is a browser-automation tooling artifact, not an app bug.

**B28:** two recipes (`eu_096`, `eu_083`) had nonsensical combined ingredient
units (e.g. "ml/100g/50g" for three different ingredients bundled into one
line). Fixed the source pack files, and added a small read-time correction
in `flask_app.py` for households (like this test household) that already
imported the old broken data, so it displays correctly everywhere without
needing a risky direct database migration.

**B47 (mobile horizontal overflow):** found two real causes - fixed-position
decorative "orb" elements bleeding off-canvas, and the Terracotta theme's
recipe-card grid forcing a 300px minimum width with no override for phones
narrower than that. Fixed both; verified no overflow at 320px/375px across
the dashboard and All Recipes in both themes.

**B48:** closed as won't-fix - the emoji fallback for the two broken image
references already looks fine.

**B46 (Norwegian translation gaps):** fixed the Settings page's biggest gaps
- signed-in-as line, Owner PIN, Refer a Friend, Activity Log, and Danger
Zone were all silently falling back to English because their translation
keys were simply missing from `i18n.json`. Added them; verified live.
Category tags, shopping-list ingredient names, and allergen language are
still untranslated in places - that's a larger, separate data-level i18n
project across the recipe database itself, not a quick fix.

**Cosmetic batch (all fixed):** the "Difficulty: Easy" on empty days was
already resolved by earlier work; expanded the Add Recipe time dropdown from
5 to 11 options; fixed the profile-picker browser-tab title mismatch;
Household Settings "Joined" dates now show as "Jul 05, 2026" instead of raw
ISO timestamps; fixed the owner's row showing their email twice; corrected
a stale button name in Tips & Tricks; and added proper hour formatting for
long prep times ("24 h" instead of "1440 min"), applied everywhere a
recipe's time is shown.

**Two new bugs found during multi-user testing (not on the original list):**

1. **Critical - cross-account data leak.** Logging in as a second real
   account on the same browser silently inherited the first account's
   entire household (menu, recipes, pantry) - and writes made as the second
   account actually landed in the first account's real data. Root cause: the
   active household id lived in the session cookie and was never re-validated
   against the currently logged-in user, and login never cleared it. Fixed
   with two independent layers: `current_household_id()` now verifies
   household membership before trusting the session value, and login now
   clears it as well. Verified live with testuser/testuser2; a stray pantry
   item that had leaked into the test household during the investigation was
   removed.
2. **Brand-new households hit a generic "Oops!" error page** on their very
   first dashboard visit (before generating a menu). Replaced with a friendly
   welcome screen with a working "Generate Menu" button.

Full details and verification notes for everything above are in
`BACKLOG_2026-07-01.md` under "Round 6".

## What was tested

Re-tests of 8 previously-fixed bugs; a full apostrophe-escaping sweep across
4 templates; a real (non-automated) pantry add/remove test; both broken-unit
recipes' detail pages; simulated mobile viewports (320px/375px) across 10
pages in 2 themes; the Settings page in Norwegian; the What's New and
What's Planned pages; and multi-user isolation testing with testuser2 and
testuser3 (which is what surfaced the two new bugs above).

## What was verified

Everything listed under "What was changed" was verified live against the
running app - either by direct interaction, by inspecting rendered page text/
DOM state, or (for the mobile pass) by simulated-viewport iframe checks since
real browser window resizing wasn't available in this testing environment.
No console errors were found in any page tested this round. testuser1's
household data was confirmed fully intact and unaffected after all of this
round's testing and fixes.

## Remaining issues / follow-up recommendations

- **B46, continued:** category tags, shopping-list ingredient names, and
  allergen language still need a dedicated i18n pass across the recipe data
  itself - out of scope for a quick fix.
- **B17:** the earlier session-persistence fix should keep being watched for
  recurrence over the next few days of normal use.
- **Settings page ordering (your request for an opinion, not yet acted on):**
  the current order puts Owner PIN and Refer a Friend at the very top, above
  Language, Theme, and the core Recipes/Categories/Pantry management people
  use daily. A more typical hierarchy would be: account info → Language/Theme
  → Recipes/Categories/Pantry (daily-use) → Recipe Packs/Personal Arsenal
  (secondary) → Owner PIN/Refer a Friend/Activity Log (account & sharing) →
  About → Danger Zone (always last, which it already correctly is). Happy to
  reorder if you'd like - this is a design opinion, not a bug, so I left it
  for you to decide rather than changing it unprompted.
- **Feature list (F1/F2/F3/F5/F8/F9):** intentionally not touched this round
  per your instruction - worth a dedicated planning conversation when you're
  ready, since several depend on decisions only you can make (image sourcing
  for F2/F9, external API use for F3's DiceBear avatars, design direction for
  F1's theme rework, content source for F5's recipe pack).
- **Environment note:** the server now runs with `debug=True` (auto-reload),
  so most code edits took effect without a manual restart this round -
  though each reload still clears the browser session, requiring a fresh
  login to keep testing.
