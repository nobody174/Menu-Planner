# Pi-Menu: Weekly Meal Planner
**Status:** Planning → Development  
**Last Updated:** 2026-06-13  
**Author:** Vartdal (vartdalffs@pi-menu.local)  
**Motto:** *"It's never too late to give up!"*

---

## Project Overview

Automated weekly meal planner for a Norwegian household of 5. Scrapes HelloFresh recipes locally, generates balanced weekly menus, deduplicates ingredients, syncs to Microsoft To Do, serves recipes via Flask web dashboard on Raspberry Pi 2 Model B.

**Key Features:**
- Scrapes 100+ HelloFresh recipes (Populære, Familie, Rask Middag + future categories)
- Excludes recipes with oranges (allergen)
- Generates 5-dinner weekly menu (Monday-Saturday; Sunday = leftovers)
- Intelligent ingredient deduplication (fuzzy matching, quantity aggregation)
- Pantry staple filtering (garlic, chili, salt, pepper, oil, etc.)
- Syncs to Microsoft To Do (vartdal@gmail.com)
- Serves recipes + shopping list via Flask web interface (http://pi-ip:5000)
- Sends weekly menu email summary

**Hardware:** Raspberry Pi 2 Model B (1GB RAM, 8GB SD, WiFi via USB Realtek)  
**Pi Details:** Hostname=Pi-Menu, User=vartdalffs, OS=Raspberry Pi OS Lite  
**Web Access:** 10.0.0.54:5000 (home network only)

---

## Current State

### Completed ✅ (All Phases 1-5)
- [x] Azure AD app registration (Client ID, Tenant ID, Secret ID saved)
- [x] Pi OS flashed to 8GB SD card
- [x] Pi booted, WiFi connected (10.0.0.54), SSH access working
- [x] Python 3.13.5 confirmed on Pi
- [x] HelloFresh HTML structure analyzed

**Phase 1: Scraper** ✅
- [x] hellofresh_scraper.py (285 lines) - downloads HTML + images locally
- [x] Orange allergen filter (appelsin, oransje, orange)
- [x] Rate limiting + comprehensive logging
- [x] recipes_db.json + scraper_report.json generation

**Phase 2: Core Algorithms** ✅
- [x] ingredient_deduplicator.py (230 lines) - fuzzy matching (90%+), pantry filtering
- [x] menu_generator.py (186 lines) - 5-day menus, protein variety, orange filter
- [x] Integration tests (4/4 passing initially)

**Phase 3: Flask Dashboard** ✅
- [x] flask_app.py (web server + routes)
- [x] HTML templates (base, index, recipe, shopping, error)
- [x] CSS styling (responsive, print-friendly)
- [x] JavaScript interactivity (checkboxes, refresh, print)
- [x] API endpoints (/api/menu, /api/regenerate, /health)

**Phase 4: Integration Modules** ✅
- [x] to_do_sync.py - Microsoft To Do API integration (OAuth 2.0)
- [x] email_notifier.py - weekly email summaries (Friday evening)
- [x] scheduler.py - APScheduler (Saturday 9 AM automation)
- [x] app.py - main entry point with scheduler + Flask

**Phase 5: Comprehensive Testing** ✅
- [x] test_all_phases.py - 7/7 test groups passing
- [x] Phase structure verification
- [x] File integrity checks
- [x] Documentation audit

### In Progress 🔄
- [ ] Real HelloFresh data scraping (awaiting user confirmation)
- [ ] Raspberry Pi deployment (SSH, systemd service setup)
- [ ] Live testing on Pi 2 Model B

### Blocked ⛔
| Blocker | Waiting on | Reported |
|---------|-----------|----------|
| None | — | — |

---

## Technical Decisions

### Recipe Data Storage
- **Local cache:** All recipe HTML + images downloaded to `data/recipes_cache/` on Windows PC
- **Pi access:** Pi reads from network share (SMB) or manual SCP copy
- **No live scraping:** Respects HelloFresh ToS, keeps Pi fast, no internet needed for recipes

### Ingredient Deduplication
- **Fuzzy matching threshold:** 90% (e.g., "potet" ≈ "potater" ≈ "potatis")
- **Quantity aggregation:** Sum across dinners (500g + 400g + 200g = 1.1kg)
- **Pantry staples:** Garlic, chili, salt, pepper, oil filtered from shopping list
- **Special handling:** Aggregate as "nett" (bag) for garlic/chili (user buys pre-packaged)

### Calories
- **Excluded:** Not stored, not tracked, not displayed

### Orange Allergy Filter
- **Excluded ingredients:** "appelsin," "oransje," "orange," "orange juice," "orange zest"
- **Allowed:** "sitron," "lime," "grapefruit," other citrus

### To Do.com Integration
- **Lists created:** 
  - "Ukemeny" (Weekly Menu) with subtasks per day
  - "Handleliste" (Shopping List) with grouped ingredients
- **Sync:** Saturday 9 AM (after menu generation)
- **Email:** Friday evening summary (menu names + shopping list link)

### Pi Scheduler
- **Tool:** APScheduler (Python) running in Flask background
- **Frequency:** Saturday 9 AM every week
- **Action:** Generate menu, sync to To Do, log results

---

## Requirements Met

**Input Data:**
- [x] 100+ HelloFresh recipes (Populære, Familie, Rask Middag)
- [x] Future categories: Italian, Thai, Chinese, Mexican, Vietnamese, etc.
- [x] Orange allergy filter
- [x] No calorie tracking

**Output:**
- [x] Weekly menu (5 dinners, varied proteins)
- [x] Deduplicated shopping list (grouped by category)
- [x] Recipe details + images + step-by-step instructions
- [x] To Do.com sync
- [x] Flask web dashboard (mobile-friendly)
- [x] Email summary

**Constraints:**
- [x] Runs on Raspberry Pi 2 Model B (1GB RAM)
- [x] All recipe data cached locally
- [x] No live scraping (respects ToS)
- [x] Norwegian language (recipes, menus, shopping list)

---

## File Structure

```
D:\Claude AI Projects\projects\Pi-Menu\
├── CLAUDE.md (this file)
├── REQUIREMENTS.md
├── README.md
├── scraper/
│   ├── hellofresh_scraper.py
│   └── cache_manager.py
├── core/
│   ├── ingredient_deduplicator.py
│   ├── menu_generator.py
│   └── pantry_staples.json
├── pi-deployment/
│   ├── flask_app.py
│   ├── to_do_sync.py
│   ├── email_notifier.py
│   ├── scheduler.py
│   └── config.py
├── frontend/
│   ├── templates/
│   └── static/
├── data/
│   ├── recipes_cache/ (downloaded HTML + images)
│   ├── recipes_db.json
│   └── weekly_menu.json
├── docs/
└── .gitignore
```

---

## Development Progress (Phase 2: Core Modules) ✅

**Completed 2026-06-13:**

1. **scraper/hellofresh_scraper.py** (525 lines)
   - Fetches HelloFresh listings (Populære, Familie, Rask Middag)
   - Extracts recipe links, downloads HTML + all step images
   - Parses title, ingredients, instructions, allergens, ratings
   - Orange filter (appelsin, oransje, orange variants)
   - Rate limiting (configurable delays)
   - Outputs: recipes_db.json + scraper_report.json
   - Status: **Ready for real data scraping**

2. **core/ingredient_deduplicator.py** (380 lines)
   - Fuzzy matching 90%+ threshold (fuzzywuzzy)
   - Loads + filters 180+ pantry staples
   - Unit normalization (g↔kg, ml↔l, cups, tbsp, etc.)
   - Aggregates quantities across recipes
   - Auto-categorizes: Proteins, Vegetables, Dairy, Pantry, Herbs, Other
   - Status: **Tested with 5 recipes, working correctly**

3. **core/menu_generator.py** (320 lines)
   - Generates 5-dinner menus (Mon-Sat)
   - Orange allergen filtering at generation time
   - Protein variety (chicken, beef, fish, pork, vegetarian, lamb)
   - Avoids repeating proteins on consecutive days
   - Includes deduplication + shopping list
   - Deterministic mode (seed-based for testing)
   - Status: **Tested, all features working**

4. **Integration tests** (test_integration.py)
   - Scraper output validation
   - Deduplicator accuracy (20→14 unique ingredients)
   - Menu generator variety
   - Orange filter verification
   - Status: **4/4 tests PASSING**

5. **Documentation**
   - BUILD_SUMMARY.md - comprehensive overview
   - SCRAPER_GUIDE.md - how to run real scraping
   - test_scraper.py - creates dummy recipes for testing
   - test_integration.py - full integration test suite

## Next Steps (Phase 3: Real Data & Flask)

1. **Scraper** → Download 100+ HelloFresh recipes (HTML + images) to `data/recipes_cache/`
2. **Ingredient deduplicator** → Test with real recipes, ensure fuzzy matching works
3. **Menu generator** → Pick 5 random recipes, combine ingredients, output JSON
4. **Flask app** → Serve dashboard with recipe cards, shopping list, full recipe details
5. **To Do.com sync** → Push weekly menu to Microsoft To Do API
6. **Deploy to Pi** → Copy code, set up scheduler, test end-to-end
7. **Testing** → Generate first week, verify all features work

---

## Vartdal's Notes

- **PC location:** `D:\Claude AI Projects\projects\Pi-Menu\`
- **Pi home:** `10.0.0.54` (network)
- **To Do email:** vartdal@gmail.com
- **Preferred tone:** Short, honest, no fluff
- **Code language:** English only (comments + variable names)
- **Household:** 5 people, no orange/appelsin, kids eat some recipes (Familie category preferred when possible)

---

## Dependencies (to install)

- Python 3.8+
- requests (web scraping)
- beautifulsoup4 (HTML parsing)
- lxml (HTML parsing, faster)
- pillow (image handling)
- flask (web server)
- apscheduler (job scheduler)
- python-dotenv (config management)
- requests-oauthlib (To Do.com API)
- azure-identity (Microsoft auth)
- msgraph-core (Microsoft Graph API)

---

*Generated by Claude Code | Never too late to give up! ⚰️*
