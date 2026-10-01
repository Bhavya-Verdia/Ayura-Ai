"""The rule-engine path composes against the energy target, not just category quotas.

`_MEAL_CONFIGS` builds a meal from a list of categories and knows nothing about
energy. Measured on a Manda-Agni patient with a 2100 kcal target: breakfast came back
as green tea and an orange — **58 kcal** — snack as a single amla (53), dinner as
zucchini and quinoa (206), for a day of 918. Across 28 days the plan ran 1082-1585
kcal against 2100, with 22-40 g of protein against a 48 g floor.

`reconcile_plan_energy` could not repair that and was right not to: it scales
portions, and no multiplier turns two oranges into a breakfast. A slot 8.99x short is
short of *food*. Composition is topped up first now, and the reconciler does the fine
scaling on something it can work with.
"""

import collections

import pytest

from services.diet_energy import energy_target
from services.diet_plan_engine import _format_food, _ITEM_PORTIONS, diet_foods, generate_diet_plan
from services.diet_portion_reconciler import reconcile_plan_energy

_PROFILES = [
    ("manda", {"dominant_dosha": "vata", "agni_type": "manda"}),
    ("sama", {"dominant_dosha": "pitta", "agni_type": "sama"}),
    ("tikshna", {"dominant_dosha": "pitta", "agni_type": "tikshna"}),
]


def _profile(**over):
    p = {"dominant_dosha": "vata", "agni_type": "manda", "age": 35, "gender": "female",
         "height_cm": 162, "weight_kg": 60, "activity_level": "moderate",
         "bmi_category": "normal", "medical_history": [], "current_season": "varsha"}
    p.update(over)
    return p


def _prefs(**over):
    p = {"dietary_type": "vegetarian", "diet_goal": "gut_health", "food_allergies": [],
         "food_intolerances": [], "gut_health_issue": "healthy",
         "intermittent_fasting": "no", "water_intake": "2-3L", "fasting_days": []}
    p.update(over)
    return p


def _built(profile, prefs):
    energy = energy_target(profile, prefs)
    plan = reconcile_plan_energy(generate_diet_plan(profile, prefs, None), energy)
    days = [d for w in plan["four_week_plan"] for d in w["days"]]
    return plan, energy, days


@pytest.mark.parametrize("label,over", _PROFILES)
def test_every_non_fasting_day_lands_in_band(label, over):
    plan, energy, days = _built(_profile(**over), _prefs())
    low, high = energy["band"]
    out = [(d["day_name"], d["daily_macros"]["calories"])
           for d in days if not d.get("is_fasting_day")
           and not low <= d["daily_macros"]["calories"] <= high]
    assert not out, f"{label}: {len(out)} days outside {energy['band']}: {out[:3]}"


@pytest.mark.parametrize("label,over", _PROFILES)
def test_the_protein_floor_is_met(label, over):
    plan, energy, days = _built(_profile(**over), _prefs())
    floor = energy["protein_floor_g"]
    short = [(d["day_name"], d["daily_macros"]["protein_g"])
             for d in days if not d.get("is_fasting_day")
             and d["daily_macros"]["protein_g"] < floor]
    assert not short, f"{label}: {short[:3]} below {floor} g"


def test_the_reconciler_has_nothing_left_to_report():
    """It reported a shortfall on all 28 days — "reaches 1368 kcal of a 2100 kcal
    target even at the largest sensible portions". Honest, and not a plan."""
    plan, _, _ = _built(_profile(), _prefs())
    rec = plan["energy_reconciliation"]
    assert rec["residual_notes"] == []
    assert rec["days_below_protein_floor"] == []


def test_a_fasting_day_is_left_light():
    """Upavasa is the therapy. Topping one up to a full day's energy would undo the
    thing the day is for, so the top-up skips them as the reconciler does."""
    plan, energy, days = _built(_profile(), _prefs(fasting_days=["Monday"]))
    fasting = [d for d in days if d.get("is_fasting_day")]
    assert fasting
    for day in fasting:
        assert day["daily_macros"]["calories"] < energy["band"][0]


def test_no_food_appears_twice_in_one_day():
    """Without the day's set, a food is added to breakfast and picked again for lunch
    — 25 repeats across a four-week plan when this was measured."""
    plan, _, days = _built(_profile(), _prefs())
    for day in days:
        ids = [i["id"] for items in day["meals"].values() for i in items]
        assert len(ids) == len(set(ids)), f"{day['day_name']}: {ids}"


def test_the_plan_does_not_collapse_onto_one_food():
    """Ranking by density alone is deterministic, so the same winner is added to every
    slot of every day: nutritional yeast appeared 56 times across 28 days, at 100 g."""
    plan, _, _ = _built(_profile(), _prefs())
    counts = collections.Counter(
        i["name"] for w in plan["four_week_plan"] for d in w["days"]
        for items in d["meals"].values() for i in items)
    assert len(counts) >= 25, f"only {len(counts)} distinct foods"
    top_name, top_n = counts.most_common(1)[0]
    assert top_n <= 28, f"{top_name} appears {top_n} times across 28 days"


def test_the_top_up_cannot_reintroduce_a_withheld_food():
    """It draws from `pool`, which has already passed every dosha, season, allergy,
    dietary-type and condition-Apathya filter. A top-up that went to the raw library
    would undo the safety model to hit a calorie number."""
    profile = _profile()
    prefs = _prefs(gut_health_issue="acidity", food_allergies=["dairy"])
    plan, _, days = _built(profile, prefs)

    from services.diet_condition_foods import condition_food_rules
    apathya = {f.lower() for f in condition_food_rules("acidity")["apathya_names"]}
    served = {i["name"].lower() for d in days for items in d["meals"].values() for i in items}
    assert not (served & apathya), sorted(served & apathya)

    dairy = {f["id"] for f in diet_foods if f["category"] == "dairy"}
    served_ids = {i["id"] for d in days for items in d["meals"].values() for i in items}
    assert not (served_ids & dairy), sorted(served_ids & dairy)


def test_no_single_portion_is_one_nobody_would_eat():
    """`_PORTION` gives a dairy food 150 ml and a grain a 150 g katori — right for milk
    and rice, absurd for butter and for a flour. Navanita came out at 1076 kcal a
    serving and nutritional yeast, a condiment measured in spoons, at 100 g and 45 g
    of protein. The portion text is shown to the patient and the macros are summed
    into a day total on screen."""
    loud = [(f["id"], _format_food(f)["portion"], _format_food(f)["macros"]["calories"])
            for f in diet_foods if _format_food(f)["macros"]["calories"] >= 300]
    assert not loud, loud


def test_the_condiments_have_their_own_portions():
    for fid in ("butter", "cream", "nutritional_yeast", "chickpea_flour_besan"):
        assert fid in _ITEM_PORTIONS, f"{fid} falls through to its category default"
