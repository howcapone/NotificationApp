import os
from dotenv import load_dotenv
import bcrypt

load_dotenv()

TOKEN = os.getenv("telegram_token")
PASSWORD_HASH = os.getenv("PASSWORD_HASH").encode('utf-8')

WEB_SERVER_URL = os.getenv("WEB_SERVER_URL", "http://localhost:5000")

DB_CONFIG = {
    "server": "localhost\SQLEXPRESS",
    "database": "NotificationAPP"
}