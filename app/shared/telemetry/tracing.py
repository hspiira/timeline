"""Utility functions and decorators for distributed tracing."""

import asyncio
from collections.abc import Callable
from functools import wraps

from opentelemetry import trace
from opentelemetry.trace import Status, StatusCode


def traced(
    operation_name: str | None = None,
    attributes: dict | None = None,
) -> Callable:
    """Decorator to create a span for a function (sync or async).

    Args:
        operation_name: Span name (defaults to module.funcname).
        attributes: Optional dict of attributes to set on the span.

    Returns:
        Decorated function.
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                _set_safe_span_attrs(span, kwargs)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            tracer = trace.get_tracer(__name__)
            span_name = operation_name or f"{func.__module__}.{func.__name__}"
            with tracer.start_as_current_span(span_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                _set_safe_span_attrs(span, kwargs)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise

        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper

    return decorator


def _set_safe_span_attrs(span: trace.Span, kwargs: dict) -> None:
    """Set span attributes from kwargs, excluding sensitive keys."""
    sensitive = {"password", "token", "secret"}
    for key, value in kwargs.items():
        if not key.startswith("_") and key not in sensitive:
            span.set_attribute(f"arg.{key}", str(value))


def add_span_attributes(**attributes: str | int | float | bool) -> None:
    """Add attributes to the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: dict | None = None) -> None:
    """Add an event to the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes=attributes or {})


def set_span_error(exception: Exception) -> None:
    """Mark the current span as error and record the exception."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.set_status(Status(StatusCode.ERROR, str(exception)))
        span.record_exception(exception)


def get_trace_id() -> str | None:
    """Return the current trace ID as 32-char hex, or None."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.trace_id, "032x")
    return None


def get_span_id() -> str | None:
    """Return the current span ID as 16-char hex, or None."""
    span = trace.get_current_span()
    if span:
        ctx = span.get_span_context()
        if ctx.is_valid:
            return format(ctx.span_id, "016x")
    return None


class TracedOperation:
    """Context manager for creating a traced operation (sync or async)."""

    def __init__(self, operation_name: str, attributes: dict | None = None) -> None:
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.tracer = trace.get_tracer(__name__)
        self.span: trace.Span | None = None

    def __enter__(self) -> "TracedOperation":
        self.span = self.tracer.start_span(self.operation_name)
        self.span.__enter__()
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        return self

    def __exit__(
        self, exc_type: type | None, exc_val: BaseException | None, exc_tb: object
    ) -> None:
        if self.span is None:
            return
        if exc_type is not None and exc_val is not None:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        self.span.__exit__(exc_type, exc_val, exc_tb)

    async def __aenter__(self) -> "TracedOperation":
        return self.__enter__()

    async def __aexit__(
        self,
        exc_type: type | None,
        exc_val: BaseException | None,
        exc_tb: object,
    ) -> None:
        self.__exit__(exc_type, exc_val, exc_tb)
