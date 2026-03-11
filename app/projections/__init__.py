"""Projection handlers: register at startup via register_all_handlers()."""

import logging

from app.core.projections import get_registry

logger = logging.getLogger(__name__)


def register_all_handlers() -> None:
    """Import all handler modules so @projection decorators run. Call from lifespan."""
    from app.projections import audit

    get_registry().all()
    logger.debug("Loaded projection handler module: %s", audit.__name__)
