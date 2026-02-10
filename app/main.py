"""FastAPI application entry point.

Wiring only: lifespan, exception handlers, middleware, routers.
No business logic here (SRP). See app.core.lifespan and app.core.exception_handlers.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded

from app.api.v1 import api_router
from app.core.config import get_settings

settings = get_settings()
from app.core.limiter import limiter
from app.core.exception_handlers import register_exception_handlers
from app.core.lifespan import create_lifespan
from app.middleware import (
    CorrelationIDMiddleware,
    RequestIDMiddleware,
    RequestSizeLimitMiddleware,
    SecurityHeadersMiddleware,
    TimeoutMiddleware,
)
from app.pages import render_root_page

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    debug=settings.debug,
    lifespan=create_lifespan,
)

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

register_exception_handlers(app)

# Middleware: first added = outermost. Order: timeout → size limit → request ID → correlation ID → security → CORS.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.allowed_origins.split(",") if o.strip()],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(
    CorrelationIDMiddleware,
    header_name=settings.correlation_id_header,
)
app.add_middleware(RequestIDMiddleware, header_name=settings.request_id_header)
app.add_middleware(RequestSizeLimitMiddleware, max_bytes=settings.max_upload_size)
app.add_middleware(TimeoutMiddleware, timeout_seconds=settings.request_timeout_seconds)

app.include_router(api_router, prefix="/api/v1")


@app.get("/", response_class=HTMLResponse)
def root() -> HTMLResponse:
    """Landing page with links to API documentation."""
    return HTMLResponse(content=render_root_page(settings.app_name))
