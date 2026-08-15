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
    _DAY_ARC,
    _arc_allows,
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
        assert breakdown["pranayama"] > 0


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


# ── Pranayama ────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("experience,minutes,expected", [
    ("beginner", 30, 12), ("intermediate", 45, 15), ("advanced", 60, 20),
    # Any level may pick any tier, and the stack is a property of the TIER.
    ("beginner", 60, 20), ("advanced", 30, 12),
])
def test_every_day_runs_the_prescribed_stack(experience, minutes, expected):
    """Bhramari, Anulom Vilom and a cleansing breath, the same three every day.
    30 minutes gets 5/4/3 rather than 5/5/5 — a half-hour session cannot spend
    half of itself breathing — and the hour gets 8/7/5. All three are always
    present."""
    for week in (1, 2, 3, 4):
        plan = generate_yoga_plan(profile(), prefs(yoga_experience=experience,
                                                   time_available_minutes=minutes),
                                  weeks=[week])
        for d in week_days(plan):
            section = d["session"]["pranayama_section"]
            names = [t["technique_name"] for t in section]
            assert len(section) == 3, f"{d['day_name']}: {names}"
            assert names[0] == "Humming Bee", names
            assert names[1] == "Alternate Nostril", names
            total = sum(t["duration_minutes"] for t in section)
            assert total == expected, f"{experience} {d['day_name']}: {total} min"


@pytest.mark.parametrize("experience,minutes,asked", [
    ("beginner", 30, 5), ("intermediate", 45, 5), ("advanced", 60, 8),
])
def test_bhramari_takes_its_full_ask_and_is_never_trimmed(experience, minutes, asked):
    """It is the one technique asked for unconditionally, so it is filled first
    and the others share what is left. The ask itself grows with the tier."""
    plan = full_plan(pr=prefs(yoga_experience=experience,
                              time_available_minutes=minutes))
    for s in sessions(plan):
        bhramari = [t for t in s["pranayama_section"] if t["technique_name"] == "Humming Bee"]
        assert bhramari, "Bhramari missing"
        assert bhramari[0]["duration_minutes"] == asked


@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_the_hours_extra_breathwork_never_lands_on_the_cleansing_breath(experience):
    """The third slot is usually Kapalabhati, which `pranayama.json` rates 3/5/10
    by experience. A pumping kriya held past its rating is a different practice —
    which is precisely why `_FORCEFUL_PRANAYAMA` is exempt from the minutes
    floor, and it would be incoherent to exempt it from a floor and then push it
    through its ceiling. The hour's extra five minutes go to Bhramari and Anulom
    Vilom, which are calming and rated 10 at advanced."""
    plan = full_plan(pr=prefs(yoga_experience=experience,
                              time_available_minutes=60))
    for s in sessions(plan):
        third = s["pranayama_section"][2]
        assert third["duration_minutes"] == 5, (
            f"the cleansing slot grew to {third['duration_minutes']} min "
            f"({third['technique_name']})")


def test_the_meditation_slot_is_gone():
    plan = full_plan()
    for s in sessions(plan):
        assert s["dharana_section"] is None
        assert s["time_breakdown_minutes"]["dharana"] == 0


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
@pytest.mark.parametrize("time_of_day", ["morning", "evening"])
def test_the_breathwork_survives_a_crowded_session(dosha, time_of_day):
    """Kapha draws far more Surya Namaskar, which pushes the fixed blocks past
    their share of the session. The prescription is not what gives — the scale
    is recomputed over the blocks that can."""
    plan = generate_yoga_plan(profile(dominant_dosha=dosha),
                              prefs(yoga_experience="advanced",
                                    time_available_minutes=60,
                                    time_of_day_preference=time_of_day),
                              weeks=[1])
    for d in week_days(plan):
        total = sum(t["duration_minutes"] for t in d["session"]["pranayama_section"])
        assert total >= 10, f"{dosha} {time_of_day} {d['day_name']}: {total} min"


def test_the_stack_does_not_swallow_a_short_session():
    """The tiers are 30/45/60; this guards preferences stored before they
    existed, where 15 minutes of breathwork would be the whole practice."""
    plan = generate_yoga_plan(profile(), prefs(time_available_minutes=15), weeks=[1])
    for d in week_days(plan):
        total = sum(t["duration_minutes"] for t in d["session"]["pranayama_section"])
        assert total <= 15 * 0.45, f"{d['day_name']}: {total} min of 15"


@pytest.mark.parametrize("condition,expected", [
    ("hypertension", "Left Nostril"),
    ("insomnia", "Three Part Breath"),
    ("migraine", "Left Nostril"),
    ("asthma", "Ocean Breath"),
    ("anxiety", "Three Part Breath"),
    ("back_pain", "Three Part Breath"),
    ("type2_diabetes", "Skull Shining"),
    ("obesity", "Skull Shining"),
])
def test_a_condition_protocol_chooses_the_third_breath(condition, expected):
    """Bhramari and Anulom Vilom are fixed, so the third slot is where clinical
    tailoring lands. Protocol beats dosha: a diagnosis is more specific than a
    constitution. Note diabetes and obesity KEEP Kapalabhati — their protocols
    prioritise it — so this is not a blanket override."""
    plan = generate_yoga_plan(profile(medical_history=[condition]),
                              prefs(yoga_experience="intermediate",
                                    time_available_minutes=45),
                              weeks=[1])
    for d in week_days(plan):
        third = d["session"]["pranayama_section"][2]
        assert third["technique_name"] == expected, (
            f"{condition} → {third['technique_name']}, expected {expected}")
    assert plan["pranayama_protocol_note"], "protocol-led choice unexplained"


def test_a_protocol_priority_cannot_reach_past_a_safety_gate():
    """The obesity protocol prioritises Kapalabhati; age forbids it. The gate
    wins and the slot falls through to something safe."""
    for age in (15, 70):
        plan = generate_yoga_plan(profile(age=age, medical_history=["obesity"]),
                                  prefs(yoga_experience="intermediate",
                                        time_available_minutes=45),
                                  weeks=[1])
        used = {t["technique_name"] for d in week_days(plan)
                for t in d["session"]["pranayama_section"]}
        assert "Skull Shining" not in used, f"age {age}: protocol bypassed the age gate"


def test_conflicting_protocols_resolve_to_one_both_permit():
    """Diabetes wants Kapalabhati; hypertension forbids it. Avoid beats
    priority, and the slot lands on the next thing the protocols recommend."""
    plan = generate_yoga_plan(
        profile(medical_history=["type2_diabetes", "hypertension"]),
        prefs(yoga_experience="intermediate", time_available_minutes=45), weeks=[1])
    used = {t["technique_name"] for d in week_days(plan)
            for t in d["session"]["pranayama_section"]}
    assert "Skull Shining" not in used
    assert len(week_days(plan)[0]["session"]["pranayama_section"]) == 3


@pytest.mark.parametrize("overrides", [
    {"age": 70, "medical_history": ["obesity"]},
    {"age": 15, "medical_history": ["obesity"]},
    {"pregnancy_status": "pregnant", "pregnancy_trimester": 3},
    {"medical_history": ["hypertension"], "age": 70},
])
def test_everyone_still_gets_three_breaths(overrides):
    """Dirgha backstops the third slot — beginner-level, no contraindications,
    safe in pregnancy. Without it a heavily gated practitioner lost the slot."""
    plan = generate_yoga_plan(profile(**overrides),
                              prefs(yoga_experience="beginner",
                                    time_available_minutes=45),
                              weeks=[1])
    for d in week_days(plan):
        assert len(d["session"]["pranayama_section"]) == 3, d["day_name"]


def test_an_unremarkable_profile_keeps_the_dosha_default():
    """No condition means no protocol, so the third slot stays constitutional."""
    plan = generate_yoga_plan(profile(), prefs(yoga_experience="intermediate",
                                               time_available_minutes=45), weeks=[1])
    assert plan["pranayama_protocol_note"] is None
    for d in week_days(plan):
        assert d["session"]["pranayama_section"][2]["technique_name"] == "Skull Shining"


def test_pitta_gets_cooling_breaths_instead_of_kapalabhati():
    """Kapalabhati is heating and Pitta is the constitution that must not be
    heated, so the cleansing slot becomes Sitali and Sitkari, alternating."""
    plan = full_plan(prof=profile(dominant_dosha="pitta", vikriti_dominant="pitta"),
                     pr=prefs(yoga_experience="intermediate",
                              time_of_day_preference="morning"))
    used = {t["technique_name"] for s in sessions(plan) for t in s["pranayama_section"]}
    assert "Skull Shining" not in used, "Kapalabhati served to a Pitta profile"
    assert {"Cooling Breath", "Hissing Breath"} <= used, used


def test_the_cooling_pair_alternates_rather_than_splitting_the_slot():
    """Two and a half minutes each is too short for either to do anything."""
    days = week_days(full_plan(prof=profile(dominant_dosha="pitta",
                                            vikriti_dominant="pitta"),
                               pr=prefs(yoga_experience="intermediate",
                                        time_available_minutes=45)))
    third = [d["session"]["pranayama_section"][2] for d in days]
    assert {t["technique_name"] for t in third} == {"Cooling Breath", "Hissing Breath"}
    assert all(t["duration_minutes"] == 5 for t in third)


def test_no_day_runs_long_on_the_prescription():
    """The breathwork is paid for out of asana, never out of the clock."""
    for minutes in (30, 45, 60):
        for experience in ("beginner", "intermediate", "advanced"):
            plan = generate_yoga_plan(profile(), prefs(yoga_experience=experience,
                                                       time_available_minutes=minutes),
                                      weeks=[1])
            for d in week_days(plan):
                built = d["session"]["total_duration_minutes"]
                assert built <= minutes * 1.10, (
                    f"{experience} {minutes}min {d['day_name']}: {built}min")


def test_the_two_named_techniques_are_preferred_when_they_are_safe():
    plan = full_plan(pr=prefs(yoga_experience="intermediate",
                              time_of_day_preference="morning"))
    used = {t["technique_name"] for s in sessions(plan) for t in s["pranayama_section"]}
    assert "Alternate Nostril" in used
    assert "Skull Shining" in used


@pytest.mark.parametrize("overrides,label", [
    ({"medical_history": ["hypertension"]}, "hypertension"),
    ({"medical_history": ["glaucoma"]}, "glaucoma"),
    ({"medical_history": ["heart_disease"]}, "heart disease"),
    ({"pregnancy_status": "pregnant", "pregnancy_trimester": 2}, "pregnancy"),
])
def test_the_emphasis_never_promotes_kapalabhati_past_a_contraindication(overrides, label):
    """The boost is applied after every gate, so it reorders safe techniques and
    never widens the set. Kapalabhati is a forceful kriya — a preference must not
    be able to outrank a contraindication."""
    plan = full_plan(prof=profile(**overrides),
                     pr=prefs(yoga_experience="advanced",
                              time_of_day_preference="morning"))
    used = {t["technique_name"] for s in sessions(plan) for t in s["pranayama_section"]}
    assert "Skull Shining" not in used, f"Kapalabhati served to a user with {label}"


def test_a_missing_emphasis_technique_explains_itself():
    """The evening gate is recoverable, and "not for you" and "not yet" are
    different messages."""
    plan = generate_yoga_plan(profile(), prefs(yoga_experience="intermediate",
                                               time_of_day_preference="evening"),
                              weeks=[1])
    notes = plan.get("pranayama_safety_exclusions") or []
    kapal = [n for n in notes if "Kapalabhati" in n["name"]]
    assert kapal, "Kapalabhati absent from an evening plan with no explanation"
    assert "morning practice" in kapal[0]["reason"].lower()


def test_beginners_get_kapalabhati_at_a_beginner_dose():
    """User decision (2026-08-14): Kapalabhati is taught from beginner level.
    Its dose is NOT stretched to the five-minute session floor — a pumping kriya
    held past what it is rated for is a different practice — so a short forceful
    primary is topped up with a calming partner instead."""
    plan = full_plan(pr=prefs(yoga_experience="beginner",
                              time_available_minutes=30,
                              time_of_day_preference="morning"))
    days = [s for s in sessions(plan)
            if any(t["technique_name"] == "Skull Shining" for t in s["pranayama_section"])]
    assert days, "Kapalabhati never appears for a beginner"
    for s in days:
        kapal = next(t for t in s["pranayama_section"]
                     if t["technique_name"] == "Skull Shining")
        assert kapal["duration_minutes"] <= 3, kapal["duration_minutes"]
        assert sum(t["duration_minutes"] for t in s["pranayama_section"]) >= 5


@pytest.mark.parametrize("age", [14, 17, 60, 70])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_forceful_kriyas_are_withheld_at_both_ends_of_the_age_range(age, experience):
    """Kapalabhati used to be level:intermediate, which shielded beginners of
    every age by accident — but an experienced 70-year-old was already being
    served it, and lowering the level to beginner widened that to everyone.
    Rapid abdominal pumping raises intra-abdominal pressure; contraindications,
    level and age are three different axes."""
    plan = full_plan(prof=profile(age=age),
                     pr=prefs(yoga_experience=experience,
                              time_of_day_preference="morning"))
    used = {t["technique_name"] for s in sessions(plan) for t in s["pranayama_section"]}
    assert "Skull Shining" not in used, f"Kapalabhati served at age {age} ({experience})"
    assert "Fire Essence" not in used, f"Agnisara served at age {age} ({experience})"


def test_adults_are_unaffected_by_the_age_gate():
    for age in (25, 45, 59):
        plan = full_plan(prof=profile(age=age),
                         pr=prefs(yoga_experience="beginner",
                                  time_of_day_preference="morning"))
        used = {t["technique_name"] for s in sessions(plan)
                for t in s["pranayama_section"]}
        assert "Skull Shining" in used, age


def test_a_short_forceful_practice_is_paired_not_stretched():
    """Kapalabhati alone at 3 minutes would undercut the session's breathwork
    floor; stretching it to 5 would overrun its own rating. It gets a partner."""
    plan = full_plan(pr=prefs(yoga_experience="beginner",
                              time_available_minutes=30,
                              time_of_day_preference="morning"))
    for s in sessions(plan):
        section = s["pranayama_section"]
        if any(t["technique_name"] == "Skull Shining" for t in section):
            assert len(section) >= 2, "Kapalabhati served alone under the floor"


# ── Daily intensity arc ──────────────────────────────────────────────────────
# The week used to be seven sessions at one intensity, which is one session seven
# times — and at week 3's 1.5x holds, seven consecutive hard ones.

def week_days(plan, week_index=0):
    return plan["four_week_plan"][week_index]["days"]


def plan_weeks(plan):
    return plan["four_week_plan"]


def test_the_week_has_a_shape_rather_than_one_intensity():
    days = week_days(full_plan())
    keys = [d["session"]["intensity"] for d in days]
    assert keys.count("strong") == 2, keys
    assert keys.count("moderate") == 3, keys
    assert keys.count("gentle") == 1, keys
    assert keys.count("restorative") == 1, keys


def test_strong_days_are_never_consecutive():
    keys = [d["session"]["intensity"] for d in week_days(full_plan())]
    assert not any(a == b == "strong" for a, b in zip(keys, keys[1:])), keys


@pytest.mark.parametrize("minutes", [15, 20, 30, 45, 60])
@pytest.mark.parametrize("week", [1, 2, 3, 4])
def test_every_day_of_the_week_asks_for_the_same_slot(minutes, week):
    """The one thing the arc must not move. A practice survives by occupying a
    fixed slot in the day; a plan asking 20 minutes on Monday and 45 on Thursday
    is a plan abandoned on Thursday. The arc changes load, never duration."""
    plan = generate_yoga_plan(profile(), prefs(time_available_minutes=minutes),
                              weeks=[week])
    days = week_days(plan)
    assert {d["session"]["requested_duration_minutes"] for d in days} == {minutes}
    # A day may still land off the slot where the safe pool runs out before the
    # budget does — a beginner asking for an hour is the standing example. What
    # it may not do is land off it silently, which is the contract the duration
    # notice already carries for the session as a whole.
    for d in days:
        session = d["session"]
        built = session["total_duration_minutes"]
        if abs(built - minutes) / minutes > 0.10:
            assert session["duration_notice"], (
                f"{d['day_name']} ({session['intensity']}) built {built}min "
                f"against a {minutes}min slot with no explanation")


@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_the_arc_does_not_make_the_week_uneven(experience):
    """At a duration the pose pool can actually serve, every day of the week
    lands on the same length. Before the overshoot and pose-floor guards, the
    restorative day ran four minutes past the slot the other six landed on,
    because a pose-count floor was being satisfied with holds minutes long."""
    for week in (1, 2, 3, 4):
        plan = generate_yoga_plan(profile(), prefs(time_available_minutes=30,
                                                   yoga_experience=experience),
                                  weeks=[week])
        built = [d["session"]["total_duration_minutes"] for d in week_days(plan)]
        assert max(built) - min(built) <= 3, (
            f"{experience} week {week} ranged {min(built)}-{max(built)}min")


def test_the_restorative_day_excludes_the_two_loaded_categories():
    """It keeps the week's sequence — that is the point of the consistency work —
    but an inversion or a deep backbend is contrary to a recovery day whatever
    your level, so those two are the exception."""
    days = week_days(full_plan())
    rest_day = next(d for d in days if d["session"]["intensity"] == "restorative")
    cats = {p["category"] for p in rest_day["session"]["main_sequence"]}
    assert not cats & {"backbend", "inversion"}, cats


def test_the_recovery_day_holds_longer_than_the_strong_days():
    days = week_days(full_plan(pr=prefs(time_available_minutes=45)))
    rest_day = next(d for d in days if d["session"]["intensity"] == "restorative")
    strong = [d for d in days if d["session"]["intensity"] == "strong"]
    longest_rest = max(p["duration_seconds"] for p in rest_day["session"]["main_sequence"])
    longest_strong = max(p["duration_seconds"]
                         for s in strong for p in s["session"]["main_sequence"])
    assert longest_rest > longest_strong


@pytest.mark.parametrize("experience", ["intermediate", "advanced"])
def test_an_easy_day_shows_the_gentler_variation_of_the_same_pose(experience):
    """The easy days keep the week's sequence, so this is what actually makes
    them easier. A hold multiplier does not: shortening holds frees budget, the
    filler spends it and `_hold_multiplier` stretches the rest back, which is why
    a measured 0.95 produced a gentle day byte-identical to a moderate one."""
    days = week_days(full_plan(pr=prefs(yoga_experience=experience)))
    easy = [d for d in days if d["session"]["intensity"] in ("gentle", "restorative")]
    hard = next(d for d in days if d["session"]["intensity"] == "strong")
    hard_mods = {p["pose_id"]: p["modification"] for p in all_poses(hard["session"])}
    for d in easy:
        shared = [p for p in all_poses(d["session"]) if p["pose_id"] in hard_mods]
        assert shared, f"{d['day_name']} shares no pose with the strong day"
        assert any(p["modification"] != hard_mods[p["pose_id"]] for p in shared), (
            f"{d['day_name']} shows the same modifications as the strong day")
        assert d["session"]["effort_cue"], d["day_name"]


def test_an_easy_day_is_still_a_full_practice():
    """Active recovery, not a stub. The arc must never empty a sequence."""
    for d in week_days(full_plan()):
        assert len(d["session"]["main_sequence"]) >= 2, d["day_name"]
        assert d["session"]["intensity_note"], d["day_name"]


@pytest.mark.parametrize("week_levels", [
    ["beginner"], ["beginner", "intermediate"],
    ["beginner", "intermediate", "advanced"],
])
def test_the_arc_only_ever_narrows_what_the_week_allows(week_levels):
    """A strong day means the full week allowance, not a new one. Putting extra
    levels or categories behind a weekday index would be a safety surface nobody
    would think to look for."""
    strong_arc = next(a for a in _DAY_ARC.values() if a["key"] == "strong")
    strong_ok = {p["id"] for p in yoga_poses if _arc_allows(p, strong_arc, week_levels)}
    assert strong_ok == {p["id"] for p in yoga_poses}, "a strong day must not filter"
    for day, arc in _DAY_ARC.items():
        allowed = {p["id"] for p in yoga_poses if _arc_allows(p, arc, week_levels)}
        assert allowed <= strong_ok, f"day {day} ({arc['key']}) permits extra poses"


def test_feedback_that_the_practice_is_too_much_softens_the_arc():
    """The arc modulates within the feedback adjustment rather than adding a
    second reduction on top of it — a week already pulled down for someone
    reporting exhaustion should not still be scheduling two strong days."""
    history = [{"week": 1, "difficulty": "too_hard", "energy_after": "drained"}]
    plan = generate_yoga_plan(profile(), prefs(), weeks=[2], feedback_history=history)
    keys = [d["session"]["intensity"] for d in week_days(plan)]
    assert "strong" not in keys, keys


# ── Core set and daily accent ────────────────────────────────────────────────
# Every day used to be a fresh shuffle of the pool. That reads as variety and
# works as amnesia: nobody gets better at Trikonasana by meeting it once.

def full_intensity_days(plan):
    return [d for d in week_days(plan)
            if d["session"]["intensity"] in ("strong", "moderate")]


def test_most_of_a_day_is_the_core_the_practitioner_is_learning():
    for d in full_intensity_days(full_plan()):
        poses = all_poses(d["session"])
        core = set(d["session"]["core_pose_ids"])
        share = len([p for p in poses if p["pose_id"] in core]) / len(poses)
        assert share >= 0.6, f"{d['day_name']} core share {share:.0%}"


def standard_days(plan, week_index=0):
    """Full-intensity days — every day now shares one asana budget."""
    return [d for d in week_days(plan, week_index)
            if d["session"]["intensity"] in ("strong", "moderate")]


def test_the_core_is_the_same_set_every_full_day_of_the_week():
    days = standard_days(full_plan())
    cores = {tuple(d["session"]["core_pose_ids"]) for d in days}
    assert len(cores) == 1, cores


def test_the_core_poses_actually_recur_across_the_week():
    days = standard_days(full_plan())
    core = set(days[0]["session"]["core_pose_ids"])
    assert core, "no core set at all"
    for pose_id in core:
        appearances = sum(1 for d in days
                          if any(p["pose_id"] == pose_id for p in all_poses(d["session"])))
        assert appearances == len(days), (
            f"{pose_id} is core but appears on {appearances}/{len(days)} days")


@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_one_day_is_mostly_yesterday(experience):
    """The property the whole core/accent split exists for. Before it, roughly
    HALF of every session changed overnight — 44-46 distinct poses across a week
    and only ~6 shared by Mon-Fri, which is a different class each morning, not a
    practice. Measured over the working days; Sat and Sun are deliberately
    different in kind, which `_DAY_ARC` owns and the arc tests cover."""
    for week in plan_weeks(full_plan(pr=prefs(yoga_experience=experience))):
        days = week["days"][:5]
        sets = [{p["pose_id"] for p in all_poses(d["session"])} for d in days]
        for prev, cur, d in zip(sets, sets[1:], days[1:]):
            overlap = len(prev & cur) / len(cur)
            assert overlap >= 0.6, (
                f"{experience} week {week['week']} {d['day_name']}: only "
                f"{overlap:.0%} of the session carried over from the day before")
        shared = set.intersection(*sets)
        assert len(shared) / (sum(len(s) for s in sets) / 5) >= 0.5, (
            f"{experience} week {week['week']}: only {len(shared)} poses run "
            f"through all five working days")


def test_a_week_that_cannot_rotate_says_so():
    """A beginner has around nine safe main-role poses and a session needs most
    of them, so the week genuinely repeats. Inventing variety would mean serving
    poses the safety filter excluded; presenting the repetition as a rotating
    week is the other way to get this wrong."""
    plan = full_plan(pr=prefs(yoga_experience="beginner"))
    limited = [s for s in sessions(plan) if s["rotation_limited"]]
    assert limited, "expected a beginner week to be too thin to rotate"
    for session in limited:
        assert session["rotation_notice"]


def test_a_plan_with_room_to_rotate_carries_no_rotation_notice():
    plan = full_plan(pr=prefs(yoga_experience="intermediate"))
    assert any(not s["rotation_limited"] for s in sessions(plan))
    for session in sessions(plan):
        if not session["rotation_limited"]:
            assert session["rotation_notice"] is None


def test_the_week_is_not_one_session_seven_times():
    """Consistency is the goal, sameness is not: where the pool has material to
    spare, the week should still move. A day that is pure core is fine — every
    day being pure core is a plan that stopped choosing."""
    plan = full_plan(pr=prefs(yoga_experience="intermediate"))
    for week in plan_weeks(plan):
        days = [d for d in week["days"] if not d["session"]["rotation_limited"]]
        if len(days) < 2:
            continue
        seqs = {frozenset(p["pose_id"] for p in all_poses(d["session"])) for d in days}
        assert len(seqs) >= 2, f"week {week['week']} is a single session repeated"


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


# ── Drawn pose figures ───────────────────────────────────────────────────────
# Poses carry joint coordinates the client draws them from. A malformed figure
# does not raise anywhere — it renders a bent stick — so the shape is asserted
# here rather than discovered by looking at it.

_JOINTS = {
    "head", "neck", "spine", "pelvis",
    "shoulderL", "shoulderR", "elbowL", "elbowR", "wristL", "wristR",
    "hipL", "hipR", "kneeL", "kneeR", "ankleL", "ankleR",
    "elbow", "wrist", "knee", "ankle",
}


def _figured_poses():
    from services.yoga_plan_engine import yoga_poses
    return [p for p in yoga_poses if p.get("figure")]


def test_figures_are_well_formed():
    figured = _figured_poses()
    assert figured, "no pose carries a figure"

    for pose in figured:
        name = pose["sanskrit_name"]
        fig = pose["figure"]

        unknown = set(fig) - _JOINTS
        assert not unknown, f"{name}: unknown joints {sorted(unknown)}"

        # Without head, neck and pelvis there is no body to hang limbs off, and
        # the renderer draws nothing at all.
        for required in ("head", "neck", "pelvis"):
            assert required in fig, f"{name}: missing {required}"

        for joint, point in fig.items():
            assert isinstance(point, list) and len(point) == 2, f"{name}.{joint} is not a point"
            x, y = point
            assert all(isinstance(v, (int, float)) for v in point), f"{name}.{joint} is not numeric"
            assert 0 <= x <= 100 and 0 <= y <= 100, f"{name}.{joint} = {point} is outside the box"


def test_figures_stand_on_the_ground_not_through_it():
    """Ground is drawn at y=92. A joint below it reads as a limb sunk into the mat."""
    for pose in _figured_poses():
        for joint, (_x, y) in pose["figure"].items():
            assert y <= 92, f"{pose['sanskrit_name']}.{joint} is below the ground line (y={y})"


def test_a_limb_is_never_half_specified():
    """A limb needs all three of its points. Two of three draws nothing, silently."""
    # The unsuffixed limbs hang off neck and pelvis, which every figure has for
    # its spine — so only their distal joints say whether the limb was drawn.
    chains = [("shoulderL", "elbowL", "wristL"), ("shoulderR", "elbowR", "wristR"),
              ("hipL", "kneeL", "ankleL"), ("hipR", "kneeR", "ankleR"),
              ("elbow", "wrist"), ("knee", "ankle")]
    for pose in _figured_poses():
        fig = pose["figure"]
        for chain in chains:
            present = [j for j in chain if j in fig]
            assert len(present) in (0, len(chain)), (
                f"{pose['sanskrit_name']}: partial limb {chain} — has {present}")


def test_the_figure_reaches_the_client():
    """Drawn in the browser from the plan payload, so it has to survive formatting."""
    from services.yoga_plan_engine import format_pose, yoga_poses

    drawn = next(p for p in yoga_poses if p.get("figure"))
    formatted = format_pose(drawn, "intermediate", week=1)
    assert formatted["figure"] == drawn["figure"]

    undrawn = next(p for p in yoga_poses if not p.get("figure"))
    assert format_pose(undrawn, "intermediate", week=1)["figure"] is None


# ── Fixed session structure (2026-08-15) ─────────────────────────────────────
# Surya Namaskar, the warm-up, the cool-down and savasana became fixed slots
# rather than shares of the leftover budget. Before this the bookends absorbed
# the length the practitioner added: a 60-minute session spent 4.8 minutes on
# sun salutations, 7.2 warming up and 7 in savasana, and the main sequence took
# what was left. The tests below pin the slots and, just as importantly, pin
# what a fixed slot must NEVER do — override a safety gate to fill itself.

def _sns(session):
    return session["surya_namaskar"]


def _closing(session):
    return next(p for p in session["cooldown"] if p["final_relaxation"])


@pytest.mark.parametrize("minutes,slot", [(30, 3.0), (45, 5.0), (60, 5.0)])
@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_surya_namaskar_fills_its_slot_whatever_the_constitution(
        minutes, slot, dosha, experience):
    """Rounds used to BE the constitutional signal — Kapha did 8 where Vata did
    2 — so the block ran anywhere from 2 to 8 minutes and the session opened at
    a different length for everybody. The dosha now sets the pace and the rounds
    fall out of the slot, so Kapha still covers more ground in the same time."""
    plan = generate_yoga_plan(
        profile(dominant_dosha=dosha, vikriti_dominant=dosha),
        prefs(time_available_minutes=minutes, yoga_experience=experience),
        weeks=[1])
    for day in plan["four_week_plan"][0]["days"]:
        block = _sns(day["session"])
        # Twelve steps is indivisible, so the block lands on the nearest whole
        # number of rounds rather than exactly on the slot.
        assert abs(block["duration_minutes"] - slot) <= 0.75, (
            f"{dosha}/{experience} @ {minutes}min: Surya Namaskar is "
            f"{block['duration_minutes']} min against a {slot} min slot")
        assert block["rounds"] >= 1


def test_a_faster_pace_buys_more_rounds_not_more_time():
    """What the dosha and experience level actually change now."""
    def rounds(dosha, experience):
        plan = generate_yoga_plan(
            profile(dominant_dosha=dosha, vikriti_dominant=dosha),
            prefs(time_available_minutes=60, yoga_experience=experience),
            weeks=[1])
        return _sns(plan["four_week_plan"][0]["days"][0]["session"])["rounds"]

    assert rounds("kapha", "advanced") > rounds("vata", "beginner")
    assert rounds("vata", "advanced") >= rounds("vata", "beginner")


@pytest.mark.parametrize("minutes,slot_minutes", [(30, 3), (45, 5), (60, 5)])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_the_warmup_is_a_fixed_slot(minutes, slot_minutes, experience):
    """It used to be 22% of whatever was left, so adding half an hour to the
    session added two and a half minutes of warm-up."""
    plan = generate_yoga_plan(profile(),
                              prefs(time_available_minutes=minutes,
                                    yoga_experience=experience),
                              weeks=[1])
    for day in plan["four_week_plan"][0]["days"]:
        held = sum(p["total_duration_seconds"] for p in day["session"]["warmup"])
        assert held <= slot_minutes * 60 * 1.15, (
            f"{experience} @ {minutes}min: warm-up ran {held / 60:.1f} min "
            f"against a {slot_minutes} min slot")


@pytest.mark.parametrize("minutes", [30, 45, 60])
@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_savasana_is_two_minutes_at_every_tier_and_level(minutes, experience):
    """It scaled 4/5/7 minutes with session length and up to 10 for an advanced
    practitioner. Two minutes flat is a user decision, so it is pinned here
    rather than left to `_CLOSING_BUDGET`, whose savasana column is now dead."""
    plan = generate_yoga_plan(profile(),
                              prefs(time_available_minutes=minutes,
                                    yoga_experience=experience),
                              weeks=[1])
    for day in plan["four_week_plan"][0]["days"]:
        assert _closing(day["session"])["total_duration_seconds"] == 120


def test_the_main_sequence_absorbs_the_added_length():
    """The point of the fixed slots: a longer session is a longer PRACTICE."""
    def main_seconds(minutes):
        plan = generate_yoga_plan(
            profile(), prefs(time_available_minutes=minutes,
                             yoga_experience="advanced"), weeks=[1])
        session = plan["four_week_plan"][0]["days"][0]["session"]
        return sum(p["total_duration_seconds"] for p in session["main_sequence"])

    # 45 against 60. What must hold is that the BOOKENDS do not grow: Surya
    # Namaskar, the warm-up and savasana are identical at both tiers, so the
    # added quarter hour goes to the practice and the prescribed breath (which
    # the user deliberately raised from 15 to 20 at the hour) and nowhere else.
    def blocks(minutes):
        plan = generate_yoga_plan(
            profile(), prefs(time_available_minutes=minutes,
                             yoga_experience="advanced"), weeks=[1])
        session = plan["four_week_plan"][0]["days"][0]["session"]
        closing = next(p for p in session["cooldown"] if p["final_relaxation"])
        return {
            "sns": session["surya_namaskar"]["duration_minutes"],
            "warmup": sum(p["total_duration_seconds"] for p in session["warmup"]),
            "savasana": closing["total_duration_seconds"],
        }

    short, long = blocks(45), blocks(60)
    assert short["sns"] == long["sns"]
    assert short["savasana"] == long["savasana"]
    assert abs(short["warmup"] - long["warmup"]) <= 30

    added_to_main = main_seconds(60) - main_seconds(45)
    # The main sequence takes the largest single share of the added time: 15
    # minutes added, 5 to pranayama, 1 to the cool-down, the rest to practice.
    assert added_to_main >= 8 * 60, (
        f"only {added_to_main / 60:.1f} of the added 15 minutes reached the "
        f"main sequence")


# ── The fixed slots must never widen a gate ──────────────────────────────────

def test_a_fixed_slot_does_not_serve_a_contraindicated_surya_namaskar():
    """A slot is a statement about length, never a reason to fill it. Each of
    these returned None before and must still, even though the session now has
    five minutes reserved and nothing else to put in them."""
    evening = generate_yoga_plan(
        profile(), prefs(time_of_day_preference="evening"), weeks=[1])
    pregnant = generate_yoga_plan(
        profile(pregnancy_or_nursing=True), prefs(), weeks=[1])
    for plan in (evening, pregnant):
        for day in plan["four_week_plan"][0]["days"]:
            assert day["session"]["surya_namaskar"] is None


def test_a_senior_is_not_given_four_rounds_to_fill_the_slot():
    """One chair-supported round is the prescription. Repeating it to reach five
    minutes would be the fixed slot overriding the age modification; the minutes
    it gives back go to asana instead."""
    plan = generate_yoga_plan(profile(age=72), prefs(time_available_minutes=60),
                              weeks=[1])
    for day in plan["four_week_plan"][0]["days"]:
        block = _sns(day["session"])
        if block:
            assert block["rounds"] == 1
            assert block["senior_modification"]


# ── Cool-down: unwinding work daily, long holds on the recovery day ──────────

def test_no_weekday_cooldown_holds_a_second_savasana():
    """The cool-down pool is two populations under one label: 22 poses of 20-90
    second unwinding work, and 8 prop-supported restorative holds of 2.5-7
    minutes. Drawing one of the latter put Salamba Paschimottanasana at four
    minutes directly in front of savasana — a session ending twice."""
    for experience in ("beginner", "intermediate", "advanced"):
        plan = generate_yoga_plan(
            profile(), prefs(time_available_minutes=60,
                             yoga_experience=experience), weeks=[1])
        for day in plan["four_week_plan"][0]["days"]:
            session = day["session"]
            if session["intensity"] == "restorative":
                continue
            for pose in session["cooldown"]:
                if pose["final_relaxation"]:
                    continue
                # Per-side, because a bilateral twist taken 80 seconds each way
                # is active work, not two and a half minutes of lying still —
                # which is the thing this rule exists to prevent.
                assert pose["duration_seconds"] < 150, (
                    f"{experience} {day['day_name']}: {pose['pose_name']} held "
                    f"{pose['duration_seconds']}s in an ordinary cool-down")


def test_the_recovery_day_may_still_hold_long():
    """The widening is the whole point of reserving them."""
    plan = generate_yoga_plan(
        profile(), prefs(time_available_minutes=60, yoga_experience="advanced"),
        weeks=[1])
    sunday = plan["four_week_plan"][0]["days"][6]["session"]
    assert sunday["intensity"] == "restorative"
    assert any(p["total_duration_seconds"] >= 150 and not p["final_relaxation"]
               for p in sunday["cooldown"])


def test_the_recovery_day_still_shares_the_weeks_cooldown_core():
    """The core is rebuilt on every day from the pool it is handed, so a pool
    that grows on day 7 would recompute a different core there and leave the
    recovery day sharing nothing with the week — the same leak that made the arc
    filter the core. Only the ACCENT widens."""
    plan = generate_yoga_plan(
        profile(), prefs(time_available_minutes=60, yoga_experience="advanced"),
        weeks=[1])
    days = [d["session"] for d in plan["four_week_plan"][0]["days"]]
    weekday = {p["pose_id"] for p in days[0]["cooldown"] if not p["final_relaxation"]}
    sunday = {p["pose_id"] for p in days[6]["cooldown"] if not p["final_relaxation"]}
    shared = weekday & sunday
    assert len(shared) >= min(len(weekday), len(sunday)) - 1, (
        f"the recovery day kept only {len(shared)} of the week's cool-down "
        f"poses ({sorted(weekday)} vs {sorted(sunday)})")


def test_counterposing_survives_the_narrowed_cooldown_pool():
    """Matsyasana is the only backbend in the cool-down pool and it is what
    neutralises Sarvangasana. Filtering the pool by hold length must not reach
    it."""
    plan = generate_yoga_plan(
        profile(), prefs(time_available_minutes=60, yoga_experience="advanced"),
        weeks=[1, 2, 3, 4])
    for session in sessions(plan):
        ordered = session["main_sequence"] + session["cooldown"]
        for i, pose in enumerate(ordered):
            if pose["category"] in _NEEDS_COUNTERPOSE:
                after = {p["category"] for p in ordered[i + 1:]}
                assert after & set(_COUNTERPOSE_CATEGORIES), (
                    f"{pose['pose_name']} is left unresolved")


@pytest.mark.parametrize("age,age_label", [(72, "senior"), (15, "youth")])
def test_no_forceful_kriya_reaches_either_end_of_the_age_range(age, age_label):
    """Contraindications, KB level and age are three independent axes, and the
    forceful set has to be listed against ALL of them.

    Bhastrika was excluded for youth only. A 70-year-old with chronic fatigue was
    prescribed it — while Kapalabhati, a less forceful practice, was correctly
    withheld from the same profile — because it sat one line below its siblings.
    """
    from services.yoga_plan_engine import _PROTOCOL_MAP

    forceful = {"Bellows Breath", "Skull Shining", "Fire Essence",
                "Breath Retention"}
    # The conditions whose protocols actively ask for a forceful practice are
    # the ones that would surface the gap.
    conditions = [c for c, p in _PROTOCOL_MAP.items()
                  if {"bellows_breath", "skull_shining", "fire_essence"}
                  & set(p.get("priority_pranayama_ids", []))]
    assert conditions, "no protocol prioritises a forceful kriya — test is inert"

    for condition in conditions:
        for experience in ("beginner", "intermediate", "advanced"):
            plan = generate_yoga_plan(
                profile(age=age, medical_history=[condition]),
                prefs(yoga_experience=experience, time_available_minutes=60),
                weeks=[1])
            for day in plan["four_week_plan"][0]["days"]:
                served = {t["technique_name"]
                          for t in day["session"]["pranayama_section"]}
                assert not (served & forceful), (
                    f"{age_label} with {condition} at {experience} was served "
                    f"{served & forceful}")
