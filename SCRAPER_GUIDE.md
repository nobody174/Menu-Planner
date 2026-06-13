# HelloFresh Scraper Guide

## Prerequisites

1. **Install dependencies:**
   ```powershell
   pip install -r requirements.txt
   ```

2. **Verify imports work:**
   ```powershell
   python -c "import requests; import bs4; import pillow; print('All dependencies OK')"
   ```

## Running the Scraper

### Basic Usage (100 recipes per category)

```powershell
cd D:\Claude AI Projects\projects\Pi-Menu
python scraper/hellofresh_scraper.py
```

This will:
1. Fetch 100 recipes from "Populære" (Popular)
2. Fetch 100 recipes from "Familie" (Family)
3. Fetch 100 recipes from "Rask Middag" (Quick Dinner)
4. **Total: up to 300 recipes** (fewer if HelloFresh has fewer pages)

**Output:**
- `data/recipes_db.json` - Complete recipe database (~5-10 MB)
- `data/recipes_cache/` - Local HTML + images for each recipe
- `logs/scraper.log` - Detailed scraping log
- `logs/scraper_report.json` - Summary statistics

### Customizing Recipe Count

```python
# In scraper/hellofresh_scraper.py, modify the last line:
if __name__ == '__main__':
    scraper = HelloFreshScraper()
    scraper.run(max_recipes_per_category=50)  # Get 50 per category (150 total)
```

### Rate Limiting

The scraper has built-in delays (2 seconds between requests) to avoid overloading HelloFresh servers.

To adjust:
```python
scraper = HelloFreshScraper(request_delay=1.0)  # 1 second between requests
```

## What Gets Downloaded

For each recipe, the scraper downloads:

```
data/recipes_cache/
└── [recipe-id]/
    ├── metadata.json        (title, ingredients, allergens, etc.)
    ├── index.html          (full recipe HTML)
    ├── step-1.jpg
    ├── step-2.jpg
    └── step-N.jpg
```

**Total disk space:** ~50-100 MB for 300 recipes (mostly images)

## Output Structure

### recipes_db.json
```json
{
  "id": "recipe-unique-id",
  "title": "Stekt laks og gulrot- og perlecouscoussalat",
  "subtitle": "med ristede valnøtter, pære og salatost",
  "category": "Populære",
  "url": "https://www.hellofresh.no/recipes/...",
  "rating": 4.0,
  "rating_count": 268,
  "time_minutes": 25,
  "difficulty": "Enkel",
  "tags": ["RASK"],
  "allergens": ["Gluten", "Hvete", "Nødder"],
  "description": "Recipe description...",
  "ingredients_included": [
    {"quantity": 234, "unit": "g", "name": "Laksefilet", "allergens": ["Fisk"]}
  ],
  "ingredients_not_included": [
    {"quantity": 4, "unit": "dl", "name": "Vann til koking", "allergens": []}
  ],
  "instructions": [
    {
      "step": 1,
      "title": "Kok perlecouscous",
      "description": "Boil until...",
      "image_path": "data/recipes_cache/recipe-id/step-1.jpg"
    }
  ],
  "scraped_at": "2026-06-13T20:00:00"
}
```

### scraper_report.json
```json
{
  "timestamp": "2026-06-13T22:30:00",
  "total_recipes_scraped": 287,
  "total_skipped": 13,
  "total_failed": 2,
  "skipped_recipes": [
    {"id": "recipe-123", "reason": "contains_orange", "title": "Stekt appelsin..."}
  ],
  "failed_recipes": [
    {"url": "https://...", "error": "ConnectionError"}
  ]
}
```

## Orange Filter

The scraper automatically filters recipes containing:
- "appelsin" (Norwegian for orange)
- "oransje" (Norwegian variant)
- "orange" (English)
- "orange juice"
- "orange zest"
- "orange marmelade"

**Allowed citrus:** sitron (lemon), lime, grapefruit

Filtered recipes appear in `scraper_report.json` under `skipped_recipes` with reason `"contains_orange"`.

## Troubleshooting

### No recipes downloaded
- Check internet connection
- HelloFresh may have changed HTML structure (check browser DevTools)
- Look at `logs/scraper.log` for error details

### Images not downloading
- Some images may have permissions issues
- Check `logs/scraper.log` for `"Failed to fetch image"` errors
- Images are JPEG-compressed at quality 85 (acceptable for thumbnails)

### Too slow
- Increase `request_delay` if HelloFresh rate-limits you
- Or decrease it if you're in a hurry (be respectful!)

### Out of memory
- For Raspberry Pi: scrape on Windows PC first, then copy `data/recipes_cache/` to Pi
- Don't run scraper on Pi (1GB RAM limitation)

## Next Steps

1. **Run the scraper:**
   ```powershell
   python scraper/hellofresh_scraper.py
   ```

2. **Verify output:**
   ```powershell
   Test-Path data/recipes_db.json
   (Get-ChildItem data/recipes_cache -Recurse -File).Count  # Should show ~1000+ files
   ```

3. **Generate a menu:**
   ```powershell
   python core/menu_generator.py
   ```
   This creates `data/weekly_menu.json` with 5 dinners + shopping list

4. **Test deduplication:**
   ```powershell
   python core/ingredient_deduplicator.py
   ```

## Performance Expectations

| Recipes | Time | Disk | Network |
|---------|------|------|---------|
| 50      | 5 min | 15 MB | 100 MB |
| 100     | 10 min | 30 MB | 200 MB |
| 300     | 30 min | 100 MB | 600 MB |

Times vary based on internet speed and HelloFresh server response time.

## Respecting HelloFresh

The scraper is designed to:
- ✅ Respect ToS (one-time scrape for personal use)
- ✅ Rate-limit requests (2-second delays)
- ✅ Cache locally (no re-downloading)
- ✅ Not distribute recipes

Use responsibly!

---

**Generated by Claude Code | Never too late to give up! ⚰️**
