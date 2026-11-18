"""
Metrics Collection with Prometheus and OpenTelemetry
"""
import os
import time
from typing import Optional, Dict, Any, Callable
from functools import wraps
from prometheus_client import Counter, Histogram, Gauge, Summary, CollectorRegistry, generate_latest
from prometheus_client.core import CollectorRegistry
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response
from opentelemetry import metrics
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.exporter.otlp.proto.grpc.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.resources import Resource, SERVICE_NAME, SERVICE_VERSION


# Prometheus metrics (for /metrics endpoint)
_prometheus_registry: Optional[CollectorRegistry] = None
_meter_provider: Optional[MeterProvider] = None

# Common metrics
http_requests_total = Counter(
    "http_requests_total",
    "Total HTTP requests",
    ["method", "endpoint", "status"],
    registry=None  # Will be set in init_metrics
)

http_request_duration_seconds = Histogram(
    "http_request_duration_seconds",
    "HTTP request duration in seconds",
    ["method", "endpoint"],
    buckets=[0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0],
    registry=None
)

http_request_size_bytes = Histogram(
    "http_request_size_bytes",
    "HTTP request size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=None
)

http_response_size_bytes = Histogram(
    "http_response_size_bytes",
    "HTTP response size in bytes",
    ["method", "endpoint"],
    buckets=[100, 1000, 10000, 100000, 1000000],
    registry=None
)

active_connections = Gauge(
    "active_connections",
    "Number of active connections",
    registry=None
)

# Business metrics
operations_total = Counter(
    "operations_total",
    "Total operations performed",
    ["operation", "status"],
    registry=None
)

operation_duration_seconds = Histogram(
    "operation_duration_seconds",
    "Operation duration in seconds",
    ["operation"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
    registry=None
)

queue_depth = Gauge(
    "queue_depth",
    "Current queue depth",
    ["queue_name"],
    registry=None
)

cache_hits_total = Counter(
    "cache_hits_total",
    "Total cache hits",
    ["cache_name"],
    registry=None
)

cache_misses_total = Counter(
    "cache_misses_total",
    "Total cache misses",
    ["cache_name"],
    registry=None
)

db_connections_active = Gauge(
    "db_connections_active",
    "Active database connections",
    registry=None
)

db_query_duration_seconds = Histogram(
    "db_query_duration_seconds",
    "Database query duration in seconds",
    ["query_type"],
    buckets=[0.001, 0.005, 0.01, 0.05, 0.1, 0.5, 1.0, 5.0],
    registry=None
)

external_api_calls_total = Counter(
    "external_api_calls_total",
    "Total external API calls",
    ["api", "endpoint", "status"],
    registry=None
)

external_api_duration_seconds = Histogram(
    "external_api_duration_seconds",
    "External API call duration in seconds",
    ["api", "endpoint"],
    buckets=[0.01, 0.05, 0.1, 0.5, 1.0, 5.0, 10.0, 30.0],
    registry=None
)


def init_metrics(
    service_name: str = "vibe-god",
    otlp_endpoint: Optional[str] = None,
    service_version: str = "unknown",
    export_interval_millis: int = 60000,
) -> MeterProvider:
    """
    Initialize OpenTelemetry metrics with Prometheus and OTLP export.

    Args:
        service_name: Service name
        otlp_endpoint: OTLP collector endpoint for metrics
        service_version: Service version
        export_interval_millis: Export interval in milliseconds

    Returns:
        Configured MeterProvider
    """
    global _prometheus_registry, _meter_provider

    # Create Prometheus registry
    _prometheus_registry = CollectorRegistry()

    # Register all metrics with Prometheus registry
    _register_prometheus_metrics()

    # Create OpenTelemetry MeterProvider
    resource = Resource.create({
        SERVICE_NAME: service_name,
        SERVICE_VERSION: service_version,
        "deployment.environment": os.getenv("ENVIRONMENT", "development"),
    })

    readers = []

    if otlp_endpoint:
        otlp_exporter = OTLPMetricExporter(endpoint=otlp_endpoint, insecure=True)
        readers.append(PeriodicExportingMetricReader(otlp_exporter, export_interval_millis=export_interval_millis))

    _meter_provider = MeterProvider(resource=resource, metric_readers=readers)
    metrics.set_meter_provider(_meter_provider)

    return _meter_provider


def _register_prometheus_metrics() -> None:
    """Register all metrics with Prometheus registry."""
    global _prometheus_registry
    if not _prometheus_registry:
        return

    metrics_list = [
        http_requests_total,
        http_request_duration_seconds,
        http_request_size_bytes,
        http_response_size_bytes,
        active_connections,
        operations_total,
        operation_duration_seconds,
        queue_depth,
        cache_hits_total,
        cache_misses_total,
        db_connections_active,
        db_query_duration_seconds,
        external_api_calls_total,
        external_api_duration_seconds,
    ]

    for metric in metrics_list:
        if hasattr(metric, '_registry') and metric._registry is None:
            # Re-create with registry
            pass  # Metrics are already registered globally


def get_meter(name: str) -> metrics.Meter:
    """
    Get an OpenTelemetry meter.

    Args:
        name: Meter name (typically __name__)

    Returns:
        OpenTelemetry meter
    """
    return metrics.get_meter(name, version="1.0.0")


def get_prometheus_registry() -> Optional[CollectorRegistry]:
    """Get the Prometheus registry for /metrics endpoint."""
    return _prometheus_registry


def generate_prometheus_metrics() -> bytes:
    """Generate Prometheus metrics in text format."""
    if _prometheus_registry:
        return generate_latest(_prometheus_registry)
    return b""


class MetricsMiddleware(BaseHTTPMiddleware):
    """Starlette/FastAPI middleware for HTTP metrics."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        start_time = time.time()
        method = request.method
        path = request.url.path

        # Track active connections
        active_connections.inc()

        try:
            response = await call_next(request)
            duration = time.time() - start_time
            status = response.status_code

            # Record metrics
            http_requests_total.labels(method=method, endpoint=path, status=status).inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)

            # Request/response size
            request_size = int(request.headers.get("content-length", 0))
            http_request_size_bytes.labels(method=method, endpoint=path).observe(request_size)

            return response
        except Exception as e:
            duration = time.time() - start_time
            http_requests_total.labels(method=method, endpoint=path, status=500).inc()
            http_request_duration_seconds.labels(method=method, endpoint=path).observe(duration)
            raise
        finally:
            active_connections.dec()


def record_operation(operation: str, status: str = "success") -> None:
    """Record an operation metric."""
    operations_total.labels(operation=operation, status=status).inc()


def record_operation_duration(operation: str, duration_seconds: float) -> None:
    """Record operation duration."""
    operation_duration_seconds.labels(operation=operation).observe(duration_seconds)


def record_queue_depth(queue_name: str, depth: int) -> None:
    """Record queue depth."""
    queue_depth.labels(queue_name=queue_name).set(depth)


def record_cache_hit(cache_name: str) -> None:
    """Record cache hit."""
    cache_hits_total.labels(cache_name=cache_name).inc()


def record_cache_miss(cache_name: str) -> None:
    """Record cache miss."""
    cache_misses_total.labels(cache_name=cache_name).inc()


def record_db_connection_active(count: int) -> None:
    """Record active DB connections."""
    db_connections_active.set(count)


def record_db_query_duration(query_type: str, duration_seconds: float) -> None:
    """Record DB query duration."""
    db_query_duration_seconds.labels(query_type=query_type).observe(duration_seconds)


def record_external_api_call(api: str, endpoint: str, status: str) -> None:
    """Record external API call."""
    external_api_calls_total.labels(api=api, endpoint=endpoint, status=status).inc()


def record_external_api_duration(api: str, endpoint: str, duration_seconds: float) -> None:
    """Record external API duration."""
    external_api_duration_seconds.labels(api=api, endpoint=endpoint).observe(duration_seconds)


# Decorators for automatic metrics
def track_operation(operation: str) -> Callable:
    """Decorator to track operation metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                record_operation(operation, "success")
                return result
            except Exception:
                record_operation(operation, "error")
                raise
            finally:
                record_operation_duration(operation, time.time() - start)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                record_operation(operation, "success")
                return result
            except Exception:
                record_operation(operation, "error")
                raise
            finally:
                record_operation_duration(operation, time.time() - start)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def track_db_query(query_type: str) -> Callable:
    """Decorator to track DB query metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return await func(*args, **kwargs)
            finally:
                record_db_query_duration(query_type, time.time() - start)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                return func(*args, **kwargs)
            finally:
                record_db_query_duration(query_type, time.time() - start)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator


def track_external_api(api: str, endpoint: str) -> Callable:
    """Decorator to track external API metrics."""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def async_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = await func(*args, **kwargs)
                record_external_api_call(api, endpoint, "success")
                return result
            except Exception:
                record_external_api_call(api, endpoint, "error")
                raise
            finally:
                record_external_api_duration(api, endpoint, time.time() - start)

        @wraps(func)
        def sync_wrapper(*args: Any, **kwargs: Any) -> Any:
            start = time.time()
            try:
                result = func(*args, **kwargs)
                record_external_api_call(api, endpoint, "success")
                return result
            except Exception:
                record_external_api_call(api, endpoint, "error")
                raise
            finally:
                record_external_api_duration(api, endpoint, time.time() - start)

        import asyncio
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        return sync_wrapper
    return decorator