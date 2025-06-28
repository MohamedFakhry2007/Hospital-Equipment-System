import os

class Config:
    SECRET_KEY = 'a_very_secret_key'  # Change this to a random, long string in production

    # Database configuration
    basedir = os.path.abspath(os.path.dirname(__file__))
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        f'sqlite:///{os.path.join(basedir, "..", "instance", "app.db")}'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ECHO = False  # Set to True for SQL query logging

    DATA_DIR = 'data'

    SCHEDULER_ENABLED = False
    # ADMIN_USERNAME = "admin"
    # ADMIN_PASSWORD = "password"

    PPM_JSON_PATH = 'data/ppm.json'
    OCM_JSON_PATH = 'data/ocm.json'
    TRAINING_JSON_PATH = 'data/training.json'
    SETTINGS_JSON_PATH = 'data/settings.json'
    AUDIT_LOG_JSON_PATH = 'data/audit_log.json'
    PUSH_SUBSCRIPTIONS_JSON_PATH = 'data/push_subscriptions.json'

    # Session Configuration
    SESSION_TYPE = 'filesystem'
    SESSION_FILE_DIR = './flask_session_data'
    SESSION_PERMANENT = True # Sessions will be permanent until they expire
    PERMANENT_SESSION_LIFETIME = 86400 # 24 hours in seconds
    SESSION_USE_SIGNER = True # Sign the session cookie for extra security



