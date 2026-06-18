# Pi-Menu Project Cleanup Proposal

**Date:** June 18, 2026  
**Status:** PROPOSAL FOR REVIEW  
**Goal:** Prepare project for public release (GitHub)

---

## 📋 Executive Summary

The Pi-Menu project is feature-complete and ready for public release. This document outlines a cleanup strategy to:
1. **Remove internal documentation** that is not useful to end users
2. **Consolidate guides** into a clear, single setup flow
3. **Clean up git branches** used for development
4. **Verify no secrets are exposed**
5. **Ensure directory structure is clean and professional**

**Estimated Time to Complete:** 30 minutes  
**Risk Level:** LOW (mostly deletions, no code changes)

---

## ✅ Files & Directories to KEEP

### Essential Documentation
- **README.md** ← Primary entry point (already excellent)
- **docs/SETUP_GUIDE.md** ← Installation & first-run instructions
- **docs/EXCEL_GUIDE.md** ← How to add recipes via Excel
- **docs/FAQ.md** ← Common questions
- **docs/INTEGRATION_SETUP_GUIDE.md** ← Optional: MS To Do, Todoist, TickTick setup
- **FEATURE_ROADMAP.md** ← Future features (useful for contributors)
- **LICENSE** ← MIT license

### Configuration
- **.env.example** ← Template showing ALL possible config keys
- **.env.template** ← Alternative template format
- **.gitignore** ← Git configuration
- **requirements.txt** ← Python dependencies
- **config.py** ← Application config logic
- **pantry_staples.json** ← Sample ingredient database

### Source Code (all directories)
- **core/** ← Core business logic
- **frontend/** ← Web interface (HTML, CSS, JS)
- **pi-deployment/** ← Application entry point
- **scripts/** ← CLI tools (recipes, categories, menu generation)
- **data/** ← Sample data (recipes, categories)
- **templates/** ← Excel import template

### Git Structure
- **.git/** ← Version history (keep)
- **master** branch ← Stable releases
- **public-release-v1** branch ← Current release (keep)

---

## 🗑️ Files & Directories to DELETE

### Internal Development Docs (Not for end users)
- [ ] **CLEANUP_AUDIT_PLAN.md** ← Internal audit (developer-only)
- [ ] **READY_FOR_REVIEW.md** ← Delivery status from dev phase
- [ ] **DELIVERY_SUMMARY.md** ← Delivery notes from dev phase
- [ ] **AUTONOMOUS_IMPROVEMENTS.md** ← Log of autonomous improvements (historical)
- [ ] **ARCHITECTURE.md** ← Overly technical, not needed for users

### Redundant Configuration
- [ ] **.env.template** ← Keep only .env.example (both serve same purpose)

### Git Branches (Keep history, delete branches)
- [ ] **backup-before-theme-updates** ← Development restore point (no longer needed)
- [ ] **scale-adjustments** ← Development restore point (no longer needed)
- Keep: **master**, **public-release-v1**, **origin/master**, **origin/public-release-v1**

### Build Artifacts (auto-generated)
- [ ] **__pycache__/** ← Python cache (auto-regenerated, not needed in repo)

---

## 📂 Directory Structure (After Cleanup)

```
Pi-Menu/
├── README.md                           ← Start here
├── LICENSE                             ← MIT License
├── requirements.txt                    ← Python dependencies
├── config.py                           ← Config logic
├── .env.example                        ← Config template
├── .gitignore                          ← Git rules
├── pantry_staples.json                 ← Sample ingredients
│
├── docs/                               ← User documentation
│   ├── SETUP_GUIDE.md                  ← Installation (5 min quick start)
│   ├── EXCEL_GUIDE.md                  ← How to add recipes
│   ├── FAQ.md                          ← Troubleshooting
│   ├── INTEGRATION_SETUP_GUIDE.md      ← Optional: Task manager sync
│   ├── FREE_RECIPE_SOURCES.md          ← Where to find recipes
│   └── V1.1_FEATURE_PLAN.md            ← Planned features
│
├── FEATURE_ROADMAP.md                  ← Future roadmap (for contributors)
│
├── core/                               ← Core logic
│   ├── __init__.py
│   ├── menu_generator.py
│   ├── ingredient_parser.py
│   └── ... (unchanged)
│
├── frontend/                           ← Web UI
│   ├── static/                         ← CSS, JS, images
│   │   ├── themes/                     ← 9 themes
│   │   ├── style.css
│   │   └── ... (unchanged)
│   └── templates/                      ← HTML templates
│       └── ... (unchanged)
│
├── pi-deployment/                      ← App entry point
│   └── app.py
│
├── scripts/                            ← CLI tools
│   ├── pi-menu-cli.py                  ← Main CLI
│   ├── import_recipes.py
│   └── ... (unchanged)
│
├── data/                               ← Sample data
│   ├── recipes_en.json                 ← 10 sample recipes
│   ├── recipes_no.json
│   └── categories.json
│
└── templates/                          ← Import templates
    ├── pi-menu-recipe-template.xlsx    ← Excel template for adding recipes
    └── recipe-template-instructions.txt
```

---

## 🔍 Pre-Release Safety Checklist

### Security ✅
- [x] **No API keys in .env** (verified - all empty/placeholder)
- [x] **No secrets in code** (verified - all config via .env)
- [x] **.gitignore is correct** (keeps .env and __pycache__ out)
- [x] **No personal data** (verified)

### Documentation ✅
- [x] **README is clear** (excellent quick start)
- [x] **SETUP_GUIDE covers installation** 
- [x] **EXCEL_GUIDE explains recipe import**
- [x] **FAQ answers common questions**
- [x] **Code is commented where needed**

### Code Quality ✅
- [x] **No hardcoded values** (all config via .env)
- [x] **Requirements.txt is current** (Flask, Werkzeug, etc.)
- [x] **Python 3.9+ compatible** (verified)
- [x] **All 9 themes working** (verified - just fixed theme dropdown)

### Git Hygiene ✅
- [x] **Commits are clean** (no merge artifacts)
- [x] **Branch names are clear** (public-release-v1 is primary)
- [x] **No stale branches** (backup-* branches can be deleted)

---

## 🚀 Cleanup Action Plan

### Step 1: Delete Internal Documentation (5 min)
```bash
cd Pi-Menu
rm CLEANUP_AUDIT_PLAN.md
rm READY_FOR_REVIEW.md
rm DELIVERY_SUMMARY.md
rm AUTONOMOUS_IMPROVEMENTS.md
rm ARCHITECTURE.md
```

### Step 2: Clean Up Config (2 min)
```bash
# Keep .env.example, remove redundant .env.template
rm .env.template

# Verify .gitignore excludes .env and __pycache__
cat .gitignore  # Should show: .env, __pycache__, venv/
```

### Step 3: Delete Git Branches (3 min)
```bash
# Delete local development branches
git branch -d backup-before-theme-updates
git branch -d scale-adjustments

# Verify only these remain:
# - master
# - public-release-v1
git branch -a
```

### Step 4: Verify & Create Final Commit (5 min)
```bash
# Review what's being deleted
git status

# Commit deletions
git add -A
git commit -m "chore: cleanup internal dev docs and branches before public release

- Remove internal-only documentation (CLEANUP_AUDIT_PLAN, READY_FOR_REVIEW, etc.)
- Delete development restore branches (backup-before-theme-updates, scale-adjustments)
- Clean up redundant .env.template
- Leave all user-facing docs and guides intact
- Project is now ready for public GitHub release

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

### Step 5: Final Verification (5 min)
```bash
# Verify project structure
find . -name "*.md" -type f | sort
# Should show only: README.md, FEATURE_ROADMAP.md, docs/* (no cleanup/audit/delivery files)

# Verify no secrets in git
git log --all --oneline | head -20  # Review recent commits

# Test that app still runs
python3 pi-deployment/app.py
# Should start cleanly on http://localhost:5000
```

---

## 📚 New User Journey (After Cleanup)

A new user will:

1. **Visit GitHub** → Sees clear README
2. **Clone repo** → 10 seconds
3. **Read SETUP_GUIDE.md** → 3 minutes (quick start covers 90% of cases)
4. **Run 5 commands** → 2 minutes
5. **Open browser** → App running with 10 sample recipes
6. **Click "Add Recipe"** → Intuitive form
7. **Click "Generate Menu"** → Menu appears
8. **Click "Shopping List"** → Deduped ingredients
9. **Read FAQ.md** if needed → Answers common questions
10. **Optional: Read INTEGRATION_SETUP_GUIDE.md** → If they want To Do sync

**Total time to running app:** ~5 minutes  
**Total time to first custom menu:** ~10 minutes

---

## ⚠️ What NOT to Delete

- **Do NOT delete FEATURE_ROADMAP.md** — Contributors need to know planned features
- **Do NOT delete docs/INTEGRATION_SETUP_GUIDE.md** — Users might want optional integrations
- **Do NOT delete docs/FREE_RECIPE_SOURCES.md** — Useful reference for finding recipes
- **Do NOT delete v1.1 feature plan** — Road map for future
- **Do NOT delete git history** — Keep all commits for transparency

---

## ✨ Result

After cleanup, the project will be:
- ✅ **Clean** — No internal/temporary files
- ✅ **Professional** — Clear directory structure
- ✅ **User-Focused** — Docs guide users, not developers
- ✅ **Production-Ready** — Can be published to GitHub immediately
- ✅ **Safe** — No secrets, no personal data
- ✅ **Well-Documented** — Users have everything they need

**Recommended Git Tag (after cleanup):**
```bash
git tag -a v1.0 -m "Pi-Menu v1.0 - First public release"
git push origin v1.0
```

---

## Approval Required

**Before proceeding with cleanup, confirm:**
- [ ] Delete CLEANUP_AUDIT_PLAN.md, READY_FOR_REVIEW.md, DELIVERY_SUMMARY.md, AUTONOMOUS_IMPROVEMENTS.md, ARCHITECTURE.md?
- [ ] Delete .env.template (keep .env.example)?
- [ ] Delete development branches (backup-before-theme-updates, scale-adjustments)?
- [ ] Create final cleanup commit?
- [ ] Ready for GitHub public release?

**Reply: "approved" to proceed with full cleanup.**
