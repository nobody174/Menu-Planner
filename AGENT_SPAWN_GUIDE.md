# Agent Spawn Guide: Completing 300 Recipes Task

**Purpose:** This document ensures the new chat spawns agents correctly to complete the remaining 163 recipes following the exact same pipeline, legal safeguards, and data structure used in the previous session.

---

## Critical Legal & Quality Requirements

### No Copying (Copyright Protection)
- **NEVER copy text directly from websites, cookbooks, or recipe databases** (e.g., matprat.no, BBC Good Food, AllRecipes)
- **ONLY use general, common-knowledge facts** about each dish (typical ingredients, general cooking method)
- **Write all recipes fresh in your own words** from general culinary knowledge
- This protects Menu-Planner from Terms-of-Service violations and copyright issues
- Document this explicitly in every agent prompt

### Bilingual Completeness
- **Every text field MUST have both Norwegian (no) and English (en)**
- Non-bilingual recipes WILL FAIL validation and block the merge
- Include field-by-field bilingual rules in the agent prompt

---

## Batches to Respawn (163 Missing Recipes)

| Pack | Batch | IDs | Count | Notes |
|------|-------|-----|-------|-------|
| Norwegian | Full 75 (fresh start) | no_031–no_105 | 75 | Previous agent only delivered 9; respawn entire batch |
| Nordic | Batch 2b | nd_069–nd_105 | 38 | Completes pack to 105 total |
| Summer | Batch 2b | sum_069–sum_105 | 38 | Completes pack to 105 total |

**Total to write:** 75 + 38 + 38 = **151 recipes** (note: plan was 300, but only 151 remain after the 149 already written)

---

## Recipe Research Briefs (Use These Exact Dish Lists)

### Norwegian (no_031–no_105, 75 dishes)
1. Sursild 2. Gravlaks 3. Røkt Laks 4. Brunost Smørbrød 5. Leverpostei Smørbrød 6. Skagenrøre Smørbrød 7. Roastbiff Smørbrød 8. Eggerøre Smørbrød 9. Kaviar Smørbrød 10. Pinnekjøttpålegg Smørbrød 11. Multekrem 12. Riskrem 13. Krumkaker 14. Goro 15. Sirupssnipper 16. Serinakaker 17. Fattigmann 18. Sandkaker 19. Berlinerkranser 20. Pepperkaker 21. Julekake 22. Lefse 23. Flatbrød 24. Lompe 25. Skillingsboller 26. Kanelsnurrer 27. Vørterkake 28. Bløtkake 29. Eplekake 30. Trollkrem 31. Rabarbragrøt 32. Sviskegrøt 33. Tykkmelk 34. Surmelk 35. Kesam med Bær 36. Fløtevelling 37. Fårefrikassé 38. Lammelår Stekt 39. Lammestek 40. Svinestek 41. Ribbe 42. Medisterkaker 43. Medisterpølse 44. Fårepølse 45. Spekemat-platte 46. Fenalår 47. Spekeskinke 48. Mølje 49. Bacalao 50. Klippfisk 51. Sei i Form 52. Makrell i Tomat 53. Steinbit i Form 54. Kveite Kokt 55. Rakfisk 56. Gravrøye 57. Krabbe Kokt 58. Kongekrabbe 59. Kamskjell 60. Blåskjell i Hvitvinsuase 61. Sild i Karry 62. Italiensk Salat 63. Potetsalat 64. Råstekte Poteter 65. Potetmos 66. Kokte Poteter 67. Klubb 68. Potetball uten Fyll 69. Stekt Flesk og Løk 70. Saltkjøtt og Suppe 71. Pinnekjøttsuppe 72. Kålrotstuing 73. Surkål 74. Rødkål 75. Lungemos

### Nordic (nd_069–nd_105, 38 dishes)
1. Isbjørnkake 2. Svartpølse 3. Rullepølse 4. Spegepølse 5. Romkugler 6. Troll Krem 7. Piskekrem 8. Boller med Sukker 9. Frøsnapper 10. Rugbrød 11. Kartoffelsuppe 12. Dansk Rugbrød 13. Kokosboller 14. Chokoladeboller 15. Brunsviger 16. Wienerbrød 17. Chokoladekake 18. Mazarin 19. Hindbærsnitter 20. Strawberry Jam Tarts 21. Æbleskiver 22. Pandekager 23. Drømmekiks 24. Vanillekrans 25. Appelsinsnitter 26. Kokosnødder 27. Shortbread Cookies 28. Gløgg 29. Glögg 30. Burnt Cream 31. Rødgrød med Fløde 32. Berry Soup 33. Kartoffel og Blomkål 34. Cauliflower Mash 35. Mushroom Stew 36. Herb Butter Vegetables 37. Root Vegetable Purée 38. Turnip Mash

### Summer (sum_069–sum_105, 38 dishes)
1. Vietnamese Fresh Spring Rolls 2. Thai Green Curry Paste 3. Lemongrass Chicken Grilled 4. Indonesian Satay with Peanut Sauce 5. Malaysian Laksa 6. Singapore Mei Fun 7. Vietnamese Pho Light Broth 8. Thai Mango Sticky Rice 9. Filipino Adobo Summer 10. Vietnamese Bánh Mì Cold 11. Thai Tom Kha Gai 12. Indonesian Gado-Gado 13. Malaysian Rendang Light 14. Vietnamese Cơm Tấm 15. Thai Papaya Salad Variations 16. Indonesian Soto Ayam 17. Vietnamese Rolls with Fish Sauce 18. Thai Basil Chicken 19. Filipino Lumpia 20. Malaysian Popiah 21. Spanish Paella Seafood 22. Spanish Fideuà 23. Portuguese Cataplana 24. Portuguese Sardine Grilled 25. Portuguese Caldo Verde Summer 26. Spanish Pulpo à Feira 27. Italian Risotto ai Funghi 28. Italian Osso Buco Light 29. Italian Tiramisu Summer 30. French Ratatouille Niçoise 31. French Bouillabaisse 32. Greek Gemista 33. Greek Fish Saganaki 34. Middle Eastern Tabbouleh Variations 35. Middle Eastern Hummus Platters 36. Middle Eastern Grilled Halloumi 37. African Peri Peri Chicken 38. African Jollof Rice Summer

---

## Exact Agent Prompt Template

Use this template for each agent spawn. Replace `[PACK]`, `[IDS]`, `[DISHES]` as needed.

```
Write a JSON array of exactly [COUNT] new recipe objects for the "[PACK]" pack, matching this exact schema:

\`\`\`json
{
  "id": "[ID]",
  "title": {"no": "Name", "en": "English Name"},
  "subtitle": {"no": "Norwegian subtitle", "en": "English subtitle"},
  "difficulty": "easy|medium|hard",
  "cookTimeMinutes": 30,
  "servings": 4,
  "category": "Fish|Meat|Other",
  "tags": ["tag1", "tag2"],
  "allergens": [],
  "ingredients": [
    {
      "name": {"no": "Norwegian", "en": "English"},
      "amount": 500,
      "unit": {"no": "gram", "en": "g"}
    }
  ],
  "instructions": {
    "no": ["1. Step one", "2. Step two"],
    "en": ["1. Step one", "2. Step two"]
  }
}
\`\`\`

## CRITICAL RULES

### Bilingual Completeness (REQUIRED)
- **Every text field MUST have both "no" and "en" dictionaries**
- If ANY field is missing bilingual text, validation will FAIL
- This includes: title, subtitle, ingredient names, ingredient units, instructions
- Non-bilingual recipes will block the entire merge operation

### Original Content (LEGAL REQUIREMENT)
- **Write all recipes in your own words from general culinary knowledge**
- **NEVER copy text from websites, cookbooks, or recipe databases**
- Using general facts about a dish (typical ingredients, basic method) is safe
- Copying specific recipes or exact wording is copyright violation
- All 149 previous recipes were written fresh—follow the same approach

### Ingredient Structure (EXACT FORMAT REQUIRED)
- **name:** bilingual {no, en} dictionary
- **amount:** numeric value only (e.g., 500, not "500g")
- **unit:** bilingual {no, en} dictionary (e.g., {"no": "gram", "en": "g"})
- No abbreviations or mixed-language fields

### Instructions (MATCHING STEP COUNT)
- **Instructions MUST have the same number of steps in both languages**
- If Norwegian has 6 steps, English must also have exactly 6 steps
- Steps should be numbered ("1. ", "2. ", etc.)
- Validation checks this; mismatches will fail

### Category (ONLY THREE OPTIONS)
- "Fish" — seafood and fish dishes
- "Meat" — beef, pork, lamb, chicken, poultry
- "Other" — vegetarian, sides, desserts, soups
- Invalid categories will fail validation

### Difficulty (ONLY THREE OPTIONS)
- "easy" — minimal prep, simple technique
- "medium" — moderate prep or technique
- "hard" — complex prep, multiple steps, advanced technique

### Servings (REALISTIC)
- Most dishes: 4 servings
- Whole roasts/large dishes: 6-8 servings
- Be realistic for the dish type

### Use These [COUNT] Dishes IN ORDER

[DISHES LIST HERE]

Output ONLY raw JSON array (no markdown, no commentary). Complete, valid JSON for all [COUNT] recipes.
```

---

## Agent Spawn Commands (Copy-Paste Ready)

### Agent 1: Norwegian Full 75 (no_031–no_105)
```
Subagent: Haiku
Description: Write 75 Norwegian recipes batch (full respawn)
Background: true (run in background)
Prompt: [Use template above with Norwegian dishes list, 75 recipes, IDs no_031–no_105]
```

### Agent 2: Nordic Batch 2b (nd_069–nd_105)
```
Subagent: Haiku
Description: Write Nordic recipes batch 2b (38 recipes)
Background: true
Prompt: [Use template above with Nordic dishes list, 38 recipes, IDs nd_069–nd_105]
```

### Agent 3: Summer Batch 2b (sum_069–sum_105)
```
Subagent: Haiku
Description: Write Summer recipes batch 2b (38 recipes)
Background: true
Prompt: [Use template above with Summer dishes list, 38 recipes, IDs sum_069–sum_105]
```

---

## After Agents Complete: Validation & Merge

### Step 1: Save JSON Outputs
- Collect all 3 agent JSON outputs
- Save to scratchpad:
  - `no_new.json` (Norwegian 75)
  - `nd_batch2b.json` (Nordic 38)
  - `sum_batch2b.json` (Summer 38)

### Step 2: Rename for Merge Script
The merge script expects exact filenames. Before running merge, rename files to:
- `no_new.json` → stays as-is
- `nd_batch2b.json` → rename to `nd_new.json` (script expects this)
- `sum_batch2b.json` → rename to `sum_new.json` (script expects this)

### Step 3: Run Validation Script
```bash
cd C:\Users\Vartd\AppData\Local\Temp\claude\c--Users-Vartd-Desktop-Learning-AI\0e53a463-5a76-4ec0-a21e-3d8a0965aca2\scratchpad
python merge_recipes.py
```

**Expected output:**
```
no_new.json: 75 recipes validated OK, IDs no_031..no_105
nd_new.json: 38 recipes validated OK, IDs nd_069..nd_105
sum_new.json: 38 recipes validated OK, IDs sum_069..sum_105
All packs merged successfully.
```

**If validation fails:** Do NOT proceed. Fix the JSON and re-run validation.

### Step 4: Run Pytest
```bash
cd d:\Claude AI Projects\projects\GitHub\Menu-Planner
pytest tests/ --tb=short
```

**Expected:** 50+ tests pass, no regressions.

### Step 5: User Review
- User spot-checks merged recipes in live packs
- Confirms tone, accuracy, bilingual consistency
- Approves for commit

### Step 6: Commit (LOCAL ONLY, NO PUSH)
```bash
git add data/recipe-packs/
git commit -m "Expand recipe packs: +163 recipes (Norwegian 75, Nordic 38, Summer 38)

Co-Authored-By: Claude Sonnet 4.6 <noreply@anthropic.com>"
```

---

## File Locations (Copy-Paste Ready)

**Scratchpad (temp working directory):**
```
C:\Users\Vartd\AppData\Local\Temp\claude\c--Users-Vartd-Desktop-Learning-AI\0e53a463-5a76-4ec0-a21e-3d8a0965aca2\scratchpad
```

**Merge script:**
```
C:\Users\Vartd\AppData\Local\Temp\claude\c--Users-Vartd-Desktop-Learning-AI\0e53a463-5a76-4ec0-a21e-3d8a0965aca2\scratchpad\merge_recipes.py
```

**Live recipe packs (final destination):**
```
d:\Claude AI Projects\projects\GitHub\Menu-Planner\data\recipe-packs
```

**Project root:**
```
d:\Claude AI Projects\projects\GitHub\Menu-Planner
```

**Tests:**
```
d:\Claude AI Projects\projects\GitHub\Menu-Planner\tests
```

---

## Validation Script Reference (merge_recipes.py)

The script does:
1. Reads new recipe JSON from scratchpad
2. Checks for required fields (id, title, subtitle, difficulty, cookTimeMinutes, servings, category, tags, allergens, ingredients, instructions)
3. Validates bilingual completeness (every text field must have {no, en})
4. Validates instruction step counts match between languages
5. Checks ingredient names and units are bilingual
6. Verifies no duplicate IDs already in pack
7. Validates category is one of: Fish, Meat, Other
8. Validates difficulty is one of: easy, medium, hard
9. Merges into live pack files
10. Updates recipeCount field
11. Writes updated packs back to disk

**Failure stops the process.** Fix the JSON and re-run.

---

## Quality Checklist Before User Review

- [ ] All 151 recipes written (75 Norwegian + 38 Nordic + 38 Summer)
- [ ] All JSON is valid (no syntax errors)
- [ ] Validation script passed without errors
- [ ] All recipes have bilingual {no, en} for every text field
- [ ] Instruction steps match between Norwegian and English
- [ ] All ingredients have bilingual names and units
- [ ] Category is Fish, Meat, or Other (no variations)
- [ ] Difficulty is easy, medium, or hard (no variations)
- [ ] No duplicate IDs in any pack
- [ ] Pytest passes with no regressions (50+ tests)
- [ ] Live pack files updated and recipeCount correct

---

## Legal & Compliance Notes

- **Copyright:** All recipes written from general culinary knowledge, no copying from protected sources
- **Bilingual integrity:** Every recipe readable in both Norwegian and English with identical structure
- **Data consistency:** All recipes follow the exact schema used by the app frontend/backend
- **Editability:** Users can edit recipes in UI; bilingual structure ensures both languages update together
- **Scalability:** recipeCount auto-updated; no hardcoded recipe limits in code

---

## Contact/Questions

If validation fails or pytest breaks, check:
1. Are all text fields bilingual {no, en}?
2. Do instructions have matching step counts?
3. Is every ingredient name and unit bilingual?
4. Are IDs sequential and not duplicated?
5. Is category one of: Fish, Meat, Other?
6. Is difficulty one of: easy, medium, hard?

If stuck, review the merge_recipes.py error message for the exact field/recipe that failed.
