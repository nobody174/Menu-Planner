import json
import logging
import smtplib
import os
from pathlib import Path
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('logs/email_notifier.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

DATA_DIR = Path('data')
MENU_FILE = DATA_DIR / 'weekly_menu.json'

class EmailNotifier:
    def __init__(self, sender_email: str, sender_password: str, recipient_email: str, smtp_server: str = 'smtp.gmail.com', smtp_port: int = 587):
        self.sender_email = sender_email
        self.sender_password = sender_password
        self.recipient_email = recipient_email
        self.smtp_server = smtp_server
        self.smtp_port = smtp_port

    def generate_menu_email(self, menu: dict) -> str:
        dinners = menu.get('dinners', [])
        shopping = menu.get('shopping_list', {})

        dinners_text = '\n'.join([
            f"{d['day']:12} | {d['title']:50} | {d['time_minutes']} min"
            for d in dinners
        ])

        shopping_text = ''
        for category, items in shopping.items():
            if items:
                shopping_text += f"\n{category}:\n"
                for item in items:
                    shopping_text += f"  - {item['ingredient']}: {item['quantity']} {item['unit']}\n"

        html = f"""
        <html>
            <head>
                <style>
                    body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; }}
                    h1 {{ color: #2c3e50; }}
                    h2 {{ color: #3498db; margin-top: 1.5em; }}
                    table {{ border-collapse: collapse; width: 100%; margin: 1em 0; }}
                    td {{ padding: 0.5em; border-bottom: 1px solid #ddd; }}
                    .footer {{ color: #999; font-size: 0.9em; margin-top: 2em; }}
                </style>
            </head>
            <body>
                <h1>Din Ukemeny</h1>
                <p>Hei Vartdal og familie,</p>
                <p>Her er menyen for denne uken ({menu.get('week_start')} til {menu.get('week_end')}):</p>

                <h2>Meny (Mandag - Lørdag)</h2>
                <pre>{dinners_text}</pre>

                <h2>Handleliste</h2>
                <pre>{shopping_text}</pre>

                <p>
                    <a href="http://10.0.0.54:5000">Se all oppskrifter her</a> |
                    <a href="http://10.0.0.54:5000/shopping">Se handleliste</a>
                </p>

                <p>Handlelisten er også oppdatert i Microsoft To Do appen din.</p>

                <p>Lykke til med matlagingen!</p>

                <div class="footer">
                    <p>Denne emailen ble generert av Pi-Menu. Never too late to give up! ⚰️</p>
                </div>
            </body>
        </html>
        """

        return html

    def send_email(self, subject: str, html_body: str) -> bool:
        try:
            message = MIMEMultipart('alternative')
            message['Subject'] = subject
            message['From'] = self.sender_email
            message['To'] = self.recipient_email

            part = MIMEText(html_body, 'html', 'utf-8')
            message.attach(part)

            with smtplib.SMTP(self.smtp_server, self.smtp_port) as server:
                server.starttls()
                server.login(self.sender_email, self.sender_password)
                server.send_message(message)

            logger.info(f"Email sent to {self.recipient_email}")
            return True

        except Exception as e:
            logger.error(f"Failed to send email: {e}")
            return False

    def send_menu_email(self, menu: dict) -> bool:
        week_start = menu.get('week_start', 'this week')
        subject = f"Din ukemeny - {week_start}"

        html_body = self.generate_menu_email(menu)

        return self.send_email(subject, html_body)

    def run(self) -> bool:
        if not MENU_FILE.exists():
            logger.error("Menu file not found")
            return False

        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            menu = json.load(f)

        logger.info("Sending menu email notification")
        return self.send_menu_email(menu)


def test_email(sender_email: str, sender_password: str, recipient_email: str):
    notifier = EmailNotifier(sender_email, sender_password, recipient_email)

    if MENU_FILE.exists():
        with open(MENU_FILE, 'r', encoding='utf-8') as f:
            menu = json.load(f)
        success = notifier.send_menu_email(menu)
        if success:
            logger.info("Test email sent successfully")
        else:
            logger.error("Failed to send test email")
    else:
        logger.warning("Menu file not found for testing")


if __name__ == '__main__':
    sender_email = os.getenv('EMAIL_USERNAME', 'your-email@gmail.com')
    sender_password = os.getenv('EMAIL_PASSWORD', 'your-app-password')
    recipient_email = os.getenv('EMAIL_RECIPIENT', 'vartdal@gmail.com')

    logger.info("Testing email notifier")
    test_email(sender_email, sender_password, recipient_email)
