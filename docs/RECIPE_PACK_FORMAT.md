# Recipe Pack Format — Developer Cheatsheet

Quick reference for writing new recipe packs or editing existing ones.
All packs live in `data/recipe-packs/` as JSON files.

---

## File Structure

```json
{
  "pack_id": "pack_norwegian",
  "display_name": { "no": "Norske Klassikere", "en": "Norwegian Classics" },
  "icon": "🇳🇴",
  "color": "#EF4444",
  "recipes": [ ... ]
}
```

---

## Recipe Structure

```json
{
  "id": "no_001",
  "title": { "no": "Kjøttkaker", "en": "Norwegian Meatballs" },
  "subtitle": { "no": "Med brun saus og poteter", "en": "With brown gravy and potatoes" },
  "difficulty": "easy",
  "cookTimeMinutes": 45,
  "servings": 4,
  "category": "Ground Meat & Sausages",
  "tags": ["traditional", "norwegian", "cuisine:norwegian"],
  "allergens": ["gluten", "milk"],
  "ingredients": [ ... ],
  "instructions": { "no": [ ... ], "en": [ ... ] }
}
```

---

## Difficulty Values

| Value | Norwegian | English |
|-------|-----------|---------|
| `"easy"` | Enkel | Easy |
| `"medium"` | Middels | Medium |
| `"hard"` | Vanskelig | Hard |

Always lowercase in JSON.

---

## Categories (use exact string)

| Category string | Norwegian name |
|---|---|
| `"Quick Dinners"` | Raske middager |
| `"Pasta & Noodles"` | Pasta og nudler |
| `"Chicken"` | Kylling |
| `"Ground Meat & Sausages"` | Kjøttdeig og pølser |
| `"Fish & Seafood"` | Fisk og sjømat |
| `"Taco & Tex-Mex"` | Taco og Tex-Mex |
| `"Grill"` | Grill |
| `"Soups & Stews"` | Supper og gryteretter |
| `"Vegetarian"` | Vegetar |
| `"Homemade"` | Hjemmelaget |
| `"Salads"` | Salater |
| `"Sides & Light Meals"` | Tilbehør (→ sides-stash, not in menus) |

---

## Common Units

| Unit | Used for |
|------|----------|
| `"g"` | grams — solid ingredients |
| `"kg"` | kilograms — large amounts |
| `"ml"` | milliliters — liquids |
| `"dl"` | deciliters — liquids (Norwegian preference) |
| `"l"` | liters — large liquid amounts |
| `"stk"` / `"pcs"` | pieces (eggs, onions, garlic cloves etc.) |
| `"ss"` / `"tbsp"` | tablespoons |
| `"ts"` / `"tsp"` | teaspoons |
| `"fedd"` / `"cloves"` | garlic cloves |
| `"never"` / `"serving"` | portions / to taste |

Use Norwegian unit in `"no"` key, English in `"en"` key:
```json
"unit": { "no": "ss", "en": "tbsp" }
```

---

## Ingredient Format

```json
{
  "name": { "no": "Kjøttdeig", "en": "Ground beef" },
  "amount": 500,
  "unit": { "no": "gram", "en": "g" }
}
```

---

## Instructions Format

One string per step, numbered:

```json
"instructions": {
  "no": [
    "1. Bland kjøttdeig med egg, løk, salt og pepper.",
    "2. Form til runde kaker.",
    "3. Stek i smør på middels varme, 4-5 min per side."
  ],
  "en": [
    "1. Mix ground beef with egg, onion, salt and pepper.",
    "2. Shape into round patties.",
    "3. Fry in butter on medium heat, 4-5 min per side."
  ]
}
```

---

## Allergens

Use these exact strings (comma list in JSON array):

`"gluten"`, `"milk"`, `"egg"`, `"fish"`, `"shellfish"`, `"nuts"`, `"peanuts"`, `"soy"`, `"sesame"`, `"celery"`, `"mustard"`, `"sulphites"`

---

## ID Convention

| Pack | Prefix | Example |
|------|--------|---------|
| Norwegian | `no_` | `no_001` |
| Nordic/Scandinavian | `nd_` | `nd_012` |
| Summer | `sum_` | `sum_004` |
| Holiday | `hol_` | `hol_037` |
| Italian | `it_` | `it_005` |
| Mexican | `mex_` | `mex_003` |
| New packs | Pick a short prefix | `bbq_001` |

IDs must be **unique across all packs**.

---

## Sides Stash

Recipes that are side dishes (not standalone dinners) go in `data/sides-stash.json` instead of a recipe pack. They won't appear in menu generation.

Examples already there: Potetsalat, Rekesalat, Medisterpølse, Kokte Poteter, Potetmos.

---

## Quick Checklist Before Adding a Recipe

- [ ] Has both `"no"` and `"en"` title
- [ ] `difficulty` is `"easy"`, `"medium"` or `"hard"` (lowercase)
- [ ] `cookTimeMinutes` is realistic (include sides if it's a full meal)
- [ ] `category` matches the exact category string from the table above
- [ ] All ingredients have both NO and EN name
- [ ] Instructions are numbered and cover the full meal (not just the main component)
- [ ] Is this actually a standalone dinner? If not → sides-stash
- [ ] ID is unique and follows prefix convention
