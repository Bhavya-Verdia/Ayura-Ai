"""The diet plan generated week by week, from the patient's own food list.

Measured before this, on sixteen live plans: 21 of 28 days carried no portion or
nutrition; one call in five lost its `weeks` array and the whole plan fell to the
rule engine; every figure was the model's estimate; and meals that broke the
patient's constraints shipped with a note on them.
"""
import pytest

import services.diet_llm_generator as gen
from tests.diet_fake_llm import make_fake

DAYS = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_BASE = {"id": "u1", "age": 35, "gender": "female", "height_cm": 160, "weight_kg": 60,
         "bmi_category": "normal", "activity_level": "moderate", "dominant_dosha": "vata",
         "agni_type": "sama", "ama_indicator": "none", "ojas_level": "moderate"}


@pytest.fixture(autouse=True)
def _no_rag(monkeypatch):
    async def none(*a, **k):
        return []
    monkeypatch.setattr(gen.rag_pipeline, "query", none)


async def _plan(monkeypatch, profile=None, prefs=None, **fake):
    calls: list = []
    monkeypatch.setattr(gen.llm_client, "generate", make_fake(calls, **fake))
    plan = await gen.generate_diet_plan_llm({**_BASE, **(profile or {})},
                                            {"diet_goal": "general_wellness", **(prefs or {})})
    return plan, calls


def _meals(plan):
    for w in plan["diet_weeks"]:
        for d in DAYS:
            day = w["daily_plan"][d]
            for s in ("breakfast", "lunch", "snack", "dinner", "special_drink"):
                yield w["week_number"], d, s, day[s]


@pytest.mark.asyncio
async def test_every_day_of_every_week_is_measured_and_on_target(monkeypatch):
    plan, calls = await _plan(monkeypatch)
    assert plan["nutrition_method"] == "computed_from_components"
    rec = plan["energy_reconciliation"]
    assert rec["days_quantified"] == 28 and rec["days_unquantified"] == 0
    lo, hi = rec["band_kcal"]
    for w in plan["diet_weeks"]:
        for d in DAYS:
            assert lo <= w["daily_plan"][d]["day_totals"]["calories"] <= hi, (w["week_number"], d)
    for *_, meal in _meals(plan):
        assert meal["components"] and meal["macros_approx"]["calories"] >= 0
        assert meal.get("nutrition_basis") == "computed"
    # Four weeks and an overview, in parallel — not one call for everything.
    assert sum("Write WEEK" in c for c in calls) == 4


@pytest.mark.asyncio
async def test_a_week_that_fails_is_retried_alone(monkeypatch):
    plan, calls = await _plan(monkeypatch, fail_weeks={2})
    assert plan is not None
    assert sum("Write WEEK 2" in c for c in calls) == 2
    assert sum("Write WEEK 1" in c for c in calls) == 1


@pytest.mark.asyncio
async def test_a_forbidden_food_is_repaired_not_noted(monkeypatch):
    """A vegan was given ghee 34 times, each with a note to substitute it."""
    plan, calls = await _plan(monkeypatch, prefs={"dietary_type": "vegan"},
                              bad={(1, "Monday", "lunch"): "ghee", (3, "Friday", "snack"): "paneer"})
    assert any("broke a rule" in c for c in calls)
    assert plan["composition_report"]["repaired"] >= 2
    assert not plan["dietary_type_alerts"]
    assert not any(c["food"] in ("ghee", "paneer") for *_, m in _meals(plan) for c in m["components"])


@pytest.mark.asyncio
async def test_an_unrepairable_meal_is_replaced_with_a_safe_one(monkeypatch):
    plan, _ = await _plan(monkeypatch, prefs={"dietary_type": "vegan"},
                          bad={(2, "Tuesday", "dinner"): "ghee"}, repair_food="ghee")
    assert plan["composition_report"]["substituted"] >= 1
    assert not plan["dietary_type_alerts"]
    assert plan["diet_weeks"][1]["daily_plan"]["Tuesday"]["dinner"].get("substituted")


@pytest.mark.asyncio
async def test_fasting_days_are_marked_and_not_scaled_up(monkeypatch):
    plan, _ = await _plan(monkeypatch, prefs={"fasting_days": ["Monday"]})
    rec = plan["energy_reconciliation"]
    assert rec["fasting_days_exempt"] == 4
    for w in plan["diet_weeks"]:
        assert w["daily_plan"]["Monday"]["is_fasting"]
    assert all(r["factor"] == 1.0 for r in rec["days"] if r["day"] == "Monday")


@pytest.mark.asyncio
async def test_diabetes_and_kidney_limits_hold_on_every_day(monkeypatch):
    plan, _ = await _plan(monkeypatch, profile={
        "medical_history": ["diabetes_type2", "ckd"], "weight_kg": 76, "height_cm": 170,
        "bmi_category": "overweight", "age": 52, "gender": "male"})
    nt = plan["nutrient_targets"]
    for w in plan["diet_weeks"]:
        for d in DAYS:
            t = w["daily_plan"][d]["day_totals"]
            assert t["protein_g"] <= nt["protein_g"]["max"] * 1.10, (w["week_number"], d, t)
            assert t["carbs_g"] - t["fiber_g"] <= nt["carbs_g"]["target"] * 1.10, (d, t)


@pytest.mark.asyncio
async def test_the_daily_drink_counts_toward_the_day(monkeypatch):
    plan, _ = await _plan(monkeypatch)
    day = plan["diet_weeks"][0]["daily_plan"]["Monday"]
    meals = sum(day[s]["macros_approx"]["calories"]
                for s in ("breakfast", "lunch", "snack", "dinner", "special_drink"))
    assert day["day_totals"]["calories"] == pytest.approx(meals, abs=2)


# ── The fallback is held to the same numbers ──────────────────────────────────

@pytest.mark.asyncio
async def test_the_rule_engine_fallback_is_screened_measured_and_on_target(monkeypatch):
    """The fallback served milk for a declared dairy allergy and lactose intolerance,
    composed meals with no cooking fat (7.5 g of fat a day), and missed the protein
    floor on 26 of 28 days."""
    async def no_llm(*a, **k):
        return None

    async def no_enrich(raw, *a, **k):
        return raw

    async def no_classify(*a, **k):
        return {}
    monkeypatch.setattr(gen, "generate_diet_plan_llm", no_llm)
    monkeypatch.setattr("services.diet_plan_enricher.enrich_diet_plan", no_enrich)
    monkeypatch.setattr("services.ahara_safety.classify_condition_apathya_llm", no_classify)
    profile = {**_BASE, "allergies": ["dairy"]}
    plan = await gen.build_diet_plan(profile, {"diet_goal": "general_wellness",
                                               "food_intolerances": ["lactose"],
                                               "food_allergies": ["dairy"]})
    assert plan["generation_method"] == "rule_engine"
    assert "four_week_plan" not in plan
    rec = plan["energy_reconciliation"]
    assert rec["days_quantified"] == 28 and rec["days_in_band"] == 28
    assert not plan["safety_alerts"]
    fats = [c for w in plan["diet_weeks"] for d in w["daily_plan"].values()
            for s in ("lunch", "dinner") for c in d[s]["components"] if c["food"] in
            ("ghee", "sesame_oil", "groundnut_oil", "sunflower_oil", "mustard_oil",
             "coconut_oil", "olive_oil")]
    assert fats
    for w in plan["diet_weeks"]:
        for d in w["daily_plan"].values():
            assert d["day_totals"]["fat_g"] >= 0.5 * plan["nutrient_targets"]["fat_g"]["target"]
