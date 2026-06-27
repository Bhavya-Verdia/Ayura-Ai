"""Tests for routine_engine gym/yoga schedule extraction robustness.

Regression for the code-review finding where a single malformed day (blank/unknown
day_name, or an explicit null session duration) raised inside the extractor and the
bare `except` discarded the ENTIRE week's schedule instead of just that day.
"""
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
