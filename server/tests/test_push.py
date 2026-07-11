"""
Tests for web push subscriptions + the onboarding reminder seed.
"""

import pytest
from datetime import datetime, timezone
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from fastapi.testclient import TestClient

from main import app
from config import settings
from services.auth_service import create_access_token


@pytest.fixture
def client():
    yield TestClient(app)


def _auth(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))


SUB = {
    "endpoint": "https://fcm.googleapis.com/fcm/send/abc123def456ghi789",
    "keys": {"p256dh": "BExamplePublicKeyMaterial", "auth": "authsecret"},
}


def test_vapid_key_endpoint_reports_disabled_without_keys(client, mock_db):
    _auth(client)
    with patch.object(settings, "VAPID_PUBLIC_KEY", None):
        res = client.get("/api/push/vapid-public-key")
    assert res.status_code == 200
    assert res.json() == {"enabled": False, "public_key": None}


def test_vapid_key_endpoint_requires_auth(client, mock_db):
    res = client.get("/api/push/vapid-public-key")
    assert res.status_code == 401


def test_subscribe_upserts_by_endpoint(client, mock_db):
    mock_db.push_subscriptions = MagicMock()
    mock_db.push_subscriptions.update_one = AsyncMock()
    _auth(client)
    with patch.object(settings, "VAPID_PUBLIC_KEY", "BFakeKey"):
        res = client.post("/api/push/subscribe", json=SUB)
    assert res.status_code == 200
    assert res.json() == {"subscribed": True}
    filt, update = mock_db.push_subscriptions.update_one.call_args.args
    assert filt == {"endpoint": SUB["endpoint"]}
    assert update["$set"]["user_id"] == "test-uuid-1234"
    assert update["$set"]["subscription"]["keys"]["p256dh"] == SUB["keys"]["p256dh"]
    assert mock_db.push_subscriptions.update_one.call_args.kwargs["upsert"] is True


def test_subscribe_503_when_push_unconfigured(client, mock_db):
    _auth(client)
    with patch.object(settings, "VAPID_PUBLIC_KEY", None):
        res = client.post("/api/push/subscribe", json=SUB)
    assert res.status_code == 503


def test_unsubscribe_scopes_to_caller(client, mock_db):
    mock_db.push_subscriptions = MagicMock()
    mock_db.push_subscriptions.delete_one = AsyncMock()
    _auth(client)
    res = client.request("DELETE", "/api/push/subscribe", json={"endpoint": SUB["endpoint"]})
    assert res.status_code == 200
    assert mock_db.push_subscriptions.delete_one.call_args.args[0] == {
        "endpoint": SUB["endpoint"],
        "user_id": "test-uuid-1234",
    }


# ── notification_service push channel ────────────────────────────────────────

@pytest.mark.asyncio
async def test_send_push_prunes_gone_subscriptions():
    from services.notification_service import _send_push
    from pywebpush import WebPushException

    db = MagicMock()
    db.user_preferences.find_one = AsyncMock(return_value={})
    sub_doc = {"_id": "s1", "user_id": "u1", "subscription": SUB}

    async def _cursor(_filt):
        yield sub_doc

    db.push_subscriptions.find = lambda f: _cursor(f)
    db.push_subscriptions.delete_one = AsyncMock()

    gone = WebPushException("gone", response=SimpleNamespace(status_code=410))
    with patch.object(settings, "VAPID_PRIVATE_KEY", "priv"), \
         patch.object(settings, "VAPID_PUBLIC_KEY", "pub"), \
         patch("pywebpush.webpush", side_effect=gone):
        await _send_push(db, "u1", "T", "B")

    db.push_subscriptions.delete_one.assert_awaited_once_with({"_id": "s1"})


@pytest.mark.asyncio
async def test_send_push_respects_opt_out():
    from services.notification_service import _send_push

    db = MagicMock()
    db.user_preferences.find_one = AsyncMock(return_value={"push_notifications": False})
    db.push_subscriptions.find = MagicMock(side_effect=AssertionError("should not query subs"))
    with patch.object(settings, "VAPID_PRIVATE_KEY", "priv"), \
         patch.object(settings, "VAPID_PUBLIC_KEY", "pub"):
        await _send_push(db, "u1", "T", "B")  # no exception, no sub lookup


# ── onboarding reminder seed ─────────────────────────────────────────────────

def _onboarding_user(complete=False):
    return {
        "_id": "test-uuid-1234",
        "name": "Test User",
        "email": "test@ayura.com",
        "auth_provider": "local",
        "is_active": True,
        "is_verified": True,
        "onboarding_complete": complete,
        "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    }


ONBOARD_BODY = {
    "gender": "female", "age": 30, "height_cm": 165, "weight_kg": 60,
    "timezone": "Asia/Kolkata",
    "dosha_scores": {"vata": 50, "pitta": 30, "kapha": 20},
}


def test_onboarding_completion_seeds_default_reminder(client, mock_db):
    mock_db.users.find_one = AsyncMock(return_value=_onboarding_user(complete=False))
    mock_db.users.update_one = AsyncMock()
    mock_db.reminders = MagicMock()
    mock_db.reminders.count_documents = AsyncMock(return_value=0)
    mock_db.reminders.insert_one = AsyncMock()
    _auth(client)
    res = client.put("/api/profile/me", json=ONBOARD_BODY)
    assert res.status_code == 200
    seeded = mock_db.reminders.insert_one.call_args.args[0]
    assert seeded["timezone"] == "Asia/Kolkata"
    assert seeded["time"] == "07:00"
    assert seeded["is_active"] is True
    assert seeded["days"] == []


def test_no_seed_when_already_onboarded(client, mock_db):
    mock_db.users.find_one = AsyncMock(return_value=_onboarding_user(complete=True))
    mock_db.users.update_one = AsyncMock()
    mock_db.reminders = MagicMock()
    mock_db.reminders.insert_one = AsyncMock()
    _auth(client)
    res = client.put("/api/profile/me", json=ONBOARD_BODY)
    assert res.status_code == 200
    mock_db.reminders.insert_one.assert_not_called()


def test_no_seed_without_timezone(client, mock_db):
    mock_db.users.find_one = AsyncMock(return_value=_onboarding_user(complete=False))
    mock_db.users.update_one = AsyncMock()
    mock_db.reminders = MagicMock()
    mock_db.reminders.count_documents = AsyncMock(return_value=0)
    mock_db.reminders.insert_one = AsyncMock()
    _auth(client)
    body = {k: v for k, v in ONBOARD_BODY.items() if k != "timezone"}
    res = client.put("/api/profile/me", json=body)
    assert res.status_code == 200
    mock_db.reminders.insert_one.assert_not_called()


def test_rejects_bogus_timezone(client, mock_db):
    _auth(client)
    res = client.put("/api/profile/me", json={"timezone": "Mars/Olympus_Mons"})
    assert res.status_code == 422
