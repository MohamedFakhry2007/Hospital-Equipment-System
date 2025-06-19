"""
Main entry point for the Hospital Equipment Maintenance Management System.
(Primarily for local development if not using Gunicorn directly)
"""

import logging
import os
from app import create_app # create_app now handles scheduler initialization
from app.config import Config

logger = logging.getLogger(__name__)


def main():
    """
    Main function to run the Flask development server.
    The scheduler is now started within create_app, so it doesn't need
    to be explicitly started here.
    This entry point is mostly for development.
    For production, Gunicorn calls create_app() directly via run.sh.
    """
    app = create_app() # This will also attempt to start the scheduler
    
    # Use the correct port from Render or a local default
    port = int(os.environ.get("PORT", 5001)) # Changed default to 5001 to avoid conflict if run locally

    # When running with `python app/main.py` for local dev:
    # - debug=True will enable the reloader.
    # - use_reloader=True (default when debug=True) can cause issues with schedulers
    #   starting twice. The scheduler in EmailService has a lock to prevent the actual
    #   loop from running twice, but it's cleaner to manage this.
    #   However, since create_app now starts the thread, and Gunicorn is the target,
    #   we might want to disable reloader here or be mindful of the scheduler's lock.
    #   For Gunicorn, run.sh does not use this main() function.
    
    if Config.SCHEDULER_ENABLED:
        logger.info("Scheduler is configured to be enabled. It will be started by create_app().")
    else:
        logger.info("Scheduler is configured to be disabled.")

    logger.info(f"Starting Flask development server on http://0.0.0.0:{port}")
    # Note: Flask's reloader can cause the scheduler thread to be started twice
    # if not careful. The lock in EmailService should prevent the actual job loop
    # from running multiple times. For production, Gunicorn handles workers.
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=port, use_reloader=False) # Explicitly set use_reloader


if __name__ == '__main__':
    # This ensures that if someone runs `python app/main.py`, it starts the dev server.
    # Gunicorn does not use this; it uses the `app:create_app()` factory.
    main()
