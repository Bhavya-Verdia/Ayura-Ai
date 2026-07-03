import pytest
from pydantic import ValidationError
from schemas.user_schema import PhysicalTraitAnswers, UserProfileResponse


def test_profile_response_exposes_clinical_fields():
    """Regression: agni_type (+ ama/ojas) must be exposed by UserProfileResponse.
    These are computed and stored on the user, but if the response model omits a
    field, FastAPI silently drops it and the frontend never sees it."""
    fields = UserProfileResponse.model_fields
    for f in ("agni_type", "ama_indicator", "ojas_level", "ojas_score", "vikriti_dominant"):
        assert f in fields, f"UserProfileResponse must expose {f}"
    # Round-trips a real value rather than dropping it.
    resp = UserProfileResponse(id="u1", email="a@b.com", name="T", agni_type="tikshna")
    assert resp.agni_type == "tikshna"


def test_physical_traits_accept_single_and_blend():
    """The Prakriti assessment must accept a single dosha OR a 'primary+secondary'
    blend so users can express constitutional duality."""
    base = dict(
        body_frame="vata", skin="vata", digestion="pitta", sleep="vata",
        temperature="vata", hair="vata", energy="vata", stress_response="vata",
        memory="vata", decision_making="vata", speech="vata", emotional_nature="vata",
    )
    single = PhysicalTraitAnswers(**base)
    assert single.body_frame == "vata"

    blended = PhysicalTraitAnswers(**{**base, "body_frame": "vata+pitta", "agni_type": "kapha+pitta"})
    assert blended.body_frame == "vata+pitta"
    assert blended.agni_type == "kapha+pitta"


def test_physical_traits_reject_bad_values():
    base = dict(
        body_frame="vata", skin="vata", digestion="pitta", sleep="vata",
        temperature="vata", hair="vata", energy="vata", stress_response="vata",
        memory="vata", decision_making="vata", speech="vata", emotional_nature="vata",
    )
    with pytest.raises(ValidationError):
        PhysicalTraitAnswers(**{**base, "body_frame": "fire"})
    with pytest.raises(ValidationError):
        PhysicalTraitAnswers(**{**base, "body_frame": "vata+pitta+kapha"})
