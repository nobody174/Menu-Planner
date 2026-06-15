# Pi-Menu - Weekly Meal Planner

A Python/Flask web application for families to organize recipes, generate weekly menus, and create shopping lists.

**Created by:** [nobody174](https://github.com/nobody174)  
**License:** MIT  
**Support:** [Patreon](https://www.patreon.com/c/Nobody174)

## Features

✅ **Recipe Management** - Add your own recipes via Excel template  
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

### Installation

```bash
# Clone repository
git clone https://github.com/nobody174/Pi-Menu-Public.git
cd Pi-Menu-Public

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Copy configuration template
cp .env.template .env

# Start application
python3 pi-deployment/app.py
```

Visit: **http://localhost:5000**

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
