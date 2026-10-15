"""What a sweep over every onboarding condition, common medicine and allergy found.

Each test here is a defect a 3,000-plan sweep surfaced and no existing test saw:
the ghee ladder ran past the Snehapana gate, Type 1 diabetes was planned emesis,
`allergies` was read by no Panchakarma code, seven everyday medicines were reported
as unchecked, Agni did not touch the Snehapana dose, a Ghrita was named on 82% of
plans that never use it, and the model's narrative reached the patient ungated.
"""
import random
import re
from pathlib import Path

import pytest

from engine.condition_vocab import condition_matches_term
from services.panchakarma_engine import (
    _SHODHANA_ABSOLUTE_CONTRA,
    _allergen_review,
    _medication_findings,
    generate_panchakarma_plan,
    pk_clinical,
)
from services.panchakarma_enricher import gate_enrichment


def _profile(**over):
    base = dict(id="t", age=40, gender="female", bmi=23, weight_kg=60, vikriti_dominant="pitta",
                fitness_level="advanced", medical_history=[], current_medications=[],
                ama_indicator="none", ojas_level="medium")
    base.update(over)
    return base


def _prefs(**over):
    base = dict(setting="clinic", available_time_days=14, detox_experience="some",
                panchakarma_goal="detox", self_care_time_per_day="1 hour")
    base.update(over)
    return base


def _karma(plan):
    return plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]


def _ladder(plan):
    return [d["dose_ml"] for d in plan["snehana_protocol"]["dose_schedule"]]


# ── The Snehapana ladder passes the Snehapana gate ────────────────────────────

@pytest.mark.parametrize("dosha", ["pitta", "kapha"])
@pytest.mark.parametrize("condition", ["gallstones"])
def test_a_barred_snehapana_withdraws_the_karma_it_prepares(dosha, condition):
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant=dosha, medical_history=[condition]),
        _prefs(current_season="vasanta" if dosha == "kapha" else "sharad"))
    assert _karma(plan) not in ("vamana", "virechana")
    assert _ladder(plan) == []
    assert any(condition in w for w in plan["clinical_decisions"]["safety_warnings"])


def test_pancreatitis_takes_no_ghee_whichever_gate_stops_it():
    """Unrecognised by the vocabulary, so triage fails closed to Shamana — no ladder."""
    plan = generate_panchakarma_plan(_profile(medical_history=["acute_pancreatitis"]), _prefs())
    assert _ladder(plan) == []


def test_a_correctable_state_on_the_snehapana_row_does_not_bar_the_karma():
    """high_ama and manda_agni are on the Snehapana row; Deepana corrects them first."""
    plan = generate_panchakarma_plan(_profile(ama_indicator="high", agni_type="manda"), _prefs())
    assert _karma(plan) == "virechana"
    assert _ladder(plan)


def test_snehapana_cautions_reach_the_karma_warnings():
    plan = generate_panchakarma_plan(_profile(medical_history=["obesity"], bmi=33), _prefs())
    assert any("Snehapana" in w and "obesity" in w
               for w in plan["clinical_decisions"]["safety_warnings"])


def test_type_1_diabetes_is_never_planned_emesis():
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", medical_history=["diabetes_type1"]),
        _prefs(current_season="vasanta"))
    assert _karma(plan) != "vamana"


@pytest.mark.parametrize("condition", ["inguinal hernia", "hernia"])
def test_a_hernia_is_never_planned_emesis(condition):
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", medical_history=[condition]),
        _prefs(current_season="vasanta"))
    assert _karma(plan) != "vamana"


@pytest.mark.parametrize("condition", ["multiple_sclerosis", "rosacea", "heart_disease"])
def test_heat_sensitive_conditions_caution_the_steam(condition):
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata", medical_history=[condition]),
                                     _prefs())
    sweda = [t for d in plan["daily_schedule"] for t in d["therapies"]
             if "sweda" in (t.get("id") or "")]
    assert sweda and all(any(c["condition"] == condition for c in t.get("cautions") or [])
                         for t in sweda)


def test_menorrhagia_bars_bloodletting():
    hard = pk_clinical["pradhana_karma"]["raktamokshana"]["hard"]
    assert "menorrhagia" in hard


# ── Agni sets the Matra ───────────────────────────────────────────────────────

@pytest.mark.parametrize("agni,cap", [("manda", 60), ("vishama", 90)])
def test_agni_caps_the_snehapana_peak(agni, cap):
    plan = generate_panchakarma_plan(_profile(agni_type=agni), _prefs(available_time_days=21))
    assert _ladder(plan) and max(_ladder(plan)) <= cap
    assert plan["snehana_protocol"]["matra"]["agni"] == agni


def test_tikshna_agni_keeps_the_full_ladder():
    sama = generate_panchakarma_plan(_profile(agni_type="sama"), _prefs(available_time_days=21))
    tik = generate_panchakarma_plan(_profile(agni_type="tikshna"), _prefs(available_time_days=21))
    assert _ladder(tik) == _ladder(sama)


def test_the_step_down_never_exceeds_the_peak():
    plan = generate_panchakarma_plan(_profile(age=10, weight_kg=22), _prefs(available_time_days=21))
    lad = _ladder(plan)
    if len(lad) >= 3:
        assert lad[-1] <= max(lad[:-1])
        assert lad[-1] % 5 == 0


# ── A medicine is named only when a schedule uses it ──────────────────────────

@pytest.mark.parametrize("dosha,setting", [("vata", "home"), ("vata", "clinic"), ("kapha", "home")])
def test_no_ghrita_on_a_course_that_takes_no_snehapana(dosha, setting):
    plan = generate_panchakarma_plan(_profile(vikriti_dominant=dosha), _prefs(setting=setting))
    assert _karma(plan) in ("basti", "basti_matra", "nasya")
    assert "internal_ghrita" not in plan["aushadha"]


# ── Allergies ─────────────────────────────────────────────────────────────────

def _allergy_items(plan, label):
    review = plan["clinical_decisions"]["allergen_review"] or {}
    return next((f["items"] for f in review.get("findings", []) if f["allergy"] == label), [])


def test_dairy_allergy_flags_the_ghee_and_the_ghrita():
    plan = generate_panchakarma_plan(_profile(allergies=["dairy"]), _prefs())
    items = " ".join(_allergy_items(plan, "Dairy"))
    assert "Snehapana ghee" in items and "Ghrita" in items
    assert plan["clinical_decisions"]["safety_warnings"][0].startswith("ALLERGY:")


def test_sesame_allergy_flags_the_enema_oil_but_not_a_mustard_base():
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata", allergies=["sesame"]),
                                     _prefs(setting="home"))
    assert any("Basti" in i for i in _allergy_items(plan, "Sesame"))
    review = _allergen_review(["sesame"], {"x": {"name": "Sarshapa Taila (Mustard)"}}, [], [])
    assert review["findings"] == []


def test_honey_allergy_flags_the_niruha():
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata", allergies=["honey"]),
                                     _prefs())
    assert _karma(plan) == "basti"
    assert any("Niruha" in i for i in _allergy_items(plan, "Honey"))


def test_an_unrecognised_allergy_is_listed_back():
    plan = generate_panchakarma_plan(_profile(allergies=["penicillin"]), _prefs())
    assert plan["clinical_decisions"]["allergen_review"]["unrecognised"] == ["penicillin"]


def test_an_allergy_given_as_a_string_is_not_read_letter_by_letter():
    review = _allergen_review("dairy", {"x": {"name": "Tila Taila"}}, [], [])
    assert review["unrecognised"] == [] and review["findings"] == []


def test_no_allergies_no_review():
    plan = generate_panchakarma_plan(_profile(), _prefs())
    assert plan["clinical_decisions"]["allergen_review"] is None


# ── Everyday medicines are recognised ─────────────────────────────────────────

@pytest.mark.parametrize("text,cls", [
    ("Metformin 500", "metformin"), ("Glycomet SR", "metformin"),
    ("Thyronorm 50mcg", "thyroid_hormone"), ("levothyroxine", "thyroid_hormone"),
    ("oral contraceptive pill", "hormonal_contraceptives"), ("Yasmin", "hormonal_contraceptives"),
    ("sertraline", "ssri_snri"), ("Nexito 10", "ssri_snri"),
    ("ibuprofen", "nsaids"), ("Combiflam", "nsaids"),
    ("atorvastatin 10", "statins"), ("Pantocid 40", "acid_suppressants"),
])
def test_everyday_medicines_resolve(text, cls):
    assert cls in _medication_findings([text])["tokens"]


def test_a_medicine_with_no_procedure_interaction_needs_no_prescriber_notice():
    plan = generate_panchakarma_plan(_profile(current_medications=["atorvastatin"]), _prefs())
    review = plan["clinical_decisions"]["medication_review"]
    assert review["unmatched"] == [] and review["prescriber_notice"] is None


def test_metformin_cautions_a_purgation():
    plan = generate_panchakarma_plan(_profile(current_medications=["metformin"]), _prefs())
    assert _karma(plan) == "virechana"
    assert any("metformin" in w.lower() for w in plan["clinical_decisions"]["safety_warnings"])


# ── Every condition onboarding offers was assessed ────────────────────────────

def _onboarding_conditions():
    js = Path(__file__).resolve().parents[2] / "client" / "src" / "constants" / "conditions.js"
    return list(dict.fromkeys(re.findall(r"id: '([a-z_0-9]+)'", js.read_text())))


def test_every_onboarding_condition_is_gated_or_assessed():
    """A condition no entry names is indistinguishable from one nobody looked at."""
    tokens = set(_SHODHANA_ABSOLUTE_CONTRA)
    for section in ("pradhana_karma", "therapies", "herbs"):
        for entry in pk_clinical[section].values():
            if isinstance(entry, dict):
                for sev in ("hard", "soft"):
                    tokens |= set((entry.get(sev) or {}).keys())
                for terms in (entry.get("restrict_to") or {}).values():
                    tokens |= set(terms)
    assessed = set(pk_clinical["assessed_no_contraindication"]) - {"_note"}
    conditions = _onboarding_conditions()
    assert len(conditions) > 60
    missing = [c for c in conditions
               if c not in assessed and not any(condition_matches_term(c, t) for t in tokens)]
    assert not missing, missing


# ── The narrative passes a gate ───────────────────────────────────────────────

def test_the_gate_withholds_a_deferred_karma_an_allergen_and_an_overdose():
    plan = generate_panchakarma_plan(_profile(agni_type="manda", allergies=["dairy"]), _prefs())
    assert plan["clinical_decisions"]["secondary_karma_deferred"]["karma"] == "raktamokshana"
    text = ("Begin each morning with warm ghee. On day 5 you will take 120 ml of Tikta Ghrita. "
            "After Virechana, a session of Raktamokshana will clear the blood. "
            "Raktamokshana is not part of this plan; discuss it with your Vaidya.")
    gated, withheld = gate_enrichment({"daily_guidance": text, "x": ["Drink milk at night."]}, plan)
    assert gated["daily_guidance"] == "Raktamokshana is not part of this plan; discuss it with your Vaidya."
    assert gated["x"] == []
    assert len(withheld) == 4


def test_the_gate_withholds_snehapana_and_niruha_from_a_matra_basti_course():
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata"), _prefs(setting="home"))
    assert _karma(plan) == "basti_matra"
    gated, withheld = gate_enrichment(
        {"x": "Snehapana with 30 ml ghee prepares you. The Matra Basti oil is retained "
              "overnight. Niruha Basti follows on day 9."}, plan)
    assert gated["x"] == "The Matra Basti oil is retained overnight."
    assert {w["reason"] for w in withheld} == {
        "this Karma takes no Snehapana", "Basti — this course is Matra Basti only"}


def test_the_gate_leaves_an_agreeing_narrative_alone():
    plan = generate_panchakarma_plan(_profile(), _prefs())
    text = "Virechana clears Pitta from the Pakvashaya. Rest on the Karma day."
    gated, withheld = gate_enrichment({"x": text}, plan)
    assert gated["x"] == text and withheld == []


# ── Structural invariants over a sample of the input space ────────────────────

def test_structural_invariants_hold_across_a_sample():
    rng = random.Random(11)
    conditions = _onboarding_conditions()
    for _ in range(150):
        age = rng.choice([9, 13, 17, 30, 50, 65, 78])
        p = _profile(age=age, bmi=round(rng.uniform(14, 38), 1),
                     vikriti_dominant=rng.choice(["vata", "pitta", "kapha"]),
                     medical_history=rng.sample(conditions, rng.choice([0, 1, 2])),
                     ama_indicator=rng.choice(["none", "mild", "high"]),
                     ojas_level=rng.choice(["low", "medium"]),
                     agni_type=rng.choice([None, "manda", "tikshna", "vishama"]),
                     allergies=rng.choice([[], ["dairy"], ["sesame"]]))
        pr = _prefs(setting=rng.choice(["home", "clinic"]), available_time_days=rng.randint(3, 21))
        plan = generate_panchakarma_plan(p, pr)
        karma = _karma(plan)
        assert len(plan["daily_schedule"]) == plan["phase_breakdown"]["total_days"]
        if _ladder(plan):
            assert karma in ("vamana", "virechana")
        if karma not in ("vamana", "virechana"):
            assert "internal_ghrita" not in plan["aushadha"] or karma is None
        for day in plan["daily_schedule"]:
            ids = [t.get("id") for t in day["therapies"] if t.get("id")]
            assert len(ids) == len(set(ids)), (day["day"], ids)


# ── A retrieval outage degrades the narrative, it does not remove it ──────────

@pytest.mark.asyncio
async def test_a_retrieval_outage_keeps_the_narrative(monkeypatch):
    import json as _json
    from services import panchakarma_enricher as enr

    async def broken(*a, **k):
        raise RuntimeError("ChromaDB not initialized")

    async def fake_generate(**kw):
        return _json.dumps({"plan_title": "t", "plan_description": "d", "shodhana_rationale": "r"})

    monkeypatch.setattr(enr.rag_pipeline, "query", broken)
    monkeypatch.setattr(enr.llm_client, "generate", fake_generate)
    plan = generate_panchakarma_plan(_profile(), _prefs())
    out = await enr.enrich_panchakarma_plan(plan, _profile(), _prefs())
    assert out["enriched"] is True and out["plan_title"] == "t"


def test_coaching_for_an_absent_phase_is_withheld():
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata"), _prefs(setting="home"))
    assert plan["samsarjana_krama"] == []
    gated, withheld = gate_enrichment(
        {"samsarjana_coaching": "Samsarjana Krama is essential.", "plan_title": "t"}, plan)
    assert "samsarjana_coaching" not in gated and gated["plan_title"] == "t"
    assert withheld[0]["reason"] == "this plan has no Samsarjana Krama"


def test_the_snehana_card_names_the_oil_the_medicines_name():
    """One oil, one Ghrita: the card and the compendium used to disagree."""
    plan = generate_panchakarma_plan(_profile(), _prefs())
    sn, aus = plan["snehana_protocol"], plan["aushadha"]
    assert sn["abhyanga_oil"]["primary"] == aus["abhyanga_oil"]["name"]
    assert sn["internal_ghrita"]["primary"] == aus["internal_ghrita"]["name"]


def test_a_substituted_plan_carries_the_substitutes_cautions_not_the_withdrawn_ones():
    plan = generate_panchakarma_plan(
        _profile(vikriti_dominant="kapha", medical_history=["diabetes_type1"],
                 current_medications=["insulin"]), _prefs(current_season="vasanta"))
    assert _karma(plan) == "nasya"
    assert not any("Peya" in w for w in plan["clinical_decisions"]["safety_warnings"])
    reason = plan["clinical_decisions"]["pradhana_karma_selected"]["reason"]
    assert "Virechana" not in reason


def test_anaemia_is_not_given_a_reducing_therapy():
    plan = generate_panchakarma_plan(_profile(medical_history=["anemia"]), _prefs())
    ids = {t.get("id") for d in plan["daily_schedule"] for t in d["therapies"]}
    assert not ids & {"udvartana", "udvartana_home"}


def test_levodopa_is_recognised():
    assert "antiparkinson" in _medication_findings(["Syndopa 110"])["tokens"]


def test_the_gate_reads_an_allergen_free_preparation_as_safe():
    """Found in a live plan: "a honey-free preparation" was withheld as naming honey."""
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="vata", allergies=["honey"]), _prefs())
    gated, withheld = gate_enrichment(
        {"x": "Today is Niruha Basti once more, again with a honey-free preparation."}, plan)
    assert withheld == []
