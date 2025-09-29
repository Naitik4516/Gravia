
import logging
from logging.handlers import RotatingFileHandler
import sys

def setup_logging():
    # Create a logger
    logger = logging.getLogger('gravia')
    logger.setLevel(logging.DEBUG)  # Set the lowest level to capture all messages

    # Create a formatter
    formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')

    # Create a rotating file handler
    # This will create up to 5 log files, each 2MB in size.
    file_handler = RotatingFileHandler('gravia.log', maxBytes=2*1024*1024, backupCount=5)
    file_handler.setLevel(logging.INFO)  # Log INFO and above to the file
    file_handler.setFormatter(formatter)

    # Create a console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG)  # Log DEBUG and above to the console
    console_handler.setFormatter(formatter)

    # Add the handlers to the logger
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)

    return logger

# Create a logger instance to be used throughout the application
logger = setup_logging()
