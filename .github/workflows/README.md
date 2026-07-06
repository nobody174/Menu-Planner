# GitHub Actions Workflows

## Branches

- **`main`** — day-to-day working branch. Pushes here run the full CI
  pipeline but never deploy.
- **`public-release-v1`** — production branch. Protected: GitHub rejects
  any direct push here unless all 8 required status checks have already
  passed on that exact commit. Ship a change via a pull request from
  `main` — once every check is green, merging the PR triggers a live
  deploy to menuplanner.no via a Render webhook.

## ci.yml — the real pipeline

Runs on every push/PR to `main` and `public-release-v1`, staged so cheap
checks fail fast before expensive ones run:

**Stage 1 (parallel, ~1-3 min each)**
- **Lint & Format** — flake8 (real syntax/undefined-name errors fail the
  build; style issues are reported only), black formatting check
- **Data Validation** — all JSON valid, recipe/category/theme/i18n structure
- **Frontend Checks** — HTML template structure, CSS files present

**Stage 2 (parallel, only runs if Stage 1 is green, ~5-15 min each)**
- **Tests** — full pytest suite against a real Postgres service container
  (matches production's database engine)
- **Security Scan** — Bandit (fails on high-severity findings), Safety
  dependency check (reported only)
- **Build Check** — dependency install + Flask/core import check on Ubuntu
  and Windows
- **Build Docker Image** — confirms the production Docker image builds

**Stage 3 (only if every Stage 2 job is green, and only on a real push to
`public-release-v1`, never on a PR)**
- Triggers the Render deploy hook
- Polls `https://menuplanner.no/health` until it reports healthy (or fails
  loudly after 5 minutes)

## release.yml — optional, manual, separate from deploy

Only fires on a version tag (`v*.*.*`), not on any branch push. Creates a
GitHub Release with notes. This is unrelated to shipping a change to
production — that happens via the `public-release-v1` push above. Tag a
release when you want one:

```
git tag v1.2.0
git push github v1.2.0
```

## Local testing before pushing to `main`

```bash
# Start the local dev server
run_local.bat        # http://localhost:5000, Ctrl+C to stop

# Run tests directly
pytest tests/ -v --cov=core

# Run the same lint checks CI runs
flake8 deployment core database --select=E9,F63,F7,F82
black --check deployment core database
```

## Secrets

- `RENDER_DEPLOY_HOOK_URL` — required for the Stage 3 deploy trigger.
- `GITHUB_TOKEN` — auto-provided by GitHub, used by `release.yml`.
