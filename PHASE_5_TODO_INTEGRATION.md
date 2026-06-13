#
# Pi-Menu Phase 5: Microsoft To Do Integration
# Author:  nobody174 (nobodylearn174@gmail.com)
# Repo:    https://github.com/nobody174/Pi-Menu
# License: All rights reserved © 2025 nobody174
#

# Phase 5: Microsoft To Do Integration

## Overview

Sync your Pi-Menu shopping list to Microsoft To Do app on your phone. Check items off as you shop, and the app will show completion status.

## Features Implemented

✅ **Manual Sync Button** - "Send Handleliste til telefon" button on shopping list page
✅ **Selective Sync** - Checkboxes next to each item; only checked items are sent
✅ **Smart Emojis** - Automatically adds relevant emojis based on ingredient type
✅ **Quantity Formatting** - Shows quantity in proper format (200ml, 500g, 2L, 3 stk, etc.)
✅ **Two-way Ready** - Structure in place for syncing back checked items
✅ **Secure Secrets** - Uses `.env` file for Azure credentials (never committed to git)

## Setup Instructions

### Step 1: Fill in Your Azure Credentials

Open `.env` file and add your Azure Client Secret:

```env
AZURE_CLIENT_SECRET=your_secret_here
AZURE_CLIENT_ID=6a554392-f3fb-4e8e-b85c-4970711ea412
AZURE_TENANT_ID=d450370d-b4f6-4ee6-916c-1d3c2091d1a3
```

**⚠️ IMPORTANT:** 
- Never commit `.env` file to git (it's in `.gitignore`)
- Keep your secret safe
- `.env.example` shows the template

### Step 2: Verify Azure Permissions

Make sure your Azure app has these permissions:
- `Tasks.ReadWrite` - Read and write To Do tasks
- `Offline_access` - Access when you're not signed in

### Step 3: Test the Connection

Run the test script to verify everything works:

```bash
python core/todo_sync.py
```

You should see:
- "Successfully authenticated with Microsoft Graph"
- "Found shopping list: [list-id]"
- "Found meal plan list: [list-id]"

## How to Use

### Sending Items to Your Phone

1. **Go to Shopping List** - Click "Se handleliste" on the dashboard
2. **Check Items** - Select checkboxes next to items you want to buy
3. **Send to Phone** - Click "Send Handleliste til telefon 📱" button
4. **Confirm** - You'll see "Handleliste sendt til telefon! 📱"
5. **Open Microsoft To Do** - Check the "Handleliste" list on your phone
6. **Shop** - Check off items as you buy them in the store

### Smart Emoji Feature

Ingredients automatically get relevant emojis:
- 🥛 Melk, Yoghurt, Fløte (Dairy)
- 🐟 Laks, Fisk, Torsk (Fish)
- 🥩 Kjøtt, Kjøttdeig, Bacon (Meat)
- 🍗 Kylling (Chicken)
- 🥕 Gulrot, Salat (Vegetables)
- 🍅 Tomat, Paprika (Tomatoes)
- 🧅 Løk, Hvitløk (Onions)
- 🥔 Poteter, Søtpotet (Potatoes)
- 📝 Unknown items (default)

### Quantity Display

Items show with proper units:
- `Melk - 2L` (liters)
- `Kjøttdeig - 800g` (grams)
- `Stk Agurk - 3` (pieces)
- `Brød - 1` (quantity)

## Architecture

### Core Module: `core/todo_sync.py`

**Classes:**

1. **MicrosoftGraphAuth** - Handles OAuth2 authentication with Azure
   - Gets access token from Azure
   - Manages token lifecycle

2. **ToDoSync** - Main sync engine
   - Authenticates with Graph API
   - Gets or creates To Do lists
   - Syncs shopping list items
   - Handles two-way sync ready

### API Endpoint: `/api/sync-shopping-list`

**Request:**
```json
{
  "items": [
    {"ingredient": "Melk", "quantity": "2", "unit": "L"},
    {"ingredient": "Kjøttdeig", "quantity": "800", "unit": "g"}
  ],
  "shopping_list": { "full shopping list data" }
}
```

**Response:**
```json
{
  "status": "success",
  "message": "Sendt 15 elementer til telefon"
}
```

### Frontend: Shopping List UI

**New Components:**
- Checkboxes next to each item (`item-checkbox`)
- "Send Handleliste til telefon" button
- Loading state during sync
- Success/error messages

## Configuration

### To Do List Names

Edit in `config.py`:
```python
TO_DO_LIST_NAME = "Ukemeny"           # Meal plan list
SHOPPING_LIST_NAME = "Handleliste"    # Shopping list
```

### Emoji Mapping

Add or modify in `core/todo_sync.py`:
```python
INGREDIENT_EMOJIS = {
    'melk': '🥛',
    'laks': '🐟',
    # ... more mappings
}
```

## Future Enhancements

### Phase 5.1: Two-Way Sync
- [ ] "Sync with phone" button to fetch completed items
- [ ] Mark items as checked if completed in To Do app
- [ ] Show completion status in UI

### Phase 5.2: Meal Plan to Do
- [ ] Create daily meal tasks in "Ukemeny" list
- [ ] Format: "Mandag: Stekt laks (25 min)"
- [ ] Link to recipes from tasks

### Phase 5.3: Smart Sync
- [ ] Automatic sync on menu generation
- [ ] Sync interval settings
- [ ] Sync history and logs

### Phase 5.4: Multiple Users
- [ ] Support multiple To Do accounts
- [ ] Share lists between family members
- [ ] User-specific preferences

## Troubleshooting

### "AZURE_CLIENT_SECRET not set"
**Solution:** Fill in your secret in `.env` file

```env
AZURE_CLIENT_SECRET=your_actual_secret_here
```

### "Failed to authenticate with Microsoft Graph"
**Check:**
1. Is `.env` file in the right location? (project root)
2. Is the secret correct?
3. Are Azure app permissions set?
4. Is client ID correct?

### "List not found"
**Solution:** First sync will create the lists automatically:
1. Run `python core/todo_sync.py` once
2. Check your Microsoft To Do app for "Handleliste" list
3. Try again

### Items not showing in To Do app
**Check:**
1. Did you click "Send Handleliste til telefon"?
2. Are items checked in the UI?
3. Refresh the To Do app on your phone
4. Check the correct list name is "Handleliste"

## Security Notes

✅ **Secrets are safe:**
- `.env` file is in `.gitignore` (never committed)
- Secret only stored locally
- Uses OAuth2 (secure token flow)
- No credentials in logs

⚠️ **For Raspberry Pi deployment:**
- Set environment variables instead of `.env` file
- Or use `.env.local` on Pi
- Never commit secrets to Git

## Testing

Run the test to verify everything works:

```bash
python core/todo_sync.py
```

Expected output:
```
Successfully authenticated with Microsoft Graph
Found shopping list: abc-123
Found meal plan list: def-456
Synced 5 items to To Do
Sync test successful!
```

## Logs

Sync logs are saved to: `logs/todo_sync.log`

View recent logs:
```bash
tail -50 logs/todo_sync.log
```

## Files Modified/Created

**Created:**
- `core/todo_sync.py` - Main sync module
- `.env` - Local secrets (NOT committed)
- `.env.example` - Template for .env
- `.gitignore` - Git ignore rules
- `PHASE_5_TODO_INTEGRATION.md` - This file

**Modified:**
- `frontend/templates/shopping.html` - Added checkboxes and sync button
- `frontend/static/style.css` - Added shopping actions styling
- `pi-deployment/flask_app.py` - Added `/api/sync-shopping-list` endpoint
- `config.py` - Added dotenv loader

## Next Steps

1. **Fill in `.env`** with your Azure secret
2. **Test the sync** with `python core/todo_sync.py`
3. **Try the UI** - Generate a menu, go to shopping list, send to phone
4. **Check To Do app** on your phone for the items
5. **Report results** - Let us know if it works!

---

*Phase 5 Complete! Ready for Phase 6: Raspberry Pi Deployment*

*Built with assistance from [Claude Code](https://claude.com/claude-code) by Anthropic.*
