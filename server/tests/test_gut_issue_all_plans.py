"""The diet form's gut question reaches every plan, not only diet.

`gut_health_issue` is a disease (acidity, constipation, bloating, IBS). The diet path
read it through `diet_conditions`, but gym, routine, Panchakarma, remedies, medicines
and the seasonal card built their condition lists from `medical_history` alone. A
live audit found the routine's snack and the gym's nutrition tip still suggesting
curd to a patient who had told the diet form they have acidity.
"""

import re
from pathlib import Path

import pytest

from engine.dosha_analyzer import disease_signal
from services.diet_brief_builder import _GUT_ISSUE_CONDITIONS, with_gut_condition

_ROOT = Path(__file__).resolve().parent.parent


def _prefs(gut):
    return {"diet": {"gut_health_issue": gut}}


@pytest.mark.parametrize("gut", sorted(_GUT_ISSUE_CONDITIONS))
def test_the_gut_issue_joins_medical_history(gut):
    out = with_gut_condition({"medical_history": ["diabetes_type2"]}, _prefs(gut))
    assert out["medical_history"][0] == "diabetes_type2"
    assert len(out["medical_history"]) == 2


@pytest.mark.parametrize("gut", sorted(_GUT_ISSUE_CONDITIONS))
def test_every_injected_condition_is_recognised(gut):
    # An unrecognised diagnosis sends Panchakarma to LLM triage and withholds
    # Shodhana; a diet-form answer must never do that.
    [key] = with_gut_condition({"medical_history": []}, _prefs(gut))["medical_history"]
    assert disease_signal(key) is not None, key


def test_nothing_is_added_twice_or_for_healthy():
    profile = {"medical_history": ["acid_reflux"]}
    assert with_gut_condition(profile, _prefs("acidity")) is profile
    assert with_gut_condition(profile, _prefs("healthy")) is profile
    assert with_gut_condition(profile, {}) is profile
    assert with_gut_condition(profile, None) is profile


def test_the_routine_snack_screen_now_sees_it():
    from services.routine_engine import _screen_food_list
    conds = with_gut_condition({"medical_history": []}, _prefs("acidity"))["medical_history"]
    kept, withheld = _screen_food_list(["curd", "soaked raisins"], conds, [], False)
    assert "curd" not in kept
    assert [w["item"] for w in withheld] == ["curd"]


def test_every_plan_route_builds_its_profile_through_declared_profile():
    src = (_ROOT / "routes" / "plans.py").read_text()
    assert not re.search(r"user_profile\s*=\s*user\.model_dump\(\)", src)
    assert "build_seasonal_guidance(dosha, user.model_dump())" not in src
    runner = (_ROOT / "routes" / "plan_runner.py").read_text()
    assert "user.medical_history" not in runner
