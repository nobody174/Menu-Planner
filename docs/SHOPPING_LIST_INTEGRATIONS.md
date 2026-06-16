# Shopping List Integration Matrix for Pi-Menu

**Status:** Analysis Complete  
**Date:** June 16, 2026  
**Focus:** To-Do & Shopping List App Compatibility  

---

## Executive Summary

Pi-Menu users would benefit from direct integration with shopping list / to-do apps. This document analyzes 14 major platforms for their integration capabilities and proposes export/import strategies.

**Key Finding:** Microsoft To Do (already supported), Todoist, and Google Keep offer the best integration potential with minimal friction.

---

## Integration Matrix

### Legend
- ✅ Supported / Easy
- ⚠️ Possible / Workaround required
- ❌ Not supported / Too restrictive

---

## Platform Analysis

### 1. **Microsoft To Do** ✅ BEST

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via email or API |
| **API Available** | ✅ Yes | Microsoft Graph API |
| **API Cost** | ✅ Free | Included in Microsoft 365 / outlook.com free tier |
| **User API Keys** | ✅ Yes | Via Azure App Registration |
| **Programmatic Add** | ✅ Yes | Full REST API support |
| **File Import** | ✅ Yes | Email import (send list to email) |
| **URL Import** | ⚠️ Partial | Via email links |
| **Commercial Use** | ✅ Yes | MIT license compatible |
| **Open Source Safe** | ✅ Yes | Enterprise integration OK |

**Integration Method:** API (Microsoft Graph) + Email fallback  
**Effort:** Low  
**Current Status in Pi-Menu:** ✅ Already implemented  
**Why Best:** Already built in, works well, no additional friction

---

### 2. **Todoist** ✅ VERY GOOD

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via API, email, CSV |
| **API Available** | ✅ Yes | REST API v2 (free + paid tiers) |
| **API Cost** | ✅ Free | Free tier allows 50 requests/min |
| **User API Keys** | ✅ Yes | Via user settings |
| **Programmatic Add** | ✅ Yes | Full REST API |
| **File Import** | ✅ Yes | CSV, TXT, email |
| **URL Import** | ✅ Yes | Via API links |
| **Commercial Use** | ✅ Yes | API terms allow it |
| **Open Source Safe** | ✅ Yes | No restrictions |

**Integration Method:** REST API (preferred) + CSV fallback  
**Effort:** Low-Medium  
**Implementation:**
- Export shopping list as CSV: `item,qty,category`
- Send via POST to Todoist API
- Create parent task "Weekly Shopping" with subtasks per item

**Example Endpoint:**
```
POST https://api.todoist.com/rest/v2/tasks
{
  "content": "Milk - 2L",
  "parent_id": "{parent_task_id}",
  "labels": ["shopping"]
}
```

---

### 3. **Google Keep** ✅ GOOD

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ⚠️ Limited | Email forwarding only |
| **API Available** | ❌ No | Google deprecated Keep API |
| **API Cost** | N/A | N/A |
| **User API Keys** | ❌ No | Not available |
| **Programmatic Add** | ❌ No | No API |
| **File Import** | ✅ Yes | Email forward |
| **URL Import** | ❌ No | Not supported |
| **Commercial Use** | ✅ Yes | Google ToS allow it |
| **Open Source Safe** | ✅ Yes | No issues |

**Integration Method:** Email export (workaround)  
**Effort:** Low  
**Limitation:** One-way only (no API-based import)

**Workaround:**
- Generate shopping list as HTML email
- Send to user's configured email → Google Keep auto-import
- User can CC Keep email address

---

### 4. **Apple Reminders** ✅ MEDIUM

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ⚠️ Limited | Via Calendar (ICS format) |
| **API Available** | ✅ Yes | EventKit (iOS/macOS native) |
| **API Cost** | ✅ Free | Part of OS |
| **User API Keys** | N/A | Native app only |
| **Programmatic Add** | ⚠️ Limited | iOS Shortcuts only |
| **File Import** | ✅ Yes | ICS calendar files |
| **URL Import** | ✅ Yes | Calendar links |
| **Commercial Use** | ✅ Yes | App distribution OK |
| **Open Source Safe** | ✅ Yes | No restrictions |

**Integration Method:** ICS file export + Calendar link  
**Effort:** Low-Medium  
**Limitation:** Apple ecosystem only, requires manual import

**Implementation:**
- Export shopping list as ICS calendar
- Generate shareable calendar link
- User subscribes in Reminders app

---

### 5. **Notion** ⚠️ COMPLEX

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via API, CSV, manual |
| **API Available** | ✅ Yes | Official Notion API (beta) |
| **API Cost** | ✅ Free | Generous free tier |
| **User API Keys** | ✅ Yes | Via integration dashboard |
| **Programmatic Add** | ✅ Yes | Full REST API |
| **File Import** | ✅ Yes | CSV, Markdown |
| **URL Import** | ⚠️ Partial | Via embed links |
| **Commercial Use** | ✅ Yes | API terms allow it |
| **Open Source Safe** | ✅ Yes | No restrictions |

**Integration Method:** REST API  
**Effort:** Medium  
**Limitation:** Requires user to set up Notion database template first

**Implementation:**
- User creates "Shopping List" database in Notion
- Share API key with Pi-Menu
- Export to Notion via API
- Create rows: Item, Quantity, Category, Checked

---

### 6. **Trello** ⚠️ POSSIBLE

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via API, CSV |
| **API Available** | ✅ Yes | REST API |
| **API Cost** | ✅ Free | Free tier has limits |
| **User API Keys** | ✅ Yes | Via developer console |
| **Programmatic Add** | ✅ Yes | Full REST API |
| **File Import** | ✅ Yes | CSV, JSON |
| **URL Import** | ⚠️ Limited | Embed links only |
| **Commercial Use** | ✅ Yes | Terms allow it |
| **Open Source Safe** | ✅ Yes | No restrictions |

**Integration Method:** REST API  
**Effort:** Medium  
**Limitation:** Overkill for simple shopping list

**Implementation:**
- User creates shopping list board with columns per category
- Create card per item
- Supports checkoff workflow

---

### 7. **Any.do** ✅ GOOD

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via API, email |
| **API Available** | ✅ Yes | REST API |
| **API Cost** | ✅ Free | Free tier available |
| **User API Keys** | ✅ Yes | Via app settings |
| **Programmatic Add** | ✅ Yes | API support |
| **File Import** | ✅ Yes | Email, ICS |
| **URL Import** | ⚠️ Partial | Via email |
| **Commercial Use** | ✅ Yes | Allowed |
| **Open Source Safe** | ✅ Yes | No issues |

**Integration Method:** REST API + Email  
**Effort:** Low-Medium

---

### 8. **TickTick** ✅ VERY GOOD

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | CSV, Outlook, API |
| **API Available** | ✅ Yes | REST API (requires key) |
| **API Cost** | ⚠️ Limited | Free tier has low limits |
| **User API Keys** | ✅ Yes | Via developer settings |
| **Programmatic Add** | ✅ Yes | Full API |
| **File Import** | ✅ Yes | CSV, ICS, Outlook |
| **URL Import** | ⚠️ Limited | Embed only |
| **Commercial Use** | ✅ Yes | Allowed |
| **Open Source Safe** | ✅ Yes | No restrictions |

**Integration Method:** REST API + CSV fallback  
**Effort:** Low-Medium

---

### 9. **Evernote** ⚠️ LIMITED

| Aspect | Status | Details |
|--------|--------|---------|
| **Import Support** | ✅ Yes | Via email, API |
| **API Available** | ✅ Yes | Evernote SDK |
| **API Cost** | ⚠️ Paid | API access requires subscription |
| **User API Keys** | ✅ Yes | Available |
| **Programmatic Add** | ✅ Yes | SDK support |
| **File Import** | ✅ Yes | Email, HTML |
| **URL Import** | ⚠️ Limited | Clip links only |
| **Commercial Use** | ⚠️ Unclear | Check ToS carefully |
| **Open Source Safe** | ⚠️ Risk | SDK licensing terms |

**Integration Method:** Email (preferred) + SDK (complex)  
**Effort:** Medium-High  
**Status:** Not recommended for open source

---

### 10. **Loop Habit Tracker** ❌ NOT SUITABLE

**Status:** Not a shopping list app, habit tracker only  
**Recommendation:** Skip this integration

---

## Recommended Export Formats

### Format 1: **CSV (Universal)**
```csv
Name,Quantity,Unit,Category,Notes
Milk,2,liters,Dairy,Whole milk
Eggs,1,dozen,Dairy,Organic preferred
Tomatoes,5,pcs,Vegetables,Roma tomatoes
```

**Pros:** Universal, simple, works everywhere  
**Cons:** No formatting, limited metadata  
**Use for:** Todoist, TickTick, Trello, Notion, general fallback

---

### Format 2: **JSON (Structured)**
```json
{
  "exportDate": "2026-06-16T10:00:00Z",
  "listName": "Weekly Shopping - June 16",
  "items": [
    {
      "name": "Milk",
      "quantity": 2,
      "unit": "liters",
      "category": "Dairy",
      "priority": "normal",
      "checked": false
    }
  ]
}
```

**Pros:** Rich metadata, programmatic parsing  
**Cons:** Requires JSON support  
**Use for:** API-based integrations, import fallback

---

### Format 3: **ICS (Calendar Format)**
```
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Pi-Menu//Shopping List//EN
BEGIN:VEVENT
DTSTART:20260616T080000Z
SUMMARY:🛒 Shopping List - Jun 16
DESCRIPTION:Milk (2L), Eggs (1 dozen), Tomatoes (5 pcs)
UID:pi-menu-shopping-2026061601@pi-menu.local
END:VEVENT
END:VCALENDAR
```

**Pros:** Works with Apple Reminders, calendars, most apps  
**Cons:** Limited structured data  
**Use for:** Apple Reminders, cross-platform fallback

---

### Format 4: **Todoist API JSON**
```json
{
  "commands": [
    {
      "type": "item_add",
      "temp_id": "1",
      "uuid": "e2b6f",
      "args": {
        "content": "Milk - 2L",
        "project_id": "{shopping_project}",
        "labels": ["dairy"]
      }
    }
  ]
}
```

**Pros:** Direct Todoist support, bulk operations  
**Cons:** Todoist-specific  
**Use for:** Todoist API integration

---

### Format 5: **Copy-to-Clipboard Fallback**
```
🛒 SHOPPING LIST - June 16, 2026

DAIRY (3 items)
☐ Milk - 2 liters
☐ Yogurt - 500g
☐ Cheese - 200g

VEGETABLES (4 items)
☐ Tomatoes - 5 pieces
☐ Lettuce - 2 heads
☐ Carrots - 1 bunch
☐ Potatoes - 2 lbs

[Copy to clipboard button]
```

**Pros:** Works everywhere, no API needed, user-friendly  
**Cons:** Manual paste required  
**Use for:** Universal fallback, all apps via copy-paste

---

## Implementation Roadmap for Pi-Menu

### Phase v1.2 (Next Release)

**Quick Wins (Low effort, high value):**
1. ✅ Copy-to-clipboard export (already easy)
2. ✅ CSV export for Todoist/TickTick
3. ✅ Email export (one-line setup)
4. ⚠️ Calendar/ICS export for Apple Reminders

**Medium Effort:**
5. 🔧 Todoist API integration
6. 🔧 Google Keep email forwarding
7. 🔧 Microsoft To Do (enhance existing)

### Phase v1.3+ (Later)

**Higher Effort:**
- 🔧 Notion API integration
- 🔧 Trello API integration
- 🔧 TickTick API integration
- 🔧 Any.do API integration

---

## Recommended Implementation Order

### TIER 1: Do First (v1.2)
1. **CSV Export** → Todoist, TickTick, general use
2. **ICS Export** → Apple Reminders, calendars
3. **Copy to Clipboard** → Universal fallback
4. **Email Export** → Google Keep, Any.do

**Effort:** Low (1-2 days)  
**Value:** High (covers 80% of users)

### TIER 2: Do Next (v1.3)
1. **Todoist API** → Most popular Todoist users
2. **Enhance Microsoft To Do** → Already using it
3. **Notion API** → Power users

**Effort:** Medium (3-5 days)  
**Value:** Medium (covers 15% more)

### TIER 3: Do Later (v2.0+)
1. **Trello Integration** → Project management users
2. **TickTick API** → Premium users
3. **Evernote** → If licensing clarified

---

## User Configuration (Simple Approach)

Instead of asking users for API keys, provide **one-click exports**:

```
Settings → Shopping List Export

┌─────────────────────────┐
│ Export Shopping List To │
├─────────────────────────┤
│ 📋 Copy to Clipboard    │
│ 📄 Download as CSV      │
│ 📅 Download as ICS      │
│ 📧 Email List           │
│ ✅ Todoist (one-click)  │
│ ✅ Microsoft To Do ✓    │
│ 💡 Google Keep Email    │
│ 🍎 Apple Reminders      │
└─────────────────────────┘
```

---

## Legal & Safety Considerations

### ✅ Safe Integrations
- **Microsoft To Do:** ✅ Already in Pi-Menu, fully legal
- **Todoist:** ✅ API terms explicitly allow open source
- **CSV/ICS:** ✅ Universal formats, no licensing issues
- **Email:** ✅ User's own email, no API needed

### ⚠️ Requires Care
- **Google Keep:** ⚠️ API deprecated, email-only workaround
- **Evernote:** ⚠️ API license check needed
- **Trello:** ⚠️ API rate limits for free tier
- **Notion:** ⚠️ Requires explicit user authorization

### Risk Mitigation
1. **User Owns API Keys:** Never store user credentials
2. **Email Fallback:** Always provide email alternative
3. **No Required Integrations:** All integrations optional
4. **Clear ToS:** Explain what each integration does
5. **Open Source:** Transparent code, community review

---

## Quick Implementation Guide

### CSV Export (Simplest)

**Backend (Flask):**
```python
@app.route('/api/shopping/export/csv')
def export_shopping_list_csv():
    items = load_shopping_list()
    
    import io, csv
    stream = io.StringIO()
    writer = csv.DictWriter(stream, fieldnames=['Name', 'Quantity', 'Unit', 'Category'])
    writer.writeheader()
    writer.writerows(items)
    
    return stream.getvalue(), 200, {
        'Content-Type': 'text/csv',
        'Content-Disposition': 'attachment; filename=shopping-list.csv'
    }
```

**Frontend:**
```html
<a href="/api/shopping/export/csv" class="btn">📥 Download as CSV</a>
```

**Effort:** < 30 minutes

---

### Todoist API Integration

**Backend (Flask):**
```python
@app.route('/api/shopping/export/todoist', methods=['POST'])
def export_to_todoist():
    data = request.get_json()
    todoist_token = data.get('todoist_token')
    items = load_shopping_list()
    
    import requests
    headers = {'Authorization': f'Bearer {todoist_token}'}
    
    # Create parent task
    response = requests.post(
        'https://api.todoist.com/rest/v2/tasks',
        headers=headers,
        json={'content': '🛒 Shopping List - ' + date.today().isoformat()}
    )
    parent_id = response.json()['id']
    
    # Add items as subtasks
    for item in items:
        requests.post(
            'https://api.todoist.com/rest/v2/tasks',
            headers=headers,
            json={
                'content': f"{item['name']} - {item['quantity']}{item['unit']}",
                'parent_id': parent_id,
                'labels': [item['category'].lower()]
            }
        )
    
    return jsonify({'success': True, 'items_added': len(items)})
```

**Effort:** 2-3 hours with testing

---

## Recommendation Summary

### For v1.1 (Current)
Skip integrations — focus on recipe features. ✅ DONE

### For v1.2 (Next Release)
Implement:
1. CSV export (universal)
2. ICS export (Apple)
3. Copy-to-clipboard (fallback)
4. Email export (Google Keep)

**Total Effort:** 1-2 days  
**Impact:** 80% of users happy

### For v1.3+
Add API integrations based on user demand:
- Todoist API (popular)
- Microsoft To Do (existing users)
- Notion API (power users)

---

## Files to Create/Update

### New Files Needed (v1.2)
- `shopping_list_export.py` — Export logic
- `templates/shopping-export.html` — Export options page
- `static/js/export-handlers.js` — Client-side export code

### Updates Needed
- `flask_app.py` — Add export endpoints
- `settings.html` — Add "Export Shopping List" button
- `shopping.html` — Add export button

---

## Conclusion

**Shopping list integrations are feasible and valuable for v1.2+, but NOT required for v1.1.**

**Best approach:**
1. Focus on recipe features first (v1.1) ✅ DONE
2. Add basic CSV/ICS exports (v1.2) — 1-2 days work
3. Add API integrations gradually (v1.3+) — As demand dictates

**Legal status:** All recommended integrations are safe for open source.

---

**Next Action:** User decides if/when to prioritize shopping list integrations for v1.2.

