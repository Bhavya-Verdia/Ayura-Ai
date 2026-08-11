"""Abuse / cost-control regressions.

Covers the three things that let a single caller ignore every limit we thought
we had: a spoofable X-Forwarded-For chain, no per-account login lockout, and no
ceiling on billed LLM calls once a caller was authenticated.
"""

from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient
from starlette.requests import Request

from config import settings
from core.quota import consume_quota
from core.rate_limit import InMemoryRateLimitMiddleware
from database.mongodb import get_mongodb
from main import app
from services.auth_service import create_access_token, hash_password


@pytest.fixture
def client():
    yield TestClient(app)


def _request(headers: dict | None = None, peer: str = "10.0.0.1") -> Request:
    raw = [(k.lower().encode(), v.encode()) for k, v in (headers or {}).items()]
    return Request({
        "type": "http",
        "method": "GET",
        "path": "/api/plans/yoga",
        "headers": raw,
        "client": (peer, 12345),
    })


# ─────────────────────────────────────────────────────────────────────
# X-Forwarded-For must not be spoofable into a fresh bucket
# ─────────────────────────────────────────────────────────────────────

def test_peer_ip_ignores_caller_supplied_forwarded_entries(monkeypatch):
    """The leading entries of XFF are caller-controlled and must be ignored.

    nginx appends the true peer at the right; reading from the left let anyone
    mint a new rate-limit bucket per request by rotating a fake first hop.
    """
    monkeypatch.setattr(settings, "TRUST_FORWARDED_FOR", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)

    spoofed = _request({"x-forwarded-for": "1.2.3.4, 203.0.113.7"})
    assert InMemoryRateLimitMiddleware._peer_ip(spoofed) == "203.0.113.7"

    # Rotating the spoofed entry must not change the identity we key on.
    other = _request({"x-forwarded-for": "9.9.9.9, 203.0.113.7"})
    assert InMemoryRateLimitMiddleware._peer_ip(other) == "203.0.113.7"


def test_peer_ip_honours_multiple_trusted_hops(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_FORWARDED_FOR", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 2)

    req = _request({"x-forwarded-for": "1.2.3.4, 203.0.113.7, 172.16.0.2"})
    assert InMemoryRateLimitMiddleware._peer_ip(req) == "203.0.113.7"


def test_peer_ip_falls_back_when_chain_shorter_than_configured(monkeypatch):
    """A request that skipped the expected proxy chain still yields something."""
    monkeypatch.setattr(settings, "TRUST_FORWARDED_FOR", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 3)

    req = _request({"x-forwarded-for": "203.0.113.7"})
    assert InMemoryRateLimitMiddleware._peer_ip(req) == "203.0.113.7"


def test_peer_ip_ignores_forwarded_header_when_untrusted(monkeypatch):
    monkeypatch.setattr(settings, "TRUST_FORWARDED_FOR", False)
    req = _request({"x-forwarded-for": "1.2.3.4"}, peer="10.0.0.9")
    assert InMemoryRateLimitMiddleware._peer_ip(req) == "10.0.0.9"


def test_rotating_forwarded_for_cannot_escape_the_limit(monkeypatch):
    """End-to-end through the real middleware, on an isolated app.

    This is the exact bypass that was live in production: 30 requests with a
    rotating first XFF entry drew 30× 200 instead of tripping at the limit.
    A private app instance keeps this from consuming the shared app's buckets.
    """
    from fastapi import FastAPI

    monkeypatch.setattr(settings, "TRUST_FORWARDED_FOR", True)
    monkeypatch.setattr(settings, "TRUSTED_PROXY_HOPS", 1)

    isolated = FastAPI()
    isolated.add_middleware(
        InMemoryRateLimitMiddleware, default_limit=5, auth_limit=5, enabled=True
    )

    @isolated.get("/api/ping")
    async def ping():
        return {"ok": True}

    with TestClient(isolated) as c:
        codes = [
            c.get("/api/ping", headers={"X-Forwarded-For": f"1.2.3.{i}, 203.0.113.7"}).status_code
            for i in range(10)
        ]

    assert codes[:5] == [200] * 5
    assert 429 in codes[5:], f"rotating X-Forwarded-For still bypassed the limit: {codes}"


# ─────────────────────────────────────────────────────────────────────
# Authenticated callers key on account, not network origin
# ─────────────────────────────────────────────────────────────────────

def test_identity_prefers_authenticated_user():
    token = create_access_token("user-abc", "a@b.com")
    req = _request({"cookie": f"{settings.ACCESS_TOKEN_COOKIE}={token}"})
    assert InMemoryRateLimitMiddleware._client_identity(req, prefer_user=True) == "u:user-abc"


def test_identity_falls_back_to_ip_for_forged_token():
    """A garbage token must land in the IP bucket, not a free one of its own."""
    req = _request({"cookie": f"{settings.ACCESS_TOKEN_COOKIE}=not-a-real-jwt"}, peer="10.0.0.4")
    assert InMemoryRateLimitMiddleware._client_identity(req, prefer_user=True) == "ip:10.0.0.4"


def test_identity_ignores_user_on_auth_endpoints():
    """Auth routes are pre-authentication, so they always key on origin."""
    token = create_access_token("user-abc", "a@b.com")
    req = _request({"cookie": f"{settings.ACCESS_TOKEN_COOKIE}={token}"}, peer="10.0.0.5")
    assert InMemoryRateLimitMiddleware._client_identity(req, prefer_user=False) == "ip:10.0.0.5"


# ─────────────────────────────────────────────────────────────────────
# Daily quota
# ─────────────────────────────────────────────────────────────────────

def _quota_db(count: int):
    db = AsyncMock()
    db.usage_quota.find_one_and_update = AsyncMock(return_value={"count": count})
    return db


@pytest.mark.asyncio
async def test_quota_allows_up_to_the_limit():
    await consume_quota(_quota_db(5), "u1", "plan", limit=5)


@pytest.mark.asyncio
async def test_quota_rejects_past_the_limit():
    with pytest.raises(HTTPException) as exc:
        await consume_quota(_quota_db(6), "u1", "plan", limit=5)
    assert exc.value.status_code == 429
    assert "Retry-After" in exc.value.headers


@pytest.mark.asyncio
async def test_quota_charges_cost_for_fan_out_requests():
    db = _quota_db(6)
    with pytest.raises(HTTPException):
        await consume_quota(db, "u1", "plan", limit=5, cost=6)
    inc = db.usage_quota.find_one_and_update.await_args.args[1]["$inc"]["count"]
    assert inc == 6


@pytest.mark.asyncio
async def test_quota_exempts_admins():
    db = _quota_db(9999)
    await consume_quota(db, "u1", "plan", limit=5, exempt=True)
    db.usage_quota.find_one_and_update.assert_not_awaited()


@pytest.mark.asyncio
async def test_quota_fails_open_when_counter_unavailable():
    """Losing the ceiling briefly beats taking plan generation down with Mongo."""
    db = AsyncMock()
    db.usage_quota.find_one_and_update = AsyncMock(side_effect=RuntimeError("mongo down"))
    await consume_quota(db, "u1", "plan", limit=1)


@pytest.mark.asyncio
async def test_quota_fails_open_on_unreadable_counter():
    db = AsyncMock()
    db.usage_quota.find_one_and_update = AsyncMock(return_value=None)
    await consume_quota(db, "u1", "plan", limit=1)


# ─────────────────────────────────────────────────────────────────────
# Per-account login lockout
# ─────────────────────────────────────────────────────────────────────

def _local_user(**overrides) -> dict:
    now = datetime.now(timezone.utc)
    base = {
        "_id": "lockout-user",
        "name": "Lock Me",
        "email": "lock@ayura.com",
        "password_hash": hash_password("TestPass123!"),
        "auth_provider": "local",
        "is_verified": True,
        "is_active": True,
        "created_at": now,
        "updated_at": now,
    }
    base.update(overrides)
    return base


def test_failed_logins_lock_the_account(client):
    """Attempts must accumulate across requests and end in a real lock window."""
    db = client.app.dependency_overrides[get_mongodb]()
    stored = _local_user()

    async def _find_one(*_args, **_kwargs):
        return dict(stored)

    async def _update_one(_filter, update, *_args, **_kwargs):
        stored.update(update.get("$set", {}))
        for field in update.get("$unset", {}):
            stored.pop(field, None)

    db.users.find_one = AsyncMock(side_effect=_find_one)
    db.users.update_one = AsyncMock(side_effect=_update_one)

    for _ in range(settings.LOGIN_MAX_FAILED_ATTEMPTS):
        resp = client.post("/api/auth/login", json={"email": "lock@ayura.com", "password": "nope"})
        assert resp.status_code == 401

    assert "lockout_until" in stored
    # Counter resets when the lock is applied, so the window — not the count —
    # is what keeps the next attempt out.
    assert stored["failed_login_attempts"] == 0

    resp = client.post("/api/auth/login", json={"email": "lock@ayura.com", "password": "TestPass123!"})
    assert resp.status_code == 429


def test_locked_account_rejects_even_the_correct_password(client):
    db = client.app.dependency_overrides[get_mongodb]()
    db.users.find_one = AsyncMock(return_value=_local_user(
        lockout_until=datetime.now(timezone.utc) + timedelta(minutes=10),
    ))

    resp = client.post("/api/auth/login", json={"email": "lock@ayura.com", "password": "TestPass123!"})
    assert resp.status_code == 429
    assert resp.headers.get("Retry-After")


def test_expired_lockout_lets_a_valid_password_through(client):
    db = client.app.dependency_overrides[get_mongodb]()
    db.users.find_one = AsyncMock(return_value=_local_user(
        lockout_until=datetime.now(timezone.utc) - timedelta(minutes=1),
        failed_login_attempts=3,
    ))
    db.users.update_one = AsyncMock()

    resp = client.post("/api/auth/login", json={"email": "lock@ayura.com", "password": "TestPass123!"})
    assert resp.status_code == 200
    # ...and the stale counter is cleared on the way through.
    reset = db.users.update_one.await_args.args[1]
    assert reset["$set"]["failed_login_attempts"] == 0
    assert "lockout_until" in reset["$unset"]
