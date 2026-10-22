"""
Every answer a preferences form collects must be one its feature's schema keeps.

The schemas do not forbid unknown fields, so a form field the schema does not
declare is accepted, returns 200 and is dropped on save. Nothing goes red, and the
form looks like it works.

That is what happened to `current_ayurvedic_medicines`. The Panchakarma engine
reads it to catch a herb the patient is already taking, but the field was put on
the remedies form, and `RemedyPreferences` does not declare it. Every answer was
dropped from 23 August, and the duplication check never had anything to compare.

Parsing JSX from Python is the same trade `test_dosha_instrument` makes: the form
and the schema are on opposite sides of the boundary with nothing shared between
them, so this is the one place they can be compared.
"""
import re
from pathlib import Path

import pytest

from routes.preferences import PREFERENCE_SCHEMAS

_MODAL = (Path(__file__).resolve().parents[2]
          / "client" / "src" / "components" / "PreferencesModal.jsx")

# Inputs the form edits in its own shape and folds into a schema field on submit.
_FORM_ONLY = {
    "gym": {"likes": "exercise_preferences", "dislikes": "exercise_preferences"},
}


def _form_fields() -> dict[str, set[str]]:
    """The modal's switch names the component each feature renders
    (`case 'gym': return <GymFields`); that component's file is the form."""
    src = _MODAL.read_text()
    body = src[src.index("const renderFormFields"):]
    # `case 'remedies':` falls through to `case 'medicines':`, so both share a form.
    fields: dict[str, set[str]] = {}
    for m in re.finditer(r"((?:\s*case '[a-z]+':)+)\s*return <(\w+)", body):
        block = (_MODAL.parent / "preferences" / f"{m.group(2)}.jsx").read_text()
        found = set(re.findall(r'name="([a-z_]+)"', block))
        found |= set(re.findall(r"handleToggle\('([a-z_]+)'", block))
        found |= set(re.findall(r"form\.([a-z_]+)\b", block))
        for feature in re.findall(r"case '([a-z]+)'", m.group(1)):
            fields[feature] = found
    return fields


def test_the_parser_sees_every_form():
    assert set(_form_fields()) == set(PREFERENCE_SCHEMAS)


@pytest.mark.parametrize("feature", sorted(PREFERENCE_SCHEMAS))
def test_every_field_a_form_collects_is_one_its_schema_keeps(feature):
    declared = set(PREFERENCE_SCHEMAS[feature].model_fields)
    folded = _FORM_ONLY.get(feature, {})
    dropped = {
        f for f in _form_fields()[feature]
        if f not in declared and folded.get(f) not in declared
    }
    assert not dropped, (
        f"the {feature} form collects {sorted(dropped)}, which its schema does not "
        "declare, so the answer is accepted and thrown away on save")


def test_the_herb_doubling_input_is_asked_wherever_herbs_are_prescribed():
    fields = _form_fields()
    for feature in ("panchakarma", "remedies", "medicines"):
        assert "current_ayurvedic_medicines" in fields[feature], feature


def test_koshtha_survives_the_round_trip_the_engine_reads_it_through():
    """`plan_runner._load_feature_preferences` re-validates the saved document
    and hands the engine `model_dump()`. Koshtha was not declared, so a Mridu
    answer reached the engine as nothing, and it planned the patient as Sama."""
    from schemas.preferences_schema import PanchakarmaPreferences

    saved = PanchakarmaPreferences(koshtha="mridu", setting="clinic").model_dump()
    assert saved["koshtha"] == "mridu"
    with pytest.raises(ValueError):
        PanchakarmaPreferences(koshtha="loose")


def test_a_select_shows_the_answer_it_saves():
    """A select whose value falls back to '' with no '' option displays its FIRST
    option while the modal saves a different default. The water-intake select showed
    "< 1L" and saved "1-2L"; Panchakarma showed 15 min of self-care and the plan was
    trimmed to 30. The fallback has to be an option the select has."""
    folder = _MODAL.parent / "preferences"
    bad = []
    for jsx in sorted(folder.glob("*.jsx")):
        src = jsx.read_text()
        for m in re.finditer(r"<select name=\"(\w+)\" value=\{form\.\w+ (?:\|\||\?\?) ''\}(.*?)</select>",
                             src, re.S):
            if 'value=""' not in m.group(2):
                bad.append(f"{jsx.name}: {m.group(1)}")
    assert not bad, f"these selects show one answer and save another: {bad}"
