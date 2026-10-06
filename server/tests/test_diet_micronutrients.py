"""Sodium, potassium, phosphorus, calcium, iron and folate in the diet plan.

The plan stated a sodium limit and an anaemia note and could check neither: the
library held energy and the four macronutrients and nothing else. These hold the
table it now reads, the targets it is held to, and the salt trim that keeps a day
under its limit.
"""
import sys
from pathlib import Path

import pytest

from services import diet_nutrition as dn
from services import diet_week_generator as wg
from services.diet_energy import energy_target, nutrient_targets

SCRIPTS = Path(__file__).resolve().parent.parent / "scripts"
if str(SCRIPTS) not in sys.path:
    sys.path.insert(0, str(SCRIPTS))

import build_diet_micronutrients as builder     # noqa: E402


def test_every_food_a_plan_can_name_has_a_row():
    table = dn.micronutrients()
    names = set(dn._library()) | set(dn.EXTRAS)
    assert set(table) == names
    assert set(builder.MAP) == names


def test_a_missing_value_is_declared_never_a_silent_zero():
    """A food with no trustworthy source is None and says why. Counting it as zero
    would read as "measured, and low"."""
    for fid, row in dn.micronutrients().items():
        if row["sodium_mg"] is None:
            assert row["source"].startswith("not available"), fid
            assert all(row[k] is None for k in dn.MICROS), fid
        else:
            # A sourced row may lack one nutrient its source did not measure (SR
            # Legacy has no folate for soy milk, jamun, cardamom, fennel): that one
            # is not counted. Sodium is never the missing one — it marks the row.
            present = [k for k in dn.MICROS if row[k] is not None]
            assert len(present) >= 5 and all(row[k] >= 0 for k in present), fid


@pytest.mark.parametrize("fid,key,low,high", [
    ("salt", "sodium_mg", 38000, 39500),
    ("ragi_flour", "calcium_mg", 300, 400),       # the calcium millet
    ("amla", "calcium_mg", 10, 40),               # Emblica, not the European gooseberry
    ("white_rice", "iron_mg", 0, 0.5),            # unenriched: Indian rice is not fortified
    ("white_rice", "folate_ug", 0, 10),
    ("spinach", "folate_ug", 120, 220),
    ("banana", "potassium_mg", 300, 420),
])
def test_anchor_values_are_the_published_ones(fid, key, low, high):
    assert low <= dn.micronutrients()[fid][key] <= high


def test_compute_names_the_foods_it_could_not_count():
    r = dn.compute([{"food": "moong_dal_yellow", "grams": 100},
                    {"food": "fox_nuts_makhana", "grams": 20},
                    {"food": "water", "grams": 250}])
    assert r["unmeasured_micros"] == ["fox_nuts_makhana"]
    assert r["nutrition"]["folate_ug"] > 0


def _targets(**kw):
    conditions = kw.pop("conditions", [])
    base = dict(age=30, weight_kg=60, pregnant_or_nursing=False, gender="female")
    base.update(kw)
    return nutrient_targets(2000, 60, 48, conditions, **base)


def test_life_stage_sets_the_mineral_targets():
    assert _targets()["iron_mg"]["min"] == 29
    assert _targets(age=55)["iron_mg"]["min"] == 19
    assert _targets(gender="male")["iron_mg"]["min"] == 19
    preg = _targets(pregnant_or_nursing=True, state="pregnant")
    assert preg["iron_mg"]["min"] == 27 and preg["folate_ug"]["min"] == 570
    assert _targets(age=14)["sodium_mg"]["max"] == 1500


def test_sex_unrecorded_takes_the_higher_requirement():
    assert _targets(gender="other")["iron_mg"]["min"] == 29


def test_potassium_is_not_pushed_where_it_is_dangerous():
    """WHO's 3510 mg is for blood pressure in healthy adults. In kidney disease, or
    on a medicine that raises potassium, the advice is the opposite."""
    assert _targets()["potassium_mg"]["min"] == 3510
    assert "potassium_mg" not in _targets(potassium_restricted=True)
    assert "potassium_mg" not in _targets(age=15)

    profile = {"age": 55, "gender": "male", "height_cm": 170, "weight_kg": 70}
    assert "potassium_mg" in energy_target(profile, {})["nutrient_targets"]
    for extra in ({"medical_history": ["ckd"]}, {"current_medications": ["Telma 40"]}):
        assert "potassium_mg" not in energy_target({**profile, **extra}, {})["nutrient_targets"]


def _day(salt_g, extra=()):
    meal = lambda comps: dn.apply_to_meal({"meal_name": "x", "components": comps})  # noqa: E731
    return {
        "breakfast": meal([{"food": "poha", "grams": 200}]),
        "lunch": meal([{"food": "white_rice", "grams": 250}, {"food": "toor_dal", "grams": 150},
                       {"food": "salt", "grams": salt_g}, *extra]),
        "snack": meal([{"food": "banana", "grams": 120}]),
        "dinner": meal([{"food": "roti_whole_wheat", "grams": 120},
                        {"food": "salt", "grams": salt_g}]),
    }


def test_salt_is_trimmed_to_the_days_limit():
    day = _day(4.0)
    energy = {"nutrient_targets": {"sodium_mg": {"max": 2000}}}
    assert wg._day_totals(day)["sodium_mg"] > 2000
    wg._trim_salt(day, energy)
    assert wg._day_totals(day)["sodium_mg"] <= 2000


def test_salt_is_never_trimmed_below_a_pinch_per_meal():
    """Foods alone can carry a day past its limit; a savoury meal still gets a pinch
    rather than none, and the report says the day is over."""
    day = _day(2.0, extra=[{"food": "cottage_cheese", "grams": 400}])
    wg._trim_salt(day, {"nutrient_targets": {"sodium_mg": {"max": 1000}}})
    salts = [c["grams"] for s in ("lunch", "dinner") for c in day[s]["components"]
             if c["food"] == "salt"]
    assert salts == [wg._MIN_SALT_PER_MEAL] * 2


def test_the_fallback_salts_its_main_meals():
    raw = {"four_week_plan": [{"week": 1, "days": [{"day_name": "Monday", "meals": {
        "lunch": [{"id": "white_rice", "category": "grain"}, {"id": "toor_dal", "category": "legume"}],
        "snack": [{"id": "banana", "category": "fruit"}]}}]}]}
    weeks, _ = wg._engine_weeks(raw, {"ghee"})
    day = weeks[0]["daily_plan"]["Monday"]
    assert any(c["food"] == "salt" for c in day["lunch"]["components"])
    assert not any(c["food"] == "salt" for c in day["snack"]["components"])


def test_the_prompt_asks_for_minerals_only_where_the_need_is_high():
    assert wg._micro_rule({"nutrient_targets": {"iron_mg": {"min": 19},
                                                "calcium_mg": {"min": 800}}}) == ""
    rule = wg._micro_rule({"nutrient_targets": {"iron_mg": {"min": 27},
                                                "calcium_mg": {"min": 1000}}})
    assert "iron about 27 mg" in rule and "calcium about 1000 mg" in rule
