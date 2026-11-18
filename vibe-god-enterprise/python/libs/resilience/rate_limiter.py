"""
Rate Limiting Implementations
Token Bucket, Sliding Window, and Fixed Window algorithms.
"""
import asyncio
import time
from dataclasses import dataclass, field
from typing import Dict, Optional, Tuple
from enum import Enum
import logging

logger = logging.getLogger(__name__)


class RateLimitAlgorithm(str, Enum):
    TOKEN_BUCKET = "token_bucket"
    SLIDING_WINDOW = "sliding_window"
    FIXED_WINDOW = "fixed_window"


@dataclass
class RateLimitConfig:
    """Configuration for rate limiter."""
    requests_per_second: float = 10.0
    burst_size: int = 20
    algorithm: RateLimitAlgorithm = RateLimitAlgorithm.TOKEN_BUCKET
    key_func: Optional[callable] = None  # Function to extract key from request


@dataclass
class RateLimitResult:
    """Result of rate limit check."""
    allowed: bool
    remaining: int
    reset_time: float
    retry_after: float = 0.0


class RateLimiter:
    """
    Generic rate limiter supporting multiple algorithms.
    """

    def __init__(self, config: RateLimitConfig):
        self.config = config
        self._limiters: Dict[str, "BaseLimiter"] = {}
        self._lock = asyncio.Lock()

    def _get_limiter(self, key: str) -> "BaseLimiter":
        """Get or create limiter for key."""
        if key not in self._limiters:
            if self.config.algorithm == RateLimitAlgorithm.TOKEN_BUCKET:
                self._limiters[key] = TokenBucket(
                    rate=self.config.requests_per_second,
                    burst=self.config.burst_size,
                )
            elif self.config.algorithm == RateLimitAlgorithm.SLIDING_WINDOW:
                self._limiters[key] = SlidingWindow(
                    rate=self.config.requests_per_second,
                    window_size=1.0,
                )
            elif self.config.algorithm == RateLimitAlgorithm.FIXED_WINDOW:
                self._limiters[key] = FixedWindow(
                    rate=self.config.requests_per_second,
                    window_size=1.0,
                )
            else:
                raise ValueError(f"Unknown algorithm: {self.config.algorithm}")
        return self._limiters[key]

    async def acquire(
        self,
        key: str = "default",
        tokens: int = 1,
    ) -> RateLimitResult:
        """
        Acquire permission to proceed.

        Args:
            key: Rate limit key (e.g., user ID, IP)
            tokens: Number of tokens to consume

        Returns:
            RateLimitResult
        """
        limiter = self._get_limiter(key)
        return await limiter.acquire(tokens)

    async def try_acquire(
        self,
        key: str = "default",
        tokens: int = 1,
    ) -> RateLimitResult:
        """
        Try to acquire without blocking.

        Args:
            key: Rate limit key
            tokens: Number of tokens

        Returns:
            RateLimitResult (allowed=False if rate limited)
        """
        limiter = self._get_limiter(key)
        return await limiter.try_acquire(tokens)

    def get_limit_info(self, key: str = "default") -> dict:
        """Get current limit info for key."""
        if key in self._limiters:
            return self._limiters[key].get_info()
        return {}


class BaseLimiter:
    """Base class for rate limiters."""

    def __init__(self, rate: float, window_size: float = 1.0):
        self.rate = rate
        self.window_size = window_size

    async def acquire(self, tokens: int = 1) -> RateLimitResult:
        raise NotImplementedError

    async def try_acquire(self, tokens: int = 1) -> RateLimitResult:
        raise NotImplementedError

    def get_info(self) -> dict:
        raise NotImplementedError


class TokenBucket(BaseLimiter):
    """
    Token Bucket Algorithm.
    Allows bursts up to bucket size, then enforces steady rate.
    """

    def __init__(self, rate: float, burst: int):
        super().__init__(rate)
        self.burst = burst
        self._tokens = float(burst)
        self._last_update = time.monotonic()
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=True)

    async def try_acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=False)

    async def _try_consume(self, tokens: int, block: bool) -> RateLimitResult:
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_update = now

        if self._tokens >= tokens:
            self._tokens -= tokens
            return RateLimitResult(
                allowed=True,
                remaining=int(self._tokens),
                reset_time=now + (tokens / self.rate) if tokens > self._tokens else now,
            )

        if not block:
            # Calculate time until enough tokens
            deficit = tokens - self._tokens
            retry_after = deficit / self.rate
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + retry_after,
                retry_after=retry_after,
            )

        # Block until tokens available
        deficit = tokens - self._tokens
        wait_time = deficit / self.rate
        await asyncio.sleep(wait_time)

        # Retry after wait
        now = time.monotonic()
        elapsed = now - self._last_update
        self._tokens = min(self.burst, self._tokens + elapsed * self.rate)
        self._last_update = now
        self._tokens -= tokens

        return RateLimitResult(
            allowed=True,
            remaining=int(self._tokens),
            reset_time=now + (tokens / self.rate) if tokens > self._tokens else now,
        )

    def get_info(self) -> dict:
        return {
            "algorithm": "token_bucket",
            "rate": self.rate,
            "burst": self.burst,
            "available_tokens": self._tokens,
        }


class SlidingWindow(BaseLimiter):
    """
    Sliding Window Algorithm.
    More accurate than fixed window, smoother rate limiting.
    """

    def __init__(self, rate: float, window_size: float = 1.0):
        super().__init__(rate, window_size)
        self.max_requests = int(rate * window_size)
        self._requests: list = []  # Timestamps of requests
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=True)

    async def try_acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=False)

    async def _try_consume(self, tokens: int, block: bool) -> RateLimitResult:
        now = time.monotonic()
        window_start = now - self.window_size

        # Remove expired requests
        self._requests = [t for t in self._requests if t > window_start]

        current_count = len(self._requests)

        if current_count + tokens <= self.max_requests:
            # Add request timestamps
            for _ in range(tokens):
                self._requests.append(now)
            return RateLimitResult(
                allowed=True,
                remaining=self.max_requests - current_count - tokens,
                reset_time=now + self.window_size,
            )

        if not block:
            # Calculate when oldest request expires
            if self._requests:
                oldest = self._requests[0]
                retry_after = oldest + self.window_size - now
            else:
                retry_after = self.window_size
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=now + retry_after,
                retry_after=max(0, retry_after),
            )

        # Block until space available
        if self._requests:
            oldest = self._requests[0]
            wait_time = oldest + self.window_size - now
            if wait_time > 0:
                await asyncio.sleep(wait_time)

        # Retry after wait
        return await self._try_consume(tokens, block=True)

    def get_info(self) -> dict:
        now = time.monotonic()
        window_start = now - self.window_size
        current = len([t for t in self._requests if t > window_start])
        return {
            "algorithm": "sliding_window",
            "rate": self.rate,
            "window_size": self.window_size,
            "max_requests": self.max_requests,
            "current_requests": current,
        }


class FixedWindow(BaseLimiter):
    """
    Fixed Window Algorithm.
    Simple but can allow bursts at window boundaries.
    """

    def __init__(self, rate: float, window_size: float = 1.0):
        super().__init__(rate, window_size)
        self.max_requests = int(rate * window_size)
        self._window_start = time.monotonic()
        self._count = 0
        self._lock = asyncio.Lock()

    async def acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=True)

    async def try_acquire(self, tokens: int = 1) -> RateLimitResult:
        async with self._lock:
            return await self._try_consume(tokens, block=False)

    async def _try_consume(self, tokens: int, block: bool) -> RateLimitResult:
        now = time.monotonic()

        # Check if window expired
        if now - self._window_start >= self.window_size:
            self._window_start = now
            self._count = 0

        if self._count + tokens <= self.max_requests:
            self._count += tokens
            return RateLimitResult(
                allowed=True,
                remaining=self.max_requests - self._count,
                reset_time=self._window_start + self.window_size,
            )

        if not block:
            retry_after = self.window_size - (now - self._window_start)
            return RateLimitResult(
                allowed=False,
                remaining=0,
                reset_time=self._window_start + self.window_size,
                retry_after=max(0, retry_after),
            )

        # Block until window resets
        wait_time = self.window_size - (now - self._window_start)
        if wait_time > 0:
            await asyncio.sleep(wait_time)

        return await self._try_consume(tokens, block=True)

    def get_info(self) -> dict:
        now = time.monotonic()
        return {
            "algorithm": "fixed_window",
            "rate": self.rate,
            "window_size": self.window_size,
            "max_requests": self.max_requests,
            "current_requests": self._count,
            "window_reset": self._window_start + self.window_size,
        }


# Distributed rate limiter using Redis (for multi-instance deployments)
class DistributedRateLimiter:
    """
    Distributed rate limiter using Redis.
    Uses sliding window with sorted sets for accuracy.
    """

    def __init__(
        self,
        redis_client,
        rate: float,
        window_size: float = 1.0,
        prefix: str = "ratelimit:",
    ):
        self.redis = redis_client
        self.rate = rate
        self.window_size = window_size
        self.max_requests = int(rate * window_size)
        self.prefix = prefix

    async def acquire(
        self,
        key: str,
        tokens: int = 1,
        block: bool = True,
        timeout: float = 30.0,
    ) -> RateLimitResult:
        """Acquire rate limit slot."""
        redis_key = f"{self.prefix}{key}"
        now = time.time()
        window_start = now - self.window_size

        # Lua script for atomic check-and-increment
        lua_script = """
        local key = KEYS[1]
        local now = tonumber(ARGV[1])
        local window_start = tonumber(ARGV[2])
        local max_requests = tonumber(ARGV[3])
        local tokens = tonumber(ARGV[4])

        -- Remove expired entries
        redis.call('ZREMRANGEBYSCORE', key, '-inf', window_start)

        -- Count current requests
        local current = redis.call('ZCARD', key)

        if current + tokens <= max_requests then
            -- Add new entries
            for i = 1, tokens do
                redis.call('ZADD', key, now, now .. ':' .. i)
            end
            redis.call('EXPIRE', key, math.ceil(window_start + 1))
            return {1, max_requests - current - tokens, 0}
        else
            local oldest = redis.call('ZRANGE', key, 0, 0, 'WITHSCORES')
            local retry_after = 0
            if #oldest > 0 then
                retry_after = oldest[2] + ARGV[5] - now
            end
            return {0, 0, retry_after}
        end
        """

        try:
            result = await self.redis.eval(
                lua_script,
                1,
                redis_key,
                now,
                window_start,
                self.max_requests,
                tokens,
                self.window_size,
            )

            allowed = bool(result[0])
            remaining = int(result[1])
            retry_after = float(result[2])

            return RateLimitResult(
                allowed=allowed,
                remaining=remaining,
                reset_time=now + retry_after if not allowed else now + self.window_size,
                retry_after=retry_after if not allowed else 0,
            )

        except Exception as e:
            logger.error(f"Distributed rate limiter error: {e}")
            # Fail open on Redis errors
            return RateLimitResult(
                allowed=True,
                remaining=self.max_requests,
                reset_time=now + self.window_size,
            )

    async def get_current_usage(self, key: str) -> int:
        """Get current usage for key."""
        redis_key = f"{self.prefix}{key}"
        now = time.time()
        window_start = now - self.window_size

        # Remove expired and count
        await self.redis.zremrangebyscore(redis_key, "-inf", window_start)
        return await self.redis.zcard(redis_key)


# Rate limiter middleware for FastAPI
class RateLimitMiddleware:
    """FastAPI middleware for rate limiting."""

    def __init__(
        self,
        app,
        rate_limiter: RateLimiter,
        key_header: str = "X-Forwarded-For",
        excluded_paths: Optional[list] = None,
    ):
        self.app = app
        self.rate_limiter = rate_limiter
        self.key_header = key_header
        self.excluded_paths = excluded_paths or ["/health", "/metrics", "/docs", "/openapi.json"]

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        path = scope.get("path", "")
        if path in self.excluded_paths:
            await self.app(scope, receive, send)
            return

        # Extract key from headers
        headers = dict(scope.get("headers", []))
        key = headers.get(self.key_header.lower().encode(), b"unknown").decode()

        result = await self.rate_limiter.try_acquire(key)

        if not result.allowed:
            # Send 429 response
            await send({
                "type": "http.response.start",
                "status": 429,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"x-ratelimit-limit", str(self.rate_limiter.config.requests_per_second).encode()),
                    (b"x-ratelimit-remaining", b"0"),
                    (b"x-ratelimit-reset", str(int(result.reset_time)).encode()),
                    (b"retry-after", str(int(result.retry_after)).encode()),
                ],
            })
            await send({
                "type": "http.response.body",
                "body": b'{"error": "Rate limit exceeded"}',
            })
            return

        # Add rate limit headers to response
        original_send = send

        async def send_with_headers(message):
            if message["type"] == "http.response.start":
                headers = list(message.get("headers", []))
                headers.extend([
                    (b"x-ratelimit-limit", str(self.rate_limiter.config.requests_per_second).encode()),
                    (b"x-ratelimit-remaining", str(result.remaining).encode()),
                    (b"x-ratelimit-reset", str(int(result.reset_time)).encode()),
                ])
                message["headers"] = headers
            await original_send(message)

        await self.app(scope, receive, send_with_headers)