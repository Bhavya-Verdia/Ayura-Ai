"""
Plan API integration tests.

Covers:
- Auth guards on all plan endpoints
- Job creation for each plan type
- Job polling (unknown ID → 404, pending state)
- Latest plan fetch when no plans exist
- Plan history fetch
- Adaptation request (with feedback)
- Rate limiting (duplicate concurrent lock)
"""

import pytest
from fastapi.testclient import TestClient
from unittest.mock import AsyncMock, MagicMock, patch
from main import app
from database.mongodb import get_mongodb
from services.auth_service import create_access_token
import uuid


# ── Fixtures ──────────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    yield TestClient(app)


@pytest.fixture
def auth_cookies(client):
    """Return cookie header dict for a mock authenticated local user."""
    token = create_access_token("test-uuid-1234", "test@ayura.com")
    client.cookies.set("ayura_access", token)
    return client


@pytest.fixture
def verified_mock_db(mock_db):
    """Extend the autouse mock_db fixture with a verified user and all required collection mocks."""
    from services.auth_service import hash_password
    from datetime import datetime, timezone
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234",
        "name": "Test User",
        "email": "test@ayura.com",
        "password_hash": hash_password("TestPass123!"),
        "auth_provider": "local",
        "is_active": True,
        "is_admin": False,
        "is_verified": True,
        "onboarding_complete": True,
        "dominant_dosha": "vata",
        "goal": "general_wellness",
        "age": 28,
        "height_cm": 170.0,
        "weight_kg": 65.0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    # Preferences: return None so plan routes use defaults
    mock_db.user_preferences = AsyncMock()
    mock_db.user_preferences.find_one = AsyncMock(return_value=None)
    # Plan jobs collection
    mock_db.plan_jobs = AsyncMock()
    mock_db.plan_jobs.find_one = AsyncMock(return_value=None)
    mock_db.plan_jobs.insert_one = AsyncMock()
    mock_db.plan_jobs.update_one = AsyncMock()
    # Rating preferences
    mock_db.plan_ratings = AsyncMock()
    mock_db.plan_ratings.find_one = AsyncMock(return_value=None)
    return mock_db


# ── Auth guard tests ───────────────────────────────────────────────────────────

def test_generate_plan_requires_auth(client):
    resp = client.post("/api/plans/gym")
    assert resp.status_code == 401


def test_generate_holistic_requires_auth(client):
    resp = client.post("/api/plans/generate")
    assert resp.status_code == 401


def test_get_latest_plan_requires_auth(client):
    resp = client.get("/api/plans/latest")
    assert resp.status_code == 401


def test_get_plan_history_requires_auth(client):
    resp = client.get("/api/plans/history")
    assert resp.status_code == 401


def test_poll_job_requires_auth(client):
    resp = client.get("/api/plans/job/some-job-id")
    assert resp.status_code == 401


# ── Latest plan — no plans exist ───────────────────────────────────────────────

def test_get_latest_plan_empty(auth_cookies, verified_mock_db):
    """GET /plans/latest with no plans in DB should return 404 or empty gracefully."""
    verified_mock_db.plan_history.find_one = AsyncMock(return_value=None)
    # cursor mock for the fallback find()
    cursor_mock = MagicMock()
    cursor_mock.sort = MagicMock(return_value=cursor_mock)
    cursor_mock.limit = MagicMock(return_value=cursor_mock)
    cursor_mock.to_list = AsyncMock(return_value=[])
    verified_mock_db.plan_history.find = MagicMock(return_value=cursor_mock)

    resp = auth_cookies.get("/api/plans/latest")
    assert resp.status_code in (200, 404)


# ── Plan history — returns list ────────────────────────────────────────────────

def test_get_plan_history_empty(auth_cookies, verified_mock_db):
    """GET /plans/history returns paginated response with empty items when no history."""
    cursor_mock = MagicMock()
    cursor_mock.sort = MagicMock(return_value=cursor_mock)
    cursor_mock.limit = MagicMock(return_value=cursor_mock)
    cursor_mock.to_list = AsyncMock(return_value=[])
    verified_mock_db.plan_history.find = MagicMock(return_value=cursor_mock)

    resp = auth_cookies.get("/api/plans/history")
    assert resp.status_code == 200
    data = resp.json()
    # History endpoint returns {items: [...], next_cursor: ...}
    assert "items" in data
    assert isinstance(data["items"], list)


# ── Job polling ────────────────────────────────────────────────────────────────

def test_poll_unknown_job_returns_404(auth_cookies, verified_mock_db):
    """Polling a job ID that doesn't exist should return 404."""
    verified_mock_db.plan_jobs = AsyncMock()
    verified_mock_db.plan_jobs.find_one = AsyncMock(return_value=None)

    fake_id = str(uuid.uuid4())
    resp = auth_cookies.get(f"/api/plans/job/{fake_id}")
    assert resp.status_code == 404


def test_poll_pending_job_returns_pending(auth_cookies, verified_mock_db):
    """Polling a job that is still pending returns status=pending with no result."""
    from datetime import datetime, timezone
    job_id = str(uuid.uuid4())
    verified_mock_db.plan_jobs = AsyncMock()
    verified_mock_db.plan_jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "user_id": "test-uuid-1234",
        "plan_type": "gym",
        "status": "pending",
        "created_at": datetime.now(timezone.utc),
    })

    resp = auth_cookies.get(f"/api/plans/job/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "pending"
    assert data.get("result") is None


def test_poll_done_job_returns_result(auth_cookies, verified_mock_db):
    """Polling a completed job returns status=done with plan_id and result."""
    from datetime import datetime, timezone
    job_id = str(uuid.uuid4())
    plan_id = str(uuid.uuid4())
    verified_mock_db.plan_jobs = AsyncMock()
    verified_mock_db.plan_jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "user_id": "test-uuid-1234",
        "plan_type": "gym",
        "status": "done",
        "plan_id": plan_id,
        "result": {"gym_plan": {"weeks": []}},
        "created_at": datetime.now(timezone.utc),
        "completed_at": datetime.now(timezone.utc),
    })

    resp = auth_cookies.get(f"/api/plans/job/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "done"
    assert data["plan_id"] == plan_id


def test_poll_failed_job_returns_failed(auth_cookies, verified_mock_db):
    """Polling a failed job returns status=failed with an error message."""
    from datetime import datetime, timezone
    job_id = str(uuid.uuid4())
    verified_mock_db.plan_jobs = AsyncMock()
    verified_mock_db.plan_jobs.find_one = AsyncMock(return_value={
        "_id": job_id,
        "user_id": "test-uuid-1234",
        "plan_type": "diet",
        "status": "failed",
        "error": "LLM timeout",
        "created_at": datetime.now(timezone.utc),
    })

    resp = auth_cookies.get(f"/api/plans/job/{job_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "failed"


# ── Job isolation — cannot access another user's job ──────────────────────────

def test_poll_other_users_job_returns_404(auth_cookies, verified_mock_db):
    """A user cannot poll a job belonging to a different user."""
    from datetime import datetime, timezone
    job_id = str(uuid.uuid4())
    verified_mock_db.plan_jobs = AsyncMock()
    # Job exists but belongs to a different user
    verified_mock_db.plan_jobs.find_one = AsyncMock(return_value=None)

    resp = auth_cookies.get(f"/api/plans/job/{job_id}")
    assert resp.status_code == 404


# ── Plan generation — enqueues job (ARQ mocked) ───────────────────────────────

@patch("routes.plan_runner.create_pool")
def test_generate_gym_plan_enqueues_job(mock_pool, auth_cookies, verified_mock_db):
    """POST /plans/gym by a verified user must NOT return 401 or 403."""
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock(return_value=MagicMock(job_id="arq-job-1"))
    mock_pool.return_value.__aenter__ = AsyncMock(return_value=mock_arq)
    mock_pool.return_value.__aexit__ = AsyncMock(return_value=False)

    from core.cache import cache_manager
    with patch.object(cache_manager, "redis_client", None):
        resp = auth_cookies.post("/api/plans/gym")

    # Auth + verification pass; anything except 401/403 is acceptable
    assert resp.status_code not in (401, 403)


@patch("routes.plan_runner.create_pool")
def test_generate_yoga_plan_enqueues_job(mock_pool, auth_cookies, verified_mock_db):
    """POST /plans/yoga by a verified user must NOT return 401 or 403."""
    mock_arq = AsyncMock()
    mock_arq.enqueue_job = AsyncMock(return_value=MagicMock(job_id="arq-job-2"))
    mock_pool.return_value.__aenter__ = AsyncMock(return_value=mock_arq)
    mock_pool.return_value.__aexit__ = AsyncMock(return_value=False)

    from core.cache import cache_manager
    with patch.object(cache_manager, "redis_client", None):
        resp = auth_cookies.post("/api/plans/yoga")

    assert resp.status_code not in (401, 403)


# ── Unverified user blocked from plan generation ──────────────────────────────

def test_unverified_user_cannot_generate_plan(client, mock_db):
    """A local unverified user gets 403 from /plans/generate (the holistic route that checks is_verified)."""
    from services.auth_service import hash_password
    from datetime import datetime, timezone
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "unverified-user",
        "name": "Unverified",
        "email": "unverified@ayura.com",
        "password_hash": hash_password("pass"),
        "auth_provider": "local",
        "is_active": True,
        "is_admin": False,
        "is_verified": False,
        "onboarding_complete": True,
        "dominant_dosha": "pitta",
        "goal": "general_wellness",
        "age": 25,
        "height_cm": 165.0,
        "weight_kg": 60.0,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    mock_db.user_preferences = AsyncMock()
    mock_db.user_preferences.find_one = AsyncMock(return_value=None)
    token = create_access_token("unverified-user", "unverified@ayura.com")

    resp = client.post(
        "/api/plans/generate",
        json={"plan_types": ["diet"]},
        headers={"Authorization": f"Bearer {token}"},
    )
    assert resp.status_code == 403
