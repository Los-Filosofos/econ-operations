"""Thread-safe in-memory rate limiter for protecting upstream quotas and endpoints."""

import threading
from collections import defaultdict
from ipaddress import ip_address
from time import monotonic

from fastapi import HTTPException, Request

from app.core.config import Settings


class SlidingWindowRateLimiter:
    def __init__(self, cleanup_interval_seconds: float = 60.0, max_tracked_clients: int = 10_000):
        self._clients: dict[str, list[float]] = defaultdict(list)
        self._lock = threading.Lock()
        self._cleanup_interval = cleanup_interval_seconds
        self._last_cleanup = monotonic()
        self._max_clients = max_tracked_clients

    def check(
        self, client_id: str, limit: int, window_seconds: float = 60.0
    ) -> tuple[bool, int, int]:
        """Check if request from client_id is within limit over window_seconds.

        Returns: (allowed, remaining, reset_seconds)
        """
        now = monotonic()
        with self._lock:
            # Periodic cleanup of stale clients
            if now - self._last_cleanup > self._cleanup_interval:
                self._cleanup(now, window_seconds)

            timestamps = self._clients[client_id]
            cutoff = now - window_seconds
            # Remove timestamps outside the sliding window
            while timestamps and timestamps[0] <= cutoff:
                timestamps.pop(0)

            if len(timestamps) >= limit:
                oldest = timestamps[0]
                reset_seconds = max(1, int(oldest + window_seconds - now) + 1)
                return False, 0, reset_seconds

            timestamps.append(now)
            remaining = max(0, limit - len(timestamps))
            return True, remaining, int(window_seconds)

    def _cleanup(self, now: float, window_seconds: float) -> None:
        self._last_cleanup = now
        cutoff = now - window_seconds
        stale_keys = []
        for key, times in self._clients.items():
            while times and times[0] <= cutoff:
                times.pop(0)
            if not times:
                stale_keys.append(key)
        for key in stale_keys:
            del self._clients[key]

        # Prevent unbounded growth if many ephemeral IPs attack
        if len(self._clients) > self._max_clients:
            self._clients.clear()

    def reset(self) -> None:
        with self._lock:
            self._clients.clear()
            self._last_cleanup = monotonic()


_GLOBAL_LIMITER = SlidingWindowRateLimiter()


def get_limiter() -> SlidingWindowRateLimiter:
    return _GLOBAL_LIMITER


def extract_client_ip(request: Request, trusted_proxies: list[str]) -> str:
    direct_ip = request.client.host if request.client else "127.0.0.1"
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded and direct_ip in trusted_proxies:
        candidate = forwarded.split(",")[0].strip()
        try:
            ip_address(candidate)
            return candidate
        except ValueError:
            pass
    return direct_ip


def check_rate_limit(
    request: Request,
    is_live: bool = False,
    custom_limit: int | None = None,
) -> None:
    settings: Settings | None = getattr(getattr(request.app, "state", None), "settings", None)
    if not settings or not settings.rate_limit_enabled:
        return

    limit = (
        custom_limit
        if custom_limit is not None
        else (settings.rate_limit_live_per_minute if is_live else settings.rate_limit_per_minute)
    )

    client_ip = extract_client_ip(request, settings.trusted_proxies)
    bucket_key = f"{client_ip}:{'live' if is_live else 'standard'}"

    allowed, remaining, reset_seconds = _GLOBAL_LIMITER.check(bucket_key, limit=limit)
    if not allowed:
        raise HTTPException(
            status_code=429,
            detail="Límite de peticiones excedido. Intenta más tarde.",
            headers={
                "Retry-After": str(reset_seconds),
                "X-RateLimit-Limit": str(limit),
                "X-RateLimit-Remaining": "0",
            },
        )
