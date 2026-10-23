"""What a person types about an injury reaches the gates however they type it.

"ankylosing spondylitis" typed into the injury box removed nothing in either engine:
the maps key it `ankylosing_spondylitis` and the typed phrase has a space. A live
profile read "ankylosing spondylytis" and the gym plan said, correctly, that it
could not act on it. Spinal flexion under load is what fractures an ankylosed spine.
"""

import pytest

from engine.movement_risk import condition_risk_tags, injury_risk_tags, respell
from services.gym_plan_engine import _resolve_injuries
from services.yoga_plan_engine import unmatched_limitations


@pytest.mark.parametrize("typed", ["ankylosing spondylitis", "Ankylosing Spondylitis",
                                   "ankylosing spondylytis", "ankylosing-spondylitis"])
def test_ankylosing_spondylitis_reaches_its_mechanism(typed):
    assert "spinal_flexion" in condition_risk_tags([typed])
    _, unmatched = _resolve_injuries({}, {"injury_detail": typed})
    assert unmatched == []
    assert unmatched_limitations({}, {"physical_limitations_detail": typed}) == []


@pytest.mark.parametrize("typed,word", [("glacoma", "glaucoma"), ("osteoporsis", "osteoporosis")])
def test_a_one_letter_slip_is_read_as_the_word(typed, word):
    assert respell(typed) == word
    assert condition_risk_tags([typed]) == condition_risk_tags([word])


@pytest.mark.parametrize("typed", ["pain everywhere", "running injury", "old surgery", "tired"])
def test_vague_words_are_still_said_back_rather_than_guessed(typed):
    _, unmatched = _resolve_injuries({}, {"injury_detail": typed})
    assert unmatched == [typed]
    assert not injury_risk_tags([typed])


def test_short_words_are_never_respelled():
    # "knee" and "neck" are one letter apart from little else, and a short word is
    # where a near miss is most often a different word.
    assert respell("knees neck hip") == "knees neck hip"


def test_no_dosha_tip_sends_anyone_into_a_cold_shower_after_training():
    """The Pitta tip said "Cool shower" beside the coaching's classical rule that
    bathing waits for Vishrama and cold water on the head straight after is out."""
    from services.gym_plan_engine import get_ayurvedic_tips

    for dosha in ("vata", "pitta", "kapha"):
        post = get_ayurvedic_tips(dosha)["post_workout"].lower()
        assert "cool shower" not in post and "cold shower," not in post, dosha
