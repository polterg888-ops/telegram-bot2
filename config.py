# config.py
import os
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")
TIMEZONE = os.getenv("TIMEZONE", "Europe/Moscow")
ADMINS = [int(x) for x in os.getenv("ADMINS", "").split(",") if x.strip()]
TIME_SLOT_MINUTES = 60  # 1 час интервалы
ENABLE_ADMIN_NOTIFICATIONS = True