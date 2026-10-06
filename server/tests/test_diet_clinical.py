"""What a dietitian writes beside the meals, and the fasts that are not planned.

The diet path read `current_medications` nowhere, and a 62-year-old diabetic on
warfarin and metformin was planned a fruit-only Monday at 1090 kcal.
"""
import pytest

from services.ahara_safety import _governed_by_avoidance
from services.diet_allowed_foods import allowed_foods, screen_foods
from services.diet_brief_builder import build_brief, fasting_days_for, fasting_withheld_reason
from services.diet_clinical_notes import (CONDITION_NOTES, MEDICATIONS, clinical_notes,
                                          medication_matches, screen_protocols)
from services.diet_energy import energy_target

_P = {"age": 40, "gender": "female", "height_cm": 160, "weight_kg": 60,
      "bmi_category": "normal", "activity_level": "moderate"}


@pytest.mark.parametrize("profile", [
    {**_P, "medical_history": ["diabetes_type2"]},
    {**_P, "medical_history": ["ckd"]},
    {**_P, "pregnancy_or_nursing": True},
    {**_P, "bmi_category": "underweight"},
    {**_P, "age": 15},
])
def test_no_planned_fast_where_a_fast_does_harm(profile):
    prefs = {"fasting_days": ["Monday"]}
    assert fasting_days_for(profile, prefs) == []
    assert fasting_withheld_reason(profile, prefs)
    assert "NO FAST" in build_brief(profile, prefs)


def test_a_healthy_adult_keeps_their_fast():
    assert fasting_days_for(_P, {"fasting_days": ["Monday"]}) == ["Monday"]
    assert fasting_withheld_reason(_P, {"fasting_days": ["Monday"]}) is None


@pytest.mark.parametrize("typed,key", [
    ("Warfarin 5mg", "warfarin"), ("Acitrom 2", "warfarin"), ("Thyronorm 50 mcg", "levothyroxine"),
    ("Glycomet SR 500", "metformin"), ("Amaryl 1", "hypoglycaemic"), ("insulin glargine", "hypoglycaemic"),
    ("Atorvastatin 10", "statin"), ("Telma 40", "potassium_raising"),
    ("spironolactone", "potassium_raising"), ("Lithium carbonate", "lithium"),
    ("Orofer XT", "iron"), ("Shelcal 500", "calcium"), ("linezolid", "maoi"),
])
def test_medicines_are_recognised_by_generic_and_indian_brand_names(typed, key):
    found, unmatched = medication_matches({"current_medications": [typed]})
    assert [m["key"] for m in found] == [key] and not unmatched


def test_an_unknown_medicine_is_reported_as_not_checked():
    _, unmatched = medication_matches({"current_medications": ["vitamin d3", "warfarin"]})
    assert unmatched == ["vitamin d3"]


def test_an_avoid_interaction_screens_the_food_out():
    """Tempeh is fermented soy — tyramine — and stays in the plan for anyone else."""
    profile = {**_P, "current_medications": ["phenelzine"]}
    assert "tempeh" not in {f["id"] for f in allowed_foods(profile, {})["allowed"]}
    assert "tempeh" in {f["id"] for f in allowed_foods(_P, {})["allowed"]}
    assert "med_maoi" in screen_protocols(profile)


def test_every_interaction_and_note_names_its_source():
    for key, row in MEDICATIONS.items():
        assert row[4], key
    for key, row in CONDITION_NOTES.items():
        assert row[2], key


def test_anaemia_in_pregnancy_is_told_to_keep_the_prescribed_iron():
    notes = clinical_notes({**_P, "pregnancy_or_nursing": True}, ["anemia"])
    text = " ".join(n["note"] for n in notes)
    assert "iron" in text and "folic" in text


def test_crohns_raises_protein_and_says_why():
    plain = energy_target({**_P, "medical_history": ["ibs"]}, {})
    crohns = energy_target({**_P, "medical_history": ["crohns disease"]}, {})
    assert crohns["protein_target_g"] >= round(60 * 1.2)
    assert crohns["protein_target_g"] > plain["protein_target_g"]
    assert any("ESPEN" in n for n in crohns["notes"])
    assert any(n["topic"].startswith("Crohn") for n in clinical_notes(
        {"medical_history": ["crohns disease"]}, ["ibs"]))


def test_gluten_free_is_not_a_recommendation_of_gluten():
    assert _governed_by_avoidance("This plan is strictly gluten-free.", "gluten")
    assert _governed_by_avoidance("A sugar free kheer.", "sugar")
    assert not _governed_by_avoidance("Feel free to have curd daily.", "curd")


# ── What the person will eat ─────────────────────────────────────────────────

def test_jain_removes_root_vegetables_honey_and_mushroom_but_not_raw_banana():
    excluded = allowed_foods({}, {"dietary_restrictions": ["jain"]})["excluded"]
    for food in ("onion", "garlic", "potato", "carrot", "beetroot", "honey", "mushroom",
                 "ginger", "sweet_potato"):
        assert food in excluded, food
    assert "raw_banana" not in excluded and "ginger_dry_saunth" not in excluded


def test_dislikes_typed_in_hindi_reach_the_library_name():
    excluded = allowed_foods({}, {"food_dislikes": ["lauki", "Bhindi", "karela"]})["excluded"]
    assert {"bottle_gourd", "okra_bhindi", "bitter_gourd_karela"} <= set(excluded)


def test_cuisine_and_restrictions_reach_the_brief():
    brief = build_brief(_P, {"cuisine_preference": "south_indian",
                             "dietary_restrictions": ["no_onion_garlic"],
                             "food_dislikes": ["mushroom"]})
    assert "South Indian" in brief and "NO ONION OR GARLIC" in brief and "mushroom" in brief


def test_the_form_offers_exactly_the_allergies_and_intolerances_the_server_enforces():
    """The form offered "Gluten Sensitivity", which no term list knew: declared and
    enforced by nothing. It did not offer mustard or histamine, which the server
    accepts."""
    import re
    from pathlib import Path

    from schemas.preferences_schema import FOOD_ALLERGIES, FOOD_INTOLERANCES
    from services.ahara_safety import ALLERGEN_TERMS

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "components" /
           "PreferencesModal.jsx").read_text()

    def chips(field):
        i = jsx.index(f"handleToggle('{field}'")
        block = jsx[jsx.rindex("{[", 0, i):i]
        return set(re.findall(r"value: '([a-z_]+)'", block))

    assert chips("food_allergies") <= FOOD_ALLERGIES
    assert chips("food_intolerances") == FOOD_INTOLERANCES
    for key in FOOD_ALLERGIES | FOOD_INTOLERANCES:
        assert key in ALLERGEN_TERMS, key
