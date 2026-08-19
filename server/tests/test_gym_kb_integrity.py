"""Structural invariants of the gym exercise knowledge base.

The engine is safe against duplicate names because it works by ID. Everything
else is not: a name lookup gets whichever row it finds first, and the two
duplicates this file was written for disagreed about whether an exercise was
safe in pregnancy. An audit of mine returned 560 phantom safety violations
before I noticed, which is the shape of the problem — a KB defect that makes the
tools you check the KB with lie to you.
"""
import collections

import pytest

from services.gym_plan_engine import gym_exercises

_REQUIRED = {
    "id": str, "name": str, "category": str, "equipment": str, "level": str,
    "primary_muscles": list, "secondary_muscles": list, "instructions": list,
    "sets_reps": dict, "dosha_suitability": dict, "goal_suitability": dict,
    "contraindications": list, "pregnancy_safe": bool,
}
_CATEGORIES = {"strength", "cardio", "stretching", "plyometrics"}
_LEVELS = {"beginner", "intermediate", "advanced"}
_DOSHAS = {"vata", "pitta", "kapha"}
_VERDICTS = {"good", "moderate", "avoid"}


def test_no_two_exercises_share_a_name():
    """`Elliptical Trainer` existed twice — once from the bulk import as a
    `strength` exercise prescribed in sets of 12-15 reps, once hand-authored as
    timed conditioning — and the two disagreed about pregnancy safety."""
    dupes = {n: c for n, c in collections.Counter(e["name"] for e in gym_exercises).items() if c > 1}
    assert not dupes, dupes


def test_no_two_exercises_share_an_id():
    ids = {i: c for i, c in collections.Counter(e["id"] for e in gym_exercises).items() if c > 1}
    assert not ids, ids


@pytest.mark.parametrize("field,kind", sorted(_REQUIRED.items()))
def test_every_exercise_carries_the_field(field, kind):
    missing = [e["id"] for e in gym_exercises
               if field not in e or not isinstance(e[field], kind)]
    assert not missing, f"{field}: {missing[:5]} ({len(missing)} rows)"


def test_categories_and_levels_use_the_vocabulary_the_engine_reads():
    """A value outside these sets does not raise — it silently fails every gate
    that checks for membership, which is how thirteen foam-rolling entries spent
    their lives filed as strength training."""
    assert {e["category"] for e in gym_exercises} <= _CATEGORIES
    assert {e["level"] for e in gym_exercises} <= _LEVELS


def test_every_dosha_verdict_is_one_the_scorer_understands():
    for e in gym_exercises:
        assert set(e["dosha_suitability"]) == _DOSHAS, e["id"]
        assert set(e["dosha_suitability"].values()) <= _VERDICTS, e["id"]


def test_no_exercise_is_unusable():
    """An entry with no instructions cannot be performed, and one suitable for no
    goal can never be selected — both are rows that cost pool depth and give
    nothing back."""
    for e in gym_exercises:
        assert e["instructions"], e["id"]
        assert any(e["goal_suitability"].values()), e["id"]


def test_pregnancy_is_not_described_twice_and_differently():
    """The flag and the contraindication token are two ways of saying the same
    thing, and ten rows used to say both and disagree."""
    conflicted = [e["id"] for e in gym_exercises
                  if e["pregnancy_safe"] and "pregnancy" in e["contraindications"]]
    assert not conflicted, conflicted


def test_contraindication_tokens_are_all_ones_the_engine_can_act_on():
    """A tag the filter has no path to is a safety note nobody reads."""
    from services.gym_condition_fallback import GYM_CONTRA_VOCAB
    from services.gym_plan_engine import _CONDITION_TO_EXERCISE_CONTRA

    reachable = set(GYM_CONTRA_VOCAB) | {"pregnancy"}
    for mapped in _CONDITION_TO_EXERCISE_CONTRA.values():
        reachable |= set(mapped)
    used = {tag for e in gym_exercises for tag in e["contraindications"]}
    assert used <= reachable, f"unreachable tags: {sorted(used - reachable)}"


def test_every_bmi_category_the_profile_can_write_is_understood():
    """Two vocabularies reach `bmi_category` and they are not the same one.

    `BMICalculator` defines seven bands; `routes/profile.py` computes BMI inline
    on save and writes four, and it is the route's value that lands on the user
    document. The engine read only the calculator's names, so a live user at BMI
    32.8 came back `obese`, fell through to `normal`, and was prescribed the jump
    training the map exists to keep away from them.
    """
    from engine.bmi_calculator import BMICalculator
    from services.gym_plan_engine import _BMI_GROUPS, _bmi_group

    # Everything the calculator can produce.
    for category in BMICalculator.BMI_CATEGORIES:
        assert category in _BMI_GROUPS, category

    # And everything the profile route can produce, at the BMI that produces it.
    route_vocabulary = {
        16.0: "underweight", 22.0: "normal", 27.0: "overweight", 33.0: "obese",
    }
    for bmi, category in route_vocabulary.items():
        assert category in _BMI_GROUPS, f"BMI {bmi} → {category!r} is not understood"
    assert _bmi_group("obese") == "obese"
    assert _bmi_group("obese_class3") == "obese"
    assert _bmi_group(None) == "normal"


def test_the_review_packet_regenerates_and_matches_the_library():
    """The packet is only useful if it describes the KB as it is now. It is
    generated rather than written, so it cannot drift — this asserts the generator
    still runs against the current library and agrees with it on the numbers."""
    from scripts.build_gym_review_packet import _coverage_rows, _exercise_rows

    exercises = _exercise_rows()
    assert len(exercises) == len(gym_exercises)

    coverage = _coverage_rows()
    assert coverage, "no mechanism groups — the grouping has stopped working"
    for row in coverage:
        assert 0 < row["tagged"] <= row["group_size"]
        assert row["contraindication"]
    # The flagged rows are the point of the exercise: a rule that fired on part of
    # a mechanism group and not the rest. If none are flagged, either the library
    # became consistent or the flagging broke, and the second is likelier.
    assert [r for r in coverage if r["inconsistent"]]


# What the library held when clinical review was last counted. The curated
# rewrite reset this to 0, and that is a real cost stated plainly rather than
# papered over: the 18 rows that carried `contraindications_reviewed` were
# `Brachialis-Smr`, `Latissimus Dorsi-Smr`, `Rhomboids-Smr`, `Gironda Sternum
# Chins`, `London Bridges` and a dozen more like them — foam-rolling entries and
# specialty variants that a curated library correctly does not contain. None of
# them survived curation, so none of the review carried across.
#
# The surface being reviewed changed shape at the same time: 884 rule-derived
# tags over 902 rows became 173 authored movements. Raise this baseline as rows
# come back reviewed; never lower it.
_REVIEWED_BASELINE = 0


def test_the_reviewed_count_only_goes_up():
    """`contraindications_reviewed` is what the packet exists to raise. A change
    that drops rows out of it is a regression, not an edit."""
    reviewed = sum(1 for e in gym_exercises if e.get("contraindications_reviewed"))
    assert reviewed >= _REVIEWED_BASELINE, (
        f"clinically reviewed rows fell to {reviewed}")
