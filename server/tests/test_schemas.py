import pytest
from pydantic import ValidationError
from schemas.user_schema import DoshaQuizAnswers

def test_dosha_quiz_answers_valid():
    data = {"answers": {"q1": 1, "q2": 5, "q3": 3}}
    quiz = DoshaQuizAnswers(**data)
    assert quiz.answers["q1"] == 1
    assert quiz.answers["q2"] == 5

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
    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers={"q1": 6})
    assert "integer between 1 and 5" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers={"q1": 0})
    assert "integer between 1 and 5" in str(exc.value)

    with pytest.raises(ValidationError) as exc:
        DoshaQuizAnswers(answers={"q1": "3"}) # Pydantic might coerce, but if it doesn't meet the range it fails.
        # Actually Pydantic coercions string "3" to int 3, which is valid. So let's test a string that doesn't coerce to int or is out of bounds.
        DoshaQuizAnswers(answers={"q1": "abc"})
    assert "Input should be a valid integer" in str(exc.value) or "integer between 1 and 5" in str(exc.value)
