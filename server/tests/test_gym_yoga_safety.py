"""
Regression tests for gym & yoga plan-quality and safety invariants.

These lock in the demo-hardening fixes:
  - beginners get full (non-empty) workout days even with a full gym
  - genuinely-advanced movements never reach beginner/intermediate plans
  - injury contraindications actually filter exercises
  - pregnancy-unsafe poses never reach a pregnant user
  - cooling/forceful pranayama is gated for the relevant medical conditions
"""
import collections
import re

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


# ── Bodyweight coverage and the beginner's first month ───────────────────────

def test_a_beginner_is_never_prescribed_plyometrics():
    """The level allowance hands beginners the intermediate tier on purpose —
    the dataset files foundational lifts (bench press, rows, shoulder press) as
    intermediate, and a beginner-only gate leaves push and pull days empty. Jump
    training is not what that allowance was for, and not one of the 25
    plyometrics is rated beginner: 16 intermediate, 9 advanced.

    Before this, a beginner asking for endurance was served Rocket Jump and
    Freehand Jump Squat nine times each over four weeks, because "endurance"
    resolved to cardio plus plyometrics and nothing else.
    """
    from services.gym_plan_engine import filter_exercises, gym_exercises

    for goal in ("endurance", "fat_loss", "general_fitness"):
        pool = filter_exercises({**_YOGA_BASE_PROFILE, "fitness_level": "beginner"},
                                {"available_equipment": ["bodyweight"], "gym_goal": goal},
                                gym_exercises)
        plyo = [e["name"] for e in pool if e.get("category") == "plyometrics"]
        assert not plyo, f"{goal}: plyometrics in a beginner pool — {plyo[:4]}"

    # An intermediate still gets them; this is a beginner gate, not a ban.
    inter = filter_exercises({**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
                             {"available_equipment": ["bodyweight"], "gym_goal": "endurance"},
                             gym_exercises)
    assert [e for e in inter if e.get("category") == "plyometrics"]


@pytest.mark.parametrize("goal", ["general_fitness", "muscle_gain", "endurance", "fat_loss"])
def test_a_home_user_can_train_every_muscle_group(goal):
    """`goal_suitability` is derived from `category`, so all 797 strength
    exercises were `endurance: false` and "endurance" meant cardio plus
    plyometrics — 45 exercises, 16 after the bodyweight filter, with ZERO for
    chest, back, shoulders, biceps or core. Bodyweight and band work is high-rep
    by nature and now counts for endurance and fat loss.

    The other half was content: 130 of 893 exercises are bodyweight and 42 of
    those are abdominal, so a home user had one shoulder exercise and two for
    biceps. Eleven equipment-free additions cover shoulders, biceps and back.
    """
    from services.gym_plan_engine import filter_exercises, split_by_muscle_group, gym_exercises

    pool = filter_exercises({**_YOGA_BASE_PROFILE, "fitness_level": "beginner"},
                            {"available_equipment": ["bodyweight"], "gym_goal": goal},
                            gym_exercises)
    split = split_by_muscle_group(pool)
    for group in ("chest", "back", "shoulders", "biceps", "triceps", "legs", "core"):
        assert len(split[group]) >= 2, (
            f"{goal}: only {len(split[group])} bodyweight options for {group} — "
            "a home user cannot train it")


# ── Progression and session length ───────────────────────────────────────────

@pytest.mark.parametrize("goal", ["muscle_gain", "strength", "fat_loss", "general_fitness", "endurance"])
def test_a_focus_day_keeps_its_exercises_across_the_block(goal):
    """Progressive overload needs the same movement to come back.

    The selection seed included the week, so every week drew a fresh random set:
    week 1 and week 2 of the same focus day shared 0-20% of their exercises,
    while that week's own note told the practitioner "same weight as W1, push for
    extra reps" and "add 2.5-5 kg vs Week 1 on main lifts". You cannot add 2.5 kg
    to a lift you are not doing, so the four-week periodisation — the best-built
    thing in this engine — was decoration.
    """
    from services.gym_plan_engine import generate_gym_plan

    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
         "gym_goal": goal, "workout_days_per_week": 4, "workout_duration_minutes": 45})

    by_focus = {}
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            if day.get("type") == "recovery" or not day["main_workout"]:
                continue
            names = {e["exercise_name"] for e in day["main_workout"]}
            by_focus.setdefault(day["focus"], {})[week["week"]] = names

    for focus, weeks in by_focus.items():
        first = weeks[1]
        for later in (2, 3, 4):
            kept = len(first & weeks[later]) / len(first)
            assert kept >= 0.5, (
                f"{goal} {focus}: only {kept:.0%} of week 1's exercises survive to "
                f"week {later} — the week's own note tells the user to add weight to them")


@pytest.mark.parametrize("goal", ["muscle_gain", "fat_loss", "general_fitness"])
def test_a_longer_session_is_a_longer_session(goal):
    """`_target_count` bucketed duration into 3, 4 or 5 and stopped, so 45 and 60
    minutes produced byte-identical sessions."""
    from services.gym_plan_engine import generate_gym_plan

    def day_one(minutes):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
             "gym_goal": goal, "workout_days_per_week": 4,
             "workout_duration_minutes": minutes})
        return plan["four_week_plan"][0]["days"][0]

    short, long = day_one(30), day_one(60)
    assert len(long["main_workout"]) > len(short["main_workout"]), (
        f"{goal}: 60 minutes buys no more work than 30")
    assert long["estimated_duration_minutes"] > short["estimated_duration_minutes"]


@pytest.mark.parametrize("minutes", [30, 45, 60])
@pytest.mark.parametrize("goal", ["muscle_gain", "fat_loss", "general_fitness", "strength"])
def test_the_reported_session_length_is_the_one_that_was_built(goal, minutes):
    """It echoed the preference straight back, so a 60-minute heading sat above
    26 minutes of work. Where the goal's rest intervals make the requested length
    impossible, the day says so rather than quietly misreporting."""
    from services.gym_plan_engine import generate_gym_plan

    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
         "gym_goal": goal, "workout_days_per_week": 4, "workout_duration_minutes": minutes})

    for week in plan["four_week_plan"]:
        for day in week["days"]:
            if day.get("type") == "recovery" or not day["main_workout"]:
                continue
            built = day["estimated_duration_minutes"]
            work = sum(e["sets"] * e["rest_seconds"] for e in day["main_workout"]) / 60
            assert built > work, "reported length is below its own rest time"
            if abs(built - minutes) / minutes > 0.15:
                assert day["duration_notice"], f"{goal} {minutes}min built {built} in silence"


# ── Age, selection quality, and the fields the user reads ────────────────────

@pytest.mark.parametrize("age,expect_gated", [(30, False), (65, True), (16, True)])
def test_age_gates_impact_and_axial_loading(age, expect_gated):
    """Age was not an input to the gym filter at all — a 65-year-old received a
    plan identical to a 30-year-old's, same exercises, same loads, same volume.
    The yoga engine caps seniors at beginner level and blanket-excludes fall risk;
    both features read the same profile, so the app was careful about a
    70-year-old doing a shoulderstand and indifferent to the same person doing a
    barbell back squat.
    """
    from services.gym_plan_engine import filter_exercises, gym_exercises

    pool = filter_exercises({**_YOGA_BASE_PROFILE, "age": age, "fitness_level": "advanced"},
                            {"available_equipment": ["barbell", "dumbbell", "machine", "cable",
                                                     "bodyweight"],
                             "gym_goal": "general_fitness"}, gym_exercises)
    plyo = [e["name"] for e in pool if e.get("category") == "plyometrics"]
    advanced = [e["name"] for e in pool if e.get("level") == "advanced"]
    axial = [e["name"] for e in pool if "osteoporosis" in (e.get("contraindications") or [])]

    if expect_gated:
        assert not plyo, f"age {age} offered jump training: {plyo[:3]}"
        assert not advanced, f"age {age} offered advanced movements: {advanced[:3]}"
        assert not axial, f"age {age} offered axial-loading work: {axial[:3]}"
    else:
        assert advanced or axial, "an adult should still reach the loaded end of the library"


@pytest.mark.parametrize("goal", ["muscle_gain", "strength", "fat_loss", "general_fitness"])
def test_every_session_has_a_compound_and_no_stacked_variants(goal):
    """Selection was a plain shuffle-and-take: nothing preferred a compound or
    noticed it had chosen five variants of one movement. 12-44% of days had NO
    compound at all, and a week-one chest day came out as two flye variants, a
    pullover, a machine press and a dip machine."""
    from collections import Counter
    from services.gym_plan_engine import (generate_gym_plan, gym_exercises,
                                          _is_compound, _movement_family)

    by_name = {e["name"]: e for e in gym_exercises}
    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
         "gym_goal": goal, "workout_days_per_week": 4, "workout_duration_minutes": 45})

    for week in plan["four_week_plan"]:
        for day in week["days"]:
            exercises = [by_name[e["exercise_name"]] for e in day.get("main_workout") or []]
            if not exercises:
                continue
            assert any(_is_compound(e) for e in exercises), (
                f"{goal} {day['focus']}: no compound movement in "
                f"{[e['name'] for e in exercises]}")
            worst = Counter(_movement_family(e) for e in exercises).most_common(1)[0]
            assert worst[1] <= 2, f"{goal} {day['focus']}: {worst[1]} variants of {worst[0]!r}"


def test_training_age_changes_the_volume():
    """Level gated WHICH exercises were eligible and nothing else, so a beginner
    and an advanced lifter on muscle gain both got 3x8-10 in week 1."""
    from services.gym_plan_engine import _get_goal_prescription

    for goal in ("muscle_gain", "strength", "fat_loss", "general_fitness", "endurance"):
        beginner = _get_goal_prescription(goal, 1, "beginner")
        advanced = _get_goal_prescription(goal, 1, "advanced")
        assert beginner["sets"] < advanced["sets"], goal
        # Reps and rest belong to the goal — they are what make a set what it is.
        assert beginner["reps"] == advanced["reps"] and beginner["rest_seconds"] == advanced["rest_seconds"]


def test_time_based_work_is_not_prescribed_in_repetitions():
    """"Brisk Walking — 4 sets of 18-22 reps, 20s rest." The goal prescription was
    applied to every exercise regardless of what it is.

    The rule is per exercise, not per category: burpees and jumping jacks are
    counted in reps and are filed as cardio, while a treadmill or a rowing machine
    is measured in minutes. The 21 exercises whose OWN knowledge-base entry is
    written in minutes or seconds must keep it.
    """
    from services.gym_plan_engine import generate_gym_plan, gym_exercises, _TIME_UNITS

    timed = {e["name"] for e in gym_exercises
             if _TIME_UNITS.search(str(((e.get("sets_reps") or {}).get("intermediate") or {}).get("reps", "")))}
    assert timed, "no time-based exercises left in the KB — the fixture has moved"

    seen = 0
    for goal in ("fat_loss", "endurance", "general_fitness"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": ["bodyweight"], "gym_goal": goal,
             "workout_days_per_week": 5, "workout_duration_minutes": 45})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                for entry in day.get("main_workout") or []:
                    if entry["exercise_name"] in timed:
                        seen += 1
                        assert any(u in str(entry["reps"]) for u in ("min", "sec")), (
                            f"{entry['exercise_name']} prescribed as {entry['reps']} reps")
    assert seen, "no time-based exercise was scheduled, so nothing was proven"


def test_no_exercise_ships_the_boilerplate_coaching_note():
    """873 of 904 rows carry one generated string — "Reduce weight or switch to
    bodyweight if form breaks down" — including every bodyweight exercise and
    every stretch, where it sat directly beneath a load field reading
    "Bodyweight". This one is shown to the user."""
    from services.gym_plan_engine import generate_gym_plan, _BOILERPLATE_MODIFICATION

    for equipment in (["bodyweight"], ["barbell", "dumbbell", "machine", "cable"]):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": equipment, "gym_goal": "general_fitness",
             "workout_days_per_week": 4, "workout_duration_minutes": 45})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                for entry in day.get("main_workout") or []:
                    assert entry["notes"] and entry["notes"] != _BOILERPLATE_MODIFICATION
                    if entry["equipment"] == "bodyweight":
                        assert "reduce weight" not in entry["notes"].lower(), entry["exercise_name"]


def test_a_day_is_named_for_what_it_holds():
    """Cardio is filtered out entirely for muscle-gain and strength goals, so the
    "Core Cardio" day kept its name and lost its content — all 32 of them."""
    from services.gym_plan_engine import generate_gym_plan

    for goal in ("muscle_gain", "strength"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
             "gym_goal": goal, "workout_days_per_week": 5, "workout_duration_minutes": 45})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                entries = day.get("main_workout") or []
                if not entries or "cardio" not in day["focus"].lower():
                    continue
                assert any(e["category"] == "cardio" for e in entries), (
                    f"{goal}: a day called {day['focus']!r} with no cardio in it")


# ── Movement patterns ────────────────────────────────────────────────────────

def test_the_pattern_classifier_reads_the_movement_not_the_machine():
    """"Calf Press On The Leg Press Machine" matched `leg press` and came out a
    squat, which would let a calf raise satisfy a leg day's squat quota."""
    from services.gym_plan_engine import gym_exercises, _movement_pattern

    by_name = {e["name"]: e for e in gym_exercises}
    expected = {
        "Calf Press On The Leg Press Machine": "isolation",
        "Barbell Squat": "squat",
        "Barbell Deadlift": "hinge",
        "Dumbbell Step Ups": "lunge",
        "Pullups": "pull_v",
    }
    for name, pattern in expected.items():
        if name in by_name:
            assert _movement_pattern(by_name[name]) == pattern, name


@pytest.mark.parametrize("goal", ["muscle_gain", "strength", "general_fitness"])
def test_a_leg_day_asks_you_to_squat_and_to_hinge(goal):
    """A legs day came out as step-ups, calf press, glute kickback and flutter
    kicks — two compounds by the letter of the rule, and nothing that squats or
    hinges at the hip, which is most of what leg training is for."""
    from services.gym_plan_engine import generate_gym_plan, gym_exercises, _movement_pattern

    by_name = {e["name"]: e for e in gym_exercises}
    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
         "gym_goal": goal, "workout_days_per_week": 4, "workout_duration_minutes": 45})

    for week in plan["four_week_plan"]:
        for day in week["days"]:
            if not day["focus"].lower().startswith("legs"):
                continue
            patterns = {_movement_pattern(by_name[e["exercise_name"]])
                        for e in day["main_workout"]}
            assert "squat" in patterns, f"{goal} leg day with no squat: {patterns}"
            assert "hinge" in patterns, f"{goal} leg day with no hinge: {patterns}"


def test_a_pull_day_asks_you_to_pull_from_overhead():
    from services.gym_plan_engine import generate_gym_plan, gym_exercises, _movement_pattern

    by_name = {e["name"]: e for e in gym_exercises}
    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": ["barbell", "dumbbell", "machine", "cable", "bodyweight"],
         "gym_goal": "muscle_gain", "workout_days_per_week": 4,
         "workout_duration_minutes": 45})
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            if "back" not in day["focus"].lower():
                continue
            patterns = {_movement_pattern(by_name[e["exercise_name"]])
                        for e in day["main_workout"]}
            assert "pull_v" in patterns, day["focus"]


def test_the_quota_never_costs_a_session():
    """The bodyweight-only library holds two squats, two hinges and ONE horizontal
    pull in total. A quota that had to be met would either fail or reach past the
    equipment the practitioner actually has, so it is a preference — the day still
    fills."""
    from services.gym_plan_engine import generate_gym_plan

    for goal in ("general_fitness", "muscle_gain", "endurance", "fat_loss"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "beginner"},
            {"available_equipment": ["bodyweight"], "gym_goal": goal,
             "workout_days_per_week": 4, "workout_duration_minutes": 45})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                if day.get("type") == "recovery":
                    continue
                assert len(day["main_workout"]) >= 3, f"{goal} {day['focus']} came up short"


@pytest.mark.parametrize("goal", ["general_fitness", "muscle_gain", "strength",
                                  "fat_loss", "endurance"])
def test_mobility_work_is_never_prescribed_as_a_lift(goal):
    """Foam rolling is not a set of eight.

    The dataset carries 51 stretches and 13 self-myofascial-release entries, and
    nothing separated them from training movements — so a fifth of all generated
    days served one as main work: "Calves-Smr — 3 sets of 8-12, 90s rest, 82-130
    kg". Mobility belongs to the warm-up and cool-down, which are written per
    focus and timed in seconds.
    """
    from services.gym_plan_engine import _SMR_NAME

    for equipment in (["bodyweight"], FULL_GYM):
        for level in ("beginner", "intermediate", "advanced"):
            plan = generate_gym_plan(
                {**_YOGA_BASE_PROFILE, "fitness_level": level},
                {"available_equipment": equipment, "gym_goal": goal,
                 "workout_days_per_week": 5, "workout_duration_minutes": 60})
            for week in plan["four_week_plan"]:
                for day in week["days"]:
                    for ex in day["main_workout"]:
                        assert ex["category"] != "stretching", (
                            f"{goal}/{level}: {ex['exercise_name']} is a stretch")
                        assert not _SMR_NAME.search(ex["exercise_name"]), (
                            f"{goal}/{level}: {ex['exercise_name']} is foam rolling")


def test_no_kb_entry_files_foam_rolling_as_strength():
    """The thirteen SMR rows were categorised `strength`, which is how they
    reached a chest day at all. The engine now excludes them by name as well, but
    the data is corrected so a future reader of the category alone is not misled."""
    from services.gym_plan_engine import _SMR_NAME

    mislabelled = [e["name"] for e in gym_exercises
                   if _SMR_NAME.search(e["name"]) and e["category"] != "stretching"]
    assert not mislabelled, mislabelled


@pytest.mark.parametrize("goal", ["strength", "muscle_gain", "fat_loss",
                                  "endurance", "general_fitness"])
def test_a_session_is_not_one_prescription_repeated(goal):
    """A barbell squat and a cable crossover both came out 3x8-10 with ninety
    seconds between sets. Measured over 360 generated days, 95% gave every
    exercise in the day identical sets, reps AND rest — the clearest tell that a
    plan was generated rather than programmed."""
    uniform = 0
    days = 0
    for level in ("beginner", "intermediate", "advanced"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": level},
            {"available_equipment": FULL_GYM, "gym_goal": goal,
             "workout_days_per_week": 4, "workout_duration_minutes": 60})
        for day in plan["four_week_plan"][0]["days"]:
            main = day["main_workout"]
            if len(main) < 3:
                continue
            days += 1
            if len({(e["sets"], str(e["reps"]), e["rest_seconds"]) for e in main}) == 1:
                uniform += 1
    assert days and uniform == 0, f"{goal}: {uniform}/{days} days are one prescription repeated"


@pytest.mark.parametrize("goal", ["strength", "muscle_gain", "general_fitness"])
def test_the_heaviest_work_comes_first(goal):
    """Selection optimises for which movement patterns the day contains and
    returned them in whatever order it found them, so a chest day opened with a
    push-up and ran three triceps extensions before it reached a fly. A session
    is performed in an order, and the order is the programme."""
    from services.gym_plan_engine import _ROLE_ORDER

    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": FULL_GYM, "gym_goal": goal,
         "workout_days_per_week": 5, "workout_duration_minutes": 60})
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            ranks = [_ROLE_ORDER.index(e["role"]) for e in day["main_workout"]]
            assert ranks == sorted(ranks), (
                f"{goal} {day['focus']}: "
                f"{[(e['exercise_name'], e['role']) for e in day['main_workout']]}")


@pytest.mark.parametrize("goal", ["strength", "muscle_gain", "fat_loss"])
def test_a_main_lift_rests_longer_than_the_isolation_after_it(goal):
    """Rest interval is the difference between a set of five and a set of
    fifteen. Giving a cable curl the squat's three minutes is not a small
    inaccuracy — it is most of why the session took the time it claimed."""
    plan = generate_gym_plan(
        {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
        {"available_equipment": FULL_GYM, "gym_goal": goal,
         "workout_days_per_week": 4, "workout_duration_minutes": 60})
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            main = [e for e in day["main_workout"] if e["role"] in ("primary", "accessory")]
            primary = [e for e in main if e["role"] == "primary"]
            accessory = [e for e in main if e["role"] == "accessory"]
            if not primary or not accessory:
                continue
            assert min(e["rest_seconds"] for e in primary) > max(e["rest_seconds"] for e in accessory), day["focus"]
            assert min(e["sets"] for e in primary) >= max(e["sets"] for e in accessory), day["focus"]


@pytest.mark.parametrize("level", ["beginner", "intermediate", "advanced"])
def test_the_week_header_describes_the_lifts_underneath_it(level):
    """The header used the intermediate prescription whoever was reading it, so
    two thirds of plans announced a set count no exercise under them used — a
    beginner was told three sets above a page of twos."""
    for goal in ("strength", "muscle_gain", "endurance"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": level},
            {"available_equipment": FULL_GYM, "gym_goal": goal,
             "workout_days_per_week": 4, "workout_duration_minutes": 60})
        for week in plan["four_week_plan"]:
            hdr = week["prescription"]
            for day in week["days"]:
                for ex in day["main_workout"]:
                    if ex["role"] != "primary":
                        continue
                    assert (ex["sets"], ex["reps"], ex["rest_seconds"]) == (
                        hdr["sets"], hdr["reps"], hdr["rest_seconds"]), (
                        f"{level}/{goal} W{week['week']}: header {hdr['sets']}x{hdr['reps']} "
                        f"vs {ex['exercise_name']} {ex['sets']}x{ex['reps']}")


@pytest.mark.parametrize("focus_word,headline,paired", [
    ("chest triceps", "chest", "triceps"),
    ("back biceps", "back", "biceps"),
    ("legs core", "legs", "core"),
])
def test_a_day_trains_the_muscle_it_is_named_for_most(focus_word, headline, paired):
    """The pool was the concatenation of the day's muscle groups, and selection
    never asked which muscle an exercise trained — so a day filled up with
    whichever muscle the dataset holds the most of. The library carries 90
    triceps movements against 68 chest, and a Chest & Triceps day came out three
    chest and five triceps: named for the muscle it trained least."""
    from services.gym_plan_engine import _muscle_key

    by_name = {e["name"]: e for e in gym_exercises}
    for goal in ("muscle_gain", "general_fitness", "fat_loss"):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": FULL_GYM, "gym_goal": goal,
             "workout_days_per_week": 4, "workout_duration_minutes": 60})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                if day["focus"].lower() != focus_word:
                    continue
                counts = collections.Counter(
                    _muscle_key(by_name[e["exercise_name"]]) for e in day["main_workout"])
                assert counts[headline] >= counts[paired], (
                    f"{goal} {day['focus']}: {dict(counts)}")


def test_weekly_volume_puts_the_big_muscles_ahead_of_the_small_ones():
    """Across a four-day week the practitioner accumulated 13 sets of triceps
    against 6 of chest, and 15 of biceps against 9 of back. Arms are trained
    directly on their own day and indirectly on every press and every row; when
    they outrank the muscles that drive those lifts, the split is upside down."""
    from services.gym_plan_engine import _muscle_key

    by_name = {e["name"]: e for e in gym_exercises}
    for days_per_week in (4, 5, 6):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "fitness_level": "intermediate"},
            {"available_equipment": FULL_GYM, "gym_goal": "muscle_gain",
             "workout_days_per_week": days_per_week, "workout_duration_minutes": 60})
        volume = collections.Counter()
        for day in plan["four_week_plan"][0]["days"]:
            for ex in day["main_workout"]:
                volume[_muscle_key(by_name[ex["exercise_name"]])] += ex["sets"]
        assert volume["chest"] >= volume["triceps"], f"{days_per_week}d: {dict(volume)}"
        assert volume["back"] >= volume["biceps"], f"{days_per_week}d: {dict(volume)}"


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
@pytest.mark.parametrize("goal", ["strength", "muscle_gain"])
def test_every_constitution_can_reach_the_foundational_lifts(dosha, goal):
    """All 179 barbell exercises were tagged `pitta: avoid` — the tag was derived
    from the EQUIPMENT, not the movement — and the pool was cut to the best 200
    by dosha score. The gap between `good` (+2) and `avoid` (-2) is wider than
    the pool is deep, so the tag did not demote those lifts, it deleted them: a
    Vata or Pitta practitioner asking for a strength programme with a full gym
    never saw a barbell squat, deadlift, bench press, row or overhead press."""
    pool = {e["name"] for e in filter_exercises(
        {**_YOGA_BASE_PROFILE, "dominant_dosha": dosha, "fitness_level": "intermediate"},
        {"available_equipment": FULL_GYM, "gym_goal": goal}, gym_exercises)}
    for lift in ("Barbell Squat", "Barbell Deadlift", "Barbell Bench Press - Medium Grip",
                 "Barbell Shoulder Press", "Bent Over Barbell Row"):
        assert lift in pool, f"{dosha}/{goal} cannot be prescribed {lift}"


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_the_pool_cut_never_empties_a_muscle_group(dosha):
    """A single global "best N by score" is a preference that behaves like a ban.
    The cut is taken per muscle group with the compounds taken first, so no
    scoring rule — present or future — can empty a group or strip it of the
    movements that train it hardest."""
    from services.gym_plan_engine import _is_compound, split_by_muscle_group

    split = split_by_muscle_group(filter_exercises(
        {**_YOGA_BASE_PROFILE, "dominant_dosha": dosha, "fitness_level": "intermediate"},
        {"available_equipment": FULL_GYM, "gym_goal": "muscle_gain"}, gym_exercises))
    for key in ("chest", "back", "legs", "shoulders", "biceps", "triceps", "core"):
        assert len(split[key]) >= 8, f"{dosha}: {key} pool is {len(split[key])}"
        assert any(_is_compound(e) for e in split[key]), f"{dosha}: {key} has no compound"


def test_no_dosha_tag_is_derived_from_the_equipment_alone():
    """A barbell is a tool and carries no dosha. Vata's aversion is to explosive,
    irregular work and Kapha's to passive work — both movement properties, and
    both correctly tagged. Pitta's was `equipment == "barbell"`, on all 179."""
    banned = collections.Counter()
    for e in gym_exercises:
        for dosha, verdict in e["dosha_suitability"].items():
            if verdict == "avoid":
                banned[(e["equipment"], dosha)] += 1
    total = collections.Counter(e["equipment"] for e in gym_exercises)
    for (equipment, dosha), count in banned.items():
        assert count < total[equipment], (
            f"every {equipment} exercise is 'avoid' for {dosha} — that is a tag on "
            f"the equipment, not on the movement")


def _kg(text):
    """The numeric range out of a weight_range string, or None if it has none."""
    m = re.match(r"^([\d.]+)–([\d.]+) kg", text)
    return (float(m.group(1)), float(m.group(2))) if m else None


def test_the_load_is_priced_per_lift_not_per_muscle_group():
    """Load was looked up by (equipment, coarse muscle group), which is not enough
    information to price a lift. Everything a barbell did to the chest got one
    number and everything it did to the legs got another:

        Barbell Bench Press  →  35–55 kg (beginner)
        Barbell Curl         →  35–55 kg
        Barbell Deadlift     →  50–80 kg
        Barbell Squat        →  50–80 kg

    A beginner told to curl 55 kg concludes the app does not know what a curl is.
    """
    from services.gym_plan_engine import _get_weight_range

    by_name = {e["name"]: e for e in gym_exercises}
    load = {n: _kg(_get_weight_range(by_name[n], "intermediate", "male", 80))
            for n in ("Barbell Curl", "Barbell Bench Press - Medium Grip",
                      "Barbell Squat", "Barbell Deadlift")}
    curl, bench, squat, deadlift = (load[n] for n in (
        "Barbell Curl", "Barbell Bench Press - Medium Grip", "Barbell Squat", "Barbell Deadlift"))
    assert curl[1] < bench[0], f"curl {curl} is not lighter than bench {bench}"
    assert bench[1] < squat[0], f"bench {bench} is not lighter than squat {squat}"
    assert squat[1] < deadlift[1], f"squat {squat} is not lighter than deadlift {deadlift}"


def test_load_scales_with_the_practitioner():
    """It is a starting load for THIS person: their bodyweight and their training
    age. Neither was an input — the old table keyed on equipment and sex alone."""
    from services.gym_plan_engine import _get_weight_range

    squat = next(e for e in gym_exercises if e["name"] == "Barbell Squat")
    light = _kg(_get_weight_range(squat, "intermediate", "male", 55))
    heavy = _kg(_get_weight_range(squat, "intermediate", "male", 95))
    assert light[1] < heavy[0], f"bodyweight ignored: {light} vs {heavy}"

    novice = _kg(_get_weight_range(squat, "beginner", "male", 75))
    veteran = _kg(_get_weight_range(squat, "advanced", "male", 75))
    assert novice[1] < veteran[0], f"training age ignored: {novice} vs {veteran}"


def test_a_one_arm_dumbbell_press_is_the_same_dumbbell():
    """The practitioner does the sides in turn — it is not half the weight. The
    unilateral discount only applies when the implement is shared between limbs."""
    from services.gym_plan_engine import _get_weight_range

    two = {"name": "Dumbbell Shoulder Press", "equipment": "dumbbell",
           "primary_muscles": ["shoulders"], "category": "strength"}
    one = dict(two, name="Dumbbell One-Arm Shoulder Press")
    assert _get_weight_range(one, "intermediate", "male", 75) == \
           _get_weight_range(two, "intermediate", "male", 75)


@pytest.mark.parametrize("goal", ["strength", "muscle_gain", "fat_loss"])
def test_no_exercise_quotes_a_range_that_is_not_a_range(goal):
    """Light isolation rounds to a single plate step, and "2–2 kg" reads as a
    defect rather than a starting point."""
    for gender, bodyweight in (("female", 52), ("male", 90)):
        plan = generate_gym_plan(
            {**_YOGA_BASE_PROFILE, "gender": gender, "weight_kg": bodyweight,
             "fitness_level": "beginner"},
            {"available_equipment": FULL_GYM, "gym_goal": goal,
             "workout_days_per_week": 5, "workout_duration_minutes": 60})
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                for ex in day["main_workout"]:
                    kg = _kg(ex["weight_range"])
                    if kg is None:
                        continue
                    assert kg[0] < kg[1], f"{ex['exercise_name']}: {ex['weight_range']}"
                    assert kg[0] > 0, f"{ex['exercise_name']}: {ex['weight_range']}"
