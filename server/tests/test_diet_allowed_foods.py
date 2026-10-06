"""The foods a plan is composed from pass the same scans the finished plan does.

Sixteen live plans shipped meals their own scans had flagged, as a note: a vegan
given ghee 34 times, a coeliac gluten 15 times. The list the model chooses from is
now screened first, by the same functions.
"""
from services.ahara_safety import _term_in_text
from services.diet_allowed_foods import allowed_foods, screen_foods
from services.diet_nutrition import _library


def _ids(profile, prefs):
    r = allowed_foods(profile, prefs)
    return {f["id"] for f in r["allowed"]}, r["excluded"]


def test_a_vegan_keeps_the_plant_proteins_and_loses_the_dairy():
    allowed, excluded = _ids({}, {"dietary_type": "vegan"})
    for plant in ("soy_milk", "almond_milk", "oat_milk", "coconut_yogurt",
                  "vegan_paneer_tofu", "tofu_firm"):
        assert plant in allowed, plant
    for dairy in ("ghee", "paneer", "milk_full_fat", "curd_yogurt", "honey"):
        assert dairy not in allowed, dairy


def test_a_dairy_allergy_keeps_plant_milk_and_a_nut_allergy_does_not():
    allowed, _ = _ids({"allergies": ["dairy"]}, {})
    assert "soy_milk" in allowed and "milk_full_fat" not in allowed
    allowed, _ = _ids({"allergies": ["dairy", "nuts_tree"]}, {})
    assert "almond_milk" not in allowed and "soy_milk" in allowed


def test_coeliac_loses_wheat_and_keeps_rice_flakes():
    """Poha is flattened rice; the gluten list named it."""
    allowed, excluded = _ids({"allergies": ["gluten"]}, {})
    assert "poha" in allowed and "rice_flakes" in allowed
    for wheat in ("roti_whole_wheat", "wheat_flour_atta", "maida", "semolina_rava", "vermicelli"):
        assert wheat in excluded, wheat


def test_condition_apathya_reaches_the_list():
    _, excluded = _ids({"medical_history": ["diabetes_type2"]}, {})
    assert "sugar" in excluded and "jaggery" in excluded


def test_an_extra_is_screened_by_its_own_allergen_tag():
    excluded = screen_foods([{"id": "groundnut_oil", "name": "Cooking oil (refined)"}],
                            allergies=["peanuts"], intolerances=[], dietary_type="vegetarian",
                            conditions=[])
    assert "groundnut_oil" in excluded


def test_a_healthy_vegetarian_keeps_nearly_the_whole_library():
    allowed, excluded = _ids({}, {"dietary_type": "vegetarian"})
    assert len([f for f in allowed if f in _library()]) >= 145, sorted(excluded)


def test_plant_qualified_dairy_words_are_not_dairy():
    assert not _term_in_text("milk", "soy milk porridge")
    assert not _term_in_text("paneer", "vegan paneer tikka")
    assert not _term_in_text("butter", "peanut butter")
    assert _term_in_text("milk", "warm cow milk")
    assert _term_in_text("butter", "buttermilk")
