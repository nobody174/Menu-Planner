# CI/CD Pipeline

## Branch model

- **`main`** — day-to-day working branch. Pushes here run the full pipeline
  (Stages 1–2) but never deploy. No branch protection — pushing is instant.
- **`public-release-v1`** — production. Protected: GitHub rejects any direct
  push unless all 8 required status checks have already passed on that
  exact commit. The only way to land a change here is a pull request from
  `main` that has gone fully green, then merged.

## Pipeline

```mermaid
flowchart TD
    pushmain["Push to main"] --> stage1
    openpr["Open PR: main -> public-release-v1"] --> stage1pr

    subgraph stage1["Stage 1 on main - fast, cheap checks (parallel)"]
        lint1["Lint & Format"]
        data1["Data Validation"]
        frontend1["Frontend Checks"]
    end

    subgraph stage1pr["Stage 1 on PR - same checks, required to merge"]
        lint2["Lint & Format"]
        data2["Data Validation"]
        frontend2["Frontend Checks"]
    end

    stage1 -->|green| stage2
    stage1pr -->|green| stage2pr

    subgraph stage2["Stage 2 on main (parallel)"]
        tests1["Tests - pytest + Postgres"]
        security1["Security Scan - Bandit high-severity"]
        build1["Build Check - Ubuntu + Windows"]
        docker1["Build Docker Image"]
    end

    subgraph stage2pr["Stage 2 on PR - required to merge (parallel)"]
        tests2["Tests"]
        security2["Security Scan"]
        build2["Build Check"]
        docker2["Build Docker Image"]
    end

    stage2 --> savedone["main updated - no deploy"]
    stage2pr -->|all 8 checks green| mergeok["PR mergeable"]

    mergeok --> merge["Merge PR"]
    merge -->|real push to public-release-v1| stage3

    subgraph stage3["Stage 3 - deploy, only on push to public-release-v1"]
        deploy["Trigger Render deploy hook"]
        health["Poll /health up to 5 min"]
        tag["Auto-tag vX.Y.Z+1"]
        deploy --> health --> tag
    end

    tag -.->|tag push| release["release.yml: Create GitHub Release"]
    manualtag["Manual: git tag vX.Y.0 for a milestone"] -.-> release
```

## What each stage does

**Stage 1 (parallel, ~1-3 min each)**
- **Lint & Format** — flake8 (real syntax/undefined-name errors fail the
  build; style issues reported only), black formatting check (a real gate)
- **Data Validation** — all JSON valid, recipe/category/theme/i18n structure
- **Frontend Checks** — HTML template structure, CSS files present

**Stage 2 (parallel, only if Stage 1 is green, ~1-5 min each)**
- **Tests** — full pytest suite against a real Postgres service container
- **Security Scan** — Bandit (`--severity-level high`, fails only on High
  findings), Safety dependency check (reported only)
- **Build Check** — dependency install + Flask/core import check on Ubuntu
  and Windows
- **Build Docker Image** — confirms the production Docker image builds

**Stage 3 (only on a real push to `public-release-v1`, i.e. a PR merge —
never on `main` pushes or PR-only runs)**
- Triggers the Render deploy hook
- Polls `https://menuplanner.no/health` for up to 5 minutes to confirm the
  live site is actually healthy
- Auto-tags a new patch version (`vX.Y.Z` → `vX.Y.Z+1`), which also fires
  `release.yml` to create a GitHub Release

A manual minor/major bump (`git tag vX.Y.0 && git push github vX.Y.0`) is
separate from this flow and only done on request, for a change that feels
like a milestone rather than a routine patch.

## Keeping this doc in sync

This diagram is a static snapshot, not generated from `ci.yml` — it will
not update itself. Whenever `ci.yml`, `release.yml`, or the
`public-release-v1` branch protection rules change, update this file in
the same change.
