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


# ── General guidelines: prose that used to pass no gate ──────────────────────

def test_dietary_guidance_is_gated_by_the_conditions_the_user_declared():
    """`build_remedy_plan` was handed the whole user profile and read only
    `dominant_dosha` from it, so the general guidelines were static per dosha.

    A diabetic was told to eat "sweet fruits" and someone with chronic kidney
    disease to drink "coconut water" — a potassium load. This engine already
    gates the remedy INGREDIENTS by condition (guggulu and honey withheld from a
    diabetic, salt from a hypertensive); only the prose beside them escaped.
    """
    from services.remedy_engine import build_remedy_plan

    def diet(dosha, history):
        plan = build_remedy_plan(
            [], {"id": "t", "dominant_dosha": dosha, "medical_history": history}, {})
        return plan["general_guidelines"]["diet_during_recovery"].lower()

    assert "sweet fruits" not in diet("pitta", ["type_2_diabetes"])
    assert "coconut water" not in diet("pitta", ["chronic_kidney_disease"])
    assert "spiced foods" not in diet("kapha", ["gerd"])
    assert "oily foods" not in diet("vata", ["gallstones"])

    # and an unaffected practitioner keeps the original guidance
    assert "coconut water" in diet("pitta", [])
    assert "sweet fruits" in diet("pitta", [])


def test_a_substitution_is_never_made_inside_the_avoid_clause():
    """Each guideline is "eat this. Avoid that." A term after "Avoid" is already
    being warned against, and substituting there inverts the advice — the first
    version of this gate produced "Avoid heavy, sweet, moist well-cooked foods
    with only a little ghee" for a Kapha with gallstones, which reads as a
    warning against the safer option."""
    from services.remedy_engine import build_remedy_plan

    plan = build_remedy_plan(
        [], {"id": "t", "dominant_dosha": "kapha",
             "medical_history": ["gallstones"]}, {})
    diet = plan["general_guidelines"]["diet_during_recovery"]
    assert diet == "Light, warm, spiced foods. Avoid heavy, sweet, oily foods."
    assert not plan["guideline_notices"]


def test_a_swapped_guideline_says_that_it_was_swapped():
    """Silently changing clinical guidance is its own problem."""
    from services.remedy_engine import build_remedy_plan

    plan = build_remedy_plan(
        [], {"id": "t", "dominant_dosha": "pitta",
             "medical_history": ["type_2_diabetes"]}, {})
    assert plan["guideline_notices"]
    assert "sweet fruits" in plan["guideline_notices"][0]
