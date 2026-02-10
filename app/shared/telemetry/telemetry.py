"""OpenTelemetry distributed tracing configuration.

Uses OTLP exporter only (no deprecated Jaeger Thrift exporter).
Jaeger is supported via its OTLP endpoint (port 4317).
"""

import logging
import threading

from fastapi import FastAPI
from opentelemetry import trace
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.logging import LoggingInstrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.sqlalchemy import SQLAlchemyInstrumentor
from opentelemetry.sdk.resources import SERVICE_NAME, SERVICE_VERSION, Resource
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.sdk.trace.sampling import TraceIdRatioBased
from sqlalchemy.ext.asyncio import AsyncEngine

logger = logging.getLogger(__name__)


class TelemetryConfig:
    """OpenTelemetry configuration for distributed tracing.

    Supports FastAPI, SQLAlchemy, Redis, and logging instrumentation.
    Exporters: console, otlp, jaeger, or none.
    """

    def __init__(
        self,
        service_name: str,
        service_version: str,
        enabled: bool = True,
        environment: str = "development",
    ) -> None:
        """Initialize telemetry config.

        Args:
            service_name: Service name for resource attributes.
            service_version: Version for resource attributes.
            enabled: Whether tracing is enabled.
            environment: Deployment environment (e.g. development, staging, production).
        """
        self.service_name = service_name
        self.service_version = service_version
        self.enabled = enabled
        self.environment = environment
        self.tracer_provider: TracerProvider | None = None

    def setup_telemetry(
        self,
        exporter_type: str = "console",
        otlp_endpoint: str | None = None,
        jaeger_endpoint: str | None = None,
        sample_rate: float = 1.0,
    ) -> TracerProvider | None:
        """Initialize OpenTelemetry tracing and set global tracer provider.

        Args:
            exporter_type: "console", "otlp", "jaeger", or "none".
            otlp_endpoint: OTLP gRPC endpoint (e.g. http://localhost:4317).
            jaeger_endpoint: Jaeger OTLP host (we use gRPC on port 4317).
            sample_rate: Sampling rate 0.0–1.0.

        Returns:
            TracerProvider or None if disabled.
        """
        if not self.enabled:
            logger.info("Telemetry disabled")
            return None
        try:
            resource = Resource(
                attributes={
                    SERVICE_NAME: self.service_name,
                    SERVICE_VERSION: self.service_version,
                    "deployment.environment": self.environment,
                }
            )
            sampler = TraceIdRatioBased(sample_rate)
            self.tracer_provider = TracerProvider(resource=resource, sampler=sampler)

            if exporter_type == "console":
                exporter = ConsoleSpanExporter()
                logger.info("Using Console span exporter (development mode)")
            elif exporter_type == "otlp" and otlp_endpoint:
                use_insecure = otlp_endpoint.startswith("http://")
                exporter = OTLPSpanExporter(
                    endpoint=otlp_endpoint, insecure=use_insecure
                )
                logger.info("Using OTLP span exporter: %s", otlp_endpoint)
            elif exporter_type == "jaeger" and jaeger_endpoint:
                # Jaeger accepts OTLP on port 4317 (gRPC); use OTLP instead of deprecated Jaeger exporter
                endpoint = f"{jaeger_endpoint}:4317"
                exporter = OTLPSpanExporter(
                    endpoint=endpoint,
                    insecure=True,
                )
                logger.info("Using OTLP span exporter for Jaeger: %s", endpoint)
            elif exporter_type == "none":
                logger.info("Telemetry enabled but no exporter configured")
                trace.set_tracer_provider(self.tracer_provider)
                return self.tracer_provider
            else:
                logger.warning(
                    "Unknown exporter type '%s', using console", exporter_type
                )
                exporter = ConsoleSpanExporter()

            self.tracer_provider.add_span_processor(BatchSpanProcessor(exporter))
            trace.set_tracer_provider(self.tracer_provider)
            logger.info(
                "OpenTelemetry initialized: service=%s, version=%s, exporter=%s",
                self.service_name,
                self.service_version,
                exporter_type,
            )
            return self.tracer_provider
        except Exception as e:
            logger.exception("Failed to initialize telemetry: %s", e)
            return None

    def instrument_fastapi(self, app: FastAPI) -> None:
        """Instrument FastAPI (requests, duration, status, exceptions)."""
        if not self.enabled or not self.tracer_provider:
            return
        try:
            FastAPIInstrumentor.instrument_app(
                app,
                tracer_provider=self.tracer_provider,
                excluded_urls="/health,/metrics",
            )
            logger.info("FastAPI instrumentation enabled")
        except Exception as e:
            logger.exception("Failed to instrument FastAPI: %s", e)

    def instrument_sqlalchemy(self, engine: AsyncEngine) -> None:
        """Instrument SQLAlchemy (queries, duration)."""
        if not self.enabled or not self.tracer_provider:
            return
        try:
            SQLAlchemyInstrumentor().instrument(
                engine=engine.sync_engine,
                tracer_provider=self.tracer_provider,
                enable_commenter=True,
            )
            logger.info("SQLAlchemy instrumentation enabled")
        except Exception as e:
            logger.exception("Failed to instrument SQLAlchemy: %s", e)

    def instrument_redis(self) -> None:
        """Instrument Redis client (commands, duration)."""
        if not self.enabled or not self.tracer_provider:
            return
        try:
            RedisInstrumentor().instrument(tracer_provider=self.tracer_provider)
            logger.info("Redis instrumentation enabled")
        except Exception as e:
            logger.exception("Failed to instrument Redis: %s", e)

    def instrument_logging(self) -> None:
        """Instrument Python logging with trace context (trace_id, span_id)."""
        if not self.enabled or not self.tracer_provider:
            return
        try:
            LoggingInstrumentor().instrument(
                tracer_provider=self.tracer_provider,
                set_logging_format=True,
            )
            logger.info("Logging instrumentation enabled")
        except Exception as e:
            logger.exception("Failed to instrument logging: %s", e)

    def shutdown(self) -> None:
        """Shutdown tracer provider and flush remaining spans."""
        if self.tracer_provider:
            try:
                self.tracer_provider.shutdown()
                logger.info("Telemetry shutdown complete")
            except Exception as e:
                logger.exception("Error during telemetry shutdown: %s", e)


_telemetry: TelemetryConfig | None = None
_telemetry_lock = threading.RLock()


def get_telemetry() -> TelemetryConfig | None:
    """Return the global telemetry instance (set at startup).

    Thread-safe: reads are protected by a module-level RLock.
    """
    with _telemetry_lock:
        return _telemetry


def set_telemetry(telemetry: TelemetryConfig) -> None:
    """Set the global telemetry instance.

    Thread-safe: writes are protected by a module-level RLock.
    Typically called once at startup before any concurrent access.
    """
    global _telemetry
    with _telemetry_lock:
        _telemetry = telemetry


def get_tracer(name: str) -> trace.Tracer:
    """Return a tracer for creating custom spans (e.g. get_tracer(__name__))."""
    return trace.get_tracer(name)
