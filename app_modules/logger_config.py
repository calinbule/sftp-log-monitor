import logging
import os
from datetime import datetime

def setup_logger(name):
    """Setup and return a logger with file and console handlers"""
    if not os.path.exists('internal-logs'):
        os.makedirs('internal-logs')

    logger = logging.getLogger(name)
    if not logger.handlers:  # Prevent duplicate handlers
        logger.setLevel(logging.DEBUG)

        current_date = datetime.now().strftime('%Y-%m-%d')
        file_handler = logging.FileHandler(f'internal-logs/{name}_{current_date}.log')
        console_handler = logging.StreamHandler()

        file_format = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        console_format = logging.Formatter('%(levelname)s - %(message)s')
        file_handler.setFormatter(file_format)
        console_handler.setFormatter(console_format)

        logger.addHandler(file_handler)
        logger.addHandler(console_handler)

    return logger
