# Menu Planner — Working Instructions for Claude Code

## Branch model

- **`main`** — day-to-day working branch. "Push main" / "save" means: push
  commits to `main`. Runs the full CI pipeline, never deploys.
- **`public-release-v1`** — production. Protected: GitHub rejects any direct
  push unless every required status check has already passed on that exact
  commit (branch protection, configured 2026-07-06). The only way to land a
  change here is a pull request from `main` that has gone green.

## "Push main" / save

1. **`git status`** first. If there's anything unexpected (stray files,
   more changes than expected, a lock file, a branch that's diverged from
   `github/main`), stop and investigate before doing anything else. Don't
   just trust a summary of what changed — check it yourself.
2. **Read the actual diff**, not just the file list. `git diff --stat` to
   see scope, then read the real diff for anything non-trivial. If a
   commit message (yours, the user's, or a co-worker session's) describes
   something unusual — "corruption recovery," a security fix, a data
   migration, mass file changes — verify that description against the
   actual diff before trusting it. Don't commit on the strength of a
   write-up alone.
3. **Pull/merge first if needed.** If local is behind `github/main`, fetch
   and merge before pushing. Resolve conflicts carefully — don't blindly
   take one side; read both hunks and keep what's real.
4. **Stage deliberately.** Prefer `git add <specific files>` over blind
   `git add -A` when the changeset is mixed; at minimum, review
   `git status` after staging to confirm nothing surprising got included
   (e.g. `.db`, `.db-journal`, or other local/generated files that should
   be gitignored, not committed).
5. **Commit** with a message that describes the *why*, not just the *what*
   — matches the style already in this repo's git log and `CHANGELOG.md`.
6. **Push**: `git push github main`.
7. Report back plainly what was pushed, in one or two sentences.

## "Ship it" / "push public" (deploy to menuplanner.no)

**Always confirm `main` is fully pushed first** — check `git status` and
whether local `main` is ahead of `github/main`. If there are uncommitted
changes or unpushed commits, do the full "push main" sequence above first
(committing/pushing them, or flagging anything that needs the user's input
first) before proceeding. Never ship stale code because `main` on GitHub
was behind local.

Then:

1. Open a pull request from `main` into `public-release-v1` (`gh pr create`).
2. Wait for all 8 required status checks to pass (Stage 1: Lint & Format,
   Data Validation, Frontend Checks; Stage 2: Tests, Security Scan, Build
   Check ubuntu-latest, Build Check windows-latest, Build Docker Image) —
   `gh pr checks <number> --watch`. This normally takes 3-5 minutes.
3. If any check fails, stop — do not merge. Report what failed. Fix it on
   `main`, push, and the same PR will pick up the new commit and re-run
   checks.
4. Once everything is green, merge the PR (`gh pr merge --merge`). This
   merge commit lands on `public-release-v1` and triggers Stage 3:
   - Render deploy hook fires
   - `/health` is polled for up to 5 minutes to confirm the live site is
     actually healthy, not just that the trigger fired
   - A new patch version tag (vX.Y.Z+1) is created automatically, which
     also fires `release.yml` to create a GitHub Release
5. Report back: what was shipped, confirmation `/health` came back
   healthy, and the new version tag.

A manual minor/major version bump (`git tag vX.Y.0 && git push github
vX.Y.0`) is separate from this flow and only done on explicit request, for
a change that feels like a real milestone rather than a routine patch.

## Local dev

- `run_local.bat` starts the local Flask dev server on `http://localhost:5000`
  (Windows batch file — run from a normal terminal, not the Bash tool; `Ctrl+C`
  to stop). It only auto-installs `requirements.txt` when creating a brand-new
  `venv/` — if `venv/` already exists and a dependency was added (e.g.
  `flask-wtf` for CSRF), run `venv\Scripts\pip.exe install -r requirements.txt`
  manually first.
- Tests: `python -m pytest tests/ -q`. Run against a throwaway DB
  (`DATABASE_URL=sqlite:///_predeploy_test.db` or similar), not the real dev
  DB, and clean up the throwaway file afterward.

## Housekeeping learned the hard way

- `*.db-journal` files are SQLite leftovers from test runs — gitignored
  (alongside `*.db`), delete them if they show up untracked rather than
  committing them.
- A stray `.git/index.lock` with no live git process holding it is safe to
  delete — check `ps` for an actual running `git` process before assuming a
  lock is real.
- No `DEPLOY.bat` / automated one-click deploy script — the user prefers
  Claude Code in VS Code to run and verify every push directly, following
  the workflow above, rather than a script that skips the diff-review step.
