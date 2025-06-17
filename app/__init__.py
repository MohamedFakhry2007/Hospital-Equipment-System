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
    """Start the email scheduler in a background thread."""
    from app.services.email_service import EmailService
    
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    
    try:
        loop.run_until_complete(EmailService.run_scheduler())
    except Exception as e:
        logging.error(f"Error in email scheduler: {str(e)}")
    finally:
        loop.close()
