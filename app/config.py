class Config:
    SECRET_KEY = 'a_very_secret_key'  # Change this to a random, long string in production

    DATA_DIR = 'data'

    SCHEDULER_ENABLED = False
    ADMIN_USERNAME = "admin"
    ADMIN_PASSWORD = "password"

    PPM_JSON_PATH = 'data/ppm.json'
    OCM_JSON_PATH = 'data/ocm.json'
    TRAINING_JSON_PATH = 'data/training.json'
    SETTINGS_JSON_PATH = 'data/settings.json'
    AUDIT_LOG_JSON_PATH = 'data/audit_log.json'
    PUSH_SUBSCRIPTIONS_JSON_PATH = 'data/push_subscriptions.json'
