"""The four questions the reviewer pack left open, answered as a dietitian would.

Each was a case where the plan was either unsafe or emptier than it needed to be:

  * kidney disease — kiwi passed every scan, because no list named it;
  * PCOS — soy was withheld from vegans, against the evidence;
  * acidity — 51 foods removed, some with no basis in either framework;
  * a 66-year-old lactose-intolerant vegetarian with IBS — under her protein floor on
    all 28 days, because curd, paneer and tofu were all gone.

And the vitamins nobody counted: B12, vitamin D, zinc and iodine.
"""
import asyncio

import pytest

import services.diet_llm_generator as gen
from services import diet_nutrition as dn
from services.diet_allowed_foods import allowed_foods, high_potassium_ids
from services.diet_energy import energy_target, nutrient_targets


def _excluded(conditions, **prefs):
    profile = {"age": 45, "gender": "female", "weight_kg": 60, "height_cm": 160,
               "medical_history": conditions}
    return allowed_foods(profile, {"dietary_type": "vegetarian", **prefs})["excluded"]


# ── Kidney disease ───────────────────────────────────────────────────────────

def test_a_kidney_patient_is_not_served_the_high_potassium_fruits():
    ex = _excluded(["kidney_disease"])
    for fid in ("kiwi", "guava", "yam", "lotus_stem", "drumstick_moringa", "raisins"):
        assert fid in ex, fid


def test_the_potassium_screen_reads_the_table_not_a_list():
    """A food added to the library later is screened by its composition."""
    k = dn.micronutrients()
    for fid in high_potassium_ids([dn.food(i) for i in dn.all_ids()]):
        assert k[fid]["potassium_mg"] >= 300, fid


def test_seasonings_and_low_potassium_vegetables_stay_for_a_kidney_patient():
    ex = _excluded(["ckd"])
    for fid in ("ginger", "garlic", "bottle_gourd", "ridge_gourd", "cabbage",
                "french_beans", "apple", "pear"):
        assert fid not in ex, (fid, ex.get(fid))


def test_the_potassium_screen_applies_only_to_kidney_disease():
    assert "kiwi" not in _excluded(["hypertension"])


# ── Soy ──────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("condition", ["pcos", "hypothyroid"])
def test_a_vegan_with_pcos_or_hypothyroidism_keeps_tofu(condition):
    ex = _excluded([condition], dietary_type="vegan")
    assert "tofu_firm" not in ex and "vegan_paneer_tofu" not in ex, ex.get("tofu_firm")
    assert "soy_milk" not in ex


def test_ibs_keeps_firm_tofu_and_still_withholds_whole_bean_soy():
    ex = _excluded(["ibs"])
    assert "tofu_firm" not in ex
    assert "soy_milk" in ex and "soya_chunks" in ex


# ── Acidity ──────────────────────────────────────────────────────────────────

def test_acidity_keeps_the_foods_with_no_case_against_them():
    ex = _excluded(["acidity"])
    for fid in ("carrot", "beetroot", "masoor_dal", "almonds"):
        assert fid not in ex, (fid, ex.get(fid))
    # The ones both frameworks agree on stay out.
    for fid in ("curd_yogurt", "tomato", "lemon_water", "black_pepper", "green_tea"):
        assert fid in ex, fid


# ── Lactose intolerance ──────────────────────────────────────────────────────

def test_lactose_intolerance_removes_milk_and_keeps_curd_and_paneer():
    ex = _excluded([], food_intolerances=["lactose"])
    assert "milk_full_fat" in ex and "lassi" in ex
    for fid in ("curd_yogurt", "paneer", "buttermilk_chaas", "ghee"):
        assert fid not in ex, (fid, ex.get(fid))


def _fallback_plan(profile, prefs, monkeypatch):
    async def none(*a, **k):
        return None

    async def same(raw, *a, **k):
        return raw

    async def empty(*a, **k):
        return {}
    monkeypatch.setattr(gen, "generate_diet_plan_llm", none)
    monkeypatch.setattr("services.diet_plan_enricher.enrich_diet_plan", same)
    monkeypatch.setattr("services.ahara_safety.classify_condition_apathya_llm", empty)
    return asyncio.run(gen.build_diet_plan(profile, prefs))


def test_the_lactose_intolerant_vegetarian_with_ibs_reaches_her_protein_floor(monkeypatch):
    """Reviewer persona 9. The pack showed her under the floor on all 28 days; the
    per-day solver had already lifted the average to the floor itself (58.5 g against
    59), by scaling dal and nuts. With curd, paneer and tofu back on her list the
    protein comes from food a 66-year-old eats, and the plan has room above the floor."""
    profile = {"id": "p9", "age": 66, "gender": "female", "height_cm": 155, "weight_kg": 54,
               "bmi_category": "normal", "activity_level": "light", "dominant_dosha": "vata",
               "agni_type": "vishama", "medical_history": ["osteoporosis"]}
    prefs = {"diet_goal": "gut_health", "dietary_type": "vegetarian",
             "food_intolerances": ["lactose"], "gut_health_issue": "ibs"}
    plan = _fallback_plan(profile, prefs, monkeypatch)
    floor = plan["energy_prescription"]["protein_floor_g"]
    days = [d for w in plan["diet_weeks"] for d in w["daily_plan"].values()]
    short = [d["day_totals"]["protein_g"] for d in days if d["day_totals"]["protein_g"] < floor * 0.95]
    assert len(short) <= 3, (floor, short)
    used = {c["food"] for d in days for s in ("breakfast", "lunch", "snack", "dinner")
            for c in (d.get(s) or {}).get("components") or []}
    assert used & {"curd_yogurt", "paneer", "tofu_firm", "vegan_paneer_tofu"}, sorted(used)
    assert "milk_full_fat" not in used


# ── Vitamins and iodine ──────────────────────────────────────────────────────

def test_every_patient_has_b12_vitamin_d_zinc_and_iodine_targets():
    nt = nutrient_targets(1800, 60, 50, [], age=40, weight_kg=60,
                          pregnant_or_nursing=False, gender="female")
    assert nt["b12_ug"]["min"] == 2.2 and nt["zinc_mg"]["min"] == 13.2
    assert nt["vitd_ug"]["min"] == 15 and nt["iodine_ug"]["min"] == 150


def test_pregnancy_raises_iodine_and_old_age_raises_vitamin_d():
    preg = nutrient_targets(2200, 70, 60, [], age=28, weight_kg=60, pregnant_or_nursing=True,
                            gender="female", state="pregnant")
    old = nutrient_targets(1700, 60, 55, [], age=75, weight_kg=60,
                           pregnant_or_nursing=False, gender="male")
    assert preg["iodine_ug"]["min"] == 250 and old["vitd_ug"]["min"] == 20


def test_hyperthyroidism_gets_no_iodine_target():
    nt = nutrient_targets(1800, 60, 50, ["hyperthyroidism"], age=40, weight_kg=60,
                          pregnant_or_nursing=False, gender="female")
    assert "iodine_ug" not in nt


def test_iodine_comes_from_iodised_salt_and_not_from_rock_salt():
    salt = dn.compute([{"food": "salt", "grams": 4}])["nutrition"]
    rock = dn.compute([{"food": "rock_salt", "grams": 4}])["nutrition"]
    assert salt["iodine_ug"] == 60 and rock["iodine_ug"] == 0


def test_plant_milks_are_counted_unfortified():
    """Indian soy and almond drinks are mostly sold without added calcium, B12 or D;
    counting a US carton's fortification would close a vegan's gap on paper."""
    t = dn.micronutrients()
    assert t["soy_milk"]["calcium_mg"] < 40 and t["soy_milk"]["b12_ug"] == 0
    assert t["almond_milk"]["calcium_mg"] < 20 and t["almond_milk"]["vitd_ug"] == 0


def test_dairy_carries_b12_and_plants_none():
    t = dn.micronutrients()
    for fid in ("milk_full_fat", "curd_yogurt", "paneer"):
        assert t[fid]["b12_ug"] > 0.3, fid
    for fid in ("moong_dal_yellow", "ragi_flour", "tofu_firm", "spinach"):
        assert t[fid]["b12_ug"] == 0, fid


def test_only_makhana_is_left_unmeasured():
    """Its published compositions disagree ten-fold; every other food is sourced."""
    t = dn.micronutrients()
    assert [f for f, r in t.items() if r["sodium_mg"] is None] == ["fox_nuts_makhana"]


def test_a_vegan_plan_says_where_b12_has_to_come_from(monkeypatch):
    profile = {"id": "v", "age": 30, "gender": "male", "height_cm": 175, "weight_kg": 70,
               "bmi_category": "normal", "activity_level": "moderate",
               "dominant_dosha": "pitta", "medical_history": []}
    plan = _fallback_plan(profile, {"diet_goal": "general_wellness", "dietary_type": "vegan"},
                          monkeypatch)
    notices = plan["energy_reconciliation"]["micronutrients"]["notices"]
    assert any("no reliable plant source of B12" in n for n in notices), notices
    assert any("sunlight" in n for n in notices), notices


def test_a_long_term_acid_reducer_gets_a_b12_note():
    from services.diet_clinical_notes import medication_matches
    found, _ = medication_matches({"current_medications": ["Pan 40"]})
    assert any(m["key"] == "acid_suppressant" for m in found)


def test_energy_target_carries_the_new_targets_through():
    e = energy_target({"age": 35, "gender": "male", "weight_kg": 70, "height_cm": 175,
                       "activity_level": "moderate"}, {"diet_goal": "general_wellness"})
    assert {"b12_ug", "vitd_ug", "zinc_mg", "iodine_ug"} <= set(e["nutrient_targets"])


def test_iodine_is_raised_only_in_pregnancy_or_on_very_little_salt():
    from services.diet_week_generator import _mineral_notices
    ordinary = {"iodine_ug": {"min": 150, "average": 55}}
    pregnant = {"iodine_ug": {"min": 250, "average": 55}}
    low_salt = {"iodine_ug": {"min": 150, "average": 20}}
    assert _mineral_notices(ordinary) == []
    assert "iodised salt" in _mineral_notices(pregnant)[0]
    assert "iodised salt" in _mineral_notices(low_salt)[0]


def test_no_side_dish_phrase_trips_a_scan():
    """`_add_mineral_sides` writes its phrase into the meal name after the scans ran;
    "ragi malt" shipped as a gluten alert for a coeliac."""
    from services.ahara_safety import ALLERGEN_TERMS, _CONDITION_APATHYA_TERMS, _term_in_text
    from services.diet_week_generator import _MINERAL_SIDES
    terms = {t for v in ALLERGEN_TERMS.values() for t in v} | {"malt"}
    terms |= {t for p in _CONDITION_APATHYA_TERMS.values() for t in p.get("terms", [])}
    for fid, _, _, phrase in _MINERAL_SIDES:
        own = {fid.split("_")[0], "curd", "milk", "chaas", "paneer", "til", "soy", "tofu",
               "almond", "pumpkin", "banana", "coconut", "amla", "methi", "gavar", "ragi"}
        bad = [t for t in terms if _term_in_text(t, phrase.lower())
               and not any(o in t or t in o for o in own)]
        assert not bad, (phrase, bad)
