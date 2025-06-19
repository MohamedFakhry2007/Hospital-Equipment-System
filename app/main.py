"""
Main entry point for the Hospital Equipment Maintenance Management System.
"""

import logging
import threading
import os
from app import create_app, start_email_scheduler
from app.config import Config

logger = logging.getLogger(__name__)


def main():
    app = create_app()
    
    if Config.SCHEDULER_ENABLED:
        threading.Thread(target=start_email_scheduler, daemon=True).start()
        app.logger.info("Email scheduler started in background thread")
    
    # Use the correct port from Render
    port = int(os.environ.get("PORT", 5000))
    # Disable reloader to prevent multiple scheduler instances during development
    app.run(debug=Config.DEBUG, host="0.0.0.0", port=port, use_reloader=False)


if __name__ == '__main__':
    main()
