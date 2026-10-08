"""Text the safety gates cannot read is never passed as checked.

Measured before this: a meal named `दही चावल` (curd rice) or `தயிர் சாதம்` raised no
alert from any gate for a dairy-allergic patient, so translating the plan's source
fields would have switched the safety model off silently. The gates now refuse such
text, and translation is an overlay the gates never read.
"""
import asyncio
import json

import pytest

from services import diet_translate as dt
from services.ahara_safety import (apply_advisory_safety, apply_script_guard,
                                   unreadable_script)


def _plan(meal):
    return {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {"lunch": meal}}}]}


@pytest.mark.parametrize("name,script", [("दही चावल", "Devanagari"), ("தயிர் சாதம்", "Tamil"),
                                         ("ಮೊಸರನ್ನ", "Kannada"), ("酸奶饭", "Cjk")])
def test_a_meal_in_another_script_is_reported_unverified(name, script):
    out = apply_script_guard(_plan({"meal_name": name, "components": [{"food": "white_rice", "grams": 150}]}))
    assert out["unscannable_alerts"] and out["unscannable_alerts"][0]["script"] == script
    assert out["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["requires_substitution"]


@pytest.mark.parametrize("text", ["Moong Dal Khichdi", "Café-style Poha", "Āmalakī chutney",
                                  "Ragi Malt — 200 ml", "Idli 3 · Sambar 150 g"])
def test_latin_text_including_iast_and_accents_is_readable(text):
    assert unreadable_script(text) is None


def test_component_ids_alone_never_trip_the_guard():
    out = apply_script_guard(_plan({"meal_name": "Curd Rice",
                                    "components": [{"food": "curd_yogurt", "grams": 150}]}))
    assert out["unscannable_alerts"] == []


def test_the_week_generator_sends_unreadable_meals_to_repair():
    from services.diet_week_generator import _scan
    found = _scan({"diet_weeks": _plan({"meal_name": "दही चावल", "components": []})["diet_weeks"]},
                  [], [], "vegetarian", [], {}, False)
    assert (1, "Monday", "lunch") in found


def test_advisory_text_in_another_script_is_withheld_or_flagged():
    plan = {"pathya_apathya": {"pathya": ["मूंग दाल — हल्की", "Moong dal — light"]},
            "condition_coaching": "दही से बचें"}
    out = apply_advisory_safety(plan, [], [], [])
    assert out["pathya_apathya"]["pathya"] == ["Moong dal — light"]
    assert any(a["condition"] == "unverified" for a in out["advisory_prose_alerts"])


# ── Translation overlay ──────────────────────────────────────────────────────

_PLAN = {
    "plan_id": "diet_x", "plan_title": "Your Pitta plan",
    "pathya_apathya": {"pathya": ["Moong dal — light and cooling"]},
    "diet_weeks": [{"week_number": 1, "phase_description": "Kindle Agni gently.", "daily_plan": {
        "Monday": {"theme": "Light start",
                   "lunch": {"meal_name": "Moong Dal Khichdi",
                             "portion": "Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)",
                             "components": [{"food": "moong_dal_yellow", "grams": 150}]},
                   "special_drink": {"name": "Jeera water", "recipe": "1 tsp cumin in 200 ml water"}}}}],
}


def test_every_display_string_is_collected_and_no_component_is():
    s = dt.display_strings(_PLAN)
    assert s["diet_weeks.0.daily_plan.Monday.lunch.portion"].startswith("Moong Dal 150 g")
    assert "pathya_apathya.pathya.0" in s
    assert not any("components" in p for p in s)


@pytest.mark.parametrize("english,translated,ok", [
    ("Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)", "मूंग दाल 150 ग्राम (1 कटोरी) · घी 5 ग्राम (1 चम्मच)", True),
    ("Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)", "मूंग दाल 200 ग्राम (1 कटोरी) · घी 5 ग्राम (1 चम्मच)", False),
    ("Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)", "मूंग दाल १५० ग्राम (१ कटोरी) · घी ५ ग्राम (१ चम्मच)", False),
    ("Moong Dal 150 g (1 katori) · Ghee 5 g (1 tsp)", "मूंग दाल 150 ग्राम (1 कटोरी) · घी 5 ग्राम (1 चम्मच) · दही", False),
    ("Kindle Agni gently.", "", False),
])
def test_a_translation_keeps_every_number_and_item(english, translated, ok):
    assert dt.faithful(english, translated, "x.lunch.portion") is ok


def test_unfaithful_lines_stay_in_english(monkeypatch):
    async def fake(prompt, **k):
        items = json.loads(prompt.split("\n", 1)[1])
        return json.dumps({"t": {key: ("अनुवाद 999" if "150" in v else f"अनुवाद {v}")
                                 for key, v in items.items()}})
    monkeypatch.setattr("ai.llm_client.llm_client.generate", fake)
    out = asyncio.run(dt.translate_diet_plan(_PLAN, "hi"))
    assert "diet_weeks.0.daily_plan.Monday.lunch.portion" not in out["strings"]
    assert out["kept_english"] == 1
    assert out["source_hash"] == dt.source_hash(dt.display_strings(_PLAN))


def test_the_overlay_never_touches_the_checked_plan(monkeypatch):
    async def fake(prompt, **k):
        items = json.loads(prompt.split("\n", 1)[1])
        return json.dumps({"t": {key: f"अनुवाद {v}" for key, v in items.items()}})
    monkeypatch.setattr("ai.llm_client.llm_client.generate", fake)
    before = json.dumps(_PLAN, sort_keys=True)
    asyncio.run(dt.translate_diet_plan(_PLAN, "hi"))
    assert json.dumps(_PLAN, sort_keys=True) == before


def test_an_unsupported_language_is_refused():
    with pytest.raises(ValueError):
        asyncio.run(dt.translate_diet_plan(_PLAN, "xx"))


def test_the_translation_prompt_asks_for_json():
    """Azure refuses json_mode unless the prompt says JSON: every live batch failed
    with BadRequest while the mocked tests passed."""
    assert "JSON" in dt.PROMPT


def test_vegan_is_never_translated_as_vegetarian():
    assert "never translate it with the word for vegetarian" in dt.SYSTEM
