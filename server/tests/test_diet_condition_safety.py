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


def test_stored_canonical_forms_resolve_and_conflict():
    """Regression: profile stores condition_vocab canonicals (chronic_kidney_disease,
    diabetes_type2) — the diet module must map them or kidney guidance silently drops."""
    from services.diet_brief_builder import (
        normalize_condition_key, detect_condition_conflicts, uncurated_conditions,
        PATHYA_APATHYA_HINTS,
    )
    assert normalize_condition_key("chronic_kidney_disease") == "kidney_disease"
    assert normalize_condition_key("diabetes_type2") == "diabetes"
    stored = ["anemia", "chronic_kidney_disease", "diabetes_type2"]
    norm = [normalize_condition_key(c) for c in stored]
    foods = {c["food"] for c in detect_condition_conflicts(norm)}
    assert "spinach" in foods and "jaggery" in foods
    # anemia has a curated hint → must NOT be sent to the LLM classifier
    assert "anemia" not in uncurated_conditions(stored)
    assert all(normalize_condition_key(c) in PATHYA_APATHYA_HINTS for c in stored)


# ── The engine's food ids must name foods that exist ──────────────────────────
#
# `avoid_ids` is a hard filter and `boost_ids` a score bonus, both matched by exact
# id against `diet_foods.json`. A misspelt id is therefore not a visible error — it
# is a clinical rule that silently never fires, and nothing downstream can tell the
# difference between "this rule did not apply" and "this rule does not work".
#
# When these were first measured, 17 of 22 `avoid_ids` and 16 of 60 `boost_ids` were
# dead. The whole avoid list for hypertension, hypothyroid and thyroid did nothing.

def _library_ids():
    import json
    from pathlib import Path
    kb = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "diet_foods.json"
    return {r["id"] for r in json.loads(kb.read_text(encoding="utf-8"))}


def test_condition_protocol_ids_all_exist():
    from services.diet_plan_engine import _CONDITION_PROTOCOLS
    ids = _library_ids()
    dead = {
        f"{condition}.{key}": sorted((protocol.get(key) or set()) - ids)
        for condition, protocol in _CONDITION_PROTOCOLS.items()
        for key in ("avoid_ids", "boost_ids")
        if (protocol.get(key) or set()) - ids
    }
    assert not dead, (
        "condition protocols name foods that are not in the library, so these rules "
        f"can never fire: {dead}")


def test_item_portion_ids_all_exist():
    """A dead portion key falls through to the category default without complaint,
    and the difference reaches the user: flax was served at the nut_seed default of
    30 g instead of the 10 g this table intends, and the engine sums portions into
    the macro bar."""
    from services.diet_plan_engine import _ITEM_PORTIONS
    dead = sorted(set(_ITEM_PORTIONS) - _library_ids())
    assert not dead, f"portion overrides for foods not in the library: {dead}"


def test_the_crucifer_avoid_stays_empty_until_a_vaidya_rules():
    """`hypothyroid` and `thyroid` avoided `broccoli_raw`/`cabbage_raw`/
    `cauliflower_raw`, which never existed — the library carries only cooked rows.

    Whether the goitrogen caution applies to the cooked form is a clinical question,
    asked in `data/golden/vaidya_diet_packet.md`. Pointing these at the cooked rows
    would answer it by fiat, so the set stays empty — which is exactly what the dead
    ids already did — and this test records that the emptiness is a decision rather
    than an oversight for someone to 'fix'.
    """
    from services.diet_plan_engine import _CONDITION_PROTOCOLS
    for condition in ("hypothyroid", "thyroid"):
        assert _CONDITION_PROTOCOLS[condition]["avoid_ids"] == set()


# ── The library's own Apathya, wired into the engine ──────────────────────────
#
# Before this, `apathya_for` was read by `build_vectors.py` and nothing else. 708
# authored clinical claims reached the model as retrieved prose and decided nothing
# deterministically, while the engine excluded 5 (condition, food) pairs from a
# hand-kept list whose ids had drifted until 17 of 22 named nothing.

def _foods():
    import json
    from pathlib import Path
    kb = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "diet_foods.json"
    return json.loads(kb.read_text(encoding="utf-8"))


_PROFILES = [
    ["acidity"], ["ibs"], ["psoriasis"], ["amavata"], ["obesity"],
    ["acidity", "ibs"],
    ["obesity", "diabetes", "hypothyroid"],
    ["ibs", "grahani", "arsha", "amavata"],
    ["amavata", "psoriasis", "acidity"],
    ["obesity", "diabetes", "hypothyroid", "high_cholesterol", "fatty_liver"],
]


def test_no_apathya_food_survives_the_filter():
    from services.diet_plan_engine import _build_condition_rules, filter_and_score_foods
    foods = _foods()
    for history in _PROFILES:
        rules = _build_condition_rules(history)
        pool = filter_and_score_foods({"dominant_dosha": "vata"}, {}, foods, cond_rules=rules)
        leaked = sorted({f["id"] for f in pool
                         if set(f.get("apathya_for") or ()) & rules["conditions"]})
        assert not leaked, f"{history}: Apathya foods survived the filter: {leaked}"


def test_no_apathya_food_reaches_a_generated_plan():
    """The filter is one layer; this asserts the property that actually matters —
    that no meal, on any day of any of the four weeks, serves a food the library
    says is Apathya in a condition the user declared."""
    from services.diet_plan_engine import generate_diet_plan
    foods = _foods()
    apathya = {f["id"]: set(f.get("apathya_for") or ()) for f in foods}
    for history in _PROFILES:
        plan = generate_diet_plan(
            {"id": "t", "dominant_dosha": "pitta", "medical_history": history}, {}, foods)
        declared = {c.lower().replace(" ", "_") for c in history}
        served = set()
        for week in plan["four_week_plan"]:
            for day in week["days"]:
                for items in day["meals"].values():
                    served |= {item["id"] for item in items}
        bad = sorted({fid for fid in served if apathya.get(fid, set()) & declared})
        assert not bad, f"{history}: plan served Apathya foods {bad}"


def test_conditions_without_a_protocol_are_still_filtered():
    """`active` lists only conditions that have a `_CONDITION_PROTOCOLS` entry. Eleven
    of the twenty conditions the library carries Apathya rows for have no protocol —
    acidity (51 foods), IBS (44), psoriasis (29) among them — and those are precisely
    the conditions with no other deterministic food rule. Keying the filter off
    `active` would have silently excluded nothing for any of them."""
    from services.diet_plan_engine import _build_condition_rules, _CONDITION_PROTOCOLS
    rules = _build_condition_rules(["acidity", "psoriasis"])
    assert rules["conditions"] == {"acidity", "psoriasis"}
    assert not set(rules["active"]) & {"acidity", "psoriasis"}, \
        "test assumes neither has a protocol; if one was added, widen the assertion"
    assert "acidity" not in _CONDITION_PROTOCOLS


def test_a_cond_rules_dict_without_the_conditions_key_still_works():
    """`filter_and_score_foods` takes `cond_rules` as a public parameter. A caller
    holding a dict built before this key existed must degrade to 'no conditions
    declared', not raise KeyError part-way through building a plan."""
    from services.diet_plan_engine import filter_and_score_foods
    legacy = {"avoid_ids": set(), "avoid_categories": set(), "boost_ids": set(),
              "score_adjust": {}, "active": []}
    pool = filter_and_score_foods({"dominant_dosha": "vata"}, {}, _foods(), cond_rules=legacy)
    assert pool


def test_the_filter_does_not_empty_a_meal_slot_that_had_food_in_it():
    """Measured before wiring: the Apathya filter empties zero meal slots that were
    not already empty with no conditions declared. Three slots are empty at baseline
    (`fasting` lunch/dinner fruit, `tikshna` snack grain) because no food in those
    categories is `meal_suitable` for those meals — a pre-existing `_MEAL_CONFIGS`
    mismatch, not something this filter caused. This pins the distinction so a future
    library edit cannot quietly starve a slot and have it blamed on the config."""
    import collections
    from services.diet_plan_engine import _build_condition_rules, _MEAL_CONFIGS
    foods = _foods()

    def empty_slots(surviving):
        out = set()
        for cfg_name, cfg in _MEAL_CONFIGS.items():
            for meal, cats in cfg.items():
                per = collections.Counter(
                    f["category"] for f in surviving if meal in (f.get("meal_suitable") or []))
                out |= {(cfg_name, meal, c) for c in cats if per[c] == 0}
        return out

    baseline = empty_slots(foods)
    assert len(baseline) == 3, f"baseline emptiness changed: {sorted(baseline)}"
    for history in _PROFILES:
        conds = _build_condition_rules(history)["conditions"]
        surviving = [f for f in foods if not set(f.get("apathya_for") or ()) & conds]
        assert not (empty_slots(surviving) - baseline), \
            f"{history} newly empties {sorted(empty_slots(surviving) - baseline)}"
