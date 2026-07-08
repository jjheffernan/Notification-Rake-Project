"""Per-IP in-memory rate limiting for public API and admin login."""

from __future__ import annotations

import time
from collections import defaultdict, deque
from threading import Lock
from typing import TYPE_CHECKING

from flask import jsonify, request

if TYPE_CHECKING:
    from flask import Flask

# ponytail: process-local buckets only — no sharing across gunicorn workers;
# upgrade path: Redis + Flask-Limiter when multi-worker limits matter.
_buckets: dict[tuple[str, str], deque[float]] = defaultdict(deque)
_lock = Lock()


def _client_ip() -> str:
    forwarded = request.headers.get("X-Forwarded-For", "")
    if forwarded:
        return forwarded.split(",", 1)[0].strip() or "unknown"
    return request.remote_addr or "unknown"


def _is_limited(*, bucket: str, limit: int, window_sec: int) -> bool:
    now = time.monotonic()
    key = (_client_ip(), bucket)
    with _lock:
        hits = _buckets[key]
        cutoff = now - window_sec
        while hits and hits[0] <= cutoff:
            hits.popleft()
        if len(hits) >= limit:
            return True
        hits.append(now)
        return False


def _should_rate_limit() -> str | None:
    from notification_rake.config import settings

    path = request.path
    if path.startswith("/api/"):
        if _is_limited(
            bucket="api",
            limit=settings.api_rate_limit,
            window_sec=settings.api_rate_limit_window_sec,
        ):
            return "api"
        return None
    if path == "/admin/login" and request.method == "POST":
        if _is_limited(
            bucket="admin_login",
            limit=settings.admin_login_rate_limit,
            window_sec=settings.admin_login_rate_limit_window_sec,
        ):
            return "admin_login"
    return None


def register_rate_limit(app: Flask) -> None:
    @app.before_request
    def _enforce_rate_limit():
        if _should_rate_limit() is None:
            return None
        if request.path.startswith("/api/"):
            response = jsonify(error="Too many requests")
            response.status_code = 429
            return response
        return ("Too many requests", 429)


def reset_rate_limits() -> None:
    """Clear buckets — test helper only."""
    with _lock:
        _buckets.clear()
