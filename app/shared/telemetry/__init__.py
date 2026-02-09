"""Shared telemetry: logging setup, OpenTelemetry config, and tracing helpers."""

from app.shared.telemetry.logging import get_logger, setup_logging
from app.shared.telemetry.telemetry import (
    TelemetryConfig,
    get_telemetry,
    get_tracer,
    set_telemetry,
)
from app.shared.telemetry.tracing import (
    TracedOperation,
    add_span_attributes,
    add_span_event,
    get_span_id,
    get_trace_id,
    set_span_error,
    traced,
)

__all__ = [
    "setup_logging",
    "get_logger",
    "TelemetryConfig",
    "get_telemetry",
    "set_telemetry",
    "get_tracer",
    "traced",
    "add_span_attributes",
    "add_span_event",
    "set_span_error",
    "get_trace_id",
    "get_span_id",
    "TracedOperation",
]
