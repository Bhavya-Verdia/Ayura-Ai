"""Workout logging, and the next block learning from it.

A gym plan used to be a document: four weeks of estimates with no record of
what was lifted, and regenerating after week four began again from the same
estimates. These cover the log, what it measures, and the block built on it.
"""
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.gym_plan_engine import generate_gym_plan
from services.workout_log import (block_summary, fingerprint, gym_history,
                                  logged_lifts, planned_sessions)

_PROFILE = {"id": "u1", "age": 30, "gender": "male", "weight_kg": 78,
            "fitness_level": "intermediate", "dominant_dosha": "pitta", "bmi_category": "normal"}
_PREFS = {"gym_goal": "muscle_gain", "workout_days_per_week": 4, "workout_duration_minutes": 60,
          "available_equipment": ["full_gym"], "strength_level": "intermediate"}


def _entry(ex, sets, week=1, day=1, effort=None, plan_id="p1"):
    return {"plan_id": plan_id, "week": week, "day": day, "exercise_id": ex,
            "exercise_name": ex.replace("_", " ").title(), "sets": sets, "effort": effort,
            "updated_at": datetime.now(timezone.utc)}


# ── What a log measures ──────────────────────────────────────────────────────

def test_the_strongest_set_is_the_measurement():
    """A deload week's lighter sets are logged too, and they are not a
    measurement of what the practitioner can do."""
    lifts = logged_lifts([
        _entry("barbell_bench_press", [{"kg": 80, "reps": 8}, {"kg": 80, "reps": 7}]),
        _entry("barbell_bench_press", [{"kg": 60, "reps": 8}], week=4),
    ])
    # 80 x 8, two short of failure -> 80 * (1 + 10/30)
    assert lifts["barbell_bench_press"]["one_rm"] == pytest.approx(106.67, abs=0.01)
    assert lifts["barbell_bench_press"]["source"] == "80 kg × 8"


def test_effort_changes_the_estimate():
    easy = logged_lifts([_entry("x", [{"kg": 50, "reps": 10}], effort="easy")])["x"]["one_rm"]
    hard = logged_lifts([_entry("x", [{"kg": 50, "reps": 10}], effort="hard")])["x"]["one_rm"]
    assert easy > hard


def test_high_rep_and_bodyweight_sets_measure_nothing():
    assert logged_lifts([_entry("push_up", [{"kg": 0, "reps": 20}]),
                         _entry("x", [{"kg": 20, "reps": 25}])]) == {}


def test_a_logged_load_replaces_the_estimate():
    base = generate_gym_plan(_PROFILE, _PREFS)
    bench = next(e for d in base["weekly_schedule"] for e in d["main_workout"]
                 if e["exercise_name"] == "Barbell Bench Press")
    logged = logged_lifts([_entry("barbell_bench_press", [{"kg": 100, "reps": 8}])])
    plan = generate_gym_plan(_PROFILE, _PREFS, logged_lifts=logged)
    after = next(e for d in plan["weekly_schedule"] for e in d["main_workout"]
                 if e["exercise_name"] == "Barbell Bench Press")
    assert "from your logged 100 kg × 8" in after["weight_range"]
    top = float(re.match(r"[\d.]+–([\d.]+)", after["weight_range"]).group(1))
    assert top > float(re.match(r"[\d.]+–([\d.]+)", bench["weight_range"]).group(1))


def test_a_logged_lift_comes_back_in_the_next_block():
    """Progressive overload needs the same movement."""
    logged = logged_lifts([_entry("t_bar_row", [{"kg": 60, "reps": 10}])])
    plan = generate_gym_plan(_PROFILE, _PREFS, logged_lifts=logged)
    names = {e["exercise_name"] for d in plan["weekly_schedule"] for e in d["main_workout"]}
    assert "T-Bar Row" in names


# ── The block ────────────────────────────────────────────────────────────────

def _block_plan():
    return generate_gym_plan(_PROFILE, _PREFS)


def test_a_block_mostly_done_is_built_on():
    plan = _block_plan()
    pid = plan["plan_id"]
    days = [(w["week"], d["day"]) for w in plan["four_week_plan"] for d in w["days"]
            if d["main_workout"]]
    entries = [_entry("barbell_squat", [{"kg": 80 + i, "reps": 8}], week=w, day=d, plan_id=pid)
               for i, (w, d) in enumerate(days[:12])]
    summary = block_summary(plan, entries)
    assert summary["sessions_planned"] == planned_sessions(plan) == 16
    assert summary["sessions_logged"] == 12 and summary["progress"] is True
    assert summary["progressed"][0]["exercise"] == "Barbell Squat"

    nxt = generate_gym_plan(_PROFILE, _PREFS, logged_lifts=logged_lifts(entries),
                            previous_block=summary)
    assert nxt["user_summary"]["block"] == 2
    assert "builds on it" in nxt["block_notice"] and "Barbell Squat +" in nxt["block_notice"]


def test_a_block_mostly_skipped_is_repeated_not_built_on():
    plan = _block_plan()
    entries = [_entry("barbell_squat", [{"kg": 80, "reps": 8}], plan_id=plan["plan_id"])]
    summary = block_summary(plan, entries)
    assert summary["progress"] is False
    nxt = generate_gym_plan(_PROFILE, _PREFS, previous_block=summary)
    assert nxt["user_summary"]["block"] == 1
    assert "repeats its structure" in nxt["block_notice"]


def test_a_first_plan_says_nothing_about_blocks():
    plan = _block_plan()
    assert plan["block_notice"] is None and plan["user_summary"]["block"] == 1


def test_the_fingerprint_moves_when_a_set_is_logged():
    """It joins the plan cache key; a plan priced from the log is stale the
    moment the log changes."""
    a = [_entry("x", [{"kg": 50, "reps": 10}])]
    b = a + [_entry("y", [{"kg": 20, "reps": 10}])]
    assert fingerprint(a) != fingerprint(b)


def _cursor(items):
    cursor = MagicMock()

    async def _aiter():
        for item in items:
            yield item
    cursor.__aiter__ = lambda _self: _aiter()
    return cursor


@pytest.mark.asyncio
async def test_a_correction_in_the_first_fortnight_is_not_a_finished_block():
    """Regenerating in week one (new equipment, changed goal) is not a block of
    which the practitioner "logged 1 of 16 sessions"."""
    plan = _block_plan()
    db = MagicMock()
    db.workout_logs.find = MagicMock(return_value=_cursor(
        [_entry("barbell_squat", [{"kg": 80, "reps": 8}], plan_id=plan["plan_id"])]))
    db.plan_history.find_one = AsyncMock(return_value={
        "plan_data": {"gym_plan": plan},
        "generated_at": datetime.now(timezone.utc) - timedelta(days=4)})
    history = await gym_history(db, "u1")
    assert history["previous_block"] is None
    assert "barbell_squat" in history["logged_lifts"]


@pytest.mark.asyncio
async def test_a_log_outage_still_builds_a_plan():
    db = MagicMock()
    db.workout_logs.find = MagicMock(side_effect=RuntimeError("mongo down"))
    history = await gym_history(db, "u1")
    assert history == {"logged_lifts": {}, "previous_block": None, "fingerprint": "unavailable"}


# ── The API ──────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.plan_history.find_one = AsyncMock(return_value={"_id": "gym_p1"})
    mock_db.workout_logs = MagicMock()
    mock_db.workout_logs.replace_one = AsyncMock()
    mock_db.workout_logs.delete_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


_LOG = {"plan_id": "gym_p1", "week": 1, "day": 1, "exercise_id": "barbell_bench_press",
        "sets": [{"kg": 60, "reps": 10}, {"kg": 60, "reps": 9}], "effort": "right"}


def test_logging_requires_auth():
    assert TestClient(app).post("/api/workouts/logs", json=_LOG).status_code == 401


def test_a_logged_exercise_is_stored_under_one_key(auth_client, mock_db):
    resp = auth_client.post("/api/workouts/logs", json=_LOG)
    assert resp.status_code == 200, resp.text
    filt, doc = mock_db.workout_logs.replace_one.await_args.args[:2]
    assert filt["_id"] == "test-uuid-1234:gym_p1:1:1:barbell_bench_press"
    assert doc["exercise_name"] == "Barbell Bench Press" and len(doc["sets"]) == 2


def test_logging_no_sets_removes_the_entry(auth_client, mock_db):
    resp = auth_client.post("/api/workouts/logs", json={**_LOG, "sets": []})
    assert resp.json()["deleted"] is True
    mock_db.workout_logs.delete_one.assert_awaited_once()


def test_an_unknown_exercise_or_someone_elses_plan_is_refused(auth_client, mock_db):
    assert auth_client.post("/api/workouts/logs",
                            json={**_LOG, "exercise_id": "made_up"}).status_code == 422
    mock_db.plan_history.find_one = AsyncMock(return_value=None)
    assert auth_client.post("/api/workouts/logs", json=_LOG).status_code == 404


def test_an_impossible_set_is_refused(auth_client):
    bad = {**_LOG, "sets": [{"kg": 900, "reps": 10}]}
    assert auth_client.post("/api/workouts/logs", json=bad).status_code == 422


# ── Erasure ──────────────────────────────────────────────────────────────────

def test_account_deletion_reaches_every_collection_written_per_user():
    """Practice history, reported adverse reactions, push endpoints and feedback
    all outlived a deleted account. Any collection the app writes with a user_id
    must be named in `delete_account`, or deliberately exempted here."""
    root = Path(__file__).resolve().parents[1]
    written = set()
    for path in list((root / "routes").glob("*.py")) + list((root / "services").glob("*.py")):
        written |= set(re.findall(
            r"db\.([a-z_]+)\.(?:insert_one|insert_many|replace_one|update_one)", path.read_text()))
    privacy = (root / "routes" / "privacy.py").read_text()
    deleted = set(re.findall(r"db\.([a-z_]+)\.delete_(?:one|many)", privacy))
    exempt = {
        "audit_log",     # pseudonymous compliance record, retained by design
        "usage_quota",   # TTL-reaped within a day
        "otps",          # keyed by phone number, deleted separately
        "users",         # deleted by _id
    }
    missing = written - deleted - exempt
    assert not missing, f"never deleted with the account: {sorted(missing)}"
