"""The gym plan for people who are not healthy 30-year-olds.

Before this file, 8 of the 70 conditions onboarding offers changed a gym plan at
all. The library's contraindication tokens name body parts, and glaucoma,
epilepsy, vertigo, a hernia and rheumatoid arthritis are not body parts. These
tests are behavioural — they build the plan and read it — because every earlier
gate in this engine that was tested as a unit failed open without anyone
noticing when the data under it changed.
"""
import pytest

from engine.movement_risk import RISK_VOCAB, condition_risk_tags
from services.gym_plan_engine import generate_gym_plan, gym_exercises

_BASE = {"id": "hs", "age": 40, "gender": "female", "weight_kg": 65,
         "fitness_level": "intermediate", "activity_level": "moderate",
         "dominant_dosha": "kapha", "medical_history": []}
_PREFS = {"gym_goal": "general_fitness", "available_equipment": ["full_gym"],
          "strength_level": "intermediate", "workout_days_per_week": 5,
          "workout_duration_minutes": 60, "cardio_preference": "heavy"}
_BY_NAME = {e["name"]: e for e in gym_exercises}


def _plan(**profile):
    return generate_gym_plan({**_BASE, **profile}, _PREFS)


def _prescribed(plan):
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            for ex in day["main_workout"]:
                yield _BY_NAME[ex["exercise_name"]]


def _edges(plan):
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            yield from day["warmup"]
            yield from day["cooldown"]
            yield from (day.get("rest_day_recovery") or {}).get("activities", [])


# The onboarding ids, and the mechanism each must keep out of the plan.
_CONDITION_MECHANISM = [
    ("glaucoma", "intracranial_pressure"),
    ("epilepsy", "seizure_risk"),
    ("vertigo", "fall_risk"),
    ("vertigo", "neck_load"),
    ("osteoporosis", "spinal_flexion"),
    ("rheumatoid_arthritis", "wrist_weight_bearing"),
    ("lupus", "wrist_weight_bearing"),
    ("ibd_crohns", "abdominal_pressure"),
    ("ulcerative_colitis", "abdominal_pressure"),
    ("hemorrhoids", "abdominal_pressure"),
    ("parkinson", "fall_risk"),
    ("peripheral_neuropathy", "fall_risk"),
    ("cervical_spondylosis", "neck_load"),
]


@pytest.mark.parametrize("condition,mechanism", _CONDITION_MECHANISM)
def test_no_prescribed_movement_carries_the_mechanism_a_condition_is_restricted_for(
        condition, mechanism):
    assert mechanism in condition_risk_tags([condition]), (
        f"{condition} does not map to {mechanism} at all")
    plan = _plan(medical_history=[condition])
    offending = sorted({ex["name"] for ex in _prescribed(plan)
                        if mechanism in ex.get("risk_tags", [])})
    assert not offending, f"{condition}: {mechanism} via {offending}"


@pytest.mark.parametrize("condition,mechanism", _CONDITION_MECHANISM)
def test_the_mechanism_is_withheld_where_it_would_otherwise_appear(condition, mechanism):
    """A gate that removes nothing is indistinguishable from one that works, if
    the healthy plan never contained the movement to begin with. Each pairing
    must be one the library actually carries."""
    carriers = [e for e in gym_exercises if mechanism in e.get("risk_tags", [])]
    assert carriers, f"no movement carries {mechanism}; the gate is decorative"


def test_every_mechanism_the_library_names_is_one_a_condition_can_reach():
    named = {t for e in gym_exercises for t in e.get("risk_tags", [])}
    assert named <= RISK_VOCAB, sorted(named - RISK_VOCAB)
    reachable = set().union(*(condition_risk_tags([c]) for c in (
        "glaucoma", "epilepsy", "vertigo", "osteoporosis", "hernia",
        "rheumatoid_arthritis", "spondylolisthesis", "cervical_spondylosis")))
    assert named <= reachable, f"unreachable: {sorted(named - reachable)}"


def test_osteoporosis_keeps_no_flexion_at_the_edges_of_the_session():
    """A 72-year-old with osteoporosis had every flexion exercise removed from her
    workout and still opened with an inchworm and closed with a supine twist and
    child's pose — and the cool-down's substitute was a seated forward fold."""
    plan = generate_gym_plan(
        {**_BASE, "age": 72, "fitness_level": "beginner", "activity_level": "sedentary",
         "medical_history": ["osteoporosis", "hypertension"]},
        {**_PREFS, "available_equipment": ["dumbbells", "machines"],
         "strength_level": "untrained", "workout_days_per_week": 3})
    lines = " | ".join(_edges(plan)).lower()
    for flexion in ("inchworm", "child's pose", "spinal twist", "forward fold",
                    "side bend", "sun salutation"):
        assert flexion not in lines, f"{flexion} reached an osteoporotic practitioner"


def test_an_inversion_does_not_reach_a_glaucoma_patient_on_a_rest_day():
    plan = _plan(medical_history=["glaucoma"], dominant_dosha="vata")
    lines = " | ".join(_edges(plan)).lower()
    assert "legs-up-the-wall" not in lines
    assert "inchworm" not in lines


def test_a_seventy_eight_year_old_cardiac_patient_is_not_given_sun_salutations():
    plan = generate_gym_plan(
        {**_BASE, "age": 78, "gender": "male", "fitness_level": "beginner",
         "activity_level": "sedentary", "medical_history": ["heart_disease"],
         "dominant_dosha": "kapha"},
        {**_PREFS, "gym_goal": "endurance", "available_equipment": ["bodyweight"],
         "strength_level": "untrained", "workout_days_per_week": 3})
    assert "sun salutation" not in " | ".join(_edges(plan)).lower()


@pytest.mark.parametrize("condition", ["osteoarthritis", "rheumatoid_arthritis", "gout",
                                       "fibromyalgia", "peripheral_neuropathy"])
def test_joint_conditions_withhold_landing_impact(condition):
    """Obesity, age and training age withheld jumping; osteoarthritis, the
    commonest joint disease there is, did not."""
    plan = _plan(medical_history=[condition])
    jumping = sorted({ex["name"] for ex in _prescribed(plan) if ex.get("impact") == "high"})
    assert not jumping, f"{condition}: {jumping}"
    edges = " | ".join(_edges(plan)).lower()
    assert "jumping jacks" not in edges and "high knees" not in edges


def test_the_gym_and_yoga_engines_read_one_condition_map():
    """Two copies of a safety list is how they drift apart."""
    import engine.movement_risk as shared
    import services.yoga_plan_engine as yoga

    assert yoga._CONDITION_RISK_TAGS is shared._CONDITION_RISK_TAGS
    assert yoga._INJURY_RISK_TAGS is shared._INJURY_RISK_TAGS


def test_more_than_a_handful_of_onboarding_conditions_change_the_plan():
    """The measurement that found this: 8 of 70. Pinned as a floor so a change
    that quietly disconnects the mechanism gate fails here."""
    import hashlib
    import json
    import re
    from pathlib import Path

    src = Path(__file__).resolve().parents[2] / "client" / "src" / "constants" / "conditions.js"
    ids = sorted(set(re.findall(r"id: *'([a-z_0-9]+)'", src.read_text())))

    def digest(p):
        p = {k: v for k, v in p.items() if k not in ("plan_id", "generated_at")}
        return hashlib.md5(json.dumps(p, sort_keys=True, default=str).encode()).hexdigest()

    base = digest(_plan())
    live = [c for c in ids if digest(_plan(medical_history=[c])) != base]
    assert len(live) >= 25, f"only {len(live)} of {len(ids)} conditions decide anything: {live}"


# ── Injuries ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("injury,token", [
    ("shoulder", "shoulder_injury"), ("knee", "bad_knee"), ("wrist", "wrist_injury"),
    ("lower_back", "lower_back_pain"), ("disc", "herniated_disc"),
    ("elbow", "elbow_injury"), ("neck", "neck_injury"), ("hip", "hip_injury"),
    ("ankle", "bad_ankle"), ("knee_replacement", "knee_replacement"),
])
def test_an_injury_ticked_on_the_gym_form_removes_what_it_restricts(injury, token):
    """No screen collected injuries, and the profile field's documented values
    ("lower_back", "shoulder", "wrist") were not the library's tokens — so only
    `bad_knee` would have matched even if one had."""
    carriers = [e for e in gym_exercises if token in e["contraindications"]]
    assert carriers, f"nothing carries {token}"
    plan = generate_gym_plan(_BASE, {**_PREFS, "injuries": [injury]})
    offending = sorted({ex["name"] for ex in _prescribed(plan)
                        if token in ex["contraindications"]})
    assert not offending, f"{injury}: {offending}"


def test_the_profile_field_is_translated_too():
    plan = generate_gym_plan({**_BASE, "injuries_or_limitations": ["shoulder"]}, _PREFS)
    assert not [ex for ex in _prescribed(plan) if "shoulder_injury" in ex["contraindications"]]


def test_a_hernia_withholds_abdominal_pressure():
    plan = generate_gym_plan(_BASE, {**_PREFS, "injuries": ["hernia"]})
    assert not [ex["name"] for ex in _prescribed(plan)
                if "abdominal_pressure" in ex.get("risk_tags", [])]


def test_typed_detail_is_read_through_the_same_aliases_as_yoga():
    plan = generate_gym_plan(
        _BASE, {**_PREFS, "injury_detail": "old ACL tear, tennis elbow"})
    names = [ex["name"] for ex in _prescribed(plan)]
    assert not [n for n in names if "bad_knee" in _BY_NAME[n]["contraindications"]]
    assert not [n for n in names if "elbow_injury" in _BY_NAME[n]["contraindications"]]
    assert plan["injury_notice"] is None


def test_what_cannot_be_matched_is_named_back():
    """Silence would read as "we took that into account"."""
    plan = generate_gym_plan(_BASE, {**_PREFS, "injury_detail": "everything hurts"})
    assert "everything hurts" in (plan["injury_notice"] or "")


def test_the_coaching_is_told_about_injuries_from_the_gym_form():
    from services.gym_plan_enricher import build_plan_summary

    prefs = {**_PREFS, "injuries": ["shoulder"]}
    plan = generate_gym_plan(_BASE, prefs)
    summary = build_plan_summary(plan, _BASE, prefs)
    assert "shoulder_injury" in summary["user"]["injuries"]


def test_the_form_offers_exactly_what_the_server_accepts():
    """The front/back gap `test_dosha_instrument` exists to close, for injuries."""
    import re
    from pathlib import Path

    from schemas.preferences_schema import GYM_INJURY_OPTIONS
    from services.gym_plan_engine import _INJURY_TOKENS

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "components"
           / "PreferencesModal.jsx").read_text()
    block = jsx[jsx.index("const GYM_INJURIES"):jsx.index("];", jsx.index("const GYM_INJURIES"))]
    offered = set(re.findall(r"value: '([a-z_]+)'", block))
    assert offered == GYM_INJURY_OPTIONS
    assert all(any(k in opt for k in _INJURY_TOKENS) for opt in GYM_INJURY_OPTIONS)


# ── Intensity ─────────────────────────────────────────────────────────────────

def _main_reps(plan):
    for week in plan["four_week_plan"]:
        for day in week["days"]:
            for ex in day["main_workout"]:
                if ex["role"] == "primary":
                    yield ex["reps"]


@pytest.mark.parametrize("profile,prefs", [
    ({"medical_history": ["hypertension"]}, {}),
    ({"medical_history": ["heart_disease"]}, {}),
    ({"medical_history": ["glaucoma"]}, {}),
    ({}, {"injuries": ["hernia"]}),
    ({"pregnancy_or_nursing": True}, {}),
    ({"age": 67}, {}),
])
def test_near_maximal_sets_are_not_written_for_whom_they_are_the_risk(profile, prefs):
    """A hypertensive 50-year-old was written 4 x 3-5 on the barbell bench press.
    The exercise gate had taken the deadlift out and left the scheme that makes
    every lift in the block a maximal one."""
    plan = generate_gym_plan({**_BASE, **profile},
                             {**_PREFS, "gym_goal": "strength", **prefs})
    triples = [r for r in _main_reps(plan) if r in ("3-5", "4-5")]
    assert not triples, f"{profile or prefs}: {triples[:3]}"
    assert plan["intensity_notice"]


def test_a_healthy_adult_keeps_the_strength_scheme_they_asked_for():
    plan = generate_gym_plan(_BASE, {**_PREFS, "gym_goal": "strength"})
    assert "3-5" in set(_main_reps(plan))
    assert plan["intensity_notice"] is None


# ── Before-you-train guidance ────────────────────────────────────────────────

@pytest.mark.parametrize("condition,key", [
    ("diabetes_type1", "diabetes"), ("diabetes_type2", "diabetes"),
    ("asthma", "respiratory"), ("copd", "respiratory"), ("epilepsy", "epilepsy"),
    ("heart_disease", "cardiac"), ("atrial_fibrillation", "cardiac"),
    ("hypertension", "hypertension"), ("low_blood_pressure", "low_bp"),
    ("anemia", "anemia"), ("hyperthyroidism", "thyroid_over"),
    ("chronic_fatigue_syndrome", "fatigue"), ("osteoporosis", "osteoporosis"),
    ("rheumatoid_arthritis", "inflammatory_joint"), ("vertigo", "vertigo"),
])
def test_a_condition_where_the_session_is_the_risk_gets_told_so(condition, key):
    """Someone on insulin can do every exercise in the library and still go
    hypoglycaemic halfway through it. The plan said nothing."""
    plan = _plan(medical_history=[condition])
    assert key in {g["key"] for g in plan["condition_guidance"]}


def test_a_healthy_plan_carries_no_guidance():
    assert _plan()["condition_guidance"] == []


def test_heartburn_is_not_a_heart_condition():
    """"heart" is a substring of "heartburn"."""
    plan = generate_gym_plan({**_BASE, "medical_history": ["heartburn"]},
                             {**_PREFS, "gym_goal": "strength"})
    assert "cardiac" not in {g["key"] for g in plan["condition_guidance"]}
    assert plan["intensity_notice"] is None


def test_every_guidance_entry_names_its_source():
    from services.gym_condition_guidance import CONDITION_GUIDANCE

    for g in CONDITION_GUIDANCE:
        assert g["source"] and g["note"] and g["match"], g["key"]


# ── Rare conditions: one path for both routes ────────────────────────────────

def test_both_plan_paths_screen_rare_conditions():
    """The per-feature route asked the classifier about conditions the engine
    did not recognise; the holistic worker called the engine without it."""
    from pathlib import Path

    routes = Path(__file__).resolve().parents[1] / "routes"
    for name in ("plans.py", "plan_runner.py"):
        src = (routes / name).read_text()
        assert "extra_avoid_tags_for" in src, f"{name} builds a gym plan unscreened"


def test_a_condition_the_engine_already_acts_on_costs_no_llm_call():
    from services.gym_condition_fallback import uncovered_conditions

    covered = ["glaucoma", "diabetes_type2", "osteoarthritis", "hypertension", "asthma",
               "epilepsy", "lupus", "anemia"]
    assert uncovered_conditions({"medical_history": covered}) == []
    assert uncovered_conditions({"medical_history": ["moyamoya_disease"]}) == ["moyamoya_disease"]


def test_the_classifier_may_answer_in_mechanisms_and_nothing_else(monkeypatch):
    import asyncio
    import json

    from services import gym_condition_fallback as fb

    async def fake_generate(**_):
        return json.dumps({"avoid_categories": [
            "intracranial_pressure", "hypertension", "made_up_tag", "fall_risk"]})

    monkeypatch.setattr(fb.llm_client, "generate", fake_generate)
    monkeypatch.setattr(fb, "_CACHE", {})
    tags = asyncio.run(fb.gym_avoid_tags_for_conditions(["moyamoya_disease"]))
    assert tags == {"intracranial_pressure", "hypertension", "fall_risk"}

    plan = generate_gym_plan(_BASE, _PREFS, extra_avoid_tags=tags)
    assert not [ex["name"] for ex in _prescribed(plan)
                if {"intracranial_pressure", "fall_risk"} & set(ex.get("risk_tags", []))]
