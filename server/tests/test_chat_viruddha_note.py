"""Chat is held to the diet plan's Viruddha rules.

Asked about "a banana milkshake with ashwagandha before bed", chat called banana
with milk "nourishing"; the diet plan's own scan flags that pair (Charaka
Sutrasthana 26)."""

from services.chat_service import chat_safety_notes, viruddha_safety_note


def test_a_pair_named_in_the_question_is_noted_when_the_reply_is_silent():
    note = viruddha_safety_note("Is a banana milkshake before bed good for sleep?",
                                "Banana with milk is nourishing and calming.")
    assert note and "milk with banana" in note.lower()


def test_a_reply_that_already_warns_is_left_alone():
    assert viruddha_safety_note("banana milkshake?",
                                "Banana and milk are Viruddha — an incompatible pair.") is None


def test_ordinary_food_talk_gets_no_note():
    assert viruddha_safety_note("What should I eat for lunch?",
                                "Rice with moong dal and a little ghee.") is None
    # Almond milk is not milk, and "lentil" holds no sesame.
    assert viruddha_safety_note("Almond milk with banana?", "Lentil soup is fine too.") is None


def test_both_notes_are_combined():
    out = chat_safety_notes("banana milkshake?", "Have it with ghee.", ["dairy"])
    assert "allergic" in out and "Viruddha" in out
