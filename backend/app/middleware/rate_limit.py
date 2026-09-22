import time
import math
import threading
from collections import defaultdict, deque
from typing import Dict, Deque
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response
from app.core.config import settings
from app.middleware.logging import get_trusted_client_ip


class SlidingWindowRateLimiter:
    """
    Thread-safe in-memory sliding window rate limiter.
    Designed for single-instance MVP deployments.
    Multi-instance deployments must substitute a distributed store (e.g. Redis).
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._history: Dict[str, Deque[float]] = defaultdict(deque)

    def is_allowed(self, key: str, max_requests: int, window_seconds: float = 60.0) -> tuple[bool, int]:
        """
        Check whether the given key is allowed under the rate limit.
        Returns (is_allowed, retry_after_seconds).
        """
        now = time.time()
        cutoff = now - window_seconds

        with self._lock:
            timestamps = self._history[key]
            # Prune expired timestamps
            while timestamps and timestamps[0] <= cutoff:
                timestamps.popleft()

            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, math.ceil(oldest + window_seconds - now))
                return False, retry_after

            timestamps.append(now)
            return True, 0

    def reset(self):
        """Reset all rate limiter state (useful for tests)."""
        with self._lock:
            self._history.clear()


# Global in-memory rate limiter instance
rate_limiter = SlidingWindowRateLimiter()


def reset_rate_limiter():
    """Helper to clear rate limiter history in tests."""
    rate_limiter.reset()


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Enforces per-client sliding window request rate limiting.
    Differentiates between standard API endpoints and compute-heavy endpoints.
    """

    HEAVY_POST_SUFFIXES = ("/repositories/analyze", "/analyze")

    def _is_heavy_endpoint(self, method: str, path: str) -> bool:
        if method != "POST":
            return False
        clean_path = path.rstrip("/")
        if clean_path.endswith("/repositories/analyze"):
            return True
        if clean_path.startswith("/api/investigations/") and clean_path.endswith("/analyze"):
            return True
        return False

    async def dispatch(self, request: Request, call_next) -> Response:
        if not settings.RATE_LIMIT_ENABLED:
            return await call_next(request)

        # Skip rate limiting for basic liveness probes
        if request.url.path in ("/api/health", "/api/health/live"):
            return await call_next(request)

        client_ip = get_trusted_client_ip(request)
        user_id = getattr(request.state, "user_id", "anon")
        is_heavy = self._is_heavy_endpoint(request.method, request.url.path)

        if is_heavy:
            category = "heavy"
            limit = settings.RATE_LIMIT_ANALYZE_PER_MINUTE
        else:
            category = "standard"
            limit = settings.RATE_LIMIT_DEFAULT_PER_MINUTE

        limiter_key = f"{user_id}:{client_ip}:{category}"
        allowed, retry_after = rate_limiter.is_allowed(limiter_key, max_requests=limit, window_seconds=60.0)

        if not allowed:
            request_id = getattr(request.state, "request_id", "req_unknown")
            return JSONResponse(
                status_code=429,
                headers={
                    "Retry-After": str(retry_after),
                    "X-Request-ID": request_id,
                },
                content={
                    "detail": f"Rate limit exceeded for {category} requests. Please retry in {retry_after} seconds.",
                    "retry_after": retry_after,
                    "request_id": request_id,
                    "error_code": "RATE_LIMIT_EXCEEDED",
                },
            )

        return await call_next(request)
