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


# ── Gym disease-awareness (medical_history gating) ───────────────────────────
def test_gym_gates_exercises_by_medical_condition():
    """Hypertension/heart-disease users must not get exercises the KB tags as
    contraindicated for those conditions (previously only injuries were gated)."""
    from services.gym_plan_engine import filter_exercises, gym_exercises
    prefs = {"gym_goal": "strength", "available_equipment": ["barbell", "dumbbell", "bodyweight"]}
    sick = {"dominant_dosha": "vata", "fitness_level": "intermediate",
            "medical_history": ["hypertension", "heart disease"], "injuries_or_limitations": []}
    pool = filter_exercises(sick, prefs, gym_exercises)
    leaks = [e["id"] for e in pool if {"hypertension", "heart_disease"} & set(e.get("contraindications", []))]
    assert leaks == [], f"contraindicated exercises leaked: {leaks[:5]}"


def test_gym_condition_alias_expansion():
    from services.gym_plan_engine import _condition_contra_tags
    assert "hypertension" in _condition_contra_tags(["high blood pressure"])
    assert "lower_back_pain" in _condition_contra_tags(["ankylosing_spondylitis"])
    assert "heart_disease" in _condition_contra_tags(["coronary_artery_disease"])


@pytest.mark.asyncio
async def test_gym_rare_condition_fallback_validates():
    """Rare condition → LLM maps to KB categories only; hallucinated categories dropped."""
    import services.gym_condition_fallback as f
    f._CACHE.clear()
    fake = _json.dumps({"avoid_categories": ["heart_disease", "hypertension", "FAKE_CATEGORY"]})
    with patch("services.gym_condition_fallback.llm_client") as m:
        m.generate = AsyncMock(return_value=fake)
        tags = await f.gym_avoid_tags_for_conditions(["marfan syndrome"])
    assert tags == {"heart_disease", "hypertension"}


@pytest.mark.asyncio
async def test_gym_fallback_failsafe_on_llm_error():
    import services.gym_condition_fallback as f
    f._CACHE.clear()
    with patch("services.gym_condition_fallback.llm_client") as m:
        m.generate = AsyncMock(side_effect=RuntimeError("down"))
        assert await f.gym_avoid_tags_for_conditions(["some rare disease"]) == set()


# ── Contraindication tokens the KB uses must be reachable from user input ────
#
# The two condition→tag maps are the only route from what a user reports to what a
# pose says about itself. A token the maps never emit is safety data that cannot
# fire, and nothing detects it: the KB looks complete, the filter looks correct,
# and the pose is served anyway. Measured before this was fixed — "arthritis" was
# named on 41 poses and excluded 1; hip and hamstring injuries were named on 29
# poses between them and excluded none.

_YOGA_BASE_PROFILE = {
    "id": "safety-user", "age": 32, "gender": "female",
    "dominant_dosha": "vata", "vikriti_dominant": "vata",
    "medical_history": [], "injuries_or_limitations": [],
    "current_symptoms": [], "stress_level": "moderate", "sleep_quality": "good",
    "agni_type": "sama", "ojas_level": "moderate", "bmi_category": "normal",
    "current_season": "grishma",
}
_YOGA_BASE_PREFS = {
    "yoga_experience": "intermediate", "yoga_goal": "stress_relief",
    "time_available_minutes": 30, "time_of_day_preference": "morning",
    "yoga_style_preference": ["hatha"],
}


def _yoga_pool(**profile_overrides):
    from services.yoga_plan_engine import filter_poses, yoga_poses
    return filter_poses({**_YOGA_BASE_PROFILE, **profile_overrides},
                        _YOGA_BASE_PREFS, yoga_poses)


def test_every_kb_contraindication_token_is_reachable():
    """Pregnancy is the deliberate exception: it runs through the trimester pools
    (_TRIMESTER_*), not the contraindication maps."""
    from services.yoga_plan_engine import (
        yoga_poses, _MEDICAL_CONTRA_MAP, _INJURY_CONTRA_MAP,
    )
    kb_tokens = set()
    for pose in yoga_poses:
        kb_tokens |= set(pose.get("contraindications") or [])
        kb_tokens |= set(pose.get("medical_conditions_contraindicated") or [])

    emitted = set()
    for mapping in (_MEDICAL_CONTRA_MAP, _INJURY_CONTRA_MAP):
        for tags in mapping.values():
            emitted |= set(tags)

    unreachable = kb_tokens - emitted - {"pregnancy", "pregnancy_third_trimester"}
    assert not unreachable, (
        f"KB contraindications no user input can trigger: {sorted(unreachable)}")


@pytest.mark.parametrize("field,value,token", [
    ("medical_history", "arthritis", "arthritis"),
    ("medical_history", "osteoarthritis", "arthritis"),
    ("medical_history", "rheumatoid arthritis", "arthritis"),
    ("medical_history", "back_pain", "back_pain"),
    ("medical_history", "sciatica", "sciatica"),
    ("medical_history", "asthma", "asthma"),
    ("injuries_or_limitations", "hip injury", "hip_injury"),
    ("injuries_or_limitations", "hamstring injury", "hamstring_injury"),
    ("injuries_or_limitations", "lower back pain", "back_pain"),
])
def test_reported_condition_removes_the_poses_that_name_it(field, value, token):
    from services.yoga_plan_engine import yoga_poses

    listed = [p for p in yoga_poses
              if token in set(p.get("contraindications") or [])
              | set(p.get("medical_conditions_contraindicated") or [])]
    assert listed, f"fixture assumption broken: no pose lists {token}"

    survivors = [p["sanskrit_name"] for p in _yoga_pool(**{field: [value]})
                 if token in set(p.get("contraindications") or [])
                 | set(p.get("medical_conditions_contraindicated") or [])]
    assert not survivors, f"{value!r} left {len(survivors)} {token} poses in: {survivors[:5]}"


def test_filtering_never_leaves_the_practitioner_with_nothing():
    """The pool backfill relaxes style and goal preference when conditions thin the
    pool — it must never relax a contraindication to do it."""
    for field, value in [("medical_history", "arthritis"),
                         ("medical_history", "back_pain"),
                         ("medical_history", "herniated_disc"),
                         ("injuries_or_limitations", "hip injury")]:
        pool = _yoga_pool(**{field: [value]})
        assert len(pool) >= 12, f"{value}: pool collapsed to {len(pool)}"


# ── Spinal extension ─────────────────────────────────────────────────────────
# The mechanism vocabulary covered spinal_flexion but not its opposite, so 18
# backbending poses carried no mechanism at all and could only be excluded by
# their hand-written contraindication lists.

def test_backbends_carry_the_extension_mechanism():
    from services.yoga_plan_engine import yoga_poses
    untagged = [p["sanskrit_name"] for p in yoga_poses
                if p["category"] == "backbend"
                and "spinal_extension" not in (p.get("risk_tags") or [])]
    assert not untagged, f"backbends with no extension mechanism: {untagged}"


@pytest.mark.parametrize("condition", [
    "spondylolisthesis", "spinal_stenosis", "facet_arthropathy", "osteoporosis",
])
def test_extension_conditions_exclude_every_backbend(condition):
    survivors = [p["sanskrit_name"] for p in _yoga_pool(medical_history=[condition])
                 if "spinal_extension" in (p.get("risk_tags") or [])]
    assert not survivors, f"{condition} left backbends in: {survivors}"


def test_a_herniated_disc_does_not_lose_every_backbend():
    """Extension is frequently the therapeutic direction for a posterior disc
    herniation. Mapping herniated_disc onto spinal_extension would be a plausible
    tidy-up and a clinically wrong one, so it is asserted against."""
    from services.yoga_plan_engine import _CONDITION_RISK_TAGS
    assert "spinal_extension" not in _CONDITION_RISK_TAGS.get("herniated_disc", set())
    kept = [p for p in _yoga_pool(medical_history=["herniated_disc"])
            if "spinal_extension" in (p.get("risk_tags") or [])]
    assert kept, "herniated disc should retain the gentle backbends"


def test_every_pose_uses_a_dosha_value_the_scorer_understands():
    """`dosha_balance` is free text in the file and a fixed vocabulary in the code.

    Thirteen poses were added on 2026-08-18 written with "reduces", which reads
    correctly to a human and scores ZERO — worse than "neutral", which scores 1,
    so the new poses ranked below poses with no dosha effect at all. Nothing
    failed: the value is only ever compared with `==`, so an unrecognised one is
    silently the absence of an effect. The RAG chunk rendering it as "Balances:
    none. Aggravates: none." is what surfaced it.
    """
    from services.yoga_plan_engine import yoga_poses

    allowed = {"balances", "neutral", "aggravates"}
    bad = {p["id"]: p["dosha_balance"] for p in yoga_poses
           if set((p.get("dosha_balance") or {}).values()) - allowed}
    assert not bad, f"dosha values the scorer ignores: {bad}"

    for pose in yoga_poses:
        assert set(pose.get("dosha_balance") or {}) == {"vata", "pitta", "kapha"}, pose["id"]


# ── The week's level gate is absolute ────────────────────────────────────────

@pytest.mark.parametrize("minutes", [30, 45, 60])
@pytest.mark.parametrize("overrides", [
    {"medical_history": ["back_pain"], "injuries_or_limitations": ["herniated_disc"]},
    {"pregnancy_or_nursing": True, "pregnancy_status": "pregnant", "pregnancy_trimester": 3},
    {},
], ids=["herniated-disc", "pregnant-T3", "healthy"])
def test_session_length_never_unlocks_a_level_the_week_has_not(overrides, minutes):
    """Asking for a longer session must not reach past the week's own levels.

    The gate was dropped whenever the week's levels did not hold enough material
    to fill the asana budget. A herniated-disc beginner asking for 60 minutes got
    plank, side plank, dolphin, half moon and eagle in WEEK ONE — 167 poses above
    their week's level across the four weeks, 12 of those sessions carrying no
    disclosure at all. A third-trimester pregnancy at 30 minutes got 86.

    This is the surface the daily arc is already forbidden from opening, only
    behind a duration setting rather than a weekday. A pool too small for the
    budget has an answer that is tested and disclosed: hold the safe poses longer
    and say the session came up short.
    """
    from services.yoga_plan_engine import generate_yoga_plan, yoga_poses

    by_id = {p["id"]: p for p in yoga_poses}
    profile = {**_YOGA_BASE_PROFILE, **overrides}
    for week in (1, 2, 3, 4):
        allowed = {"beginner"} if week < 3 else {"beginner", "intermediate"}
        plan = generate_yoga_plan(profile,
                                  {**_YOGA_BASE_PREFS, "yoga_experience": "beginner",
                                   "time_available_minutes": minutes},
                                  weeks=[week])
        for day in plan["four_week_plan"][0]["days"]:
            session = day["session"]
            served = [p for section in ("warmup", "main_sequence", "cooldown")
                      for p in session[section]]
            above = [p["pose_id"] for p in served
                     if by_id[p["pose_id"]]["level"] not in allowed]
            assert not above, (
                f"week {week} at {minutes}min served {above} above "
                f"{sorted(allowed)} — session length reached past the level gate")


def test_a_pool_too_thin_for_the_budget_says_so_instead():
    """The replacement for widening: a short session that explains itself. A
    third-trimester pregnancy has 22 eligible poses and cannot fill an hour."""
    from services.yoga_plan_engine import generate_yoga_plan

    plan = generate_yoga_plan(
        {**_YOGA_BASE_PROFILE, "pregnancy_or_nursing": True,
         "pregnancy_status": "pregnant", "pregnancy_trimester": 3},
        {**_YOGA_BASE_PREFS, "yoga_experience": "beginner",
         "time_available_minutes": 60}, weeks=[1])
    for day in plan["four_week_plan"][0]["days"]:
        session = day["session"]
        if abs(session["total_duration_minutes"] - 60) / 60 > 0.10:
            assert session["duration_notice"], "short session with no explanation"


# ── Pregnancy is described twice; both descriptions must agree ───────────────

def test_no_kb_entry_claims_to_be_pregnancy_safe_and_contraindicates_pregnancy():
    """Pregnancy is stored TWICE — a `pregnancy_safe` boolean and a `pregnancy`
    contraindication token — and ten gym exercises said both at once:
    `pregnancy_safe: true` beside `contraindications: [..., "pregnancy"]`.

    Every one was abdominal (Toe Touchers, Scissor Kick, Hanging Leg Raise,
    Stomach Vacuum…), so the exercises a pregnant practitioner most needs kept
    away were exactly the ones the flag waved through. `filter_exercises` read
    only the boolean, so a pregnant beginner's four-week plan served Toe Touchers
    eight times and Seated Leg Tucks seven. Eight yoga poses carried the same
    contradiction, harmlessly, because `filter_poses` has always read both.
    """
    from services.gym_plan_engine import gym_exercises
    from services.yoga_plan_engine import yoga_poses

    for label, entries in (("gym", gym_exercises), ("yoga", yoga_poses)):
        contradictory = [e.get("id") or e.get("name") for e in entries
                         if e.get("pregnancy_safe")
                         and "pregnancy" in (e.get("contraindications") or [])]
        assert not contradictory, (
            f"{label}: marked pregnancy-safe while contraindicating pregnancy: "
            f"{contradictory[:6]}")


@pytest.mark.parametrize("equipment", [["bodyweight"], ["barbell", "dumbbell", "machine", "cable"]])
@pytest.mark.parametrize("goal", ["general_fitness", "muscle_gain", "endurance"])
def test_a_pregnant_user_is_never_prescribed_a_pregnancy_contraindicated_exercise(equipment, goal):
    """The gate, not the data — either field saying no has to be a no, so that
    correcting one file later cannot quietly reopen this."""
    from services.gym_plan_engine import generate_gym_plan, gym_exercises

    by_name = {e["name"]: e for e in gym_exercises}
    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "beginner", "pregnancy_or_nursing": True},
        {"available_equipment": equipment, "gym_goal": goal,
         "workout_days_per_week": 4, "workout_duration_minutes": 45})

    for week in plan["four_week_plan"]:
        for day in week["days"]:
            for entry in day.get("main_workout") or []:
                exercise = by_name[entry["exercise_name"]]
                assert exercise.get("pregnancy_safe"), entry["exercise_name"]
                assert "pregnancy" not in (exercise.get("contraindications") or []), \
                    entry["exercise_name"]


def test_a_pregnant_plan_says_the_library_is_thin():
    """13 safe exercises at beginner level is not a prenatal programme, and the
    plan should not imply that it is."""
    from services.gym_plan_engine import generate_gym_plan

    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "beginner", "pregnancy_or_nursing": True},
        {"available_equipment": ["bodyweight"], "gym_goal": "general_fitness",
         "workout_days_per_week": 4, "workout_duration_minutes": 45})
    assert plan["pool_notice"] and "prenatal" in plan["pool_notice"]

    unrestricted = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable"],
         "gym_goal": "muscle_gain", "workout_days_per_week": 4,
         "workout_duration_minutes": 45})
    assert unrestricted["pool_notice"] is None
