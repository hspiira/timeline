"""Centralized exception handlers for the FastAPI app.

Register with register_exception_handlers(app). Maps domain and framework
exceptions to HTTP responses (SRP, OCP for adding new handlers).
"""

import logging
from typing import Any

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.core.config import get_settings
from app.domain.exceptions import TimelineException

logger = logging.getLogger(__name__)

# Map domain error_code to HTTP status when applicable
_ERROR_CODE_STATUS: dict[str, int] = {
    "RESOURCE_NOT_FOUND": 404,
    "TENANT_NOT_FOUND": 404,
    "TENANT_ALREADY_EXISTS": 409,
    "AUTHENTICATION_ERROR": 401,
    "AUTHORIZATION_ERROR": 403,
    "VALIDATION_ERROR": 400,
    "PERMISSION_DENIED": 403,
    "CHAIN_INTEGRITY_ERROR": 400,
    "SCHEMA_VALIDATION_ERROR": 400,
}


def _timeline_exception_handler(
    request: Request, exc: TimelineException
) -> JSONResponse:
    """Return JSON from TimelineException.to_dict() with appropriate status code."""
    status = _ERROR_CODE_STATUS.get(exc.error_code, 400)
    return JSONResponse(
        status_code=status,
        content=exc.to_dict(),
    )


def _validation_exception_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Return 422 with validation error details."""
    return JSONResponse(
        status_code=422,
        content={
            "error": "VALIDATION_ERROR",
            "message": "Request validation failed",
            "details": exc.errors(),
        },
    )


def _http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Return JSON for Starlette HTTP exceptions (status + detail)."""
    return JSONResponse(
        status_code=exc.status_code,
        content={"error": "HTTP_ERROR", "message": exc.detail},
    )


def _generic_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Return 500; include detail only when debug is True."""
    logger.exception("Unhandled exception: %s", exc)
    settings = get_settings()
    detail: Any = str(exc) if settings.debug else "Internal server error"
    return JSONResponse(
        status_code=500,
        content={"error": "INTERNAL_ERROR", "message": detail},
    )


def register_exception_handlers(app: FastAPI) -> None:
    """Register all exception handlers on the FastAPI app.

    Call once after creating the app. Handlers: TimelineException (and
    subclasses), RequestValidationError, StarletteHTTPException, generic Exception.
    """
    app.add_exception_handler(TimelineException, _timeline_exception_handler)
    app.add_exception_handler(RequestValidationError, _validation_exception_handler)
    app.add_exception_handler(StarletteHTTPException, _http_exception_handler)
    app.add_exception_handler(Exception, _generic_exception_handler)
