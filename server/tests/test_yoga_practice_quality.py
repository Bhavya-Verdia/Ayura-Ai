"""
Regression tests for yoga plan *quality* — the properties that make a generated
plan a real practice rather than a list of poses.

The existing yoga tests (test_gym_yoga_safety.py) cover contraindication gating.
None of them would have caught what this suite locks in, which is why all of it
shipped: a 30-minute request producing nine minutes of content, Savasana opening
every session, unilateral poses counted as a single hold, a herniated disc
yielding an empty main sequence, and sequences with no arc or counterposing.
"""
import pytest

from services.yoga_plan_engine import (
    generate_yoga_plan,
    filter_poses,
    yoga_poses,
    _CATEGORY_ARC,
    _COUNTERPOSE_CATEGORIES,
    _NEEDS_COUNTERPOSE,
    _MAX_POSE_HOLD_SECONDS,
)

BASE_PROFILE = {
    "id": "test-user", "age": 32, "gender": "female",
    "dominant_dosha": "vata", "vikriti_dominant": "vata",
    "medical_history": [], "current_symptoms": [],
    "stress_level": "moderate", "sleep_quality": "good",
    "agni_type": "sama", "ojas_level": "moderate",
    "bmi_category": "normal", "current_season": "grishma",
}

BASE_PREFS = {
    "yoga_experience": "beginner", "yoga_goal": "stress_relief",
    "time_available_minutes": 30, "time_of_day_preference": "morning",
    "yoga_style_preference": ["hatha"],
}


def profile(**overrides):
    return {**BASE_PROFILE, **overrides}


def prefs(**overrides):
    return {**BASE_PREFS, **overrides}


def sessions(plan):
    return [d["session"] for w in plan["four_week_plan"]
            for d in w["days"] if d.get("session")]


def all_poses(session):
    return session["warmup"] + session["main_sequence"] + session["cooldown"]


# ── Session length ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("minutes", [15, 20, 30, 45, 60])
@pytest.mark.parametrize("experience", ["beginner", "intermediate"])
def test_session_length_is_close_to_what_was_requested(minutes, experience):
    """A 30-minute request used to produce 5-9 minutes of practice."""
    plan = generate_yoga_plan(
        profile(), prefs(time_available_minutes=minutes, yoga_experience=experience))
    for session in sessions(plan):
        estimate = session["estimated_pose_time_minutes"]
        assert abs(estimate - minutes) / minutes <= 0.35, (
            f"{minutes}min {experience} session estimated at {estimate}min")


def test_time_estimate_covers_every_timed_block():
    """The estimate excluded Surya Namaskar and Dharana, so it did not even
    match the session's own content."""
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        breakdown = session["time_breakdown_minutes"]
        assert session["estimated_pose_time_minutes"] == pytest.approx(
            sum(breakdown.values()), abs=0.2)
        if session["surya_namaskar"]:
            assert breakdown["surya_namaskar"] > 0
        assert breakdown["dharana"] > 0


# ── Bilateral poses ──────────────────────────────────────────────────────────

def test_unilateral_poses_are_counted_on_both_sides():
    plan = generate_yoga_plan(profile(), prefs())
    seen_bilateral = False
    for session in sessions(plan):
        for pose in all_poses(session):
            assert pose["total_duration_seconds"] == pose["duration_seconds"] * pose["sides"]
            if pose["bilateral"]:
                seen_bilateral = True
                assert pose["sides"] == 2
                assert pose["side_cue"]
    assert seen_bilateral, "no bilateral pose appeared in a 4-week plan"


# ── Savasana placement ───────────────────────────────────────────────────────

def test_savasana_never_opens_a_practice():
    """Corpse pose qualified for the warmup pool and opened all 20 sessions."""
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        assert not any(p["final_relaxation"] for p in session["warmup"])
        assert not any(p["final_relaxation"] for p in session["main_sequence"])


def test_practice_closes_with_exactly_one_final_relaxation():
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        closing = [p for p in all_poses(session) if p["final_relaxation"]]
        assert len(closing) == 1
        assert session["cooldown"][-1]["final_relaxation"]


def test_final_relaxation_is_held_for_minutes_not_seconds():
    """Savasana shipped with a 20-second hold."""
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        closing = next(p for p in session["cooldown"] if p["final_relaxation"])
        assert closing["duration_seconds"] >= 120


def test_no_ordinary_pose_is_held_longer_than_the_cap():
    plan = generate_yoga_plan(profile(), prefs(time_available_minutes=60))
    for session in sessions(plan):
        for pose in all_poses(session):
            if not pose["final_relaxation"]:
                assert pose["duration_seconds"] <= _MAX_POSE_HOLD_SECONDS


# ── Sequencing ───────────────────────────────────────────────────────────────

def test_main_sequence_follows_the_category_arc():
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        ranks = [_CATEGORY_ARC.get(p["category"], 5) for p in session["main_sequence"]]
        # The counterpose is appended after sorting, so allow the final entry to
        # break the ordering.
        assert ranks[:-1] == sorted(ranks[:-1]), ranks


def test_backbends_and_inversions_are_always_counterposed():
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        sequence = session["main_sequence"] + session["cooldown"]
        peaks = [i for i, p in enumerate(sequence)
                 if p["category"] in _NEEDS_COUNTERPOSE]
        if not peaks:
            continue
        after = sequence[max(peaks) + 1:]
        assert any(p["category"] in _COUNTERPOSE_CATEGORIES for p in after), (
            "peak pose left unresolved: "
            + " -> ".join(f"{p['pose_name']}({p['category']})" for p in sequence))


def test_the_opening_pose_varies_across_the_plan():
    """Child's Pose used to open all 20 sessions."""
    plan = generate_yoga_plan(profile(), prefs())
    openers = {s["warmup"][0]["pose_id"] for s in sessions(plan) if s["warmup"]}
    assert len(openers) >= 3, openers


def test_no_pose_repeats_within_a_single_session():
    plan = generate_yoga_plan(profile(), prefs())
    for session in sessions(plan):
        ids = [p["pose_id"] for p in all_poses(session)]
        assert len(ids) == len(set(ids)), ids


# ── Pool sufficiency ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("condition", [
    "herniated_disc", "hypertension", "osteoporosis", "glaucoma", "vertigo",
])
def test_restricted_profiles_still_get_a_real_main_sequence(condition):
    """A herniated disc produced an empty main sequence, silently."""
    plan = generate_yoga_plan(profile(medical_history=[condition]), prefs())
    for session in sessions(plan):
        assert len(session["main_sequence"]) >= 2, (
            f"{condition} produced a {len(session['main_sequence'])}-pose main sequence")


def test_a_heavily_filtered_plan_says_so():
    plan = generate_yoga_plan(
        profile(age=70, medical_history=["hypertension", "arthritis"]), prefs())
    assert plan["practice_pool_notice"], (
        "a plan built from a heavily restricted pool should explain itself")


def test_an_unrestricted_plan_carries_no_pool_notice():
    plan = generate_yoga_plan(profile(), prefs())
    assert plan["practice_pool_notice"] is None


# ── Mechanism-level safety ───────────────────────────────────────────────────

@pytest.mark.parametrize("condition,forbidden", [
    ("hernia",          ["boat", "locust_pose", "plow", "crow", "garland_pose"]),
    ("glaucoma",        ["supported_headstand_pose", "shoulder_stand", "plow",
                         "downward_facing_dog", "gorilla_pose"]),
    ("retinal_detachment", ["supported_headstand_pose", "shoulder_stand", "dolphin_pose"]),
    ("epilepsy",        ["supported_headstand_pose", "wheel", "forearm_stand"]),
    ("vertigo",         ["tree_pose", "eagle", "half_moon", "dancer_pose"]),
    ("osteoporosis",    ["seated_forward_bend", "gorilla_pose", "big_toe_pose"]),
    ("carpal_tunnel",   ["plank", "downward_facing_dog", "crow",
                         "four_limbed_staff_pose"]),
])
def test_conditions_exclude_the_poses_that_actually_endanger_them(condition, forbidden):
    """These used to be mapped onto unrelated tags — hernia onto knee_injury,
    epilepsy onto heart_disease — so the dangerous poses were never removed."""
    prof = profile(medical_history=[condition])
    pool_ids = {p["id"] for p in filter_poses(prof, prefs(), yoga_poses)}
    leaked = sorted(set(forbidden) & pool_ids)
    assert not leaked, f"{condition} should exclude {leaked}"


def test_wrist_injury_excludes_weight_bearing_on_the_hands():
    prof = profile(injuries_or_limitations=["wrist pain"])
    pool_ids = {p["id"] for p in filter_poses(prof, prefs(), yoga_poses)}
    assert not ({"plank", "crow", "downward_facing_dog"} & pool_ids)


# ── Pregnancy and nursing ────────────────────────────────────────────────────

def test_nursing_is_not_filtered_as_pregnancy():
    """One boolean covered both, so nursing mothers lost most of the library."""
    nursing = filter_poses(
        profile(pregnancy_or_nursing=True, pregnancy_status="nursing"),
        prefs(), yoga_poses)
    unrestricted = filter_poses(profile(), prefs(), yoga_poses)
    assert len(nursing) == len(unrestricted)


def test_trimesters_are_progressively_more_restrictive():
    pools = [
        len(filter_poses(
            profile(pregnancy_or_nursing=True, pregnancy_status="pregnant",
                    pregnancy_trimester=t),
            prefs(), yoga_poses))
        for t in (1, 2, 3)
    ]
    assert pools[0] > pools[1] > pools[2], pools


def test_third_trimester_excludes_prone_and_supine():
    prof = profile(pregnancy_or_nursing=True, pregnancy_status="pregnant",
                   pregnancy_trimester=3)
    categories = {p["category"] for p in filter_poses(prof, prefs(), yoga_poses)}
    assert "prone" not in categories
    assert "supine" not in categories
    assert "inversion" not in categories


def test_unspecified_pregnancy_flag_is_treated_as_the_safest_case():
    """Existing users only have the boolean; it must not become permissive."""
    legacy = filter_poses(profile(pregnancy_or_nursing=True), prefs(), yoga_poses)
    third = filter_poses(
        profile(pregnancy_or_nursing=True, pregnancy_status="pregnant",
                pregnancy_trimester=3), prefs(), yoga_poses)
    assert len(legacy) == len(third)


def test_pregnancy_disclaimer_names_the_trimester():
    plan = generate_yoga_plan(
        profile(pregnancy_or_nursing=True, pregnancy_status="pregnant",
                pregnancy_trimester=2), prefs())
    assert "TRIMESTER 2" in plan["disclaimer"]


# ── Determinism ──────────────────────────────────────────────────────────────

def test_the_same_profile_produces_the_same_plan():
    a = generate_yoga_plan(profile(), prefs())
    b = generate_yoga_plan(profile(), prefs())
    for sa, sb in zip(sessions(a), sessions(b)):
        assert [p["pose_id"] for p in all_poses(sa)] == [p["pose_id"] for p in all_poses(sb)]
