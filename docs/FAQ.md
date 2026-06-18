# Frequently Asked Questions (FAQ)

## General Questions

### What is Menu Planner?

Menu Planner is a weekly meal planner that helps you:
- Organize your family recipes
- Automatically generate weekly menus
- Create shopping lists
- Sync with Microsoft To Do (optional)
- Support multiple languages

### Is Menu Planner free?

Yes! Menu Planner is open-source and free to use. 

Support the creator on Patreon: https://www.patreon.com/c/Nobody174

### How do I run Menu Planner on a Raspberry Pi?

See [Setup Guide - Deployment to Raspberry Pi](SETUP_GUIDE.md#deployment-to-raspberry-pi)

## Usage Questions

### How do I change my family name?

Edit `.env` file:
```
HOUSEHOLD_NAME=Your Family Name
```

Then restart the app. The name will appear in the title and footer.

### How do I add recipes?

1. Get the Excel template
2. Fill in your recipes
3. Import via web interface (Settings → + Legg til oppskrift)
4. Or use command: `python3 scripts/import_recipes.py my_recipes.xlsx`

See [Excel Guide](EXCEL_GUIDE.md) for detailed instructions.

### How do I switch language?

1. Open Settings (⚙️ in top right)
2. Click "Språk" (Language)
3. Select 🇳🇴 Norsk or 🇬🇧 English
4. Page reloads with new language

Current default: Norwegian

### How do I change measurement units?

When language is set to English, all metric measurements (g, ml, dl, l) automatically convert to imperial (oz, cups, fl oz) where possible.

Default: Metric (Norwegian style)

### How do I customize categories?

Edit `data/categories.json`:

```json
[
  {
    "code": "pizza",
    "name_no": "Pizza",
    "name_en": "Pizza",
    "description_no": "Hjemmelaget pizza",
    "description_en": "Homemade pizza",
    "icon": "🍕",
    "color": "#FF6B6B"
  }
]
```

Then restart the app.

## Technical Questions

### How do I set up To Do sync?

1. Create Azure app at https://portal.azure.com
2. Get credentials: Client ID, Secret, Tenant ID
3. Add to `.env`:
   ```
   AZURE_CLIENT_ID=your-id
   AZURE_CLIENT_SECRET=your-secret
   AZURE_TENANT_ID=your-tenant-id
   ```
4. Restart app
5. Click "Logg inn" (Login) in Settings
6. Approve permissions
7. Shopping lists sync to To Do

See [Setup Guide](SETUP_GUIDE.md#to-do-sync-optional) for more.

### How do I set up email notifications?

1. Get Gmail app password: https://myaccount.google.com/apppasswords
2. Add to `.env`:
   ```
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENTS=family@example.com
   EMAIL_SEND_ENABLED=true
   ```
3. Restart app
4. Weekly menu email sends every Friday at 6 PM

### How do I change the schedule?

Edit `config.py`:

```python
MENU_GENERATION_SCHEDULE = {
    "day_of_week": "sat",  # sat = Saturday
    "hour": 9,             # 9 AM
    "minute": 0
}

EMAIL_SEND_SCHEDULE = {
    "day_of_week": "fri",  # fri = Friday
    "hour": 18,            # 6 PM
    "minute": 0
}
```

Days: mon, tue, wed, thu, fri, sat, sun

### What ingredients are in the pantry staples?

Edit `core/pantry_staples.json` to customize. By default, Menu Planner filters out common pantry items (salt, oil, etc.) from shopping lists.

### How do I generate a new menu?

1. Click "Generer ny meny" (Generate New Menu) in navigation
2. Optionally select categories to prefer
3. Click "Bruk" (Apply)
4. New menu is generated with recipes from selected categories

## Troubleshooting

### My recipes aren't showing up

- Check `.env` setting: `HOUSEHOLD_NAME` is set
- Verify recipes are in `data/sample_recipes.json`
- Check recipe categories match `data/categories.json`
- Restart the app

### To Do sync isn't working

- Check credentials in `.env` are correct
- Log out and log in again (Settings → Logg ut → Logg inn)
- Check logs: `logs/flask_app.log`
- Ensure you have Microsoft To Do account

### Shopping list is empty

- Generate a new menu first
- Check that recipes have ingredients
- Verify ingredients are not all pantry staples
- Check ingredient fuzzy matching threshold in `config.py`

### Email notifications aren't sending

- Check `.env` settings are correct
- Enable: `EMAIL_SEND_ENABLED=true`
- Check logs: `logs/pi-menu.log`
- Verify SMTP server settings
- For Gmail, use app-specific password (not regular password)

### App is running slow

- Check available disk space
- Reduce number of recipes if over 500
- Clear browser cache
- Restart app: `pkill -f pi-menu`

## Feature Requests & Bugs

Found a bug or want a feature?

- Report on GitHub: https://github.com/nobody174/Menu-Planner/issues
- Contact creator: nobody174
- Patreon: https://www.patreon.com/c/Nobody174

## Privacy & Security

### Are my recipes stored securely?

Recipes are stored locally in JSON files. They are not sent to any external service unless you explicitly enable To Do sync.

### Is my data backed up?

You should back up:
- `.env` file (contains configuration)
- `data/sample_recipes.json` (your recipes)
- `data/categories.json` (customized categories)

Recommendation: Use git to version control your recipes and settings.

### Can I export my recipes?

Yes! Your recipes are in standard JSON format:
```bash
cat data/sample_recipes.json  # View/export recipes
```

Copy the file to back up or migrate to another installation.

## More Help

- [Setup Guide](SETUP_GUIDE.md)
- [Excel Template Guide](EXCEL_GUIDE.md)
- [Categories Documentation](CATEGORIES_GUIDE.md)
- [GitHub Issues](https://github.com/nobody174/Menu-Planner/issues)
