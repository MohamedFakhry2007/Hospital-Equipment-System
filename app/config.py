import logging
import os
from pathlib import Path
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# Load environment variables from .env file
load_dotenv()
logger.debug("Environment variables loaded from .env file")

# Base directory
BASE_DIR = Path(__file__).resolve().parent.parent

# App configuration
class Config:
    # Flask configuration
    SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    
    # File paths
    DATA_DIR = os.path.join(BASE_DIR, "data")
    PPM_JSON_PATH = os.path.join(DATA_DIR, "ppm.json")
    OCM_JSON_PATH = os.path.join(DATA_DIR, "ocm.json")
    SETTINGS_JSON_PATH = os.path.join(DATA_DIR, "settings.json")
    
    # Mailjet configuration
    MAILJET_API_KEY = os.getenv("MAILJET_API_KEY", "")
    MAILJET_SECRET_KEY = os.getenv("MAILJET_SECRET_KEY", "")
    EMAIL_SENDER = os.getenv("EMAIL_SENDER", "mailjet@equipment.com")
    EMAIL_RECEIVER = os.getenv("EMAIL_RECEIVER", "")

    # Reminder configuration
    REMINDER_DAYS = int(os.getenv("REMINDER_DAYS", "60")) # Days ahead to look for maintenance tasks
    SCHEDULER_ENABLED = os.getenv("SCHEDULER_ENABLED", "True").lower() == "true" # Global switch for the email scheduler thread
    # SCHEDULER_INTERVAL (previously here) has been removed as the interval is now managed dynamically
    # via 'email_reminder_interval_minutes' in settings.json

    # VAPID Keys for Web Push Notifications
    VAPID_PRIVATE_KEY = os.getenv("VAPID_PRIVATE_KEY", "")
    VAPID_PUBLIC_KEY = os.getenv("VAPID_PUBLIC_KEY", "")
    VAPID_SUBJECT = os.getenv("VAPID_SUBJECT", "mailto:default@example.com") # Must be a mailto: or https: URL
