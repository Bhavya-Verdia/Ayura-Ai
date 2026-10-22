"""Every locale holds the app's screen strings (`ui`) in the same shape as English.

`client/scripts/i18n-strings.mjs` writes en.json's `ui` from the `tr()` and `<Trans>`
calls in the source (and `npm run lint` fails if it is stale); `scripts/translate_ui.py`
fills the other seven. A translation that loses a {{placeholder}} prints the raw
braces, and one that loses a <0>…</0> tag drops a link or the bold word, so both are
checked for every string in every locale.
"""
import json
import re
from pathlib import Path

import pytest

LOCALES = Path(__file__).resolve().parents[2] / "client" / "src" / "locales"
LANGS = ("hi", "kn", "ta", "sa", "es", "fr", "zh")
_PH = re.compile(r"\{\{\s*(\w+)\s*\}\}")
_TAG = re.compile(r"</?\d+/?>")


def _flat(tree, prefix=""):
    out = {}
    for k, v in tree.items():
        if isinstance(v, dict):
            out.update(_flat(v, f"{prefix}{k}."))
        else:
            out[f"{prefix}{k}"] = v
    return out


EN = _flat(json.loads((LOCALES / "en-ui.json").read_text())["ui"])


def test_english_is_not_empty():
    assert len(EN) > 1500


@pytest.mark.parametrize("lang", LANGS)
def test_every_string_is_translated(lang):
    got = _flat(json.loads((LOCALES / f"{lang}.json").read_text()).get("ui") or {})
    missing = sorted(set(EN) - set(got))
    # A handful may fall back to English; more than that is a translation run not done.
    assert len(missing) <= 10, f"{lang}: {len(missing)} missing, e.g. {missing[:5]}"
    assert not set(got) - set(EN), f"{lang}: keys English no longer has"


@pytest.mark.parametrize("lang", LANGS)
def test_placeholders_and_tags_survive(lang):
    got = _flat(json.loads((LOCALES / f"{lang}.json").read_text()).get("ui") or {})
    bad = [k for k, v in got.items()
           if set(_PH.findall(v)) != set(_PH.findall(EN[k]))
           or sorted(_TAG.findall(v)) != sorted(_TAG.findall(EN[k]))]
    assert not bad, f"{lang}: {bad[:5]}"


@pytest.mark.parametrize("lang", ("hi", "sa"))
def test_vegetarian_is_never_vegan(lang):
    got = _flat(json.loads((LOCALES / f"{lang}.json").read_text()).get("ui") or {})
    for k, v in got.items():
        if "vegetarian" in EN[k].lower() and "vegan" not in EN[k].lower():
            assert "वीगन" not in v, (k, v)


def test_no_english_value_is_spliced_into_a_sentence():
    """A sentence assembled from English words picked by a condition ("{{value}}" =
    "suggestions", "were") cannot be translated: the words stay English. Plurals are
    written as two whole sentences instead."""
    src = Path(__file__).resolve().parents[2] / "client" / "src"
    spliced = re.compile(r"(?:tr\('ui|<Trans )[^;]*?\b\w+: [^,}]*\? '[A-Za-z][^'(]*' : '[^']*'")
    hits = [f"{p.relative_to(src)}: {m.group(0)[-80:]}"
            for p in src.rglob("*.js*") for m in spliced.finditer(p.read_text())
            if "style={{" not in m.group(0)]
    assert not hits, hits[:5]
