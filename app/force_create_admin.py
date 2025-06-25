"""
Script to force create an admin user.
"""
from app import create_app, db
from app.models.user import User
from app.utils.logger_setup import setup_logger
import logging

logger = logging.getLogger('app')
logger.debug("[app.force_create_admin] Logging started for force_create_admin.py")

app = create_app()
logger.debug("[app.force_create_admin] Application created")

with app.app_context():
    logger.debug("[app.force_create_admin] Entered application context")
    username = "admin"
    password = "changeme"
    logger.info("[app.force_create_admin] Starting force_create_admin script")
    
    existing_user = User.query.filter_by(username=username).first()
    if existing_user:
        logger.info(f"[app.force_create_admin] User '{username}' already exists")
        print(f"User '{username}' already exists")
    else:
        try:
            logger.debug(f"[app.force_create_admin] Creating new admin user '{username}'")
            admin_user = User(username=username)
            logger.debug("[app.force_create_admin] User object created")
            admin_user.set_password(password)
            logger.debug("[app.force_create_admin] Password set for admin user")
            db.session.add(admin_user)
            logger.debug("[app.force_create_admin] Admin user added to database session")
            db.session.commit()
            logger.info(f"[app.force_create_admin] Admin user '{username}' created successfully with password '{password}'")
            print(f"Admin user '{username}' created with password '{password}'")
        except Exception as e:
            logger.error(f"[app.force_create_admin] Error creating admin user: {str(e)}")
            db.session.rollback()
            logger.debug("[app.force_create_admin] Database session rolled back due to error")
            print(f"Error creating admin user: {str(e)}")