"""
Structured logging configuration for VeriClaim AI MVP backend.

This module sets up Python logging with JSON structured logging
for better log aggregation and analysis in production.
"""

import logging
import logging.config
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict
from app.core.config import settings

# Anchored to the backend package root so log destination does not depend on
# the directory uvicorn happens to be launched from.
LOG_DIR = Path(__file__).resolve().parents[2] / "logs"


class JSONFormatter(logging.Formatter):
    """Custom JSON formatter for structured logging."""

    def format(self, record: logging.LogRecord) -> str:
        """Format log record as JSON."""
        log_data: Dict[str, Any] = {
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "message": record.getMessage(),
            "module": record.module,
            "function": record.funcName,
            "line": record.lineno,
        }

        # Add exception info if present
        if record.exc_info:
            log_data["exception"] = self.formatException(record.exc_info)

        # Add extra fields if present
        if hasattr(record, "extra_fields"):
            log_data.update(record.extra_fields)

        return json.dumps(log_data)


def configure_logging() -> None:
    """Configure structured logging for the application."""

    # Ensure logs directory exists
    LOG_DIR.mkdir(parents=True, exist_ok=True)

    # Windows consoles default to cp1252, which cannot encode the symbols used
    # in startup messages; without this the handler raises UnicodeEncodeError
    # and logging prints a traceback instead of the record.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            try:
                stream.reconfigure(encoding="utf-8", errors="replace")
            except (ValueError, OSError):  # detached or non-reconfigurable stream
                pass

    logging_config = {
        "version": 1,
        "disable_existing_loggers": False,
        "formatters": {
            "standard": {
                "format": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
                "datefmt": "%Y-%m-%d %H:%M:%S",
            },
            "json": {
                "()": JSONFormatter,
            },
        },
        "handlers": {
            "console": {
                "class": "logging.StreamHandler",
                "level": settings.log_level,
                "formatter": "json" if not settings.debug else "standard",
                "stream": "ext://sys.stdout",
            },
            "file": {
                "class": "logging.handlers.RotatingFileHandler",
                "level": settings.log_level,
                "formatter": "json",
                "filename": str(LOG_DIR / "vericlaim.log"),
                "maxBytes": 10485760,  # 10MB
                "backupCount": 10,
                "encoding": "utf-8",
            },
        },
        "loggers": {
            "": {  # Root logger
                "level": settings.log_level,
                "handlers": ["console", "file"],
            },
            "fastapi": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "uvicorn": {
                "level": "INFO",
                "handlers": ["console"],
                "propagate": False,
            },
            "sqlalchemy.engine": {
                "level": "WARNING",
                "handlers": ["console"],
                "propagate": False,
            },
        },
    }

    logging.config.dictConfig(logging_config)


def get_logger(name: str) -> logging.Logger:
    """
    Get a logger instance with the given name.

    Args:
        name: Logger name, typically __name__ from the calling module.

    Returns:
        Configured logger instance.
    """
    return logging.getLogger(name)
