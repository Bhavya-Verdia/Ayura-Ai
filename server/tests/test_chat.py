"""
Tests for the chat health-context builders that turn the user's full set of
plans into a compact, personalised context for the assistant (replacing the old
1500-char raw-JSON truncation that left the chat unaware of the user's plans).
"""
from types import SimpleNamespace

import pytest

from services.chat_service import (
    summarize_plans_for_chat,
    summarize_user_health,
    build_today_detail,
    extract_xml_tags,
    parse_reminder_specs,
    apply_chat_side_effects,
    _section,
)


class _FakeColl:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)

    async def update_one(self, *a, **k):
        pass


class _FakeDB:
    def __init__(self):
        self.reminders = _FakeColl()
        self.timeline = _FakeColl()
        self.users = _FakeColl()


def _nested(feature_key, data):
    return {feature_key: data, "user_summary": {}}


def test_summarize_plans_surfaces_key_facts():
    active = {
        "gym": _nested("gym_plan", {
            "weekly_schedule": [{"day_name": "Monday", "focus": "Chest Triceps"}],
            "user_summary": {"gym_goal": "muscle_gain", "fitness_level": "beginner"},
        }),
        "yoga": _nested("yoga_plan", {
            "weekly_schedule": [{"day_name": "Monday"}],
            "pranayama_safety_exclusions": [{"name": "Kapalabhati"}],
        }),
        "medicines": _nested("medicines", {
            "primary_formulations": [{"name": "Arjuna Churna", "dosage": "3-5g", "timing": "twice_daily"}],
            "chikitsa_approach": "Shamana",
        }),
        "panchakarma": _nested("panchakarma_plan", {
            "clinical_decisions": {
                "shodhana_or_shamana": {"type": "shamana"},
                "pradhana_karma_selected": {"primary": "basti_matra"},
            },
        }),
    }
    out = summarize_plans_for_chat(active)
    assert "Chest Triceps" in out
    assert "Kapalabhati" in out and "do NOT suggest" in out
    assert "Arjuna Churna" in out and "3-5g" in out
    assert "shamana" in out and "basti_matra" in out


def test_summarize_plans_never_crashes_on_bad_data():
    # Missing, None, wrong types — must degrade gracefully
    for active in ({}, {"gym": None}, {"diet": {"diet_plan": "oops"}},
                   {"medicines": _nested("medicines", {"primary_formulations": [None, {}]})}):
        assert isinstance(summarize_plans_for_chat(active), str)
    assert "No wellness plans" in summarize_plans_for_chat({})


def test_summarize_user_health_includes_constitution_and_allergies():
    user = SimpleNamespace(
        name="Ravi", age=40, gender="male", dominant_dosha="pitta",
        prakriti_classical_name="Pitta-Vata", dosha_constitution_type="pitta_vata",
        dosha_scores={"vata": 30, "pitta": 60, "kapha": 10},
        vikriti_dominant="pitta", vikriti_secondary="vata",
        agni_type="tikshna", ama_indicator="mild", ojas_level="medium",
        manas_prakriti="Rajasic Pitta", medical_history=["hyperacidity"],
        allergies=["dairy"], current_medications=[], current_symptoms=["acidity"],
    )
    out = summarize_user_health(user)
    assert "Pitta-Vata" in out
    assert "tikshna" in out
    assert "dairy" in out and "NEVER recommend" in out


def test_summarize_user_health_handles_unassessed_user():
    user = SimpleNamespace(name=None)
    assert isinstance(summarize_user_health(user), str)


def test_section_unwraps_nested_and_flat():
    assert _section({"gym_plan": {"x": 1}}, "gym") == {"x": 1}
    assert _section({"x": 1}, "gym") == {"x": 1}     # flat fallback
    assert _section(None, "gym") == {}


# ── Agent tools ──────────────────────────────────────────────────────────────

def test_extract_xml_tags_parses_reminder_and_symptoms():
    text = ("Take it at night.\n"
            "<reminder>Take Triphala Churna | 22:00 | medication</reminder>"
            "<symptoms>insomnia</symptoms>")
    clean, symptoms, plans, reminders = extract_xml_tags(text)
    assert clean == "Take it at night."           # tags stripped
    assert symptoms == ["insomnia"]
    assert reminders == [{"title": "Take Triphala Churna", "time": "22:00", "reminder_type": "medication"}]


def test_parse_reminder_specs_validates():
    assert parse_reminder_specs([{"title": "x", "time": "10pm"}]) == []          # bad time
    assert parse_reminder_specs([{"title": "", "time": "09:30"}]) == []          # empty title
    out = parse_reminder_specs([{"title": "Walk", "time": "07:00", "reminder_type": "bogus"}])
    assert out == [{"title": "Walk", "time": "07:00", "reminder_type": "general"}]  # type defaulted


@pytest.mark.asyncio
async def test_apply_side_effects_creates_reminder():
    db = _FakeDB()
    created = await apply_chat_side_effects(
        db, "u1", [], [], "remind me",
        reminders=[{"title": "Take Triphala", "time": "22:00", "reminder_type": "medication"}],
    )
    assert len(db.reminders.docs) == 1
    doc = db.reminders.docs[0]
    assert doc["title"] == "Take Triphala" and doc["time"] == "22:00" and doc["is_active"] is True
    assert created and created[0]["time"] == "22:00"


@pytest.mark.asyncio
async def test_apply_side_effects_rejects_bad_reminder():
    db = _FakeDB()
    created = await apply_chat_side_effects(
        db, "u1", [], [], "x",
        reminders=[{"title": "", "time": "22:00"}, {"title": "ok", "time": "notatime"}],
    )
    assert db.reminders.docs == [] and created == []


def test_build_today_detail_handles_rest_and_workout(monkeypatch):
    import services.chat_service as cs

    class _DT:
        @staticmethod
        def now(tz=None):
            import datetime as _d
            return _d.datetime(2026, 6, 24, tzinfo=tz)  # a Wednesday

    monkeypatch.setattr(cs, "datetime", _DT)
    active = {"gym": {"gym_plan": {"four_week_plan": [{"days": [
        {"day_name": "Wednesday", "focus": "Back Biceps",
         "main_workout": [{"exercise_name": "Barbell Row", "sets": 4, "reps": "8-10"}]},
    ]}]}}}
    out = build_today_detail(active)
    assert "Wednesday" in out and "Barbell Row" in out
