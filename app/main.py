import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import HTMLResponse

from app.api.v1 import api_router
from app.core.config import settings
from app.infrastructure.firebase import init_firebase
from app.pages import render_root_page

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    fb_initialized = init_firebase()
    logger.info("Firebase initialized: %s", fb_initialized)
    from app.api.websocket import ConnectionManager

    app.state.ws_manager = ConnectionManager()
    if settings.redis_enabled:
        from app.infrastructure.cache.redis_cache import CacheService

        cache = CacheService()
        await cache.connect()
        app.state.cache = cache
    else:
        app.state.cache = None
    yield
    # Shutdown
    if getattr(app.state, "cache", None) is not None:
        await app.state.cache.disconnect()


app = FastAPI(
    title=settings.app_name,
    debug=settings.debug,
    lifespan=lifespan,
)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Landing page with links to API documentation."""
    return HTMLResponse(content=render_root_page(settings.app_name))
