"""The special drink is not a second bedtime drink."""

from services.diet_week_generator import WEEK_PROMPT, _ritual_line


def test_the_week_prompt_names_the_fixed_drinks():
    line = _ritual_line([{"slot": "wake_up", "name": "Water with soaked raisins"},
                         {"slot": "bedtime", "name": "Cool milk with cardamom and fennel"}])
    assert "Cool milk with cardamom and fennel" in line
    assert "never on waking or at bedtime" in line
    assert "{rituals}" in WEEK_PROMPT


def test_no_fixed_drinks_adds_nothing():
    """Inside an eating window there is no bedtime drink, and nothing to avoid."""
    assert _ritual_line([]) == ""
