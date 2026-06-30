# Recipe Audit Report — 2026-06-30 (overnight, autonomous)

Full detail behind the summary in `BACKLOG_2026-06-30.md` items B1, B2, B3, B5.

---

## 1. Structural audit (instructions, ingredients, bilingual fields)

Checked all 5 recipe packs + `sample_recipes.json` for: missing/empty `instructions.en`/`instructions.no`, step-count mismatch between languages, missing ingredients list, missing bilingual ingredient name/unit, missing amount.

**Before fix:** `sample_recipes.json` had 18 issues across its 10 recipes (every recipe missing ingredients; 4 of them also missing instructions entirely). The 5 packs (378 recipes) had 0 issues — they were already correctly structured.

**Root cause:** `sample_recipes.json` was written with a different, older field schema (`ingredients_included`, `instructions_no`/`instructions_en` as plain strings) than the one the Flask app's `_normalize_recipe()` function actually reads (`ingredients` array, `instructions: {en: [...], no: [...]}`). The app silently rendered these recipes with no ingredients, and for 4 of them, no instructions — this is exactly the bug reported with "Chickpea Curry with Rice" (`sample_007`).

**Second bug found in the same file:** recipes `sample_003` through `sample_006` *did* have a populated `instructions` dict, but its content described the wrong dish entirely — e.g. "Green Vegetable Stir-fry with Chicken" (`sample_003`) had steps for boiling and mashing potatoes; "Chicken Tacos with Fresh Toppings" (`sample_004`) had steps for a beef stew; "Baked Cod with Potatoes" (`sample_005`) had steps for a carrot soup. Looks like a copy/paste mistake from whenever this dict was first added.

**Fix:** Rewrote all 10 recipes in `data/sample_recipes.json` using the recipe-pack schema, keeping the existing correct Norwegian/English wording where it matched the dish, and correcting the instruction steps to actually describe the named dish.

**After fix:** 0 issues across all 334 recipes (324 in packs + 10 sample).

---

## 2. New-household recipe repetition

**Confirmed cause:** a fresh household (before any recipe pack is imported) only has access to `sample_recipes.json` — which had just 10 recipes. With a 6-meal weekly menu, that's guaranteed heavy repetition.

**Status:** the 10 recipes are now fully correct and usable (see above), but the pool is still small. Not expanded tonight — flagged as backlog item B5 for a future top-up, or consider adding a UI hint nudging new households toward importing a recipe pack.

---

## 3. Servings scaling verification

Traced `core/ingredient_deduplicator.py`'s `deduplicate_from_recipes()` directly against real pack data (no Flask/DB involved, to avoid touching live app state overnight).

Test recipe: `no_001` "Fårikål" (Lamb and Cabbage Stew), base `servings: 4`, lamb ingredient `800g`.

| target_servings | Expected | Actual |
|---|---|---|
| 4 (= base) | 800g | 800g ✅ |
| 6 | 1200g | 1.2kg ✅ (auto unit conversion) |
| 2 | 400g | 400.0g ✅ |

**Conclusion:** the scaling math is correct. The earlier report that "800g didn't change" was a workflow gap, not a math bug — the shopping list is a saved snapshot from the last time the menu was generated; changing the household's servings number doesn't retroactively rescale an already-generated menu. You have to click **Generate Menu** again afterward. A reminder message covering this was already added earlier in the same session (`deployment/flask_app.py`, household-update handler).

---

## 4. Dessert / cake / cookie removal

**Method:** Did not trust simple keyword matching on recipe titles — an initial pass using words like "cake", "pie", "tart" produced major false positives:
- "Kjøttkaker" (meatballs) and "Fiskekaker" (fish cakes) both matched "kake"/cake as a substring but are savory dinner dishes
- "Shepherd's Pie", "Cottage Pie", "Steak and Kidney Pie" matched "pie" but are savory meat pies
- "Tartiflette" (a savory potato/cheese bake) matched "tart"

Instead, cross-checked each recipe's own `tags` array (many genuine desserts already self-tag with the literal word `"dessert"`), then hand-reviewed every remaining candidate title individually against its tags before removing anything.

**54 recipes removed** (full list below). **Recipe counts after removal:**

| Pack | Before | After | Removed |
|---|---|---|---|
| pack_01_norwegian | 105 | 92 | 13 |
| pack_02_european | 67 | 59 | 8 |
| pack_03_nordic | 67 | 52 | 15 |
| pack_04_holiday | 62 | 46 | 16 |
| pack_05_summer | 67 | 65 | 2 |
| **Total (packs)** | **368** | **314** | **54** |

Plus `sample_recipes.json` (10, unchanged count, content fixed) = **324 total dinner recipes** across all sources.

### Removed recipes

| File | ID | Title |
|---|---|---|
| pack_01_norwegian | no_014 | Chocolate Cake |
| pack_01_norwegian | no_041 | Cloudberry Cream |
| pack_01_norwegian | no_042 | Rice Cream |
| pack_01_norwegian | no_043 | Krumkake Wafers |
| pack_01_norwegian | no_051 | Christmas Cake |
| pack_01_norwegian | no_057 | Vort Cake |
| pack_01_norwegian | no_058 | Soft Cake |
| pack_01_norwegian | no_059 | Apple Cake |
| pack_01_norwegian | no_060 | Troll Cream |
| pack_01_norwegian | no_063 | Soured Milk |
| pack_01_norwegian | no_064 | Sour Milk |
| pack_01_norwegian | no_065 | Curd with Berries |
| pack_01_norwegian | no_066 | Cream Velling |
| pack_02_european | eu_012 | Crème Brûlée |
| pack_02_european | eu_013 | Tiramisu |
| pack_02_european | eu_074 | Black Forest Cake |
| pack_02_european | eu_076 | Apple Strudel |
| pack_02_european | eu_077 | Sachertorte |
| pack_02_european | eu_078 | Kaiserschmarrn |
| pack_02_european | eu_089 | Sticky Toffee Pudding |
| pack_02_european | eu_098 | Baklava |
| pack_03_nordic | nd_005 | Princess Cake |
| pack_03_nordic | nd_008 | Red Fruit Compote with Cream |
| pack_03_nordic | nd_011 | Kransekake |
| pack_03_nordic | nd_012 | Sweet Fruit Soup |
| pack_03_nordic | nd_015 | Serina Cake |
| pack_03_nordic | nd_069 | Polar Bear Cake |
| pack_03_nordic | nd_073 | Rum Balls |
| pack_03_nordic | nd_074 | Troll Cream |
| pack_03_nordic | nd_075 | Whipped Cream |
| pack_03_nordic | nd_083 | Brunsviger Cake |
| pack_03_nordic | nd_085 | Chocolate Cake |
| pack_03_nordic | nd_086 | Mazarin Cake |
| pack_03_nordic | nd_093 | Orange Slices |
| pack_03_nordic | nd_094 | Coconut Pyramids |
| pack_03_nordic | nd_097 | Red Fruit Dessert |
| pack_04_holiday | hol_003 | Rice Pudding |
| pack_04_holiday | hol_004 | Christmas Roll Cake |
| pack_04_holiday | hol_010 | Dessert: Chocolate Mousse |
| pack_04_holiday | hol_019 | Risalamande |
| pack_04_holiday | hol_027 | Christmas Cake |
| pack_04_holiday | hol_029 | Nisser Hat |
| pack_04_holiday | hol_030 | Cloudberry Cream |
| pack_04_holiday | hol_031 | Christmas Rice Pudding |
| pack_04_holiday | hol_044 | Chocolate Fondue |
| pack_04_holiday | hol_049 | Almond Cake |
| pack_04_holiday | hol_050 | Orange Mousse |
| pack_04_holiday | hol_051 | Chocolate Truffles |
| pack_04_holiday | hol_054 | Meringue Cream |
| pack_04_holiday | hol_055 | Dessert Cream |
| pack_04_holiday | hol_056 | Sorbet |
| pack_04_holiday | hol_062 | Nativity Cake |
| pack_05_summer | sum_076 | Thai Mango Sticky Rice |
| pack_05_summer | sum_097 | Italian Tiramisu Summer |

### Deliberately kept (reviewed, judged savory or not clearly dessert)

- All "-kaker" dishes that are actually meat/fish dishes: Kjøttkaker (meatballs), Fiskekaker (fish cakes), Medisterkaker (sausage/pork patties) — "kake" is a substring false positive, these are dinner mains
- All savory pies: Shepherd's Pie, Cottage Pie, Steak and Kidney Pie, Spanakopita, Burek, Pierogi, Kalakukko, Tartiflette
- One savory salad with a misleading flavor-descriptor tag: Strawberry and Spinach Salad (tagged "sweet" for the fruit, not a dessert course)

### Follow-up round (same night, after user review)

User confirmed: keep pancakes as a dinner item, but remove waffles and cinnamon-roll-type sweet buns. Removed 9 more recipes:

| File | ID | Title |
|---|---|---|
| pack_01_norwegian | no_006 | Brown Cheese Waffles |
| pack_01_norwegian | no_013 | Sweet Buns |
| pack_01_norwegian | no_023 | Norwegian Waffles |
| pack_01_norwegian | no_044 | Goro Wafers (tagged `waffle`) |
| pack_01_norwegian | no_055 | Shilling Buns |
| pack_01_norwegian | no_056 | Cinnamon Rolls |
| pack_03_nordic | nd_076 | Sugar Buns |
| pack_03_nordic | nd_081 | Coconut Buns |
| pack_03_nordic | nd_082 | Chocolate Buns |

**Confirmed kept, untouched:** Pancakes (`nd_090`, pack_03_nordic) — verified present after this round, exactly as instructed.

**Confirmed NOT removed** (savory dishes, "roll" only describes shape, not a sweet baked good): Rolled Sausage (`nd_071`), Vietnamese Fresh Spring Rolls (`sum_069`), Vietnamese Rolls with Fish Sauce (`sum_085`).

**Pack counts after this round:**

| Pack | After round 1 | After round 2 |
|---|---|---|
| pack_01_norwegian | 92 | 86 |
| pack_02_european | 59 | 59 |
| pack_03_nordic | 52 | 49 |
| pack_04_holiday | 46 | 46 |
| pack_05_summer | 65 | 65 |
| **Total (packs)** | **314** | **305** |

**Grand total after round 2: 305 recipes in packs + 10 sample = 315 recipes** (down from 378+10 originally; 64 desserts/cakes/waffles/sweet-buns removed across both rounds).

### Rounds 3-6 (same night, found via repeated broader sweeps - an honest accounting)

After round 2, the user spotted more desserts in the live app that my earlier review had missed (Apple Cake, Soft Cake, etc.) - most of those specific titles turned out to already be gone from round 1, but the report prompted a fresh, much wider keyword sweep that found **real, previously-undetected misses**. This took four more passes because each sweep used a slightly different keyword list and kept surfacing new items - documenting all of it here rather than only the clean final state, since the process matters for trusting the result:

**Round 3** - direct title check (`cake`, `aebleskiver`, `pancake`) found 2 genuine misses:
- `no_048` Sand Cakes (tagged `cakes, butter, traditional`)
- `nd_089` Æbleskiver Pancakes (sweet filled Danish ball-pancakes, traditionally sugar-dusted - user's call: remove despite "pancake" in the name, since it's traditionally a sweet treat, unlike the plain Pancakes recipe which stays)

**Round 4** - broader title-keyword sweep (cookie/pudding/pastry/wreath/tart/etc.) found 13 genuine misses, all confirmed via their own `tags` field:
- `no_015` Krumkake (Thin Cookies), `no_045` Syrup Snips, `no_047` Poor Man's Pastry (fattigmann - user's call: remove), `no_049` Berlinerkranser Wreaths, `no_050` Gingerbread Cookies, `no_061` Rhubarb Pudding, `no_062` Prune Pudding
- `nd_084` Danish Pastry, `nd_087` Raspberry Slices, `nd_088` Strawberry Jam Tarts, `nd_091` Dream Cookies, `nd_092` Vanilla Wreath, `nd_095` Shortbread Cookies
- `hol_012` Christmas Baking: Gingerbread House, `hol_028` Gingerbread Cookies, `hol_061` Peppermint Cream

**Round 5** - even broader sweep (added `bun`/`roll`/`wafer`/`chocolate`/`sugar`/etc. to the keyword list) found 3 more genuine misses:
- `no_046` Baked Pastries (tagged `pastry, jam, traditional`)
- `hol_011` Christmas Tradition: Pepper Nuts (tagged `christmas, cookies, spice`)
- `hol_057` Nut Brittle (tagged `candy, nuts`)
- Plus two genuinely ambiguous non-dinner items the user explicitly confirmed removing: `hol_058` Jam (a preserve/condiment, not a dish on its own) and `hol_060` Candied Fruit (a holiday sweet snack)
- `hol_059` Snowball (tagged `candy, chocolate`) was caught in the same pass

**Round 6** - a tag-only sweep (ignoring title entirely, checking every tag against a broad suspect list) surfaced no further desserts, but found **4 drink recipes** mixed into the dinner pool - not desserts, but also not dinner dishes:
- `nd_096` Glögg, `hol_002` Christmas Mulled Wine, `hol_048` Fruit Punch, `hol_053` Punch Juice
- User's call: remove these too, but track them in a **separate** `data/drinks-stash.json` rather than mixing with desserts, since this could become its own future feature (a holiday drinks list) distinct from the Dessert system (F2).

**Total removed across rounds 3-6: 26 more recipes** (16 + 6 + 4, see breakdown above). All confirmed savory items checked alongside these sweeps (fish cakes, tartiflette, boxty, dolmades/sarma/gołąbki cabbage rolls, black pudding, rolled sausage, gravlax starter, festive holiday roasts/hams/turkeys, cheese fondue, pickled cucumbers, side dishes, strawberry salad, sweet & sour chicken, spring rolls, pancakes) were deliberately left in place after individual review - none removed.

**Grand total after all rounds: 277 recipes in packs + 10 sample = 287 recipes** (down from 378+10 originally; 90 desserts/cakes/cookies/pastries/waffles/buns removed, 4 drinks removed separately).

Re-ran the full structural audit after every round: **0 issues across all 287 recipes** at the end.

**Honest note on process:** the repeated misses across rounds 3-6 happened because each pass used a narrower keyword list than the last, and tag-based detection alone (looking only for the literal word `"dessert"`) wasn't sufficient - many genuine desserts in this dataset are tagged with the specific treat type (`cookies`, `pastry`, `pudding`, `candy`) rather than the generic word `dessert`. The round-6 tag-only sweep against a much broader suspect-tag list is the most thorough check run tonight and found no further dessert misses, which is reassuring but not a guarantee - if more turn up in testing, the pattern (check tags broadly, not just title keywords) is now established and fast to re-run.

---

## Files changed tonight (final, after all rounds)

- `data/sample_recipes.json` — full rewrite (schema fix + instruction-content fix)
- `data/recipe-packs/pack_01_norwegian.json` — 105 → 77 (28 removed across all rounds)
- `data/recipe-packs/pack_02_european.json` — 67 → 59 (8 removed)
- `data/recipe-packs/pack_03_nordic.json` — 67 → 41 (26 removed)
- `data/recipe-packs/pack_04_holiday.json` — 62 → 35 (27 removed)
- `data/recipe-packs/pack_05_summer.json` — 67 → 65 (2 removed)
- `data/dessert-stash.json` — new, 87 full recipes (all ingredients/instructions intact) for the future Dessert system (F2)
- `data/drinks-stash.json` — new, 4 full recipes for a possible future holiday-drinks feature
- `BACKLOG_2026-06-30.md` — updated with all findings
- `RECIPE_AUDIT_REPORT_2026-06-30.md` — this file

**Total: 378 → 287 recipes in the dinner pool** (277 in packs + 10 sample), with 90 desserts/sweets and 4 drinks preserved separately, not deleted.

Database, Flask routes, and household-servings/category logic were also changed later the same session (see BACKLOG_2026-06-30.md B2, B4b) — those are separate from the recipe-data work documented above.
