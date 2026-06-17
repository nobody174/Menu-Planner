# Pi-Menu Complete Cleanup Audit & Action Plan

**Date:** June 17, 2026  
**Status:** ANALYSIS COMPLETE - AWAITING APPROVAL  
**Total Project Size:** 4.3MB

---

## 🔴 CRITICAL FINDINGS: SECRETS EXPOSED

### Active Secrets in Version Control (HIGH RISK)

**Location:** `.env` (root directory)
- **TICKTICK_API_TOKEN:** `[REDACTED_TICKTICK_TOKEN]`
- **NOTION_API_TOKEN:** `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`
- **Status:** ⚠️ THESE ARE COMMITTED TO GIT

**Risk Level:** CRITICAL - These tokens are valid, active credentials.

**Action Required:** 
1. Rotate both tokens immediately (user should do this in their service accounts)
2. Remove `.env` from this commit and force-push (or new commit to sanitize)

---

## 📊 PROJECT STRUCTURE ANALYSIS

### Root Level Files (18 items)
```
.env (CONTAINS SECRETS - see above)
.env.example
.env.template
.env (duplicate in pi-deployment/)
ARCHITECTURE.md
AUTONOMOUS_IMPROVEMENTS.md
DELIVERY_SUMMARY.md
FEATURE_ROADMAP.md
LICENSE
README.md
READY_FOR_REVIEW.md
SHOPPING_INTEGRATIONS.md
config.py
requirements.txt
pantry_staples.json
.gitignore
.git/ (git metadata)
__pycache__/ (build artifact)
```

### Directories Analysis

#### `/core` (4 Python files)
- `__init__.py` - Empty, can keep
- `error_handler.py` - Active, keep
- `ingredient_deduplicator.py` - Active, keep
- `menu_generator.py` - Active, keep
- `todo_sync.py` - **DUPLICATE ISSUE** (see below)

#### `/pi-deployment` (9 files + 2 subdirs)
- `.env` - CONTAINS SECRETS (different from root - has empty values, safer)
- `.env.template` - Safe, template
- `__init__.py` - Empty, keep
- `auth.py` - Active, keep
- `flask_app.py` - Active, main app (48KB)
- `shopping_integrations.py` - Active, keep
- `to_do_sync.py` - **DUPLICATE of core/todo_sync.py** (different versions!)
- `scheduler.py` - Active, keep
- `email_notifier.py` - Active, keep
- `cert.pem` - Self-signed certificate, keep (needed for HTTPS)
- `key.pem` - Self-signed key, keep (needed for HTTPS)
- `flask.log` - 1.6KB log file
- `/logs/` - Application logs (144KB total, old logs)
- `/__pycache__/` - 140KB compiled Python (build artifact)

#### `/frontend`
- `/static/` - All active, keep (JS, CSS, i18n, manifest, service worker)
- `/templates/` - All active HTML templates, keep (11 templates)

#### `/data`
- `categories.json` - Active data, keep
- `recipes_db.json` - Active data (212KB), keep
- `sample_recipes.json` - Active sample data, keep
- `weekly_menu.json` - User data, keep
- `/recipe-packs/` - 5 active recipe pack files (180KB total), keep
- `/recipes_cache/` - Empty directory, DELETE

#### `/docs`
- `DEVELOPER_GUIDE.md` - Active, keep
- `EXCEL_GUIDE.md` - Active, keep
- `FAQ.md` - Active, keep
- `FREE_RECIPE_SOURCES.md` - Active, keep
- `HEADER_TEMPLATE.txt` - Template file, keep
- `INTEGRATION_SETUP_GUIDE.md` - Active, recently updated
- `SETUP_GUIDE.md` - Active, keep
- `V1.1_FEATURE_PLAN.md` - Active roadmap, keep
- `/screenshots/` - 8 empty directories (no files), DELETE

#### `/logs`
- `app.log` - 796KB (old development logs)
- `deduplicator.log` - 7.6KB
- `flask_app.log` - 20KB (old logs from development)
- `email_notifier.log` - Empty
- `menu_generator.log` - Empty
- `scheduler.log` - Empty
- `to_do_sync.log` - Empty
All old/empty - CONSIDER DELETING (development artifacts)

#### `/scripts`
- `category-editor.py` - Standalone utility script
- `import_recipes.py` - Standalone utility script
- `pi-menu-cli.py` - CLI tool, not used in web app
- `test-api.py` - Test script
- `test-local.py` - Test script
**Status:** None of these are active in the web application; they're standalone utilities

#### `/templates`
- `recipe-template-instructions.txt` - Template documentation, keep

---

## 🗑️ CLEANUP ACTION LIST

### SECTION A: FILES TO DELETE (Non-Code)

| Path | Type | Reason | Risk | Action |
|------|------|--------|------|--------|
| `/logs/app.log` | File | 796KB old development log | LOW | DELETE |
| `/logs/deduplicator.log` | File | Old development log | LOW | DELETE |
| `/logs/flask_app.log` | File | Old development log | LOW | DELETE |
| `/logs/email_notifier.log` | File | Empty log file | NONE | DELETE |
| `/logs/menu_generator.log` | File | Empty log file | NONE | DELETE |
| `/logs/scheduler.log` | File | Empty log file | NONE | DELETE |
| `/logs/to_do_sync.log` | File | Empty log file | NONE | DELETE |
| `/pi-deployment/flask.log` | File | 1.6KB old log | LOW | DELETE |
| `/data/recipes_cache/` | Folder | Empty cache folder | NONE | DELETE |
| `/docs/screenshots/anydo/` | Folder | Empty, feature removed | NONE | DELETE |
| `/docs/screenshots/apple-reminders/` | Folder | Empty (no screenshots) | NONE | DELETE |
| `/docs/screenshots/google-keep/` | Folder | Empty, feature removed | NONE | DELETE |
| `/docs/screenshots/microsoft-todo/` | Folder | Empty (no screenshots) | NONE | DELETE |
| `/docs/screenshots/notion/` | Folder | Empty, feature removed | NONE | DELETE |
| `/docs/screenshots/ticktick/` | Folder | Empty (no screenshots) | NONE | DELETE |
| `/docs/screenshots/todoist/` | Folder | Empty (no screenshots) | NONE | DELETE |
| `/docs/screenshots/trello/` | Folder | Empty, feature removed | NONE | DELETE |
| `__pycache__/` (root) | Folder | 4KB compiled Python | NONE | DELETE |
| `__pycache__/` (core) | Folder | 49KB compiled Python | NONE | DELETE |
| `__pycache__/` (pi-deployment) | Folder | 140KB compiled Python | NONE | DELETE |

**Total space to reclaim:** ~2MB

---

### SECTION B: DUPLICATE/CONFLICTING FILES

| Path | Issue | Versions | Action |
|------|-------|----------|--------|
| `core/todo_sync.py` vs `pi-deployment/to_do_sync.py` | **DUPLICATE WITH DIFFERENCES** | Different implementations (core has 13KB, pi-deployment has 7.5KB) | **DECISION NEEDED**: Keep pi-deployment version (simpler, correct), DELETE core version |

**Impact:** Remove redundant code, reduce confusion

---

### SECTION C: FILES TO SANITIZE (Secrets/Credentials)

| Path | Contents | Current Status | Action |
|------|----------|---|--------|
| `.env` (root) | TICKTICK_API_TOKEN, NOTION_API_TOKEN | **CONTAINS REAL SECRETS** | CREATE NEW CLEAN VERSION (empty values) + FORCE PUSH |
| `.env` (pi-deployment) | All empty values | SAFE | No action, keep as-is |
| `.gitignore` | Correctly lists .env | OK | Keep as-is |

**Critical Step:** 
1. Rotate TICKTICK and NOTION tokens immediately
2. Replace `.env` with empty placeholder
3. Force push to remove secret from git history (or new commit)

---

### SECTION D: FILES TO KEEP (No Changes)

| Path | Type | Reason |
|------|------|--------|
| `/core/*.py` (3 files, minus duplicate) | Code | Active application logic |
| `/pi-deployment/flask_app.py` | Code | Main Flask application |
| `/pi-deployment/shopping_integrations.py` | Code | Integration handlers |
| `/pi-deployment/auth.py` | Code | Authentication |
| `/pi-deployment/scheduler.py` | Code | Scheduled tasks |
| `/pi-deployment/email_notifier.py` | Code | Email notifications |
| `/frontend/static/*` | UI Assets | Active stylesheets, JS, i18n |
| `/frontend/templates/*` | HTML | All 11 templates are active |
| `/data/*.json` | Data | Recipe database, categories, menus |
| `/data/recipe-packs/*.json` | Data | 5 recipe packs (72+ recipes) |
| `/docs/*.md` | Documentation | User guides and setup docs |
| `/scripts/*.py` | Utilities | Standalone tools (not in main app) |
| `/pi-deployment/cert.pem` + `key.pem` | Security | SSL certificates (needed for HTTPS) |
| `.env.template` + `.env.example` | Config | Safe templates, no secrets |
| `config.py` | Code | Configuration constants |
| `requirements.txt` | Config | Dependency list |
| `README.md` | Docs | Main readme |
| `LICENSE` | Legal | MIT license |
| `FEATURE_ROADMAP.md` | Docs | Roadmap |
| `pantry_staples.json` | Data | Ingredient reference |
| `.gitignore` | Config | Already protects .env |

---

### SECTION E: DOCUMENTATION TO REVIEW

| File | Status | Note |
|------|--------|------|
| `ARCHITECTURE.md` | Review | May reference removed features |
| `AUTONOMOUS_IMPROVEMENTS.md` | Review | May reference removed features |
| `DELIVERY_SUMMARY.md` | Review | May reference removed features |
| `SHOPPING_INTEGRATIONS.md` | **RECENTLY UPDATED** | Reflects current integrations (Todoist, TickTick, Apple Reminders) |
| `READY_FOR_REVIEW.md` | Review | May be outdated |
| `INTEGRATION_SETUP_GUIDE.md` | **RECENTLY UPDATED** | Reflects current integrations only |

**Action:** Quick scan for references to removed features (Any.do, Trello, Notion, Google Keep, Microsoft To Do)

---

### SECTION F: POTENTIALLY UNUSED SCRIPTS

| File | Type | Used | Action |
|------|------|------|--------|
| `/scripts/test-api.py` | Test utility | No (development testing) | KEEP (useful for testing) |
| `/scripts/test-local.py` | Test utility | No (development testing) | KEEP (useful for testing) |
| `/scripts/pi-menu-cli.py` | CLI tool | No (web app doesn't use CLI) | CONSIDER DELETING (feature removed) |
| `/scripts/category-editor.py` | Utility | No (feature removed) | CONSIDER DELETING |
| `/scripts/import_recipes.py` | Utility | Possibly (web app has import) | KEEP |

**Note:** Keeping test scripts for development; removing CLI tools that don't fit web-app focus.

---

## 📋 SUMMARY OF CLEANUP ACTIONS

### High Priority (SECURITY)
- [ ] **Rotate TICKTICK_API_TOKEN** (user action)
- [ ] **Rotate NOTION_API_TOKEN** (user action)
- [ ] **Replace .env file** with empty template
- [ ] **Force push sanitized commit** to remove secrets from git history

### Medium Priority (CODEBASE)
- [ ] Delete `core/todo_sync.py` (duplicate)
- [ ] Verify `pi-deployment/to_do_sync.py` is correct (simpler, better structured)
- [ ] Scan documentation for removed feature references

### Low Priority (CLEANUP)
- [ ] Delete all `/logs/*` files (development artifacts)
- [ ] Delete `__pycache__` folders (rebuilds automatically)
- [ ] Delete `/data/recipes_cache/` (empty directory)
- [ ] Delete empty `/docs/screenshots/*` subdirectories
- [ ] Consider deleting `/scripts/pi-menu-cli.py` and `category-editor.py` (unused)

### No Changes Needed
- [ ] Keep all active Python code
- [ ] Keep all data files
- [ ] Keep frontend assets
- [ ] Keep documentation
- [ ] Keep SSL certificates

---

## 🔒 SECURITY REVIEW SUMMARY

**Current State:**
- ✅ `.gitignore` correctly lists `.env`
- ⚠️ **BUT:** `.env` was committed WITH SECRETS before .gitignore was added
- ✅ `.env.template` and `.env.example` are safe (no secrets)
- ✅ `/pi-deployment/.env` is safe (no real values)

**Risks Identified:**
- 🔴 **ACTIVE TOKENS IN GIT HISTORY**
  - TICKTICK_API_TOKEN
  - NOTION_API_TOKEN
  
**Remediation Required:**
1. Rotate both tokens in their services
2. Remove from git history (new clean commit)
3. User should NOT reuse these tokens

---

## 📊 SPACE ANALYSIS

**Current Size:** 4.3MB

**Breakdown:**
- Logs: 828KB (deletable: 812KB)
- __pycache__: 193KB (deletable)
- Screenshot folders: Empty (deletable)
- Active code: ~500KB
- Data: ~350KB
- Docs: ~100KB

**After Cleanup:** ~2.3MB (46% reduction)

---

## ✅ VERIFICATION CHECKLIST

Before cleanup approval, verify:
- [ ] User has backed up any local .env files
- [ ] User has rotated tokens (or willing to do after cleanup)
- [ ] User understands git history will need force-push
- [ ] No active development work in progress
- [ ] Flask can be restarted cleanly

---

## 🎯 NEXT STEPS

**AWAITING YOUR APPROVAL**

When you say **"GO!"**, I will:

1. **Rotate Secrets** (you handle via service dashboards)
2. **Delete files** per "SECTION A" above
3. **Remove duplicate** `core/todo_sync.py`
4. **Sanitize `.env`** with empty template
5. **Scan docs** for feature references
6. **Force-push clean commit** with message:
   ```
   Project cleanup: removed development artifacts, sanitized secrets, 
   deleted unused files, verified integrity
   ```
7. **Test Flask** to confirm everything works
8. **Final verification** of project state

---

**STATUS:** READY FOR APPROVAL ✋

Please review and approve each section before I proceed.
