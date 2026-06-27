"""
Tests for the progress summary streak data consumed by the dashboard StreakCard.

The StreakCard reads streak_data.{current_streak_days, active_dates, checked_in_today};
these must be derived from the user's actual progress_logs (regression guard for the
field-name mismatch that left the card stuck at 0).
"""

import pytest
from datetime import datetime, timezone, timedelta, date
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token


class _FakeCursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    async def to_list(self, length=None):
        return self._docs[:length] if length else self._docs


@pytest.fixture
def client():
    yield TestClient(app)


def _log(day: date):
    return {"_id": f"log-{day.isoformat()}", "user_id": "test-uuid-1234",
            "date": datetime(day.year, day.month, day.day, 9, tzinfo=timezone.utc),
            "weight_kg": 70, "mood": "good", "adherence_percent": 80}


def test_progress_summary_requires_auth(client):
    assert client.get("/api/progress/summary").status_code == 401


def test_streak_and_active_dates_from_logs(client, mock_db):
    today = date.today()
    docs = [_log(today), _log(today - timedelta(days=1))]  # 2 consecutive days
    mock_db.progress_logs = MagicMock()
    mock_db.progress_logs.find = MagicMock(return_value=_FakeCursor(docs))

    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    res = client.get("/api/progress/summary")
    assert res.status_code == 200

    sd = res.json()["streak_data"]
    assert sd["current_streak_days"] == 2
    assert sd["current_streak"] == 2          # dashboard alias
    assert sd["checked_in_today"] is True
    assert today.isoformat() in sd["active_dates"]
    assert (today - timedelta(days=1)).isoformat() in sd["active_dates"]


def test_streak_breaks_when_today_missing(client, mock_db):
    today = date.today()
    docs = [_log(today - timedelta(days=2)), _log(today - timedelta(days=3))]
    mock_db.progress_logs = MagicMock()
    mock_db.progress_logs.find = MagicMock(return_value=_FakeCursor(docs))

    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    res = client.get("/api/progress/summary")
    assert res.status_code == 200

    sd = res.json()["streak_data"]
    assert sd["current_streak_days"] == 0     # nothing logged today → streak broken
    assert sd["checked_in_today"] is False
