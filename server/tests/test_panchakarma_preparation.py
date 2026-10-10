"""Purvakarma follows the Karma it prepares for.

Every Basti, Matra Basti, Nasya and Raktamokshana course used to open with the
Snehapana ladder — 30 -> 120 ml of ghee over up to seven days — and a warning that
it was "shorter than classical" for Vata. Snehapana precedes Vamana and Virechana
only; the therapy KB's own `karma` tag on the Snehapana row says so. The same
reading of the plans found oil massages inside the Ama-clearing phase and clinic
days that held two Abhyangas and two steams.
"""
import itertools

import pytest

from services.panchakarma_engine import (
    _DEEPANA_EXCLUDED_THERAPIES,
    _ROW_KARMA,
    _therapy_kind,
    generate_panchakarma_plan,
)


def _profile(**over):
    base = dict(id="t", age=40, gender="male", bmi=23, vikriti_dominant="vata",
                fitness_level="intermediate", medical_history=[],
                ama_indicator="none", ojas_level="medium")
    base.update(over)
    return base


def _prefs(**over):
    base = dict(setting="clinic", available_time_days=14, detox_experience="some",
                access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
                self_care_time_per_day="2+ hours", panchakarma_goal="detox")
    base.update(over)
    return base


def _karma(plan):
    return plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]


# (profile overrides, prefs overrides) that land on each Karma.
_COURSES = {
    "basti": (dict(vikriti_dominant="vata"), {}),
    "basti_matra": (dict(vikriti_dominant="vata"), dict(setting="home")),
    "nasya": (dict(vikriti_dominant="kapha", medical_history=["hypertension"]), {}),
    "raktamokshana": (dict(vikriti_dominant="pitta"),
                      dict(panchakarma_goal="seasonal_cleanse", current_season="grishma")),
    "virechana": (dict(vikriti_dominant="pitta"), {}),
    "vamana": (dict(vikriti_dominant="kapha"), dict(current_season="vasanta")),
}


@pytest.mark.parametrize("karma", sorted(_COURSES))
def test_the_courses_land_where_these_tests_assume(karma):
    prof, prefs = _COURSES[karma]
    assert _karma(generate_panchakarma_plan(_profile(**prof), _prefs(**prefs))) == karma


@pytest.mark.parametrize("karma", ["basti", "basti_matra", "nasya", "raktamokshana"])
def test_a_course_without_internal_oleation_schedules_none(karma):
    prof, prefs = _COURSES[karma]
    plan = generate_panchakarma_plan(_profile(**prof), _prefs(**prefs))
    assert karma not in _ROW_KARMA["snehapana_home"]

    assert plan["snehana_protocol"]["dose_schedule"] == []
    assert plan["snehana_protocol"]["internal_ghrita"] is None
    assert not any(d.get("snehapana") or d.get("snehana_signs") for d in plan["daily_schedule"])
    assert not any("SNEHANA SHORTER" in w for w in plan["clinical_decisions"]["safety_warnings"])
    purva = next(p for p in plan["phase_breakdown"]["phases"] if p["key"] == "purvakarma")
    assert "Abhyanga + Swedana" in purva["sub"]
    assert purva["days"] <= 3


@pytest.mark.parametrize("karma", ["vamana", "virechana"])
def test_vamana_and_virechana_still_climb_the_ladder(karma):
    prof, prefs = _COURSES[karma]
    plan = generate_panchakarma_plan(_profile(**prof), _prefs(**prefs))
    doses = [d["snehapana"]["dose_ml"] for d in plan["daily_schedule"] if d.get("snehapana")]
    assert len(doses) >= 3 and doses[1] > doses[0]
    assert plan["snehana_protocol"]["internal_ghrita"]


def test_a_basti_course_gets_the_days_the_ladder_used_to_take():
    """14 days of Vata used to be 5 of ghee, 6 of Basti. The Yoga Basti is 8."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    assert plan["phase_breakdown"]["pradhana_karma_days"] == 8


_SWEEP = list(itertools.product(
    ["vata", "pitta", "kapha"],
    ["home", "clinic", "both"],
    ["none", "high"],
    [None, "pitta"],
))


def _plans():
    for dosha, setting, ama, sec in _SWEEP:
        yield (dosha, setting, ama, sec), generate_panchakarma_plan(
            _profile(vikriti_dominant=dosha, vikriti_secondary=sec, ama_indicator=ama),
            _prefs(setting=setting, available_time_days=21))


def test_no_oil_therapy_inside_deepana_pachana():
    """AH Su 2.9 withholds Abhyanga in Ajirna; the phase exists because Ama is unripe."""
    seen = 0
    for key, plan in _plans():
        for day in plan["daily_schedule"]:
            if "Deepana" not in day["phase"]:
                continue
            seen += 1
            ids = {t.get("id") for t in day["therapies"]}
            assert not ids & _DEEPANA_EXCLUDED_THERAPIES, (key, day)
    assert seen, "the sweep must reach the phase it guards"


def test_no_day_holds_the_same_procedure_twice():
    for key, plan in _plans():
        for day in plan["daily_schedule"]:
            kinds = [_therapy_kind(t["id"]) for t in day["therapies"]
                     if t.get("id") and not t.get("is_pradhana_karma")]
            assert len(kinds) == len(set(kinds)), (key, day["day"], kinds)


def test_a_clinic_course_does_not_hand_out_the_home_version_beside_the_clinic_one():
    for (dosha, setting, ama, sec), plan in _plans():
        if setting != "clinic":
            continue
        ids = {t.get("id") for d in plan["daily_schedule"] for t in d["therapies"]}
        assert not {"abhyanga_self", "swedana_home"} & ids, (dosha, ama, sec)


def test_udvartana_is_not_rubbed_off_a_vata_or_pitta_snehana():
    for (dosha, *_), plan in _plans():
        if dosha == "kapha":
            continue
        for day in plan["daily_schedule"]:
            if day["phase"].startswith("Purvakarma"):
                assert not any(str(t.get("id", "")).startswith("udvartana")
                               for t in day["therapies"]), (dosha, day)
