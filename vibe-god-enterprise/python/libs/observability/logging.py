"""
Structured Logging with OpenTelemetry Integration
"""
import os
import sys
import structlog
from typing import Any, Dict, Optional
from structlog.types import Processor
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporter
from opentelemetry.instrumentation.logging import LoggingInstrumentor


def configure_logging(
    level: str = "INFO",
    json_output: bool = True,
    service_name: str = "vibe-god",
    otlp_endpoint: Optional[str] = None,
) -> None:
    """
    Configure structured logging with OpenTelemetry integration.

    Args:
        level: Log level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
        json_output: Whether to output JSON (True) or human-readable (False)
        service_name: Service name for tracing
        otlp_endpoint: OTLP collector endpoint (e.g., "http://jaeger:4317")
    """
    # Configure structlog processors
    processors: list[Processor] = [
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        _add_service_context(service_name),
        _add_trace_context,
    ]

    if json_output:
        processors.append(structlog.processors.JSONRenderer())
    else:
        processors.append(structlog.dev.ConsoleRenderer(colors=True))

    structlog.configure(
        processors=processors,
        context_class=dict,
        logger_factory=structlog.stdlib.LoggerFactory(),
        wrapper_class=structlog.stdlib.BoundLogger,
        cache_logger_on_first_use=True,
    )

    # Configure standard library logging
    import logging
    logging.basicConfig(
        format="%(message)s",
        stream=sys.stdout,
        level=getattr(logging, level.upper()),
    )

    # Instrument logging with OpenTelemetry
    LoggingInstrumentor().instrument(set_logging_format=True)

    # Initialize tracing if endpoint provided
    if otlp_endpoint:
        init_tracing(service_name, otlp_endpoint)


def _add_service_context(service_name: str) -> Processor:
    """Add service context to all log entries."""
    def processor(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
        event_dict["service"] = service_name
        event_dict["environment"] = os.getenv("ENVIRONMENT", "development")
        event_dict["version"] = os.getenv("APP_VERSION", "unknown")
        return event_dict
    return processor


def _add_trace_context(logger: Any, method_name: str, event_dict: Dict[str, Any]) -> Dict[str, Any]:
    """Add trace context to log entries for correlation."""
    span = trace.get_current_span()
    if span and span.get_span_context().trace_id:
        event_dict["trace_id"] = format(span.get_span_context().trace_id, "032x")
        event_dict["span_id"] = format(span.get_span_context().span_id, "016x")
    return event_dict


def get_logger(name: str) -> structlog.BoundLogger:
    """
    Get a structured logger instance.

    Args:
        name: Logger name (typically __name__)

    Returns:
        Configured structlog logger
    """
    return structlog.get_logger(name)


class LogContext:
    """Context manager for adding structured context to logs."""

    def __init__(self, **kwargs: Any):
        self.context = kwargs
        self.token = None

    def __enter__(self):
        self.token = structlog.contextvars.bind_contextvars(**self.context)
        return self

    def __exit__(self, *args):
        if self.token:
            structlog.contextvars.unbind_contextvars(*self.context.keys())


def bind_context(**kwargs: Any) -> LogContext:
    """Bind context variables to current logging context."""
    return LogContext(**kwargs)


# Convenience functions for common log patterns
def log_operation_start(logger: structlog.BoundLogger, operation: str, **kwargs: Any) -> None:
    """Log operation start with consistent format."""
    logger.info("operation.started", operation=operation, **kwargs)


def log_operation_success(logger: structlog.BoundLogger, operation: str, duration_ms: float, **kwargs: Any) -> None:
    """Log operation success with duration."""
    logger.info("operation.succeeded", operation=operation, duration_ms=duration_ms, **kwargs)


def log_operation_failure(logger: structlog.BoundLogger, operation: str, error: Exception, duration_ms: float, **kwargs: Any) -> None:
    """Log operation failure with error details."""
    logger.error(
        "operation.failed",
        operation=operation,
        error_type=type(error).__name__,
        error_message=str(error),
        duration_ms=duration_ms,
        **kwargs
    )


def log_retry_attempt(logger: structlog.BoundLogger, operation: str, attempt: int, max_attempts: int, error: Exception, **kwargs: Any) -> None:
    """Log retry attempt."""
    logger.warning(
        "operation.retry",
        operation=operation,
        attempt=attempt,
        max_attempts=max_attempts,
        error_type=type(error).__name__,
        error_message=str(error),
        **kwargs
    )