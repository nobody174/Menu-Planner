# Menu Planner – Advanced User Guide

This guide is for power users who want to understand how the system works under the hood and get the most out of every feature.

---

## How the System Works

### Data Architecture

Each household has its own isolated data space stored in PostgreSQL (JSONB columns on the Household record):

| Column | What it stores |
|---|---|
| `recipes_db` | All household recipes (imported + manually added) |
| `categories` | Category list with codes, names, icons |
| `weekly_menu` | Current week's generated menu |
| `pantry` | List of pantry item strings |
| `activity_log` | Timestamped audit trail (capped at 200 entries) |
| `removed_categories` | Tombstone list of deleted category codes |
| `imported_packs` | Metadata for imported recipe packs |

Everything is **per-household** — two households never see each other's data.

---

## How Categories Work

### Category Codes vs Names

Every category has a **code** (internal ID, never changes) and a **name** (what you see, can be renamed). For example:

```
code: "chicken"
name_en: "Chicken"
name_no: "Kylling"
```

This means you can rename "Chicken" to "Chicken Dinners" without breaking any recipes — the code stays the same.

### The Self-Heal System

The app has a self-heal mechanism for categories. When you load your categories, it checks the **base seed file** and automatically adds any new categories that were added to the system after your household was created.

**But it never:**
- Overwrites a category you've renamed
- Re-adds a category you've explicitly deleted
- Changes the order you've set

Deleted categories are tracked in `removed_categories` — a tombstone list. If you delete "Grill" and the base seed has "Grill", it won't come back.

### Imported Pack Categories

When you import a recipe pack, any pack-specific category is marked `"imported": true`. These show at the **bottom** of the category list and are excluded from the main Manage Categories view to reduce clutter. They're still fully functional for menu generation.

---

## How Recipe Packs Work

### What a Pack Contains

A recipe pack is a JSON file with a list of recipes, all pre-formatted with bilingual titles, ingredients, instructions, categories, allergens and difficulty levels.

### Import Flow

1. You click **Import Pack**
2. The app reads the pack JSON file from the server
3. All recipes are added to your household's `recipes_db` JSONB column
4. Pack metadata (name, icon, colour) is saved to `imported_packs`
5. Any new categories in the pack are added to your `categories` list (tagged `imported: true`)

### Re-importing a Pack

If you re-import a pack you already have, the app checks recipe IDs. Existing recipes are **not duplicated**. New recipes in the pack (added since you last imported) are added.

### Removing a Pack

Go to **All Recipes** → **Manage Packs** → Remove. This:
1. Deletes all recipes from that pack from your `recipes_db`
2. Removes the pack metadata from `imported_packs`
3. Removes any pack-specific categories (if empty)
4. Moves any recipes you manually moved to other categories to **Uncategorized** (they're yours now, not the pack's)

---

## How Menu Generation Works

### The Algorithm

When you click **Generate**:

1. **Load recipes**: Loads your `recipes_db` + the shared `sample_recipes.json` base file
2. **Filter by category**: Keeps only recipes in your selected categories
3. **Deduplicate**: Checks recently used recipe IDs (stored in previous menus) and deprioritises recently served recipes
4. **Protein balance**: The generator tries to balance protein types across the week (not 6 chicken dinners in a row)
5. **Pick 6**: Randomly selects 6 recipes from the filtered, balanced pool
6. **Save**: Writes the menu to your household's `weekly_menu` JSONB column

### Favourites in Menu Generation

If you select the **Favourites** category:
- Favourite recipe IDs are read from your browser's `localStorage`
- Only those recipes are eligible for selection
- If you select Favourites + other categories, the pool is the union of both

### Why You Sometimes Get Fewer Than 6

If a category has fewer than 6 recipes and it's the only one selected, you'll get fewer dinners. The app returns a 400 error if the selected categories have **zero** recipes total (not even 1 to pick from).

---

## How the Pantry Works

### Bilingual Pairing

Pantry items are stored as lowercase strings. The app has a built-in **translation table** (`pantry_staples.json`) mapping English ↔ Norwegian for ~100 common staples.

When you add "lemon":
- "lemon" is stored
- "sitron" is also stored automatically (the Norwegian pair)

When you view the pantry in Norwegian, only Norwegian items show. In English, only English items show. Items that are identical in both languages (e.g. "salt") always show.

When you remove "lemon", "sitron" is also removed.

### Pantry and Shopping List

The shopping list is generated from the weekly menu's ingredients. Each ingredient is compared against your pantry (case-insensitive, lowercased). Matches are greyed out but still shown — you decide whether to buy more or use what you have.

---

## Activity Log

The activity log records every significant action in the household:

- Who added/edited/deleted a recipe
- Who generated or regenerated the menu
- Who added/removed pantry items
- Who changed categories

It shows the **profile name** (or email if no profile active), the action, and a timestamp. Capped at 200 entries — oldest entries drop off automatically.

Only the **household owner** can see the activity log (under Settings).

---

## Advanced Workflows

### Setting Up a New Household from Scratch

1. Import 2-3 recipe packs that match your family's taste
2. Add 5-10 of your own family recipes manually
3. Set up categories (rename defaults to match what you actually cook)
4. Update your pantry — remove things you never have, add things you always have
5. Generate your first menu with all categories selected
6. Regenerate until you get a week you're happy with

### Managing a Large Recipe Collection

- Use **categories** as filters, not just labels. If "Chicken" has 40 recipes, the generator has great variety. If it has 3, you'll see repeats quickly.
- Use **Merge into...** to consolidate near-duplicate categories (e.g. "Pasta" and "Pasta & Noodles")
- The generator deduplicates across recent menus, so a large pool means longer before repeats

### Getting Consistent Variety

The menu generator uses random selection within the filtered pool. For best variety:
- Have at least 10+ recipes per selected category
- Select 4-6 categories when generating (not just 1-2)
- Let the deduplication work — don't regenerate too many times in a row (it resets the pool)

### Multi-Household Setup

If you manage multiple households (e.g. home + cabin):
- Each household is completely separate
- Switch between them via the profile picker / household selector
- Recipes, menus and pantry are never shared between households

---

## Tips for Power Users

- **Category codes are permanent**: Renaming is safe. Deleting and re-adding creates a new code — any recipes that were in the old category need to be re-categorised.
- **Sample recipes are shared**: The base `sample_recipes.json` file is visible to all households. Your `recipes_db` contains only your household's own recipes on top of those.
- **Pack recipes stay even if you uninstall the pack app-side**: Once imported, recipes live in your household's database. Removing a pack is a deliberate action, not automatic.
- **The shopping list is per-menu**: It reflects the **current** weekly menu only. If you regenerate, the shopping list updates.
- **Pantry reset is non-destructive to your customisations... except it replaces everything**: Use it only to restore the default list. Your custom items will be gone after a reset.

---

*For technical/developer documentation see DEVELOPER_GUIDE.md and SYSTEM_ARCHITECTURE.md.*
