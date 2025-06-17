"""
Logger setup for the application.
"""
import logging
import os
from logging.handlers import RotatingFileHandler
from pathlib import Path

def setup_logger(app_name: str = 'app') -> logging.Logger:
    """
    Set up application logging with the following features:
    - Logs to both file and console
    - Uses rotating file handler to manage log file size
    - Includes timestamp, log level, and message
    - Creates log directory if it doesn't exist
    """
    logger = logging.getLogger(app_name)
    logger.setLevel(logging.DEBUG)  # Set root logger to DEBUG

    # Create formatters and add it to the handlers
    log_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
    )

    # Set up file handler with rotation
    log_dir = Path(__file__).parent.parent / 'logs'
    log_dir.mkdir(exist_ok=True)
    log_file = log_dir / 'app.log'
    
    file_handler = RotatingFileHandler(
        log_file,
        maxBytes=10000000,  # 10MB
        backupCount=5
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(log_format)

    # Set up console handler
    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(log_format)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger
