"""The patient's medicines reach the procedures, not only the herbs.

`current_medications` was read by the herb-interaction gate and nothing else. A
patient on lithium was planned a purgation, one on warfarin an emesis, one on
clopidogrel a leech — each the same plan a person on no medicine received.
"""
import pytest

from services.panchakarma_engine import (
    _medication_findings,
    generate_panchakarma_plan,
    pk_clinical,
)

_CLASSES = {k for k in pk_clinical["medication_classes"] if not k.startswith("_")}


def _profile(**over):
    base = dict(id="t", age=40, gender="male", bmi=24, vikriti_dominant="pitta",
                fitness_level="advanced", medical_history=[], current_medications=[],
                ama_indicator="none", ojas_level="medium")
    base.update(over)
    return base


def _prefs(**over):
    base = dict(setting="clinic", available_time_days=14, detox_experience="some",
                panchakarma_goal="detox")
    base.update(over)
    return base


def _karma(plan):
    return plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]


@pytest.mark.parametrize("text,cls", [
    ("Warfarin 5mg", "anticoagulants"), ("Acitrom 2", "anticoagulants"),
    ("Ecosprin 75", "antiplatelets"), ("clopidogrel", "antiplatelets"),
    ("Lantus 20 units", "insulin_or_sulfonylurea"), ("Amaryl 1mg", "insulin_or_sulfonylurea"),
    ("Jardiance", "sglt2_inhibitors"), ("Lasix 40", "diuretics"),
    ("Telma 40", "antihypertensives"), ("Licab 300", "lithium"), ("Lanoxin", "digoxin"),
    ("Wysolone 10", "corticosteroids"), ("methotrexate weekly", "immunosuppressants"),
    ("Levipil 500", "antiepileptics"),
])
def test_generic_and_indian_brand_names_resolve(text, cls):
    assert cls in _medication_findings([text])["tokens"]


def test_an_unrecognised_medicine_is_listed_back_not_read_as_checked():
    found = _medication_findings(["vitamin d3", "Warfarin"])
    assert found["unmatched"] == ["vitamin d3"]
    plan = generate_panchakarma_plan(_profile(current_medications=["zyxolin 10mg"]), _prefs())
    review = plan["clinical_decisions"]["medication_review"]
    assert "zyxolin 10mg" in review["notice"]


def test_no_medicines_no_review():
    plan = generate_panchakarma_plan(_profile(), _prefs())
    assert plan["clinical_decisions"]["medication_review"] is None


def test_every_class_is_named_by_some_gate_and_every_gate_token_is_a_class():
    """A class no gate names is collected and ignored; a gate token naming a
    class that does not exist is a contraindication that can never fire."""
    named = set()
    for section in ("pradhana_karma", "therapies"):
        for entry in pk_clinical[section].values():
            if isinstance(entry, dict):
                for sev in ("hard", "soft"):
                    named |= set((entry.get(sev) or {}).keys())
    assessed = {k for k in _CLASSES if pk_clinical["medication_classes"][k].get("assessed_no_procedure_interaction")}
    assert _CLASSES - assessed <= named, (_CLASSES - assessed) - named
    # An assessed class must really gate nothing, or its stated reason is false.
    assert not (assessed & named), assessed & named


def test_lithium_withdraws_purgation_and_emesis():
    plan = generate_panchakarma_plan(_profile(current_medications=["Licab 300"]), _prefs())
    assert _karma(plan) not in ("virechana", "vamana")
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", current_medications=["lithium"]),
        _prefs(current_season="vasanta"))
    assert _karma(plan) != "vamana"


def test_an_anticoagulant_withdraws_emesis():
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", current_medications=["warfarin"]),
        _prefs(current_season="vasanta"))
    assert _karma(plan) != "vamana"


@pytest.mark.parametrize("med", ["warfarin", "clopidogrel", "methotrexate"])
def test_bloodletting_is_withdrawn_from_a_patient_who_cannot_close_or_defend_the_wound(med):
    prefs = _prefs(panchakarma_goal="seasonal_cleanse", current_season="grishma")
    assert _karma(generate_panchakarma_plan(_profile(medical_history=["psoriasis"]), prefs)) \
        == "raktamokshana"
    plan = generate_panchakarma_plan(
        _profile(medical_history=["psoriasis"], current_medications=[med]), prefs)
    assert _karma(plan) != "raktamokshana"


def test_insulin_is_a_caution_that_names_the_fast_and_the_prescriber():
    plan = generate_panchakarma_plan(_profile(current_medications=["insulin glargine"]), _prefs())
    assert _karma(plan) == "virechana"
    assert any("insulin_or_sulfonylurea" in w and "prescribing doctor" in w
               for w in plan["clinical_decisions"]["safety_warnings"])
    assert "insulin" in plan["clinical_decisions"]["medication_review"]["prescriber_notice"].lower()


def test_a_substitution_keeps_the_other_cautions():
    """Lithium forces a substitution; the insulin caution must still be stated."""
    plan = generate_panchakarma_plan(
        _profile(current_medications=["lithium", "insulin"]), _prefs())
    warnings = plan["clinical_decisions"]["safety_warnings"]
    assert any(w.startswith("SAFETY SUBSTITUTION") for w in warnings)
    assert any("insulin_or_sulfonylurea" in w for w in warnings)


def test_a_medication_changes_the_cache_key():
    """Medicines decide the Karma now, so a new one must regenerate the plan."""
    import inspect
    from routes.plan_runner import _check_plan_cache
    assert "current_medications" in inspect.getsource(_check_plan_cache)
