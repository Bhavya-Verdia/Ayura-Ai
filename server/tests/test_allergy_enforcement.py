"""Integration test: allergy exclusion in plan generation engines."""
import sys
import os

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from engine.condition_filter import condition_filter


def test_nut_allergy_excludes_nut_remedies():
    """Users with nut allergies must never receive nut-containing remedies."""
    user_profile = {
        "allergies": ["nuts", "peanuts"],
        "dominant_dosha": "vata",
        "age": 30,
        "gender": "female",
    }
    remedies = [
        {"id": "1", "name": "Almond Milk Turmeric", "ingredients": ["almond", "turmeric"], "tags": ["nuts"]},
        {"id": "2", "name": "Ginger Tea", "ingredients": ["ginger", "honey"], "tags": []},
        {"id": "3", "name": "Peanut Butter Snack", "ingredients": ["peanut butter"], "tags": ["peanuts"]},
        {"id": "4", "name": "Ashwagandha Milk", "ingredients": ["ashwagandha", "milk"], "tags": []},
    ]
    filtered = condition_filter.filter_by_allergies(user_profile, remedies)
    names = [r["name"] for r in filtered]

    assert "Almond Milk Turmeric" not in names, "nut-tagged item must be excluded"
    assert "Peanut Butter Snack" not in names, "peanut ingredient must be excluded"
    assert "Ginger Tea" in names
    assert "Ashwagandha Milk" in names


def test_dairy_allergy_excludes_dairy():
    user_profile = {"allergies": ["dairy", "lactose"], "dominant_dosha": "pitta"}
    remedies = [
        {"id": "1", "name": "Warm Milk Remedy", "ingredients": ["milk"], "tags": ["dairy"]},
        {"id": "2", "name": "Tulsi Tea", "ingredients": ["tulsi", "water"], "tags": []},
    ]
    filtered = condition_filter.filter_by_allergies(user_profile, remedies)
    names = [r["name"] for r in filtered]

    assert "Warm Milk Remedy" not in names
    assert "Tulsi Tea" in names


def test_no_allergies_returns_all_items():
    user_profile = {"allergies": [], "dominant_dosha": "kapha"}
    remedies = [
        {"id": "1", "name": "Almond Drink", "ingredients": ["almond"], "tags": ["nuts"]},
        {"id": "2", "name": "Ghee Remedy", "ingredients": ["ghee"], "tags": ["dairy"]},
    ]
    filtered = condition_filter.filter_by_allergies(user_profile, remedies)
    assert len(filtered) == 2


def test_gluten_allergy_excludes_wheat_items():
    user_profile = {"allergies": ["gluten"]}
    remedies = [
        {"id": "1", "name": "Wheat Bran Cereal", "ingredients": ["wheat bran", "oats"], "tags": ["gluten"]},
        {"id": "2", "name": "Rice Porridge", "ingredients": ["rice", "water"], "tags": []},
    ]
    filtered = condition_filter.filter_by_allergies(user_profile, remedies)
    names = [r["name"] for r in filtered]

    assert "Wheat Bran Cereal" not in names
    assert "Rice Porridge" in names
