"""Logging configuration for the application."""

import logging
import sys


def setup_logging(level: str = "INFO") -> logging.Logger:
    """Configure structured console logging."""
    log_format = "%(asctime)s [%(levelname)s] [%(name)s]: %(message)s"
    date_format = "%Y-%m-%d %H:%M:%S"

    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format=log_format,
        datefmt=date_format,
        handlers=[logging.StreamHandler(sys.stdout)],
        force=True,
    )

    logger = logging.getLogger("support_inbox_assistant")
    logger.setLevel(getattr(logging, level.upper(), logging.INFO))
    return logger


logger = setup_logging()
