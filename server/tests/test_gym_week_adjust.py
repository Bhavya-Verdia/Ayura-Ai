"""Next week's weights from last week's sets and check-in.

The log used to reach only the next four-week block, so a dumbbell press logged
"easy" at the top of the range in week one was shown the same weight for weeks
two and three. These hold the coach's rule — up a step, hold, or down — and the
limits on it: a deload stays a deload, a check-in can only hold or lower, and a
red flag ends the question of load.
"""
from datetime import datetime, timezone
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi.testclient import TestClient

from main import app
from services.auth_service import create_access_token
from services.gym_plan_engine import _parse_reps, generate_gym_plan
from services.gym_week_adjust import _quoted_kg, week_adjustments

_PROFILE = {"id": "u1", "age": 30, "gender": "male", "weight_kg": 78,
            "fitness_level": "intermediate", "dominant_dosha": "pitta", "bmi_category": "normal"}
_PREFS = {"gym_goal": "muscle_gain", "workout_days_per_week": 4, "workout_duration_minutes": 60,
          "available_equipment": ["full_gym"], "strength_level": "intermediate"}


@pytest.fixture(scope="module")
def plan():
    p = generate_gym_plan(_PROFILE, _PREFS)
    p["plan_id"] = "p1"
    return p


def _loaded(plan, week, *, kettlebell=False):
    """(day, exercise) in `week` with a quoted kg range that also appears in the
    week after, so there is a next week to adjust."""
    nxt = {e["exercise_id"] for d in plan["four_week_plan"][week]["days"]
           for e in d["main_workout"]}
    for d in plan["four_week_plan"][week - 1]["days"]:
        for e in d["main_workout"]:
            if (e["exercise_id"] in nxt and _parse_reps(e["reps"]) and
                    _quoted_kg(e["weight_range"]) and
                    ("kettlebell" in e["equipment"]) == kettlebell):
                return d["day"], e
    raise AssertionError("no loaded exercise carried into the next week")


def _entry(day, ex, reps, kg=40.0, effort="right", week=1):
    return {"plan_id": "p1", "week": week, "day": day, "exercise_id": ex["exercise_id"],
            "sets": [{"kg": kg, "reps": r} for r in reps], "effort": effort}


def test_week_one_has_nothing_to_adjust_from(plan):
    assert week_adjustments(plan, [], None, 1)["exercises"] == {}


def test_every_set_at_the_top_of_the_range_goes_up_one_step(plan):
    day, ex = _loaded(plan, 1)
    lo, hi = _parse_reps(ex["reps"])
    adj = week_adjustments(plan, [_entry(day, ex, [hi] * 3, kg=40)], None, 2)
    got = adj["exercises"][ex["exercise_id"]]
    assert got["direction"] == "up"
    assert got["load_kg"] == pytest.approx(42.5)
    assert "40×" in got["reason"]


def test_easy_with_reps_to_spare_goes_up_and_light_weights_move_by_a_kilo(plan):
    day, ex = _loaded(plan, 1)
    lo, hi = _parse_reps(ex["reps"])
    adj = week_adjustments(plan, [_entry(day, ex, [lo] * 3, kg=12, effort="easy")], None, 2)
    assert adj["exercises"][ex["exercise_id"]]["load_kg"] == pytest.approx(13)


def test_inside_the_range_and_about_right_holds_the_weight(plan):
    day, ex = _loaded(plan, 1)
    lo, hi = _parse_reps(ex["reps"])
    got = week_adjustments(plan, [_entry(day, ex, [lo, lo, lo])], None, 2)["exercises"][
        ex["exercise_id"]]
    assert got["direction"] == "hold" and got["load_kg"] == pytest.approx(40)
    assert "one more rep" in got["reason"]


def test_falling_short_and_very_hard_comes_down_about_ten_percent(plan):
    day, ex = _loaded(plan, 1)
    lo, _ = _parse_reps(ex["reps"])
    got = week_adjustments(plan, [_entry(day, ex, [lo - 3] * 3, kg=50, effort="hard")],
                           None, 2)["exercises"][ex["exercise_id"]]
    assert got["direction"] == "down" and got["load_kg"] == pytest.approx(45)


def test_falling_short_without_it_feeling_hard_holds(plan):
    day, ex = _loaded(plan, 1)
    lo, _ = _parse_reps(ex["reps"])
    got = week_adjustments(plan, [_entry(day, ex, [lo - 2] * 3, kg=50)], None, 2)[
        "exercises"][ex["exercise_id"]]
    assert got["direction"] == "hold" and got["load_kg"] == pytest.approx(50)


def test_a_deload_week_is_still_lighter_than_the_week_before(plan):
    """The plan's own ratio between weeks three and four is kept: an adjustment
    that erased the deload would be the plan contradicting its own week note."""
    day, ex = _loaded(plan, 3)
    lo, _ = _parse_reps(ex["reps"])
    got = week_adjustments(plan, [_entry(day, ex, [lo] * 3, kg=60, week=3)], None, 4)[
        "exercises"][ex["exercise_id"]]
    assert got["direction"] == "deload" and got["load_kg"] < 60
    assert "deload week" in got["reason"]


def test_a_deload_week_never_adds_weight(plan):
    """At 4-5 kg the plan's deload rounds to the same quote in both weeks, so
    the ratio alone let a top-of-range set go up in the deload week."""
    day, ex = _loaded(plan, 3)
    _, hi = _parse_reps(ex["reps"])
    got = week_adjustments(plan, [_entry(day, ex, [hi] * 3, kg=5, effort="easy", week=3)],
                           None, 4)["exercises"][ex["exercise_id"]]
    assert got["direction"] == "deload" and got["load_kg"] <= 5


def test_a_check_in_can_hold_a_rise_but_never_cause_one(plan):
    day, ex = _loaded(plan, 1)
    _, hi = _parse_reps(ex["reps"])
    entries = [_entry(day, ex, [hi] * 3, kg=40)]
    for checkin in ({"feeling": "too_hard"}, {"unwell": True}):
        adj = week_adjustments(plan, entries, checkin, 2)
        assert adj["exercises"][ex["exercise_id"]]["load_kg"] == pytest.approx(40)
        assert adj["notices"]
    # "Too easy" with nothing logged raises nothing, and says why.
    adj = week_adjustments(plan, [], {"feeling": "too_easy"}, 2)
    assert adj["exercises"] == {} and "log your sets" in adj["notices"][0]


def test_a_red_flag_stops_the_conversation_about_load(plan):
    day, ex = _loaded(plan, 1)
    _, hi = _parse_reps(ex["reps"])
    adj = week_adjustments(plan, [_entry(day, ex, [hi] * 3)], {"red_flags": ["chest_pain"]}, 2)
    assert adj["exercises"] == {}
    assert "chest pain" in adj["stop"] and "doctor" in adj["stop"]


def test_very_hard_under_an_intensity_ceiling_is_named(plan):
    day, ex = _loaded(plan, 1)
    lo, _ = _parse_reps(ex["reps"])
    capped = {**plan, "intensity_notice": "Sets are kept to 8-12 for your heart."}
    got = week_adjustments(capped, [_entry(day, ex, [lo] * 3, effort="hard")], None, 2)[
        "exercises"][ex["exercise_id"]]
    assert "short of failure" in got["reason"]


def test_bodyweight_moves_to_the_harder_variant_the_library_names():
    profile = {**_PROFILE, "fitness_level": "beginner"}
    prefs = {**_PREFS, "available_equipment": ["bodyweight"], "strength_level": "beginner"}
    p = {**generate_gym_plan(profile, prefs), "plan_id": "p1"}
    nxt = {e["exercise_id"] for d in p["four_week_plan"][1]["days"] for e in d["main_workout"]}
    day, ex = next((d["day"], e) for d in p["four_week_plan"][0]["days"]
                   for e in d["main_workout"]
                   if e["exercise_id"] in nxt and "Too easy?" in (e.get("notes") or "")
                   and _parse_reps(e["reps"]))
    _, hi = _parse_reps(ex["reps"])
    got = week_adjustments(p, [_entry(day, ex, [hi] * 3, kg=0)], None, 2)["exercises"][
        ex["exercise_id"]]
    assert got["direction"] == "up" and got["text"].startswith("Move to ")


def test_another_plans_logs_change_nothing(plan):
    day, ex = _loaded(plan, 1)
    _, hi = _parse_reps(ex["reps"])
    other = {**_entry(day, ex, [hi] * 3), "plan_id": "someone_else"}
    assert week_adjustments(plan, [other], None, 2)["exercises"] == {}


# ── The API ──────────────────────────────────────────────────────────────────

@pytest.fixture
def auth_client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.plan_history.find_one = AsyncMock(return_value={"_id": "gym_p1", "plan_data": {}})
    mock_db.gym_checkins = MagicMock()
    mock_db.gym_checkins.replace_one = AsyncMock()
    mock_db.user_preferences = MagicMock()
    mock_db.user_preferences.update_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


_CHECKIN = {"plan_id": "gym_p1", "week": 1, "feeling": "right", "pain_areas": ["knee"]}


def test_a_check_in_is_stored_once_per_plan_week(auth_client, mock_db):
    mock_db.user_preferences.find_one = AsyncMock(return_value={})
    resp = auth_client.post("/api/workouts/checkins", json=_CHECKIN)
    assert resp.status_code == 200, resp.text
    filt, doc = mock_db.gym_checkins.replace_one.await_args.args[:2]
    assert filt["_id"] == "test-uuid-1234:gym_p1:1" and doc["pain_areas"] == ["knee"]
    # Pain reported once is not made a standing restriction unless asked.
    assert resp.json()["injuries_added"] == []
    mock_db.user_preferences.update_one.assert_not_awaited()


def test_pain_added_to_injuries_reaches_both_saved_forms_and_asks_for_a_rebuild(
        auth_client, mock_db):
    mock_db.user_preferences.find_one = AsyncMock(return_value={
        "gym": {"injuries": ["wrist"]}, "yoga": {"injuries": []}})
    resp = auth_client.post("/api/workouts/checkins",
                            json={**_CHECKIN, "pain_areas": ["knee", "wrist"],
                                  "add_to_injuries": True})
    body = resp.json()
    assert body["injuries_added"] == ["knee"] and body["rebuild_recommended"] is True
    update = mock_db.user_preferences.update_one.await_args.args[1]
    assert update["$addToSet"] == {"gym.injuries": {"$each": ["knee"]},
                                   "yoga.injuries": {"$each": ["knee"]}}


def test_injuries_are_not_written_into_a_form_never_saved(auth_client, mock_db):
    mock_db.user_preferences.find_one = AsyncMock(return_value={"gym": {"injuries": []}})
    auth_client.post("/api/workouts/checkins", json={**_CHECKIN, "add_to_injuries": True})
    update = mock_db.user_preferences.update_one.await_args.args[1]
    assert list(update["$addToSet"]) == ["gym.injuries"]


def test_an_unknown_area_or_symptom_is_refused(auth_client):
    assert auth_client.post("/api/workouts/checkins",
                            json={**_CHECKIN, "pain_areas": ["soul"]}).status_code == 422
    assert auth_client.post("/api/workouts/checkins",
                            json={**_CHECKIN, "red_flags": ["sad"]}).status_code == 422


def test_the_check_in_offers_only_what_the_server_accepts():
    """The chips and the validators live on opposite sides of the boundary; a
    chip the server does not know is a check-in that 422s on save."""
    import re
    from pathlib import Path

    from schemas.preferences_schema import GYM_INJURY_OPTIONS
    from services.gym_week_adjust import RED_FLAGS

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "components" /
           "planViews" / "GymWeekCheckin.jsx").read_text()

    def values(name):
        block = jsx[jsx.index(f"const {name}"):jsx.index("]", jsx.index(f"const {name}"))]
        return set(re.findall(r"value: '([a-z_]+)'", block))

    assert values("PAIN_AREAS") and values("PAIN_AREAS") <= GYM_INJURY_OPTIONS
    assert values("RED_FLAGS") == set(RED_FLAGS)
    assert values("FEELINGS") == {"too_easy", "right", "too_hard"}


class _Cursor:
    def __init__(self, docs):
        self._docs = list(docs)

    def __aiter__(self):
        return self

    async def __anext__(self):
        if not self._docs:
            raise StopAsyncIteration
        return self._docs.pop(0)


def test_the_endpoint_reads_last_weeks_logs_and_check_in(auth_client, mock_db, plan):
    day, ex = _loaded(plan, 1)
    _, hi = _parse_reps(ex["reps"])
    mock_db.plan_history.find_one = AsyncMock(return_value={"plan_data": {"gym_plan": plan}})
    mock_db.workout_logs = MagicMock()
    mock_db.workout_logs.find = MagicMock(
        return_value=_Cursor([_entry(day, ex, [hi] * 3, kg=40)]))
    mock_db.gym_checkins.find_one = AsyncMock(return_value={"feeling": "too_hard"})

    resp = auth_client.get("/api/workouts/adjustments", params={"plan_id": "p1", "week": 2})
    assert resp.status_code == 200, resp.text
    got = resp.json()
    # Last week only, and this user's check-in for it.
    assert mock_db.workout_logs.find.call_args.args[0] == {
        "user_id": "test-uuid-1234", "plan_id": "p1", "week": 1}
    assert mock_db.gym_checkins.find_one.await_args.args[0]["_id"] == "test-uuid-1234:p1:1"
    assert got["exercises"][ex["exercise_id"]]["load_kg"] == 40   # held by "too hard"
