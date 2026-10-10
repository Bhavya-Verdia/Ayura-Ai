"""An allergy declared once is honoured everywhere.

The app stores an allergy in two places — `user_profile["allergies"]`, from
onboarding's health step, and `diet_prefs["food_allergies"]`, from the diet form.

The diet path read only the second. The remedies filter, the chat agent's system
prompt and the Vaidya PDF export read only the first — and no screen collected it, so
it was `null` for all twelve users in production and those three had never once seen
an allergy. (A first count said eleven users had one; that was `{"$ne": []}` matching
nulls. Counted with `$size`, it is zero.)

Worse than absent: `filter_by_allergies` matched by substring, and the canonical keys
the app stores do not survive that — `"nuts_tree" in "tree nuts"` is False in both
directions, so a declared tree-nut allergy matched an almond by no route at all.
"""

import pytest

from engine.condition_filter import condition_filter
from services.ahara_safety import apply_ahara_safety
from services.diet_brief_builder import build_brief, diet_allergies

_PROFILE = {
    "dominant_dosha": "vata", "agni_type": "sama", "age": 30, "gender": "female",
    "height_cm": 162, "weight_kg": 55, "activity_level": "moderate",
    "bmi_category": "normal", "medical_history": [],
}


def _prefs(**over):
    base = {
        "dietary_type": "vegetarian", "diet_goal": "general_wellness",
        "food_allergies": [], "food_intolerances": [], "gut_health_issue": "healthy",
        "intermittent_fasting": "no", "water_intake": "2-3L", "fasting_days": [],
    }
    base.update(over)
    return base


def test_both_places_are_read():
    prof = {**_PROFILE, "allergies": ["peanuts", "Dairy"]}
    assert diet_allergies(prof, _prefs(food_allergies=["gluten"])) == [
        "gluten", "peanuts", "dairy"
    ]


def test_it_is_a_union_and_never_a_choice():
    """An allergy is the one declaration where asking twice and honouring one answer
    is not acceptable."""
    prof = {**_PROFILE, "allergies": ["peanuts"]}
    assert diet_allergies(prof, _prefs(food_allergies=[])) == ["peanuts"]
    assert diet_allergies(_PROFILE, _prefs(food_allergies=["peanuts"])) == ["peanuts"]


def test_the_same_allergy_in_both_places_is_carried_once():
    prof = {**_PROFILE, "allergies": ["dairy"]}
    assert diet_allergies(prof, _prefs(food_allergies=["dairy"])) == ["dairy"]


def test_a_profile_allergy_reaches_the_brief():
    """The brief's ALLERGIES line is the model's only instruction about it."""
    prof = {**_PROFILE, "allergies": ["peanuts"]}
    brief = build_brief(prof, _prefs(food_allergies=[]))
    assert "ALLERGIES (absolutely avoid): peanuts" in brief


def test_a_profile_allergy_reaches_the_deterministic_meal_scan():
    """The reported shape, from #61: a declared allergy and a meal that names it, on a
    plan reporting `allergen_safe: True` with zero alerts."""
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "special_drink": {"name": "Badam Milk with Saffron",
                          "recipe": "warm cow's milk with soaked almonds"}}}}]}
    prof = {**_PROFILE, "allergies": ["nuts_tree", "dairy"]}
    out = apply_ahara_safety(plan, diet_allergies(prof, _prefs()), [])
    assert out["allergen_safe"] is False
    assert out["safety_alerts"]


@pytest.mark.parametrize("declared,withheld", [
    ("nuts_tree", True),    # the key that substring matching could never resolve
    ("dairy", True),
    ("peanuts", False),     # an almond is not a peanut
])
def test_the_remedies_filter_resolves_a_canonical_allergy_key(declared, withheld):
    items = [{"name": "Badam Milk", "ingredients": ["almonds", "milk"], "tags": []}]
    kept = condition_filter.filter_by_allergies({"allergies": [declared]}, items)
    assert (kept == []) is withheld


def test_the_remedies_filter_still_honours_free_text():
    """The raw string is kept beside the expansion, so an entry that is not a
    canonical key keeps working."""
    items = [{"name": "Tulsi Kadha", "ingredients": ["tulsi", "black pepper"], "tags": []}]
    assert condition_filter.filter_by_allergies({"allergies": ["tulsi"]}, items) == []


def test_no_declared_allergy_withholds_nothing():
    items = [{"name": "Badam Milk", "ingredients": ["almonds"], "tags": []}]
    for profile in ({"allergies": []}, {"allergies": None}, {}):
        assert condition_filter.filter_by_allergies(profile, items) == items


def test_the_onboarding_vocabulary_matches_the_schema():
    """One vocabulary across the two forms, or the union above silently degrades into
    two free-text lists that only substring matching can reconcile."""
    import re
    from pathlib import Path

    from schemas.preferences_schema import FOOD_ALLERGIES

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "pages"
           / "Onboarding.jsx").read_text(encoding="utf-8")
    block = re.search(r"const FOOD_ALLERGIES = \[(.*?)\]", jsx, re.S)
    assert block, "Onboarding.jsx no longer declares a FOOD_ALLERGIES list"
    collected = set(re.findall(r"id:\s*'([a-z_]+)'", block.group(1)))
    assert collected == FOOD_ALLERGIES, (
        f"onboarding collects {sorted(collected)}; the schema accepts "
        f"{sorted(FOOD_ALLERGIES)}"
    )
