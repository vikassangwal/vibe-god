"""
Timeout Management with Deadline Propagation
"""
import asyncio
from dataclasses import dataclass
from typing import Callable, Any, Optional, Dict
from functools import wraps
from contextvars import ContextVar
import time
import logging

logger = logging.getLogger(__name__)

# Context variable for deadline propagation
_deadline_var: ContextVar[Optional[float]] = ContextVar("deadline", default=None)


@dataclass
class TimeoutConfig:
    """Configuration for timeout."""
    timeout: float = 30.0  # Default timeout in seconds
    deadline_aware: bool = True  # Propagate deadlines to child calls


class TimeoutError(Exception):
    """Raised when operation times out."""
    def __init__(self, operation: str, timeout: float, elapsed: float):
        self.operation = operation
        self.timeout = timeout
        self.elapsed = elapsed
        super().__init__(
            f"Operation '{operation}' timed out after {elapsed:.2f}s (limit: {timeout}s)"
        )


def get_deadline() -> Optional[float]:
    """Get current deadline from context."""
    return _deadline_var.get()


def set_deadline(deadline: Optional[float]) -> None:
    """Set deadline in context."""
    _deadline_var.set(deadline)


def calculate_remaining_timeout(configured_timeout: float) -> float:
    """
    Calculate remaining timeout based on deadline.

    Args:
        configured_timeout: Configured timeout

    Returns:
        Effective timeout (minimum of configured and deadline-based)
    """
    deadline = get_deadline()
    if deadline is None:
        return configured_timeout

    remaining = deadline - time.monotonic()
    if remaining <= 0:
        raise TimeoutError("deadline_check", configured_timeout, configured_timeout - remaining)

    return min(configured_timeout, remaining)


async def timeout(
    func: Callable,
    *args: Any,
    timeout_seconds: float,
    operation_name: Optional[str] = None,
    **kwargs: Any,
) -> Any:
    """
    Execute function with timeout.

    Args:
        func: Async function to execute
        *args: Positional arguments
        timeout_seconds: Timeout in seconds
        operation_name: Name for error messages
        **kwargs: Keyword arguments

    Returns:
        Function result

    Raises:
        TimeoutError: If timeout exceeded
    """
    name = operation_name or getattr(func, "__name__", "unknown")
    effective_timeout = calculate_remaining_timeout(timeout_seconds)

    try:
        return await asyncio.wait_for(
            func(*args, **kwargs),
            timeout=effective_timeout,
        )
    except asyncio.TimeoutError:
        elapsed = time.monotonic() - (time.monotonic() - effective_timeout)
        raise TimeoutError(name, timeout_seconds, elapsed)


def with_timeout(
    timeout_seconds: float,
    operation_name: Optional[str] = None,
) -> Callable:
    """
    Decorator to add timeout to a function.

    Args:
        timeout_seconds: Timeout in seconds
        operation_name: Name for error messages

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await timeout(
                func,
                *args,
                timeout_seconds=timeout_seconds,
                operation_name=operation_name or func.__name__,
                **kwargs,
            )
        return wrapper
    return decorator


class TimeoutManager:
    """Manages timeouts for multiple operations."""

    def __init__(self, default_timeout: float = 30.0):
        self.default_timeout = default_timeout
        self._timeouts: Dict[str, float] = {}

    def set_timeout(self, operation: str, timeout: float) -> None:
        """Set timeout for specific operation."""
        self._timeouts[operation] = timeout

    def get_timeout(self, operation: str) -> float:
        """Get timeout for operation."""
        return self._timeouts.get(operation, self.default_timeout)

    async def execute(
        self,
        operation: str,
        func: Callable,
        *args: Any,
        **kwargs: Any,
    ) -> Any:
        """Execute with operation-specific timeout."""
        timeout_seconds = self.get_timeout(operation)
        return await timeout(
            func,
            *args,
            timeout_seconds=timeout_seconds,
            operation_name=operation,
            **kwargs,
        )

    def with_deadline(self, deadline: float) -> "DeadlineContext":
        """Create a deadline context."""
        return DeadlineContext(deadline)


class DeadlineContext:
    """Context manager for deadline propagation."""

    def __init__(self, deadline: float):
        self.deadline = deadline
        self.previous_deadline: Optional[float] = None

    def __enter__(self):
        self.previous_deadline = get_deadline()
        # Use the earlier deadline if one already exists
        if self.previous_deadline is not None:
            set_deadline(min(self.previous_deadline, self.deadline))
        else:
            set_deadline(self.deadline)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        set_deadline(self.previous_deadline)


async def run_with_deadline(
    deadline: float,
    func: Callable,
    *args: Any,
    **kwargs: Any,
) -> Any:
    """Run function with explicit deadline."""
    async with DeadlineContext(deadline):
        return await func(*args, **kwargs)


# Timeout policies for common operations
class TimeoutPolicies:
    """Predefined timeout policies."""

    # HTTP requests
    HTTP_REQUEST = 30.0
    HTTP_CONNECT = 10.0
    HTTP_READ = 60.0

    # Database
    DB_QUERY = 10.0
    DB_TRANSACTION = 30.0
    DB_MIGRATION = 300.0

    # External APIs
    EXTERNAL_API = 30.0
    EXTERNAL_API_LONG = 120.0

    # Cache
    CACHE_GET = 1.0
    CACHE_SET = 2.0

    # Message queue
    MQ_PUBLISH = 5.0
    MQ_CONSUME = 30.0

    # File operations
    FILE_READ = 10.0
    FILE_WRITE = 10.0
    FILE_UPLOAD = 120.0

    # Authentication
    AUTH_VERIFY = 5.0
    AUTH_TOKEN_REFRESH = 10.0

    # Background jobs
    JOB_SHORT = 60.0
    JOB_MEDIUM = 300.0
    JOB_LONG = 3600.0


def get_timeout_policy(operation_type: str) -> float:
    """Get timeout for operation type."""
    return getattr(TimeoutPolicies, operation_type.upper(), TimeoutPolicies.HTTP_REQUEST)