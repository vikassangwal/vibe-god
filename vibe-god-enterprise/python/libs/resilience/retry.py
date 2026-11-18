"""
Retry Policy with Exponential Backoff and Jitter
"""
import asyncio
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Tuple, Type, List
from functools import wraps
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class BackoffStrategy(str, Enum):
    FIXED = "fixed"
    LINEAR = "linear"
    EXPONENTIAL = "exponential"
    EXPONENTIAL_JITTER = "exponential_jitter"
    DECORRELATED_JITTER = "decorrelated_jitter"


@dataclass
class RetryConfig:
    """Configuration for retry policy."""
    max_attempts: int = 3
    base_delay: float = 1.0          # Base delay in seconds
    max_delay: float = 60.0          # Maximum delay cap
    strategy: BackoffStrategy = BackoffStrategy.EXPONENTIAL_JITTER
    jitter_factor: float = 0.1       # Jitter as fraction of delay
    retry_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    exclude_exceptions: Tuple[Type[Exception], ...] = ()
    should_retry: Optional[Callable[[Exception], bool]] = None
    on_retry: Optional[Callable[[Exception, int, float], Any]] = None  # callback(exception, attempt, delay)


@dataclass
class RetryAttempt:
    """Information about a retry attempt."""
    attempt: int
    exception: Exception
    delay: float
    timestamp: float = field(default_factory=time.time)


@dataclass
class RetryResult:
    """Result of retry execution."""
    success: bool
    result: Any = None
    exception: Optional[Exception] = None
    attempts: List[RetryAttempt] = field(default_factory=list)
    total_time: float = 0.0


def calculate_delay(
    attempt: int,
    config: RetryConfig,
    previous_delay: Optional[float] = None,
) -> float:
    """
    Calculate delay for next retry attempt.

    Args:
        attempt: Current attempt number (0-indexed)
        config: Retry configuration
        previous_delay: Previous delay (for decorrelated jitter)

    Returns:
        Delay in seconds
    """
    if config.strategy == BackoffStrategy.FIXED:
        delay = config.base_delay
    elif config.strategy == BackoffStrategy.LINEAR:
        delay = config.base_delay * (attempt + 1)
    elif config.strategy == BackoffStrategy.EXPONENTIAL:
        delay = config.base_delay * (2 ** attempt)
    elif config.strategy == BackoffStrategy.EXPONENTIAL_JITTER:
        delay = config.base_delay * (2 ** attempt)
        # Add jitter
        jitter = delay * config.jitter_factor
        delay = delay + random.uniform(-jitter, jitter)
    elif config.strategy == BackoffStrategy.DECORRELATED_JITTER:
        if previous_delay is None:
            delay = config.base_delay
        else:
            delay = random.uniform(config.base_delay, previous_delay * 3)
    else:
        delay = config.base_delay

    # Cap at max_delay
    return min(max(delay, 0), config.max_delay)


def should_retry_exception(exception: Exception, config: RetryConfig) -> bool:
    """Determine if exception should trigger a retry."""
    # Check excluded exceptions first
    if isinstance(exception, config.exclude_exceptions):
        return False

    # Check custom predicate
    if config.should_retry is not None:
        return config.should_retry(exception)

    # Check retry exceptions
    return isinstance(exception, config.retry_exceptions)


async def retry_with_policy(
    func: Callable,
    *args: Any,
    config: Optional[RetryConfig] = None,
    **kwargs: Any,
) -> RetryResult:
    """
    Execute function with retry policy.

    Args:
        func: Async function to execute
        *args: Positional arguments
        **kwargs: Keyword arguments
        config: Retry configuration

    Returns:
        RetryResult with execution details
    """
    if config is None:
        config = RetryConfig()

    result = RetryResult(success=False)
    start_time = time.time()
    previous_delay = None

    for attempt in range(config.max_attempts):
        attempt_start = time.time()

        try:
            result.result = await func(*args, **kwargs)
            result.success = True
            result.total_time = time.time() - start_time
            return result

        except Exception as e:
            attempt_time = time.time() - attempt_start
            retry_attempt = RetryAttempt(
                attempt=attempt,
                exception=e,
                delay=0,
                timestamp=attempt_start,
            )
            result.attempts.append(retry_attempt)

            # Check if we should retry
            if attempt < config.max_attempts - 1 and should_retry_exception(e, config):
                delay = calculate_delay(attempt, config, previous_delay)
                retry_attempt.delay = delay
                previous_delay = delay

                logger.warning(
                    f"Retry attempt {attempt + 1}/{config.max_attempts} for {func.__name__}: "
                    f"{type(e).__name__}: {e}. Waiting {delay:.2f}s"
                )

                # Call on_retry callback
                if config.on_retry:
                    try:
                        await config.on_retry(e, attempt, delay)
                    except Exception:
                        pass  # Ignore callback errors

                await asyncio.sleep(delay)
                continue
            else:
                # No more retries or shouldn't retry
                result.exception = e
                result.total_time = time.time() - start_time
                return result

    result.total_time = time.time() - start_time
    return result


def retry(
    config: Optional[RetryConfig] = None,
    **config_kwargs: Any,
) -> Callable:
    """
    Decorator to add retry logic to a function.

    Args:
        config: RetryConfig instance
        **config_kwargs: RetryConfig parameters as kwargs

    Returns:
        Decorated function
    """
    if config is None:
        config = RetryConfig(**config_kwargs)

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            result = await retry_with_policy(func, *args, config=config, **kwargs)
            if result.success:
                return result.result
            else:
                raise result.exception

        # Attach config for inspection
        wrapper.retry_config = config
        return wrapper
    return decorator


class RetryPolicy:
    """Retry policy with state tracking."""

    def __init__(self, config: RetryConfig):
        self.config = config
        self.history: List[RetryResult] = []
        self._lock = asyncio.Lock()

    async def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function with retry policy."""
        result = await retry_with_policy(func, *args, config=self.config, **kwargs)

        async with self._lock:
            self.history.append(result)
            # Keep only last 1000 results
            if len(self.history) > 1000:
                self.history = self.history[-1000:]

        if result.success:
            return result.result
        else:
            raise result.exception

    def get_stats(self) -> dict:
        """Get retry statistics."""
        if not self.history:
            return {
                "total_executions": 0,
                "success_rate": 0,
                "avg_attempts": 0,
                "avg_time": 0,
            }

        total = len(self.history)
        successes = sum(1 for r in self.history if r.success)
        total_attempts = sum(len(r.attempts) + 1 for r in self.history)
        total_time = sum(r.total_time for r in self.history)

        return {
            "total_executions": total,
            "success_rate": successes / total,
            "avg_attempts": total_attempts / total,
            "avg_time": total_time / total,
            "recent_failures": [
                {"exception": type(r.exception).__name__, "attempts": len(r.attempts)}
                for r in self.history[-10:] if not r.success
            ],
        }

    def clear_history(self) -> None:
        """Clear execution history."""
        self.history.clear()


# Predefined retry policies
DEFAULT_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    strategy=BackoffStrategy.EXPONENTIAL_JITTER,
)

AGGRESSIVE_RETRY = RetryConfig(
    max_attempts=5,
    base_delay=0.5,
    max_delay=10.0,
    strategy=BackoffStrategy.EXPONENTIAL_JITTER,
)

CONSERVATIVE_RETRY = RetryConfig(
    max_attempts=2,
    base_delay=2.0,
    max_delay=60.0,
    strategy=BackoffStrategy.EXPONENTIAL,
)

NETWORK_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=1.0,
    max_delay=30.0,
    strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retry_exceptions=(
        ConnectionError,
        TimeoutError,
        OSError,
    ),
)

DATABASE_RETRY = RetryConfig(
    max_attempts=3,
    base_delay=0.5,
    max_delay=10.0,
    strategy=BackoffStrategy.EXPONENTIAL_JITTER,
    retry_exceptions=(
        ConnectionError,
        TimeoutError,
    ),
    exclude_exceptions=(
        # Don't retry integrity errors, etc.
    ),
)