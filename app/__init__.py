"""
Hospital Equipment Maintenance Management System.

This Flask application manages hospital equipment maintenance schedules
and provides email reminders for upcoming maintenance tasks.
"""
import asyncio
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path
import threading # Added import

from flask import Flask
from app.utils.logger_setup import setup_logger
from app.config import Config


# This function remains here as it's called by the thread started in create_app
def start_email_scheduler():
    """Start the email scheduler."""
    # This function is intended to be run in a separate thread
    from app.services.email_service import EmailService
    # Import PushNotificationService here or adjust as needed
    from app.services.push_notification_service import PushNotificationService


    logger = logging.getLogger(__name__) # Get a logger instance

    # Create a new event loop for this thread
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info("Background thread for scheduler is starting.")
        # EmailService.run_scheduler_async_loop will now handle the singleton check
        loop.run_until_complete(EmailService.run_scheduler_async_loop())
    except Exception as e:
        logger.error(f"Exception in the email scheduler thread: {str(e)}", exc_info=True)
    finally:
        if loop.is_running():
            loop.stop() # Stop the loop if it's still running
        loop.close()
        logger.info("Background thread for email scheduler has finished.")


# Function to start the Push Notification scheduler
def start_push_notification_scheduler():
    """Start the push notification scheduler."""
    # This function is intended to be run in a separate thread
    # EmailService import is above, ensure PushNotificationService is also imported
    from app.services.push_notification_service import PushNotificationService # Or ensure it's imported with EmailService

    logger = logging.getLogger(__name__)

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    try:
        logger.info("Background thread for Push Notification scheduler is starting.")
        # PushNotificationService.run_scheduler_async_loop will handle its own singleton check
        loop.run_until_complete(PushNotificationService.run_scheduler_async_loop())
    except Exception as e:
        logger.error(f"Exception in the Push Notification scheduler thread: {str(e)}", exc_info=True)
    finally:
        if loop.is_running():
            loop.stop()
        loop.close()
        logger.info("Background thread for Push Notification scheduler has finished.")


def create_app():
    """Create and configure the Flask application.
    
    Returns:
        Flask application instance
    """
    # Create app
    app = Flask(__name__)
    
    # Set up logging
    # Ensure logger is available for the scheduler start message
    logger = setup_logger('app') # Assuming this returns the 'app' logger configured
    app.logger = logger # Also assign to app.logger if not done by setup_logger implicitly for Flask
    logger.info('Initializing application')
    
    # Load configuration
    app.config.from_object(Config)
    
    # Ensure data directory exists
    os.makedirs(Config.DATA_DIR, exist_ok=True)
    
    # Register blueprints
    from app.routes.views import views_bp
    from app.routes.api import api_bp
    
    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix='/api')

    # Start the scheduler in a background thread if enabled
    # This will be called when Gunicorn workers are initialized.
    # The EmailService itself has a lock (_scheduler_running)
    # to prevent multiple instances of the scheduler loop from running.
    if Config.SCHEDULER_ENABLED:
        # Each Gunicorn worker will call create_app(), thus creating this thread.
        # The EmailService.run_scheduler_async_loop() has an internal lock
        # (_scheduler_lock and _scheduler_running) to ensure only one
        # instance of the actual scheduling logic runs across all workers/threads.
        email_scheduler_thread = threading.Thread(target=start_email_scheduler, daemon=True)
        email_scheduler_thread.start()
        logger.info("Email scheduler thread initiated from create_app.")

        # Start Push Notification Scheduler
        # Similar logic for PushNotificationService, assuming it has its own lock
        push_scheduler_thread = threading.Thread(target=start_push_notification_scheduler, daemon=True)
        push_scheduler_thread.start()
        logger.info("Push Notification scheduler thread initiated from create_app.")
    else:
        logger.info("Schedulers are disabled in config (SCHEDULER_ENABLED=False). Email and Push Notification schedulers will not start.")

    logger.info('Application initialization complete')
    
    # Update PPM statuses on startup
    # Ensure DataService is imported
    from app.services.data_service import DataService
    try:
        logger.info("Attempting to update PPM statuses on application startup...")
        DataService.update_all_ppm_statuses()
        logger.info("PPM statuses update process completed.")
    except Exception as e:
        logger.error(f"Error during initial PPM status update: {str(e)}", exc_info=True)

    return app
