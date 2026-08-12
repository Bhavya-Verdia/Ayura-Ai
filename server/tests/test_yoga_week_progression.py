"""
Week-by-week yoga progression API tests.

The plan is now built one week at a time, each week shaped by what the user
reported about the last. This covers the endpoint that does it: auth, ownership,
validation, that the new week is *appended* rather than replacing the practice
history, that feedback is keyed by week so a re-submission corrects rather than
compounds, and that the whole thing works with no feedback at all — nobody
should be blocked from practising by a form.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.yoga_plan_engine import generate_yoga_plan


BASE_PROFILE = {
    "id": "test-uuid-1234", "age": 32, "gender": "female",
    "dominant_dosha": "vata", "medical_history": [],
}
YOGA_PREFS = {
    "yoga_experience": "intermediate", "yoga_goal": "stress_relief",
    "time_available_minutes": 30, "time_of_day_preference": "morning",
    "yoga_style_preference": ["hatha"],
}


@pytest.fixture
def client():
    yield TestClient(app)


@pytest.fixture
def auth_client(client):
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


@pytest.fixture
def week_db(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "dominant_dosha": "vata", "age": 32, "gender": "female",
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.user_preferences.find_one = AsyncMock(return_value={
        "user_id": "test-uuid-1234", "yoga": YOGA_PREFS})

    week_one = generate_yoga_plan(BASE_PROFILE, YOGA_PREFS)
    mock_db.plan_history.find_one = AsyncMock(return_value={
        "_id": "yoga-plan-1", "user_id": "test-uuid-1234", "plan_type": "yoga",
        "plan_data": {"yoga_plan": week_one},
    })
    mock_db.plan_history.update_one = AsyncMock()
    mock_db.timeline = AsyncMock()
    mock_db.timeline.insert_one = AsyncMock()
    mock_db.usage_quota = AsyncMock()
    mock_db.usage_quota.find_one = AsyncMock(return_value=None)
    mock_db.usage_quota.update_one = AsyncMock()
    mock_db._week_one = week_one
    return mock_db


@pytest.fixture(autouse=True)
def _no_llm_enrichment(monkeypatch):
    """The enricher only adds narrative; these tests are about plan structure."""
    async def passthrough(plan, *_args, **_kwargs):
        return plan
    monkeypatch.setattr("services.yoga_plan_enricher.enrich_yoga_plan", passthrough)


REQUEST = {
    "plan_id": "yoga-plan-1",
    "week": 1,
    "feedback": {
        "difficulty": "too_hard", "session_length": "just_right",
        "energy_after": "drained", "days_practised": 6, "dropped_pose_ids": [],
    },
}


# ── Guards ───────────────────────────────────────────────────────────────────

def test_requires_auth(client):
    assert client.post("/api/plans/yoga/next-week", json=REQUEST).status_code == 401


def test_unknown_plan_is_rejected(auth_client, week_db):
    week_db.plan_history.find_one = AsyncMock(return_value=None)
    resp = auth_client.post("/api/plans/yoga/next-week", json=REQUEST)
    assert resp.status_code == 404


def test_a_finished_plan_cannot_be_extended(auth_client, week_db):
    full = generate_yoga_plan(BASE_PROFILE, YOGA_PREFS, weeks=[1, 2, 3, 4])
    week_db.plan_history.find_one = AsyncMock(return_value={
        "_id": "yoga-plan-1", "user_id": "test-uuid-1234",
        "plan_data": {"yoga_plan": full}})
    resp = auth_client.post("/api/plans/yoga/next-week", json=REQUEST)
    assert resp.status_code == 409


@pytest.mark.parametrize("bad", [
    {"difficulty": "banana"},
    {"days_practised": 9},
    {"energy_after": "elated"},
])
def test_invalid_feedback_values_are_rejected(auth_client, week_db, bad):
    resp = auth_client.post("/api/plans/yoga/next-week",
                            json={**REQUEST, "feedback": bad})
    assert resp.status_code == 422


# ── Behaviour ────────────────────────────────────────────────────────────────

def test_the_next_week_is_appended_not_substituted(auth_client, week_db):
    resp = auth_client.post("/api/plans/yoga/next-week", json=REQUEST)
    assert resp.status_code == 200, resp.text
    plan = resp.json()
    assert plan["weeks_generated"] == [1, 2]
    assert [w["week"] for w in plan["four_week_plan"]] == [1, 2]
    assert plan["next_week"] == 3

    # Week 1 must survive untouched — it is the user's practice history now.
    original = week_db._week_one["four_week_plan"][0]
    assert plan["four_week_plan"][0] == original


def test_feedback_visibly_changes_the_generated_week(auth_client, week_db):
    plan = auth_client.post("/api/plans/yoga/next-week", json=REQUEST).json()
    week_one_minutes = plan["four_week_plan"][0]["days"][0]["session"]["total_duration_minutes"]
    week_two_minutes = plan["four_week_plan"][1]["days"][0]["session"]["total_duration_minutes"]
    assert week_two_minutes < week_one_minutes
    assert plan["progression_adjustment"]["reasons"]


def test_the_plan_is_persisted_with_its_feedback(auth_client, week_db):
    auth_client.post("/api/plans/yoga/next-week", json=REQUEST)
    week_db.plan_history.update_one.assert_awaited_once()
    update = week_db.plan_history.update_one.await_args.args[1]["$set"]
    stored = update["plan_data.yoga_plan"]
    assert stored["weeks_generated"] == [1, 2]
    assert stored["week_feedback"][0]["week"] == 1
    assert stored["week_feedback"][0]["difficulty"] == "too_hard"


def test_a_timeline_event_is_recorded(auth_client, week_db):
    auth_client.post("/api/plans/yoga/next-week", json=REQUEST)
    event = week_db.timeline.insert_one.await_args.args[0]
    assert event["event_type"] == "yoga_week_generated"
    assert event["details"]["week"] == 2


def test_the_next_week_can_be_generated_without_any_feedback(auth_client, week_db):
    """Nobody should be blocked from practising because they skipped a form."""
    resp = auth_client.post("/api/plans/yoga/next-week",
                            json={"plan_id": "yoga-plan-1"})
    assert resp.status_code == 200
    plan = resp.json()
    assert plan["weeks_generated"] == [1, 2]
    assert plan["progression_adjustment"] is None


def test_resubmitting_a_week_corrects_rather_than_compounds(auth_client, week_db):
    """Feedback is keyed by week, so answering twice must not double the effect."""
    first = auth_client.post("/api/plans/yoga/next-week", json=REQUEST).json()

    # Feed the stored plan (which already holds week 1's feedback) back in and
    # submit a *different* answer for the same week.
    week_db.plan_history.find_one = AsyncMock(return_value={
        "_id": "yoga-plan-1", "user_id": "test-uuid-1234",
        "plan_data": {"yoga_plan": {**first, "four_week_plan": first["four_week_plan"][:1],
                                    "weeks_generated": [1], "next_week": 2}},
    })
    corrected = auth_client.post("/api/plans/yoga/next-week", json={
        **REQUEST, "feedback": {"difficulty": "just_right"}}).json()

    assert len(corrected["week_feedback"]) == 1
    assert corrected["week_feedback"][0]["difficulty"] == "just_right"


def test_dropped_poses_are_excluded_from_the_generated_week(auth_client, week_db):
    week_one = week_db._week_one
    dropped = week_one["four_week_plan"][0]["days"][0]["session"]["main_sequence"][0]["pose_id"]
    plan = auth_client.post("/api/plans/yoga/next-week", json={
        **REQUEST,
        "feedback": {"difficulty": "just_right", "dropped_pose_ids": [dropped]},
    }).json()

    week_two = plan["four_week_plan"][1]
    used = {p["pose_id"] for d in week_two["days"] if d.get("session")
            for section in ("warmup", "main_sequence", "cooldown")
            for p in d["session"][section]}
    assert dropped not in used
