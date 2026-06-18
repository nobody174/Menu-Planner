# Menu Planner

*Originally built for Raspberry Pi — now runs anywhere Python does.*

A Python/Flask web application for families to organize recipes, generate weekly menus, and create shopping lists.

**Created by:** [nobody174](https://github.com/nobody174)  
**License:** MIT  
**Support:** [Patreon](https://www.patreon.com/c/Nobody174)

## Features

✅ **Recipe Management** - Add your own recipes via web form or import from Excel  
✅ **Sample Recipes** - 10 bilingual sample recipes included to get started  
✅ **Menu Generation** - Automatically generate weekly menus from your recipes  
✅ **Shopping Lists** - Automatically deduplicated ingredient lists  
✅ **Bilingual Support** - Norwegian & English with one-click toggle  
✅ **Categories** - Organize recipes (Family, Quick, Vegetarian, Fish, Meat, Other)  
✅ **Microsoft To Do Sync** - Push shopping lists to To Do lists (optional)  
✅ **Email Notifications** - Weekly menu summaries via email (optional)  
✅ **Responsive Design** - Works on desktop, tablet, and mobile  
✅ **Multiple Themes** - 9+ beautiful themes to choose from  
✅ **Open Source** - 100% free, no tracking, no accounts needed  

## Quick Start

### Prerequisites

- Python 3.9+
- Git
- pip (Python package manager)

### Installation (5 minutes)

```bash
# 1. Clone repository
git clone https://github.com/nobody174/Pi-Menu-Public.git
cd Pi-Menu-Public

# 2. Create & activate virtual environment
python3 -m venv venv
source venv/bin/activate
# On Windows: venv\Scripts\activate

# 3. Install dependencies
pip install -r requirements.txt

# 4. Configure (edit .env with your family name)
cp .env.template .env
nano .env  # Edit: HOUSEHOLD_NAME=Your Family

# 5. Start the app
python3 pi-deployment/app.py
```

**Open browser:** http://localhost:5000

### First Steps

1. **Explore sample recipes** - 10 bilingual recipes included as examples
2. **Add your recipes** - Click "Legg til oppskrift" (Add Recipe) and fill in the form
3. **Generate menu** - Click "Generer ny meny" (Generate Menu)
4. **Create shopping list** - Click "Handleliste" (Shopping List)
5. **Customize** - Change language, theme, and categories in Settings

## Configuration

Edit `.env`:

```ini
# Your family name
HOUSEHOLD_NAME=My Family

# Optional: Microsoft To Do sync
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=

# Optional: Email notifications
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=app-password
EMAIL_RECIPIENTS=family@example.com
EMAIL_SEND_ENABLED=false
```

## Usage

### 1. Add Recipes

- Download Excel template from `templates/`
- Fill in your family recipes
- Import via web interface or CLI:
  ```bash
  python3 scripts/import_recipes.py my_recipes.xlsx
  ```

### 2. Generate Menu

- Click "Generer ny meny" (Generate New Menu)
- Select preferred categories
- Weekly menu is generated automatically

### 3. Create Shopping List

- Click "Handleliste" (Shopping List)
- Review automatically deduplicated ingredients
- Print or sync to To Do lists

### 4. Customize

- Change language: Settings → Språk
- Switch theme: Settings → Tema
- Edit categories: `data/categories.json`

## Command-Line Tools

Manage Pi-Menu from the terminal:

```bash
# List all recipes
python3 scripts/pi-menu-cli.py recipes list

# Count recipes by category
python3 scripts/pi-menu-cli.py recipes count

# Validate recipe data
python3 scripts/pi-menu-cli.py recipes validate

# List categories
python3 scripts/pi-menu-cli.py categories list

# Generate weekly menu
python3 scripts/pi-menu-cli.py menu generate

# Validate configuration
python3 scripts/pi-menu-cli.py validate

# Manage categories
python3 scripts/category-editor.py --list
python3 scripts/category-editor.py --add
python3 scripts/category-editor.py --backup
```

## Documentation

- **[Setup Guide](docs/SETUP_GUIDE.md)** - Installation & configuration
- **[Excel Template Guide](docs/EXCEL_GUIDE.md)** - How to add recipes
- **[FAQ](docs/FAQ.md)** - Common questions & troubleshooting
- **[Architecture](ARCHITECTURE.md)** - System design & data flow

## License

MIT License - See [LICENSE](LICENSE) file

## Credits

**Creator:** [nobody174](https://github.com/nobody174)

Built with [Flask](https://flask.palletsprojects.com/) and [Claude Code](https://claude.com/claude-code).

## Support

- **GitHub:** [Pi-Menu-Public](https://github.com/nobody174/Pi-Menu-Public)
- **Patreon:** [Support on Patreon](https://www.patreon.com/c/Nobody174)
