"""A Viruddha meal goes to repair like any other flagged meal.

`_scan` read Viruddha from the plan-level `viruddha_ahara_detected`, which carries no
week or day, so it never produced a key and no Viruddha meal was ever repaired. A live
plan served "Banana milk" in weeks 2 and 3 beside its own "Viruddha Ahara detected:
milk with banana" banner.
"""

from services.ahara_safety import scan_meal_for_viruddha
from services.diet_week_generator import _scan


def _plan(snack):
    return {"diet_weeks": [{"week_number": 2, "daily_plan": {"Friday": {"snack": snack}}}]}


def _found(snack):
    return _scan(_plan(snack), [], [], "vegetarian", [], {}, False)


def test_banana_with_cow_milk_is_sent_to_repair():
    found = _found({"meal_name": "Banana milk",
                    "description": "Ripe banana blended with warm milk and cardamom."})
    assert (2, "Friday", "snack") in found
    assert any("Milk with banana" in r for r in found[(2, "Friday", "snack")])


def test_almond_milk_is_not_milk():
    found = _found({"meal_name": "Banana Almond Bowl",
                    "description": "Ripe banana with soaked almonds and warm almond milk."})
    assert found == {}


def test_a_word_inside_another_word_is_not_that_food():
    # "til" (sesame) inside "lentil", "mula" (radish) inside "formula".
    assert scan_meal_for_viruddha({"meal_name": "Lentil soup with a glass of milk"}, "lunch") == []
    assert scan_meal_for_viruddha({"meal_name": "Milk made to the classic formula"}, "snack") == []


def test_real_combinations_still_fire():
    assert scan_meal_for_viruddha({"meal_name": "Til ladoo with warm milk"}, "snack")
    assert scan_meal_for_viruddha({"meal_name": "Kela milkshake"}, "snack")
