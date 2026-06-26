"""
Regression tests for gym & yoga plan-quality and safety invariants.

These lock in the demo-hardening fixes:
  - beginners get full (non-empty) workout days even with a full gym
  - genuinely-advanced movements never reach beginner/intermediate plans
  - injury contraindications actually filter exercises
  - pregnancy-unsafe poses never reach a pregnant user
  - cooling/forceful pranayama is gated for the relevant medical conditions
"""
import pytest

from services.gym_plan_engine import (
    filter_exercises,
    generate_gym_plan,
    gym_exercises,
)
from services.yoga_plan_engine import (
    generate_yoga_plan,
    pranayama_list,
    _pranayama_hard_blocked,
)

FULL_GYM = ["barbell", "dumbbell", "machine", "cable", "bodyweight"]


def _workout_days(plan):
    return [
        d for d in plan["four_week_plan"][0]["days"]
        if d.get("type") != "rest" and "rest" not in str(d.get("focus", "")).lower()
    ]


@pytest.mark.parametrize("goal", ["muscle_gain", "strength", "fat_loss"])
def test_beginner_full_gym_has_no_empty_workout_days(goal):
    """A beginner with a full gym must never get a blank workout day. Regression
    against the level-skew bug where ~95% of exercises were tagged 'intermediate',
    starving beginner push/pull days of chest/back/shoulder work."""
    prof = {"fitness_level": "beginner", "dominant_dosha": "kapha"}
    prefs = {"gym_goal": goal, "available_equipment": FULL_GYM, "workout_days": 4}
    plan = generate_gym_plan(prof, prefs, None)
    for d in _workout_days(plan):
        assert d.get("main_workout"), f"empty workout day: {d.get('focus')}"


def test_advanced_movements_never_reach_beginners():
    """Olympic lifts / plyometrics / elite gymnastics are tagged 'advanced' and
    must be excluded from beginner plans."""
    prof = {"fitness_level": "beginner", "dominant_dosha": "vata"}
    prefs = {"gym_goal": "muscle_gain", "available_equipment": FULL_GYM}
    picked = filter_exercises(prof, prefs, gym_exercises)
    leaked = [e["name"] for e in picked if e.get("level") == "advanced"]
    assert not leaked, f"advanced leaked to beginner: {leaked[:5]}"


def test_shoulder_injury_excludes_pressing_exercises():
    """Exercises listing shoulder_injury/rotator_cuff must be filtered for a
    shoulder-injured user (e.g. the previously-uncovered chin/hang/press lifts)."""
    prof = {
        "fitness_level": "intermediate",
        "dominant_dosha": "pitta",
        "injuries_or_limitations": ["shoulder_injury"],
    }
    prefs = {"gym_goal": "strength", "available_equipment": FULL_GYM}
    picked = {e["id"] for e in filter_exercises(prof, prefs, gym_exercises)}
    for banned in ["One_Handed_Hang", "Mixed_Grip_Chin", "Gironda_Sternum_Chins",
                   "Cable_Iron_Cross"]:
        assert banned not in picked, f"{banned} not filtered for shoulder_injury"


def test_no_gym_exercise_has_empty_instructions():
    """Every exercise must render instructions in the UI."""
    empty = [e["id"] for e in gym_exercises if not (e.get("instructions") or [])]
    assert not empty, f"exercises with empty instructions: {empty}"


def test_pregnant_user_gets_no_pregnancy_unsafe_poses():
    """Boat/Locust/Splits and other strong poses must not appear for a pregnant
    user. Regression against the 38 poses that defaulted to pregnancy_safe=True."""
    prof = {
        "pregnancy_or_nursing": True,
        "dominant_dosha": "vata",
        "vikriti_dominant": "vata",
        "medical_history": [],
        "injuries_or_limitations": [],
    }
    prefs = {"yoga_goal": "stress_relief", "yoga_experience": "intermediate",
             "time_of_day_preference": "morning"}
    plan = generate_yoga_plan(prof, prefs, None)
    import json
    txt = json.dumps(plan, default=str).lower()
    for banned in ["navasana", "salabhasana", "hanumanasana"]:
        assert banned not in txt, f"pregnancy-unsafe pose surfaced: {banned}"


@pytest.mark.parametrize("pid,condition", [
    ("cooling_breath", "low_blood_pressure"),
    ("hissing_breath", "asthma"),
    ("left_nostril", "depression"),
    ("extended_cooling", "heart_disease"),
    ("extended_cooling", "glaucoma"),
])
def test_cooling_pranayama_gated_for_condition(pid, condition):
    by_id = {p["id"]: p for p in pranayama_list}
    assert _pranayama_hard_blocked(by_id[pid], {condition}) is True


def test_cooling_pranayama_allowed_when_unrelated_condition():
    by_id = {p["id"]: p for p in pranayama_list}
    assert _pranayama_hard_blocked(by_id["cooling_breath"], {"diabetes"}) is False
