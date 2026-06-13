#
# Pi-Menu
# Author:  nobody174 (nobodylearn174@gmail.com)
# Repo:    https://github.com/nobody174/Pi-Menu
# License: All rights reserved © 2025 nobody174
# "It's never too late to give up!"
#

# Pi-Menu: Weekly Menu & Shopping List Generator

A smart weekly meal planner that generates diverse 6-day menus from Hello Fresh recipes and produces organized shopping lists.

## Features

- 🍽️ **Automatic Menu Generation** - Generates 6-day menus (Mon-Sat) with protein variety
- 🛒 **Smart Shopping Lists** - Deduplicated ingredients organized by category
- 📱 **Flask Dashboard** - Beautiful web interface for menu management
- 🔍 **Recipe Scraping** - Automatic scraping of recipes from Hello Fresh
- 🏷️ **Category Selection** - Choose which recipe categories to include in menu generation
- 📋 **Ingredient Deduplication** - Uses fuzzy matching to consolidate ingredients
- 🇳🇴 **Norwegian UI** - Full Norwegian language support

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run Flask dashboard
python pi-deployment/flask_app.py

# Open browser: http://localhost:5000
```

## Project Structure

```
Pi-Menu/
├── core/                    # Core logic modules
├── pi-deployment/           # Flask application
├── frontend/                # Web templates and styling
├── data/                    # Recipes and menu data
├── config.py               # Configuration
└── README.md               # This file
```

## Usage

### Web Dashboard
```bash
python pi-deployment/flask_app.py
```
Open http://localhost:5000 to view and manage menus.

### Generate Menu from Command Line
```python
from core.menu_generator import MenuGenerator
gen = MenuGenerator(selected_categories=['Familie', 'Rask Middag'])
menu = gen.run(num_dinners=6, save=True)
```

## License

All rights reserved © 2025 nobody174

---

*Built with assistance from [Claude Code](https://claude.com/claude-code) by Anthropic.*
