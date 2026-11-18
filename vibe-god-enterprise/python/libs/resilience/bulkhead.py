"""
Bulkhead Pattern Implementation
Isolates resources to prevent cascade failures.
"""
import asyncio
from dataclasses import dataclass, field
from typing import Callable, Any, Optional, Dict
from functools import wraps
from enum import Enum
import logging
import time

logger = logging.getLogger(__name__)


class BulkheadType(str, Enum):
    SEMAPHORE = "semaphore"      # Limits concurrent calls
    THREAD_POOL = "thread_pool"  # Dedicated thread pool
    PROCESS_POOL = "process_pool"  # Dedicated process pool (for CPU-bound)


class BulkheadFullError(Exception):
    """Raised when bulkhead is at capacity."""
    def __init__(self, bulkhead_name: str, max_concurrent: int, current: int):
        self.bulkhead_name = bulkhead_name
        self.max_concurrent = max_concurrent
        self.current = current
        super().__init__(
            f"Bulkhead '{bulkhead_name}' full: {current}/{max_concurrent} concurrent"
        )


@dataclass
class BulkheadConfig:
    """Configuration for bulkhead."""
    max_concurrent: int = 10
    max_queue_size: int = 100
    timeout: float = 30.0  # Max wait time for slot
    bulkhead_type: BulkheadType = BulkheadType.SEMAPHORE
    name: str = "default"


@dataclass
class BulkheadMetrics:
    """Metrics for bulkhead."""
    total_calls: int = 0
    successful_calls: int = 0
    failed_calls: int = 0
    rejected_calls: int = 0
    timed_out_calls: int = 0
    current_concurrent: int = 0
    max_concurrent_seen: int = 0
    total_wait_time: float = 0.0
    max_wait_time: float = 0.0


class Bulkhead:
    """
    Bulkhead implementation using semaphore for concurrency control.
    """

    def __init__(self, config: BulkheadConfig):
        self.config = config
        self._semaphore: Optional[asyncio.Semaphore] = None
        self._queue: Optional[asyncio.Queue] = None
        self._metrics = BulkheadMetrics()
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _ensure_initialized(self) -> None:
        """Lazy initialization."""
        if not self._initialized:
            async with self._lock:
                if not self._initialized:
                    self._semaphore = asyncio.Semaphore(self.config.max_concurrent)
                    if self.config.max_queue_size > 0:
                        self._queue = asyncio.Queue(maxsize=self.config.max_queue_size)
                    self._initialized = True

    async def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """
        Execute function within bulkhead.

        Args:
            func: Async function to execute
            *args: Positional arguments
            **kwargs: Keyword arguments

        Returns:
            Function result

        Raises:
            BulkheadFullError: If bulkhead is at capacity
            asyncio.TimeoutError: If timeout exceeded
        """
        await self._ensure_initialized()

        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.current_concurrent += 1
            self._metrics.max_concurrent_seen = max(
                self._metrics.max_concurrent_seen,
                self._metrics.current_concurrent
            )

        wait_start = time.monotonic()
        acquired = False

        try:
            # Try to acquire semaphore with timeout
            try:
                await asyncio.wait_for(
                    self._semaphore.acquire(),
                    timeout=self.config.timeout
                )
                acquired = True
            except asyncio.TimeoutError:
                async with self._lock:
                    self._metrics.timed_out_calls += 1
                    self._metrics.current_concurrent -= 1
                raise

            wait_time = time.monotonic() - wait_start
            async with self._lock:
                self._metrics.total_wait_time += wait_time
                self._metrics.max_wait_time = max(
                    self._metrics.max_wait_time,
                    wait_time
                )

            # Execute function
            try:
                result = await func(*args, **kwargs)
                async with self._lock:
                    self._metrics.successful_calls += 1
                return result
            except Exception as e:
                async with self._lock:
                    self._metrics.failed_calls += 1
                raise

        finally:
            if acquired:
                self._semaphore.release()
            async with self._lock:
                self._metrics.current_concurrent -= 1

    def get_metrics(self) -> Dict[str, Any]:
        """Get bulkhead metrics."""
        avg_wait = 0.0
        if self._metrics.total_calls > 0:
            avg_wait = self._metrics.total_wait_time / self._metrics.total_calls

        return {
            "name": self.config.name,
            "max_concurrent": self.config.max_concurrent,
            "current_concurrent": self._metrics.current_concurrent,
            "max_concurrent_seen": self._metrics.max_concurrent_seen,
            "total_calls": self._metrics.total_calls,
            "successful_calls": self._metrics.successful_calls,
            "failed_calls": self._metrics.failed_calls,
            "rejected_calls": self._metrics.rejected_calls,
            "timed_out_calls": self._metrics.timed_out_calls,
            "avg_wait_time": avg_wait,
            "max_wait_time": self._metrics.max_wait_time,
            "utilization": (
                self._metrics.current_concurrent / self.config.max_concurrent
                if self.config.max_concurrent > 0 else 0
            ),
        }

    def reset_metrics(self) -> None:
        """Reset metrics."""
        self._metrics = BulkheadMetrics()

    @property
    def available_slots(self) -> int:
        """Get available slots."""
        if self._semaphore:
            return self._semaphore._value
        return self.config.max_concurrent

    @property
    def is_full(self) -> bool:
        """Check if bulkhead is full."""
        return self.available_slots == 0


class ThreadPoolBulkhead:
    """
    Bulkhead using dedicated thread pool for CPU-bound operations.
    """

    def __init__(self, config: BulkheadConfig):
        from concurrent.futures import ThreadPoolExecutor
        self.config = config
        self.executor = ThreadPoolExecutor(max_workers=config.max_concurrent)
        self._metrics = BulkheadMetrics()
        self._lock = asyncio.Lock()

    async def execute(self, func: Callable, *args: Any, **kwargs: Any) -> Any:
        """Execute function in thread pool."""
        loop = asyncio.get_event_loop()

        async with self._lock:
            self._metrics.total_calls += 1
            self._metrics.current_concurrent += 1
            self._metrics.max_concurrent_seen = max(
                self._metrics.max_concurrent_seen,
                self._metrics.current_concurrent
            )

        try:
            # Run in thread pool
            result = await loop.run_in_executor(
                self.executor,
                lambda: func(*args, **kwargs)
            )
            async with self._lock:
                self._metrics.successful_calls += 1
            return result
        except Exception as e:
            async with self._lock:
                self._metrics.failed_calls += 1
            raise
        finally:
            async with self._lock:
                self._metrics.current_concurrent -= 1

    def get_metrics(self) -> Dict[str, Any]:
        return {
            "name": self.config.name,
            "type": "thread_pool",
            "max_workers": self.config.max_concurrent,
            "current_concurrent": self._metrics.current_concurrent,
            "total_calls": self._metrics.total_calls,
            "successful_calls": self._metrics.successful_calls,
            "failed_calls": self._metrics.failed_calls,
        }

    def shutdown(self, wait: bool = True) -> None:
        """Shutdown thread pool."""
        self.executor.shutdown(wait=wait)


# Global bulkhead registry
_bulkheads: Dict[str, Bulkhead] = {}


def get_bulkhead(name: str, config: Optional[BulkheadConfig] = None) -> Bulkhead:
    """Get or create a bulkhead."""
    if name not in _bulkheads:
        if config is None:
            config = BulkheadConfig(name=name)
        _bulkheads[name] = Bulkhead(config)
    return _bulkheads[name]


def bulkhead(
    name: str,
    config: Optional[BulkheadConfig] = None,
) -> Callable:
    """
    Decorator to add bulkhead isolation to a function.

    Args:
        name: Bulkhead name
        config: Optional configuration

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        bh = get_bulkhead(name, config)

        @wraps(func)
        async def wrapper(*args: Any, **kwargs: Any) -> Any:
            return await bh.execute(func, *args, **kwargs)

        wrapper.bulkhead = bh
        return wrapper
    return decorator


class BulkheadRegistry:
    """Registry for managing multiple bulkheads."""

    def __init__(self):
        self._bulkheads: Dict[str, Bulkhead] = {}

    def register(self, name: str, config: BulkheadConfig) -> Bulkhead:
        """Register a new bulkhead."""
        bh = Bulkhead(config)
        self._bulkheads[name] = bh
        return bh

    def get(self, name: str) -> Optional[Bulkhead]:
        """Get bulkhead by name."""
        return self._bulkheads.get(name)

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """Get metrics for all bulkheads."""
        return {name: bh.get_metrics() for name, bh in self._bulkheads.items()}


# Global registry
_bulkhead_registry = BulkheadRegistry()


def get_bulkhead_registry() -> BulkheadRegistry:
    """Get global bulkhead registry."""
    return _bulkhead_registry