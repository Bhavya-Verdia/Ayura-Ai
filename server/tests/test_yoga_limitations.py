"""Yoga preferences that were collected and decided nothing.

A probe across six profiles found five of yoga's ten preference fields inert — the
user answers a question, the answer is stored, and no plan differs for it. The one
that matters most is `physical_limitations_detail`: a free-text box where a user
describes an injury in their own words, which no filter read.
"""
import pytest

import schemas.preferences_schema as S
from services.yoga_plan_engine import generate_yoga_plan, unmatched_limitations


def _profile(**over):
    base = dict(
        id="t", age=32, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
        fitness_level="intermediate", medical_history=[], injuries_or_limitations=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = S.YogaPreferences().model_dump()
    base.update(over)
    return base


def _pose_names(plan):
    session = plan["weekly_schedule"][0]["session"]
    return [
        x.get("sanskrit_name") or x.get("id")
        for block in ("warmup", "main_sequence", "cooldown")
        for x in (session.get(block) or [])
    ]


@pytest.mark.parametrize("detail,body_part", [
    ("frozen shoulder", "shoulder"),
    ("bad knee", "knee"),
    ("chronic lower back pain", "back"),
    ("wrist pain", "wrist"),
    ("neck stiffness", "neck"),
])
def test_a_typed_limitation_excludes_poses(detail, body_part):
    """`physical_limitations_detail` was stored and read by no code. A user typing
    "frozen shoulder" got the same sequence as one who typed nothing."""
    base = _pose_names(generate_yoga_plan(_profile(), _prefs(), None, None))
    limited = _pose_names(generate_yoga_plan(
        _profile(), _prefs(physical_limitations_detail=detail), None, None))
    assert set(base) - set(limited), f"{detail!r} excluded nothing"


@pytest.mark.parametrize("typed,canonical", [
    ("recovering from ACL surgery", "knee"),
    ("rotator cuff tear", "shoulder"),
    ("sciatica", "lower back"),
    ("carpal tunnel", "wrist"),
])
def test_the_words_people_actually_type_reach_the_injury_maps(typed, canonical):
    """The maps key on body parts — "knee", "shoulder". Nobody types "knee injury";
    they type "ACL". Only unambiguous aliases are mapped: "surgery" on its own stays
    unrecognised rather than being guessed at."""
    base = _pose_names(generate_yoga_plan(_profile(), _prefs(), None, None))
    limited = _pose_names(generate_yoga_plan(
        _profile(), _prefs(physical_limitations_detail=typed), None, None))
    assert set(base) - set(limited), f"{typed!r} excluded nothing"
    assert not unmatched_limitations(_profile(), _prefs(physical_limitations_detail=typed))


def test_a_multi_part_sentence_is_split_not_swallowed():
    """"frozen shoulder, cannot raise left arm" is two phrases. Matched as one string
    it matches nothing at all."""
    prefs = _prefs(physical_limitations_detail="frozen shoulder, cannot raise left arm")
    base = _pose_names(generate_yoga_plan(_profile(), _prefs(), None, None))
    limited = _pose_names(generate_yoga_plan(_profile(), prefs, None, None))
    assert set(base) - set(limited), "the recognised half must still filter"

    unmatched = unmatched_limitations(_profile(), prefs)
    assert unmatched == ["cannot raise left arm"], unmatched


@pytest.mark.parametrize("phrase", ["everything hurts", "post-op recovery", "feeling weak"])
def test_a_limitation_the_engine_cannot_use_is_reported_not_dropped(phrase):
    """The worst outcome is silence. The user described an injury and every filter
    passed it by — exactly as an unmapped condition passes a contraindication gate.
    The plan has to say which words it could not act on."""
    plan = generate_yoga_plan(
        _profile(), _prefs(physical_limitations_detail=phrase), None, None)
    block = plan["unrecognised_limitations"]

    assert block, f"{phrase!r} was silently ignored"
    assert phrase in " ".join(block["phrases"])
    assert "no pose was excluded" in block["notice"]
    # And it tells the user how to make it work, not just that it did not.
    assert "knee" in block["notice"] and "shoulder" in block["notice"]


def test_no_notice_when_everything_was_understood():
    """The notice has to mean something, so it cannot appear on every plan."""
    for detail in (None, "bad knee", "shoulder injury"):
        plan = generate_yoga_plan(
            _profile(), _prefs(physical_limitations_detail=detail), None, None)
        assert plan["unrecognised_limitations"] is None


@pytest.mark.parametrize("experience", ["beginner", "intermediate", "advanced"])
def test_low_flexibility_restricts_and_high_flexibility_does_not_expand(experience):
    """`flexibility_level` was inert. The pose KB has no flexibility dimension, only
    `level`, so `level` is an explicit proxy — used in the restricting direction only.
    Expanding what a user is offered on the strength of a proxy would add risk on a
    guess, which is not a trade this engine should make.
    """
    def names(flex):
        return _pose_names(generate_yoga_plan(
            _profile(), _prefs(flexibility_level=flex, yoga_experience=experience), None, None))

    low, moderate, high = names("low"), names("moderate"), names("high")
    assert low != moderate, "low flexibility must change the sequence"
    assert high == moderate, "high flexibility must not unlock anything on a proxy"


def test_the_limitation_filter_does_not_empty_the_practice():
    """Every test above removes poses; this is the counterweight. A stiff beginner
    with several complaints must still get a session, not an empty one."""
    plan = generate_yoga_plan(
        _profile(age=64, fitness_level="beginner"),
        _prefs(yoga_experience="beginner", flexibility_level="low",
               physical_limitations_detail="bad knee, wrist pain, neck stiffness"),
        None, None)
    session = plan["weekly_schedule"][0]["session"]
    assert _pose_names(plan), "no poses survived the filter"
    assert session["total_duration_minutes"] > 0
