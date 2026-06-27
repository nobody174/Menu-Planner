# Phase 1 Testing Guide — Local Setup

**Phase 1 is complete!** You've fixed 3 bugs + added 2 features + Docker support.

This guide shows you how to **test all changes locally** before release.

---

## Quick Start (5 minutes)

### Option 1: Docker (Easiest)

```bash
# Navigate to project
cd d:\Claude AI Projects\projects\GitHub\Menu-Planner

# Start with Docker Compose
docker-compose up -d

# View logs (should see "Running on http://0.0.0.0:5000")
docker-compose logs -f

# Open browser
http://localhost:5000
```

**Stop:**
```bash
docker-compose down
```

---

### Option 2: Local Python (Faster for development)

```bash
# Navigate to project
cd d:\Claude AI Projects\projects\GitHub\Menu-Planner

# Create virtual environment
python -m venv venv

# Activate it
# On Windows:
venv\Scripts\activate
# On Mac/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env from template
copy .env.example .env
# Edit .env: set HOUSEHOLD_NAME=Your Family

# Create data directory if missing
mkdir -p data logs

# Run Flask
python pi-deployment/flask_app.py
```

**Output should show:**
```
 * Running on http://127.0.0.1:5000
```

Open: http://localhost:5000

---

## Testing Checklist

### ✅ Test A0: Pantry Bug Fix

**What changed:** Pantry staples filter now loads from correct JSON keys

**How to test:**

1. Go to: http://localhost:5000/shopping
2. Check the shopping list — common items like "salt", "pepper", "oil" should NOT be on the list
3. Before fix: pantry filter was broken (loading 0 items)
4. After fix: pantry items are correctly filtered out

**Expected result:** Shopping list only shows items you actually need to buy, not pantry staples.

---

### ✅ Test A1: Recipe Edit Endpoint

**What changed:** Users can now edit recipes by ID

**How to test:**

1. Go to: http://localhost:5000/add-recipe
2. Add a test recipe:
   - Title: "Test Recipe"
   - Description: "Test description"
   - Time: 30 min
   - Difficulty: Easy
   - Ingredient: "salt, 1 tsp"
   - Category: "HomeMade"
   - Click "Save Recipe"

3. Go to: http://localhost:5000/all-recipes
4. Find "Test Recipe" in the list, note the recipe ID in the URL

5. **Edit via API** (use Postman, curl, or browser console):

```javascript
// In browser console (F12 → Console tab):
fetch('/api/edit-recipe', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    recipe_id: 'YOUR_RECIPE_ID_HERE',
    title: 'Test Recipe - EDITED',
    description: 'Updated description',
    difficulty: 'Medium',
    time_minutes: 45,
    ingredients: [{ name: 'salt', quantity: 1, unit: 'tsp' }],
    category: 'HomeMade'
  })
})
.then(r => r.json())
.then(d => console.log(d));
```

**Expected result:**
```json
{
  "status": "success",
  "message": "✅ Test Recipe - EDITED updated!",
  "recipe_id": "YOUR_RECIPE_ID_HERE"
}
```

6. Refresh http://localhost:5000/all-recipes — recipe title should be updated

---

### ✅ Test A2: Shopping List Checkboxes

**What changed:** Checkboxes now persist across page reloads using localStorage

**How to test:**

1. Go to: http://localhost:5000 (dashboard)
2. Click "Generer ny meny" (Generate Menu) if no menu exists
3. Click "Handleliste" (Shopping List)

4. **Check off some items:**
   - Click checkboxes next to ingredients
   - Items should appear grayed out + strikethrough

5. **Test persistence:**
   - Refresh the page (F5)
   - Checkmarks should still be there

6. **Test week-based reset:**
   - Open browser console (F12)
   - Run: `localStorage.getItem('shopping-checked-' + new Date().getFullYear() + '-W' + String(new Date().getWeek()).padStart(2, '0'))`
   - You should see the checked items stored as JSON

7. **Next week (if you wait):**
   - Week number changes → localStorage key changes → checkmarks reset automatically

**Expected result:**
- Checkmarks persist across refresh
- Items appear visually checked (grayed out)
- Week-based storage (auto-reset on new week)

---

### ✅ Test A3: Docker Support

**What changed:** App now runs in Docker container

**How to test:**

1. **Build image:**
```bash
docker build -t menu-planner .
```

2. **Start container:**
```bash
docker-compose up -d
```

3. **Check it's running:**
```bash
docker-compose ps
```

Should show:
```
CONTAINER ID   IMAGE              STATUS
xxx            menu-planner:latest   Up X seconds
```

4. **Access app:**
http://localhost:5000

5. **View logs:**
```bash
docker-compose logs -f
```

Should show:
```
[2026-06-27 XX:XX:XX +0000] [X] [INFO] Starting gunicorn X.X.X
[2026-06-27 XX:XX:XX +0000] [X] [INFO] Listening at: http://0.0.0.0:5000
```

6. **Health check:**
```bash
docker-compose ps
```

STATUS should show healthy after ~5 seconds

7. **Stop container:**
```bash
docker-compose down
```

**Expected result:**
- Container starts without errors
- App accessible at http://localhost:5000
- Health checks pass
- Container restarts on failure

---

## Full Feature Test (All 3)

1. Start with Docker: `docker-compose up -d`
2. Add a recipe with pantry items (salt, pepper)
3. Generate a menu
4. Go to shopping list
5. Edit the recipe to remove a non-pantry item
6. Check off items as you shop
7. Refresh — checkmarks persist
8. See that pantry items (salt, pepper) are NOT on list (A0 fix)

---

## Troubleshooting

### "Docker not found"
Install Docker Desktop: https://www.docker.com/products/docker-desktop

### "Port 5000 already in use"
Change in docker-compose.yml:
```yaml
ports:
  - "5001:5000"  # Use 5001 instead
```
Then access: http://localhost:5001

### "ModuleNotFoundError: No module named 'flask'"
You're missing dependencies. Run:
```bash
pip install -r requirements.txt
```

### "No menu generated yet"
Go to http://localhost:5000, click "Generate Menu" button

### Checkboxes not persisting
- Check browser console (F12) for JavaScript errors
- Verify localStorage is enabled
- Try incognito mode (localStorage might be disabled)

---

## Next Steps

After testing:

1. ✅ Commit any fixes needed from testing
2. ✅ Create GitHub release: `v1.1.0`
3. ✅ Push to GitHub: `git push origin main`
4. ✅ Tag release: `git tag v1.1.0 && git push origin v1.1.0`

Then Phase 2: Cloud MVP

---

## Quick Commands

```bash
# Start local server
python pi-deployment/flask_app.py

# Start Docker
docker-compose up -d

# View logs
docker-compose logs -f

# Stop Docker
docker-compose down

# Rebuild Docker image
docker-compose build --no-cache

# Access container shell
docker-compose exec menu-planner bash

# Test endpoint
curl http://localhost:5000/health
```

---

**Ready to test?** Start with Docker or local Python above. 🚀
