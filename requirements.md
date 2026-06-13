# Pi-Menu: Technical Requirements & Specifications

**Version:** 1.0  
**Date:** 2026-06-13  
**Author:** Vartdal + Claude Code  
**License:** Personal Use (Vartdal Household)

---

## 1. Data Model & Structure

### 1.1 Recipe JSON Schema

```json
{
  "id": "unique-recipe-id",
  "title": "Stekt laks og gulrot- og perlecouscoussalat",
  "subtitle": "med ristede valnøtter, pære og salatost",
  "category": "Populære",
  "url": "https://www.hellofresh.no/recipes/...",
  "rating": 4.0,
  "rating_count": 268,
  "time_minutes": 25,
  "difficulty": "Enkel",
  "tags": ["RASK"],
  "allergens": ["Gluten", "Hvete", "Nødder", "Melk", "Egg", "Fisk"],
  "description": "Recipe description paragraph...",
  "ingredients_included": [
    {
      "quantity": 234,
      "unit": "stk",
      "name": "Perlecouscous",
      "allergens": ["Gluten", "Hvete"]
    }
  ],
  "ingredients_not_included": [
    {
      "quantity": 4,
      "unit": "dl",
      "name": "Vann til perlecouscous"
    }
  ],
  "instructions": [
    {
      "step": 1,
      "title": "Kok perlecouscous",
      "description": "Detailed step instructions...",
      "image_path": "data/recipes_cache/[recipe-id]/step-1.jpg"
    }
  ]
}
```

**Notes:**
- NO calories field (intentionally excluded)
- Images stored locally (not URLs)
- Both included & not-included ingredients captured

### 1.2 Pantry Staples (Never on Shopping List)

```json
{
  "pantry_staples": [
    "salt",
    "pepper",
    "oil",
    "olivenolje",
    "smør",
    "vann",
    "vann til koking",
    "hvitløk",
    "garlic",
    "chili",
    "chilipepper",
    "sukker",
    "løk",
    "onion"
  ]
}
```

**Filtering logic:** If ingredient name fuzzy-matches any pantry staple, exclude from shopping list.

### 1.3 Weekly Menu JSON

```json
{
  "week_start": "2026-06-16",
  "week_end": "2026-06-22",
  "generated_at": "2026-06-13T09:00:00Z",
  "dinners": [
    {
      "day": "Mandag",
      "recipe_id": "stekt-laks-og-gulrot-...",
      "title": "Stekt laks og gulrot- og perlecouscoussalat",
      "time_minutes": 25
    },
    {
      "day": "Tirsdag",
      "recipe_id": "kjottboller-i-cajunkrydret-...",
      "title": "Kjøttboller i cajunkrydret tomatsaus",
      "time_minutes": 25
    }
  ],
  "shopping_list": {
    "Proteins": [
      {"ingredient": "Laksefilet", "quantity": 300, "unit": "g"},
      {"ingredient": "Kjøttdeig", "quantity": 500, "unit": "g"}
    ],
    "Vegetables": [
      {"ingredient": "Potet", "quantity": 1.5, "unit": "kg"},
      {"ingredient": "Gulrot", "quantity": 800, "unit": "g"}
    ],
    "Pantry": []
  }
}
```

---

## 2. Scraper Specifications

### 2.1 Recipe Sources

**Initial seed (3 categories):**
1. https://www.hellofresh.no/recipes/mest-populaere-oppskrifter (Popular)
2. https://www.hellofresh.no/recipes/familie (Family)
3. https://www.hellofresh.no/recipes/rask-mat (Quick dinner)

**Target:** 100+ recipes across these 3 categories

**Future categories (Phase 3):**
- Italiensk mat, Thaimat, Kinesisk mat, Meksikansk mat, Vietnamesisk mat, etc.

### 2.2 Scraper Logic

**hellofresh_scraper.py:**

```
1. Fetch listing page (e.g., mest-populaere-oppskrifter)
2. Extract all recipe links from the listing
3. For each recipe link:
   a. Fetch the individual recipe page (HTML)
   b. Parse all fields (title, ingredients, instructions, images)
   c. Download all step images locally
   d. Save HTML to data/recipes_cache/[recipe-id]/index.html
   e. Save images to data/recipes_cache/[recipe-id]/step-[N].jpg
   f. Create JSON metadata: data/recipes_cache/[recipe-id]/metadata.json
4. Compile all metadata into recipes_db.json
5. Log results (skipped recipes, errors, etc.)
```

**Key constraints:**
- No live scraping on Pi (only on Windows PC)
- Images downloaded locally (no external image URLs in final JSON)
- Respects HelloFresh ToS (one-time scrape, no distribution)
- Rate limiting (1-2 second delays between requests to avoid overload)

### 2.3 Orange Allergy Filter

**During scraping, exclude recipes containing:**
- "appelsin"
- "oransje"
- "orange" (English, if it appears)
- "orange juice"
- "orange zest"
- "orange marmelade"

**Allow these citrus:**
- "sitron" (lemon)
- "lime"
- "grapefruit"
- "sitrusfrukt"

**Implementation:** Simple string matching (case-insensitive) in recipe title, subtitle, ingredients, or description.

---

## 3. Ingredient Deduplication Specifications

### 3.1 Fuzzy Matching Algorithm

**Threshold:** 90% similarity (using Levenshtein distance or similar fuzzy string matching)

**Example mappings:**
```
"potet" = "potater" = "potatis" = "potato" → Normalize to "Potet"
"gulrot" = "gulrøtter" → Normalize to "Gulrot"
"løk" = "løker" = "onion" → Normalize to "Løk"
"hvitløk" = "hvitlok" = "garlic" → Normalize to "Hvitløk" (then filtered as pantry staple)
```

**But keep separate:**
- "Potet" ≠ "Søtpotet" (regular potato vs. sweet potato)
- "Sitron" ≠ "Appelsin" (lemon vs. orange - orange filtered anyway)
- "Chili" ≠ "Chiliflakes" (whole vs. flakes - both grouped as "Chili")

### 3.2 Quantity Aggregation

**Rule:** Sum quantities across dinners for the same ingredient

**Example:**
```
Dinner 1: 500g Potet
Dinner 2: 400g Poteter
Dinner 3: 200g Potet
---
Result: 1.1 kg Potet (or "1 stor pose" / large bag)
```

**Unit handling:**
- Convert compatible units: 1000g = 1kg
- Keep original units if incompatible: "3 cloves" + "1 head" → stay separate (user groups manually)

### 3.3 Pantry Staple Filtering

**List of pantry staples** (not on shopping list):
- Salt, pepper, oil, butter, sugar, water
- Garlic, chili (user buys pre-packaged "nett" or "pose")
- Any custom user-defined staples

**Filtering logic:**
```
For each ingredient:
  IF ingredient.name fuzzy_matches any pantry_staple:
    SKIP (don't add to shopping list)
  ELSE:
    ADD to shopping list
```

### 3.4 Shopping List Grouping

**Categories (auto-grouped):**
1. **Proteins:** Meat, fish, chicken, tofu, etc.
2. **Vegetables:** Fresh produce
3. **Dairy:** Cheese, yogurt, milk, etc.
4. **Pantry:** Rice, pasta, beans, spices (excluding staples)
5. **Other:** Anything else

**Output format:**
```json
{
  "Proteins": [
    {"ingredient": "Laksefilet", "quantity": 600, "unit": "g"},
    {"ingredient": "Kjøttdeig", "quantity": 800, "unit": "g"}
  ],
  "Vegetables": [
    {"ingredient": "Potet", "quantity": 1.5, "unit": "kg"},
    {"ingredient": "Gulrot", "quantity": 1.0, "unit": "kg"}
  ]
}
```

---

## 4. Menu Generator Specifications

### 4.1 Menu Generation Rules

**Input:** Recipes database (recipes_db.json)

**Output:** Weekly menu (5 dinners for Monday-Saturday; Sunday = leftovers or takeout)

**Rules:**
1. **No oranges:** Exclude recipes with orange allergen filter
2. **Variety of proteins:**
   - Try to mix: chicken, beef, fish, vegetarian (at least 1 veggie)
   - Avoid repeating protein type on consecutive days
3. **Time variety:**
   - Mix of quick (15-25 min) and moderate (25-35 min) recipes
4. **Random selection:** Pick randomly from filtered pool each time

**Algorithm:**
```
1. Filter recipes (exclude oranges, any other user filters)
2. For each dinner (Mon-Sat):
   a. Pick a random recipe from remaining pool
   b. Track protein type used
   c. Prefer different protein than previous dinner
3. Deduplicate ingredients across all 5 dinners
4. Output weekly_menu.json
```

### 4.2 Determinism (Optional)

**For debugging:** Can add seed parameter to make menu generation repeatable.  
**Default:** True randomness (different menu each week)

---

## 5. Flask Dashboard Specifications

### 5.1 Web Interface Pages

**Home/Dashboard (`/`):**
- Display week at a glance
- 5 dinner cards (Mon-Sat)
- Each card: title, time, protein type
- Clickable to view full recipe

**Recipe Detail (`/recipe/<recipe-id>`):**
- Full recipe: title, subtitle, time, difficulty
- All ingredients (grouped)
- Step-by-step instructions with images
- Print-friendly view

**Shopping List (`/shopping`):**
- Grouped by category (Proteins, Vegetables, Dairy, etc.)
- Checkboxes for each item (client-side only, not saved)
- Print-friendly
- Export to text (optional)

**API endpoint (`/api/menu`):**
- Returns current week's menu as JSON
- Used by email notifier, To Do sync

### 5.2 UI/UX Requirements

- **Mobile-friendly:** Responsive design (works on phone, tablet, desktop)
- **Language:** Norwegian
- **Colors:** Clean, light (Vartdal's preference)
- **Images:** All step-by-step photos displayed
- **No tracking/analytics:** Plain HTML/CSS/JS, no external dependencies

### 5.3 Hosting

- **Server:** Flask (built-in development server for simplicity)
- **Port:** 5000 (http://10.0.0.54:5000)
- **Access:** Home WiFi only (not exposed to internet)
- **Startup:** Run as background service on Pi (systemd or manual)

---

## 6. To Do.com Integration Specifications

### 6.1 Authentication

**OAuth 2.0 flow using Microsoft Identity:**
- Client ID: `6a554392-f3fb-4e8e-b85c-4970711ea412`
- Tenant ID: `d450370d-b4f6-4ee6-916c-1d3c2091d1a3`
- Client Secret: [saved on Pi securely]

### 6.2 Lists to Create

**1. "Ukemeny" (Weekly Menu)**
```
├─ Mandag: Stekt laks og gulrot- og perlecouscoussalat
│  └─ Ingredients: Laksefilet (300g), Gulrot (1), ...
├─ Tirsdag: Kjøttboller i cajunkrydret tomatsaus
│  └─ Ingredients: Kjøttdeig (500g), Løk (2), ...
├─ Onsdag: ...
├─ Torsdag: ...
├─ Fredag: ...
└─ Lørdag: ...
```

**2. "Handleliste" (Shopping List)**
```
├─ Proteins
│  ├─ Laksefilet 600g
│  ├─ Kjøttdeig 800g
├─ Vegetables
│  ├─ Potet 1.5 kg
│  ├─ Gulrot 1.0 kg
├─ Dairy
│  ├─ Ost 200g
└─ Other
   └─ ...
```

### 6.3 Sync Trigger

- **When:** Saturday 9 AM
- **Action:** Generate menu → create/overwrite Ukemeny list → create/overwrite Handleliste
- **Access:** Both lists visible in To Do app (phone + web)
- **Checkboxes:** Users check items off in To Do app as they shop

---

## 7. Email Notifier Specifications

### 7.1 Email Contents

**Subject:** "Din ukemeny - [Week Start Date]"

**Body:**
```
Hei Vartdal og familie,

Her er menyen for denne uken (Mandag-Lørdag):

Mandag: Stekt laks og gulrot- og perlecouscoussalat (25 min)
Tirsdag: Kjøttboller i cajunkrydret tomatsaus (25 min)
Onsdag: ...
Torsdag: ...
Fredag: ...
Lørdag: ...

Handlelisten er oppdatert i To Do: [link to To Do list]

Eller se alle oppskrifter her: http://10.0.0.54:5000

Lykke til med matlagingen!
```

**Timing:** Friday 6 PM (or configurable)  
**Recipients:** vartdal@gmail.com (wife can be added later)

---

## 8. Scheduler & Automation Specifications

### 8.1 Cron Job (APScheduler)

```python
# Run every Saturday at 9 AM
scheduler.add_job(
    func=generate_and_sync_menu,
    trigger="cron",
    day_of_week="sat",
    hour=9,
    minute=0
)
```

**Actions:**
1. Generate new menu (menu_generator.py)
2. Sync to To Do.com (to_do_sync.py)
3. Save weekly_menu.json
4. Log completion

### 8.2 Manual Trigger (Optional)

**Flask endpoint:** `POST /api/regenerate`
- Allows manual menu generation anytime
- Useful for testing or unexpected changes

---

## 9. Deployment to Raspberry Pi

### 9.1 Pi Directory Structure

```
/home/vartdalffs/pi-menu/
├── app.py                 (Flask entry point)
├── config.py              (Settings, API keys)
├── requirements.txt       (Dependencies)
├── systemd/
│   └── pi-menu.service   (Autostart service)
├── logs/
│   └── app.log
└── data/
    ├── recipes_db.json
    ├── weekly_menu.json
    └── recipes_cache/    (copied from PC or shared folder)
```

### 9.2 Setup Steps

1. **Copy code to Pi** (via SCP or shared folder)
2. **Install dependencies:** `pip install -r requirements.txt --break-system-packages`
3. **Create config.py** with Azure credentials
4. **Test Flask app:** `python app.py`
5. **Setup systemd service** (autostart on reboot)
6. **Copy recipe cache** from PC to Pi

### 9.3 Network Share (Optional)

**Alternative to copying:** Pi reads recipes_cache from Windows shared folder
- Faster development (update recipes on PC, Pi reads live)
- Requires SMB/Samba setup
- Add to /etc/fstab for auto-mount

---

## 10. Testing Checklist

- [ ] Scraper fetches 100+ recipes successfully
- [ ] Orange filter excludes all orange-containing recipes
- [ ] Ingredient deduplication fuzzy-matches correctly
- [ ] Menu generator picks 5 diverse recipes
- [ ] Shopping list deduplicates quantities correctly
- [ ] Flask dashboard loads all pages
- [ ] Recipe images display correctly
- [ ] To Do.com sync creates lists with correct structure
- [ ] Email notifier sends with correct formatting
- [ ] Scheduler runs Saturday 9 AM automatically
- [ ] Pi can run Flask server 24/7 without memory issues

---

## 11. Success Criteria

✅ Weekly menu generated automatically every Saturday  
✅ All recipes + images cached locally (no live scraping)  
✅ Shopping list deduplicated and grouped  
✅ To Do.com updated with menu + shopping list  
✅ Flask dashboard accessible on home WiFi  
✅ Email summary sent Friday evening  
✅ Pantry staples (garlic, chili) not on shopping list  
✅ Orange allergen filtered correctly  
✅ Pi 2 can handle all operations (memory, CPU)  
✅ Norwegian language throughout  

---

*Generated by Claude Code | Never too late to give up! ⚰️*
