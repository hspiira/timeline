"""Logging configuration for the application."""

import logging
import sys

from app.core.config import get_settings


def setup_logging() -> None:
    """Configure application-wide logging.

    Level is DEBUG when settings.debug is True, otherwise INFO.
    Output goes to stdout.
    """
    settings = get_settings()
    log_level = logging.DEBUG if settings.debug else logging.INFO
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[logging.StreamHandler(sys.stdout)],
    )


def get_logger(name: str) -> logging.Logger:
    """Return a logger for the given module name.

    Args:
        name: Usually __name__ of the calling module.

    Returns:
        Logger instance.
    """
    return logging.getLogger(name)
