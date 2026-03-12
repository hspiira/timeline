"""Background job: projection engine (Phase 5)."""

import asyncio
import logging

from fastapi import FastAPI

from app.core.config import get_settings
from app.core.projections import get_registry
from app.infrastructure.persistence.database import AsyncSessionLocal
from app.infrastructure.persistence.repositories import (
    EventRepository,
    ProjectionRepository,
)
from app.infrastructure.services.projection_engine import ProjectionEngine

logger = logging.getLogger(__name__)


async def run_projection_engine_job(_app: FastAPI) -> None:
    """Loop: every interval, advance all active projections; one transaction per cycle.

    Uses a fresh session per cycle. Cancelling the task stops the loop.
    """
    settings = get_settings()
    await asyncio.sleep(10)  # initial delay so server can settle

    if AsyncSessionLocal is None:
        logger.error("Projection engine: database not configured")
        return

    registry = get_registry()
    interval = settings.projection_engine_interval_seconds
    batch_size = settings.projection_engine_batch_size

    while True:
        try:
            async with AsyncSessionLocal() as db:
                async with db.begin():
                    projection_repo = ProjectionRepository(db)
                    event_repo = EventRepository(db)

                    engine = ProjectionEngine(
                        projection_repo=projection_repo,
                        event_repo=event_repo,
                        registry=registry,
                        interval_seconds=interval,
                        batch_size=batch_size,
                    )
                    await engine.run_once()
        except asyncio.CancelledError:
            logger.info("Projection engine cancelled, shutting down")
            raise
        except Exception:
            logger.exception("Projection engine cycle error")

        await asyncio.sleep(interval)
