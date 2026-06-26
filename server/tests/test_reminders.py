"""
Tests for timezone-aware reminders.

Covers:
- reminder_service.reminder_due / fired_token (local-time scheduling)
- partial update (toggle sends only {is_active})
- request validation (HH:MM time, IANA timezone)
"""

import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock
from zoneinfo import ZoneInfo
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.reminder_service import reminder_due, fired_token

# 02:30 UTC == 08:00 Asia/Kolkata (UTC+5:30, no DST)
NOW = datetime(2026, 6, 26, 2, 30, tzinfo=timezone.utc)


# ── reminder_service helpers ─────────────────────────────────────────────────────

def test_due_in_user_timezone():
    r = {"is_active": True, "time": "08:00", "days": [], "timezone": "Asia/Kolkata"}
    assert reminder_due(r, NOW) is True


def test_not_due_when_timezone_differs():
    r = {"is_active": True, "time": "08:00", "days": [], "timezone": "UTC"}  # 02:30 UTC ≠ 08:00
    assert reminder_due(r, NOW) is False


def test_day_filter_uses_local_day():
    local_day = NOW.astimezone(ZoneInfo("Asia/Kolkata")).strftime("%A").lower()
    other_day = "monday" if local_day != "monday" else "tuesday"
    base = {"is_active": True, "time": "08:00", "timezone": "Asia/Kolkata"}
    assert reminder_due({**base, "days": [local_day]}, NOW) is True
    assert reminder_due({**base, "days": [other_day]}, NOW) is False


def test_inactive_never_due():
    r = {"is_active": False, "time": "08:00", "days": [], "timezone": "Asia/Kolkata"}
    assert reminder_due(r, NOW) is False


def test_invalid_timezone_falls_back_to_utc():
    r = {"is_active": True, "time": "02:30", "days": [], "timezone": "Not/AZone"}
    assert reminder_due(r, NOW) is True  # fallback to UTC → 02:30 matches


def test_fired_token_is_local_minute():
    assert fired_token({"timezone": "Asia/Kolkata"}, NOW) == "2026-06-26 08:00"


# ── Route behaviour ──────────────────────────────────────────────────────────────

@pytest.fixture
def client():
    yield TestClient(app)


def _auth(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))


def test_partial_update_toggle_only_is_active(client, mock_db):
    mock_db.reminders = MagicMock()
    mock_db.reminders.update_one = AsyncMock(return_value=SimpleNamespace(matched_count=1))
    mock_db.reminders.find_one = AsyncMock(return_value={
        "_id": "r1", "user_id": "test-uuid-1234", "title": "Med", "time": "08:00",
        "days": [], "reminder_type": "medication", "is_active": False,
        "timezone": "Asia/Kolkata", "created_at": datetime.now(timezone.utc),
    })
    _auth(client)
    res = client.put("/api/reminders/r1", json={"is_active": False})
    assert res.status_code == 200
    assert res.json()["is_active"] is False
    # only is_active should be in the $set — title/time not required for a toggle
    assert mock_db.reminders.update_one.call_args.args[1]["$set"] == {"is_active": False}


def test_create_rejects_malformed_time(client, mock_db):
    _auth(client)
    res = client.post("/api/reminders", json={"title": "X", "time": "25:99"})
    assert res.status_code == 422


def test_create_rejects_invalid_timezone(client, mock_db):
    _auth(client)
    res = client.post("/api/reminders", json={"title": "X", "time": "08:00", "timezone": "Mars/Olympus"})
    assert res.status_code == 422
