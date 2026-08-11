"""
Simple in-memory rate limiting middleware.
Suitable for local and single-process deployments; use Redis at scale.
"""

from __future__ import annotations

import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class InMemoryRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(
        self,
        app,
        default_limit: int = 120,
        auth_limit: int = 20,
        sensitive_limit: int = 5,
        window_seconds: int = 60,
        enabled: bool = True,
        redis_url: str | None = None,
    ):
        super().__init__(app)
        self.default_limit = default_limit
        self.auth_limit = auth_limit
        self.sensitive_limit = sensitive_limit
        self.window_seconds = window_seconds
        self.enabled = enabled
        self._hits: dict[tuple[str, str], deque[float]] = defaultdict(deque)
        self._last_cleanup: float = time.monotonic()
        self._cleanup_interval: int = 60  # seconds
        self._redis = None
        if redis_url:
            try:
                from redis.asyncio import Redis

                self._redis = Redis.from_url(redis_url, decode_responses=True)
            except Exception:
                self._redis = None

    async def dispatch(self, request: Request, call_next):
        if not self.enabled:
            return await call_next(request)

        path = request.url.path
        if path.startswith("/uploads") or path == "/api/health":
            return await call_next(request)

        # Periodically evict stale entries to prevent memory leak
        now = time.monotonic()
        if now - self._last_cleanup > self._cleanup_interval:
            self._evict_stale(now)
            self._last_cleanup = now

        if path.startswith("/api/auth"):
            limit = self.auth_limit
            bucket_name = "auth"
        elif path in ["/api/plans/medicines", "/api/plans/remedies"]:
            limit = self.sensitive_limit
            bucket_name = "sensitive_plans"
        else:
            limit = self.default_limit
            bucket_name = "api"

        # Auth endpoints are pre-authentication by definition, so they always key
        # on network origin. Everything else prefers the authenticated user id,
        # which both survives carrier-grade NAT (many real users behind one IPv4
        # would otherwise share a bucket) and pins abuse to an account.
        identity = self._client_identity(request, prefer_user=(bucket_name != "auth"))
        if self._redis:
            try:
                limited_response = await self._redis_limit(identity, bucket_name, limit)
                if limited_response:
                    return limited_response
                response = await call_next(request)
                response.headers["X-RateLimit-Limit"] = str(limit)
                return response
            except Exception as _redis_err:
                import logging as _log
                _log.getLogger("ayura.rate_limit").warning(
                    "Redis rate-limit failed (%s); falling back to in-memory", _redis_err
                )

        bucket_key = (identity, bucket_name)
        now = time.monotonic()
        bucket = self._hits[bucket_key]

        while bucket and now - bucket[0] > self.window_seconds:
            bucket.popleft()

        if len(bucket) >= limit:
            retry_after = max(1, round(self.window_seconds - (now - bucket[0])))
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers={"Retry-After": str(retry_after)},
            )

        bucket.append(now)
        response = await call_next(request)
        response.headers["X-RateLimit-Limit"] = str(limit)
        response.headers["X-RateLimit-Remaining"] = str(max(0, limit - len(bucket)))
        return response

    async def _redis_limit(self, identity: str, bucket_name: str, limit: int):
        key = f"rate:{bucket_name}:{identity}"
        count = await self._redis.incr(key)
        if count == 1:
            await self._redis.expire(key, self.window_seconds)
        if count > limit:
            ttl = await self._redis.ttl(key)
            return JSONResponse(
                status_code=429,
                content={"detail": "Too many requests. Please try again shortly."},
                headers={"Retry-After": str(max(1, ttl))},
            )
        return None

    @staticmethod
    def _client_identity(request: Request, prefer_user: bool = False) -> str:
        if prefer_user:
            user_id = InMemoryRateLimitMiddleware._user_identity(request)
            if user_id:
                return f"u:{user_id}"

        return f"ip:{InMemoryRateLimitMiddleware._peer_ip(request)}"

    @staticmethod
    def _user_identity(request: Request) -> str | None:
        """User id from the access-token cookie, or None if absent/invalid.

        Signature-verified, so a caller cannot forge someone else's bucket — and
        a forged/expired token just falls through to the IP bucket rather than
        creating a free one.
        """
        from config import settings

        token = request.cookies.get(settings.ACCESS_TOKEN_COOKIE)
        if not token:
            auth = request.headers.get("authorization") or ""
            if auth.startswith("Bearer "):
                token = auth.split(" ", 1)[1]
        if not token:
            return None
        try:
            from services.auth_service import get_current_user_id

            return get_current_user_id(token)
        except Exception:
            return None

    @staticmethod
    def _peer_ip(request: Request) -> str:
        """Real client IP, counting X-Forwarded-For from the RIGHT.

        Each proxy we control appends one entry, so the Nth-from-last entry is
        the address our outermost proxy actually saw. Reading from the left
        instead would take an entry the caller wrote, letting anyone mint a new
        rate-limit bucket per request with a spoofed header.
        """
        from config import settings

        if getattr(settings, "TRUST_FORWARDED_FOR", False):
            forwarded_for = request.headers.get("x-forwarded-for")
            if forwarded_for:
                parts = [p.strip() for p in forwarded_for.split(",") if p.strip()]
                if parts:
                    hops = max(1, int(getattr(settings, "TRUSTED_PROXY_HOPS", 1) or 1))
                    # Clamp: a header shorter than the configured hop count means
                    # the request didn't traverse the expected chain, so fall back
                    # to the leftmost entry we were actually given.
                    return parts[-min(hops, len(parts))]
        return request.client.host if request.client else "unknown"

    def _evict_stale(self, now: float) -> None:
        """Remove buckets with no hits within 2× the window to prevent memory leak."""
        cutoff = now - (self.window_seconds * 2)
        stale_keys = [key for key, bucket in self._hits.items() if not bucket or bucket[-1] < cutoff]
        for key in stale_keys:
            del self._hits[key]
