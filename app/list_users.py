"""
Script to list all users in the database.
"""
from app import create_app, db
from app.models.user import User
import logging

logger = logging.getLogger('app')
logger.debug("[app.list_users] Logging started for list_users.py")

app = create_app()
logger.debug("[app.list_users] Application created")

with app.app_context():
    logger.debug("[app.list_users] Entered application context")
    users = User.query.all()
    logger.info("[app.list_users] Queried all users from database")
    
    if not users:
        logger.info("[app.list_users] No users found in the database")
        print("No users found in the database.")
    else:
        logger.debug(f"[app.list_users] Found {len(users)} users in the database")
        for user in users:
            logger.debug(f"[app.list_users] Processing user: {user.username}")
            print(f"Username: {user.username}")
        logger.info("[app.list_users] Completed listing all users")