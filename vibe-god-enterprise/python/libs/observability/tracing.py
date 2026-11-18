"""
Distributed Tracing with OpenTelemetry
"""
import os
from typing import Optional, Callable, Any
from functools import wraps
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.aiohttp_client import AioHttpClientInstrumentor
from opentelemetry.instrumentation.psycopg2 import Psycopg2Instrumentor
from opentelemetry.instrumentation.redis import RedisInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
from opentelemetry.instrumentation.httpx import HTTPXClientInstrumentor
from opentelemetry.propagate import set_global_textmap
from opentelemetry.propagators.b3 import B3MultiFormat
from opentelemetry.trace import Status, StatusCode


_tracer_provider: Optional[TracerProvider] = None


def init_tracing(
    service_name: str = "vibe-god",
    otlp_endpoint: Optional[str] = None,
    service_version: str = "unknown",
    enable_console_export: bool = False,
) -> TracerProvider:
    """
    Initialize OpenTelemetry tracing.

    Args:
        service_name: Name of the service
        otlp_endpoint: OTLP collector endpoint (e.g., "http://jaeger:4317")
        service_version: Service version
        enable_console_export: Whether to export to console (for debugging)

    Returns:
        Configured TracerProvider
    """
    global _tracer_provider

    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    _tracer_provider = TracerProvider(resource=resource)
    trace.set_tracer_provider(_tracer_provider)

    # Configure exporters
    if otlp_endpoint:
        otlp_exporter = OTLPSpanExporter(endpoint=otlp_endpoint, insecure=True)
        _tracer_provider.add_span_processor(BatchSpanProcessor(otlp_exporter))

    if enable_console_export:
        console_exporter = ConsoleSpanExporter()
        _tracer_provider.add_span_processor(BatchSpanProcessor(console_exporter))

    # Set propagator for distributed tracing (B3 for compatibility)
    set_global_textmap(B3MultiFormat())

    # Auto-instrument common libraries
    _auto_instrument()

    return _tracer_provider


def _auto_instrument() -> None:
    """Auto-instrument common libraries."""
    try:
        FastAPIInstrumentor.instrument()
    except Exception:
        pass
    try:
        AioHttpClientInstrumentor.instrument()
    except Exception:
        pass
    try:
        Psycopg2Instrumentor.instrument()
    except Exception:
        pass
    try:
        RedisInstrumentor.instrument()
    except Exception:
        pass
    try:
        RequestsInstrumentor.instrument()
    except Exception:
        pass
    try:
        HTTPXClientInstrumentor.instrument()
    except Exception:
        pass


def get_tracer(name: str) -> trace.Tracer:
    """
    Get a tracer instance.

    Args:
        name: Tracer name (typically __name__)

    Returns:
        OpenTelemetry tracer
    """
    return trace.get_tracer(name, version="1.0.0")


def trace_operation(
    operation_name: str,
    attributes: Optional[dict] = None,
    tracer_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to trace an async function.

    Args:
        operation_name: Name of the operation
        attributes: Additional span attributes
        tracer_name: Tracer name (defaults to caller's module)

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(tracer_name or func.__module__)
            with tracer.start_as_current_span(operation_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = await func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


def trace_sync_operation(
    operation_name: str,
    attributes: Optional[dict] = None,
    tracer_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to trace a synchronous function.

    Args:
        operation_name: Name of the operation
        attributes: Additional span attributes
        tracer_name: Tracer name (defaults to caller's module)

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            tracer = get_tracer(tracer_name or func.__module__)
            with tracer.start_as_current_span(operation_name) as span:
                if attributes:
                    for key, value in attributes.items():
                        span.set_attribute(key, value)
                try:
                    result = func(*args, **kwargs)
                    span.set_status(Status(StatusCode.OK))
                    return result
                except Exception as e:
                    span.set_status(Status(StatusCode.ERROR, str(e)))
                    span.record_exception(e)
                    raise
        return wrapper
    return decorator


class TraceContext:
    """Context manager for manual span management."""

    def __init__(
        self,
        operation_name: str,
        attributes: Optional[dict] = None,
        tracer_name: Optional[str] = None,
    ):
        self.operation_name = operation_name
        self.attributes = attributes or {}
        self.tracer_name = tracer_name
        self.span = None

    def __enter__(self):
        tracer = get_tracer(self.tracer_name or "manual")
        self.span = tracer.start_span(self.operation_name)
        for key, value in self.attributes.items():
            self.span.set_attribute(key, value)
        self.span.__enter__()
        return self.span

    def __exit__(self, exc_type, exc_val, exc_tb):
        if exc_val:
            self.span.set_status(Status(StatusCode.ERROR, str(exc_val)))
            self.span.record_exception(exc_val)
        else:
            self.span.set_status(Status(StatusCode.OK))
        self.span.__exit__(exc_type, exc_val, exc_tb)


def add_span_attributes(attributes: dict) -> None:
    """Add attributes to the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        for key, value in attributes.items():
            span.set_attribute(key, value)


def add_span_event(name: str, attributes: Optional[dict] = None) -> None:
    """Add an event to the current span."""
    span = trace.get_current_span()
    if span and span.is_recording():
        span.add_event(name, attributes or {})