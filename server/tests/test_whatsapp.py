"""WhatsApp: who can receive a message, what it says, and what it costs to get wrong.

A number receives nothing until its owner enters the code sent to it, and each message
is billed, so these hold the verification, the opt-in per kind, and that only the
callers that ask for WhatsApp ever reach it.
"""
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from services import whatsapp_service as wa
from services.auth_service import create_access_token


# ── Pure helpers ────────────────────────────────────────────────────────────

@pytest.mark.parametrize("raw,expected", [
    ("98765 43210", "+919876543210"),
    ("09876543210", "+919876543210"),
    ("+91 98765-43210", "+919876543210"),
    ("0044 7700 900123", "+447700900123"),
    ("+1 415 555 0100", "+14155550100"),
    ("12345", None),
    ("not a number", None),
])
def test_phone_numbers_are_read_as_indian_unless_they_say_otherwise(raw, expected):
    assert wa.normalise_phone(raw) == expected


def test_a_masked_number_shows_only_its_ends():
    assert wa.mask("+919876543210") == "+91 ••••••3210"


def test_template_parameters_meta_would_reject_are_cleaned():
    """A newline, a tab or five spaces in a parameter fails the whole message."""
    out = wa.clean_param("Breakfast:\nPoha\t\tLunch:     Dal")
    assert "\n" not in out and "\t" not in out and "  " not in out
    assert len(wa.clean_param("x" * 5000)) <= 900


def _diet(started: datetime):
    day = {"breakfast": {"meal_name": "Moong Chilla"}, "lunch": {"meal_name": "Dal Khichdi"},
           "dinner": {"meal_name": "Lauki Sabzi with Roti"}, "snack": {"meal_name": "Makhana"}}
    return {"generated_at": started, "plan_data": {"diet_plan": {"diet_weeks": [
        {"week_number": n, "daily_plan": {d: day for d in wa._DAY_FULL}} for n in (1, 2, 3, 4)]}}}


def test_todays_meals_follow_the_plans_own_calendar():
    started = datetime(2026, 10, 12, 9, 0, tzinfo=timezone.utc)
    text = wa.todays_meals(_diet(started), date(2026, 10, 17))
    assert text == "Breakfast: Moong Chilla; Lunch: Dal Khichdi; Dinner: Lauki Sabzi with Roti"


def test_no_meals_before_a_plan_starts_or_after_it_ends():
    started = datetime(2026, 10, 12, tzinfo=timezone.utc)
    assert wa.todays_meals(_diet(started), date(2026, 10, 11)) is None
    assert wa.todays_meals(_diet(started), date(2026, 11, 9)) is None   # day 28
    assert wa.todays_meals(None, date(2026, 10, 17)) is None


def test_the_morning_message_never_shames_a_missing_streak():
    assert wa.daily_text("Asha Rao", None, 0)[2] == "Log one thing today to start a streak."
    assert wa.daily_text("Asha Rao", "x", 6) == ["Asha", "x", "You are on a 6-day streak."]


def test_only_a_verified_opted_in_number_receives_anything():
    user = {"whatsapp": {"phone": "+919876543210", "verified_at": datetime.now(timezone.utc),
                         "reminders": True, "daily": False}}
    assert wa.opted_in(user, "reminders") == "+919876543210"
    assert wa.opted_in(user, "daily") is None
    unverified = {"whatsapp": {"phone": "+919876543210", "reminders": True}}
    assert wa.opted_in(unverified, "reminders") is None


# ── Who reaches WhatsApp ────────────────────────────────────────────────────

def test_only_reminders_and_the_morning_message_use_whatsapp():
    """Each message is billed. A notification goes to WhatsApp only when its caller
    passes whatsapp=True; today that is the reminder dispatcher alone."""
    import re
    root = Path(__file__).resolve().parents[1]
    call = re.compile(r"^\s+whatsapp=True\s*[,)]", re.M)   # a keyword argument, not prose
    callers = [p.name for p in [root / "worker.py", *root.glob("routes/*.py"), *root.glob("services/*.py")]
               if call.search(p.read_text())]
    assert callers == ["worker.py"], callers


def test_the_profile_endpoint_cannot_mark_a_number_verified():
    from schemas.user_schema import UserProfileUpdate
    upd = UserProfileUpdate(**{"name": "A", "whatsapp": {"phone": "+911", "verified_at": "now"}})
    assert "whatsapp" not in upd.model_dump(exclude_unset=True)


# ── The verification flow ───────────────────────────────────────────────────

@pytest.fixture
def client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.users.update_one = AsyncMock()
    mock_db.whatsapp_verifications = MagicMock()
    mock_db.whatsapp_verifications.find_one = AsyncMock(return_value=None)
    mock_db.whatsapp_verifications.update_one = AsyncMock()
    mock_db.whatsapp_verifications.delete_one = AsyncMock()
    c = TestClient(app)
    c.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return c


@pytest.fixture
def enabled():
    with patch.object(wa.settings, "WHATSAPP_ENABLED", True), \
         patch("routes.whatsapp.send_template", new=AsyncMock(return_value=True)) as send:
        yield send


def test_nothing_is_offered_while_whatsapp_is_off(client):
    assert client.get("/api/whatsapp/status").json()["available"] is False
    r = client.post("/api/whatsapp/start", json={"phone": "9876543210", "consent": True})
    assert r.status_code == 503


def test_a_code_needs_consent_and_a_real_number(client, enabled):
    assert client.post("/api/whatsapp/start", json={"phone": "9876543210", "consent": False}).status_code == 422
    assert client.post("/api/whatsapp/start", json={"phone": "12345", "consent": True}).status_code == 422
    enabled.assert_not_called()


def test_the_code_is_sent_and_stored_hashed(client, mock_db, enabled):
    r = client.post("/api/whatsapp/start", json={"phone": "98765 43210", "consent": True})
    assert r.status_code == 200 and r.json()["phone"] == "+91 ••••••3210"
    to, template, params = enabled.call_args[0]
    code = params[0]
    assert to == "+919876543210" and len(code) == 6
    stored = mock_db.whatsapp_verifications.update_one.call_args[0][1]["$set"]
    assert code not in str(stored) and stored["tries"] == 0


def test_a_second_code_within_a_minute_is_refused(client, mock_db, enabled):
    mock_db.whatsapp_verifications.find_one = AsyncMock(return_value={
        "sent_at": datetime.now(timezone.utc) - timedelta(seconds=20)})
    assert client.post("/api/whatsapp/start", json={"phone": "9876543210", "consent": True}).status_code == 429


def test_five_codes_a_day_is_the_limit(client, mock_db, enabled):
    mock_db.whatsapp_verifications.find_one = AsyncMock(return_value={
        "sent_at": datetime.now(timezone.utc) - timedelta(hours=1),
        "sends_day": datetime.now(timezone.utc).date().isoformat(), "sends": 5})
    assert client.post("/api/whatsapp/start", json={"phone": "9876543210", "consent": True}).status_code == 429


def _pending(code="123456", **kw):
    from routes.whatsapp import _hash
    return {"_id": "test-uuid-1234", "phone": "+919876543210",
            "code_hash": _hash("test-uuid-1234", "+919876543210", code),
            "expires_at": datetime.now(timezone.utc) + timedelta(minutes=5), "tries": 0, **kw}


def test_the_right_code_verifies_and_turns_on_reminders_only(client, mock_db):
    mock_db.whatsapp_verifications.find_one = AsyncMock(return_value=_pending())
    r = client.post("/api/whatsapp/verify", json={"code": "123456"})
    assert r.status_code == 200
    body = r.json()
    assert body["verified"] and body["reminders"] and not body["daily"]
    saved = mock_db.users.update_one.call_args[0][1]["$set"]["whatsapp"]
    assert saved["phone"] == "+919876543210" and saved["consent_at"]


@pytest.mark.parametrize("pending,code,status", [
    ({}, "654321", 400),                                                           # wrong
    ({"expires_at": datetime.now(timezone.utc) - timedelta(seconds=1)}, "123456", 400),  # expired
    ({"tries": 5}, "123456", 429),                                                 # spent
])
def test_a_wrong_expired_or_exhausted_code_does_not_verify(client, mock_db, pending, code, status):
    mock_db.whatsapp_verifications.find_one = AsyncMock(return_value=_pending(**pending))
    assert client.post("/api/whatsapp/verify", json={"code": code}).status_code == status
    for call in mock_db.users.update_one.call_args_list:
        assert "whatsapp" not in str(call)


def test_settings_need_a_verified_number_and_a_real_time(client, mock_db):
    assert client.put("/api/whatsapp/settings", json={"daily": True}).status_code == 400
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "T", "email": "t@a.c", "auth_provider": "local",
        "is_active": True, "is_verified": True, "onboarding_complete": True,
        "whatsapp": {"phone": "+919876543210", "verified_at": datetime.now(timezone.utc), "reminders": True},
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc)})
    assert client.put("/api/whatsapp/settings", json={"daily_time": "25:00"}).status_code == 422
    r = client.put("/api/whatsapp/settings", json={"daily": True, "daily_time": "06:30"})
    assert r.status_code == 200 and r.json()["daily"] and r.json()["daily_time"] == "06:30"


# ── The morning message ─────────────────────────────────────────────────────

class _Users:
    def __init__(self, docs):
        self.docs = docs
        self.updates = []

    def find(self, flt, projection=None):
        docs = self.docs

        class C:
            def __aiter__(self):
                self.i = iter(docs)
                return self

            async def __anext__(self):
                try:
                    return next(self.i)
                except StopIteration:
                    raise StopAsyncIteration
        return C()

    async def update_one(self, flt, upd):
        self.updates.append(upd)


def test_the_morning_message_goes_once_at_the_chosen_local_time():
    started = datetime(2026, 10, 12, tzinfo=timezone.utc)
    user = {"_id": "u1", "name": "Asha", "timezone": "Asia/Kolkata",
            "whatsapp": {"phone": "+919876543210", "verified_at": started, "daily": True,
                         "daily_time": "07:00"}}
    db = MagicMock()
    db.users = _Users([user])
    db.plan_history.find_one = AsyncMock(return_value=_diet(started))
    at_7 = datetime(2026, 10, 17, 1, 30, tzinfo=timezone.utc)  # 07:00 IST
    with patch.object(wa.settings, "WHATSAPP_ENABLED", True), \
         patch("services.whatsapp_service.send_template", new=AsyncMock(return_value=True)) as send, \
         patch("services.rewards.activity", new=AsyncMock(return_value={"dates": set(), "kinds": set()})):
        import asyncio
        assert asyncio.run(wa.send_daily_messages(db, at_7)) == 1
        params = send.call_args[0][2]
        assert params[0] == "Asha" and "Moong Chilla" in params[1]
        # the same minute again, after the day was marked: nothing more
        user["whatsapp"]["daily_sent_on"] = "2026-10-17"
        assert asyncio.run(wa.send_daily_messages(db, at_7)) == 0
        # a different minute: nothing
        user["whatsapp"].pop("daily_sent_on")
        assert asyncio.run(wa.send_daily_messages(db, at_7 + timedelta(minutes=1))) == 0
