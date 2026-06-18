# GitHub Actions Workflows

This directory contains automated CI/CD workflows for Menu Planner.

## Workflows Overview

### 1. **tests.yml** — Unit Testing
- **When:** On push and pull requests
- **Tests:** Python 3.9, 3.10, 3.11
- **Coverage:** Core modules and backend
- **Reports:** Codecov coverage reports
- **Time:** ~5-10 minutes

### 2. **lint.yml** — Code Quality & Linting
- **When:** On push and pull requests
- **Checks:**
  - Black code formatting
  - Flake8 style validation
  - Pylint quality scoring (threshold: 7.0)
  - isort import sorting
- **Time:** ~3-5 minutes

### 3. **security.yml** — Security Analysis
- **When:** On push and pull requests
- **Checks:**
  - Bandit security scanning (Python)
  - Safety dependency vulnerability check
  - CodeQL analysis (Python + JavaScript)
- **Reports:** Security advisories on suspicious patterns
- **Time:** ~10-15 minutes

### 4. **build.yml** — Cross-platform Build
- **When:** On push and pull requests
- **Platforms:** Ubuntu, Windows, macOS
- **Python Versions:** 3.9, 3.11
- **Checks:**
  - All dependencies install successfully
  - Core modules import without errors
  - Required data files are valid JSON
  - Flask app initializes correctly
- **Time:** ~15-20 minutes (parallel across OS)

### 5. **frontend-checks.yml** — Frontend Validation
- **When:** On push and pull requests
- **Checks:**
  - HTML template structure validation
  - CSS files existence and integrity
  - Theme registry completeness
  - i18n translation coverage (English/Norwegian)
- **Time:** ~3-5 minutes

### 6. **data-validation.yml** — Data Integrity
- **When:** On push and pull requests
- **Validates:**
  - All JSON files are syntactically valid
  - Recipe data has required fields
  - Categories are properly structured
  - Pantry staples are complete
  - Theme registry consistency
  - i18n translations are paired (EN/NO)
- **Time:** ~3-5 minutes

### 7. **release.yml** — Release & Deployment
- **When:** On version tags (v*.*.*)
- **Actions:**
  - Final validation before release
  - Creates GitHub Release
  - Generates release notes
- **Triggers:** `git tag -a v1.0 -m "Message"` then `git push origin v1.0`
- **Time:** ~5 minutes

---

## Running Workflows Manually

Workflows automatically run on push/PR. To manually trigger:

1. Go to **Actions** tab on GitHub
2. Select the workflow
3. Click **Run workflow**
4. Choose branch and click **Run**

---

## Workflow Status

Check the status badge on README.md or in **Actions** tab.

Failed workflows indicate:
- **tests.yml:** Unit test failures
- **lint.yml:** Code style issues
- **security.yml:** Security vulnerabilities
- **build.yml:** Dependency issues on any platform
- **frontend-checks.yml:** HTML/CSS/i18n problems
- **data-validation.yml:** Data structure issues
- **release.yml:** Release validation failed

---

## Local Testing

Before pushing, run tests locally:

```bash
# Run tests
pytest tests/ -v --cov=core

# Run linting
flake8 core/ pi-deployment/
black --check core/ pi-deployment/
pylint core/ pi-deployment/

# Security check
bandit -r core/ pi-deployment/
safety check

# Validate data
python -c "import json; json.load(open('data/sample_recipes.json'))"
```

---

## Configuration

To modify workflow behavior, edit the respective `.yml` file:
- **Add branches:** Edit `on.push.branches` and `on.pull_request.branches`
- **Change Python versions:** Edit `matrix.python-version`
- **Change schedules:** Add `schedule` trigger
- **Skip workflow:** Add `[skip ci]` to commit message

---

## Secrets & Environment

Currently using:
- `GITHUB_TOKEN` (auto-provided by GitHub)
- No additional secrets required

If you add integrations later:
1. Go to **Settings → Secrets and variables → Actions**
2. Add secret (e.g., `CODECOV_TOKEN`)
3. Reference in workflow: `${{ secrets.CODECOV_TOKEN }}`

---

## Next Steps

1. Create a test directory: `mkdir tests/`
2. Add unit tests: `touch tests/test_menu_generator.py`
3. Push to GitHub to trigger workflows
4. Check **Actions** tab for results
5. Fix any failures before merging to master

---

**Created:** June 18, 2026  
**Workflows Status:** Ready (not yet triggered)  
**Manual Trigger:** Available in Actions tab
