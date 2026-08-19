"""Tests for routine_engine gym/yoga schedule extraction robustness.

Regression for the code-review finding where a single malformed day (blank/unknown
day_name, or an explicit null session duration) raised inside the extractor and the
bare `except` discarded the ENTIRE week's schedule instead of just that day.
"""
import pytest

from services.routine_engine import _extract_yoga_schedule, _extract_gym_schedule


def test_yoga_schedule_skips_unknown_day_keeps_rest():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Monday", "session": {"total_duration_minutes": 60, "dosha_theme": "Vata"}},
        {"day_name": "", "session": {"total_duration_minutes": 45}},          # malformed → skip
        {"day_name": "Wednesday", "rest": True},
    ]}]}
    out = _extract_yoga_schedule(plan)
    assert 0 in out and out[0]["ex_duration"] == "60 min"
    assert 2 in out and out[2]["is_rest"] is True
    assert 1 not in out  # blank day skipped, surrounding days survive


def test_yoga_schedule_null_duration_defaults_not_crash():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Tuesday", "session": {"total_duration_minutes": None, "dosha_theme": "Kapha"}},
    ]}]}
    out = _extract_yoga_schedule(plan)
    assert out[1]["ex_duration"] == "30 min"  # explicit null → default 30, no TypeError


def test_gym_schedule_skips_unknown_day_keeps_rest():
    plan = {"four_week_plan": [{"days": [
        {"day_name": "Funday", "focus": "Legs"},                # unknown weekday → skip
        {"day_name": "Friday", "focus": "Push"},
        {"day_name": "Sunday", "type": "rest"},
    ]}]}
    out = _extract_gym_schedule(plan)
    assert 4 in out and out[4]["gym_focus"] == "Push"
    assert 6 in out and out[6]["is_rest"] is True
    assert len(out) == 2  # the unknown day did not poison the whole schedule


# ── Pregnancy ────────────────────────────────────────────────────────────────

def _routine(pregnant, dosha="kapha"):
    from services.routine_engine import generate_routine_plan
    return generate_routine_plan(
        {"id": "t", "age": 29, "gender": "female", "dominant_dosha": dosha,
         "weight_kg": 68, "height": 162, "bmi_category": "normal",
         "medical_history": [], "pregnancy_or_nursing": pregnant},
        {"wake_time": "06:00", "sleep_time": "22:00"})


_SHODHANA = ("virechana", "vamana", "basti", "nasya")
_WITHHELD_LANGUAGE = ("withheld", "contraindicated", "set aside", "no virechana",
                      "not undertaken", "omitted", "skip")


@pytest.mark.parametrize("dosha", ["vata", "pitta", "kapha"])
def test_no_shodhana_is_recommended_during_pregnancy(dosha):
    """This engine handled twenty condition tokens and had no concept of
    pregnancy — the word did not appear in the file. A pregnant practitioner's
    autumn Ritucharya read "Virechana (Pitta purge) classically recommended",
    spring offered "Vamana if supervised", monsoon "Basti karma", and Nasya
    reached her every morning.

    `panchakarma_engine` has always refused: "Pregnancy / nursing — Shodhana
    contraindicated". Virechana IS Shodhana. Both engines read the same profile;
    this one was never asked.
    """
    import json
    import re

    blob = json.dumps(_routine(True, dosha), default=str)
    offending = []
    for match in re.finditer(r'"[^"]*(?:%s)[^"]*"' % "|".join(_SHODHANA), blob, re.I):
        text = match.group(0).strip('"')
        if len(text) > 15 and not any(w in text.lower() for w in _WITHHELD_LANGUAGE):
            offending.append(text[:90])
    assert not offending, offending


def test_the_same_instruction_is_gated_in_every_structure_that_carries_it():
    """The ritual list, the seasonal guidance and the weekly timeline each hold
    their OWN copy of the Nasya instruction. Gating the first two left the third
    untouched — seven times, once per day — which is exactly how prose has
    escaped a gate everywhere else in this codebase."""
    import json

    plan = _routine(True)
    timeline_text = json.dumps(plan["weekly_routine"], default=str).lower()
    assert "nasya with warm mustard oil" not in timeline_text
    assert "nasya, kavala" not in timeline_text


def test_a_practitioner_who_is_not_pregnant_keeps_the_full_routine():
    """The gate withholds; it does not water the feature down for everyone."""
    plan = _routine(False)
    nasya = [r for r in plan["dinacharya_protocol"]["morning_rituals"]
             if r["name"] == "Nasya"]
    assert nasya and "drops" in nasya[0]["instruction"]
    assert not plan["dinacharya_protocol"].get("pregnancy_notices")


def test_a_withheld_practice_says_that_it_was_withheld():
    plan = _routine(True)
    notices = plan["dinacharya_protocol"]["pregnancy_notices"]
    assert notices
    assert any("Shodhana" in n for n in notices)
