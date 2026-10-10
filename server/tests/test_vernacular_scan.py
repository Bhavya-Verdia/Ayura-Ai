"""The gates are written in English; the prompt asks for Indian meal names.

`diet_llm_generator`'s system prompt says "Generate REAL Indian meal names", and
`_term_in_text` is a word match against English and Sanskrit terms. So the same food
was caught or missed depending on which name the model happened to reach for:

    curd -> caught        dahi  -> missed
    tamarind -> caught    imli  -> missed
    pickle -> caught      achar -> missed
    jaggery -> caught     gud   -> missed
    cabbage -> caught     patta gobhi -> missed

The library carries Sanskrit because its rows are named that way (`dadhi`), and the
curated tables carry English. Neither carried the Hindi-Urdu register the prompt
actually requests — the one a meal name is most likely to be written in.
"""

import pytest

from services.ahara_safety import (
    ALLERGEN_TERMS,
    _CONDITION_APATHYA_TERMS,
    _DIET_TYPE_FORBIDDEN,
    _VERNACULAR,
    _term_in_text,
    apply_ahara_safety,
    apply_condition_food_safety,
)
from services.diet_condition_foods import condition_food_rules, library_conditions


def _meal(name, ingredients):
    return {"diet_weeks": [{"week_number": 1, "daily_plan": {"Mon": {
        "lunch": {"meal_name": name, "key_ingredients": ingredients}}}}]}


def _flagged(name, ingredients, condition):
    out = apply_condition_food_safety(_meal(name, ingredients), [condition], {}, False)
    return sorted({a["food"] for a in out["condition_safety_alerts"]})


@pytest.mark.parametrize("condition,name,ingredients", [
    ("acidity", "Dahi Bhalla with imli chutney", ["dahi", "imli"]),
    ("acidity", "Achar with paratha", ["achar"]),
    ("acidity", "Sirka pyaaz", ["sirka"]),
    ("bloating", "Chole Bhature", ["chole"]),
    ("bloating", "Patta Gobhi ki Sabzi", ["patta gobhi"]),
    ("bloating", "Arbi ki Sabzi", ["arbi"]),
    ("bloating", "Rajma Chawal", ["rajma"]),
    ("diabetes", "Gud ki Kheer", ["gud"]),
    ("diabetes", "Aloo Paratha", ["aloo"]),
    ("hypothyroid", "Patta gobhi aur phool gobhi ki sabzi", ["patta gobhi"]),
    ("constipation", "Masoor dal tadka", ["masoor"]),
])
def test_the_vernacular_name_is_caught_like_the_english_one(condition, name, ingredients):
    assert _flagged(name, ingredients, condition), f"{name!r} passed for {condition}"


@pytest.mark.parametrize("condition,name,ingredients", [
    # Prescribed foods. A false positive withholds what the patient came to be given,
    # and is the worse of the two failures.
    ("bloating", "Mudga yusha with hing and ajwain", ["moong dal", "hing"]),
    ("bloating", "Lauki ki sabzi", ["lauki"]),
    ("acidity", "Narikela Jala (tender coconut water)", ["coconut water"]),
    ("diabetes", "Karela sabzi", ["karela"]),
    ("acidity", "Shali rice with ghee", ["rice", "ghee"]),
])
def test_a_permitted_food_is_not_withheld_by_its_indian_name(condition, name, ingredients):
    assert _flagged(name, ingredients, condition) == []


def test_the_allergen_scan_reads_the_vernacular_too():
    """`flag_allergens` and the Viruddha scan share `_meal_text`, so all three gates
    gain this at once — which is why the expansion lives there and not in one scan."""
    out = apply_ahara_safety(_meal("Dahi Bhalla", ["dahi"]), ["dairy"], [])
    assert out["allergen_safe"] is False


def test_expansion_appends_and_never_substitutes():
    """A term that already matched must not stop matching because a vernacular word
    was also present."""
    assert _flagged("Curd and dahi raita", ["curd", "dahi"], "acidity")
    assert _flagged("Curd raita", ["curd"], "acidity")


def test_no_vernacular_entry_is_inert():
    """Every canonical must be a word some gate actually holds, or the entry is
    decoration. `chole -> chickpeas` looked right and fired nothing, because the
    tables say `chana`. Thirteen entries were inert when this was first written."""
    vocab = set()
    for proto in _CONDITION_APATHYA_TERMS.values():
        vocab |= set(proto["terms"])
    for condition in library_conditions():
        vocab |= set(condition_food_rules(condition)["apathya_terms"])
    for terms in ALLERGEN_TERMS.values():
        vocab |= set(terms)
    for terms in _DIET_TYPE_FORBIDDEN.values():
        vocab |= set(terms)

    inert = sorted((v, c) for v, c in _VERNACULAR.items()
                   if not any(_term_in_text(t, c) for t in vocab))
    assert not inert, f"these map onto words no gate holds: {inert}"


def test_words_the_tables_exclude_on_purpose_stay_out():
    """`salt` is in every savoury meal, `tea` is the form half these medicines take,
    and `rice` and `lemon` are only Apathya in a named preparation. Mapping a
    vernacular word onto one of them would reintroduce through the back door exactly
    what the term tables were careful to keep out."""
    for excluded in ("salt", "tea", "rice", "lemon", "oil", "water"):
        assert excluded not in _VERNACULAR.values(), excluded


def test_the_longest_name_wins():
    """`patta gobhi` is cabbage and `phool gobhi` is cauliflower; matching a bare
    `gobhi` first would make them the same vegetable."""
    assert _flagged("Phool gobhi ki sabzi", ["phool gobhi"], "hypothyroid") == ["cauliflower"]
    assert _flagged("Patta gobhi ki sabzi", ["patta gobhi"], "hypothyroid") == ["cabbage"]


def test_no_vernacular_word_swallows_a_different_food():
    """`_term_regex` allows a suffix on purpose — "milk" has to match "milkshake" — so
    every short vernacular key swallows the longer words that start with it.

    Most of those are benign, because the longer word is the same food in Sanskrit:
    `badam`/`badama`, `palak`/`palakya`, `til`/`tila`, `chana`/`chanaka`. Two were not.
    `makhan` (butter) matched **makhana**, the fox nut this app prescribes as a light
    snack, and flagged a plain day of Chilla, Khichdi, Makhana and Lauki Sabzi as
    containing butter. `alu` (potato) matched **alubukhara**, a dried plum.

    A new entry that swallows a different food fails here and belongs in
    `_ALLERGEN_FALSE_FRIENDS` beside those two.
    """
    import json
    import re
    from pathlib import Path

    from services.ahara_safety import _ALLERGEN_FALSE_FRIENDS, _term_regex

    rows = json.loads((Path(__file__).resolve().parent.parent / "data"
                       / "knowledge_base" / "diet_foods.json").read_text(encoding="utf-8"))
    words = set()
    for row in rows:
        words |= set(re.findall(r"[a-z]+", row["name"].lower()))
        words |= set(row["id"].split("_"))
    words |= {w for key in _VERNACULAR for w in key.split()}
    # Dish words a meal name carries that the library does not.
    words |= {"makhana", "makhane", "makhani", "alubukhara", "tilkut", "chanachur",
              "khichdi", "kheer", "raita", "bhalla", "barfi", "laddu", "halwa",
              "dhokla", "sabzi", "tadka", "chutney", "kadhi", "pulao", "thepla"}

    # The longer word is the same food, usually its Sanskrit name.
    same_food = {
        ("badam", "badama"), ("palak", "palakya"), ("til", "tila"), ("til", "tilkut"),
        ("chana", "chanaka"), ("chana", "chanachur"), ("pista", "pistachios"),
        ("shakarkand", "shakarkandi"), ("alu", "aluka"),
    }

    bad = []
    for vern in _VERNACULAR:
        rx = _term_regex(vern)
        excused = _ALLERGEN_FALSE_FRIENDS.get(vern, frozenset())
        for word in words:
            if word == vern or word in excused:
                continue
            if rx.fullmatch(word) and (vern, word) not in same_food:
                bad.append((vern, word))
    assert not bad, (
        f"these vernacular keys match a different food: {sorted(bad)} — add the "
        f"longer word to _ALLERGEN_FALSE_FRIENDS, or narrow the key"
    )


def test_makhana_is_not_butter():
    """The regression itself, in the shape the guard test found it."""
    plan = _meal("Roasted Makhana with fennel", ["makhana"])
    out = apply_condition_food_safety(plan, ["gallstones"], {}, False)
    assert out["condition_food_safe"] is True, [
        a["food"] for a in out["condition_safety_alerts"]]
