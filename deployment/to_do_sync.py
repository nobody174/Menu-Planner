import json
import logging
from pathlib import Path
from datetime import datetime
import requests
from typing import Dict, Optional

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/to_do_sync.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
MENU_FILE = DATA_DIR / 'weekly_menu.json'

class ToDoSync:
    def __init__(self, client_id: str, client_secret: str, tenant_id: str):
        self.client_id = client_id
        self.client_secret = client_secret
        self.tenant_id = tenant_id
        self.access_token = None
        self.graph_endpoint = 'https://graph.microsoft.com/v1.0'
        self.todo_endpoint = f'{self.graph_endpoint}/me/todo/lists'

    def authenticate(self) -> bool:
        try:
            auth_endpoint = f'https://login.microsoftonline.com/{self.tenant_id}/oauth2/v2.0/token'

            data = {
                'client_id': self.client_id,
                'client_secret': self.client_secret,
                'scope': 'https://graph.microsoft.com/.default',
                'grant_type': 'client_credentials'
            }

            response = requests.post(auth_endpoint, data=data, timeout=10)
            response.raise_for_status()

            self.access_token = response.json()['access_token']
            logger.info("Successfully authenticated with Azure")
            return True

        except Exception as e:
            logger.error(f"Authentication failed: {e}")
            return False

    def get_headers(self) -> Dict:
        return {
            'Authorization': f'Bearer {self.access_token}',
            'Content-Type': 'application/json'
        }

    def get_or_create_list(self, list_name: str) -> Optional[str]:
        try:
            response = requests.get(self.todo_endpoint, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            lists = response.json().get('value', [])

            for lst in lists:
                if lst['displayName'] == list_name:
                    logger.info(f"Found existing list: {list_name}")
                    return lst['id']

            body = {'displayName': list_name}
            response = requests.post(self.todo_endpoint, json=body, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            list_id = response.json()['id']
            logger.info(f"Created new list: {list_name}")
            return list_id

        except Exception as e:
            logger.error(f"Failed to get/create list '{list_name}': {e}")
            return None

    def clear_list_tasks(self, list_id: str) -> bool:
        try:
            endpoint = f'{self.todo_endpoint}/{list_id}/tasks'
            response = requests.get(endpoint, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            tasks = response.json().get('value', [])

            for task in tasks:
                delete_endpoint = f'{endpoint}/{task["id"]}'
                requests.delete(delete_endpoint, headers=self.get_headers(), timeout=10)

            logger.info(f"Cleared {len(tasks)} tasks from list {list_id}")
            return True

        except Exception as e:
            logger.error(f"Failed to clear list tasks: {e}")
            return False

    def add_task(self, list_id: str, task_title: str, subtasks: list = None) -> bool:
        try:
            endpoint = f'{self.todo_endpoint}/{list_id}/tasks'

            body = {
                'title': task_title,
                'categories': ['Menu']
            }

            response = requests.post(endpoint, json=body, headers=self.get_headers(), timeout=10)
            response.raise_for_status()

            task_id = response.json()['id']

            if subtasks:
                for subtask in subtasks:
                    subtask_endpoint = f'{endpoint}/{task_id}/checklistItems'
                    subtask_body = {'displayName': subtask}
                    requests.post(subtask_endpoint, json=subtask_body, headers=self.get_headers(), timeout=10)

            logger.info(f"Added task: {task_title}")
            return True

        except Exception as e:
            logger.error(f"Failed to add task: {e}")
            return False

    def sync_menu(self, menu: Dict) -> bool:
        if not self.authenticate():
            logger.error("Failed to sync menu - authentication failed")
            return False

        menu_list_id = self.get_or_create_list('Ukemeny')
        if not menu_list_id:
            logger.error("Failed to get/create menu list")
            return False

        self.clear_list_tasks(menu_list_id)

        for dinner in menu.get('dinners', []):
            day = dinner['day']
            title = dinner['title']
            time = dinner['time_minutes']

            task_title = f"{day}: {title} ({time} min)"
            ingredients = [f"- {ing['ingredient']}: {ing['quantity']} {ing['unit']}"
                          for ing in dinner.get('ingredients', [])]

            self.add_task(menu_list_id, task_title, ingredients[:10])

        logger.info("Menu synced to To Do successfully")
        return True

    def sync_shopping_list(self, menu: Dict) -> bool:
        if not self.authenticate():
            logger.error("Failed to sync shopping list - authentication failed")
            return False

        shopping_list_id = self.get_or_create_list('Handleliste')
        if not shopping_list_id:
            logger.error("Failed to get/create shopping list")
            return False

        self.clear_list_tasks(shopping_list_id)

        shopping = menu.get('shopping_list', {})

        for category, items in shopping.items():
            if items:
                category_task_id = self.add_task(shopping_list_id, category)

                for item in items:
                    item_title = f"{item['ingredient']} ({item['quantity']} {item['unit']})"
                    self.add_task(shopping_list_id, item_title)

        logger.info("Shopping list synced to To Do successfully")
        return True

    def run(self) -> bool:
        if not MENU_FILE.exists():
            logger.error("Menu file not found")
            return False

        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            menu = json.load(f)

        logger.info("Starting To Do sync")

        menu_synced = self.sync_menu(menu)
        shopping_synced = self.sync_shopping_list(menu)

        if menu_synced and shopping_synced:
            logger.info("To Do sync completed successfully")
            return True
        else:
            logger.warning("To Do sync completed with errors")
            return False


def test_sync(client_id: str, client_secret: str, tenant_id: str):
    syncer = ToDoSync(client_id, client_secret, tenant_id)

    if syncer.authenticate():
        logger.info("Authentication successful")
    else:
        logger.error("Authentication failed")
        return

    if MENU_FILE.exists():
        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            menu = json.load(f)
        syncer.sync_menu(menu)
    else:
        logger.warning("Menu file not found for testing")


if __name__ == '__main__':
    import os
    client_id = os.getenv('AZURE_CLIENT_ID', '')
    client_secret = os.getenv('AZURE_CLIENT_SECRET', '')
    tenant_id = os.getenv('AZURE_TENANT_ID', '')

    logger.info("Testing To Do sync")
    test_sync(client_id, client_secret, tenant_id)
