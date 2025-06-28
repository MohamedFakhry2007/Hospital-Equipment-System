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
import threading

from flask import Flask, render_template, request, current_app, send_from_directory
from flask_session import Session

from app.config import Config
from app.utils.logger_setup import setup_logger
from app.extensions import db, login_manager, migrate, csrf


# ----------------- Scheduler Thread Functions -----------------

def start_email_scheduler():
    """Start the email scheduler in a separate thread."""
    from app.services.email_service import EmailService
    logger = logging.getLogger(__name__)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("Background thread for scheduler is starting.")
        loop.run_until_complete(EmailService.run_scheduler_async_loop())
    except Exception as e:
        logger.error(f"Exception in the email scheduler thread: {str(e)}", exc_info=True)
    finally:
        if loop.is_running():
            loop.stop()
        loop.close()
        logger.info("Background thread for email scheduler has finished.")


def start_push_notification_scheduler():
    """Start the push notification scheduler in a separate thread."""
    from app.services.push_notification_service import PushNotificationService
    logger = logging.getLogger(__name__)
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        logger.info("Background thread for Push Notification scheduler is starting.")
        loop.run_until_complete(PushNotificationService.run_scheduler_async_loop())
    except Exception as e:
        logger.error(f"Exception in the Push Notification scheduler thread: {str(e)}", exc_info=True)
    finally:
        if loop.is_running():
            loop.stop()
        loop.close()
        logger.info("Background thread for Push Notification scheduler has finished.")


# ---------------------- App Factory ----------------------

def create_app():
    """Create and configure the Flask application."""
    app = Flask(__name__, static_folder='static')

    # Load configuration
    app.config.from_object(Config)
    
    # Serve static files in development
    if app.debug:  # This will be True in development mode
        @app.route('/static/<path:path>')
        def send_static(path):
            return send_from_directory('static', path)

    # Initialize extensions
    db.init_app(app)
    migrate.init_app(app, db)
    login_manager.init_app(app)
    login_manager.login_view = 'auth.login'
    csrf.init_app(app)
    Session(app)

    # Set up logging
    logger = setup_logger('app')
    app.logger = logger
    logger.info('Initializing application')

    # Ensure data directory exists
    os.makedirs(Config.DATA_DIR, exist_ok=True)

    # Import models after initializing db
    from app.models.user import User, Role, Permission
    from app.models.ppm_equipment import PPMEquipment  # Import PPMEquipment model

    # Register blueprints
    from app.routes.views import views_bp
    from app.routes.api import api_bp
    from app.routes.admin import admin_bp
    from app.routes.training import training_bp
    from app.auth.routes import auth_bp

    app.register_blueprint(views_bp)
    app.register_blueprint(api_bp, url_prefix='/api')
    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(training_bp)

    # Initialize CLI commands
    from app.cli import init_app as init_cli
    init_cli(app)

    # Start background schedulers if enabled
    if Config.SCHEDULER_ENABLED:
        email_scheduler_thread = threading.Thread(target=start_email_scheduler, daemon=True)
        email_scheduler_thread.start()
        logger.info("Email scheduler thread initiated from create_app.")

        push_scheduler_thread = threading.Thread(target=start_push_notification_scheduler, daemon=True)
        push_scheduler_thread.start()
        logger.info("Push Notification scheduler thread initiated from create_app.")
    else:
        logger.info("Schedulers are disabled in config (SCHEDULER_ENABLED=False).")

    # Update PPM statuses on startup
    from app.services.data_service import DataService
    try:
        logger.info("Attempting to update PPM statuses on application startup...")
        DataService.update_all_ppm_statuses()
        logger.info("PPM statuses update process completed.")
    except Exception as e:
        logger.error(f"Error during initial PPM status update: {str(e)}", exc_info=True)

    # Error handlers
    app.register_error_handler(404, page_not_found)
    app.register_error_handler(500, internal_server_error)

    logger.info('Application initialization complete')
    return app


# ------------------- Error Handlers --------------------

def page_not_found(e):
    current_app.logger.warning(f"404 Not Found: {request.path}")
    return render_template("404.html"), 404

def internal_server_error(e):
    current_app.logger.error(f"500 Internal Server Error: {e}", exc_info=True)
    return render_template("500.html"), 500
