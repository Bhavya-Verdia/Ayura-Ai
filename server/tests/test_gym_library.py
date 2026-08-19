"""Invariants of the curated gym library.

The previous library was imported, so the only things worth asserting about it
were the ones the importer might have broken. This one is authored, and the
fields it carries — `role`, `mechanic`, `family`, `load_class`, `impact`,
`skill_floor`, `movement_pattern` — are exactly the things the engine used to
guess from an exercise's name. These tests guard the guesses staying gone.
"""
import json
import subprocess
import sys
from pathlib import Path

import pytest

SERVER = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(SERVER / "scripts"))

from gym_library import schema  # noqa: E402
from services.gym_plan_engine import (  # noqa: E402
    _LIFT_BW, _LOAD_CLASS_ALIAS, _WORKING_ROLES, gym_exercises)

WORKING = [e for e in gym_exercises if e["role"] in _WORKING_ROLES]


def test_every_entry_satisfies_the_schema():
    """The builder refuses to write an entry that does not; this catches a file
    edited by hand afterwards."""
    errors = []
    for e in gym_exercises:
        errors.extend(schema.validate(e))
    assert not errors, errors[:10]


def test_the_library_is_what_the_spec_builds():
    """Generated, so it cannot drift from the spec that documents the judgment
    in it. A hand-edit to the JSON is a change nobody reviewed."""
    r = subprocess.run([sys.executable, "scripts/build_gym_library.py", "--check"],
                       cwd=SERVER, capture_output=True, text=True)
    assert r.returncode == 0, r.stdout + r.stderr


def test_a_stretch_can_never_hold_a_working_slot():
    """The rule the whole rewrite exists to enforce. 46% of generated training
    days used to prescribe a stretch as a set of eight, because a stretch whose
    name did not contain the word "stretch" was filed as `strength`."""
    for e in gym_exercises:
        if e["category"] == "stretching":
            assert e["role"] not in _WORKING_ROLES, e["name"]
        # `mobility` is a stretch and can never carry a weight. `warmup` can —
        # a rotator-cuff drill is done with three kilos, and pricing it is the
        # whole reason `external_rotation` is in the load model.
        if e["role"] == "mobility":
            assert not e["load_class"], f"{e['name']} is a stretch with a load"


def test_no_isolation_movement_can_open_a_session():
    for e in gym_exercises:
        if e["role"] == "main":
            assert e["mechanic"] == "compound", e["name"]


def test_every_load_class_resolves_to_a_calibrated_number():
    """A `load_class` the engine cannot price falls through to the muscle-group
    fallback, which is the bug the field was added to remove."""
    for e in gym_exercises:
        lc = e["load_class"]
        if not lc:
            continue
        assert _LOAD_CLASS_ALIAS.get(lc, lc) in _LIFT_BW, f"{e['name']}: {lc}"


def test_isolation_work_is_priced_far_below_the_lift_it_supports():
    """`External Rotation` was quoted at 17-22.5 kg per hand because it trains
    the shoulder and a shoulder press is what shoulders were priced with."""
    from services.gym_plan_engine import _get_weight_range

    by_name = {e["name"]: e for e in gym_exercises}

    def kg(name):
        text = _get_weight_range(by_name[name], "intermediate", "male", 80)
        return float(text.split("–")[0])

    assert kg("External Rotation") <= 8, "a cuff drill is not a shoulder press"
    assert kg("Side Lateral Raise") <= 12
    assert kg("External Rotation") < kg("Barbell Shoulder Press")
    assert kg("Barbell Curl") < kg("Barbell Bench Press")


def test_every_contraindication_token_is_one_the_engine_can_act_on():
    used = {t for e in gym_exercises for t in e["contraindications"]}
    assert used <= schema.CONTRA_VOCAB, sorted(used - schema.CONTRA_VOCAB)


def test_every_movement_has_an_authored_clinical_judgment_with_a_reason():
    """Contraindications, pregnancy and dosha were derived by rule. Writing them
    per movement changed the answer on 89 of 173 — the rule had no concept of
    body position, so every supine press came out pregnancy-safe, and it withheld
    `Wall Slide`, a scapular rehab drill, from anyone with a shoulder problem.

    The rationale is not decoration: it is what lets a reviewer confirm a stated
    mechanism instead of reverse-engineering intent from a list of tags."""
    for e in gym_exercises:
        assert e["clinical_basis"] == "authored", e["name"]
        assert len(e["clinical_rationale"]) > 20, e["name"]


def test_no_supine_movement_is_offered_in_pregnancy():
    """Lying flat is ordinarily avoided after the first trimester. The derived
    rule modelled impact, skill and load, and had no idea which way up you were."""
    supine = {"Barbell Bench Press", "Dumbbell Bench Press", "Machine Bench Press",
              "Dumbbell Flyes", "Glute Bridge", "Crunches", "Lying Leg Raise",
              "Barbell Floor Press", "Dumbbell Floor Press", "Dead Bug"}
    by_name = {e["name"]: e for e in gym_exercises}
    for name in supine:
        assert not by_name[name]["pregnancy_safe"], name


def test_the_movements_that_treat_a_restriction_are_not_withheld_by_it():
    """A rule keyed on movement pattern removed the rehab work from the people it
    is for: `Wall Slide` and `External Rotation` are what a cranky shoulder is
    given, and the floor press is the press it keeps."""
    by_name = {e["name"]: e for e in gym_exercises}
    for name in ("Wall Slide", "External Rotation", "Face Pull", "Band Pull Apart"):
        tags = set(by_name[name]["contraindications"])
        assert not tags & {"shoulder_injury", "rotator_cuff"}, (name, tags)
    for name in ("Barbell Floor Press", "Dumbbell Floor Press"):
        tags = set(by_name[name]["contraindications"])
        assert not tags & {"shoulder_injury", "rotator_cuff"}, (name, tags)


@pytest.mark.parametrize("profile,label", [
    ({"age": 68, "fitness_level": "advanced"}, "senior"),
    ({"age": 16, "fitness_level": "advanced"}, "youth"),
    ({"age": 30, "fitness_level": "beginner"}, "beginner"),
    ({"age": 30, "fitness_level": "advanced", "bmi_category": "obese"}, "obese"),
])
def test_landing_impact_never_reaches_anyone_it_is_withheld_from(profile, label):
    """Four separate gates withhold jump training, and each was written against
    `category == "plyometrics"`. The curated library records landing force in its
    own field and files jump work as conditioning, so that test silently stopped
    matching — and the gates failed open one at a time as they were found. This
    covers all four at once, against behaviour rather than implementation."""
    from services.gym_plan_engine import filter_exercises

    base = {"id": "t", "gender": "male", "dominant_dosha": "vata", "weight_kg": 80,
            "height": 175, "bmi_category": "normal", "medical_history": []}
    pool = filter_exercises({**base, **profile},
                            {"available_equipment": ["full_gym"],
                             "gym_goal": "fat_loss"}, gym_exercises)
    offered = [e["name"] for e in pool if e["impact"] == "high"]
    assert not offered, f"{label} was offered {offered[:3]}"


def test_a_shoulder_restriction_is_honoured_under_either_name():
    """`rotator_cuff` and `shoulder_injury` are two names for one restriction and
    the engine treats them as separate tokens, so a rule emitting one and not the
    other leaves half the people who declared it unprotected."""
    for e in gym_exercises:
        tags = set(e["contraindications"])
        # Overhead work under a bar or bodyweight carries both names. A neutral
        # close grip or a band carries only `shoulder_injury`, deliberately —
        # see the rationale on each of those entries.
        if "rotator_cuff" in tags:
            assert "shoulder_injury" in tags, e["name"]


@pytest.mark.parametrize("bucket", ["chest", "back", "shoulders", "legs", "core",
                                    "biceps", "triceps"])
def test_a_home_user_can_train_every_region(bucket):
    """The imported library held 141 bodyweight entries, 42 of them abdominal,
    against five for the lats and three for the mid back — so a home user's back
    day was three prone raises and the same wall drill every session."""
    home = [e for e in WORKING
            if e["equipment"] in ("bodyweight", "bands")
            and e["bucket"] == bucket and e["skill_floor"] == "beginner"]
    assert len(home) >= 2, f"{bucket}: {[e['name'] for e in home]}"


def test_an_unloaded_movement_says_how_to_progress_out_of_it():
    """A barbell row progresses by adding 2.5 kg and the quoted range says so. A
    push-up progresses by becoming a different push-up, and if the entry does not
    name which one, a home user has no route forward at all."""
    for e in gym_exercises:
        if e["role"] in _WORKING_ROLES and e["equipment"] in ("bodyweight", "bands"):
            assert any(e["progression"].values()), e["name"]


def test_instructions_are_written_for_this_audience():
    """Reused upstream prose is written for an American gym. Every load in this
    app is quoted in kilograms, and one entry spent an instruction step on how
    many calories a 150 lb person burns."""
    import re
    imperial = re.compile(r"\b\d+\s*(?:-\s*\d+\s*)?"
                          r"(?:inch|inches|feet|foot|lb|lbs|pound|pounds)\b", re.I)
    for e in gym_exercises:
        text = " ".join(e["instructions"])
        assert not imperial.search(text), f"{e['name']}: {imperial.search(text).group(0)}"
        if e["role"] != "mobility":
            assert len(e["instructions"]) >= 3, f"{e['name']}: {len(e['instructions'])} steps"


def test_dosha_is_a_preference_that_actually_discriminates():
    """The first correction over-shot: everything not high-impact came out
    `good/good/good`, so the field said the same thing about 83% of the library.
    It should also never say `avoid` — the pool cut treats that gap as wider than
    the pool is deep, which is how a mislabel became a ban."""
    import collections
    values = collections.Counter(
        tuple(sorted(e["dosha_suitability"].items())) for e in gym_exercises)
    largest = max(values.values())
    assert largest < len(gym_exercises) * 0.6, (
        f"{largest}/{len(gym_exercises)} movements share one dosha value")
    for e in gym_exercises:
        assert "avoid" not in e["dosha_suitability"].values(), e["name"]


def test_every_region_a_gym_user_trains_has_a_main_lift():
    for bucket in ("chest", "back", "shoulders", "legs"):
        mains = [e for e in gym_exercises
                 if e["bucket"] == bucket and e["role"] == "main"
                 and e["equipment"] not in ("bodyweight", "bands")]
        assert len(mains) >= 3, bucket


def test_a_movement_that_is_measured_in_time_is_not_prescribed_in_reps():
    """A carry is not "5 sets of 8-10" — of what, it did not say."""
    for e in gym_exercises:
        if e["rep_style"] in ("time", "distance", "isometric"):
            reps = str(e["sets_reps"]["intermediate"]["reps"])
            assert not reps.replace("-", "").isdigit(), f"{e['name']}: {reps}"


def test_the_canonical_lift_of_a_pattern_is_stated_not_inferred():
    """Name plainness ranked "T-Bar Row" above "Bent Over Barbell Row"."""
    canonical = {e["name"] for e in gym_exercises if e.get("canonical")}
    for expected in ("Barbell Squat", "Barbell Deadlift", "Barbell Bench Press",
                     "Bent Over Barbell Row", "Barbell Shoulder Press"):
        assert expected in canonical, expected


def test_no_instruction_text_comes_from_the_dataset():
    """Upstream supplies muscle lists and nothing else.

    120 movements used its prose and 89 carried a defect: `Dumbbell Romanian
    Deadlift` opened "put a barbell in front of you on the ground", two entries
    instructed the reader to hold their breath under load — the mechanism
    `hypertension` is tagged for — and 66 said "This will be your starting
    position". Every step is now written in `prose.py`."""
    src = json.loads((SERVER / "data" / "sources" / "free_exercise_db.json").read_text())
    upstream = {e["name"]: e.get("instructions") or [] for e in src}
    for e in gym_exercises:
        assert e["prose"] == "authored", e["name"]
        theirs = upstream.get(e["anatomy_source"]) or []
        shared = set(e["instructions"]) & set(theirs)
        assert not shared, f"{e['name']} reuses an upstream step: {list(shared)[:1]}"


def test_the_prose_house_style_holds():
    """One voice across the library. These are the tells of the imported text."""
    import re
    banned = {
        "this will be your starting position": "dataset boilerplate",
        "repeat for the recommended": "the app prints sets and reps above the steps",
        "repeat for the prescribed": "the app prints sets and reps above the steps",
        "tip:": "inline artifact",
        "hold your breath": "teaches the strain the safety model gates for",
        "holding your breath": "teaches the strain the safety model gates for",
    }
    for e in gym_exercises:
        text = " ".join(e["instructions"]).lower()
        for phrase, why in banned.items():
            assert phrase not in text, f"{e['name']}: {phrase!r} — {why}"
        assert 3 <= len(e["instructions"]) <= 8 or e["role"] == "mobility", e["name"]


def test_the_keyword_contraindication_filler_refuses_to_run():
    """It matched keywords against names: `("bent over", ...)` tagged everything
    with those words `herniated_disc`, including the chest-supported rows whose
    whole point is that the bench takes the spine out of it. Running it now would
    also erase the authored/derived distinction the packet depends on."""
    r = subprocess.run([sys.executable, "scripts/fill_gym_contraindications.py"],
                       cwd=SERVER, capture_output=True, text=True)
    assert r.returncode != 0
    assert "build_gym_library" in r.stdout


def test_the_retired_importer_refuses_to_run():
    """Running it would silently restore 176 rows that contradict their own
    source, and re-derive `pitta: avoid` onto every barbell exercise."""
    r = subprocess.run([sys.executable, "scripts/seed_gym_exercises.py"],
                       cwd=SERVER, capture_output=True, text=True)
    assert r.returncode != 0
    assert "build_gym_library" in r.stdout
