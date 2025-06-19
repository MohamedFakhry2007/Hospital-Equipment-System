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

from flask import Flask
from app.utils.logger_setup import setup_logger
from app.config import Config


def create_app():
    """Create and configure the Flask application.
    
    Returns:
        Flask application instance
    """
    # Create app
    app = Flask(__name__)
    
    # Set up logging
    logger = setup_logger('app')
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
    
    logger.info('Application initialization complete')
    
    return app


def start_email_scheduler():
    """Start the email scheduler."""
    # This function is intended to be run in a separate thread by app/main.py
    from app.services.email_service import EmailService
    
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
        logger.info("Background thread for scheduler has finished.")
