# Pi-Menu: Complete Recipe Scraping & Category Selector UI Task

## Overview
This task involves scraping ALL Hello Fresh recipe categories and implementing a category selector UI for the Pi-Menu project. This work can be done independently without interaction from the main development team.

**Status**: READY FOR INDEPENDENT AGENT EXECUTION
**Estimated Time**: 2-4 hours (mostly waiting for page loads)
**Notification**: Agent should notify when ALL tasks are complete

---

## Current Project State

### What We Have Now
- Pi-Menu project located at: `D:\Claude AI Projects\projects\Pi-Menu`
- **52 recipes** already scraped from 3 main categories:
  - Familie: 22 recipes
  - Populære: 16 recipes
  - Rask Middag: 14 recipes
- These 52 recipes are currently in: `D:\Claude AI Projects\projects\Pi-Menu\data\recipes_db.json`
- Working Hello Fresh scraper at: `D:\Claude AI Projects\projects\Pi-Menu\core\hellofresh_proper_scraper.py`
- Working full-category scraper at: `D:\Claude AI Projects\projects\Pi-Menu\core\scrape_all_categories.py` (needs minor fixes)

### Project Structure
```
D:\Claude AI Projects\projects\Pi-Menu\
├── config.py                          # Project configuration
├── core/
│   ├── menu_generator.py             # Menu generation logic
│   ├── ingredient_deduplicator.py    # Ingredient deduplication
│   ├── hellofresh_proper_scraper.py  # 3-category scraper (WORKING)
│   └── scrape_all_categories.py      # All-categories scraper (NEEDS FIXES)
├── data/
│   ├── recipes_db.json               # Current 52 recipes (WILL MERGE WITH NEW ONES)
│   ├── weekly_menu.json              # Current weekly menu
│   └── menus/                        # [NEW FOLDER - TO CREATE]
│       ├── Populære/
│       │   └── recipes.json
│       ├── Familie/
│       │   └── recipes.json
│       ├── Rask Middag/
│       │   └── recipes.json
│       └── [ALL OTHER CATEGORIES DISCOVERED]/
├── frontend/templates/               # Flask templates
│   ├── base.html
│   ├── index.html
│   ├── shopping.html
│   └── error.html
├── pi-deployment/flask_app.py        # Flask application
└── logs/                             # Log files
```

---

## Task 1: Complete All-Categories Scraping

### Objective
Scrape ALL Hello Fresh recipe categories and save recipes organized by category in `/data/menus/` folder structure.

### Prerequisites
- Playwright library already installed
- Chromium browser already installed
- Python 3.10+ with required dependencies

### Current Issues to Fix
In `scrape_all_categories.py`:
1. ✓ Category name cleanup (newlines handled) - ALREADY FIXED
2. Need to filter out individual recipe links and keep only category pages
3. Need to handle special character filename issues on Windows
4. Need to skip categories with 0 recipes (don't create empty folders)

### Execution Steps

**Step 1: Run the full scraper**
```bash
cd "D:\Claude AI Projects\projects\Pi-Menu"
python core/scrape_all_categories.py
```

**What this will do:**
- Find all Hello Fresh recipe categories (should be ~80-120 unique main categories after filtering)
- For each category, scrape the recipes visible on the first page
- Create folder structure: `data/menus/[category_name]/recipes.json`
- Save recipes in JSON format for each category
- Log progress to: `logs/full_scraper.log`

**Expected Output:**
- Multiple category folders under `data/menus/`
- Each containing `recipes.json` with recipes from that category
- Log file showing which categories were scraped and how many recipes per category

**Time**: ~2-3 hours (depends on number of categories × 3 seconds per category load)

---

## Task 2: Reorganize Existing Recipes

### Objective
Merge the 52 existing recipes from `recipes_db.json` into the new `/data/menus/` structure.

### Execution Steps

**Step 1: Create a migration script**
Create file: `D:\Claude AI Projects\projects\Pi-Menu\migrate_recipes_to_menus.py`

```python
import json
from pathlib import Path

# Load existing recipes from recipes_db.json
recipes_db_path = Path('data/recipes_db.json')
menus_dir = Path('data/menus')

if recipes_db_path.exists():
    with open(recipes_db_path, 'r', encoding='utf-8') as f:
        recipes = json.load(f)
    
    print(f"Migrating {len(recipes)} recipes to menus folder structure...")
    
    # Group recipes by category
    by_category = {}
    for recipe in recipes:
        cat = recipe.get('category', 'Uncategorized')
        if cat not in by_category:
            by_category[cat] = []
        by_category[cat].append(recipe)
    
    # Write to respective folders
    for category, cat_recipes in by_category.items():
        cat_dir = menus_dir / category
        cat_dir.mkdir(parents=True, exist_ok=True)
        
        recipes_file = cat_dir / 'recipes.json'
        
        # Merge with existing if category folder already has recipes
        existing = []
        if recipes_file.exists():
            with open(recipes_file, 'r', encoding='utf-8') as f:
                existing = json.load(f)
        
        # Avoid duplicates by ID
        existing_ids = {r['id'] for r in existing}
        new_recipes = [r for r in cat_recipes if r['id'] not in existing_ids]
        
        merged = existing + new_recipes
        
        with open(recipes_file, 'w', encoding='utf-8') as f:
            json.dump(merged, f, ensure_ascii=False, indent=2)
        
        print(f"  {category}: {len(merged)} total recipes ({len(new_recipes)} new)")
    
    print(f"Migration complete!")
else:
    print("recipes_db.json not found")
```

**Step 2: Run the migration**
```bash
python migrate_recipes_to_menus.py
```

**Expected Output:**
- Organized recipe folders under `data/menus/`
- Each category folder contains `recipes.json` with all recipes for that category
- No duplicate recipes (checked by ID)

---

## Task 3: Update Menu Generator to Read from `/menus/` Structure

### Objective
Modify `core/menu_generator.py` to:
1. Accept a list of selected categories
2. Read recipes from `data/menus/[category]/recipes.json` instead of `recipes_db.json`
3. Generate menus using only recipes from selected categories

### File to Modify
`D:\Claude AI Projects\projects\Pi-Menu\core\menu_generator.py`

### Changes Required

**Modify the constructor:**
```python
def __init__(self, seed: Optional[int] = None, selected_categories: Optional[List[str]] = None):
    self.seed = seed
    self.selected_categories = selected_categories or ['Populære', 'Familie', 'Rask Middag']
    # ... rest of init
```

**Modify load_recipes() method:**
```python
def load_recipes(self) -> bool:
    """Load recipes from selected categories in menus folder"""
    self.recipes_db = []
    menus_dir = Path('data/menus')
    
    if not menus_dir.exists():
        logger.error(f"Menus directory not found: {menus_dir}")
        return False
    
    for category in self.selected_categories:
        category_dir = menus_dir / category
        recipes_file = category_dir / 'recipes.json'
        
        if recipes_file.exists():
            with open(recipes_file, 'r', encoding='utf-8') as f:
                recipes = json.load(f)
                self.recipes_db.extend(recipes)
                logger.info(f"Loaded {len(recipes)} recipes from {category}")
        else:
            logger.warning(f"No recipes found for category: {category}")
    
    logger.info(f"Total recipes loaded: {len(self.recipes_db)}")
    return len(self.recipes_db) > 0
```

**Verify the rest of the code works as-is** (should not need changes - it works with self.recipes_db)

---

## Task 4: Update Flask App to Accept Category Selection

### Objective
Modify Flask app to:
1. Accept selected categories from UI
2. Pass them to menu generator
3. Store selected categories in weekly_menu.json

### File to Modify
`D:\Claude AI Projects\projects\Pi-Menu\pi-deployment\flask_app.py`

### Changes Required

**Modify the /api/regenerate endpoint:**
```python
@app.route('/api/regenerate', methods=['POST'])
def api_regenerate():
    try:
        from core.menu_generator import MenuGenerator
        
        # Get selected categories from request
        data = request.get_json() or {}
        selected_categories = data.get('selected_categories', ['Populære', 'Familie', 'Rask Middag'])
        
        logger.info(f"Generating menu with categories: {selected_categories}")
        
        generator = MenuGenerator(selected_categories=selected_categories)
        menu = generator.run(num_dinners=6, save=True)
        
        # Store which categories were used
        menu['selected_categories'] = selected_categories
        
        logger.info("Menu regenerated via API")
        return jsonify({'status': 'success', 'menu': menu})
    except Exception as e:
        logger.error(f"Menu regeneration failed: {e}")
        return jsonify({'status': 'error', 'message': str(e)}), 500
```

**Add endpoint to get available categories:**
```python
@app.route('/api/categories')
def get_categories():
    """Return list of all available recipe categories"""
    menus_dir = Path('../data/menus')
    categories = []
    
    if menus_dir.exists():
        categories = [d.name for d in menus_dir.iterdir() if d.is_dir()]
    
    logger.info(f"Available categories: {len(categories)}")
    return jsonify({'categories': sorted(categories)})
```

---

## Task 5: Create Category Selector UI Component

### Objective
Add a category selector component to the Flask templates with checkboxes.

### Files to Create/Modify

**Create: `frontend/templates/category_selector.html`** (new partial template)
```html
<div class="category-selector" id="categorySelector">
    <h3>Velg oppskriftskategorier</h3>
    <div class="category-checkboxes" id="categoryCheckboxes">
        <p class="loading">Laster kategorier...</p>
    </div>
    <button class="btn btn-primary" onclick="generateMenuWithCategories()">Generer ny meny med valgte kategorier</button>
</div>

<script>
// Load available categories on page load
document.addEventListener('DOMContentLoaded', function() {
    loadCategories();
});

function loadCategories() {
    fetch('/api/categories')
        .then(response => response.json())
        .then(data => {
            const container = document.getElementById('categoryCheckboxes');
            container.innerHTML = '';
            
            // Default selected categories
            const defaultCategories = ['Populære', 'Familie', 'Rask Middag'];
            
            data.categories.forEach(category => {
                const isChecked = defaultCategories.includes(category);
                const label = document.createElement('label');
                label.className = 'category-checkbox';
                label.innerHTML = `
                    <input type="checkbox" value="${category}" ${isChecked ? 'checked' : ''}>
                    <span>${category}</span>
                `;
                container.appendChild(label);
            });
        })
        .catch(error => {
            console.error('Error loading categories:', error);
            document.getElementById('categoryCheckboxes').innerHTML = '<p class="error">Kunne ikke laste kategorier</p>';
        });
}

function generateMenuWithCategories() {
    const checkboxes = document.querySelectorAll('#categoryCheckboxes input[type="checkbox"]:checked');
    const selectedCategories = Array.from(checkboxes).map(cb => cb.value);
    
    if (selectedCategories.length === 0) {
        alert('Velg minst en kategori');
        return;
    }
    
    console.log('Generating menu with categories:', selectedCategories);
    
    fetch('/api/regenerate', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            selected_categories: selectedCategories
        })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            console.log('Menu generated successfully');
            location.reload(); // Refresh to show new menu
        } else {
            alert('Feil ved generering av meny: ' + data.message);
        }
    })
    .catch(error => {
        console.error('Error:', error);
        alert('Feil ved generering av meny');
    });
}
</script>

<style>
.category-selector {
    background: #f5f5f5;
    padding: 20px;
    border-radius: 8px;
    margin: 20px 0;
}

.category-selector h3 {
    margin-top: 0;
}

.category-checkboxes {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(200px, 1fr));
    gap: 10px;
    margin-bottom: 20px;
}

.category-checkbox {
    display: flex;
    align-items: center;
    cursor: pointer;
}

.category-checkbox input {
    margin-right: 10px;
}

.category-checkbox span {
    user-select: none;
}
</style>
```

**Modify: `frontend/templates/index.html`**
Add the category selector at the top of the content section:
```html
{% extends "base.html" %}

{% block title %}Vartdals Ukesmeny{% endblock %}

{% block content %}
{% include "category_selector.html" %}

<div class="hero">
    <h1>Vartdals Ukesmeny</h1>
    <p class="week-range">{{ menu.week_start }} til {{ menu.week_end }}</p>
    {% if menu.selected_categories %}
    <p class="categories-info">Kategorier: {{ menu.selected_categories | join(', ') }}</p>
    {% endif %}
</div>

<!-- rest of the template remains the same -->
```

---

## Task 6: Add CSS Styling for Category Selector

### File to Modify
`frontend/static/style.css`

### Add to the end of the file:
```css
/* Category Selector Styles */
.categories-info {
    font-size: 0.9em;
    color: #666;
    margin-top: 10px;
}

.category-checkbox {
    padding: 8px 12px;
    background: white;
    border: 1px solid #ddd;
    border-radius: 4px;
    transition: all 0.2s;
}

.category-checkbox:hover {
    background: #f0f0f0;
    border-color: #4CAF50;
}

.category-checkbox input:checked + span {
    font-weight: bold;
    color: #4CAF50;
}
```

---

## Execution Order (IMPORTANT)

1. **Task 1**: Run full scraper → creates `/data/menus/` with all categories
2. **Task 2**: Run migration script → merges existing 52 recipes into new structure
3. **Task 3**: Update menu_generator.py → add selected_categories parameter
4. **Task 4**: Update flask_app.py → add category endpoints and parameters
5. **Task 5**: Create category_selector.html → add UI component
6. **Task 6**: Modify index.html → include category selector
7. **Task 6b**: Update style.css → add styling
8. **Verify**: Test the complete flow:
   - Open http://localhost:5000
   - See category checkboxes
   - Select different categories
   - Click "Generer ny meny med valgte kategorier"
   - Verify menu generates with only selected categories

---

## Testing Checklist

After completing all tasks, verify:
- [ ] `/data/menus/` folder structure exists with all categories
- [ ] Each category folder has `recipes.json`
- [ ] Flask `/api/categories` endpoint returns list of all categories
- [ ] Category selector UI loads checkboxes from API
- [ ] Default categories (Populære, Familie, Rask Middag) are pre-checked
- [ ] Menu generates using only selected categories
- [ ] Generated menu JSON includes `selected_categories` field
- [ ] No duplicate recipes in any category
- [ ] Log files show progress (check `logs/full_scraper.log` and `logs/menu_generator.log`)

---

## Logs to Check

- **Scraping progress**: `logs/full_scraper.log`
- **Menu generation**: `logs/menu_generator.log`
- **Flask requests**: `logs/flask_app.log`

---

## Success Criteria

Task is complete when:
1. ✓ All Hello Fresh categories scraped into `/data/menus/` structure
2. ✓ Menu generator reads from `/menus/` and accepts category selection
3. ✓ Flask API endpoints working (`/api/categories`, `/api/regenerate` with categories)
4. ✓ UI shows category checkboxes on main page
5. ✓ Users can select categories and generate menus from selected categories only
6. ✓ All changes tested and working without errors
7. ✓ Agent notifies main team when complete with summary of work done

---

## Notes for Agent

- Work completely independently - no user interaction needed
- If you encounter errors, log them and continue with other categories
- Some recipes may have incomplete data (that's OK - save what you can get)
- Don't worry about perfect categorization - the system is flexible
- If a category takes too long (>10 seconds), skip it and continue
- The main team will integrate your work into the main branch
- Update logs frequently so progress can be monitored
- Create a summary file: `AGENT_WORK_SUMMARY.md` with what was done when complete

---

## Files You'll Create/Modify

**Create:**
- `migrate_recipes_to_menus.py`
- `frontend/templates/category_selector.html`
- `AGENT_WORK_SUMMARY.md` (when complete)
- Multiple `data/menus/[category]/recipes.json` files

**Modify:**
- `core/menu_generator.py` (add selected_categories support)
- `pi-deployment/flask_app.py` (add category endpoints)
- `frontend/templates/index.html` (include category selector)
- `frontend/static/style.css` (add styling)

---

## Questions or Issues?

If any task is ambiguous or you need clarification:
1. Check the logs for error details
2. Review the existing code structure (it's well-documented)
3. Make reasonable assumptions and document them in your summary
4. Proceed with the task - the main team will review and adjust if needed

Good luck! 🚀
