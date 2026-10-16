"""PUT /api/plans/routine/schedule — the user moves a slot of their routine.

The change is stored beside the form's answers (saving the form replaces the
whole `routine` document, which would wipe it), the day is rebuilt by the engine,
and the previous coaching is carried over: moving lunch must not bill an LLM call
or a plan from the daily quota.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token


@pytest.fixture
def client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test", "email": "test@ayura.com", "auth_provider": "local",
        "is_active": True, "is_admin": False, "is_verified": True, "onboarding_complete": True,
        "dominant_dosha": "vata", "age": 30, "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc)})
    store = {"user_id": "test-uuid-1234",
             "routine": {"wake_preference": "natural", "occupation_type": "moderately_active",
                         "agni_type_self_report": "assessed", "intermittent_fasting": "no",
                         "fasting_days": [], "exclude_gym_plan": True, "exclude_yoga_plan": True}}

    async def update_one(_q, update, **_k):
        store.update(update["$set"])
    mock_db.user_preferences = AsyncMock()
    mock_db.user_preferences.find_one = AsyncMock(side_effect=lambda *a, **k: dict(store))
    mock_db.user_preferences.update_one = AsyncMock(side_effect=update_one)

    previous = {"plan_data": {"routine_plan": {
        "enriched": True, "enrichment_model": "azure",
        "sleep_coaching": "Be in bed by 10 PM. Rest restores Ojas."}}}

    async def find_plan(query, *a, **k):
        return None if "preference_hash" in query else previous
    mock_db.plan_history.find_one = AsyncMock(side_effect=find_plan)
    mock_db.plan_history.insert_one = AsyncMock()

    c = TestClient(app)
    c.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    c.store = store
    return c


def _put(client, body):
    with patch("routes.plans.consume_plan_quota", new=AsyncMock()) as quota, \
            patch("routes.plans.log_plan_generated", new=AsyncMock()):
        resp = client.put("/api/plans/routine/schedule", json=body)
    return resp, quota


def test_moving_a_slot_saves_it_beside_the_form_and_bills_nothing(client):
    resp, quota = _put(client, {"slot_id": "lunch", "time": "14:00"})
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    lunch = next(s for s in plan["weekly_routine"][0]["timeline"] if s["id"] == "lunch")
    assert lunch["time"] == "2:00 PM" and lunch["user_set"]
    assert client.store["routine_schedule"]["custom_times"] == {"lunch": "14:00"}
    assert "custom_times" not in client.store["routine"]
    quota.assert_not_awaited()
    assert plan["sleep_coaching"] == "Rest restores Ojas."


def test_one_day_then_put_back_for_every_day(client):
    _put(client, {"slot_id": "work", "time": "off", "day": "saturday"})
    assert client.store["routine_schedule"]["custom_times_by_day"] == {"saturday": {"work": "off"}}
    _put(client, {"slot_id": "work", "time": None})
    assert client.store["routine_schedule"] == {"custom_times": {}, "custom_times_by_day": {}}


@pytest.mark.parametrize("body", [
    {"slot_id": "lunch", "time": "off"},
    {"slot_id": "nonsense", "time": "10:00"},
    {"slot_id": "work", "time": "25:00"},
    {"slot_id": "work", "time": "09:00", "day": "someday"},
])
def test_a_change_the_routine_cannot_honour_is_refused(client, body):
    resp, _ = _put(client, body)
    assert resp.status_code == 422


def test_reset_all(client):
    _put(client, {"slot_id": "wake", "time": "07:00"})
    _put(client, {"reset_all": True})
    assert client.store["routine_schedule"] == {"custom_times": {}, "custom_times_by_day": {}}


def _req(client, method, url, body=None):
    with patch("routes.plans.consume_plan_quota", new=AsyncMock()) as quota, \
            patch("routes.plans.log_plan_generated", new=AsyncMock()):
        resp = client.request(method, url, json=body)
    return resp, quota


def test_an_item_can_be_added_edited_and_removed(client):
    resp, quota = _req(client, "POST", "/api/plans/routine/items",
                       {"title": "School pickup", "time": "15:15", "duration_minutes": 30, "days": ["Monday"]})
    assert resp.status_code == 200, resp.text
    quota.assert_not_awaited()
    [item] = client.store["routine_schedule"]["custom_items"]
    assert item["days"] == ["monday"] and item["id"].startswith("custom_")
    slot = next(s for s in resp.json()["weekly_routine"][0]["timeline"] if s["id"] == item["id"])
    assert slot["time"] == "3:15 PM"

    resp, _ = _req(client, "PUT", f"/api/plans/routine/items/{item['id']}",
                   {"title": "School pickup", "time": "15:45", "duration_minutes": 30})
    assert client.store["routine_schedule"]["custom_items"][0]["time"] == "15:45"
    # A time edit elsewhere keeps the items.
    _req(client, "PUT", "/api/plans/routine/schedule", {"slot_id": "lunch", "time": "13:30"})
    assert len(client.store["routine_schedule"]["custom_items"]) == 1
    resp, _ = _req(client, "DELETE", f"/api/plans/routine/items/{item['id']}")
    assert resp.status_code == 200 and client.store["routine_schedule"]["custom_items"] == []


@pytest.mark.parametrize("body", [
    {"title": "", "time": "10:00"},
    {"title": "x", "time": "25:00"},
    {"title": "x", "time": "10:00", "days": ["someday"]},
    {"title": "x", "time": "10:00", "category": "bogus"},
])
def test_an_item_the_routine_cannot_hold_is_refused(client, body):
    resp, _ = _req(client, "POST", "/api/plans/routine/items", body)
    assert resp.status_code == 422


def test_editing_an_item_that_does_not_exist_is_a_404(client):
    resp, _ = _req(client, "DELETE", "/api/plans/routine/items/custom_nope000")
    assert resp.status_code == 404
