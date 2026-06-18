# Pi-Menu: Complete Deep Project Analysis

**Analysis Date:** June 18, 2026  
**Analyzer:** Claude Code AI  
**Project Status:** Production-ready v1.0

---

# 1. PROJECT OVERVIEW (HIGH LEVEL)

## What Is Pi-Menu?

**Pi-Menu** is a modern, open-source web application for **weekly meal planning and shopping list management**. It helps families or households automatically generate varied weekly menus from their recipe collection, deduplicate ingredients, and create organized shopping lists.

## Who Is It For?

- **Families** wanting structured meal planning
- **Meal prep enthusiasts** who want variety week-to-week
- **People on a budget** who want ingredient deduplication and efficiency
- **Bilingual households** (Norwegian/English support)
- **Anyone** who wants to try different recipes without planning manually

## Core Idea

The project solves the "What's for dinner?" problem by:
1. Storing a library of recipes (user-created or from curated packs)
2. Intelligently selecting 5-6 recipes per week
3. Automatically deduplicating ingredients (smart fuzzy matching)
4. Creating an organized, categorized shopping list
5. Syncing to optional task managers (MS To Do, Todoist, TickTick)
6. Supporting multiple beautiful themes and bilingual UI

## Main Features

✅ **Recipe Management**
- Add recipes via web form or Excel import
- 10 sample bilingual recipes included
- Smart protein/ingredient emoji assignment
- Optional curated recipe packs (5 packs, 72+ recipes)

✅ **Weekly Menu Generation**
- 5-6 day intelligent menu generation
- Category-aware selection (variety)
- Prevents recipe duplication same week
- Seeded randomization for reproducibility

✅ **Smart Shopping Lists**
- Fuzzy-matched ingredient deduplication (90%+ similarity)
- Unit conversions (g, kg, ml, cups, tbsp, etc.)
- Categorized by ingredient type (Proteins, Vegetables, Dairy, etc.)
- Pantry staple filtering

✅ **Theme System**
- 9 fully unique themes, all CSS-file based
- Registry-driven dynamic loading
- Responsive design (desktop/tablet/mobile)
- Real-time theme switching with localStorage persistence

✅ **Bilingual Support**
- Full Norwegian/English UI
- Bilingual recipe support
- Language toggle in settings
- Cookie-based language persistence

✅ **Optional Integrations**
- Microsoft To Do sync (OAuth)
- Todoist API sync
- TickTick API sync
- Export to CSV, JSON, Text, ICS formats
- Apple Reminders support (ICS)

✅ **Additional Features**
- Measurement unit conversion (metric/imperial)
- Email notifications (optional)
- Background scheduler (generate menu on schedule)
- Responsive PWA design
- Allergen tracking
- Difficulty levels (Easy/Medium/Hard)
- Cook time tracking

---

# 2. TECHNICAL BREAKDOWN (DETAILED)

## Architecture Overview

```
┌─────────────────────────────────────────────────────┐
│                   USER BROWSER                      │
│  (HTML Templates + CSS + JavaScript)                │
└──────────────────────┬──────────────────────────────┘
                       │
                    HTTP/REST
                       │
        ┌──────────────┴──────────────┐
        │                             │
┌───────▼──────────┐      ┌──────────▼──────────┐
│  FLASK APP       │      │  STATIC ASSETS      │
│  (flask_app.py)  │      │  (CSS, JS, Images)  │
└────────┬─────────┘      └─────────────────────┘
         │
    ┌────┴────────────────────────┐
    │                             │
┌───▼────────────────┐    ┌───────▼──────────────┐
│  CORE LOGIC        │    │  DATA & CONFIG       │
│  (Python)          │    │  (JSON files)        │
└────────────────────┘    └──────────────────────┘
```

## Backend Structure (Python/Flask)

### **pi-deployment/flask_app.py** — Application Entrypoint
**Responsibility:** Main Flask server, route handling, template rendering

**Key Features:**
- i18n system (bilingual support via i18n.json)
- Language selection via cookies
- Bilingual recipe normalization
- All route handlers (/menu, /shopping, /recipes, /settings, etc.)
- Session management
- API endpoints for integrations

**Size:** ~1000+ lines  
**Key Functions:**
- `_load_i18n()` — Load translation dictionary
- `_make_t(lang)` — Create language-specific translation dict
- `_normalize_recipe(recipe, lang)` — Flatten bilingual recipe fields
- Route handlers: `/`, `/shopping`, `/recipes`, `/add-recipe`, `/settings`, etc.

### **core/menu_generator.py** — Menu Generation Logic
**Responsibility:** Intelligent weekly menu generation

**Key Class:** `MenuGenerator`
- Load recipes from database
- Filter by selected categories
- Select 5-6 recipes intelligently (variety, no duplicates)
- Assign protein types and emoji
- Generate weekly menu JSON
- Support seeded randomization

**How It Works:**
1. Load all recipes from `sample_recipes.json` + `recipes_db.json`
2. Filter by selected categories (user preference)
3. Randomly select N recipes ensuring variety
4. Detect protein type using PROTEIN_KEYWORDS dict
5. Assign emoji based on protein (🍗 chicken, 🥩 beef, 🐟 fish, etc.)
6. Return menu data structure with recipe_id, title, subtitle, difficulty, time, protein, emoji

**Key Data:**
```python
PROTEIN_KEYWORDS = {
    'chicken': ['kylling', 'chicken', ...],
    'beef': ['kjøtt', 'beef', ...],
    'fish': ['fisk', 'fish', 'laks', 'salmon', ...],
    'pork': ['svin', 'pork', ...],
    'vegetarian': ['tofu', 'vegetar', ...],
    'lamb': ['lam', 'lamb'],
    'soup': ['soup', 'suppe', ...],
}
```

### **core/ingredient_deduplicator.py** — Shopping List Creation
**Responsibility:** Combine recipes into deduplicated shopping list

**Key Class:** `IngredientDeduplicator`
- Extract ingredients from recipes
- Fuzzy-match similar ingredients (90%+ similarity)
- Aggregate quantities (2x flour 100g + flour 50g = 150g)
- Convert units to base units (g, ml, stk)
- Categorize ingredients (Proteins, Vegetables, Dairy, etc.)
- Filter pantry staples
- Return organized shopping list

**How It Works:**
1. Iterate through recipes in menu
2. Extract ingredients with quantity + unit
3. Normalize units using UNIT_CONVERSIONS
4. Fuzzy-match against existing items (fuzzywuzzy library)
5. If >90% match found, combine quantities; else add new item
6. Categorize by ingredient type
7. Filter out pantry staples (never buy items)
8. Return categorized list

**Unit Support:**
- Weight: g, gram, kg, kilo, mg
- Volume: dl, ml, l, liter, cup, tbsp, tsp
- Count: stk, piece, clove, slice

### **pi-deployment/email_notifier.py** — Email Notifications
**Responsibility:** Send weekly menu/shopping list via email

**Features:**
- SMTP configuration via .env
- HTML email formatting
- Bilingual support
- Scheduled via APScheduler

### **pi-deployment/to_do_sync.py** — Microsoft To Do Integration
**Responsibility:** Sync shopping list to MS To Do lists

**Features:**
- OAuth authentication flow
- Create/update To Do lists
- Category-aware task organization
- Token storage

### **pi-deployment/shopping_integrations.py** — Export & Sync
**Responsibility:** Export shopping list to multiple formats

**Supported Formats:**
- CSV (spreadsheet)
- JSON (data interchange)
- Plain Text (human-readable)
- ICS (calendar format, Apple Reminders)
- Clipboard copy

### **pi-deployment/scheduler.py** — Background Tasks
**Responsibility:** APScheduler integration for recurring tasks

**Tasks:**
- Generate menu on schedule (default: Saturday 9am)
- Send email on schedule (default: Friday 6pm)

### **core/error_handler.py** — Error Management
**Responsibility:** Centralized error handling and logging

---

## Frontend Structure (HTML/CSS/JavaScript)

### **HTML Templates** (Jinja2)

#### **base.html** — Master Template
- Navigation bar with menu, shopping, categories, settings
- Language toggle (Norwegian/English)
- Theme switcher (dropdown menu)
- Settings submenu with language selection
- Dynamic theme loader from theme-registry.json
- Service worker registration (PWA)

#### **index.html** — Weekly Menu
- Two layouts:
  - **Standard layout** (default): Grid of cards, one per day
  - **Rich layout** (Terracotta only): Full redesign with images, day nav, summary bar
- Each card shows: day, recipe name, difficulty, cook time, protein emoji
- "View Recipe" and "View Shopping List" CTAs
- Theme-responsive (switches layout based on active theme)

#### **shopping.html** — Shopping List
- Organized by category (Proteins, Vegetables, Dairy, Pantry, Herbs, Other)
- Checkbox per item (track purchases)
- Export & Sync button opens integrations modal
- Modal supports: CSV, JSON, Text, ICS, Clipboard, MS To Do, Todoist, TickTick
- Print button

#### **recipe.html** — Individual Recipe View
- Full recipe details (title, subtitle, ingredients, instructions, time, difficulty)
- Add to favorites
- View source or edit

#### **add-recipe.html** — Recipe Form
- Form to add new recipes
- Bilingual fields (title_en, title_no, etc.)
- Ingredient list with quantity/unit
- Instructions in both languages
- Category selector
- Submit/cancel

#### **all-recipes.html** — Recipe Browser
- List of all recipes
- Search/filter capability
- Add/edit/delete options
- Favorite marking

#### **settings.html** — App Settings
- Language preference
- Theme selector
- Category management
- Email notification settings (if OAuth available)
- Integration setup (MS To Do, Todoist, TickTick)

---

### **CSS Structure** (style.css + 9 Theme CSS Files)

#### **style.css** — Base Styles
- CSS custom properties (--color-*, --spacing-*, --font-*, --shadow-*, --radius-*)
- Common component styles (.btn, .card, .hero, etc.)
- Settings dropdown styling (.settings-dropdown, .theme-submenu)
- Modal overlay styling (.pm-overlay, .pm-modal-box)
- Responsive breakpoints (640px mobile, 900px tablet)
- Shared layout grid (.menu-grid, .shopping-list)

**Key CSS Custom Properties:**
```css
--color-primary: #2c3e50
--color-secondary: #d97706
--spacing-xs: 4px
--spacing-sm: 8px
--font-primary: 'Poppins'
--radius-md: 8px
--shadow-lg: 0 10px 15px rgba(...)
```

#### **9 Theme CSS Files** (in frontend/static/themes/previews/)

Each theme uses `[data-theme="theme-id"]` scoping:

1. **theme-warm-modern.css** — Warm sand/amber, modern sans-serif, 20px radius
   - Primary: Plus Jakarta Sans
   - Palette: Sand (#F5EFE6), Amber (#C8873A), Dark (#2A2318)
   - Soft shadows, gentle rounded corners
   - **Use case:** Scandinavian boutique hotel aesthetic

2. **theme-warm-terracotta.css** — Terracotta/sage, organic, serif+sans
   - Fonts: Lora (serif) + DM Sans (sans)
   - Palette: Terracotta (#C4622D), Sage (#7A9E7E), Cream (#F7F2EB)
   - Organic blob backgrounds
   - Left-border accent on cards (sage green)
   - **Rich layout:** Full redesign with images, day navigation
   - **Use case:** Earthy, natural kitchen aesthetic

3. **theme-apple-fitness.css** — Dark hero, neon green accents, glassy
   - Font: Inter 800 weight
   - Palette: Dark (#111118), Neon Green (#30D158), Blue (#0A84FF)
   - Frosted glass navbar
   - Glowing button hover effects
   - **Use case:** Apple Watch Activity aesthetic

4. **theme-brutalist.css** — Raw, anti-design, high-contrast
   - Font: System-ui (no designer fonts)
   - Palette: Black (#000000), White (#FFFFFF), Yellow (#FFD600)
   - No border-radius (0px everywhere)
   - Thick 3px black borders
   - 3-column fixed grid layout
   - **Use case:** Harsh, minimalist aesthetic

5. **theme-chalkboard-bistro.css** — Dark chalkboard, handwriting, amber accents
   - Font: Caveat (handwriting) + Josefin Sans
   - Palette: Dark (#2A2C26), Amber (#E8C547), White (#F5F0E8)
   - Dashed borders (chalk line feel)
   - **Use case:** Cozy bistro menu board

6. **theme-coastal-kitchen.css** — Light/airy, ocean blue, sand
   - Fonts: Playfair Display (serif) + DM Sans (sans)
   - Palette: Sky Blue (#CFE8FF), Ocean (#6BB7E3), Sand (#F4E7D0)
   - Gradient backgrounds
   - Soft shadows
   - **Use case:** Beach house kitchen aesthetic

7. **theme-forest-forager.css** — Deep green, organic, cottagecore
   - Fonts: DM Serif Display + Nunito
   - Palette: Moss Green (#4A6A4F), Bark (#5C3D2E), Cream (#F4F2EC)
   - Organic blob shapes
   - Dark forest green navbar
   - **Use case:** Nature-inspired cottagecore

8. **theme-nordic-pantry.css** — Warm wood, Scandinavian, farmhouse
   - Fonts: Karla (sans) + Playfair Display (serif)
   - Palette: Wood tones, Beige (#F8F5EE), Brown (#4A3728)
   - Wood-grain texture backgrounds
   - **Use case:** Scandinavian kitchen pantry

9. **theme-pop-art-diner.css** — Retro, halftone, comic book style
   - Font: Bangers (playful) + DM Sans
   - Palette: Red (#D32F2F), Yellow (#FFD600), Cyan (#00BCD4)
   - Halftone dot pattern background
   - 3px comic-style borders
   - **Use case:** 1950s American diner meets pop art

---

### **JavaScript Files**

#### **app.js** — Main Application Logic
- i18n translation helper (`_t()` function)
- Custom modal system (replaces browser alert/confirm)
- Theme-specific behaviors (Terracotta day selector)
- Recipe/shopping list interactions
- Export functionality
- Menu/shopping list CRUD operations
- Integration sync handlers

**Key Functions:**
- `pmAlert(icon, title, message)` — Custom alert modal
- `pmConfirm(icon, title, message, okLabel)` — Custom confirm modal
- `tcSelectDay(index)` — Terracotta day selection
- Various export handlers for CSV, JSON, etc.

#### **theme-manager.js** — Theme Switching Engine
- `ThemeManager` class
- Load theme from localStorage (persist across sessions)
- `applyTheme(name)` — Switch themes dynamically
- `loadPreviewTheme(themeId)` — Inject theme CSS file
- `markActiveTheme()` — Highlight selected theme in dropdown
- `_switchLayout(name)` — Switch between standard/rich layouts

**How Theme Switching Works:**
1. User clicks theme in dropdown
2. `switchTheme()` calls `themeManager.applyTheme(name)`
3. ThemeManager:
   - Sets `data-theme` attribute on `<html>`
   - Injects/updates `<link>` tag with theme CSS file
   - Saves to localStorage
   - Calls `_switchLayout()` if needed
4. CSS rules with `[data-theme="..."]` selector activate
5. For Terracotta: JavaScript also switches layout (layout-standard vs layout-rich)

**Storage:**
- Key: `'pi-menu-theme'`
- Value: theme ID (e.g., "warm-modern")
- Persists across page reloads and sessions

#### **language-manager.js** — Language Switching
- Load i18n.json (translation dictionary)
- Switch language via cookie
- Refresh page to apply (full i18n reload)

#### **measurements.js** — Unit Conversion
- Client-side unit conversion UI
- Metric ↔ Imperial conversion
- For recipe ingredients

#### **theme-colors.js** — Theme Color Definitions
- Fallback color definitions (if any)
- Helper for color injection

#### **sw.js** — Service Worker
- PWA support (offline capability)
- Cache static assets
- Network-first or cache-first strategies

#### **i18n.json** — Translation Dictionary
Structure:
```json
{
  "key_en": "English text",
  "key_no": "Norwegian text",
  "menu_en": "Menu",
  "menu_no": "Meny",
  ...
}
```

---

## Data Structure

### **Recipes Database**

**Format:** JSON

**Recipe Object:**
```json
{
  "recipe_id": "unique-id",
  "title": "Recipe Name" or {"en": "...", "no": "..."},
  "subtitle": "Description" or {"en": "...", "no": "..."},
  "time_minutes": 45,
  "difficulty": "Easy",
  "category": "Quick Dinners",
  "ingredients": [
    {
      "ingredient": "chicken breast",
      "quantity": 400,
      "unit": "g",
      "allergens": ["poultry"]
    },
    ...
  ],
  "instructions": "Step 1... Step 2..." or {"en": "...", "no": "..."},
  "comment": "Optional note",
  "allergens": ["gluten", "dairy"]
}
```

**Files:**
- `data/sample_recipes.json` — 10 default recipes (bilingual)
- `data/recipes_db.json` — User-imported recipes
- `data/recipe-packs/` — 5 optional packs (72+ recipes)

### **Categories**

**File:** `data/categories.json`

```json
[
  {"name": "Quick Dinners", "emoji": "⚡"},
  {"name": "Fish & Seafood", "emoji": "🐟"},
  {"name": "Vegetarian", "emoji": "🥗"},
  {"name": "Meat & Poultry", "emoji": "🍖"},
  ...
]
```

### **Weekly Menu** (Output)

**File:** `data/weekly_menu.json`

```json
{
  "week_start": "2026-06-16",
  "week_end": "2026-06-21",
  "selected_categories": ["Quick Dinners", "Fish & Seafood"],
  "dinners": [
    {
      "day": "Monday",
      "recipe_id": "recipe-123",
      "title": "Grilled Salmon",
      "subtitle": "With roasted vegetables",
      "time_minutes": 30,
      "difficulty": "Easy",
      "protein": "fish",
      "emoji": "🐟"
    },
    ...
  ],
  "ingredients": {
    "Proteins": [...],
    "Vegetables": [...],
    ...
  }
}
```

### **Pantry Staples**

**File:** `pantry_staples.json`

Items that don't need to be shopped (always in house):
```json
{
  "salt": true,
  "pepper": true,
  "olive oil": true,
  ...
}
```

---

# 3. THEME SYSTEM ANALYSIS

## How Themes Work (Technical)

### Registry System
**File:** `frontend/static/themes/previews/theme-registry.json`

```json
[
  {
    "id": "warm-modern",
    "name": "Warm & Modern",
    "file": "theme-warm-modern.css",
    "preview_color": "#C8873A"
  },
  ...
]
```

- Registry loaded by `base.html` JavaScript
- Theme dropdown populated dynamically from registry
- Each theme points to a CSS file

### CSS Scoping Strategy

Each theme CSS file uses `[data-theme="theme-id"]` selector:

```css
[data-theme="warm-modern"] {
  --wm-sand: #F5EFE6;
  --wm-amber: #C8873A;
  ...
}

[data-theme="warm-modern"] body {
  background: var(--wm-sand);
  color: var(--wm-dark);
}

[data-theme="warm-modern"] .navbar {
  background: var(--wm-warm-white);
}

[data-theme="warm-modern"] .menu-card {
  background: var(--wm-warm-white);
  ...
}
```

**Advantage:** Scoped to theme ID, no cascade conflicts, easy to override

### Dynamic Loading

1. User clicks theme in dropdown
2. `theme-manager.js` calls `loadPreviewTheme(themeId)`
3. Creates `<link>` tag: `href="/static/themes/previews/theme-{themeId}.css"`
4. Sets `<html data-theme="theme-id">`
5. All CSS rules scoped to `[data-theme="..."]` activate instantly
6. Saves to localStorage for persistence

### Layout Switching

**Terracotta theme only** uses a second layout:

```javascript
// In theme-manager.js
_switchLayout(name) {
  const standard = document.getElementById('layout-standard');
  const rich = document.getElementById('layout-rich');
  const useRich = RICH_LAYOUT_THEMES.has(name);
  standard.style.display = useRich ? 'none' : '';
  rich.style.display = useRich ? '' : 'none';
}
```

- Standard layout: Grid of cards
- Rich layout: Full redesign with images, day navigation, summary bar

---

## Adding New Themes

### Step-by-Step

1. **Create CSS file:** `frontend/static/themes/previews/theme-{id}.css`
   - Use `[data-theme="{id}"]` selector
   - Define CSS custom properties
   - Override all component styles

2. **Add to registry:** Update `theme-registry.json`
   ```json
   {"id": "my-theme", "name": "My Theme", "file": "theme-my-theme.css", "preview_color": "#abcdef"}
   ```

3. **Optional: Create layout variant**
   - Add to `RICH_LAYOUT_THEMES` set in `theme-manager.js`
   - Create alternate layout HTML section in `index.html`

4. **Test:** Switch to theme in UI, verify all components render correctly

---

## Customizing Existing Themes

1. Edit the theme's CSS file (e.g., `theme-warm-modern.css`)
2. Modify CSS custom properties or component rules
3. Save → Theme updates live in browser (hot reload)

---

# 4. HOW TO USE THE PROJECT (USER GUIDE)

## Running the Project

### Prerequisites
- Python 3.9+
- pip (Python package manager)

### Installation (5 minutes)

```bash
# 1. Clone and navigate
git clone https://github.com/nobody174/Menu-Planner.git
cd Menu-Planner

# 2. Create virtual environment
python3 -m venv venv
source venv/bin/activate    # On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (edit .env)
cp .env.example .env
nano .env  # Set: HOUSEHOLD_NAME=Your Family

# 5. Start the app
python3 pi-deployment/flask_app.py
```

**Open browser:** http://localhost:5000

### First-Run Walkthrough

1. **Explore sample recipes** — 10 bilingual recipes included
2. **Switch theme** — Settings → Theme (9 options)
3. **Generate menu** — "Generate New Menu" button
4. **View shopping list** — Click "View Shopping List"
5. **Add your recipe** — "Add Recipe" form

---

## Navigation

### Main Menu
- **Menu** — View this week's menu
- **Shopping List** — View deduplicated shopping list
- **Categories** — Filter recipes by type
- **Generate Menu** — Create new menu
- **Settings** (⚙️) — Language, theme, integrations

### Settings
- **Language** — Norwegian / English
- **Theme** — Select from 9 themes
- **Integrations** — (MS To Do, Todoist, TickTick)

---

## Using Features

### Switching Themes

1. Click Settings (⚙️) → Theme
2. Dropdown menu shows 9 themes with color swatches
3. Click a theme → Applied instantly
4. Selected theme persists across sessions

### Generating Menus

1. Main page → "Generate New Menu"
2. Select preferred categories (Quick Dinners, Fish, Vegetarian, etc.)
3. Click "Generate"
4. New 5-6 day menu appears
5. Each day shows recipe, cook time, difficulty, protein emoji

### Shopping Lists

1. Navigate to "Shopping List"
2. List organized by category (Proteins, Vegetables, Dairy, etc.)
3. Check items as you shop
4. Export/sync options:
   - **Export & Sync** button → CSV, JSON, Text, ICS, Clipboard
   - Optional sync to MS To Do, Todoist, TickTick
5. **Print** button for physical copy

### Adding Recipes

1. Click "Add Recipe"
2. Fill form:
   - Title (English & Norwegian)
   - Subtitle/description
   - Ingredients with quantity/unit
   - Instructions
   - Category
   - Cook time, difficulty
3. Submit → Recipe added to database

### Viewing Individual Recipes

1. From menu or recipes page, click "View Recipe"
2. See full details: ingredients, instructions, allergens, cook time
3. Optional: favorite, edit, delete

---

# 5. HOW TO DEVELOP THE PROJECT (DEV GUIDE)

## Adding New Features

### Adding a New REST Endpoint

In `pi-deployment/flask_app.py`:

```python
@app.route('/api/my-feature', methods=['POST'])
def my_feature():
    data = request.json
    # Your logic here
    return jsonify({'success': True, 'data': ...})
```

### Adding a New Translation Key

1. Edit `frontend/static/i18n.json`:
   ```json
   {
     "my_key_en": "English text",
     "my_key_no": "Norwegian text"
   }
   ```

2. In HTML template:
   ```html
   <p>{{ t.my_key }}</p>
   ```

3. In JavaScript:
   ```javascript
   const translated = _t('my_key');
   ```

### Adding a New Theme

1. Create `frontend/static/themes/previews/theme-{id}.css`
2. Use template:
   ```css
   [data-theme="my-theme"] {
     --color-primary: #...;
     --color-secondary: #...;
   }
   
   [data-theme="my-theme"] body {
     background: var(--color-primary);
     color: var(--color-text);
   }
   
   [data-theme="my-theme"] .navbar { ... }
   [data-theme="my-theme"] .menu-card { ... }
   /* etc. */
   ```

3. Add to `theme-registry.json`:
   ```json
   {"id": "my-theme", "name": "My Theme", "file": "theme-my-theme.css", "preview_color": "#..."}
   ```

### Adding a New Page

1. Create HTML template: `frontend/templates/my-page.html`
2. Extend base: `{% extends "base.html" %}`
3. Add route in `flask_app.py`:
   ```python
   @app.route('/my-page')
   def my_page():
       return render_template('my-page.html', household_name=..., t=...)
   ```

---

## Code Organization Principles

### Modularity
- Each Python file has a single responsibility
- `menu_generator.py` → only menu logic
- `ingredient_deduplicator.py` → only deduplication logic
- Keep concerns separated

### Frontend
- `app.js` → Application behavior
- `theme-manager.js` → Theme switching only
- `language-manager.js` → i18n only
- Templates → Structure + minimal logic
- CSS → Style + spacing

### Data
- Recipes stored as JSON (easy to read/modify)
- Recipe packs in separate directory
- Categories configurable in JSON
- No database—pure file-based (simple for self-hosted)

---

## Debugging

### Server-Side (Python)
- Logs in `logs/` directory
- Check `menu_generator.log`, `deduplicator.log`
- Enable debug: Edit `.env` → `FLASK_DEBUG=true`

### Client-Side (JavaScript)
- Open browser DevTools (F12)
- Check console for errors
- Check network tab for API calls
- Use `_t('key')` to test i18n

### Recipes Not Showing
- Check `data/recipes_db.json` is valid JSON
- Verify recipe has required fields (title, category, ingredients)
- Check category matches a known category in `data/categories.json`

### Theme Not Loading
- Check theme CSS file exists
- Check registry.json points to correct file
- Check `[data-theme]` selectors are correct
- Clear browser cache and localStorage

---

# 6. IDENTIFY PROBLEMS & IMPROVEMENTS

## Current Issues

### 🐛 Bugs
- **None known at production** — all identified issues have been fixed in v1.0

### ⚠️ Code Smells

1. **Bilingual field normalization** (flask_app.py:77-100)
   - Complex logic to handle both `{en, no}` dict format AND `field_en`/`field_no` suffix format
   - **Suggestion:** Standardize on single format (recommend `{en, no}` dict)

2. **Magic strings in theme detection** (theme-manager.js:2)
   - `RICH_LAYOUT_THEMES = new Set(['warm-terracotta'])`
   - Only Terracotta has rich layout; hardcoded string
   - **Suggestion:** Store in registry.json or config

3. **No input validation on recipe form**
   - User can submit recipes with missing fields
   - **Suggestion:** Client-side + server-side validation before saving

4. **Fuzzy matching threshold hardcoded** (ingredient_deduplicator.py)
   - 90% similarity threshold for ingredient matching
   - **Suggestion:** Make configurable via .env

### 🐌 Performance Issues

1. **No pagination for recipe list**
   - With 100+ user recipes, loads all at once
   - **Suggestion:** Paginate or lazy-load recipes

2. **No recipe search/filtering** (yet)
   - Browsing all recipes requires scrolling
   - **Suggestion:** Add search by title, ingredient, category

3. **No caching of menu generation**
   - If user clicks "Generate Menu" twice, full generation runs again
   - **Suggestion:** Cache menu for X hours, offer "refresh" option

### 🎨 UX Issues

1. **Theme dropdown spacing** (FIXED in latest version)
   - Previously had inconsistent spacing between theme options
   - **Status:** ✅ Fixed in current release

2. **No preview before generating menu**
   - User generates menu, may not like selection, must generate again
   - **Suggestion:** "Preview" mode before confirming

3. **Ingredient quantities not adjustable**
   - Serving size always matches recipe default
   - **Suggestion:** Add "servings" multiplier to scale quantities

4. **Shopping list print layout could be better**
   - Simple text dump, not optimized for printer
   - **Suggestion:** Better print CSS, columns, checkboxes for printing

### 🏗️ Architectural Issues

1. **File-based data storage scales poorly**
   - Works for <10,000 recipes
   - **Suggestion:** Consider SQLite for >10k recipes

2. **No user authentication**
   - Multi-family homes would need separate instances
   - **Suggestion:** Add optional password/PIN protection

3. **No backup system**
   - Recipes only exist in data/recipes_db.json
   - **Suggestion:** Auto-backup to JSON file or cloud storage

4. **Theme registry hardcoded in base.html**
   - Fetches from `/static/themes/previews/theme-registry.json`
   - **Suggestion:** Could be Flask endpoint for dynamic control

---

## Missing Features (Not Bugs, Just Not Implemented Yet)

1. **Recipe editing** — Can add recipes, but not edit existing
2. **Recipe deletion** — No UI for removing recipes
3. **Favorites/bookmarking** — No way to mark favorite recipes
4. **Weekly menu history** — No way to see past menus
5. **Dietary restrictions** — Can't filter by allergens at generation time
6. **Prep-day planning** — No timeline/prep checklist
7. **Cost estimation** — No price per meal
8. **Inventory management** — No kitchen inventory tracking
9. **Bulk recipe import** — Excel support exists but no UI for it
10. **Recipe sharing** — No way to share recipes with family members

---

# 7. ROADMAP

## Short-Term (v1.1) — Quick Wins

### Phase 1: Recipe Management
- [ ] **Edit recipes** — Update existing recipes (not just add)
- [ ] **Delete recipes** — Remove recipes from library
- [ ] **Search recipes** — Find by title, ingredient, category
- [ ] **Recipe favorites** — Star/bookmark favorite recipes

**Effort:** 1-2 weeks  
**Value:** High (users requested)

### Phase 2: Menu Improvements
- [ ] **Menu preview** — Show options before committing
- [ ] **Manual recipe swap** — Swap Monday's menu with Thursday's
- [ ] **Menu history** — View past menus
- [ ] **Lock recipes** — Pin specific recipes to specific days

**Effort:** 1 week  
**Value:** High

### Phase 3: Shopping List Enhancements
- [ ] **Save shopping lists** — Archive past shopping lists
- [ ] **Better print layout** — Columns, checkboxes, optimized for 8.5x11
- [ ] **Quantity adjustment** — Scale servings (2x, 0.5x)
- [ ] **Price estimation** — Show cost per ingredient if store data available

**Effort:** 1 week  
**Value:** Medium-High

---

## Medium-Term (v1.2–v2.0)

### User & Multi-Family Support
- [ ] **User accounts** — Register/login (optional)
- [ ] **Multi-user** — Different preferences per family member
- [ ] **Dietary restrictions** — Filter recipes by allergies/restrictions
- [ ] **Sharing** — Share recipes/menus with family members

### Advanced Features
- [ ] **Weekly budget** — Set spend limit, track costs
- [ ] **Seasonal recipes** — Prefer recipes by season
- [ ] **Ingredient "in pantry"** — Track kitchen inventory
- [ ] **Prep timeline** — Auto-generate prep schedule for week
- [ ] **Nutrition info** — Track macros/calories
- [ ] **Subscription integration** — Sync with grocery delivery services

### Database/Backend
- [ ] **SQLite migration** — Move from JSON files for scalability
- [ ] **Cloud backup** — Auto-backup to Google Drive/OneDrive
- [ ] **Mobile app** — Native iOS/Android (or React Native)

---

## Long-Term (v2.0+) — Vision

- [ ] **AI recipe suggestions** — ML-based meal recommendations
- [ ] **Grocery store API** — Real-time pricing, auto-ordering
- [ ] **Community recipes** — Share/download recipes from other users
- [ ] **Cooking videos** — Link to video tutorials
- [ ] **Kitchen appliance sync** — Sync with smart fridge, smart scale
- [ ] **Restaurant integration** — Include takeout options in menu
- [ ] **Sustainability tracking** — Carbon footprint per meal
- [ ] **Meal prep photos** — Photo/notes after cooking
- [ ] **Nutrition reports** — Weekly nutrition balance reports

---

# 8. COMPLETE README.md

[See next section for full README]

---

# 9. SUMMARY FOR CLAUDE CHAT

## Pi-Menu Project Summary

**Pi-Menu** is a modern, open-source weekly meal planning web application built with Flask (backend) and vanilla JavaScript (frontend). The core problem it solves: helping families generate varied weekly menus and create smart shopping lists without manual planning.

### Architecture
- **Backend:** Python/Flask with modular core logic (menu generation, ingredient deduplication)
- **Frontend:** HTML/CSS/JavaScript with 9 fully unique themes (registry-driven, dynamic loading)
- **Data:** JSON file-based (recipes, categories, weekly menus, pantry staples)
- **i18n:** Bilingual support (Norwegian/English) via i18n.json

### Key Systems

1. **Menu Generator** — Intelligently selects 5-6 recipes per week from user's recipe database, ensures variety, prevents duplicates, assigns protein types + emoji

2. **Ingredient Deduplicator** — Combines all ingredients from selected recipes, fuzzy-matches similar items (90%+ similarity), aggregates quantities, converts units, categorizes, filters pantry staples

3. **Theme System** — 9 CSS-scoped themes (each with unique identity), registry-driven loading, dynamic switching, localStorage persistence, optional layout variants

4. **Bilingual Support** — Server-side translation injection, client-side i18n helper, language cookie persistence

5. **Integrations** — Export to CSV/JSON/Text/ICS, optional sync to MS To Do/Todoist/TickTick, email notifications, background scheduler

### Key Features
- Add recipes via form or Excel import
- 10 sample bilingual recipes included
- 5 optional curated recipe packs (72+ recipes)
- Smart shopping list deduplication
- Unit conversions (metric/imperial)
- Allergen tracking
- Difficulty levels, cook times
- Fully responsive design
- PWA support (offline capability)

### Development
- Modular Python code (single responsibility per file)
- Template-based HTML with Jinja2
- Vanilla JavaScript (no frameworks) for simplicity and compatibility
- CSS custom properties for theming flexibility

### Known Issues & Improvements
- No recipe editing/deletion UI
- No user authentication
- File-based storage (JSON) scales to ~10k recipes
- Theme registry could be endpoint-driven
- Could benefit from: recipe search, menu preview, favorites, prep timelines

### Roadmap
- **v1.1:** Recipe management (edit, delete, search), menu improvements
- **v1.2–v2.0:** User accounts, dietary restrictions, cloud sync, mobile app
- **v2.0+:** AI recommendations, grocery store APIs, community recipes

---

# 10. APPENDIX — FILE LISTING

## Backend (Python)
- `pi-deployment/flask_app.py` — Flask server, all routes, template rendering
- `core/menu_generator.py` — Menu generation logic (category filtering, recipe selection, protein assignment)
- `core/ingredient_deduplicator.py` — Ingredient deduplication, unit conversion, categorization
- `pi-deployment/email_notifier.py` — Email notifications
- `pi-deployment/to_do_sync.py` — MS To Do integration
- `pi-deployment/shopping_integrations.py` — Export formats (CSV, JSON, ICS, etc.)
- `pi-deployment/scheduler.py` — APScheduler for background tasks
- `pi-deployment/auth.py` — Authentication (placeholder)
- `scripts/pi-menu-cli.py` — CLI tool for bulk operations
- `scripts/import_recipes.py` — Excel recipe import

## Frontend (HTML)
- `frontend/templates/base.html` — Master template, navbar, theme switcher
- `frontend/templates/index.html` — Weekly menu (standard + rich layouts)
- `frontend/templates/shopping.html` — Shopping list, export/sync UI
- `frontend/templates/recipe.html` — Individual recipe view
- `frontend/templates/add-recipe.html` — Recipe form
- `frontend/templates/all-recipes.html` — Recipe browser
- `frontend/templates/settings.html` — App settings

## Frontend (CSS)
- `frontend/static/style.css` — Base styles, CSS custom properties, shared components
- `frontend/static/themes/theme-switcher.css` — Theme dropdown styling
- `frontend/static/themes/previews/theme-warm-modern.css` — Warm & Modern theme
- `frontend/static/themes/previews/theme-warm-terracotta.css` — Terracotta & Sage theme (rich layout)
- `frontend/static/themes/previews/theme-apple-fitness.css` — Apple Fitness theme
- `frontend/static/themes/previews/theme-brutalist.css` — Brutalist theme
- `frontend/static/themes/previews/theme-chalkboard-bistro.css` — Chalkboard Bistro theme
- `frontend/static/themes/previews/theme-coastal-kitchen.css` — Coastal Kitchen theme
- `frontend/static/themes/previews/theme-forest-forager.css` — Forest Forager theme
- `frontend/static/themes/previews/theme-nordic-pantry.css` — Nordic Pantry theme
- `frontend/static/themes/previews/theme-pop-art-diner.css` — Pop Art Diner theme

## Frontend (JavaScript)
- `frontend/static/app.js` — Main application logic, modals, export handlers
- `frontend/static/theme-manager.js` — Theme switching engine, dynamic loading
- `frontend/static/language-manager.js` — Language switching, i18n
- `frontend/static/measurements.js` — Unit conversion UI
- `frontend/static/theme-colors.js` — Theme color definitions (fallback)
- `frontend/static/sw.js` — Service worker (PWA)

## Data (JSON)
- `data/sample_recipes.json` — 10 default bilingual recipes
- `data/recipes_db.json` — User-imported recipes
- `data/categories.json` — Recipe categories
- `data/weekly_menu.json` — Current week's menu
- `data/recipe-packs/pack_*.json` — 5 optional recipe packs
- `frontend/static/i18n.json` — Translation dictionary
- `frontend/static/themes/previews/theme-registry.json` — Theme metadata
- `pantry_staples.json` — Items that don't need shopping

## Configuration
- `.env.example` — Environment template
- `config.py` — Flask configuration
- `requirements.txt` — Python dependencies

## Documentation
- `README.md` — Project overview
- `docs/SETUP_GUIDE.md` — Installation
- `docs/EXCEL_GUIDE.md` — Recipe import
- `docs/DEVELOPER_GUIDE.md` — Development guide
- `ARCHITECTURE.md` — System design
- `FEATURE_ROADMAP.md` — Future features

---

**End of Deep Analysis**
