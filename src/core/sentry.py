"""Sentry error tracking initialization."""

import logging
from typing import Optional
import sentry_sdk
from sentry_sdk.integrations.fastapi import FastApiIntegration

from src.core.config import settings

logger = logging.getLogger("support_inbox_assistant.sentry")


def init_sentry(dsn: Optional[str] = None) -> bool:
    """Initialize Sentry SDK if DSN is provided."""
    target_dsn = dsn or settings.sentry_dsn
    if not target_dsn:
        logger.info("Sentry DSN not configured; skipping Sentry initialization.")
        return False

    sentry_sdk.init(
        dsn=target_dsn,
        environment=settings.environment,
        integrations=[FastApiIntegration()],
        traces_sample_rate=1.0 if settings.debug else 0.1,
    )
    logger.info("Sentry initialized successfully.")
    return True
