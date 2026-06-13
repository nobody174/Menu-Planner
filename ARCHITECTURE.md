# Pi-Menu Architecture

## System Overview

```
┌─────────────────────────────────────────────────────────────────┐
│                         WINDOWS PC (Data Generation)             │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Scraper (hellofresh_scraper.py)                         │   │
│  │ - Fetches 3 HelloFresh categories                       │   │
│  │ - Downloads HTML + images locally                       │   │
│  │ - Orange filter applied during scraping                 │   │
│  └─────────────────────┬──────────────────────────────────┘   │
│                        │ recipes_db.json (JSON)               │
│                        │ recipes_cache/ (HTML + JPEGs)        │
│                        ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Menu Generator (menu_generator.py)                      │   │
│  │ - Loads recipes from JSON                               │   │
│  │ - Selects 5 random recipes (no orange)                  │   │
│  │ - Ensures protein variety                               │   │
│  └─────────────────────┬──────────────────────────────────┘   │
│                        │ weekly_menu.json                     │
│                        ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Ingredient Deduplicator (ingredient_deduplicator.py)   │   │
│  │ - Loads selected recipes                                │   │
│  │ - Fuzzy matches ingredients (90%+)                      │   │
│  │ - Filters pantry staples                                │   │
│  │ - Aggregates quantities                                 │   │
│  │ - Categorizes by type                                   │   │
│  └─────────────────────┬──────────────────────────────────┘   │
│                        │ shopping_list (in weekly_menu.json)  │
│                        ▼                                       │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Data Exported to Pi (or Network Share)                  │   │
│  │ - recipes_db.json (300+ recipes)                        │   │
│  │ - recipes_cache/ (all HTML + images)                    │   │
│  │ - weekly_menu.json (current week)                       │   │
│  └──────────────────────────────────────────────────────────┘   │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │ SCP / SMB Share
                           ▼
┌─────────────────────────────────────────────────────────────────┐
│               RASPBERRY PI 2 (Web Server + Scheduler)           │
├─────────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ Flask App (pi-deployment/flask_app.py) - PORT 5000     │   │
│  │ - GET  / : Dashboard (5 dinner cards)                   │   │
│  │ - GET  /recipe/<id> : Full recipe with images          │   │
│  │ - GET  /shopping : Shopping list (grouped)              │   │
│  │ - GET  /api/menu : JSON endpoint                        │   │
│  │ - POST /api/regenerate : Manual trigger                 │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                        │
│                        ▼                                        │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ APScheduler (pi-deployment/scheduler.py)               │   │
│  │ - Runs every Saturday 9 AM                              │   │
│  │ - Calls menu_generator.py                              │   │
│  │ - Triggers to_do_sync.py                               │   │
│  │ - Sends email_notifier.py                              │   │
│  └──────────────────────────────────────────────────────────┘   │
│                        │                                        │
│         ┌──────────────┼──────────────┐                        │
│         ▼              ▼              ▼                        │
│  ┌──────────┐   ┌──────────┐   ┌──────────────┐               │
│  │ To Do    │   │  Email   │   │ Save JSON    │               │
│  │ Sync     │   │ Notifier │   │ Updates      │               │
│  └──────────┘   └──────────┘   └──────────────┘               │
│                                                                  │
└─────────────────────────────────────────────────────────────────┘
                           │
                           ▼
                    ┌──────────────┐
                    │ Home WiFi    │
                    │ (10.0.0.54)  │
                    │ :5000        │
                    └──────────────┘
                           │
                           ▼
        ┌────────────────────────────────────┐
        │ User Access (Phone, Tablet, PC)   │
        │ - View weekly menu                │
        │ - Check recipes + instructions    │
        │ - See shopping list               │
        └────────────────────────────────────┘
```

---

## Data Flow

### 1. Data Generation (Windows PC)

```
hellofresh_scraper.py
├── Fetch listing: mest-populaere-oppskrifter
├── Extract 100 recipe links
├── For each recipe:
│   ├── Fetch HTML
│   ├── Parse fields (title, ingredients, allergens)
│   ├── Apply orange filter (skip if found)
│   ├── Download step images → data/recipes_cache/[id]/
│   └── Save metadata.json
└── Compile → data/recipes_db.json (291 recipes)
    └── Include: 9 orange recipes removed
```

**Output:** `recipes_db.json` + `recipes_cache/` (local disk)

### 2. Menu Generation (Windows PC or Pi)

```
menu_generator.py
├── Load recipes_db.json
├── Filter (remove orange recipes)
├── For each of 5 dinners:
│   ├── Pick random recipe
│   ├── Check protein type
│   ├── Avoid repeating protein
│   └── Add to menu
└── Output weekly_menu.json
    ├── 5 dinners (Mon-Sat)
    └── Raw ingredient list (100+ items)
```

### 3. Ingredient Deduplication (Part of menu generator)

```
ingredient_deduplicator.py
├── Load pantry_staples.json (180+ items)
├── Load recipes for selected 5 dinners
├── For each ingredient:
│   ├── Fuzzy match against pantry staples
│   │   └── If 90%+ match → FILTER OUT
│   ├── Fuzzy match against existing ingredients
│   │   └── If 90%+ match → MERGE (add quantities)
│   └── Normalize units (g→kg, ml→l)
├── Categorize by type (Proteins, Vegetables, etc.)
└── Output shopping_list (14-20 unique items)
    └── Grouped by category with quantities
```

**Output:** `shopping_list` in `weekly_menu.json`

### 4. Web Server (Raspberry Pi)

```
Flask App (Port 5000)
├── Static Files (CSS, JS)
│   └── frontend/static/
├── Templates (HTML)
│   └── frontend/templates/
├── Routes:
│   ├── GET / → Dashboard
│   │   ├── Load weekly_menu.json
│   │   ├── Render 5 dinner cards
│   │   └── Show thumbnail images
│   │
│   ├── GET /recipe/<recipe_id> → Detail
│   │   ├── Load metadata.json
│   │   ├── Display all step images
│   │   ├── List ingredients
│   │   └── Print-friendly layout
│   │
│   ├── GET /shopping → Shopping List
│   │   ├── Parse shopping_list from weekly_menu.json
│   │   ├── Group by category
│   │   ├── Add checkboxes (client-side)
│   │   └── Print view
│   │
│   └── GET /api/menu → JSON (for external tools)
│       └── Return weekly_menu.json
│
└── Served to home WiFi (10.0.0.54:5000)
```

### 5. Scheduler (Raspberry Pi)

```
APScheduler
├── Trigger: Every Saturday 9 AM
└── Actions:
    ├── Run menu_generator.py
    │   └── Generate new menu + shopping list
    │
    ├── Run to_do_sync.py
    │   ├── Authenticate to Microsoft
    │   └── Update "Ukemeny" + "Handleliste" lists
    │
    ├── Run email_notifier.py
    │   └── Send Friday 6 PM: Menu summary + links
    │
    └── Log results
        └── logs/scheduler.log
```

---

## Data Structures

### recipes_db.json (Array of recipes)

```json
[
  {
    "id": "recipe-unique-id",
    "title": "Stekt laks og gulrot med ris",
    "subtitle": "med sitron",
    "category": "Familie",
    "url": "https://www.hellofresh.no/recipes/...",
    "rating": 4.5,
    "rating_count": 100,
    "time_minutes": 25,
    "difficulty": "Enkel",
    "tags": ["RASK"],
    "allergens": ["Fisk"],
    "description": "...",
    "ingredients_included": [
      {"quantity": 400, "unit": "g", "name": "Laksefilet", "allergens": ["Fisk"]}
    ],
    "ingredients_not_included": [
      {"quantity": 0, "unit": "", "name": "Salt til koking"}
    ],
    "instructions": [
      {
        "step": 1,
        "title": "Tilberedning",
        "description": "...",
        "image_path": "data/recipes_cache/recipe-id/step-1.jpg"
      }
    ],
    "scraped_at": "2026-06-13T20:00:00"
  }
]
```

### weekly_menu.json

```json
{
  "week_start": "2026-06-16",
  "week_end": "2026-06-22",
  "generated_at": "2026-06-13T09:00:00Z",
  "dinners": [
    {
      "day": "Mandag",
      "recipe_id": "laks-gulrot",
      "title": "Stekt laks og gulrot med ris",
      "time_minutes": 25,
      "difficulty": "Enkel",
      "protein": "fish"
    }
  ],
  "shopping_list": {
    "Proteins": [
      {"ingredient": "Laksefilet", "quantity": 400, "unit": "g"}
    ],
    "Vegetables": [
      {"ingredient": "Gulrot", "quantity": 700, "unit": "g"}
    ]
  }
}
```

---

## File Organization

```
D:\Claude AI Projects\projects\Pi-Menu\
│
├── scraper/
│   ├── __init__.py
│   ├── hellofresh_scraper.py       (525 lines, primary scraper)
│   └── cache_manager.py            (TODO: cache cleanup, compression)
│
├── core/
│   ├── __init__.py
│   ├── ingredient_deduplicator.py  (380 lines, deduplication)
│   └── menu_generator.py           (320 lines, 5-day menus)
│
├── pi-deployment/
│   ├── __init__.py
│   ├── flask_app.py                (TODO: web dashboard)
│   ├── to_do_sync.py               (TODO: Microsoft Graph API)
│   ├── email_notifier.py           (TODO: email summaries)
│   ├── scheduler.py                (TODO: APScheduler setup)
│   └── config.py                   (API keys, secrets)
│
├── frontend/
│   ├── templates/
│   │   ├── base.html              (TODO: layout)
│   │   ├── index.html             (TODO: dashboard)
│   │   ├── recipe.html            (TODO: detail view)
│   │   └── shopping.html          (TODO: shopping list)
│   └── static/
│       ├── style.css              (TODO: styling)
│       └── app.js                 (TODO: client-side logic)
│
├── data/
│   ├── recipes_db.json            (300+ recipes from scraper)
│   ├── weekly_menu.json           (current week's menu)
│   ├── recipes_cache/
│   │   └── [recipe-id]/
│   │       ├── metadata.json
│   │       ├── index.html
│   │       ├── step-1.jpg
│   │       ├── step-2.jpg
│   │       └── ...
│   └── recipes_db_backup.json     (weekly backups)
│
├── logs/
│   ├── scraper.log
│   ├── scraper_report.json
│   ├── menu_generator.log
│   ├── deduplicator.log
│   └── scheduler.log
│
├── CLAUDE.md                      (project overview + status)
├── REQUIREMENTS.md                (specifications)
├── README.md                      (user guide)
├── BUILD_SUMMARY.md               (what's been built)
├── SCRAPER_GUIDE.md               (how to run scraper)
├── ARCHITECTURE.md                (this file)
├── requirements.txt               (Python dependencies)
├── .gitignore                     (git config)
├── test_scraper.py                (creates dummy data)
├── test_integration.py            (full test suite)
└── config.py                      (config base)
```

---

## Orange Filter Implementation

The orange filter is applied **twice**:

1. **During scraping** (`hellofresh_scraper.py`)
   ```python
   if self.contains_orange(title) or \
      self.contains_orange(subtitle) or \
      self.contains_orange(description):
       skip_recipe()
   ```

2. **During menu generation** (`menu_generator.py`)
   ```python
   generator.filter_recipes()  # Removes any orange recipes
   menu = generator.generate_menu()
   ```

**Tested keywords:**
- "appelsin" (Norwegian)
- "oransje" (Norwegian variant)
- "orange" (English)
- "orange juice", "orange zest", "orange marmelade"

---

## Pantry Staple Filtering

**Excluded from shopping list** (180+ items):
- Basics: salt, pepper, oil, butter, sugar, water
- Aromatics: garlic, onion, chili
- Condiments: soy sauce, ketchup, mustard, vinegar
- Spices: paprika, oregano, cumin, cinnamon
- Pantry: flour, baking powder, yeast, honey
- Pantry shelf-stable cheese: feta, parmesan, grana padano

**Logic:**
```
For each ingredient:
  IF fuzzy_match(ingredient, pantry_staples) >= 90%:
    FILTER OUT
  ELSE:
    ADD to shopping list
```

---

## Performance Targets

| Operation | Windows PC | Raspberry Pi 2 |
|-----------|-----------|--------|
| Scrape 100 recipes | 10 min | N/A (not recommended) |
| Generate menu (5 dinners) | <1 sec | <2 sec |
| Deduplicate ingredients | <1 sec | <1 sec |
| Render dashboard | <100 ms | <200 ms |
| Memory (Flask server idle) | N/A | <50 MB |
| Memory (serving 5 users) | N/A | <100 MB |

---

## Deployment Checklist

- [ ] Scrape 100+ recipes on Windows (SCRAPER_GUIDE.md)
- [ ] Test menu generation locally
- [ ] Copy `data/recipes_cache/` to Pi (via SCP or SMB)
- [ ] Copy `data/recipes_db.json` to Pi
- [ ] Install dependencies on Pi (--break-system-packages)
- [ ] Create Flask app + routes
- [ ] Test Flask server locally (port 5000)
- [ ] Setup systemd service (autostart on reboot)
- [ ] Test To Do.com sync
- [ ] Setup scheduler (Saturday 9 AM)
- [ ] Test email notifier
- [ ] Go live!

---

**Generated by Claude Code | Never too late to give up! ⚰️**
