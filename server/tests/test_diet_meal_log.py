"""The meal log and what it changes in the next diet plan."""
from datetime import datetime, timedelta, timezone

import pytest

from services import diet_log as dl
from services.diet_energy import energy_target

T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _logs(n, status="eaten", slot="lunch", foods=("moong_dal_yellow",)):
    return [{"slot": slot, "status": status, "foods": list(foods)} for _ in range(n)]


def _weights(start, per_week, weeks=4):
    return [(T0 + timedelta(days=7 * i), start + per_week * i) for i in range(weeks + 1)]


def test_thin_evidence_changes_nothing():
    assert dl.adaptation(_logs(10), _weights(80, 0), goal="weight_loss", bmi_category="obese") == {}


def test_a_slot_skipped_on_most_days_is_kept_light_not_dropped():
    logs = _logs(10) + _logs(6, "skipped", "breakfast") + _logs(2, "eaten", "breakfast")
    a = dl.adaptation(logs, [], goal=None, bmi_category=None)
    assert a["skipped_slots"] == ["breakfast"]
    assert "do not drop it" in dl.brief_block(a)


def test_a_food_left_uneaten_again_and_again_is_used_rarely():
    logs = _logs(12) + _logs(4, "skipped", "dinner", ("bitter_gourd_karela", "roti_whole_wheat")) \
        + _logs(1, "eaten", "dinner", ("bitter_gourd_karela",))
    a = dl.adaptation(logs, [], goal=None, bmi_category=None)
    assert a["avoided_foods"][0] == "bitter_gourd_karela"
    # Roti was served only in the skipped dinners, so it is caught too; moong, eaten
    # in all twelve lunches, is not.
    assert "roti_whole_wheat" in a["avoided_foods"]
    assert "moong_dal_yellow" not in a["avoided_foods"]


def test_a_weight_loss_plan_that_does_not_move_weight_comes_down_150():
    a = dl.adaptation(_logs(20), _weights(90, -0.05), goal="weight_loss", bmi_category="obese")
    assert a["energy_adjust_kcal"] == -150 and "0.25-1 kg" in a["energy_reason"]


def test_weight_falling_faster_than_one_percent_a_week_goes_back_up():
    a = dl.adaptation(_logs(20), _weights(60, -1.0), goal="weight_loss", bmi_category="normal")
    assert a["energy_adjust_kcal"] == 150


def test_an_underweight_patient_not_gaining_gets_more():
    a = dl.adaptation(_logs(20), _weights(45, 0.0), goal="general_wellness",
                      bmi_category="underweight")
    assert a["energy_adjust_kcal"] == 150


def test_low_adherence_changes_no_energy_figure():
    """The plan was not tested, so it is not wrong."""
    logs = _logs(8) + _logs(12, "skipped")
    a = dl.adaptation(logs, _weights(90, 0.0), goal="weight_loss", bmi_category="obese")
    assert "energy_adjust_kcal" not in a


def test_weigh_ins_under_two_weeks_apart_are_not_a_trend():
    w = [(T0, 90.0), (T0 + timedelta(days=10), 90.0)]
    a = dl.adaptation(_logs(20), w, goal="weight_loss", bmi_category="obese")
    assert "energy_adjust_kcal" not in a


def test_the_fingerprint_ignores_one_more_logged_meal():
    a = dl.adaptation(_logs(20), _weights(90, 0), goal="weight_loss", bmi_category="obese")
    b = dl.adaptation(_logs(21), _weights(90, 0), goal="weight_loss", bmi_category="obese")
    assert dl.fingerprint(a) == dl.fingerprint(b)


def _profile(**k):
    return {"age": 40, "gender": "female", "weight_kg": 80, "height_cm": 160,
            "activity_level": "light", "bmi_category": "obese", **k}


def test_the_energy_target_applies_the_log_and_says_why():
    base = energy_target(_profile(), {"diet_goal": "weight_loss"})
    adj = energy_target(_profile(diet_log={"energy_adjust_kcal": -150, "energy_reason": "x"}),
                        {"diet_goal": "weight_loss"})
    assert adj["target_calories"] in (base["target_calories"] - 150, adj["floor_calories"])
    assert any("meal log" in n for n in adj["notes"])


@pytest.mark.parametrize("extra", [{"age": 15}, {"pregnancy_or_nursing": True}])
def test_no_log_driven_deficit_for_a_child_or_in_pregnancy(extra):
    base = energy_target(_profile(**extra), {"diet_goal": "general_wellness"})
    adj = energy_target(_profile(**extra, diet_log={"energy_adjust_kcal": -150}),
                        {"diet_goal": "general_wellness"})
    assert adj["target_calories"] == base["target_calories"]


def test_the_cache_key_changes_when_the_adaptation_does():
    import asyncio

    from routes.plan_runner import _check_plan_cache

    class _Coll:
        async def find_one(self, *a, **k):
            return None

    class _DB:
        plan_history = _Coll()

    def key(log):
        return asyncio.run(_check_plan_cache(_DB(), "u", "diet", _profile(diet_log=log), {}, False))[1]
    assert key({}) == key(None)
    assert key({"energy_adjust_kcal": -150}) != key({})


# ── The API ──────────────────────────────────────────────────────────────────

from unittest.mock import AsyncMock, MagicMock  # noqa: E402

from fastapi.testclient import TestClient  # noqa: E402

from main import app  # noqa: E402
from services.auth_service import create_access_token  # noqa: E402

_DIET_DOC = {"_id": "diet_p1", "plan_data": {"diet_plan": {"diet_weeks": [{
    "week_number": 1, "daily_plan": {"Monday": {"lunch": {
        "meal_name": "Karela Sabzi with Roti",
        "components": [{"food": "bitter_gourd_karela", "grams": 150},
                       {"food": "roti_whole_wheat", "grams": 80}]}}}}]}}}


@pytest.fixture
def auth_client(mock_db):
    mock_db.users.find_one = AsyncMock(return_value={
        "_id": "test-uuid-1234", "name": "Test User", "email": "test@ayura.com",
        "auth_provider": "local", "is_active": True, "is_admin": False,
        "is_verified": True, "onboarding_complete": True,
        "created_at": datetime.now(timezone.utc), "updated_at": datetime.now(timezone.utc),
    })
    mock_db.plan_history.find_one = AsyncMock(return_value=_DIET_DOC)
    mock_db.meal_logs = MagicMock()
    mock_db.meal_logs.replace_one = AsyncMock()
    mock_db.meal_logs.delete_one = AsyncMock()
    client = TestClient(app)
    client.cookies.set("ayura_access", create_access_token("test-uuid-1234", "test@ayura.com"))
    return client


_LOG = {"plan_id": "diet_p1", "week": 1, "day": "Monday", "slot": "lunch", "status": "skipped"}


def test_meal_logging_requires_auth():
    assert TestClient(app).post("/api/meals/logs", json=_LOG).status_code == 401


def test_a_logged_meal_carries_its_foods(auth_client, mock_db):
    resp = auth_client.post("/api/meals/logs", json=_LOG)
    assert resp.status_code == 200, resp.text
    filt, doc = mock_db.meal_logs.replace_one.await_args.args[:2]
    assert filt["_id"] == "test-uuid-1234:diet_p1:1:Monday:lunch"
    assert doc["foods"] == ["bitter_gourd_karela", "roti_whole_wheat"]
    assert doc["status"] == "skipped"


def test_a_meal_the_plan_does_not_have_is_refused(auth_client):
    resp = auth_client.post("/api/meals/logs", json={**_LOG, "day": "Tuesday"})
    assert resp.status_code == 422


def test_a_null_status_removes_the_log(auth_client, mock_db):
    resp = auth_client.post("/api/meals/logs", json={**_LOG, "status": None})
    assert resp.json()["deleted"] is True
    mock_db.meal_logs.delete_one.assert_awaited_once()
