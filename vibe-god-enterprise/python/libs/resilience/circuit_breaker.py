"""
Circuit Breaker Pattern Implementation
Prevents cascade failures by stopping calls to failing services.
"""
import asyncio
import time
from enum import Enum
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Type, Tuple, Dict
from functools import wraps
import logging

logger = logging.getLogger(__name__)


class CircuitState(Enum):
    CLOSED = "closed"      # Normal operation, requests go through
    OPEN = "open"          # Failing, requests blocked
    HALF_OPEN = "half_open"  # Testing if service recovered


class CircuitOpenError(Exception):
    """Raised when circuit breaker is open."""
    def __init__(self, circuit_name: str, retry_after: float):
        self.circuit_name = circuit_name
        self.retry_after = retry_after
        super().__init__(f"Circuit '{circuit_name}' is OPEN. Retry after {retry_after:.1f}s")


@dataclass
class CircuitBreakerConfig:
    """Configuration for circuit breaker."""
    failure_threshold: int = 5           # Failures before opening
    success_threshold: int = 2           # Successes in half-open before closing
    timeout: float = 30.0                # Seconds before half-open
    excluded_exceptions: Tuple[Type[Exception], ...] = ()  # Don't count these as failures
    expected_exceptions: Tuple[Type[Exception], ...] = (Exception,)  # Count these as failures
    fallback: Optional[Callable] = None  # Fallback function when open
    name: str = "default"


@dataclass
class CircuitBreakerMetrics:
    """Metrics for circuit breaker."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    fallback_calls: int = 0
    state_changes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    consecutive_failures: int = 0
    consecutive_successes: int = 0


class CircuitBreaker:
    """
    Circuit breaker implementation with three states:
    - CLOSED: Normal operation, counting failures
    - OPEN: Blocking requests, waiting for timeout
    - HALF_OPEN: Testing recovery with limited requests
    """

    def __init__(self, config: CircuitBreakerConfig):
        self.config = config
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._lock = asyncio.Lock()
        self._half_open_lock = asyncio.Lock()  # Limit concurrent half-open calls
        self._last_state_change = time.time()

    @property
    def name(self) -> str:
        return self.config.name

    async def call(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function with circuit breaker protection.

        Args:
            func: Async function to call
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            CircuitOpenError: If circuit is open
            Exception: Any exception from the function
        """
        async with self._lock:
            self.metrics.total_calls += 1

            # Check if we should transition from OPEN to HALF_OPEN
            if self.state == CircuitState.OPEN:
                if time.time() - self.metrics.last_failure_time >= self.config.timeout:
                    await self._transition_to_half_open()
                else:
                    self.metrics.rejected_calls += 1
                    retry_after = self.config.timeout - (time.time() - self.metrics.last_failure_time)
                    raise CircuitOpenError(self.name, retry_after)

            # In HALF_OPEN, limit concurrent requests
            if self.state == CircuitState.HALF_OPEN:
                # Allow only one request at a time in half-open
                pass  # The lock below handles this

        # Execute the function
        try:
            if self.state == CircuitState.HALF_OPEN:
                async with self._half_open_lock:
                    result = await func(*args, **kwargs)
            else:
                result = await func(*args, **kwargs)

            await self._on_success()
            return result

        except self.config.excluded_exceptions:
            # Excluded exceptions don't count as failures
            raise
        except self.config.expected_exceptions as e:
            await self._on_failure()
            raise

    async def _on_success(self) -> None:
        """Handle successful call."""
        async with self._lock:
            self.metrics.successful_calls += 1
            self.metrics.last_success_time = time.time()
            self.metrics.consecutive_failures = 0

            if self.state == CircuitState.HALF_OPEN:
                self.metrics.consecutive_successes += 1
                if self.metrics.consecutive_successes >= self.config.success_threshold:
                    await self._transition_to_closed()

    async def _on_failure(self) -> None:
        """Handle failed call."""
        async with self._lock:
            self.metrics.failed_calls += 1
            self.metrics.last_failure_time = time.time()
            self.metrics.consecutive_successes = 0
            self.metrics.consecutive_failures += 1

            if self.state == CircuitState.HALF_OPEN:
                # Any failure in half-open goes back to open
                await self._transition_to_open()
            elif self.state == CircuitState.CLOSED:
                if self.metrics.consecutive_failures >= self.config.failure_threshold:
                    await self._transition_to_open()

    async def _transition_to_open(self) -> None:
        """Transition to OPEN state."""
        if self.state != CircuitState.OPEN:
            logger.warning(f"Circuit '{self.name}' OPENED after {self.metrics.consecutive_failures} failures")
            self.state = CircuitState.OPEN
            self.metrics.state_changes += 1
            self._last_state_change = time.time()

    async def _transition_to_half_open(self) -> None:
        """Transition to HALF_OPEN state."""
        logger.info(f"Circuit '{self.name}' entering HALF_OPEN state")
        self.state = CircuitState.HALF_OPEN
        self.metrics.consecutive_successes = 0
        self.metrics.state_changes += 1
        self._last_state_change = time.time()

    async def _transition_to_closed(self) -> None:
        """Transition to CLOSED state."""
        logger.info(f"Circuit '{self.name}' CLOSED (recovered)")
        self.state = CircuitState.CLOSED
        self.metrics.consecutive_failures = 0
        self.metrics.consecutive_successes = 0
        self.metrics.state_changes += 1
        self._last_state_change = time.time()

    def get_state(self) -> CircuitState:
        """Get current circuit state."""
        return self.state

    def get_metrics(self) -> Dict[str, Any]:
        """Get circuit breaker metrics."""
        return {
            "name": self.name,
            "state": self.state.value,
            "total_calls": self.metrics.total_calls,
            "successful_calls": self.metrics.successful_calls,
            "failed_calls": self.metrics.failed_calls,
            "rejected_calls": self.metrics.rejected_calls,
            "fallback_calls": self.metrics.fallback_calls,
            "state_changes": self.metrics.state_changes,
            "consecutive_failures": self.metrics.consecutive_failures,
            "consecutive_successes": self.metrics.consecutive_successes,
            "last_failure_time": self.metrics.last_failure_time,
            "last_success_time": self.metrics.last_success_time,
            "time_in_current_state": time.time() - self._last_state_change,
        }

    def reset(self) -> None:
        """Reset circuit breaker to initial state."""
        self.state = CircuitState.CLOSED
        self.metrics = CircuitBreakerMetrics()
        self._last_state_change = time.time()

    def force_open(self) -> None:
        """Manually force circuit open."""
        self.state = CircuitState.OPEN
        self.metrics.last_failure_time = time.time()
        self.metrics.state_changes += 1
        self._last_state_change = time.time()

    def force_closed(self) -> None:
        """Manually force circuit closed."""
        self.state = CircuitState.CLOSED
        self.metrics.consecutive_failures = 0
        self.metrics.consecutive_successes = 0
        self.metrics.state_changes += 1
        self._last_state_change = time.time()


# Global circuit breaker registry
_circuit_breakers: Dict[str, CircuitBreaker] = {}


def get_circuit_breaker(name: str, config: Optional[CircuitBreakerConfig] = None) -> CircuitBreaker:
    """Get or create a circuit breaker."""
    if name not in _circuit_breakers:
        if config is None:
            config = CircuitBreakerConfig(name=name)
        _circuit_breakers[name] = CircuitBreaker(config)
    return _circuit_breakers[name]


def circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
) -> Callable:
    """
    Decorator to add circuit breaker to a function.

    Args:
        name: Circuit breaker name
        config: Optional configuration

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        cb = get_circuit_breaker(name, config)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await cb.call(func, *args, **kwargs)

        # Attach circuit breaker for inspection
        wrapper.circuit_breaker = cb
        return wrapper
    return decorator


class CircuitBreakerRegistry:
    """Registry for managing multiple circuit breakers."""

    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}

    def register(self, name: str, config: CircuitBreakerConfig) -> CircuitBreaker:
        """Register a new circuit breaker."""
        breaker = CircuitBreaker(config)
        self._breakers[name] = breaker
        return breaker

    def get(self, name: str) -> Optional[CircuitBreaker]:
        """Get circuit breaker by name."""
        return self._breakers.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all circuit breakers."""
        return {name: cb.get_metrics() for name, cb in self._breakers.items()}

    def get_all_states(self) -> Dict[str, CircuitState]:
        """Get states for all circuit breakers."""
        return {name: cb.get_state() for name, cb in self._breakers.items()}

    def reset_all(self) -> None:
        """Reset all circuit breakers."""
        for cb in self._breakers.values():
            cb.reset()


# Global registry
_registry = CircuitBreakerRegistry()


def get_registry() -> CircuitBreakerRegistry:
    """Get global circuit breaker registry."""
    return _registry