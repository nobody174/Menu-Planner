# Menu Planner Feature Roadmap

This document tracks feature ideas and enhancements for Menu Planner v1.0 and beyond.

## How to Use This Document

- **v1.0 Current** - Features in the current release
- **v1.1 Planned** - Next planned update (discuss with user)
- **v2.0+ Future** - Long-term ideas for major versions
- **💡 Community Ideas** - Ideas to explore further

---

## v1.0 Current Features ✅

### Core Functionality
- [x] Recipe management (add via form)
- [x] Weekly menu generation
- [x] Shopping list with deduplication
- [x] Bilingual support (NO/EN)
- [x] Category system
- [x] Theme support (9 themes)
- [x] Responsive design
- [x] Sample recipes (10 bilingual)

### Optional Features
- [x] Microsoft To Do sync
- [x] Email notifications
- [x] Background scheduler
- [x] Measurement conversion (metric/imperial)

---

## v1.1 Planned / Proposed ⏳

**Status:** Active development

### 🍽️ Recipe Discovery & Preloaded Content (NEW)

#### 1. Free Recipe Sources Library
**Description:** Curated list of free recipe sources for users to discover
**Priority:** Quick Win - Documentation only
**Deliverable:** `FREE_RECIPE_SOURCES.md`
- [x] Norwegian free recipe sites (with linking permission notes)
- [x] English free recipe sites (with linking permission notes)
- [x] Attribution and usage guidelines
- [x] How to manually import recipes

**Why:** Users need legitimate sources to expand their recipe collection

---

#### 2. Preloaded Recipe Packs System
**Description:** Optional, curated recipe collections users can import with one click
**Priority:** Medium - Requires UI + JSON data
**Components:**
- [ ] UI "Import Recipe Packs" button in settings
- [ ] Pack selection modal with descriptions
- [ ] One-click import functionality
- [ ] Pack management (view imported packs, remove if needed)

**Why:** New users get immediate recipe library to explore

---

#### 3. Curated Recipe Packs (Data)
**Priority:** Medium-High - Data creation but straightforward
**Packs to create (15 recipes each, bilingual NO/EN):**

**Pack 1: Popular Norwegian Recipes**
- Traditional Norwegian favorites
- Family-friendly classics
- 15 recipes with full bilingual support
- Examples: Fårikål, Raspeball, Kjøttkaker, etc.

**Pack 2: European Classics**
- Italian, French, Spanish favorites
- International comfort food
- 15 recipes
- Examples: Pasta, Risotto, Bouillabaisse, etc.

**Pack 3: Nordic Classics**
- Nordic regional specialties
- Scandinavian heritage recipes
- 15 recipes
- Examples: Swedish Meatballs, Danish pastries, etc.

**Pack 4: Holiday Recipes**
- Christmas & festive meals
- Easter special dishes
- 10-12 recipes
- Bilingual with seasonal notes

**Pack 5: Summer Recipes**
- **Fresh Salads** (5 recipes)
- **Grill Recipes** (5 recipes)
- **Seafood** - Shrimp, crab, fish (5 recipes)
- Light, seasonal focus

**Each recipe includes:**
- Title (NO/EN)
- Subtitle (NO/EN)
- Ingredients with quantities & units
- Step-by-step instructions (NO/EN)
- Category mapping
- Tags (seasonal, difficulty, cook time)
- Allergen information
- Bilingual complete support

**Why:** Removes "blank slate" problem for new users

---

#### 4. Personal Recipe Arsenal Management
**Description:** Users can organize, import, and export their own recipe collections
**Priority:** Medium-High - Core functionality with UI
**Features:**
- [ ] Export personal recipes as JSON pack
- [ ] Import custom recipe packs (JSON format)
- [ ] Create named personal collections
- [ ] Share collections with family
- [ ] Backup/restore collections
- [ ] Recipe pack templates (for sharing)

**Why:** Enable power users and community sharing

---

### User-Requested Features

#### 1. Recipe Import Enhancements
**Description:** Better recipe bulk import options
**Ideas:**
- [ ] CSV import support
- [ ] JSON import for recipe backup/restore
- [ ] Duplicate detection (avoid adding same recipe twice)
- [ ] Recipe update/edit functionality (currently add-only)

**Why:** Users may want to migrate recipes from other meal planning apps

---

#### 2. Recipe Management Features
**Description:** Better control over personal recipes
**Ideas:**
- [ ] Edit existing recipes
- [ ] Delete recipes
- [ ] Recipe search/filtering
- [ ] Favorite/star recipes
- [ ] Recipe tags (custom, beyond categories)
- [ ] Nutrition info (calories, protein, carbs)
- [ ] Allergen tracking (currently basic)
- [ ] Prep time vs. cooking time separation

**Why:** Users need flexibility to manage their recipe collection

---

#### 3. Menu Management
**Description:** More control over generated menus
**Ideas:**
- [ ] Lock specific recipes to specific days
- [ ] Swap recipes between days with one click
- [ ] View menu before confirming
- [ ] Menu history (past menus)
- [ ] Save multiple menu variants
- [ ] Menu comparison

**Why:** Users may want specific meals on specific nights

---

#### 4. Shopping List Enhancements
**Description:** Better shopping list functionality
**Ideas:**
- [ ] Check off items as purchased
- [ ] Save shopping list history
- [ ] Export to PDF/print format
- [ ] Share shopping list (with family)
- [ ] Price estimation (if store data available)
- [ ] Quantity adjust per serving

**Why:** Shopping lists are the primary output users interact with

---

#### 5. Family/Household Features
**Description:** Multi-user support within household
**Ideas:**
- [ ] Multiple family members with preferences
- [ ] Dietary restrictions per person
- [ ] Favorite tracking per person
- [ ] Shared shopping list with notifications
- [ ] Permission levels (admin, viewer, editor)

**Why:** Families have different tastes and dietary needs

---

#### 6. Smart Generation Features
**Description:** AI-like menu generation improvements
**Ideas:**
- [ ] Avoid repeating ingredients in same week
- [ ] Leftovers tracking (use day 2's recipe day 3)
- [ ] Seasonal recipe preference
- [ ] Ingredient-based filtering (in pantry vs. need to buy)
- [ ] "Use up" feature (recipes using specific ingredients)
- [ ] Macro-balanced weeks (protein, carbs, fats)

**Why:** Better menu variety and ingredient efficiency

---

#### 7. Integration Features
**Description:** Connect with external services
**Ideas:**
- [ ] Grocery store integration (Coop, Meny, etc.)
- [ ] Price lookup per store
- [ ] Auto-ordering from store
- [ ] Fitbit/Apple Health integration
- [ ] Google Calendar sync (for meal prep days)
- [ ] Slack/email reminders (what's for dinner?)

**Why:** Automate the end-to-end meal planning workflow

---

#### 8. Data & Backup Features
**Description:** Data management and safety
**Ideas:**
- [ ] Export all recipes as JSON
- [ ] Export menu as PDF/image
- [ ] Data backup to cloud (Google Drive, OneDrive)
- [ ] Restore from backup
- [ ] Sync across devices

**Why:** Users shouldn't lose their recipe collection

---

#### 9. Analytics & Insights
**Description:** Track patterns and provide insights
**Ideas:**
- [ ] Most cooked recipes
- [ ] Favorite categories
- [ ] Cooking time trends
- [ ] Cost per meal tracking
- [ ] Dietary balance reports
- [ ] Waste reduction (repeat purchases)

**Why:** Help users understand their eating patterns

---

#### 10. Mobile App
**Description:** Native mobile application
**Ideas:**
- [ ] iOS app
- [ ] Android app
- [ ] Offline recipe browsing
- [ ] Quick recipe add from mobile
- [ ] Push notifications for meals

**Why:** Mobile access is convenient for shopping/cooking

---

#### 11. Recipe Source Features
**Description:** Easier recipe discovery
**Ideas:**
- [ ] Recipe sharing between users
- [ ] Recipe marketplace/library
- [ ] Recipe suggestions based on ingredients
- [ ] Link to original recipe source
- [ ] Cooking videos/tutorials
- [ ] User ratings and reviews

**Why:** Users spend time finding recipes; make it easier

---

#### 12. Accessibility Features
**Description:** Better support for different abilities
**Ideas:**
- [ ] Larger text size option
- [ ] High contrast mode
- [ ] Screen reader optimization
- [ ] Voice input for recipe adding
- [ ] Voice output for recipes while cooking

**Why:** Inclusive design benefits everyone

---

## v2.0+ Long-Term Vision 🚀

### Major Features
- [ ] Machine learning for personalized recommendations
- [ ] Community recipe sharing (optional/private)
- [ ] Recipe OCR (photograph of recipe → digital)
- [ ] Cooking technique guides
- [ ] Kitchen inventory management
- [ ] Smart fridge integration
- [ ] Dietary restriction AI matching
- [ ] Meal prep planning & steps
- [ ] Cost optimization
- [ ] Sustainability tracking (carbon footprint)

---

## v1.1 Implementation Priority

### Phase 1: Quick Wins (Week 1-2)
**Free Recipe Sources Library** ⚡
1. Research & document Norwegian free recipe sources
2. Research & document English free recipe sources
3. Create `FREE_RECIPE_SOURCES.md`
4. **Deliverable:** Complete documentation
5. **Effort:** 1-2 days

### Phase 2: Foundation (Week 2-3)
**Preloaded Recipe Packs - Data Creation** 📦
1. Create 75+ bilingual recipes (5 packs)
2. Structure: JSON format with schema
3. Ensure bilingual complete coverage (NO/EN)
4. Allergen & tag standardization
5. **Deliverable:** `data/recipe-packs/` with all packs
6. **Effort:** 3-4 days (parallel work possible)

### Phase 3: UI Implementation (Week 3-4)
**Recipe Pack Import System** 🎛️
1. Add "Import Recipe Packs" button to settings
2. Create pack selection modal
3. Show pack preview (name, description, recipe count)
4. Implement one-click import
5. Add "Manage Imported Packs" interface
6. **Deliverable:** Full UI integration
7. **Effort:** 2-3 days

### Phase 4: Advanced Features (Week 4-5)
**Personal Recipe Arsenal** 📚
1. Export personal recipes as JSON
2. Import custom recipe packs
3. Named collections management
4. Backup/restore functionality
5. **Deliverable:** Full export/import system
6. **Effort:** 2-3 days

---

## Overall v1.1 Priority (All Features)

**Quick Wins (Week 1):**
1. Free Recipe Sources documentation
2. Recipe edit/delete functionality
3. Shopping list checkboxes
4. Recipe search

**High Value / Moderate Effort (Weeks 2-3):**
1. Preloaded recipe packs (data + UI)
2. Personal recipe arsenal
3. Menu history
4. PDF export

**Medium Value / Lower Priority (Weeks 3+):**
1. Family/household features
2. Multi-user support
3. Recipe backup/restore
4. Analytics dashboard
5. Ingredient-based filtering

**High Value / High Effort (v2.0):**
1. Mobile app
2. Cloud sync
3. Grocery store integration
4. ML recommendations
5. Community features

---

## Technical Debt / Improvements

### Code Quality
- [ ] Add integration tests
- [ ] Improve error messages
- [ ] Add data validation
- [ ] Performance optimization for 1000+ recipes
- [ ] Database migration (if > file-based system)

### Infrastructure
- [ ] Docker support
- [ ] Cloud deployment guide
- [ ] Database (SQLite or similar) for scalability
- [ ] API rate limiting

### Documentation
- [ ] Video tutorials
- [ ] Interactive walkthrough
- [ ] Troubleshooting guide expansions
- [ ] API documentation (for extensions)

---

## Community Ideas

**Placeholder for user-submitted ideas**

---

## Decision Framework

When considering new features, ask:
1. **Core Mission:** Does it help with weekly meal planning?
2. **Complexity:** How much code/maintenance?
3. **User Value:** How many users benefit?
4. **Dependencies:** Does it block other features?
5. **Maintenance:** Is it simple to maintain long-term?

---

## How to Request a Feature

1. Open an issue on GitHub
2. Describe the problem you're solving
3. Suggest a solution
4. Add to this roadmap
5. Discuss with community

---

**Last Updated:** June 16, 2026  
**Status:** Open for discussion and contributions  
