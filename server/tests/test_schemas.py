import pytest
from pydantic import ValidationError
from schemas.user_schema import DoshaQuizAnswers, UserProfileResponse


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

def test_dosha_quiz_answers_valid():
    data = {"answers": {f"q{i}": (i%5)+1 for i in range(10)}}
    quiz = DoshaQuizAnswers(**data)
    assert quiz.answers["q0"] == 1
    assert quiz.answers["q1"] == 2

def test_dosha_quiz_answers_empty():
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers={})
    assert "cannot be empty" in str(exc.value)

def test_dosha_quiz_answers_too_many():
    data = {"answers": {f"q{i}": 3 for i in range(35)}}
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(**data)
    assert "Too many answers" in str(exc.value)

def test_dosha_quiz_answers_invalid_values():
    data = {f"q{i}": 3 for i in range(10)}

    data_bad_val = data.copy()
    data_bad_val["q1"] = 6
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers=data_bad_val)
    assert "integer between 1 and 5" in str(exc.value)

    data_zero = data.copy()
    data_zero["q1"] = 0
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers=data_zero)
    assert "integer between 1 and 5" in str(exc.value)

    data_str = data.copy()
    data_str["q1"] = "abc"
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers=data_str)
    assert "Input should be a valid integer" in str(exc.value) or "integer between 1 and 5" in str(exc.value)
