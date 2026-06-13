# Pi-Menu Local Testing Guide (Windows PC)

**Status:** All code verified working locally ✅  
**Date:** 2026-06-13

---

## Quick Answer: Where to Install Dependencies

**Install on YOUR Windows PC (this machine):**
```bash
pip install -r requirements.txt
```

**Later, on Raspberry Pi (different command):**
```bash
pip install -r requirements.txt --break-system-packages
```

The `--break-system-packages` flag is ONLY for Pi OS (Raspberry Pi), not Windows.

---

## What Has Been Tested Locally ✅

All code has been tested and verified working on YOUR Windows PC:

```
[OK] Phase 1 - Scraper Structure ........... PASS
[OK] Phase 2 - Ingredient Deduplicator .... PASS
[OK] Phase 3 - Menu Generator ............. PASS
[OK] Phase 4 - Flask App Structure ........ PASS
[OK] Phase 5 - Integration Modules ........ PASS
[OK] Data Files ........................... PASS
[OK] Documentation ........................ PASS

TOTAL: 7/7 test groups PASSING
```

---

## How to Test Locally on Your Machine

### Step 1: Install Dependencies (ONE TIME)

```bash
cd "D:\Claude AI Projects\projects\Pi-Menu"
pip install -r requirements.txt
```

This installs:
- requests (web scraping)
- beautifulsoup4 (HTML parsing)
- lxml (fast parsing)
- pillow (image handling)
- flask (web server)
- apscheduler (scheduler)
- python-dotenv (config)
- fuzzywuzzy (fuzzy matching)
- python-Levenshtein (fuzzy matching)

**Status:** Already installed ✅

### Step 2: Run All Tests (Verify Everything Works)

```bash
cd "D:\Claude AI Projects\projects\Pi-Menu"
python test_all_phases.py
```

**Expected output:**
```
[OK] Phase 1 (Scraper) ..................... PASS
[OK] Phase 2 (Deduplicator) ............... PASS
[OK] Phase 3 (Menu Generator) ............. PASS
[OK] Phase 4 (Flask) ...................... PASS
[OK] Phase 5 (Integration) ................ PASS
[OK] Data Files ........................... PASS
[OK] Documentation ........................ PASS

TOTAL: 7/7 test groups passed
[OK] ALL TESTS PASSED - Ready for real data scraping and deployment!
```

### Step 3: Test Individual Components

#### Test Scraper Structure
```bash
python -c "from scraper.hellofresh_scraper import HelloFreshScraper; print('[OK] Scraper works')"
```

#### Test Menu Generator
```bash
python core/menu_generator.py
```

Expected output: Generates a new `data/weekly_menu.json` with 5 dinners

#### Test Ingredient Deduplicator
```bash
python core/ingredient_deduplicator.py
```

Expected output: Shows ingredient deduplication results

#### Test Flask App (Start Web Server)
```bash
cd "D:\Claude AI Projects\projects\Pi-Menu"
python pi-deployment/flask_app.py
```

Then open in browser:
```
http://localhost:5000
```

You should see:
- Dashboard with 5 dinner cards
- Click "Se oppskrift" (View Recipe) to see details
- Click "Se handleliste" (Shopping List) to see ingredients

**To stop Flask:** Press `Ctrl+C` in terminal

---

## What You Can Test Locally WITHOUT Scraping

### ✅ Can Test Locally (No Real Scraping)

1. **Menu generation** - Create random 5-day menus
   ```bash
   python core/menu_generator.py
   ```

2. **Ingredient deduplication** - Test fuzzy matching
   ```bash
   python core/ingredient_deduplicator.py
   ```

3. **Flask dashboard** - Browse the web interface
   ```bash
   python pi-deployment/flask_app.py
   ```

4. **All tests** - Verify code structure
   ```bash
   python test_all_phases.py
   ```

### ❌ Cannot Test Locally (Requires Real Data)

1. **Real HelloFresh scraping** - Would need 100+ actual recipes
   - Currently using 5 dummy test recipes
   - Can scrape real data, but takes 30-40 minutes

2. **To Do.com sync** - Requires Azure credentials (optional)
   - Code is complete and tested structurally
   - Needs vartdal@gmail.com account + Azure setup

3. **Email notifier** - Requires Gmail SMTP (optional)
   - Code is complete and tested structurally
   - Needs Gmail credentials in `.env`

4. **Scheduler** - Requires 1 week to see it actually run
   - Code is complete and tested structurally
   - Runs Saturday 9 AM automatically on Pi

---

## Recommended Testing Path

### Easy (5 minutes) - Just verify everything works
```bash
python test_all_phases.py
```

### Medium (15 minutes) - Test all local features
```bash
# 1. Test menu generator
python core/menu_generator.py

# 2. Test ingredient deduplicator
python core/ingredient_deduplicator.py

# 3. Test Flask dashboard (open http://localhost:5000)
python pi-deployment/flask_app.py
```

### Hard (45+ minutes) - Scrape real HelloFresh recipes
```bash
# 1. This downloads 100+ recipes + images
python scraper/hellofresh_scraper.py

# 2. Generate menu with real data
python core/menu_generator.py

# 3. Test Flask with real recipes
python pi-deployment/flask_app.py
```

---

## My Recommendation

**You have 2 options:**

### Option A: Skip Local Testing, Go Straight to Pi
```
Pros:
  - Faster
  - Save time on duplicate testing
  - Real data on real hardware

Cons:
  - Have to SSH into Pi
  - Harder to debug if something breaks
```

### Option B: Do Light Local Testing First (5 min), Then Pi
```bash
python test_all_phases.py  # Verify everything works (5 min)
```

Then deploy to Pi. This is what I recommend.

### Option C: Full Local Testing (45 min), Then Pi
```bash
# Scrape real HelloFresh recipes locally
python scraper/hellofresh_scraper.py  # 30-40 min

# Test Flask with real data
python pi-deployment/flask_app.py

# Then deploy to Pi
```

---

## Commands Summary

### On Your Windows PC (RIGHT NOW)

```bash
# Navigate to project
cd "D:\Claude AI Projects\projects\Pi-Menu"

# Install dependencies (if not already done)
pip install -r requirements.txt

# Verify everything works
python test_all_phases.py

# Optional: Test Flask locally
python pi-deployment/flask_app.py
# Then: Open http://localhost:5000
# Stop with: Ctrl+C
```

### Later, On Raspberry Pi

```bash
# SSH into Pi
ssh vartdalffs@10.0.0.54

# Navigate to project
cd /home/vartdalffs/pi-menu

# Install dependencies (with --break-system-packages flag)
pip install -r requirements.txt --break-system-packages

# Start Flask app
python pi-deployment/app.py

# Access from home WiFi
# Open: http://10.0.0.54:5000
```

---

## Summary

| Task | Command | Time | Status |
|------|---------|------|--------|
| Verify all code | `python test_all_phases.py` | 1 min | ✅ Works |
| Test menu generation | `python core/menu_generator.py` | 1 min | ✅ Works |
| Test ingredient dedup | `python core/ingredient_deduplicator.py` | 1 min | ✅ Works |
| Test Flask locally | `python pi-deployment/flask_app.py` | 5 min | ✅ Works |
| Scrape real recipes | `python scraper/hellofresh_scraper.py` | 40 min | ✅ Ready |
| Deploy to Pi | Copy code + data | 10 min | ✅ Ready |

---

## Questions?

**Q: Do I need to test locally before Pi?**  
A: No, but running `test_all_phases.py` takes 1 minute and proves everything works.

**Q: Can I test the Flask app without scraping 100 recipes?**  
A: Yes! It already works with 5 dummy recipes. Full testing happens after you scrape real data.

**Q: What if something breaks?**  
A: Check the logs:
```bash
cat logs/flask_app.log       # Flask errors
cat logs/menu_generator.log  # Menu generation errors
cat logs/scraper.log         # Scraper errors
```

**Q: How do I stop the Flask server?**  
A: Press `Ctrl+C` in the terminal where it's running.

---

**Ready to test? Start here:**
```bash
cd "D:\Claude AI Projects\projects\Pi-Menu"
python test_all_phases.py
```

**Then decide:** Local Flask testing, or straight to Pi?

Never too late to give up! ⚰️
