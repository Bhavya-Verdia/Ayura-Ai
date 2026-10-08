"""The diet screen's strings, held in step across the eight locales.

`DietView.jsx` is the source of the English (`scripts/diet_view_strings.py` reads it),
and i18next falls back to English for any key a locale lacks — silently. These keep
the locales complete, keep their placeholders intact (a dropped `{{floor}}` prints a
sentence with no number in it), and pin the two mistakes the first generated set made:
a Sanskrit "Ate it" that meant "not eaten", and breakfast and snack sharing one word.
"""
import json
import re

import pytest

from scripts.diet_view_strings import LOCALES, extract, placeholders

LANGS = ("hi", "kn", "ta", "sa", "es", "fr", "zh")
EN = json.loads((LOCALES / "en.json").read_text())["diet"]


def _diet(lang):
    return json.loads((LOCALES / f"{lang}.json").read_text()).get("diet") or {}


def test_en_json_is_what_the_screen_says():
    """Change a string in the JSX, then run `scripts/diet_view_strings.py --write`."""
    assert extract() == EN


@pytest.mark.parametrize("lang", LANGS)
def test_every_locale_has_every_string(lang):
    missing = sorted(set(EN) - set(_diet(lang)))
    assert not missing, f"{lang} would show English for: {missing}"


@pytest.mark.parametrize("lang", LANGS)
def test_placeholders_survive_translation(lang):
    bad = {k: v for k, v in _diet(lang).items() if k in EN and placeholders(v) != placeholders(EN[k])}
    assert not bad, bad


@pytest.mark.parametrize("lang", ["en", *LANGS])
def test_meal_labels_and_log_buttons_are_distinct(lang):
    d = EN if lang == "en" else _diet(lang)
    slots = [d[f"slot_{s}"] for s in ("breakfast", "lunch", "snack", "dinner", "special_drink")]
    buttons = [d[k] for k in ("logEaten", "logPartly", "logSkipped", "logSwapped")]
    assert len(set(slots)) == 5, slots
    assert len(set(buttons)) == 4, buttons


def test_sanskrit_ate_it_is_not_its_negation():
    """अभुक्तम् ("not eaten") was the first generated label for the eaten button."""
    assert _diet("sa")["logEaten"] == "भुक्तम्"
    assert not _diet("sa")["logEaten"].startswith("अ")


@pytest.mark.parametrize("lang", ["hi", "sa", "kn", "ta"])
def test_ayurvedic_terms_are_in_the_locale_script(lang):
    latin = re.compile(r"\b(Pathya|Apathya|Agni|Viruddha|Dosha|Dinacharya)\b")
    stray = {k: v for k, v in _diet(lang).items() if latin.search(v)}
    assert not stray, stray
