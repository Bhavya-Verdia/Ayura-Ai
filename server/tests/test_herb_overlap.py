"""
A herb the patient already takes, prescribed again inside a formulation.

Panchakarma checked for this and the medicines plan, which prescribes the most
formulations, did not. Both now use `engine.herb_overlap`. These tests pin
three things:

* the matcher reads what people type
* it stays quiet on the carriers half the formulations are made in
* a medicine declared on either form reaches both engines
"""
import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from engine.herb_overlap import already_taking, declared_ayurvedic, herbs_in
from services.remedy_engine import _MEDICINES_KB, generate_medicines_plan


@pytest.mark.parametrize("typed, herb", [
    ("Ashwagandha Churna", "ashwagandha"),
    ("ASHWAGANDHA churna 5g", "ashwagandha"),
    ("Ashwagandharishta", "ashwagandha"),   # the preparation fused onto the herb
    ("Brahmi Ghrita", "brahmi"),            # the ghee is the vehicle
    ("giloy juice", "guduchi"),             # Hindi name
    ("Amritarishta", "guduchi"),            # classical synonym, fused
    ("Shankhpushpi tab", "shankhapushpi"),  # the PK KB's spelling vs the medicine KB's
    ("Dry ginger powder", "shunthi"),
])
def test_what_people_type_is_read_as_the_herb(typed, herb):
    assert herb in herbs_in(typed)


def test_a_compound_is_read_as_what_is_in_it():
    assert herbs_in("Triphala") == {"amalaki", "bibhitaki", "haritaki"}
    assert {"pippali", "maricha", "shunthi"} <= herbs_in("Trikatu churna")


@pytest.mark.parametrize("typed", ["a", "ghee", "honey", "sesame oil", "jaggery", "",
                                   "Other herbs", "1 tsp twice daily"])
def test_nothing_that_names_no_herb_matches_anything(typed):
    """The Panchakarma matcher compared substrings in both directions, so a one
    letter entry was "in" every herb name it was compared against."""
    assert not herbs_in(typed)
    for med in _MEDICINES_KB:
        assert not already_taking(med["ingredients"], [typed]), (typed, med["name"])


def test_a_ghrita_is_not_flagged_against_every_formulation_made_in_ghee():
    ghee_based = [m for m in _MEDICINES_KB
                  if any(i.lower().startswith("ghee") for i in m["ingredients"])]
    assert ghee_based
    for med in ghee_based:
        hits = already_taking(med["ingredients"], ["Brahmi Ghrita"])
        assert all("Ghee" not in h for hit in hits for h in hit["herbs"]), med["name"]


def test_triphala_overlaps_a_formulation_containing_haritaki():
    tri = next(m for m in _MEDICINES_KB if m["name"] == "Triphala Churna")
    hits = already_taking(tri["ingredients"], ["Haritaki", "Brahmi Ghrita", "triphala 1 tsp"])
    assert [h["already_taking"] for h in hits] == ["Haritaki", "triphala 1 tsp"]
    assert len(hits[1]["herbs"]) == 3


def _plan(taking):
    profile = {"id": "u", "age": 40, "gender": "female", "dominant_dosha": "vata",
               "vikriti_dominant": "vata", "medical_history": ["arthritis", "insomnia"]}
    prefs = {"ingredient_access": "full_access", "current_allopathic_medications": [],
             "current_ayurvedic_medicines": taking}
    return generate_medicines_plan(profile, prefs, [])


def _formulations(plan):
    return (plan["primary_formulations"] + plan["supporting_formulations"]
            + plan["external_therapies"])


def test_the_medicines_plan_flags_a_herb_already_being_taken():
    baseline = _formulations(_plan([]))
    assert all(not m["already_taking"] for m in baseline)
    # Take the lead herb of the first prescribed formulation, as a patient would type it.
    target = baseline[0]
    lead = target["ingredients"][0].split(" (")[0]
    flagged = {m["name"]: m["already_taking"] for m in _formulations(_plan([f"{lead} churna"]))}
    assert flagged[target["name"]], (target["name"], lead)
    note = flagged[target["name"]][0]["note"]
    assert "doubles" in note and target["name"] in note


def test_flagged_is_not_withheld():
    """Usually the fix is to stop the one being taken on their own. That is the
    patient's and the Vaidya's call, so the plan states it and changes nothing."""
    baseline = [m["name"] for m in _formulations(_plan([]))]
    lead = _formulations(_plan([]))[0]["ingredients"][0].split(" (")[0]
    assert [m["name"] for m in _formulations(_plan([lead]))] == baseline


def test_either_form_reaches_both_engines():
    doc = {
        "panchakarma": {"current_ayurvedic_medicines": ["Ashwagandha Churna"]},
        "remedies": {"current_ayurvedic_medicines": ["Triphala", "ashwagandha churna"]},
    }
    assert declared_ayurvedic(doc) == ["Ashwagandha Churna", "Triphala"]
    assert declared_ayurvedic({}) == []
    assert declared_ayurvedic({"remedies": {"current_ayurvedic_medicines": None}}) == []


@pytest.mark.parametrize("plan_type", ["panchakarma", "remedies", "medicines"])
def test_the_holistic_path_merges_them_too(plan_type):
    from routes.plan_runner import _load_feature_preferences

    db = MagicMock()
    db.user_preferences.find_one = AsyncMock(return_value={
        "panchakarma": {"current_ayurvedic_medicines": ["Brahmi Ghrita"]},
        "remedies": {"current_ayurvedic_medicines": ["Triphala"]},
    })
    prefs = asyncio.run(_load_feature_preferences(db, "u", plan_type))
    assert prefs["current_ayurvedic_medicines"] == ["Brahmi Ghrita", "Triphala"]
