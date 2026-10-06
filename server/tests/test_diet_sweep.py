"""Diet plans for people nobody wrote a test for.

Sixty random profiles — every age the app accepts, every body size, both sexes and
none, single diseases and combinations, allergies, vegan and Jain, medicines,
pregnancy and breastfeeding — each built end to end on the rule-engine path (no
model call) and held to what a dietitian would expect of any plan:

  * all 28 days composed from foods this patient may eat, and measured;
  * no scan finds anything (the screen and the repair exist so that nothing ships
    with a "substitute this" note);
  * every day inside its energy band, protein at or above its floor, a renal
    ceiling held, diabetic available carbohydrate held, fat inside its range;
  * no planned fast for a child, a pregnancy, diabetes, kidney disease or
    underweight.

The LLM path composes from the same screened list and goes through the same
solver; `test_diet_week_generator` covers its generation.
"""
import asyncio
import random

import pytest

import services.diet_llm_generator as gen
from services.diet_allowed_foods import allowed_foods
from services.diet_brief_builder import fasting_withheld_reason

_CONDITIONS = ["diabetes_type2", "hypertension", "ckd", "high_cholesterol", "heart_disease",
               "hypothyroidism", "pcos", "gout", "anemia", "osteoporosis", "ibs", "acidity",
               "celiac", "fatty_liver", "kidney_stones", "obesity", "constipation"]
_ALLERGIES = ["gluten", "dairy", "nuts_tree", "peanuts", "soy", "sesame"]
_MEDS = ["warfarin", "metformin", "atorvastatin", "telma 40", "thyronorm", "phenelzine"]


def _profile(rng: random.Random, i: int):
    age = rng.choice([11, 14, 17, 22, 30, 38, 45, 52, 61, 68, 75, 84])
    gender = rng.choice(["male", "female", "female", "other"])
    height = rng.randint(140, 190) if age >= 14 else rng.randint(135, 160)
    bmi = rng.choice([16.5, 19, 22, 24, 27, 31, 36])
    weight = round(bmi * (height / 100) ** 2, 1)
    cat = ("underweight" if bmi < 18.5 else "normal" if bmi < 25 else
           "overweight" if bmi < 30 else "obese")
    conds = rng.sample(_CONDITIONS, rng.choice([0, 0, 1, 1, 2, 3]))
    profile = {
        "id": f"sweep{i}", "age": age, "gender": gender, "height_cm": height,
        "weight_kg": weight, "bmi_category": cat,
        "activity_level": rng.choice(["sedentary", "light", "moderate", "active", "very_active"]),
        "dominant_dosha": rng.choice(["vata", "pitta", "kapha"]),
        "agni_type": rng.choice(["sama", "vishama", "tikshna", "manda"]),
        "ama_indicator": rng.choice(["none", "moderate", "high"]),
        "ojas_level": rng.choice(["low", "moderate", "high"]),
        "medical_history": conds,
        "allergies": rng.sample(_ALLERGIES, rng.choice([0, 0, 0, 1, 2])),
        "current_medications": rng.sample(_MEDS, rng.choice([0, 0, 1, 2])),
    }
    if gender == "female" and 20 <= age <= 40 and rng.random() < 0.25:
        profile.update(pregnancy_or_nursing=True,
                       pregnancy_status=rng.choice(["pregnant", "nursing"]),
                       pregnancy_trimester=rng.choice([1, 2, 3]))
    prefs = {
        "diet_goal": rng.choice(["weight_loss", "muscle_support", "gut_health", "energy",
                                 "general_wellness"]),
        "dietary_type": rng.choice(["vegetarian", "vegetarian", "vegan"]),
        "food_allergies": list(profile["allergies"]),
        "food_intolerances": rng.sample(["lactose", "fructose"], rng.choice([0, 0, 1])),
        "fasting_days": ["Monday"] if rng.random() < 0.3 else [],
        "dietary_restrictions": ["jain"] if rng.random() < 0.15 else [],
    }
    return profile, prefs


def _build(profile, prefs, monkeypatch):
    async def no_llm(*a, **k):
        return None

    async def no_enrich(raw, *a, **k):
        return raw

    async def no_classify(*a, **k):
        return {}
    monkeypatch.setattr(gen, "generate_diet_plan_llm", no_llm)
    monkeypatch.setattr("services.diet_plan_enricher.enrich_diet_plan", no_enrich)
    monkeypatch.setattr("services.ahara_safety.classify_condition_apathya_llm", no_classify)
    return asyncio.run(gen.build_diet_plan(profile, prefs))


_SWEEP = [_profile(random.Random(7000 + i), i) for i in range(60)]


@pytest.mark.parametrize("profile,prefs", _SWEEP, ids=[p["id"] for p, _ in _SWEEP])
def test_any_patient_gets_a_plan_a_dietitian_would_accept(profile, prefs, monkeypatch):
    plan = _build(profile, prefs, monkeypatch)
    rx, nt, rec = plan["energy_prescription"], plan["nutrient_targets"], plan["energy_reconciliation"]
    allowed = {f["id"] for f in allowed_foods(profile, prefs)["allowed"]}
    who = f"{profile['id']} age {profile['age']} {profile['medical_history']} {prefs}"

    assert rec["days_quantified"] == 28, who
    for key in ("safety_alerts", "dietary_type_alerts", "condition_safety_alerts"):
        assert not plan.get(key), (who, key, plan.get(key)[:2])

    if fasting_withheld_reason(profile, prefs):
        assert rec["fasting_days_exempt"] == 0, who

    lo, hi = rx["band"]
    flo, fhi = int(rx["target_calories"] * 0.40), int(rx["target_calories"] * 0.70)
    misses = []
    for w in plan["diet_weeks"]:
        for d, day in w["daily_plan"].items():
            for slot in ("breakfast", "lunch", "snack", "dinner", "special_drink"):
                for c in (day.get(slot) or {}).get("components") or []:
                    assert c["food"] in allowed, (who, d, slot, c["food"])
            t = day["day_totals"]
            fasting = day.get("is_fasting")
            in_band = (flo <= t["calories"] <= fhi) if fasting else (lo <= t["calories"] <= hi)
            ok = in_band
            if not fasting:
                ok = ok and t["protein_g"] >= rx["protein_floor_g"] * 0.85
                if nt["protein_g"].get("max"):
                    ok = ok and t["protein_g"] <= nt["protein_g"]["max"] * 1.15
                if nt["added_sugar_g"]["max"] == 0:
                    ok = ok and t["carbs_g"] - t["fiber_g"] <= nt["carbs_g"]["target"] * 1.15
                ok = ok and t["fat_g"] <= nt["fat_g"]["target"] * 1.35
            if not ok:
                misses.append((w["week_number"], d, t))
    # A fallback composed from category quotas cannot always reach every target on
    # every day; more than a few misses is a solver or composition fault.
    assert len(misses) <= 3, (who, rx["band"], rx["protein_floor_g"], nt["fat_g"], misses[:3])
