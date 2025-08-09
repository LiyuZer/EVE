import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
import os

LOG_FILE = os.getenv("LOG_FILE", "project.log")


def setup_logger(name: str, log_file: str = LOG_FILE, level: str = "INFO") -> Logger:
    """
    Set up a logger with a rotating file handler. Set level via LOG_LEVEL env var or parameter.
    """
    logger = logging.getLogger(name)
    if not logger.handlers:
        log_level = os.getenv("LOG_LEVEL", level).upper()
        handler = RotatingFileHandler(log_file, maxBytes=2 * 1024 * 1024, backupCount=2)
        formatter = logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s | %(message)s', datefmt='%Y-%m-%d %H:%M:%S'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
        logger.setLevel(getattr(logging, log_level, logging.INFO))
    return logger
