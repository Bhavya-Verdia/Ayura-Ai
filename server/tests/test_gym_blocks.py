"""Block over block: what a person who followed the plan for a month gets next.

Until this the block number was a label — block 2 had block 1's sets and
exercises, only the weights moved — the level never moved from what the form
said, nothing marked the end of a block, and month one fell out of the 42-day
window by month three. These hold the next block, the long history, the
level-up offer and the reminder.
"""
from datetime import datetime, timedelta, timezone
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.gym_plan_engine import generate_gym_plan
from services.workout_log import (block_history, consecutive_progressed, level_up_offer,
                                  notify_finished_blocks)

_PROFILE = {"id": "u1", "age": 30, "gender": "male", "weight_kg": 78,
            "fitness_level": "beginner", "dominant_dosha": "pitta", "bmi_category": "normal"}
_PREFS = {"gym_goal": "muscle_gain", "workout_days_per_week": 3, "workout_duration_minutes": 60,
          "available_equipment": ["full_gym"], "strength_level": "beginner"}
_DONE = {"block": 1, "progress": True, "sessions_logged": 10, "sessions_planned": 12,
         "progressed": []}


def _exercises(plan, role=None):
    return [(w["week"], d["day"], e) for w in plan["four_week_plan"] for d in w["days"]
            for e in d["main_workout"] if role is None or e["role"] == role]


# ── The next block is a next block ───────────────────────────────────────────

@pytest.fixture(scope="module")
def blocks():
    one = generate_gym_plan(dict(_PROFILE), dict(_PREFS))
    two = generate_gym_plan(dict(_PROFILE), dict(_PREFS), previous_block=_DONE)
    return one, two


def test_a_block_built_on_adds_a_main_lift_set_and_says_so(blocks):
    one, two = blocks
    assert two["user_summary"]["block"] == 2
    sets_one = {(w, d, e["exercise_id"]): e["sets"] for w, d, e in _exercises(one, "primary")}
    for w, d, e in _exercises(two, "primary"):
        assert e["sets"] == min(6, sets_one[(w, d, e["exercise_id"])] + 1)
    for w1, w2 in zip(one["four_week_plan"], two["four_week_plan"]):
        assert w2["prescription"]["sets"] == min(6, w1["prescription"]["sets"] + 1)
    assert "a set more" in two["block_notice"]


def test_the_main_lifts_stay_and_some_accessory_work_changes(blocks):
    one, two = blocks
    assert ({e["exercise_id"] for _, _, e in _exercises(one, "primary")}
            == {e["exercise_id"] for _, _, e in _exercises(two, "primary")})
    assert ({e["exercise_id"] for _, _, e in _exercises(one)}
            != {e["exercise_id"] for _, _, e in _exercises(two)})


def test_the_extra_set_still_fits_the_session(blocks):
    _, two = blocks
    for w in two["four_week_plan"]:
        for d in w["days"]:
            if d["main_workout"]:
                assert d["estimated_duration_minutes"] <= 60 + 5, (w["week"], d["day_name"])


def test_a_repeated_block_keeps_its_number_and_its_volume():
    repeat = {**_DONE, "block": 2, "progress": False}
    plan = generate_gym_plan(dict(_PROFILE), dict(_PREFS), previous_block=repeat)
    built = generate_gym_plan(dict(_PROFILE), dict(_PREFS), previous_block=_DONE)
    assert plan["user_summary"]["block"] == 2
    assert ([e["sets"] for _, _, e in _exercises(plan, "primary")]
            == [e["sets"] for _, _, e in _exercises(built, "primary")])


def test_pregnancy_is_maintained_not_progressed():
    profile = {**_PROFILE, "gender": "female", "pregnancy_or_nursing": True}
    one = generate_gym_plan(dict(profile), dict(_PREFS))
    two = generate_gym_plan(dict(profile), dict(_PREFS), previous_block=_DONE)
    assert ([w["prescription"]["sets"] for w in one["four_week_plan"]]
            == [w["prescription"]["sets"] for w in two["four_week_plan"]])
    assert "a set more" not in (two["block_notice"] or "")


def test_a_first_block_is_unchanged_by_this():
    """Block 1 keeps the selection seed it always had."""
    a = generate_gym_plan(dict(_PROFILE), dict(_PREFS))
    b = generate_gym_plan(dict(_PROFILE), dict(_PREFS), previous_block=None)
    assert ([e["exercise_id"] for _, _, e in _exercises(a)]
            == [e["exercise_id"] for _, _, e in _exercises(b)])


# ── The long history ─────────────────────────────────────────────────────────

class _Cursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def sort(self, key, direction):
        self.docs.sort(key=lambda d: d.get(key), reverse=direction < 0)
        return self

    def limit(self, n):
        self.docs = self.docs[:n]
        return self

    def __aiter__(self):
        self._it = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def _match(doc, filt):
    for k, v in filt.items():
        have = doc.get(k)
        if isinstance(v, dict):
            for op, arg in v.items():
                if op == "$in" and have not in arg:
                    return False
                if op == "$exists" and (k in doc) != arg:
                    return False
                if op == "$lte" and not (have is not None and have <= arg):
                    return False
                if op == "$gte" and not (have is not None and have >= arg):
                    return False
                if op == "$gt" and not (have is not None and have > arg):
                    return False
        elif have != v:
            return False
    return True


class _Coll:
    def __init__(self, docs=()):
        self.docs = [dict(d) for d in docs]

    def find(self, filt=None, *_):
        return _Cursor(d for d in self.docs if _match(d, filt or {}))

    async def find_one(self, filt=None, *_ , **__):
        return next((d for d in self.docs if _match(d, filt or {})), None)

    async def update_one(self, filt, update, **_):
        for d in self.docs:
            if _match(d, filt):
                d.update(update.get("$set") or {})
                return


def _plan_record(pid, days_ago, block=1, now=None):
    now = now or datetime.now(timezone.utc)
    plan = generate_gym_plan(dict(_PROFILE), dict(_PREFS))
    plan["user_summary"]["block"] = block
    return {"_id": pid, "user_id": "u1", "plan_type": "gym",
            "generated_at": now - timedelta(days=days_ago), "plan_data": {"gym_plan": plan}}


def _logs_for(record, sessions, kg):
    """`sessions` logged sessions on a plan, each with its main lift at `kg`."""
    plan = record["plan_data"]["gym_plan"]
    days = [(w["week"], d) for w in plan["four_week_plan"] for d in w["days"]
            if d["main_workout"]][:sessions]
    out = []
    for week, d in days:
        ex = next(e for e in d["main_workout"] if e["role"] == "primary")
        out.append({"user_id": "u1", "plan_id": record["_id"], "week": week, "day": d["day"],
                    "exercise_id": ex["exercise_id"], "exercise_name": ex["exercise_name"],
                    "sets": [{"kg": kg, "reps": 8}], "effort": "right",
                    "updated_at": record["generated_at"] + timedelta(days=week * 7)})
    return out


@pytest.fixture(scope="module")
def three_blocks():
    recs = [_plan_record("g1", 120), _plan_record("g_fix", 118),   # a correction, never trained
            _plan_record("g2", 90, block=2), _plan_record("g3", 60, block=3),
            _plan_record("g4", 10, block=4)]
    logs = (_logs_for(recs[0], 10, 60) + _logs_for(recs[2], 11, 65)
            + _logs_for(recs[3], 9, 70) + _logs_for(recs[4], 2, 72))
    return SimpleDB(recs, logs)


class SimpleDB:
    def __init__(self, plans, logs):
        self.plan_history = _Coll(plans)
        self.workout_logs = _Coll(logs)


@pytest.mark.asyncio
async def test_history_reaches_past_the_load_window_and_skips_corrections(three_blocks):
    rows = await block_history(three_blocks, "u1")
    assert [r["plan_id"] for r in rows] == ["g1", "g2", "g3", "g4"]
    # Month one is four months old and still counted.
    assert rows[0]["sessions_logged"] == 10 and rows[0]["finished"]
    # The current block, 10 days in with only week one logged, is not finished.
    assert not rows[-1]["finished"]
    assert consecutive_progressed(rows) == 3


@pytest.mark.asyncio
async def test_three_consistent_blocks_with_gains_offer_intermediate(three_blocks):
    rows = await block_history(three_blocks, "u1")
    offer = level_up_offer(rows, {"fitness_level": "beginner", "age": 30})
    assert offer["to"] == "intermediate" and offer["blocks"] == 3
    assert offer["gains"]


@pytest.mark.asyncio
async def test_no_offer_for_a_child_a_pregnancy_or_someone_already_there(three_blocks):
    rows = await block_history(three_blocks, "u1")
    for profile in ({"fitness_level": "beginner", "age": 16},
                    {"fitness_level": "beginner", "age": 30, "pregnancy_or_nursing": True},
                    {"fitness_level": "intermediate", "age": 30}):
        assert level_up_offer(rows, profile) is None


def test_no_offer_without_evidence_or_with_a_broken_run():
    def row(progress, kg):
        return {"finished": True, "progress": progress,
                "best_lifts": {"squat": {"name": "Squat", "one_rm": kg}}}
    flat = [row(True, 80), row(True, 80), row(True, 80)]
    assert level_up_offer(flat, {"fitness_level": "beginner", "age": 30}) is None
    broken = [row(True, 70), row(False, 75), row(True, 80), row(True, 85)]
    assert consecutive_progressed(broken) == 2
    assert level_up_offer(broken, {"fitness_level": "beginner", "age": 30}) is None


# ── The reminder ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_finished_block_is_announced_once_and_a_superseded_one_never():
    now = datetime.now(timezone.utc)
    done = _plan_record("old", 30, now=now)
    superseded = {**_plan_record("older", 31, now=now), "user_id": "u2"}
    newer = {**_plan_record("newer", 5, now=now), "user_id": "u2"}
    db = SimpleDB([done, superseded, newer], _logs_for(done, 9, 60))
    with patch("services.notification_service.create_and_deliver_notification",
               new=AsyncMock()) as send:
        assert await notify_finished_blocks(db, now) == 1
        kwargs = send.await_args.kwargs
        assert kwargs["user_id"] == "u1" and "Block 2 is ready" in kwargs["body"]
        assert await notify_finished_blocks(db, now) == 0
    assert all("block_end_notified" in d for d in db.plan_history.docs if d["_id"] != "newer")


@pytest.mark.asyncio
async def test_an_abandoned_plan_is_not_announced_a_year_later():
    now = datetime.now(timezone.utc)
    db = SimpleDB([_plan_record("ancient", 300, now=now)], [])
    with patch("services.notification_service.create_and_deliver_notification",
               new=AsyncMock()) as send:
        assert await notify_finished_blocks(db, now) == 0
        send.assert_not_awaited()


# ── The API ──────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True, "fitness_level": "beginner",
        "age": 30, "created_at": datetime.now(timezone.utc),
        "updated_at": datetime.now(timezone.utc),
    })
    mock_db.users.update_one = AsyncMock()
    mock_db.user_preferences = MagicMock()
    mock_db.user_preferences.update_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


def test_level_up_is_refused_without_the_evidence(auth_client, mock_db):
    with patch("routes.workouts.block_history", new=AsyncMock(return_value=[])):
        assert auth_client.post("/api/workouts/level-up").status_code == 409
    mock_db.users.update_one.assert_not_awaited()


def test_level_up_moves_the_profile_and_the_gym_form_together(auth_client, mock_db):
    offer = {"to": "intermediate", "blocks": 3, "gains": [], "reason": ""}
    with patch("routes.workouts.block_history", new=AsyncMock(return_value=[])), \
            patch("routes.workouts.level_up_offer", return_value=offer):
        resp = auth_client.post("/api/workouts/level-up")
    assert resp.json() == {"fitness_level": "intermediate"}
    assert mock_db.users.update_one.await_args.args[1]["$set"]["fitness_level"] == "intermediate"
    filt, update = mock_db.user_preferences.update_one.await_args.args[:2]
    assert filt["gym"] == {"$exists": True}
    assert update["$set"]["gym.strength_level"] == "intermediate"


def test_blocks_endpoint_returns_history_and_offer(auth_client):
    rows = [{"plan_id": "g1", "finished": True, "progress": True, "best_lifts": {}}]
    with patch("routes.workouts.block_history", new=AsyncMock(return_value=rows)):
        body = auth_client.get("/api/workouts/blocks").json()
    assert body["blocks"] == rows and body["consecutive"] == 1 and body["level_up"] is None
