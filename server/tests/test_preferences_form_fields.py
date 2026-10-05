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
    src = _MODAL.read_text()
    body = src[src.index("const renderFormFields"):]
    # `case 'remedies':` falls through to `case 'medicines':`, so both share a block.
    parts = re.split(r"\n\s*case '([a-z]+)':", body)
    fields: dict[str, set[str]] = {}
    pending: list[str] = []
    for i in range(1, len(parts), 2):
        name, block = parts[i], parts[i + 1]
        pending.append(name)
        found = set(re.findall(r'name="([a-z_]+)"', block))
        found |= set(re.findall(r"handleToggle\('([a-z_]+)'", block))
        found |= set(re.findall(r"form\.([a-z_]+)\b", block))
        if found:
            for feature in pending:
                fields[feature] = found
            pending = []
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


def test_the_herb_duplication_input_is_on_the_form_its_reader_saves():
    fields = _form_fields()
    assert "current_ayurvedic_medicines" in fields["panchakarma"]
    assert "current_ayurvedic_medicines" not in fields["remedies"]


def test_koshtha_survives_the_round_trip_the_engine_reads_it_through():
    """`plan_runner._load_feature_preferences` re-validates the saved document
    and hands the engine `model_dump()`. Koshtha was not declared, so a Mridu
    answer reached the engine as nothing, and it planned the patient as Sama."""
    from schemas.preferences_schema import PanchakarmaPreferences

    saved = PanchakarmaPreferences(koshtha="mridu", setting="clinic").model_dump()
    assert saved["koshtha"] == "mridu"
    with pytest.raises(ValueError):
        PanchakarmaPreferences(koshtha="loose")
