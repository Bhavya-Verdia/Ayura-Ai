"""
Regression tests for the home-remedies engine.

Locks in two demo-hardening fixes:
  - filter_remedies has a bundled-JSON fallback, so it works even when the
    Mongo kb_ayurvedic_remedies collection is unseeded.
  - every symptom the onboarding picker can emit resolves to a remedy (the
    onboarding labels didn't match the KB's clinical symptom_ids, so ~half
    silently returned nothing until the alias map was added).
"""
import pytest

from services.remedy_engine import filter_remedies, _REMEDIES_FALLBACK

# Mirror of client/src/pages/Onboarding.jsx `SYMPTOMS`. Keep in sync — this test
# fails loudly if a new onboarding symptom has no remedy mapping.
ONBOARDING_SYMPTOMS = [
    "acidity", "bloating", "constipation", "insomnia", "joint_pain", "fatigue",
    "anxiety", "dry_skin", "skin_rash", "weight_gain", "hair_loss",
    "irregular_periods", "headache", "cough", "cold",
]

_PROFILE = {
    "dominant_dosha": "vata", "secondary_dosha": "pitta",
    "medical_history": [], "allergies": [], "current_medications": [],
}


def test_remedies_fallback_is_loaded():
    """The offline fallback KB must be present (so remedies never silently empty
    when Mongo is unseeded)."""
    assert len(_REMEDIES_FALLBACK) >= 50
    assert all(r.get("symptom_id") for r in _REMEDIES_FALLBACK)


@pytest.mark.parametrize("symptom", ONBOARDING_SYMPTOMS)
def test_every_onboarding_symptom_yields_a_remedy(symptom):
    results = filter_remedies(_PROFILE, {"symptoms": [symptom]})
    actionable = [r for r in results if r.get("action") != "see_doctor"]
    assert actionable, f"onboarding symptom '{symptom}' resolved to no remedy"


def test_unknown_symptom_degrades_safely():
    """An unmapped symptom must not crash — it just yields nothing."""
    assert filter_remedies(_PROFILE, {"symptoms": ["totally_unknown_xyz"]}) == []
