# Menu Planner Architecture

## System Overview

Pi-Menu is a weekly meal planning system that:
1. Loads recipes from user-provided Excel templates
2. Generates weekly menus with selected recipes
3. Deduplicates ingredients for shopping lists
4. Syncs with Microsoft To Do (optional)
5. Sends email notifications (optional)

## Core Components

### 1. Data Management
- **recipes_db.json**: User's recipe database
- **categories.json**: Recipe categories (configurable)
- **weekly_menu.json**: Current week's menu and shopping list
- **pantry_staples.json**: Ingredients that don't need to be shopped

### 2. Menu Generation
- **menu_generator.py**: Randomly selects recipes from user database
- Respects category preferences
- Ensures nutritional variety
- Avoids duplicate recipes in same week

### 3. Ingredient Processing
- **ingredient_deduplicator.py**: 
  - Fuzzy matches ingredients (90%+ similarity)
  - Aggregates quantities across recipes
  - Filters pantry staples
  - Categorizes by type (proteins, vegetables, etc.)
  - Generates shopping list

### 4. Integration Features
- **to_do_sync.py**: Microsoft Graph API integration
  - Syncs menu to To Do lists
  - Syncs shopping list to To Do lists
- **email_notifier.py**: Email notifications
  - Sends weekly menu summaries
  - Sends shopping lists
- **scheduler.py**: Background task scheduler
  - Runs menu generation on schedule (default: Saturday 9am)
  - Sends emails on schedule (default: Friday 6pm)

### 5. Web Interface
- **flask_app.py**: Flask web application
  - View weekly menus
  - Browse recipes
  - Add/edit recipes
  - Configure settings
  - Language toggle (Norwegian/English)

## Deployment Architecture

### Development (Windows/Mac)
```
Flask App (http://localhost:5000)
  ├── Config & Environment Variables
  ├── Recipe Database
  ├── Menu Generator
  ├── Ingredient Deduplicator
  └── Optional: To Do Sync, Email Notifier
```

### Production (Raspberry Pi / Server)
```
Systemd Service
  └── Flask App (HTTPS, gunicorn)
      ├── Background Scheduler
      ├── To Do Sync (optional)
      ├── Email Notifier (optional)
      └── Recipe Database
```

## Data Flow

1. **User adds recipes** → Excel template → Import script → recipes_db.json
2. **Menu generation** (Saturday 9am) →
   - Menu generator selects 5 recipes
   - Ingredient deduplicator creates shopping list
   - weekly_menu.json created
3. **Email notification** (Friday 6pm) →
   - Menu summary sent to email
   - Shopping list sent to email
4. **To Do sync** (optional) →
   - Menu items synced to To Do lists
   - Shopping items synced to To Do lists

## Configuration

All configuration via environment variables (.env file):
- Azure credentials (optional - for To Do sync)
- Email settings (optional)
- Household name
- Scheduler times
- Flask settings

No hardcoded credentials or personal data.

## Technology Stack

- **Backend**: Python 3.9+
- **Framework**: Flask
- **Scheduling**: APScheduler
- **Database**: JSON files
- **Authentication**: Azure AD (optional)
- **Frontend**: HTML, CSS, JavaScript
- **Email**: SMTP (Gmail or custom)
- **Deployment**: systemd (Linux) or Docker
