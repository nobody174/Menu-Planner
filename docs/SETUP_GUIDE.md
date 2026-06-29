# Menu Planner Setup Guide

Complete step-by-step guide to set up Menu Planner for your household.

## Prerequisites

- Python 3.9 or higher
- Git
- A computer or Raspberry Pi to run the application
- Optional: Microsoft account (for To Do sync)

## Installation Steps

### 1. Clone the Repository

```bash
git clone https://github.com/nobody174/Menu-Planner.git
cd Menu-Planner
```

### 2. Create Virtual Environment

```bash
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure Environment

Copy the template file and fill in your settings:

```bash
cp .env.template .env
```

Edit `.env` with your settings:

```
# Your household/family name (displayed in the app)
HOUSEHOLD_NAME=Your Family Name

# Optional: Azure credentials for Microsoft To Do sync
AZURE_CLIENT_ID=
AZURE_CLIENT_SECRET=
AZURE_TENANT_ID=

# Optional: Email notifications
EMAIL_USERNAME=your-email@gmail.com
EMAIL_PASSWORD=your-app-password
EMAIL_RECIPIENTS=yourfamily@example.com
EMAIL_SEND_ENABLED=false

# Flask
FLASK_SECRET_KEY=generate-a-random-string-here
```

### 5. Add Your Recipes

Download the Excel template and add your family recipes:

1. Get template from: `templates/recipe-template-instructions.txt`
2. Fill in your recipes in the Excel file
3. Save as: `my_recipes.xlsx`
4. Import using the web interface or command:

```bash
python3 scripts/import_recipes.py my_recipes.xlsx
```

### 6. Start the Application

```bash
python3 deployment/flask_app.py
```

Visit: `http://localhost:5000`

### 7. Generate First Menu

1. Click "Generer ny meny" (Generate New Menu)
2. Select your preferred categories
3. First week's menu is generated!

## Configuration

### Household Name

Set in `.env`:
```
HOUSEHOLD_NAME=My Family
```

This appears in the app title and browser tab.

### Categories

Edit `data/categories.json` to customize recipe categories. Default categories:

- Familie (Family)
- Rask Middag (Quick Dinner)
- Vegetar (Vegetarian)
- Fisk & Sjømat (Fish & Seafood)
- Kjøtt (Meat)
- Annet (Other)

### Language

Supported languages:
- **Norwegian** (default) - 🇳🇴
- **English** - 🇬🇧

Switch in settings menu.

### To Do Sync (Optional)

For Microsoft To Do integration:

1. Register an Azure app: https://portal.azure.com
2. Get credentials: Client ID, Client Secret, Tenant ID
3. Add to `.env`
4. Click "Logg inn" (Login) in settings
5. Approve permissions
6. Shopping lists sync to your To Do lists

### Email Notifications (Optional)

For weekly menu email summaries:

1. Get Gmail app password: https://myaccount.google.com/apppasswords
2. Add to `.env`:
   ```
   EMAIL_USERNAME=your-email@gmail.com
   EMAIL_PASSWORD=your-app-password
   EMAIL_RECIPIENTS=user1@example.com,user2@example.com
   EMAIL_SEND_ENABLED=true
   ```
3. Emails send every Friday at 6 PM

## Deployment to Raspberry Pi

### Copy to Pi

```bash
scp -r Menu-Planner pi@192.168.1.100:/home/pi/
```

### Set Up Service

Create `/etc/systemd/system/pi-menu.service`:

```ini
[Unit]
Description=Menu Planner Weekly Planner
After=network.target

[Service]
Type=simple
User=pi
WorkingDirectory=/home/pi/Menu-Planner
Environment="PATH=/home/pi/Menu-Planner/venv/bin"
ExecStart=/home/pi/Menu-Planner/venv/bin/python3 deployment/flask_app.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable pi-menu
sudo systemctl start pi-menu
```

## Troubleshooting

### Module not found errors

Ensure virtual environment is activated:

```bash
source venv/bin/activate
pip install -r requirements.txt
```

### Port already in use

Change port in `deployment/flask_app.py`:

```python
app.run(host='0.0.0.0', port=5001)  # Use 5001 instead of 5000
```

### HTTPS certificate errors

Generate self-signed certificates:

```bash
openssl req -x509 -newkey rsa:4096 -nodes -out deployment/cert.pem -keyout deployment/key.pem -days 365
```

### To Do sync not working

1. Check `.env` credentials
2. Log out and log in again via /login
3. Check logs: `logs/flask_app.log`

## Next Steps

- [Recipe Template Guide](EXCEL_GUIDE.md)
- [Categories Documentation](CATEGORIES_GUIDE.md)
- [Frequently Asked Questions](FAQ.md)
- [GitHub Repository](https://github.com/nobody174/Menu-Planner)

## Support

- Report issues: https://github.com/nobody174/Menu-Planner/issues
- Creator: nobody174
- Support on Patreon: https://www.patreon.com/c/Nobody174
