import logging
import sys
import os

def setup_logger(name: str = None, log_file: str = "project.log"):
    """
    Sets up a logger based on an environment variable LOG_LEVEL. Falls back to INFO if not set.
    """
    log_level_str = os.getenv("LOG_LEVEL", "INFO").upper()
    log_level = getattr(logging, log_level_str, logging.INFO)
    LOG_FORMAT = "%(asctime)s [%(levelname)s] %(message)s"

    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    file_handler = logging.FileHandler(log_file)
    file_handler.setFormatter(logging.Formatter(LOG_FORMAT))

    logger = logging.getLogger(name)
    logger.setLevel(log_level)
    logger.handlers = []  # Clear existing handlers
    logger.addHandler(console_handler)
    logger.addHandler(file_handler)
    return logger
