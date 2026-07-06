# Menu Planner — Working Instructions for Claude Code

## Deploy workflow (how pushes to production happen)

Pushes to `public-release-v1` auto-deploy to **menuplanner.no** via a Render
webhook triggered by `.github/workflows/ci.yml`. A bad push goes live
automatically unless caught first. Follow this every time, no shortcuts:

1. **`git status`** first. If there's anything unexpected (stray files,
   more changes than expected, a lock file, a branch that's diverged from
   `github/public-release-v1`), stop and investigate before doing anything
   else. Don't just trust a summary of what changed — check it yourself.
2. **Read the actual diff**, not just the file list. `git diff --stat` to
   see scope, then read the real diff for anything non-trivial. If a
   commit message (yours, the user's, or a co-worker session's) describes
   something unusual — "corruption recovery," a security fix, a data
   migration, mass file changes — verify that description against the
   actual diff before trusting it. Don't commit on the strength of a
   write-up alone.
3. **Pull/merge first if needed.** If local is behind
   `github/public-release-v1`, fetch and merge before pushing. Resolve
   conflicts carefully — don't blindly take one side; read both hunks and
   keep what's real (see past merges in this repo for the pattern: keep
   both additions when they're independent, don't discard either side
   without reading it).
4. **Stage deliberately.** Prefer `git add <specific files>` over blind
   `git add -A` when the changeset is mixed; at minimum, review
   `git status` after staging to confirm nothing surprising got included
   (e.g. `.db`, `.db-journal`, or other local/generated files that should
   be gitignored, not committed).
5. **Commit** with a message that describes the *why*, not just the *what*
   — matches the style already in this repo's git log and `CHANGELOG.md`.
6. **Push**: `git push github public-release-v1` (the `github` remote is
   `https://github.com/nobody174/Menu-Planner.git` — same target as
   `origin`).
7. **Confirm CI is green.** This repo runs several workflows on push
   (`ci.yml`, `lint.yml`, `tests.yml`, `security.yml`, `build.yml`,
   `frontend-checks.yml`, `data-validation.yml`) — the one that actually
   triggers the Render deploy is `ci.yml`. Check
   `gh run list --workflow=ci.yml --branch=public-release-v1 --limit=1` (or
   `gh run watch <id>`) rather than assuming success. If it fails, the
   Render deploy trigger may not have fired, or may have fired against
   broken code — flag this immediately, don't treat the push as done.
8. **Report back plainly**: what was pushed, in one or two sentences, plus
   confirmation CI passed (or a clear flag if it didn't/couldn't be
   checked).

Tags (`v1.0.0`, `v1.1.0`, ...) are separate from this flow and only created
on explicit request — a push to `public-release-v1` does not tag a release
(see `.github/workflows/release.yml`).

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
