"""What a sweep of the medicines and home-remedy plans found.

Each test is a defect no existing test saw: 30 of 70 onboarding conditions reached
no formulation, a typed medicine name was checked against nothing, `allergies`
was matched as a word inside herb lists, a third of plans prescribed seven
formulations, a mercury tablet evaded the age gate on a type string, the
lifestyle lines and the AI narrative passed no gate, the "Shodhana indicated"
banner ignored the Panchakarma engine's eligibility, and a remedy caution was
written onto the shared KB and served to the next user.
"""
import json
import re
from pathlib import Path

import pytest

from services import remedy_engine as R
from services.remedy_engine import (
    _CONDITION_KB_TERMS,
    _MEDICINES_KB,
    _is_mineral,
    _med_covers_condition,
    build_remedy_plan,
    filter_remedies,
    generate_medicines_plan,
)
from services.remedy_enricher import gate_remedy_enrichment


def _p(**over):
    base = dict(id="t", age=45, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
                medical_history=[], current_medications=[], allergies=[])
    base.update(over)
    return base


def _names(plan):
    return [m["name"] for k in ("primary_formulations", "supporting_formulations", "external_therapies")
            for m in plan[k]]


def _internal(plan):
    return [m for k in ("primary_formulations", "supporting_formulations") for m in plan[k]]


# ── Every onboarding condition reaches the formulary, or is uncovered on purpose ──

# Left uncovered deliberately: a near match would be the wrong medicine.
_DELIBERATELY_UNCOVERED = {
    "multiple_sclerosis", "tinnitus", "vertigo", "bipolar", "atrial_fibrillation",
    "varicose_veins", "low_blood_pressure", "sleep_apnea", "gallstones", "celiac",
    "diabetes_type1", "hyperthyroidism", "rosacea", "lupus", "scleroderma",
}


def _onboarding_conditions():
    js = Path(__file__).resolve().parents[2] / "client" / "src" / "constants" / "conditions.js"
    return list(dict.fromkeys(re.findall(r"id: '([a-z_0-9]+)'", js.read_text())))


def test_every_onboarding_condition_reaches_a_formulation_or_is_left_out_on_purpose():
    reached = {c for c in _onboarding_conditions()
               if any(_med_covers_condition(m, R._CONDITION_ALIAS.get(c, c)) for m in _MEDICINES_KB)}
    unaccounted = set(_onboarding_conditions()) - reached - _DELIBERATELY_UNCOVERED
    assert not unaccounted, unaccounted
    # And the deliberate list is still deliberate — nothing in it reaches a formulation.
    assert not (reached & _DELIBERATELY_UNCOVERED), reached & _DELIBERATELY_UNCOVERED


def test_osteoarthritis_gets_joint_medicine_not_a_cough_powder():
    plan = generate_medicines_plan(_p(medical_history=["osteoarthritis"]), {}, [])
    assert plan["condition_coverage"] == "curated"
    assert any(_med_covers_condition(m, "osteoarthritis") for m in _internal(plan))
    assert "Sitopaladi Churna" not in _names(plan)


def test_ibs_is_not_sent_to_the_ibd_formulations():
    plan = generate_medicines_plan(_p(medical_history=["ibs"]), {}, [])
    for m in plan["primary_formulations"]:
        conds = [c.lower() for c in m["conditions"]]
        assert {"ibs", "irritable_bowel", "grahani"} & set(conds), m["name"]


def test_hyperthyroidism_never_reaches_the_thyroid_stimulating_entries():
    plan = generate_medicines_plan(_p(medical_history=["hyperthyroidism"]), {}, [])
    assert plan["uncovered_conditions"] == ["hyperthyroid"]
    assert not {"Kanchanara Guggulu", "Varanadi Kashayam", "Navaka Guggulu"} & set(_names(plan))


def test_every_authored_mapping_reaches_something():
    for cond, (terms, reason) in _CONDITION_KB_TERMS.items():
        assert reason, cond
        assert any(_med_covers_condition(m, cond) for m in _MEDICINES_KB), cond


# ── How many, and which kind ──────────────────────────────────────────────────

@pytest.mark.parametrize("conds", [["osteoarthritis"], ["rheumatoid_arthritis", "obesity", "diabetes_type2"],
                                   ["anxiety", "insomnia", "acid_reflux"], []])
def test_at_most_four_by_mouth_one_oil_one_guggulu_one_fermented(conds):
    for d in ("vata", "pitta", "kapha"):
        plan = generate_medicines_plan(_p(dominant_dosha=d, vikriti_dominant=d, medical_history=conds), {}, [])
        internal = _internal(plan)
        assert len(internal) <= 4
        assert len(plan["external_therapies"]) <= 1
        classes = [R._formulation_class(m) for m in internal if R._formulation_class(m)]
        assert len(classes) == len(set(classes)), [m["name"] for m in internal]


def test_wellness_support_is_a_rasayana_written_for_the_dosha():
    picks = {}
    for d in ("vata", "pitta", "kapha"):
        plan = generate_medicines_plan(_p(dominant_dosha=d, vikriti_dominant=d), {}, [])
        picks[d] = tuple(m["name"] for m in plan["supporting_formulations"])
        assert "Sitopaladi Churna" not in picks[d]
    assert len(set(picks.values())) == 3, picks


def test_a_condition_left_with_only_an_oil_says_so():
    plan = generate_medicines_plan(_p(dominant_dosha="pitta", vikriti_dominant="pitta",
                                      medical_history=["sciatica"]), {}, [])
    assert plan["external_only_conditions"] == ["sciatica"]
    assert "sciatica" in plan["coverage_note"] and plan["vaidya_review_required"]
    assert len(_internal(plan)) >= 1


# ── Mineral preparations ──────────────────────────────────────────────────────

def test_every_mercury_or_metal_preparation_is_recognised_as_mineral():
    by_name = {m["name"]: m for m in _MEDICINES_KB}
    for name in ("Shwas Kuthar Rasa", "Abhraka Bhasma", "Laghu Sootashekara Rasa", "Praval Pishti", "Loha Bhasma"):
        assert _is_mineral(by_name[name]), name
    assert not _is_mineral(by_name["Triphala Churna"])


@pytest.mark.parametrize("age", [10, 11, 75])
def test_no_mineral_preparation_for_a_child_or_an_elder(age):
    for d in ("vata", "kapha"):
        plan = generate_medicines_plan(_p(age=age, dominant_dosha=d, vikriti_dominant=d,
                                          medical_history=["asthma"]), {}, [])
        assert not any(_is_mineral(m) for m in _internal(plan))


# ── Typed medicines ───────────────────────────────────────────────────────────

def test_a_typed_anticoagulant_is_checked_like_the_form_option():
    typed = generate_medicines_plan(_p(medical_history=["osteoarthritis"], current_medications=["Acitrom 2"]), {}, [])
    assert not any("guggulu" in n.lower() or n == "Haridra Churna" for n in _names(typed))
    assert typed["medication_review"]["matched"][0]["classes"] == ["Anticoagulant"]


def test_an_unrecognised_medicine_is_listed_back():
    plan = generate_medicines_plan(_p(current_medications=["zyxolin"]), {}, [])
    assert plan["medication_review"]["unmatched"] == ["zyxolin"]


def test_a_typed_medicine_reaches_the_remedies_too():
    out = filter_remedies(_p(medical_history=[], current_medications=["Glycomet 500"]),
                          {"symptoms": ["joint_pain"]})
    blob = json.dumps(out).lower()
    assert "diabetes medication" in blob or "triphala" not in blob


# ── Allergies ─────────────────────────────────────────────────────────────────

def test_dairy_withholds_ghee_formulations_and_swaps_a_milk_anupana():
    plan = generate_medicines_plan(_p(dominant_dosha="pitta", vikriti_dominant="pitta",
                                      medical_history=["osteoarthritis"], allergies=["dairy"]), {}, [])
    for m in _internal(plan):
        assert not re.search(r"\b(milk|ghee)\b", m["selected_anupana"].lower()), m["name"]
    assert any("dairy" in b["reason"] for b in plan["blocked_medicines"])
    assert any(m.get("anupana_note") for m in _internal(plan))


def test_a_remedy_with_honey_in_its_method_is_not_given_to_a_diabetic():
    out = filter_remedies(_p(dominant_dosha="kapha", medical_history=["diabetes_type2"]),
                          {"symptoms": ["headache"]})
    served = [x["remedy"] for x in out if x.get("remedy")]
    # Served without honey, or referred — never served with it.
    assert served or any(x.get("action") == "consult_doctor" for x in out)
    assert not any("honey" in (r.get("preparation") or "").lower() for r in served)


def test_a_remedy_allergy_is_read_from_the_method_and_the_ingredients():
    out = filter_remedies(_p(allergies=["dairy"]), {"symptoms": ["constipation", "brain_fog"]})
    for x in out:
        if x.get("remedy"):
            text = json.dumps(x["remedy"]).lower()
            assert not re.search(r"\b(milk|ghee|butter)\b", text), x["symptom_id"]


# ── Shared state ──────────────────────────────────────────────────────────────

def test_a_remedy_caution_never_reaches_the_next_user():
    snapshot = json.dumps(R._REMEDIES_FALLBACK, sort_keys=True)
    filter_remedies(_p(medical_history=["hypothyroidism"]), {"symptoms": ["fatigue", "anxiety"]})
    after = filter_remedies(_p(), {"symptoms": ["fatigue", "anxiety"]})
    assert json.dumps(R._REMEDIES_FALLBACK, sort_keys=True) == snapshot
    assert "thyroid" not in json.dumps(after).lower()


def test_a_caution_belongs_to_the_remedy_served():
    out = filter_remedies(_p(medical_history=["hypothyroidism"]), {"symptoms": ["fatigue"]})
    for x in out:
        if x.get("caution_notes"):
            assert "ashwagandha" in json.dumps(x["remedy"]).lower()


# ── Lifestyle and Shodhana ────────────────────────────────────────────────────

def test_lifestyle_lines_follow_the_conditions_and_allergies():
    plan = generate_medicines_plan(_p(dominant_dosha="kapha", vikriti_dominant="kapha",
                                      medical_history=["diabetes_type2", "heart_disease"]), {}, [])
    lg = plan["lifestyle_guidance"]
    assert "Skip breakfast" not in lg["dietary_note"] and "Vigorous exercise" not in lg["routine_note"]
    assert len(lg["changed_for_you"]) == 3
    vata = generate_medicines_plan(_p(allergies=["dairy", "sesame"]), {}, [])["lifestyle_guidance"]
    assert "generous ghee" not in vata["dietary_note"] and "oil rather than ghee" in vata["dietary_note"]
    assert "sesame" not in vata["routine_note"]


def test_shodhana_is_the_panchakarma_engines_verdict():
    child = generate_medicines_plan(_p(age=10, dominant_dosha="kapha", vikriti_dominant="kapha",
                                       ama_indicator="high"), {}, [])
    assert child["shodhana_strength"] == "mridu" and "Vamana" in child["shodhana_withheld"]
    pregnant = generate_medicines_plan(_p(age=30, ama_indicator="high", pregnancy_or_nursing=True), {}, [])
    assert pregnant["chikitsa_approach"] == "Shamana" and pregnant["shodhana_withheld"]


# ── The narrative passes a gate ───────────────────────────────────────────────

def test_the_gate_holds_pathya_and_prose_to_the_plan():
    prof = _p(dominant_dosha="pitta", vikriti_dominant="pitta",
              medical_history=["osteoarthritis", "diabetes_type2"],
              current_medications=["warfarin"], allergies=["dairy"])
    plan = generate_medicines_plan(prof, {}, [])
    enr = {"pathya": ["Warm milk with turmeric at bedtime", "Bitter gourd and leafy greens",
                      "Sweet ripe mango"],
           "synergy_note": ("Yogaraj Guggulu clears Ama from the joints. Avoid ghee-heavy sweets. "
                            "Take a glass of warm milk at night.")}
    out, withheld = gate_remedy_enrichment(enr, plan, prof, ("pathya",))
    assert out["pathya"] == ["Bitter gourd and leafy greens"]
    assert out["synergy_note"] == "Avoid ghee-heavy sweets."
    assert len(withheld) == 4


def test_the_gate_leaves_agreeing_prose_alone():
    prof = _p(medical_history=["osteoarthritis"])
    plan = generate_medicines_plan(prof, {}, [])
    text = "Take the medicines after food with warm water. Rest the joints."
    out, withheld = gate_remedy_enrichment({"synergy_note": text}, plan, prof, ("pathya",))
    assert out["synergy_note"] == text and withheld == []


# ── Found by reading eight live plans whole ───────────────────────────────────

def test_pregnancy_gets_the_authored_pregnancy_alternative():
    out = filter_remedies(_p(dominant_dosha="pitta", pregnancy_or_nursing=True),
                          {"symptoms": ["acid_reflux", "nausea"]})
    assert all(x.get("pregnancy_alternative") for x in out), out
    assert "fennel" in out[0]["remedy"]["preparation"].lower()


def test_a_pregnancy_alternative_is_screened_like_any_remedy():
    out = filter_remedies(_p(dominant_dosha="pitta", pregnancy_or_nursing=True, allergies=["dairy"]),
                          {"symptoms": ["acid_reflux"]})          # "small amounts of cold milk"
    assert out[0].get("action") == "consult_doctor"


def test_an_unrecorded_second_dosha_is_not_assumed_to_be_pitta():
    out = filter_remedies(_p(dominant_dosha="kapha", medical_history=["diabetes_type2", "obesity"]),
                          {"symptoms": ["fatigue"]})
    assert all(x.get("dosha_used") in (None, "kapha", "universal") for x in out)


def test_no_airway_irritant_for_an_asthmatic():
    out = filter_remedies(_p(age=11, dominant_dosha="kapha", medical_history=["asthma"]),
                          {"symptoms": ["sinus_congestion", "cough_wet"]})
    text = json.dumps([x.get("remedy") for x in out]).lower()
    assert "eucalyptus" not in text and "sniff" not in text


def test_no_salt_anupana_with_hypertension_or_kidney_disease():
    plan = generate_medicines_plan(_p(age=74, gender="male", medical_history=["chronic_kidney_disease",
                                                                              "hypertension"]), {}, [])
    for m in _internal(plan):
        assert "salt" not in m["selected_anupana"].lower(), m["name"]


def test_shilajit_is_withheld_in_kidney_disease_by_the_herb_table():
    plan = generate_medicines_plan(_p(age=60, gender="male", medical_history=["chronic_kidney_disease"]), {}, [])
    assert "Shilajit" not in _names(plan)
    assert any(b["name"] == "Shilajit" and "GFR" in b["reason"] for b in plan["blocked_medicines"])


def test_every_condition_gets_a_formulation_before_any_gets_two():
    plan = generate_medicines_plan(_p(medical_history=["anxiety", "ibs"]), {}, [])
    internal = _internal(plan)
    assert any(_med_covers_condition(m, "anxiety") for m in internal)
    assert any(_med_covers_condition(m, "ibs") for m in internal)


def test_a_condition_whose_formulations_were_all_withheld_is_not_called_unmatched():
    plan = generate_medicines_plan(_p(dominant_dosha="kapha", vikriti_dominant="kapha",
                                      medical_history=["hypothyroidism", "pcos"],
                                      current_medications=["Thyronorm 75"]), {}, [])
    assert plan["withheld_conditions"] == ["hypothyroid"]
    assert "No formulation in our classical knowledge base" not in plan["coverage_note"]


def test_medicines_start_one_at_a_time():
    plan = generate_medicines_plan(_p(medical_history=["osteoarthritis"]), {}, [])
    assert "one formulation at a time" in plan["treatment_protocol"]["week_1_2"]


def test_the_remedies_read_the_same_drug_herb_map_as_the_medicines():
    out = filter_remedies(_p(current_medications=["clonazepam"]), {"symptoms": ["anxiety"]})
    assert "ashwagandha" not in json.dumps([x.get("remedy") for x in out]).lower()


def test_narrative_in_a_script_the_gate_cannot_read_is_not_served():
    prof = _p(medical_history=["pcos"])
    plan = generate_medicines_plan(prof, {}, [])
    out, withheld = gate_remedy_enrichment({"dose_note": "अग्नि सम है, इसलिए औषधि को सामान्य मात्रा से शुरू करें।"},
                                           plan, prof, ("pathya",))
    assert out["dose_note"] == "" and "Devanagari" in withheld[0]["reason"]


# ── Herb x medicine: the documented interactions withhold, by herb ─────────────

@pytest.mark.parametrize("typed,herbs", [
    ("Licab 300", {"punarnava", "gokshura"}),            # lithium
    ("Lanoxin", {"yashtimadhu"}),                         # digoxin
    ("Wysolone 10", {"yashtimadhu"}),                     # prednisolone
    ("Pangraf 1mg", {"pippali", "maricha"}),              # tacrolimus — piperine, CYP3A4
    ("Eptoin 100 phenytoin", {"shankhpushpi"}),
    ("clonazepam", {"jatamansi", "tagara", "sarpagandha", "ashwagandha", "brahmi"}),
])
def test_a_documented_interaction_is_never_served(typed, herbs):
    for d in ("vata", "pitta", "kapha"):
        for cond in ("osteoarthritis", "anxiety", "kidney_stones", "asthma", "obesity"):
            plan = generate_medicines_plan(_p(dominant_dosha=d, vikriti_dominant=d, medical_history=[cond],
                                              current_medications=[typed]), {}, [])
            for m in _internal(plan):
                assert not (R._active_herbs(m) & herbs), (typed, m["name"])


def test_no_arishta_with_metronidazole():
    plan = generate_medicines_plan(_p(medical_history=["ibs"], current_medications=["Flagyl 400"]), {}, [])
    assert not any(R._formulation_class(m) == "fermented" for m in _internal(plan))


def test_a_moderate_interaction_is_served_with_its_mechanism():
    plan = generate_medicines_plan(_p(medical_history=["osteoarthritis"], current_medications=["warfarin"]), {}, [])
    cautions = [c for m in _internal(plan) for c in m["usage_cautions"]]
    assert any("anticoagulant" in c for c in cautions)


def test_the_form_chips_reach_the_herb_table():
    plan = generate_medicines_plan(_p(medical_history=["anxiety"]),
                                   {"current_allopathic_medications": ["sedatives"]}, [])
    assert not any(R._active_herbs(m) & {"jatamansi", "tagara", "ashwagandha", "brahmi"} for m in _internal(plan))


# ── What a formulation is made of ─────────────────────────────────────────────

def test_no_mercury_or_copper_preparation_is_self_served():
    for cond in ("fatty_liver", "asthma", "obesity"):
        plan = generate_medicines_plan(_p(medical_history=[cond]), {}, [])
        assert "Arogyavardhini Vati" not in _names(plan)
        assert not any("parada" in json.dumps(m).lower() for m in _internal(plan))


@pytest.mark.parametrize("age", [13, 16, 17])
def test_no_alcohol_based_preparation_under_18(age):
    for cond in ("menorrhagia", "acne_severe", "ibs", "anemia"):
        plan = generate_medicines_plan(_p(age=age, medical_history=[cond]), {}, [])
        assert not any(R._formulation_class(m) == "fermented" for m in _internal(plan))


def test_no_alcohol_based_preparation_in_liver_disease():
    plan = generate_medicines_plan(_p(medical_history=["fatty_liver"]), {}, [])
    assert not any(R._formulation_class(m) == "fermented" for m in _internal(plan))


def test_no_sugar_based_jam_for_a_diabetic():
    for d in ("vata", "pitta", "kapha"):
        plan = generate_medicines_plan(_p(dominant_dosha=d, vikriti_dominant=d,
                                          medical_history=["diabetes_type2", "anemia"]), {}, [])
        for m in _internal(plan):
            assert not any(k in m["type"].lower() for k in ("avaleha", "gulam", "pak", "khanda")), m["name"]


def test_no_purgative_herb_in_ulcerative_colitis():
    plan = generate_medicines_plan(_p(medical_history=["ulcerative_colitis", "acid_reflux"]), {}, [])
    assert not any(R._active_herbs(m) & {"trivrit", "danti"} for m in _internal(plan))


# ── Age bands ─────────────────────────────────────────────────────────────────

def test_lower_end_parses_every_range_shape():
    assert R._lower_end("3–5g with warm water") == "3g with warm water"
    assert R._lower_end("1–2 tablets twice daily") == "1 tablet twice daily"
    assert R._lower_end("500mg–1g with water") == "500mg with water"
    assert R._lower_end("250mg") == "250mg"


@pytest.mark.parametrize("age,basis", [(13, "adolescent"), (15, "adolescent"), (80, "older adult")])
def test_adolescents_and_the_old_start_at_the_bottom_of_the_range(age, basis):
    plan = generate_medicines_plan(_p(age=age, medical_history=["acid_reflux"]), {}, [])
    lowered = [m for m in _internal(plan) if (m.get("dosage_basis") or "").startswith(basis)]
    assert lowered
    for m in lowered:
        assert m["dosage"] != m["dosage_adult"]


def test_a_sedating_herb_after_65_carries_the_falls_caution():
    plan = generate_medicines_plan(_p(age=70, medical_history=["insomnia"]), {}, [])
    sedating = [m for m in _internal(plan) if R._active_herbs(m) & R._SEDATING_HERBS]
    assert sedating and all(any("falls" in c for c in m["usage_cautions"]) for m in sedating)


# ── Season ────────────────────────────────────────────────────────────────────

def test_the_season_moves_the_choice_by_virya():
    hot = generate_medicines_plan(_p(current_season="grishma"), {}, [])
    cold = generate_medicines_plan(_p(current_season="hemanta"), {}, [])
    assert all(m["virya"].lower() == "sheeta" for m in hot["supporting_formulations"])
    assert all(m["virya"].lower() == "ushna" for m in cold["supporting_formulations"])


def test_an_unset_season_comes_from_the_calendar():
    plan = generate_medicines_plan(_p(current_season=None), {}, [])
    assert plan["current_season"] in {"vasanta", "grishma", "varsha", "sharad", "hemanta", "shishira"}


# ── Found by the second live read ─────────────────────────────────────────────

def test_a_herb_named_like_a_metal_is_not_withheld_as_one():
    """'naga' sits inside Nagakeshara and 'vanga' inside Lavanga."""
    by_name = {m["name"]: m for m in _MEDICINES_KB}
    for n in ("Avipattikar Churna", "Kutajarishta"):
        bar, _ = R._formulation_rule_findings(by_name[n], [], 40, set())
        assert not (bar or "").startswith("Prescribed in person"), n
    bar, _ = R._formulation_rule_findings(by_name["Manasamitra Vatakam"], [], 40, set())
    assert bar.startswith("Prescribed in person")            # Naga Bhasma is lead


def test_no_aloe_in_heavy_menstrual_bleeding():
    plan = generate_medicines_plan(_p(dominant_dosha="pitta", vikriti_dominant="pitta",
                                      medical_history=["endometriosis", "menorrhagia"]), {}, [])
    assert not any("kumari" in R._active_herbs(m) for m in _internal(plan))


def test_no_calcium_supplement_for_a_stone_former():
    plan = generate_medicines_plan(_p(medical_history=["kidney_stones", "insomnia"]), {}, [])
    assert not {"Praval Pishti", "Mukta Pishti"} & set(_names(plan))


def test_no_arishta_for_an_older_adult_on_a_sleeping_pill():
    plan = generate_medicines_plan(_p(age=82, gender="male", medical_history=["constipation_chronic"],
                                      current_medications=["zolpidem"]), {}, [])
    assert not any(R._formulation_class(m) == "fermented" for m in _internal(plan))


def test_the_shodhana_banner_asks_the_whole_panchakarma_engine():
    plan = generate_medicines_plan(_p(age=47, dominant_dosha="kapha", vikriti_dominant="kapha",
                                      medical_history=["chronic_kidney_disease", "diabetes_type2"],
                                      current_medications=["Pangraf 1mg", "Wysolone 5"],
                                      ama_indicator="high"), {}, [])
    assert plan["shodhana_strength"] != "full"
    assert plan["shodhana_withheld"]
