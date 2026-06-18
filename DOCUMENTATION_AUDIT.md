# Documentation File Audit

**Date:** June 18, 2026  
**Purpose:** Determine which documentation files are necessary for public release vs. which are leftover planning docs

---

## 📄 Files Analyzed

### Root Level Files

#### 1. **SHOPPING_INTEGRATIONS.md** — 317 lines
**Status:** ⚠️ **KEEP WITH CAUTION**

**Content Summary:**
- Setup guides for 8 integrations: Trello, Notion, Google Keep, Any.do, Todoist, TickTick, Apple Reminders, Microsoft To Do
- Export formats: CSV, JSON, Text, ICS, Clipboard
- Configuration templates
- Troubleshooting tips

**Reality Check:**
- ❌ **Trello integration:** NOT implemented in current code (no `to_do_sync.py` for Trello)
- ❌ **Notion integration:** NOT implemented (references to `NOTION_API_TOKEN` but no backend code)
- ❌ **Google Keep integration:** NOT implemented (no email workaround coded)
- ❌ **Any.do integration:** NOT implemented
- ✅ **Microsoft To Do:** Implemented (OAuth flow works)
- ✅ **Todoist:** Setup guide exists, API integration possible
- ✅ **TickTick:** API token support in `.env`
- ✅ **Apple Reminders:** ICS export works
- ✅ **Export formats:** CSV, JSON, Text, Clipboard work

**Problem:** This doc describes 4-5 integrations that **do not exist in the code**. It's an aspirational roadmap, not actual functionality.

**Recommendation:** 
- **DELETE SHOPPING_INTEGRATIONS.md** ← Not accurate for v1.0
- **KEEP docs/INTEGRATION_SETUP_GUIDE.md** ← Covers only implemented features (MS To Do, exports)

---

#### 2. **FEATURE_ROADMAP.md** — 433 lines
**Status:** ✅ **KEEP (valuable for contributors)**

**Content Summary:**
- v1.0 completed features ✅
- v1.1 planned features (recipe discovery, preloaded packs, personal arsenal)
- v2.0+ future vision
- 12+ feature categories with detailed ideas
- Implementation priorities

**Assessment:**
- ✅ Accurate reflection of v1.0 state
- ✅ Clear roadmap for future development
- ✅ Useful for contributors to understand direction
- ✅ Not just "leftover" — it's a strategic planning document
- ✅ Helps community understand the project vision

**Recommendation:** **KEEP** — This is valuable for a public open-source project

---

#### 3. **SHOPPING_INTEGRATIONS.md vs docs/INTEGRATION_SETUP_GUIDE.md**
**Conflict Detected**

Both files exist and cover similar ground:

**SHOPPING_INTEGRATIONS.md:**
- Describes 8 integrations (many not implemented)
- 317 lines
- Aspirational/roadmap focused

**docs/INTEGRATION_SETUP_GUIDE.md:**
- Focused setup guide (cleaner)
- Covers only implemented features
- Follows the documentation structure pattern

**Issue:** Having both is confusing. Users might try to set up Trello/Notion and fail.

**Recommendation:** **DELETE SHOPPING_INTEGRATIONS.md** — Keep only `docs/INTEGRATION_SETUP_GUIDE.md`

---

### docs/ Directory Files

#### 4. **docs/SETUP_GUIDE.md**
**Status:** ✅ **KEEP (essential)**
- Installation instructions
- First-run setup
- Configuration guide
- Essential for new users

#### 5. **docs/EXCEL_GUIDE.md**
**Status:** ✅ **KEEP (essential)**
- How to add recipes via Excel
- Template instructions
- Import process
- Needed by users who want to bulk-add recipes

#### 6. **docs/FAQ.md**
**Status:** ✅ **KEEP (essential)**
- Common questions
- Troubleshooting
- Usage help
- Important for user support

#### 7. **docs/FREE_RECIPE_SOURCES.md** — 80+ lines
**Status:** ⚠️ **QUESTIONABLE - KEEP**

**Content:**
- Links to free Norwegian recipe sites (Mat.no, Tine.no, ICA.no, etc.)
- Links to free English recipe sites
- Usage rights information
- How to manually import

**Assessment:**
- ✅ Useful reference for users who want to add recipes
- ✅ No implementation required (documentation only)
- ⚠️ Links may go stale
- ✅ Part of v1.1 planning but useful as-is

**Recommendation:** **KEEP** — Users will appreciate the curated list of recipe sources

---

#### 8. **docs/V1.1_FEATURE_PLAN.md** — 293 lines
**Status:** ⚠️ **CONSIDER MOVING OR RENAMING**

**Content:**
- Detailed plan for v1.1 features (recipe packs, personal arsenal)
- Timeline (5 weeks)
- Success metrics
- Technical notes

**Assessment:**
- ❌ This is NOT v1.0 — it's planning for v1.1
- ❌ Users will be confused seeing "v1.1 Feature Plan" on public release
- ⚠️ It's detailed implementation planning, not general roadmap
- ✅ Useful for developers/contributors

**Recommendation:** 
- **MOVE to FEATURE_ROADMAP.md** — Merge v1.1 details into the main roadmap
- **DELETE docs/V1.1_FEATURE_PLAN.md** — It's redundant with FEATURE_ROADMAP.md

---

#### 9. **docs/INTEGRATION_SETUP_GUIDE.md** — 50+ lines
**Status:** ✅ **KEEP (essential)**

**Content:**
- Setup for implemented integrations
- Export formats
- Configuration steps
- Troubleshooting

**Assessment:**
- ✅ Covers only implemented features
- ✅ Clear step-by-step instructions
- ✅ Accurate for v1.0

**Recommendation:** **KEEP** — This is the right guide to keep

---

## 🎯 Final Recommendations

### DELETE (Inaccurate or Redundant)
- ❌ **SHOPPING_INTEGRATIONS.md** — Describes non-existent integrations (Trello, Notion, Google Keep, Any.do)
- ❌ **docs/V1.1_FEATURE_PLAN.md** — Redundant with FEATURE_ROADMAP.md, confusing to have as separate file

### KEEP (Essential for Users & Contributors)
- ✅ **README.md** — Entry point
- ✅ **ARCHITECTURE.md** — For contributors
- ✅ **FEATURE_ROADMAP.md** — Project vision
- ✅ **docs/SETUP_GUIDE.md** — Installation
- ✅ **docs/EXCEL_GUIDE.md** — Recipe import
- ✅ **docs/FAQ.md** — Troubleshooting
- ✅ **docs/FREE_RECIPE_SOURCES.md** — Recipe discovery
- ✅ **docs/INTEGRATION_SETUP_GUIDE.md** — Integration setup (only working ones)

---

## 📊 Impact Summary

### Before Cleanup
- 2 integration guides (conflicting)
- 1 feature plan file + 1 roadmap file (redundant)
- 1 file describing non-existent features

### After Cleanup
- 1 clear integration setup guide (docs/)
- 1 unified feature roadmap (root level)
- No false claims about integrations

### File Count
- **Before:** 15 documentation files
- **After:** 13 documentation files
- **Removed:** 2 files (SHOPPING_INTEGRATIONS.md, docs/V1.1_FEATURE_PLAN.md)

---

## ⚠️ Critical Finding

**SHOPPING_INTEGRATIONS.md is inaccurate for v1.0:**

Line 83-101 (TickTick) ✅ — Has backend support  
Line 62-80 (Todoist) ✅ — Has API token support  
Line 104-122 (Any.do) ❌ — **NO backend code**  
Line 149-177 (Notion) ❌ — **NO backend code**  
Line 180-201 (Trello) ❌ — **NO backend code**  
Line 126-147 (Google Keep) ❌ — **NO backend code**  

**Users who follow SHOPPING_INTEGRATIONS.md will configure tokens that don't work.**

This is why you should DELETE it and use only docs/INTEGRATION_SETUP_GUIDE.md (which is accurate).

---

## Action Items

To complete the documentation audit cleanup:

```bash
# 1. Delete inaccurate integration guide
rm SHOPPING_INTEGRATIONS.md

# 2. Delete redundant feature plan
rm docs/V1.1_FEATURE_PLAN.md

# 3. Commit
git add -A
git commit -m "docs: remove inaccurate and redundant documentation files

- Delete SHOPPING_INTEGRATIONS.md (describes non-implemented integrations)
- Delete docs/V1.1_FEATURE_PLAN.md (redundant with FEATURE_ROADMAP.md)
- Keep docs/INTEGRATION_SETUP_GUIDE.md (accurate for v1.0)

This prevents user confusion and aligns documentation with actual functionality."
```

---

**Status:** Ready for implementation  
**Files to delete:** 2  
**Estimated impact:** Low (removes confusing/redundant docs)  
**User-facing impact:** Positive (clearer documentation)
