"""Deterministic condition-contraindicated food scan on the diet plan.

Covers the gap where the LLM-primary path trusted the model to honour each
condition's Apathya; apply_condition_food_safety now enforces a floor.
"""
import json
import pytest
from unittest.mock import AsyncMock, patch

from services.ahara_safety import (
    apply_condition_food_safety,
    classify_condition_apathya_llm,
    _CONDITION_APATHYA_TERMS,
    _canon_condition,
)


def _plan(meals):
    """Build a minimal LLM-shaped plan with one day of the given meals."""
    return {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": meals}}]}


def test_flags_contraindicated_food_for_condition():
    plan = _plan({
        "breakfast": {"meal_name": "Banana Oats Porridge", "key_ingredients": ["banana", "oats"]},
        "lunch": {"meal_name": "White Rice with Dal", "key_ingredients": ["white rice", "toor dal"]},
    })
    res = apply_condition_food_safety(plan, ["type2_diabetes"])
    assert res["condition_food_safe"] is False
    foods = {a["food"] for a in res["condition_safety_alerts"]}
    assert "banana" in foods and "white rice" in foods
    # per-meal flag attached
    assert plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["requires_substitution"] is True


def test_multi_condition_flags_each():
    plan = _plan({"breakfast": {"meal_name": "Banana shake", "key_ingredients": ["banana"]}})
    res = apply_condition_food_safety(plan, ["diabetes", "kidney disease"])
    conds = {a["condition"] for a in res["condition_safety_alerts"]}
    # banana is Apathya for BOTH diabetes (glycaemic) and kidney disease (potassium)
    assert any("Prameha" in c for c in conds)
    assert any("Kidney" in c for c in conds)


def test_low_false_positive_khichdi_rice_not_flagged():
    # Plain 'rice' in khichdi must NOT trip the diabetes 'white rice' rule.
    plan = _plan({"dinner": {"meal_name": "Moong Dal Khichdi", "key_ingredients": ["moong dal", "rice"]}})
    res = apply_condition_food_safety(plan, ["diabetes"])
    assert res["condition_food_safe"] is True


def test_no_matching_condition_is_safe_and_non_raising():
    res = apply_condition_food_safety(_plan({"lunch": {"meal_name": "Sugar-laden dessert"}}), ["sarcoidosis"])
    assert res["condition_food_safe"] is True
    assert res["condition_safety_alerts"] == []


def test_never_raises_on_malformed_plan():
    res = apply_condition_food_safety({"diet_weeks": "not a list"}, ["diabetes"])
    assert res["condition_safety_checked"] in (True, False)  # marked, never throws


def test_cholesterol_now_curated_scan():
    assert _canon_condition("high cholesterol") == "high_cholesterol"
    assert "high_cholesterol" in _CONDITION_APATHYA_TERMS
    res = apply_condition_food_safety(_plan(
        {"lunch": {"meal_name": "Deep Fried Samosa", "key_ingredients": ["potato", "fried"]}}
    ), ["cholesterol"])
    assert res["condition_food_safe"] is False


@pytest.mark.asyncio
async def test_rare_disease_apathya_classified_then_scanned():
    """A rare, uncurated disease gets its Apathya from the LLM, then the
    deterministic scan flags those foods — the safety floor now covers all diseases."""
    import services.ahara_safety as a
    a._CONDITION_APATHYA_CACHE.clear()
    fake = json.dumps({"Ankylosing Spondylitis": {
        "name": "Ankylosing Spondylitis (Amavata)",
        "reason": "Ama-forming, Vata-aggravating foods worsen Amavata.",
        "apathya_foods": ["curd", "fried", "cold drinks"]}})
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(return_value=fake)
        extra = await classify_condition_apathya_llm(["ankylosing spondylitis"])
    assert "ankylosing_spondylitis" in extra
    plan = _plan({"lunch": {"meal_name": "Fried Pakora with Curd", "key_ingredients": ["besan", "curd"]}})
    res = apply_condition_food_safety(plan, ["ankylosing spondylitis"], extra_terms=extra)
    assert res["condition_food_safe"] is False
    assert any("AI-inferred" in a2["condition"] for a2 in res["condition_safety_alerts"])


@pytest.mark.asyncio
async def test_apathya_classifier_failsafe_on_llm_error():
    import services.ahara_safety as a
    a._CONDITION_APATHYA_CACHE.clear()
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(side_effect=RuntimeError("llm down"))
        extra = await classify_condition_apathya_llm(["some rare syndrome"])
    assert extra == {}  # no crash, just no extra scan terms


@pytest.mark.asyncio
async def test_apathya_classifier_skips_already_curated():
    """Curated conditions must not trigger an LLM call — they already have a scan entry."""
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(return_value="{}")
        extra = await classify_condition_apathya_llm(["diabetes", "hypertension"])
    m.generate.assert_not_called()
    assert extra == {}


# ── Multi-condition conflict resolution ──────────────────────────────────────
from services.diet_brief_builder import detect_condition_conflicts, build_brief, _food_headword


def test_food_headword_extraction():
    assert _food_headword("banana (high potassium)") == "banana"
    assert _food_headword("spinach in large amounts") == "spinach"
    assert _food_headword("jaggery in excess") == "jaggery"
    assert _food_headword("old rice") == "rice"
    assert _food_headword("cold foods") == ""   # generic → no signal


def test_detects_real_conflicts():
    conflicts = detect_condition_conflicts(["anemia", "kidney_disease", "diabetes"])
    foods = {c["food"] for c in conflicts}
    assert "spinach" in foods   # anemia-beneficial, kidney-contraindicated
    assert "jaggery" in foods   # anemia-beneficial, diabetes-contraindicated
    spinach = next(c for c in conflicts if c["food"] == "spinach")
    assert "anemia" in spinach["beneficial_for"]
    assert "kidney_disease" in spinach["contraindicated_for"]


def test_no_conflict_for_single_or_aligned_conditions():
    assert detect_condition_conflicts(["diabetes"]) == []
    # BP + diabetes + cholesterol reinforce each other — no beneficial/harmful clash
    assert detect_condition_conflicts(["diabetes", "hypertension", "high_cholesterol"]) == []


def test_conflict_section_injected_into_brief_and_names_primary():
    profile = {"medical_history": ["anemia", "kidney disease"], "dominant_dosha": "vata"}
    brief = build_brief(profile, {"dietary_type": "vegetarian"})
    assert "CONFLICT RESOLUTION" in brief
    assert "Spinach" in brief
    assert "Primary condition" in brief and "Kidney" in brief  # tier-1 wins


def test_conflict_detection_never_needed_below_two_known():
    # Rare/uncurated condition + one known → nothing to compare, no crash
    assert detect_condition_conflicts(["sarcoidosis", "diabetes"]) == []
