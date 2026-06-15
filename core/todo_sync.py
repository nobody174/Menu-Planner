#
# Pi-Menu - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Pi-Menu-Public
# License: MIT
#

import logging
import json
import os
import time
from pathlib import Path
from typing import List, Dict, Optional
import requests
from datetime import datetime

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))
from config import (
    AZURE_CLIENT_ID,
    AZURE_CLIENT_SECRET,
    AZURE_TENANT_ID,
    TO_DO_LIST_NAME,
    SHOPPING_LIST_NAME,
    LOGS_DIR
)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(LOGS_DIR / 'todo_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Emoji mapping for ingredient types
INGREDIENT_EMOJIS = {
    'melk': '🥛', 'yoghurt': '🥛', 'fløte': '🥛', 'ost': '🧀',
    'laks': '🐟', 'fisk': '🐟', 'torsk': '🐟', 'sei': '🐟', 'reke': '🦐',
    'kjøtt': '🥩', 'kjøttdeig': '🥩', 'bacon': '🥓', 'svin': '🐷', 'steak': '🥩',
    'kylling': '🍗', 'høne': '🍗',
    'lam': '🐑',
    'tomat': '🍅', 'løk': '🧅', 'hvitløk': '🧄', 'paprika': '🌶️',
    'gulrot': '🥕', 'salat': '🥗', 'spinat': '🥬', 'brokk': '🥦', 'blomkål': '🥦',
    'sopp': '🍄', 'agurk': '🥒', 'avokado': '🥑', 'mais': '🌽',
    'brød': '🍞', 'pasta': '🍝', 'ris': '🍚', 'couscous': '🍚',
    'egg': '🥚',
    'poteter': '🥔', 'søtpotet': '🥔', 'rot': '🥔',
    'tofu': '🟫', 'bønner': '🫘', 'linser': '🫘',
    'smør': '🧈', 'olje': '🫒',
}


class MicrosoftGraphAuth:
    """Handle Microsoft Graph API authentication using Device Code flow"""

    def __init__(self):
        self.client_id = AZURE_CLIENT_ID
        self.tenant_id = AZURE_TENANT_ID
        self.access_token = None
        self.token_expiry = None

    def get_access_token(self) -> Optional[str]:
        """Get OAuth2 access token using Device Code flow (browser-based)"""
        try:
            logger.info("\n" + "="*60)
            logger.info("DEVICE CODE AUTHENTICATION")
            logger.info("="*60)

            # Step 1: Get device code
            device_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/devicecode"
            device_data = {
                'client_id': self.client_id,
                'scope': 'https://graph.microsoft.com/.default'
            }

            device_response = requests.post(device_url, data=device_data, timeout=10)
            device_response.raise_for_status()
            device_info = device_response.json()

            device_code = device_info['device_code']
            user_code = device_info['user_code']
            verification_uri = device_info['verification_uri']

            logger.info("\n⚠️  PLEASE FOLLOW THESE STEPS:")
            logger.info(f"1. Open: {verification_uri}")
            logger.info(f"2. Enter this code: {user_code}")
            logger.info("3. Authenticate with your Microsoft account")
            logger.info("4. Return here (the app will continue automatically)\n")

            # Step 2: Poll for token
            token_url = f"https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token"
            polling_interval = device_info.get('interval', 5)
            max_attempts = 120  # 10 minutes with 5-second intervals

            for attempt in range(max_attempts):
                token_data = {
                    'client_id': self.client_id,
                    'device_code': device_code,
                    'grant_type': 'urn:ietf:params:oauth:grant-type:device_code'
                }

                token_response = requests.post(token_url, data=token_data, timeout=10)

                if token_response.status_code == 200:
                    token_info = token_response.json()
                    self.access_token = token_info['access_token']
                    logger.info("✅ Successfully authenticated with Microsoft Graph!")
                    return self.access_token

                elif token_response.status_code == 400:
                    error_code = token_response.json().get('error', '')
                    if error_code == 'authorization_pending':
                        # Still waiting for user to authenticate
                        logger.info(f"Waiting for authentication... ({attempt+1}/{max_attempts})")
                        import time
                        time.sleep(polling_interval)
                    elif error_code == 'expired_token':
                        logger.error("Device code expired. Please try again.")
                        return None
                    else:
                        logger.error(f"Authentication error: {error_code}")
                        return None
                else:
                    logger.error(f"Unexpected response: {token_response.status_code}")
                    return None

            logger.error("Authentication timeout. Please try again.")
            return None

        except Exception as e:
            logger.error(f"Failed to authenticate with Azure: {e}")
            return None


class ToDoSync:
    """Sync shopping list and meal plan with Microsoft To Do"""

    def __init__(self):
        self.auth = MicrosoftGraphAuth()
        self.access_token = None
        self.shopping_list_id = None
        self.meal_plan_list_id = None

    def authenticate(self) -> bool:
        """Authenticate with Microsoft Graph"""
        self.access_token = self.auth.get_access_token()
        if not self.access_token:
            return False

        # Get or create lists
        if not self.get_or_create_lists():
            return False

        logger.info("To Do sync authenticated and ready")
        return True

    def get_headers(self) -> Dict:
        """Get authorization headers for Graph API"""
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def get_or_create_lists(self) -> bool:
        """Get existing lists or create them if they don't exist"""
        try:
            # Try beta endpoint first (works better with personal accounts)
            url = "https://graph.microsoft.com/beta/me/todo/lists"
            response = requests.get(url, headers=self.get_headers(), timeout=10)

            # Fall back to v1.0 if beta doesn't work
            if response.status_code == 401 or response.status_code == 403:
                logger.warning("Beta endpoint returned 401/403, trying v1.0 endpoint")
                url = "https://graph.microsoft.com/v1.0/me/todo/lists"
                response = requests.get(url, headers=self.get_headers(), timeout=10)

            response.raise_for_status()

            lists = response.json().get('value', [])

            # Find our lists
            for lst in lists:
                if lst['displayName'] == SHOPPING_LIST_NAME:
                    self.shopping_list_id = lst['id']
                    logger.info(f"Found shopping list: {self.shopping_list_id}")
                elif lst['displayName'] == TO_DO_LIST_NAME:
                    self.meal_plan_list_id = lst['id']
                    logger.info(f"Found meal plan list: {self.meal_plan_list_id}")

            # Create missing lists
            if not self.shopping_list_id:
                self.shopping_list_id = self._create_list(SHOPPING_LIST_NAME)
            if not self.meal_plan_list_id:
                self.meal_plan_list_id = self._create_list(TO_DO_LIST_NAME)

            return bool(self.shopping_list_id and self.meal_plan_list_id)

        except Exception as e:
            logger.error(f"Failed to get or create lists: {e}")
            return False

    def _create_list(self, list_name: str) -> Optional[str]:
        """Create a new task list"""
        try:
            url = "https://graph.microsoft.com/beta/me/todo/lists"
            data = {'displayName': list_name}

            response = requests.post(url, headers=self.get_headers(), json=data, timeout=10)
            response.raise_for_status()

            list_id = response.json()['id']
            logger.info(f"Created new list: {list_name} ({list_id})")
            return list_id

        except Exception as e:
            logger.error(f"Failed to create list {list_name}: {e}")
            return None

    def get_emoji_for_ingredient(self, ingredient_name: str) -> str:
        """Get appropriate emoji for ingredient"""
        name_lower = ingredient_name.lower()

        for keyword, emoji in INGREDIENT_EMOJIS.items():
            if keyword in name_lower:
                return emoji

        return '📝'  # Default emoji

    def sync_shopping_list_to_todo(self, shopping_list: Dict[str, List[Dict]]) -> bool:
        """Sync shopping list items to To Do"""
        if not self.access_token:
            if not self.authenticate():
                return False

        try:
            # Clear existing tasks in shopping list
            self._clear_list(self.shopping_list_id)

            logger.info("Syncing shopping list to To Do...")

            # Add each ingredient as a task
            for category, items in shopping_list.items():
                for item in items:
                    ingredient = item['ingredient']
                    quantity = item['quantity']
                    unit = item['unit']

                    # Format task title with quantity and emoji
                    emoji = self.get_emoji_for_ingredient(ingredient)
                    task_title = f"{emoji} {ingredient} - {quantity}{unit}".strip()

                    # Create task
                    self._create_task(self.shopping_list_id, task_title)

            logger.info("Shopping list synced to To Do successfully")
            return True

        except Exception as e:
            logger.error(f"Failed to sync shopping list: {e}")
            return False

    def _clear_list(self, list_id: str) -> bool:
        """Remove all tasks from a list"""
        try:
            url = f"https://graph.microsoft.com/beta/me/todo/lists/{list_id}/tasks"
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            tasks = response.json().get('value', [])

            for task in tasks:
                task_id = task['id']
                delete_url = f"https://graph.microsoft.com/beta/me/todo/lists/{list_id}/tasks/{task_id}"
                requests.delete(delete_url, headers=self.get_headers(), timeout=10)

            logger.info(f"Cleared {len(tasks)} tasks from list")
            return True

        except Exception as e:
            logger.error(f"Failed to clear list: {e}")
            return False

    def _create_task(self, list_id: str, task_title: str) -> Optional[str]:
        """Create a new task in a list"""
        try:
            url = f"https://graph.microsoft.com/beta/me/todo/lists/{list_id}/tasks"
            data = {
                'title': task_title,
                'importance': 'normal',
                'isReminderOn': False
            }

            response = requests.post(url, headers=self.get_headers(), json=data, timeout=10)
            response.raise_for_status()

            task_id = response.json()['id']
            return task_id

        except Exception as e:
            logger.error(f"Failed to create task '{task_title}': {e}")
            return None

    def sync_todo_back_to_app(self) -> Dict[str, bool]:
        """Get task completion status from To Do and return mapping"""
        if not self.access_token:
            if not self.authenticate():
                return {}

        try:
            url = f"https://graph.microsoft.com/beta/me/todo/lists/{self.shopping_list_id}/tasks"
            response = requests.get(url, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            tasks = response.json().get('value', [])
            task_status = {}

            for task in tasks:
                task_title = task['title']
                is_completed = task.get('status') == 'completed'
                task_status[task_title] = is_completed

            logger.info(f"Synced {len(tasks)} tasks from To Do")
            return task_status

        except Exception as e:
            logger.error(f"Failed to sync from To Do: {e}")
            return {}


def test_sync():
    """Test the To Do sync functionality"""
    logger.info("Testing To Do sync...")

    sync = ToDoSync()

    # Test authentication
    if not sync.authenticate():
        logger.error("Authentication failed")
        return

    # Test syncing a sample shopping list
    sample_list = {
        'Dairy': [
            {'ingredient': 'Melk', 'quantity': 2, 'unit': 'L'},
            {'ingredient': 'Yoghurt', 'quantity': 500, 'unit': 'g'}
        ],
        'Proteins': [
            {'ingredient': 'Laks', 'quantity': 400, 'unit': 'g'},
            {'ingredient': 'Kjøttdeig', 'quantity': 800, 'unit': 'g'}
        ]
    }

    if sync.sync_shopping_list_to_todo(sample_list):
        logger.info("Sync test successful!")
    else:
        logger.error("Sync test failed")


if __name__ == '__main__':
    test_sync()
