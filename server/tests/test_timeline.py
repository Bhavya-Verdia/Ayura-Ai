"""
Tests for the Health Timeline endpoint (routes/timeline.py).

Covers:
- _normalize() shape conversion (dict details, bare-string details, timestamps, ids)
- GET /api/timeline auth guard + happy-path pagination/normalization
"""

import pytest
from datetime import datetime, timezone
from unittest.mock import MagicMock
from fastapi.testclient import TestClient

from main import app
from routes.timeline import _normalize
from services.auth_service import create_access_token


# ── _normalize unit tests ───────────────────────────────────────────────────────

def test_normalize_dict_details_passthrough():
    ts = datetime(2026, 6, 25, 8, 30, tzinfo=timezone.utc)
    out = _normalize({
        "_id": "abc123",
        "event_type": "progress_logged",
        "details": {"weight_kg": 72.5, "adherence_percent": 85, "mood": "good"},
        "source": "api",
        "timestamp": ts,
    })
    assert out["id"] == "abc123"
    assert out["event_type"] == "progress_logged"
    assert out["timestamp"] == ts.isoformat()
    assert out["details"]["weight_kg"] == 72.5
    assert out["source"] == "api"


def test_normalize_string_details_mapped_by_event_type():
    sym = _normalize({"_id": 1, "event_type": "symptom_logged", "details": "headache",
                      "timestamp": datetime.now(timezone.utc)})
    assert sym["details"] == {"symptom": "headache"}

    rem = _normalize({"_id": 2, "event_type": "reminder_set", "details": "Drink water at 09:00",
                      "timestamp": datetime.now(timezone.utc)})
    assert rem["details"] == {"reminder": "Drink water at 09:00"}


def test_normalize_unknown_string_details_falls_back_to_info():
    out = _normalize({"_id": 3, "event_type": "mystery", "details": "something",
                      "timestamp": datetime.now(timezone.utc)})
    assert out["details"] == {"info": "something"}


def test_normalize_missing_or_empty_details_is_empty_dict():
    assert _normalize({"_id": 4, "event_type": "x", "timestamp": None})["details"] == {}
    assert _normalize({"_id": 5, "event_type": "x", "details": None})["details"] == {}


def test_normalize_stringifies_id_and_handles_iso_string_timestamp():
    out = _normalize({"_id": 99, "event_type": "x", "timestamp": "2026-06-25T08:30:00+00:00"})
    assert out["id"] == "99"
    assert out["timestamp"] == "2026-06-25T08:30:00+00:00"


# ── Endpoint tests ───────────────────────────────────────────────────────────────

class _FakeCursor:
    """Minimal async cursor supporting .sort().skip().limit() + async iteration."""
    def __init__(self, docs):
        self._docs = list(docs)

    def sort(self, *args, **kwargs):
        return self

    def skip(self, n):
        self._docs = self._docs[n:]
        return self

    def limit(self, n):
        self._docs = self._docs[:n]
        return self

    def __aiter__(self):
        async def _gen():
            for d in self._docs:
                yield d
        return _gen()


@pytest.fixture
def client():
    yield TestClient(app)


def test_timeline_requires_auth(client):
    assert client.get("/api/timeline").status_code == 401


def test_timeline_returns_normalized_events(client, mock_db):
    now = datetime.now(timezone.utc)
    docs = [
        {"_id": "e1", "user_id": "test-uuid-1234", "event_type": "progress_logged",
         "details": {"weight_kg": 70, "adherence_percent": 90, "mood": "great"},
         "source": "api", "timestamp": now},
        {"_id": "e2", "user_id": "test-uuid-1234", "event_type": "symptom_logged",
         "details": "fatigue", "source": "chat", "timestamp": now},
    ]
    mock_db.timeline = MagicMock()
    mock_db.timeline.find = MagicMock(return_value=_FakeCursor(docs))

    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    res = client.get("/api/timeline", params={"offset": 0, "limit": 10})

    assert res.status_code == 200
    body = res.json()
    assert len(body) == 2
    assert body[0]["details"]["weight_kg"] == 70
    assert body[1]["details"] == {"symptom": "fatigue"}


def test_timeline_pagination_slices(client, mock_db):
    now = datetime.now(timezone.utc)
    docs = [{"_id": f"e{i}", "user_id": "test-uuid-1234", "event_type": "x",
             "details": {}, "timestamp": now} for i in range(5)]
    mock_db.timeline = MagicMock()
    mock_db.timeline.find = MagicMock(return_value=_FakeCursor(docs))

    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    res = client.get("/api/timeline", params={"offset": 2, "limit": 2})

    assert res.status_code == 200
    body = res.json()
    assert [e["id"] for e in body] == ["e2", "e3"]
