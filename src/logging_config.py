import logging
from logging import Logger
from logging.handlers import RotatingFileHandler
import os
import json
from typing import Optional

LOG_FILE = os.getenv("LOG_FILE", "project.log")


def _is_true(value: Optional[str]) -> bool:
    """Return True for common truthy strings (1, true, yes, on)."""
    if value is None:
        return False
    return str(value).strip().lower() in {"1", "true", "yes", "on"}


class JsonFormatter(logging.Formatter):
    """Simple JSON line formatter.

    Produces a compact JSON object with keys: time, level, name, message.
    Respects datefmt for the time field, similar to logging.Formatter.
    """

    def format(self, record: logging.LogRecord) -> str:
        timestamp = self.formatTime(record, self.datefmt)
        payload = {
            "time": timestamp,
            "level": record.levelname,
            "name": record.name,
            "message": record.getMessage(),
        }
        if record.exc_info:
            payload["exc_info"] = self.formatException(record.exc_info)
        return json.dumps(payload, ensure_ascii=False)


def setup_logger(name: str, log_file: str = LOG_FILE, level: str = "INFO") -> Logger:
    """
    Set up a logger with a rotating file handler. Level can be set via LOG_LEVEL env or parameter.

    When LOG_JSON is set to a truthy value (1/true/yes/on), logs are written as JSON lines.
    Otherwise, a plain text pipe-delimited formatter is used (backward compatible default).

    Only adds a handler once per logger name; the logger level is (re)applied on each call.
    """
    logger = logging.getLogger(name)

    # Determine log level on each call (env overrides parameter)
    log_level_str = os.getenv("LOG_LEVEL", level).upper()
    log_level = getattr(logging, log_level_str, logging.INFO)

    # Only attach a handler once to avoid duplicates
    if not logger.handlers:
        handler = RotatingFileHandler(
            log_file,
            maxBytes=2 * 1024 * 1024,
            backupCount=2,
            encoding="utf-8",
        )
        if _is_true(os.getenv("LOG_JSON")):
            formatter = JsonFormatter(datefmt="%Y-%m-%d %H:%M:%S")
        else:
            formatter = logging.Formatter(
                '%(asctime)s | %(levelname)s | %(name)s | %(message)s',
                datefmt='%Y-%m-%d %H:%M:%S',
            )
        handler.setFormatter(formatter)
        logger.addHandler(handler)

    logger.setLevel(log_level)
    return logger


def get_logger(name: str) -> Logger:
    """Convenience factory reading env: LOG_FILE, LOG_LEVEL, LOG_JSON.

    - LOG_FILE (default 'project.log')
    - LOG_LEVEL (default 'INFO')
    - LOG_JSON (true-like for JSON lines)
    """
    log_file = os.getenv("LOG_FILE", LOG_FILE)
    level = os.getenv("LOG_LEVEL", "INFO")
    return setup_logger(name, log_file=log_file, level=level)