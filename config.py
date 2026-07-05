#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

# Configuration file for Pi-Menu application

import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# ============================================================================
# PATHS
# ============================================================================

PROJECT_ROOT = Path(__file__).parent
DATA_DIR = PROJECT_ROOT / "data"
RECIPES_CACHE_DIR = DATA_DIR / "recipes_cache"
RECIPES_DB_PATH = DATA_DIR / "recipes_db.json"
WEEKLY_MENU_PATH = DATA_DIR / "weekly_menu.json"
LOGS_DIR = PROJECT_ROOT / "logs"

# Create directories if they don't exist
for directory in [DATA_DIR, RECIPES_CACHE_DIR, LOGS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# ============================================================================
# EMAIL CONFIGURATION
# ============================================================================

EMAIL_SENDER = os.getenv("EMAIL_SENDER", "noreply@pi-menu.local")
EMAIL_RECIPIENTS = os.getenv("EMAIL_RECIPIENTS", "").split(",") if os.getenv("EMAIL_RECIPIENTS") else []
EMAIL_SMTP_SERVER = "smtp.gmail.com"  # Or your SMTP server
EMAIL_SMTP_PORT = 587
EMAIL_USERNAME = os.getenv("EMAIL_USERNAME", "")
EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD", "")
EMAIL_SEND_ENABLED = os.getenv("EMAIL_SEND_ENABLED", "false").lower() == "true"

# ============================================================================
# SCHEDULER
# ============================================================================

SCHEDULER_ENABLED = True
MENU_GENERATION_SCHEDULE = {
    "day_of_week": "sat",  # Saturday
    "hour": 9,             # 9 AM
    "minute": 0
}
EMAIL_SEND_SCHEDULE = {
    "day_of_week": "fri",  # Friday
    "hour": 18,            # 6 PM
    "minute": 0
}

# ============================================================================
# FLASK APP
# ============================================================================

FLASK_HOST = "0.0.0.0"
FLASK_PORT = 5000
FLASK_DEBUG = False  # Set to True only for development

# ============================================================================
# MENU GENERATION SETTINGS
# ============================================================================

MENU_DAYS = 5  # Monday-Saturday (5 dinners; Sunday = leftovers)
PREFERRED_CATEGORIES = ["Familie", "Rask Middag"]  # Prefer family-friendly recipes

# ============================================================================
# INGREDIENT DEDUPLICATION SETTINGS
# ============================================================================

FUZZY_MATCH_THRESHOLD = 90  # Percentage (0-100)
PANTRY_STAPLES_PATH = PROJECT_ROOT / "core" / "pantry_staples.json"

# ============================================================================
# ALLERGEN FILTERS
# ============================================================================

ALLERGEN_FILTERS = {
    "orange": ["appelsin", "oransje", "orange", "orange juice", "orange zest"],
    # Add more as needed
}

# ============================================================================
# LOGGING
# ============================================================================

LOG_FILE = LOGS_DIR / "pi-menu.log"
LOG_LEVEL = "INFO"  # DEBUG, INFO, WARNING, ERROR, CRITICAL

# ============================================================================
# HOUSEHPLD SETTINGS
# ============================================================================

HOUSEHOLD_NAME = os.getenv("HOUSEHOLD_NAME", "{Family_Name}")
HOUSEHOLD_SIZE = 5
TIMEZONE = "Europe/Oslo"

# ============================================================================
# API ENDPOINTS
# ============================================================================

# ============================================================================
# NOTES
# ============================================================================

"""
Environment variables to set before running:

  EMAIL_USERNAME         - Gmail/SMTP username
  EMAIL_PASSWORD         - Gmail/SMTP password (or app-specific password)
  EMAIL_SEND_ENABLED     - Set to "true" to enable email sending

Example .env file:
  EMAIL_USERNAME=your-email@gmail.com
  EMAIL_PASSWORD=your-app-password
  EMAIL_SEND_ENABLED=true

Load from .env file using:
  from dotenv import load_dotenv
  load_dotenv()
"""
