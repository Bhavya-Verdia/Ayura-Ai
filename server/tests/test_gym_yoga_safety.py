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


# ── Dynamic (LLM) protocol: pose-level contraindications for rare conditions ──
import json as _json
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
async def test_dynamic_protocol_validates_and_avoid_wins():
    """The rare-condition LLM protocol must drop hallucinated pose IDs and never
    keep a pose in both priority and avoid (avoid wins for safety)."""
    from services.yoga_condition_fallback import _generate_single_protocol, _CACHE
    _CACHE.clear()
    fake = _json.dumps({
        "condition": "some_rare_myelopathy",
        "name": "Test Protocol",
        "priority_pose_ids": ["snake_pose", "tree", "NOT_A_REAL_POSE"],
        "priority_pranayama_ids": ["ocean_breath"],
        "avoid_pranayama_ids": [],
        "avoid_pose_ids": ["tree", "ALSO_FAKE"],   # tree also in priority → avoid wins
    })
    with patch("services.yoga_condition_fallback.llm_client") as m:
        m.generate = AsyncMock(return_value=fake)
        proto = await _generate_single_protocol("some rare myelopathy",
                                                ["snake_pose", "tree", "cow"], ["ocean_breath"])
    assert proto["avoid_pose_ids"] == ["tree"]            # fake dropped
    assert "NOT_A_REAL_POSE" not in proto["priority_pose_ids"]  # hallucination dropped
    assert "tree" not in proto["priority_pose_ids"]       # avoid wins over priority


def test_avoided_pose_excluded_by_filter():
    """A dynamic protocol's avoid_pose_ids must hard-exclude that pose from the
    filtered pool for a user with that condition — verified at pose-id level."""
    from services.yoga_plan_engine import filter_poses, yoga_poses
    prof = {
        "dominant_dosha": "vata", "vikriti_dominant": "vata",
        "medical_history": ["rare_spinal_condition"],
        "injuries_or_limitations": [], "age": 35,
    }
    prefs = {"yoga_goal": "flexibility", "yoga_experience": "intermediate"}
    # tiger_pose 'balances' Vata (+3) → normally ranks into the pool.
    base_ids = {p.get("id") for p in filter_poses(prof, prefs, yoga_poses, protocol_map={})}
    assert "tiger_pose" in base_ids, "precondition: tiger_pose is normally eligible"

    proto_map = {"rare_spinal_condition": {"priority_pose_ids": [], "avoid_pose_ids": ["tiger_pose"]}}
    avoided_ids = {p.get("id") for p in filter_poses(prof, prefs, yoga_poses, protocol_map=proto_map)}
    assert "tiger_pose" not in avoided_ids, "avoid_pose_ids must hard-exclude the pose"
