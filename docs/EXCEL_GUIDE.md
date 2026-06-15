# Excel Recipe Template Guide

Complete guide to using the Excel template for adding your recipes to Pi-Menu.

## Template Overview

The Excel template has 4 sheets:

1. **Add Your Recipes** - Where you enter your recipes (main sheet)
2. **Categories** - Reference list of available categories
3. **Units** - Reference list of measurement units
4. **Instructions** - Detailed how-to guide

## Sheet 1: Add Your Recipes

### Required Columns

| Column | Type | Example | Notes |
|--------|------|---------|-------|
| Recipe Name (NO) | Text | Kremete Pasta | Norwegian recipe name (required) |
| Recipe Name (EN) | Text | Creamy Pasta | English recipe name (required) |
| Category | Text | Familie | Must match a category from Sheet 2 |
| Prep Time (min) | Number | 35 | Time in minutes |
| Difficulty | Text | Middels | Easy/Middels/Vanskelig |
| Servings | Number | 4 | Number of servings |
| Allergens | Text | melk, gluten | Comma-separated list |

### Ingredient Columns

For each ingredient row:

| Column | Type | Example |
|--------|------|---------|
| Ingredient Name (NO) | Text | Hakket kjøtt |
| Ingredient Name (EN) | Text | Ground beef |
| Quantity | Number | 500 |
| Unit | Text | g | Must match a unit from Sheet 3 |
| Category | Text | Kjøtt | Type of ingredient |

### Instructions

| Column | Type | Example |
|--------|------|---------|
| Instructions (NO) | Text | 1. Brun kjøttet. 2. Tilsett løk... | Step-by-step numbered instructions |
| Instructions (EN) | Text | 1. Brown meat. 2. Add onion... | English instructions |

## Sheet 2: Categories Reference

Available categories (read-only reference):

- Familie (Family)
- Rask Middag (Quick Dinner)
- Vegetar (Vegetarian)
- Fisk & Sjømat (Fish & Seafood)
- Kjøtt (Meat)
- Annet (Other)

Use these exact values in the Category column.

## Sheet 3: Units Reference

Available measurement units:

| Metric | Imperial | Unit |
|--------|----------|------|
| - | stk | pieces |
| - | fedd | cloves |
| g | - | grams |
| kg | - | kilograms |
| ml | fl oz | milliliters |
| dl | cup | deciliters |
| l | - | liters |
| - | tsp | teaspoons |
| - | tbsp | tablespoons |
| - | cup | cups |

## Sheet 4: Instructions

Detailed guide with examples and best practices.

## Example Recipe

### Grillet Laks med Asparges (Grilled Salmon with Asparagus)

```
Recipe Name (NO): Grillet Laks med Aspargess
Recipe Name (EN): Grilled Salmon with Asparagus
Category: Fisk & Sjømat
Prep Time: 25
Difficulty: Enkel
Servings: 2
Allergens: fisk

Ingredients:
  - Laksefillet / Salmon fillet / 400 / g / Fisk
  - Asparges / Asparagus / 300 / g / Grønnsaker
  - Sitron / Lemon / 1 / stk / Frukter
  - Olivenolje / Olive oil / 30 / ml / Oljer

Instructions (NO):
1. Varm grillen til 200°C
2. Klem sitronjuice over laksen
3. Grill laksen ca 12 minutter
4. Tilsett asparges på grillen
5. Grill til alt er mørt og varmt

Instructions (EN):
1. Heat grill to 200°C
2. Squeeze lemon juice over salmon
3. Grill salmon for about 12 minutes
4. Add asparagus to grill
5. Grill until everything is tender and warm
```

## Validation Rules

✓ **Recipe Name** - Required in both languages
✓ **Category** - Must match Sheet 2 list
✓ **Prep Time** - Positive number only
✓ **Servings** - Positive number only
✓ **Difficulty** - Must be: Enkel / Middels / Vanskelig
✓ **Quantity** - Positive decimal numbers (e.g., 0.5, 1, 500)
✓ **Unit** - Must match Sheet 3 list
✓ **Instructions** - Numbered steps recommended

## Best Practices

### Recipe Names
- Clear and descriptive
- Include main ingredients (e.g., "Grillet Laks med Asparges")
- Avoid special characters except dash and slash

### Ingredient Names
- Use simple names (e.g., "Laks" not "Atlantisk Laks")
- Standardize spelling across recipes
- Use "Hakket kjøtt" not "Kjøttdeig" for consistency

### Instructions
- Number each step (1., 2., 3., ...)
- Keep steps concise and clear
- Include cooking temperatures and times
- Provide both Norwegian and English

### Categories
- Use consistently across recipes
- Add new categories to Sheet 2 first, then use in recipes
- Keep family preferences in mind (if family doesn't like fish, keep minimal fish recipes)

## Troubleshooting

### Recipe not imported
- Check that Category matches Sheet 2 exactly
- Ensure Recipe Name is in both languages
- Verify all Units match Sheet 3

### Units not converting correctly
- Check spelling matches Sheet 3
- Use metric units (g, ml, dl) for automatic conversion
- Imperial units (tsp, tbsp, cup) work but don't convert

### Missing ingredients in shopping list
- Check ingredient names match across recipes (Pi-Menu fuzzy-matches at 90%)
- Spelling variations may prevent matching
- Use standardized ingredient names

## Import via Command Line

```bash
python3 scripts/import_recipes.py my_recipes.xlsx
```

Or import via web interface: Settings → + Legg til oppskrift

## See Also

- [Setup Guide](SETUP_GUIDE.md)
- [Categories Guide](CATEGORIES_GUIDE.md)
- [FAQ](FAQ.md)
