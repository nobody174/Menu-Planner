# Pi-Menu v1.1 Testing Guide

## Quick Setup: Run in VSCode Terminal

### Step 1: Open VSCode in the Project
```bash
# From PowerShell/Command Prompt
cd "D:\Claude AI Projects\projects\Public-Pi-Menu"
code .
```

### Step 2: Open Terminal in VSCode
- **Keyboard:** Ctrl + ` (backtick)
- **Menu:** Terminal → New Terminal

### Step 3: Check if Pi-Menu is Running on Pi

**If Pi is running Pi-Menu on port 5000:**
- You need to use a **different port** on your Windows machine
- Stop the Pi's Flask app temporarily, OR
- Use a different port (5001, 5002, 5003, etc.)

**To use a different port:**
```bash
# Edit the Flask app to use port 5001 instead
python3 pi-deployment/app.py  # This uses port 5000 by default
```

If you want to change the port, edit `pi-deployment/app.py` line 440:
```python
# BEFORE: app.run(host='0.0.0.0', port=5000, debug=False)
# AFTER:  app.run(host='0.0.0.0', port=5001, debug=False)
```

### Step 4: Start the Flask App
In the VSCode terminal, run:
```bash
python3 pi-deployment/app.py
```

You should see output like:
```
2026-06-16 21:05:13,684 - INFO - Flask templates: D:\Claude AI Projects\projects\Public-Pi-Menu\frontend\templates
2026-06-16 21:05:14,470 - INFO - Starting Flask app on http://0.0.0.0:5000
 * Running on http://127.0.0.1:5000
```

### Step 5: Access the App
Open browser to:
- **http://localhost:5000** (if using port 5000)
- **http://localhost:5001** (if using port 5001)
- **http://localhost:5002** (if using port 5002)

Now you'll have:
- ✅ Browser window showing the app
- ✅ Terminal window showing logs
- ✅ Easy to see errors and debug

---

## Test Checklist

### 1. Language Default (FIXED ✅)
- [ ] App loads in **English** (not Norwegian)
- [ ] Language toggle button visible (⚙️ gear icon)
- [ ] Click gear → See "Language" section
- [ ] Click "🇬🇧 English" → Stays English
- [ ] Click "🇳🇴 Norsk" → Changes to Norwegian
- [ ] Click "🇬🇧 English" → Changes back

### 2. Theme Switching (TESTING NEEDED)
- [ ] Click ⚙️ gear icon → Settings dropdown
- [ ] Click "Theme" or "Choose Theme"
- [ ] See 9 theme options
- [ ] Click a theme color square
- [ ] Check logs for errors (terminal)
- [ ] Theme should change colors

**If theme doesn't change:**
- Check browser console (F12 → Console tab)
- Check terminal output
- Look for JavaScript errors

### 3. Generate Menu
- [ ] Click "Generate Menu" button
- [ ] Menu generates with 6 dinners
- [ ] Shopping list appears
- [ ] Check terminal for any errors

### 4. Test Settings Page (For Import/Export)
- [ ] Click ⚙️ → Click "Settings"
- [ ] OR go to: `http://localhost:5000/settings`
- [ ] Should see these sections:
  - Language selection
  - Theme previews
  - **Recipe Packs** (NEW)
  - **Personal Recipe Arsenal** (NEW)
  - About section

### 5. Test Recipe Pack Import
On Settings page:
- [ ] Find "Recipe Packs" section
- [ ] Click "📦 Importer oppskrifter-pakker" button
- [ ] Modal opens showing 5 packs:
  1. Popular Norwegian Recipes (15)
  2. European Classics (15)
  3. Nordic Classics (15)
  4. Holiday Recipes (12)
  5. Summer Recipes (15)
- [ ] Click checkbox on one pack
- [ ] Click "Import" button
- [ ] Success message appears
- [ ] Check terminal logs

### 6. Test Personal Recipe Export
On Settings page:
- [ ] Find "Personal Recipe Arsenal" section
- [ ] Click "💾 Eksporter alle oppskrifter"
- [ ] Browser downloads file (check Downloads folder)
- [ ] File named: `pi-menu-personal-recipes-2026-06-16.json`

### 7. Test Personal Recipe Import
On Settings page:
- [ ] Find "Personal Recipe Arsenal" section
- [ ] Click "📥 Importer fra fil"
- [ ] Modal opens with file picker
- [ ] Click "📁 Velg fil"
- [ ] Select a `.json` file (use the one you just downloaded)
- [ ] Success message appears

---

## Understanding the Terminal Log

### Good Logs (What You Should See)
```
2026-06-16 21:05:14,470 - INFO - Starting Flask app on http://0.0.0.0:5000
127.0.0.1 - - [16/Jun/2026 21:05:20] "GET /settings HTTP/1.1" 200 -
127.0.0.1 - - [16/Jun/2026 21:05:21] "GET /api/recipe-packs/list HTTP/1.1" 200 -
```

**What to look for:**
- `200` = Success ✅
- `404` = Page not found ❌
- `500` = Server error ❌

### Common Errors

**Theme not switching:**
- Check browser console (F12)
- Look for JavaScript errors
- Check `frontend/static/themes/theme-manager.js`

**Import button not visible:**
- Make sure you're on `/settings` page
- Reload page (Ctrl+R)
- Check terminal for 404 errors

**API errors:**
- Check terminal for `POST /api/recipe-packs/import`
- Should show `200` response
- If `404`, check that file `/api/recipe-packs/list` is working

---

## Troubleshooting

### Issue: Theme Changes Don't Persist
**Solution:**
- Clear browser cache: Ctrl+Shift+Delete
- Then reload page

### Issue: Settings Page Shows Norwegian
**Solution:**
- This was FIXED in latest commit
- Pull latest changes: `git pull`
- Refresh browser: Ctrl+F5 (hard refresh)

### Issue: Recipe Pack Import Button Missing
**Solution:**
1. Make sure you're on `/settings` page
2. Scroll down to find "Recipe Packs" section
3. If not visible, check browser console for errors (F12)
4. Reload page

### Issue: Terminal Shows "Address Already in Use"
**Solution:**
- Port 5000 is already in use
- Run: `lsof -i :5000` (Mac/Linux) or `netstat -ano | findstr :5000` (Windows)
- Kill process: `kill <PID>` or restart VSCode
- Start app again

### Issue: "No module named 'flask'"
**Solution:**
```bash
pip install flask python-dotenv apscheduler requests
```

### Issue: "Address Already in Use" on Port 5000
**This means Pi's Flask app is running!**

**Solution 1: Stop Pi's Flask app**
- SSH into Pi: `ssh vartdalffs@10.0.0.54`
- Kill Flask: `pkill -f "python3 pi-deployment"`
- Then test on Windows

**Solution 2: Use Different Port**
- Edit `pi-deployment/app.py` line 440
- Change port to 5001, 5002, 5003, etc.
- Test on Windows at `http://localhost:5001`

**Solution 3: Run on Pi Itself**
- SSH into Pi
- Run: `python3 pi-deployment/app.py`
- Access from Windows: `http://10.0.0.54:5000`
- Terminal shows logs in SSH session

---

## URLs to Test

| URL | Purpose | Expected |
|-----|---------|----------|
| `http://localhost:5000/` | Dashboard | Shows menu or error (no menu yet) |
| `http://localhost:5000/settings` | Settings page | Shows all settings options |
| `http://localhost:5000/add-recipe` | Add recipe form | Recipe entry form |
| `http://localhost:5000/all-recipes` | View all recipes | List of recipes |
| `http://localhost:5000/shopping` | Shopping list | Empty or populated list |
| `http://localhost:5000/api/recipe-packs/list` | API test | JSON with 5 packs |
| `http://localhost:5000/api/recipes/export` | API export | JSON with recipes |

---

## Testing with Logs

### Follow These Steps:

1. **Open VSCode terminal**
   ```bash
   python3 pi-deployment/app.py
   ```

2. **Keep terminal visible** (don't minimize)

3. **Open browser** in separate window/monitor
   - Left side: Browser with app
   - Right side: VSCode with terminal logs

4. **Click a button/link**
   - Watch terminal for instant logs
   - See `GET /settings HTTP/1.1" 200`
   - Any errors show immediately

5. **Debug easily**
   - See API calls in terminal
   - Check status codes (200 vs 404)
   - Copy-paste errors from terminal into search

---

## Success Indicators

✅ **You'll know it's working when:**
- Language defaults to English
- Language toggle works (buttons respond)
- Settings page loads
- Theme options visible (even if not switching yet)
- Recipe packs list API works (check URL)
- Terminal shows `200` status codes
- No red errors in browser console (F12)

---

## Next Steps After Testing

1. **If all tests pass:**
   - Celebrate! 🎉
   - Note any small issues
   - Create issue for theme switching if needed

2. **If tests fail:**
   - Look at terminal output
   - Note the HTTP status code
   - Copy the error message
   - Check browser console (F12)

3. **Report findings:**
   - Which features work
   - Which features don't
   - Any error messages
   - Browser/OS information

---

**Happy testing! 🚀**
