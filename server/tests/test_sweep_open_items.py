"""The three items the 2026-10-18 live sweep left open.

1. A medicine's dose named its own vehicle ("with warm milk") above the patient's
   Anupana, which had been changed to warm water for a dairy allergy.
2. GERD was served the IBS / Grahani yoga protocol: practice after a meal, with
   belly compression first, and Downward Dog in every Surya Namaskar.
3. The diet arc told a hypothyroid patient Brimhana was withheld for Prameha,
   Medoroga and Kushtha, and opened a Tikshna-Agni reflux patient on warming spices.
"""
import json
import re

import pytest

from routes.export import handoff_plan_data
from services.diet_plan_arc import choose_arc
from services.remedy_engine import _MEDICINES_KB, _dose_without_vehicle, generate_medicines_plan
from services.yoga_plan_engine import _PROTOCOL_MAP, generate_yoga_plan
from tests.test_sweep_findings import MEDICINES_PLAN, _doc

_VEHICLE_WORDS = r"\b(milk|honey|ghee|buttermilk|coconut water|rose water|mishri|jaggery|cream)\b"


# ── 1. The dose and the Anupana ───────────────────────────────────────────────

@pytest.mark.parametrize("med", _MEDICINES_KB, ids=lambda m: m["id"])
def test_no_catalogue_dose_keeps_a_vehicle_once_stripped(med):
    for key in ("dosage", "dosage_pediatric"):
        dose = med.get(key) or ""
        out = _dose_without_vehicle(dose)
        if "diluted" in dose or "with equal" in dose:
            continue
        assert not re.search(_VEHICLE_WORDS, out, re.I), (key, dose, out)
        # The amount survives: everything before the vehicle is kept as written.
        assert out.startswith(dose.split(" with ")[0].strip()), (dose, out)


@pytest.mark.parametrize("dose", [
    "10–15ml diluted with 45ml warm water before food",
    "15–30ml with equal water after meals",
    "External use; 5ml oral with guidance",
])
def test_dilutions_and_supervision_are_kept(dose):
    assert _dose_without_vehicle(dose) == dose


def test_a_dairy_allergy_sees_no_milk_in_the_dose():
    plan = generate_medicines_plan(
        dict(id="t", age=45, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
             medical_history=["insomnia", "anxiety"], current_medications=[], allergies=["dairy"]),
        {}, [])
    meds = plan["primary_formulations"] + plan["supporting_formulations"]
    assert meds
    for m in meds:
        assert not re.search(r"\bmilk\b", m["dosage"], re.I), (m["name"], m["dosage"])
    for slot in plan["dosage_schedule"]:
        for line in slot["medicines"]:
            assert line.count("with ") <= 1 or "diluted" in line or "equal" in line, line


def test_a_stored_plan_reaches_the_handoff_without_the_catalogue_vehicle():
    data, _ = handoff_plan_data([_doc("medicines", {"medicines": MEDICINES_PLAN}, 0)])
    [item] = data["medicines"]
    assert item["dosage"] == "3–5g twice daily"
    assert item["anupana"].startswith("warm water")


# ── 2. Acid reflux has its own yoga protocol ─────────────────────────────────

_REFLUX = dict(age=40, gender="female", dominant_dosha="pitta")


@pytest.mark.parametrize("cond", ["acid_reflux", "gerd", "heartburn", "acidity"])
def test_reflux_reaches_the_reflux_protocol_not_ibs(cond):
    assert _PROTOCOL_MAP[cond]["id"] == "acid_reflux_protocol"


def test_ibs_aliases_no_longer_carry_reflux():
    ibs = next(p for p in _PROTOCOL_MAP.values() if p["id"] == "ibs_specific_protocol")
    assert not {"gerd", "acid_reflux", "heartburn"} & set(ibs["alternate_conditions"])


@pytest.mark.parametrize("time_of_day", ["morning", "evening"])
def test_a_reflux_plan_contains_no_excluded_pose_or_breath(time_of_day):
    proto = _PROTOCOL_MAP["acid_reflux"]
    plan = generate_yoga_plan({**_REFLUX, "medical_history": ["acid_reflux"]},
                              {"yoga_experience": "intermediate", "time_of_day_preference": time_of_day},
                              None, None)
    text = json.dumps(plan)
    banned = proto["avoid_pose_ids"] + proto["avoid_pranayama_ids"]
    assert not [b for b in banned if f'"{b}"' in text]
    assert all(c["protocol_name"].startswith("Acid Reflux") for c in plan["condition_protocols"])


def test_surya_namaskar_stays_for_a_patient_whose_protocol_allows_it():
    plan = generate_yoga_plan({**_REFLUX, "medical_history": []},
                              {"yoga_experience": "beginner", "time_of_day_preference": "morning"},
                              None, None)
    assert plan["weekly_schedule"][0]["session"].get("surya_namaskar")


# ── 3. The diet arc cites what the patient has, and does not heat Pitta ─────

def _arc(**profile):
    return choose_arc({"bmi_category": "normal", "ama_indicator": "none", **profile}, {})


def test_hypothyroid_is_not_told_about_diseases_it_does_not_have():
    arc = _arc(medical_history=["hypothyroid"], agni_type="sama")
    note = " ".join(arc["withheld"])
    for absent in ("Prameha", "Medoroga", "Kushtha"):
        assert absent not in note
    assert "modern extrapolation" in note
    assert "Medoroga" not in json.dumps(arc["weeks"])


def test_a_diabetic_still_gets_the_classical_citation():
    arc = _arc(medical_history=["diabetes_type2"], bmi_category="obese", agni_type="manda")
    assert "Prameha" in " ".join(arc["withheld"])
    assert "Kushtha" not in " ".join(arc["withheld"])


@pytest.mark.parametrize("profile", [
    dict(medical_history=["hypothyroid", "acid_reflux"], agni_type="tikshna"),
    dict(medical_history=["acid_reflux"], agni_type="sama"),
    dict(medical_history=[], agni_type="tikshna"),
    dict(medical_history=["acid_reflux"], agni_type="sama", ama_indicator="high"),
])
def test_a_sharp_or_pitta_provoked_agni_is_never_kindled_with_heat(profile):
    arc = _arc(**profile)
    weeks = json.dumps(arc["weeks"]).lower()
    assert "agni deepana" not in weeks
    assert "warming spices" not in weeks
    assert "ginger, ajwain" not in weeks
    assert any("Heating Deepana" in w for w in arc["withheld"])


def test_a_dull_agni_keeps_its_kindling():
    arc = _arc(medical_history=[], agni_type="manda")
    assert arc["weeks"][0]["phase"] == "Agni Deepana"
    assert not any("Heating Deepana" in w for w in arc["withheld"])
