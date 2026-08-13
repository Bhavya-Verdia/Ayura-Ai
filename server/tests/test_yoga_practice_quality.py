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


ALL_WEEKS = [1, 2, 3, 4]


def full_plan(prof=None, pr=None, **kwargs):
    """All four weeks at once — for invariants that span the whole arc."""
    return generate_yoga_plan(prof or profile(), pr or prefs(), weeks=ALL_WEEKS, **kwargs)


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
    plan = full_plan(pr=prefs(time_available_minutes=minutes,
                              yoga_experience=experience))
    for session in sessions(plan):
        estimate = session["estimated_pose_time_minutes"]
        assert abs(estimate - minutes) / minutes <= 0.35, (
            f"{minutes}min {experience} session estimated at {estimate}min")


@pytest.mark.parametrize("minutes", [10, 15, 20, 30, 45, 60])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_the_displayed_duration_is_the_session_that_was_built(minutes, experience):
    """The badge used to render time_available_minutes echoed back, so a 60-minute
    beginner vinyasa request displayed "60 min" over 42 minutes of practice."""
    plan = full_plan(pr=prefs(time_available_minutes=minutes,
                              yoga_experience=experience,
                              yoga_style_preference=["vinyasa"]))
    for session in sessions(plan):
        # Within half a minute: the badge is whole minutes, the estimate one decimal.
        assert abs(session["total_duration_minutes"]
                   - session["estimated_pose_time_minutes"]) <= 0.5, (
            f"badge says {session['total_duration_minutes']}min, "
            f"session is {session['estimated_pose_time_minutes']}min")
        assert session["requested_duration_minutes"] == minutes


def test_a_session_that_cannot_fill_the_budget_says_so():
    """A beginner asking for an hour gets ~42 minutes: the safe pool at that level
    runs out before the budget does. Serving it silently is the dishonest part."""
    plan = full_plan(pr=prefs(time_available_minutes=60, yoga_experience="beginner",
                              yoga_style_preference=["vinyasa"]))
    short = [s for s in sessions(plan)
             if (60 - s["total_duration_minutes"]) / 60 > 0.10]
    assert short, "fixture assumption broken: expected a short beginner hour"
    for session in short:
        assert session["duration_notice"], "short session carries no explanation"
        assert str(session["total_duration_minutes"]) in session["duration_notice"]


def test_a_session_that_matches_the_request_carries_no_notice():
    plan = full_plan(pr=prefs(time_available_minutes=30, yoga_experience="intermediate"))
    for session in sessions(plan):
        if abs(30 - session["total_duration_minutes"]) / 30 <= 0.10:
            assert session["duration_notice"] is None


def test_time_estimate_covers_every_timed_block():
    """The estimate excluded Surya Namaskar and Dharana, so it did not even
    match the session's own content."""
    plan = full_plan()
    for session in sessions(plan):
        breakdown = session["time_breakdown_minutes"]
        assert session["estimated_pose_time_minutes"] == pytest.approx(
            sum(breakdown.values()), abs=0.2)
        if session["surya_namaskar"]:
            assert breakdown["surya_namaskar"] > 0
        assert breakdown["dharana"] > 0


# ── Bilateral poses ──────────────────────────────────────────────────────────

def test_unilateral_poses_are_counted_on_both_sides():
    plan = full_plan()
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
    plan = full_plan()
    for session in sessions(plan):
        assert not any(p["final_relaxation"] for p in session["warmup"])
        assert not any(p["final_relaxation"] for p in session["main_sequence"])


def test_practice_closes_with_exactly_one_final_relaxation():
    plan = full_plan()
    for session in sessions(plan):
        closing = [p for p in all_poses(session) if p["final_relaxation"]]
        assert len(closing) == 1
        assert session["cooldown"][-1]["final_relaxation"]


def test_final_relaxation_is_held_for_minutes_not_seconds():
    """Savasana shipped with a 20-second hold."""
    plan = full_plan()
    for session in sessions(plan):
        closing = next(p for p in session["cooldown"] if p["final_relaxation"])
        assert closing["duration_seconds"] >= 120


def test_no_ordinary_pose_is_held_longer_than_the_cap():
    plan = full_plan(pr=prefs(time_available_minutes=60))
    for session in sessions(plan):
        for pose in all_poses(session):
            if not pose["final_relaxation"]:
                assert pose["duration_seconds"] <= _MAX_POSE_HOLD_SECONDS


# ── Sequencing ───────────────────────────────────────────────────────────────

def test_main_sequence_follows_the_category_arc():
    plan = full_plan()
    for session in sessions(plan):
        ranks = [_CATEGORY_ARC.get(p["category"], 5) for p in session["main_sequence"]]
        # The counterpose is appended after sorting, so allow the final entry to
        # break the ordering.
        assert ranks[:-1] == sorted(ranks[:-1]), ranks


def test_backbends_and_inversions_are_always_counterposed():
    plan = full_plan()
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
    plan = full_plan()
    openers = {s["warmup"][0]["pose_id"] for s in sessions(plan) if s["warmup"]}
    assert len(openers) >= 3, openers


def test_no_pose_repeats_within_a_single_session():
    plan = full_plan()
    for session in sessions(plan):
        ids = [p["pose_id"] for p in all_poses(session)]
        assert len(ids) == len(set(ids)), ids


# ── Pool sufficiency ─────────────────────────────────────────────────────────

@pytest.mark.parametrize("condition", [
    "herniated_disc", "hypertension", "osteoporosis", "glaucoma", "vertigo",
])
def test_restricted_profiles_still_get_a_real_main_sequence(condition):
    """A herniated disc produced an empty main sequence, silently."""
    plan = full_plan(prof=profile(medical_history=[condition]))
    for session in sessions(plan):
        assert len(session["main_sequence"]) >= 2, (
            f"{condition} produced a {len(session['main_sequence'])}-pose main sequence")


def test_a_heavily_filtered_plan_says_so():
    plan = full_plan(prof=profile(age=70, medical_history=["hypertension", "arthritis"]))
    assert plan["practice_pool_notice"], (
        "a plan built from a heavily restricted pool should explain itself")


def test_an_unrestricted_plan_carries_no_pool_notice():
    plan = full_plan()
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
    plan = full_plan(prof=profile(pregnancy_or_nursing=True, pregnancy_status="pregnant",
                                  pregnancy_trimester=2))
    assert "TRIMESTER 2" in plan["disclaimer"]


# ── Determinism ──────────────────────────────────────────────────────────────

def test_the_same_profile_produces_the_same_plan():
    a = full_plan()
    b = full_plan()
    for sa, sb in zip(sessions(a), sessions(b)):
        assert [p["pose_id"] for p in all_poses(sa)] == [p["pose_id"] for p in all_poses(sb)]


# ── Daily practice (no rest days) ────────────────────────────────────────────

@pytest.mark.parametrize("time_of_day", ["morning", "evening", "flexible"])
def test_every_day_of_the_week_has_a_session(time_of_day):
    """Yoga is a daily practice — unlike resistance training it does not need
    recovery days, and the plan used to blank out two days a week."""
    plan = full_plan(pr=prefs(time_of_day_preference=time_of_day))
    for week in plan["four_week_plan"]:
        assert len(week["days"]) == 7
        assert all(d["session"] for d in week["days"]), (
            f"week {week['week']} has a day with no session")
        assert not any(d["rest"] for d in week["days"])


# ── Week-by-week generation ──────────────────────────────────────────────────

def test_generation_defaults_to_a_single_week():
    """Weeks are built one at a time so each can respond to real feedback."""
    plan = generate_yoga_plan(profile(), prefs())
    assert plan["weeks_generated"] == [1]
    assert plan["next_week"] == 2
    assert plan["total_weeks"] == 4
    assert len(plan["four_week_plan"]) == 1


def test_a_specific_week_can_be_generated_on_its_own():
    plan = generate_yoga_plan(profile(), prefs(), weeks=[3])
    assert plan["weeks_generated"] == [3]
    assert plan["four_week_plan"][0]["week"] == 3
    assert plan["four_week_plan"][0]["theme"] == "Challenge"


def test_the_last_week_offers_no_next_week():
    plan = generate_yoga_plan(profile(), prefs(), weeks=[4])
    assert plan["next_week"] is None


def test_week_one_has_no_progression_adjustment():
    assert generate_yoga_plan(profile(), prefs())["progression_adjustment"] is None


def test_recently_used_poses_are_deprioritised():
    """With seven sessions a week the pool cycles fast; the next week should
    still reach for something new where it can."""
    week1 = generate_yoga_plan(profile(), prefs())
    used = {p["pose_id"] for s in sessions(week1) for p in all_poses(s)}
    fresh = generate_yoga_plan(profile(), prefs(), weeks=[2], recent_pose_ids=used)
    fresh_ids = {p["pose_id"] for s in sessions(fresh) for p in all_poses(s)}
    repeat = generate_yoga_plan(profile(), prefs(), weeks=[2])
    repeat_ids = {p["pose_id"] for s in sessions(repeat) for p in all_poses(s)}
    assert len(fresh_ids - used) >= len(repeat_ids - used)


# ── Feedback → plan changes ──────────────────────────────────────────────────

def _week_two(feedback):
    return generate_yoga_plan(profile(), prefs(yoga_experience="intermediate"),
                              weeks=[2], feedback_history=feedback)


def _session_minutes(plan):
    # The progression levers scale the session *target*; total_duration_minutes now
    # reports what was actually built, which the pool can hold short of the target.
    return plan["four_week_plan"][0]["days"][0]["session"]["requested_duration_minutes"]


def test_too_hard_makes_the_next_week_easier():
    base = _week_two([{"difficulty": "just_right"}])
    easier = _week_two([{"difficulty": "too_hard"}])
    assert _session_minutes(easier) < _session_minutes(base)
    assert easier["user_summary"]["experience"] == "beginner"


def test_too_easy_makes_the_next_week_harder():
    base = _week_two([{"difficulty": "just_right"}])
    harder = _week_two([{"difficulty": "too_easy"}])
    assert _session_minutes(harder) > _session_minutes(base)
    assert harder["user_summary"]["experience"] == "advanced"


@pytest.mark.parametrize("answer,direction", [("too_long", -1), ("too_short", 1)])
def test_session_length_feedback_moves_the_duration(answer, direction):
    base = _session_minutes(_week_two([{"session_length": "just_right"}]))
    changed = _session_minutes(_week_two([{"session_length": answer}]))
    assert (changed - base) * direction > 0


def test_feeling_drained_biases_toward_restorative_work():
    calm = _week_two([{"energy_after": "drained"}])
    base = _week_two([{"energy_after": "neutral"}])

    def vigorous(plan):
        return sum(1 for s in sessions(plan) for p in s["main_sequence"]
                   if p["category"] in ("inversion", "backbend", "balancing"))
    assert vigorous(calm) < vigorous(base)


def test_practising_only_a_few_days_shortens_the_sessions():
    """Low adherence usually means the sessions did not fit the week."""
    busy = _session_minutes(_week_two([{"days_practised": 2}]))
    regular = _session_minutes(_week_two([{"days_practised": 7}]))
    assert busy < regular


def test_dropped_poses_never_come_back():
    week1 = generate_yoga_plan(profile(), prefs())
    used = [p["pose_id"] for s in sessions(week1) for p in all_poses(s)]
    dropped = used[0]
    later = generate_yoga_plan(
        profile(), prefs(), weeks=[2, 3, 4],
        feedback_history=[{"dropped_pose_ids": [dropped]}])
    assert dropped not in {p["pose_id"] for s in sessions(later) for p in all_poses(s)}


def test_feedback_accumulates_across_weeks():
    """Reporting 'too hard' three weeks running should keep easing, not reset."""
    once = _session_minutes(_week_two([{"difficulty": "too_hard"}]))
    thrice = _session_minutes(_week_two([{"difficulty": "too_hard"}] * 3))
    assert thrice < once


def test_repeated_feedback_cannot_shrink_the_practice_to_nothing():
    extreme = [{"difficulty": "too_hard", "session_length": "too_long",
                "energy_after": "drained", "days_practised": 0}] * 8
    plan = generate_yoga_plan(profile(), prefs(), weeks=[4], feedback_history=extreme)
    session = plan["four_week_plan"][0]["days"][0]["session"]
    assert session["total_duration_minutes"] >= 10
    assert len(session["main_sequence"]) >= 2


def test_the_adjustment_explains_itself_in_plain_language():
    plan = _week_two([{"difficulty": "too_hard", "energy_after": "drained"}])
    reasons = plan["progression_adjustment"]["reasons"]
    assert reasons and all(isinstance(r, str) and r.strip() for r in reasons)


def test_malformed_feedback_is_ignored_rather_than_crashing():
    for junk in ([None], ["nonsense"], [{"difficulty": "banana"}], [{}]):
        plan = generate_yoga_plan(profile(), prefs(), weeks=[2], feedback_history=junk)
        assert plan["four_week_plan"][0]["days"][0]["session"]
