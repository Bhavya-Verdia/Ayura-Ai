"""
One body, two plans: injuries declared on either form reach both.

The gym form collected injuries with chips and a free-text box. The yoga form had
a free-text box. Each engine read only its own form, so a hernia ticked for the
gym never reached the yoga plan built for the same person. Yoga also could not act on
two of the gym's chips. `disc` was never read as a lower back, and
`abdominal_surgery` lives only in the condition map, which yoga did not run
injuries through.
"""
import asyncio
import json
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.movement_risk import declared_injuries, with_declared_injuries
from schemas.preferences_schema import GymPreferences, YogaPreferences
from services.yoga_plan_engine import (
    _build_contra_set, _build_risk_set, generate_yoga_plan, unmatched_limitations,
)

_POSES = {p["id"]: p for p in json.loads(
    (Path(__file__).resolve().parents[1] / "data" / "knowledge_base" / "yoga_poses.json").read_text())}


def test_the_two_forms_are_one_declaration():
    doc = {
        "gym": {"injuries": ["hernia", "knee"], "injury_detail": "old ACL tear"},
        "yoga": {"injuries": ["knee", "wrist"], "physical_limitations_detail": "can't kneel"},
    }
    chips, detail = declared_injuries(doc)
    assert chips == ["hernia", "knee", "wrist"]
    assert detail == "old ACL tear; can't kneel"
    assert declared_injuries({}) == ([], None)


def test_each_engine_receives_it_in_its_own_field():
    doc = {"gym": {"injuries": ["hernia"], "injury_detail": "tennis elbow"}}
    yoga = with_declared_injuries("yoga", {"yoga_goal": "flexibility"}, doc)
    assert yoga["injuries"] == ["hernia"]
    assert yoga["physical_limitations_detail"] == "tennis elbow"
    gym = with_declared_injuries("gym", {"injuries": []}, {"yoga": {"injuries": ["neck"]}})
    assert gym["injuries"] == ["neck"]


@pytest.mark.parametrize("chip, effect", [
    ("disc", ("contra", "herniated_disc")),
    ("abdominal_surgery", ("risk", "abdominal_pressure")),
    ("hernia", ("risk", "abdominal_pressure")),
    ("knee_replacement", ("contra", "knee_injury")),
    ("wrist", ("risk", "wrist_weight_bearing")),
])
def test_every_gym_chip_yoga_can_act_on_does_something(chip, effect):
    prefs = {"injuries": [chip]}
    sets = {"contra": _build_contra_set({"age": 35}, "adult", prefs),
            "risk": _build_risk_set({"age": 35}, "adult", prefs)}
    assert effect[1] in sets[effect[0]]


def test_a_chip_yoga_cannot_act_on_is_said_back():
    """The pose library has no elbow mechanism. The gym plan acts on an elbow and
    the yoga plan must not imply it did as well."""
    assert unmatched_limitations({}, {"injuries": ["elbow", "knee"]}) == ["elbow"]


def _pose_ids(obj):
    if isinstance(obj, dict):
        if obj.get("pose_id"):
            yield obj["pose_id"]
        for v in obj.values():
            yield from _pose_ids(v)
    elif isinstance(obj, list):
        for v in obj:
            yield from _pose_ids(v)


def test_a_hernia_ticked_for_the_gym_shapes_the_yoga_plan():
    from routes.plan_runner import _load_feature_preferences

    db = MagicMock()
    db.user_preferences.find_one = AsyncMock(return_value={
        "gym": {"gym_goal": "strength", "injuries": ["hernia"]},
        "yoga": {"yoga_goal": "strength", "yoga_experience": "intermediate"},
    })
    prefs = asyncio.run(_load_feature_preferences(db, "u", "yoga"))
    assert prefs["injuries"] == ["hernia"]

    profile = {"id": "u", "age": 35, "dominant_dosha": "kapha", "medical_history": []}
    baseline = set(_pose_ids(generate_yoga_plan(profile, {**prefs, "injuries": []})))
    assert any("abdominal_pressure" in (_POSES.get(p, {}).get("risk_tags") or [])
               for p in baseline), "the baseline must contain what the hernia removes"
    plan = set(_pose_ids(generate_yoga_plan(profile, prefs)))
    loaded = [p for p in plan if "abdominal_pressure" in (_POSES.get(p, {}).get("risk_tags") or [])]
    assert not loaded


# ── Saving: one list of chips across both forms ──────────────────────────────

def _db(doc):
    db = MagicMock()
    db.user_preferences.find_one = AsyncMock(return_value=doc)
    db.user_preferences.update_one = AsyncMock()
    return db


def _set_of(db):
    return db.user_preferences.update_one.call_args.args[1]["$set"]


def test_unticking_on_one_form_clears_it_for_both():
    from routes.preferences import save_yoga_preferences

    db = _db({"gym": {"injuries": ["hernia", "knee"]}, "yoga": {"injuries": ["hernia", "knee"]}})
    asyncio.run(save_yoga_preferences(
        YogaPreferences(yoga_goal="flexibility", injuries=["knee"]),
        user=SimpleNamespace(id="u"), db=db))
    assert _set_of(db)["gym.injuries"] == ["knee"]


def test_a_form_never_saved_is_not_created_by_the_other():
    """Writing `yoga.injuries` into a document with no yoga preferences creates a
    partial one, which the plan routes would read as preferences set."""
    from routes.preferences import save_gym_preferences

    db = _db({"gym": {"injuries": []}})
    asyncio.run(save_gym_preferences(
        GymPreferences(gym_goal="strength", injuries=["hernia"]),
        user=SimpleNamespace(id="u"), db=db))
    assert "yoga.injuries" not in _set_of(db)


def test_a_form_opened_for_the_first_time_shows_the_other_forms_chips():
    from routes.preferences import get_feature_preferences

    db = _db({"gym": {"gym_goal": "strength", "injuries": ["hernia"]}})
    res = asyncio.run(get_feature_preferences("yoga", user=SimpleNamespace(id="u"), db=db))
    assert res.is_set is False
    assert res.preferences["injuries"] == ["hernia"]


def test_a_herniated_disc_is_not_a_hernia():
    """Every map matches by substring, and "hernia" is in "herniated". A slipped
    disc was given the hernia note, the intensity ceiling, a Kapalabhati block and
    the loss of every abdominal-pressure pose. A real hernia still gets all four."""
    from engine.movement_risk import condition_risk_tags, injury_risk_tags
    from services.gym_condition_guidance import guidance_for
    from services.gym_plan_engine import _intensity_ceiling
    from services.yoga_plan_engine import _pranayama_hard_blocked

    kapalabhati = {"id": "skull_shining"}
    for disc in ("herniated_disc", "Herniated disc L4-L5", "disc herniation"):
        assert "abdominal_pressure" not in condition_risk_tags([disc]) | injury_risk_tags([disc])
        assert "abdominal" not in {g["key"] for g in guidance_for([disc])}
        assert _intensity_ceiling({"age": 35, "medical_history": [disc]}) is None
        assert not _pranayama_hard_blocked(kapalabhati, {disc.lower()})
    assert "back" in {g["key"] for g in guidance_for(["herniated_disc"])}

    for hernia in ("hernia", "inguinal_hernia"):
        assert "abdominal_pressure" in condition_risk_tags([hernia])
        assert _intensity_ceiling({"age": 35, "medical_history": [hernia]})
        assert _pranayama_hard_blocked(kapalabhati, {hernia})
