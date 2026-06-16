# Pi-Menu Feature Roadmap

This document tracks feature ideas and enhancements for Pi-Menu v1.0 and beyond.

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

**Status:** Ready for discussion with user

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

## Implementation Priority

**High Value / Easy to Implement:**
1. Recipe edit/delete functionality
2. Shopping list checkboxes
3. Menu history
4. PDF export
5. Recipe search

**High Value / Moderate Effort:**
1. Family/household features
2. Multi-user support
3. Recipe backup/restore
4. Analytics dashboard
5. Ingredient-based filtering

**High Value / High Effort:**
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
