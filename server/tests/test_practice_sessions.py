"""
Practice session API tests.

Covers the endpoint that turned the yoga plan from a document into something the
app knows was actually practised: auth guards, validation, the timeline event,
and the streak arithmetic (which is easy to get subtly wrong — two sessions in
one day must not count twice, and today's missing session must not break a
streak before the user has practised).
"""
from datetime import datetime, timezone, timedelta
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from routes.practice import _streak_days, _completion_percent, PracticeSessionLog
from services.auth_service import create_access_token


@pytest.fixture
def client():
    yield TestClient(app)


@pytest.fixture
def auth_client(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


@pytest.fixture
def practice_db(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.practice_sessions = AsyncMock()
    mock_db.practice_sessions.insert_one = AsyncMock(
        return_value=MagicMock(inserted_id="session-1"))
    mock_db.practice_sessions.count_documents = AsyncMock(return_value=3)

    def _empty_cursor(*_args, **_kwargs):
        cursor = MagicMock()
        cursor.sort = MagicMock(return_value=cursor)

        async def _aiter():
            for item in ():
                yield item
        cursor.__aiter__ = lambda _self: _aiter()
        return cursor

    mock_db.practice_sessions.find = MagicMock(side_effect=_empty_cursor)
    mock_db.timeline = AsyncMock()
    mock_db.timeline.insert_one = AsyncMock()
    return mock_db


VALID_SESSION = {
    "plan_id": "yoga_test_1", "feature": "yoga", "week": 1, "day": 2,
    "duration_seconds": 1780, "segments_total": 31, "segments_completed": 31,
    "completed": True, "skipped_pose_ids": [],
}


# ── Auth ─────────────────────────────────────────────────────────────────────

def test_log_session_requires_auth(client):
    assert client.post("/api/practice/session", json=VALID_SESSION).status_code == 401


def test_summary_requires_auth(client):
    assert client.get("/api/practice/summary").status_code == 401


# ── Logging ──────────────────────────────────────────────────────────────────

def test_logging_a_session_writes_a_timeline_event(auth_client, practice_db):
    resp = auth_client.post("/api/practice/session", json=VALID_SESSION)
    assert resp.status_code == 200, resp.text
    body = resp.json()
    assert body["id"] == "session-1"
    assert body["sessions_this_week"] == 3

    practice_db.timeline.insert_one.assert_awaited_once()
    event = practice_db.timeline.insert_one.await_args.args[0]
    assert event["event_type"] == "practice_completed"
    assert event["details"]["completion_percent"] == 100
    assert event["details"]["duration_minutes"] == 30


def test_partial_session_is_recorded_as_incomplete(auth_client, practice_db):
    resp = auth_client.post("/api/practice/session", json={
        **VALID_SESSION, "segments_completed": 12, "completed": False,
    })
    assert resp.status_code == 200
    stored = practice_db.practice_sessions.insert_one.await_args.args[0]
    assert stored["completed"] is False
    assert stored["completion_percent"] == 39


def test_completed_segments_cannot_exceed_the_total(auth_client, practice_db):
    resp = auth_client.post("/api/practice/session", json={
        **VALID_SESSION, "segments_total": 10, "segments_completed": 40,
    })
    assert resp.status_code == 400


def test_an_absurdly_long_session_is_rejected(auth_client, practice_db):
    """A forgotten tab is not a practice, and would poison the averages."""
    resp = auth_client.post("/api/practice/session", json={
        **VALID_SESSION, "duration_seconds": 60 * 60 * 9,
    })
    assert resp.status_code == 422


@pytest.mark.parametrize("field,value", [("week", 9), ("day", 0), ("duration_seconds", -5)])
def test_out_of_range_values_are_rejected(auth_client, practice_db, field, value):
    resp = auth_client.post("/api/practice/session", json={**VALID_SESSION, field: value})
    assert resp.status_code == 422


# ── Completion percentage ────────────────────────────────────────────────────

@pytest.mark.parametrize("total,done,completed,expected", [
    (31, 31, True, 100),
    (31, 0, False, 0),
    (10, 5, False, 50),
    (0, 0, True, 100),   # a session with no segments, but finished
    (0, 0, False, 0),
])
def test_completion_percent(total, done, completed, expected):
    log = PracticeSessionLog(
        week=1, day=1, duration_seconds=60, segments_total=total,
        segments_completed=done, completed=completed)
    assert _completion_percent(log) == expected


# ── Streaks ──────────────────────────────────────────────────────────────────

def _db_with_practice_days(offsets, now):
    """A db whose practice_sessions.find yields sessions N days before `now`."""
    db = MagicMock()
    docs = [{"started_at": now - timedelta(days=o)} for o in offsets]

    def _find(*_args, **_kwargs):
        cursor = MagicMock()

        async def _aiter():
            for d in docs:
                yield d
        cursor.__aiter__ = lambda _self: _aiter()
        return cursor

    db.practice_sessions.find = MagicMock(side_effect=_find)
    return db


@pytest.mark.asyncio
async def test_streak_counts_consecutive_days():
    now = datetime.now(timezone.utc)
    db = _db_with_practice_days([0, 1, 2, 3], now)
    assert await _streak_days(db, "u1", now) == 4


@pytest.mark.asyncio
async def test_two_sessions_in_one_day_count_once():
    now = datetime.now(timezone.utc)
    db = _db_with_practice_days([0, 0, 0, 1], now)
    assert await _streak_days(db, "u1", now) == 2


@pytest.mark.asyncio
async def test_streak_survives_until_today_is_missed_twice():
    """Practised yesterday but not yet today — the streak is alive, not broken."""
    now = datetime.now(timezone.utc)
    db = _db_with_practice_days([1, 2, 3], now)
    assert await _streak_days(db, "u1", now) == 3


@pytest.mark.asyncio
async def test_a_gap_ends_the_streak():
    now = datetime.now(timezone.utc)
    db = _db_with_practice_days([0, 1, 4, 5], now)
    assert await _streak_days(db, "u1", now) == 2


@pytest.mark.asyncio
async def test_no_practice_is_a_zero_streak():
    now = datetime.now(timezone.utc)
    db = _db_with_practice_days([], now)
    assert await _streak_days(db, "u1", now) == 0
