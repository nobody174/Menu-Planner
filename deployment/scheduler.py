#
# Menu Planner - Weekly Meal Planner
# Creator: nobody174 (nobodylearn174@gmail.com)
# GitHub: https://github.com/nobody174/Menu-Planner
# License: MIT
#

import logging
import os
import sys
from pathlib import Path
from datetime import datetime
from apscheduler.schedulers.background import BackgroundScheduler

sys.path.insert(0, str(Path(__file__).parent.parent))

from core.menu_generator import MenuGenerator
from to_do_sync import ToDoSync
from email_notifier import EmailNotifier

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler("logs/scheduler.log"), logging.StreamHandler()],
)
logger = logging.getLogger(__name__)


class MenuScheduler:
    def __init__(self):
        self.scheduler = BackgroundScheduler()
        self.scheduler.daemon = True

        self.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "")

        self.email_username = os.getenv("EMAIL_USERNAME", "")
        self.email_password = os.getenv("EMAIL_PASSWORD", "")
        self.email_recipient = os.getenv("EMAIL_RECIPIENT", "your-email@gmail.com")

    def generate_menu(self):
        try:
            logger.info("=== GENERATING MENU ===")
            generator = MenuGenerator()
            menu = generator.run(num_dinners=5, save=True)
            logger.info(
                f"Menu generated successfully: {len(menu.get('dinners', []))} dinners"
            )
            return menu
        except Exception as e:
            logger.error(f"Failed to generate menu: {e}")
            return None

    def sync_to_do(self, menu):
        try:
            if not self.client_secret:
                logger.warning(
                    "Azure client secret not configured - skipping To Do sync"
                )
                return False

            logger.info("=== SYNCING TO DO ===")
            syncer = ToDoSync(self.client_id, self.client_secret, self.tenant_id)
            success = syncer.run()

            if success:
                logger.info("To Do sync completed successfully")
            else:
                logger.error("To Do sync failed")

            return success
        except Exception as e:
            logger.error(f"Failed to sync To Do: {e}")
            return False

    def send_email(self):
        try:
            if not self.email_username or not self.email_password:
                logger.warning("Email credentials not configured - skipping email")
                return False

            logger.info("=== SENDING EMAIL ===")
            from pathlib import Path
            import json

            menu_file = Path("data/weekly_menu.json")
            if not menu_file.exists():
                logger.error("Menu file not found for email")
                return False

            with open(menu_file, "r", encoding="utf-8") as f:
                menu = json.load(f)

            notifier = EmailNotifier(
                self.email_username, self.email_password, self.email_recipient
            )
            success = notifier.send_menu_email(menu)

            if success:
                logger.info("Email sent successfully")
            else:
                logger.error("Failed to send email")

            return success
        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def scheduled_job(self):
        try:
            logger.info("=" * 60)
            logger.info(f"Scheduled job started: {datetime.now()}")
            logger.info("=" * 60)

            menu = self.generate_menu()

            if menu:
                self.sync_to_do(menu)
                self.send_email()

            logger.info("=" * 60)
            logger.info(f"Scheduled job completed: {datetime.now()}")
            logger.info("=" * 60)

        except Exception as e:
            logger.error(f"Scheduled job failed: {e}")

    def start(self):
        try:
            logger.info("Starting scheduler...")

            self.scheduler.add_job(
                self.scheduled_job,
                trigger="cron",
                day_of_week="sat",
                hour=9,
                minute=0,
                id="menu_generation",
                name="Weekly menu generation and sync",
            )

            self.scheduler.start()
            logger.info("Scheduler started successfully. Waiting for Saturday 9 AM...")

            return True

        except Exception as e:
            logger.error(f"Failed to start scheduler: {e}")
            return False

    def run_once(self):
        logger.info("Running menu generation once (not scheduled)")
        self.scheduled_job()

    def shutdown(self):
        if self.scheduler.running:
            self.scheduler.shutdown()
            logger.info("Scheduler shut down")


def main():
    scheduler = MenuScheduler()

    scheduler.start()

    try:
        import time

        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        logger.info("Scheduler interrupted by user")
        scheduler.shutdown()


if __name__ == "__main__":
    main()
