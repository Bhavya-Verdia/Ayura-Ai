"""A plan's nutrition is computed from what is in it, not written to fit the target.

Every figure a plan showed was the model's estimate: "4 medium idli + 2 tbsp
chutney" carried 540 kcal, where those foods come to about 300, and days landed
within a few kcal of target because the figure was written to match it.
"""
import pytest

from services.diet_nutrition import (EXTRAS, SEASONINGS, _library, all_ids, apply_to_meal,
                                      compute, household, portion_text, scale)


def test_every_food_a_plan_can_name_has_nutrition_and_a_source():
    for fid in all_ids():
        from services.diet_nutrition import food
        f = food(fid)
        per = f["nutrition_per_100g"]
        assert all(k in per for k in ("calories", "protein_g", "carbs_g", "fat_g")), fid
        assert f.get("nutrition_source"), fid


def test_the_extras_never_shadow_a_library_row():
    assert not set(EXTRAS) & set(_library())


def test_energy_is_the_sum_of_its_components():
    """A breakfast of four idli, sambar and chutney — the one the model put at
    540 kcal — computed from its foods."""
    r = compute([{"food": "idli", "grams": 160}, {"food": "sambar", "grams": 150},
                 {"food": "coconut_chutney", "grams": 30}])
    assert r["unknown"] == []
    assert 330 <= r["nutrition"]["calories"] <= 400
    # The macros reproduce the energy they claim (Atwater 4/4/9) within rounding
    # and the fibre the label omits.
    n = r["nutrition"]
    assert n["protein_g"] * 4 + n["carbs_g"] * 4 + n["fat_g"] * 9 == pytest.approx(
        n["calories"], rel=0.12)


def test_an_unknown_food_is_reported_not_guessed():
    r = compute([{"food": "moong_dal_yellow", "grams": 150}, {"food": "unicorn", "grams": 50}])
    assert r["unknown"] == ["unicorn"]
    meal = apply_to_meal({"components": [{"food": "unicorn", "grams": 50}]})
    assert meal["nutrition_basis"] == "partial"


def test_portion_text_is_written_from_the_grams():
    text = portion_text([{"food": "moong_dal_yellow", "grams": 150}, {"food": "ghee", "grams": 5},
                         {"food": "salt", "grams": 1}, {"food": "milk_full_fat", "grams": 200}])
    assert "150 g (1 katori)" in text and "5 g (1 tsp)" in text and "200 ml (1 glass)" in text
    assert "Salt" not in text


@pytest.mark.parametrize("fid,grams,expected", [
    ("almonds", 10, "8 almonds"), ("roti_whole_wheat", 80, "2 rotis"),
    ("ghee", 15, "1 tbsp"), ("dates", 24, "3 dates"), ("basmati_rice", 225, "1.5 katori"),
])
def test_household_measures(fid, grams, expected):
    assert household(fid, grams) == expected


def test_scaling_moves_the_food_and_leaves_the_seasoning():
    out = scale([{"food": "basmati_rice", "grams": 150}, {"food": "salt", "grams": 1}], 1.4)
    assert out[0]["grams"] == 210 and out[1]["grams"] == 1


def test_the_vegan_and_allergen_flags_on_the_extras():
    assert not EXTRAS["honey"]["vegan"]
    assert "gluten" in EXTRAS["wheat_flour_atta"]["allergens"]
    assert "peanuts" in EXTRAS["groundnut_oil"]["allergens"]
    assert "salt" in SEASONINGS
