"""Sodium, potassium, phosphorus, calcium, iron and folate in the diet plan.

The plan stated a sodium limit and an anaemia note and could check neither: the
library held energy and the four macronutrients and nothing else. These hold the
table it now reads, the targets it is held to, and the salt trim that keeps a day
under its limit.
"""
import json
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


def test_the_table_is_what_the_builder_makes_from_the_cited_rows():
    """Never hand-edit the JSON: change `MAP`, run `extract`, then build."""
    assert builder.render(builder.build()) == builder.OUT.read_text()
    src = json.loads(builder.SOURCES.read_text())
    assert {(k, r) for k in ("sr", "ifct") for r in src[k]} == builder.cited()


def test_a_missing_value_is_declared_never_a_silent_zero():
    """A food with no trustworthy source is None and says why. Counting it as zero
    would read as "measured, and low"."""
    for fid, row in dn.micronutrients().items():
        if row["sodium_mg"] is None:
            assert row["source"].startswith("not available"), fid
            assert all(row[k] is None for k in dn.MICROS), fid
        else:
            # A sourced row may lack one nutrient its source did not measure (SR
            # Legacy has no folate for jamun, cardamom or fennel): that one
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


# ── Mineral sides ────────────────────────────────────────────────────────────

_ADULT_F = {"nutrient_targets": {"calcium_mg": {"min": 1000}, "iron_mg": {"min": 29}}}


def _plain_day():
    meal = lambda comps: dn.apply_to_meal({"meal_name": "Plain", "components": comps})  # noqa: E731
    return {
        "breakfast": meal([{"food": "poha", "grams": 200}, {"food": "banana", "grams": 100}]),
        "lunch": meal([{"food": "white_rice", "grams": 250}, {"food": "toor_dal", "grams": 150}]),
        "snack": meal([{"food": "apple", "grams": 120}]),
        "dinner": meal([{"food": "roti_whole_wheat", "grams": 120},
                        {"food": "bottle_gourd", "grams": 150}]),
    }


def test_sides_come_only_from_the_screened_list():
    vegan_ok = {"soy_milk", "tofu_firm", "sesame_seeds_til", "ragi_flour"}
    day = _plain_day()
    added = wg._add_mineral_sides(day, _ADULT_F, vegan_ok)
    assert added and set(added) <= vegan_ok
    assert wg._add_mineral_sides(_plain_day(), _ADULT_F, set()) == []


def test_a_side_never_makes_a_viruddha_pair():
    """Breakfast holds a banana, so milk is not added to it — milk with banana is
    the textbook Viruddha Ahara."""
    day = _plain_day()
    wg._add_mineral_sides(day, _ADULT_F, {"milk_full_fat"})
    assert not any(c["food"] == "milk_full_fat" for c in day["breakfast"]["components"])


def test_a_side_keeps_its_portion_through_the_solver():
    energy = {**_ADULT_F, "target_calories": 1800, "band": (1650, 1950),
              "protein_floor_g": 48, "protein_target_g": 60,
              "meal_budget": {"breakfast": 400, "lunch": 600, "snack": 200, "dinner": 600}}
    energy["nutrient_targets"].update({"carbs_g": {"target": 250}, "fat_g": {"target": 55},
                                       "sodium_mg": {"max": 2000}})
    day = _plain_day()
    assert "sesame_seeds_til" in wg._add_mineral_sides(day, energy, {"sesame_seeds_til"})
    wg._reconcile_day(day, energy)
    til = [c["grams"] for c in day["snack"]["components"] if c["food"] == "sesame_seeds_til"]
    assert til == [10]


def test_a_kidney_plan_gets_no_sides():
    from services.diet_week_generator import finalise_weeks
    day = _plain_day()
    energy = {"nutrient_targets": {"calcium_mg": {"min": 1000}, "protein_g": {"max": 45},
                                   "carbs_g": {"target": 250}, "fat_g": {"target": 55}},
              "target_calories": 1800, "band": (1650, 1950), "protein_floor_g": 40,
              "protein_target_g": 45,
              "meal_budget": {"breakfast": 400, "lunch": 600, "snack": 200, "dinner": 600}}
    weeks = [{"week_number": 1, "daily_plan": {d: (day if d == "Monday" else _plain_day())
                                               for d in wg.DAYS}}]
    finalise_weeks(weeks, energy, set(), {"curd_yogurt", "sesame_seeds_til"})
    assert not any(m.get("mineral_sides") for m in day.values() if isinstance(m, dict))


def test_a_shortfall_food_cannot_close_is_said_with_who_decides():
    notes = wg._mineral_notices({"iron_mg": {"min": 29, "average": 21.0},
                                 "calcium_mg": {"min": 1000, "average": 950.0}})
    assert len(notes) == 1 and "iron" in notes[0] and "doctor" in notes[0]
