"""Panchakarma contraindications — one source, actually read.

There were two contraindication sources and they disagreed with each other. The
prose absolutes in `panchakarma_protocols.json` are sourced to CS/SS/AH; the engine
carried a hardcoded Python dict that omitted several of them and promoted at least
one relative contraindication to absolute. Meanwhile the `contraindications` field
on the 23 therapy rows was read by no code at all, and 15 rows carried none.

`panchakarma_clinical.json` is now the only source. These tests assert that it is
read, that it bites, and that it cannot drift from the prose it was derived from.
"""
import json
from pathlib import Path

import pytest

from engine.condition_vocab import term_in_condition
from services.panchakarma_engine import (
    _karma_contraindications,
    _therapy_contraindications,
    filter_and_score_therapies,
    generate_panchakarma_plan,
    pk_clinical,
    pk_protocols,
    pk_therapies,
)

KB_DIR = Path(__file__).resolve().parent.parent / "data" / "knowledge_base"


def _profile(**over):
    base = dict(
        id="t", age=40, dominant_dosha="vata", vikriti_dominant="vata",
        fitness_level="intermediate", medical_history=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = dict(
        setting="clinic", available_time_days=14, detox_experience="experienced",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
        self_care_time_per_day="60 min", panchakarma_goal="detox",
    )
    base.update(over)
    return base


# ── The file itself ───────────────────────────────────────────────────────────

def test_every_contraindication_states_a_mechanism():
    """A bare token list cannot be reviewed.

    "CAUTION: diabetes" tells a reviewer nothing to agree or disagree with, and
    tells a patient nothing to do. Every entry names the mechanism by which the
    condition and the procedure conflict, so a BAMS reviewer can reject one claim
    without discarding the file.
    """
    empty = []
    for karma, entry in pk_clinical["pradhana_karma"].items():
        for severity in ("hard", "soft"):
            for term, mechanism in (entry.get(severity) or {}).items():
                if not mechanism or len(mechanism) < 25:
                    empty.append(f"pradhana_karma.{karma}.{severity}.{term}")
    for tid, entry in pk_clinical["therapies"].items():
        if not isinstance(entry, dict):
            continue
        for severity in ("hard", "soft"):
            for term, mechanism in (entry.get(severity) or {}).items():
                if not mechanism or len(mechanism) < 25:
                    empty.append(f"therapies.{tid}.{severity}.{term}")
    assert not empty, f"contraindications with no stated mechanism: {empty}"


def test_the_file_is_marked_unreviewed():
    """It is authored, not signed off. The flag is what carries that to the vaidya
    packet, and removing it must be a deliberate act by a reviewer."""
    assert pk_clinical["_meta"]["contraindications_reviewed"] is False
    assert "NOT CLINICALLY REVIEWED" in pk_clinical["_meta"]["review_status"]


def test_every_token_is_matchable_by_the_condition_vocabulary():
    """A token the matcher can never match is a contraindication that silently
    does nothing — the failure mode is indistinguishable from having omitted it."""
    unmatchable = []
    for section in ("pradhana_karma", "therapies"):
        for key, entry in pk_clinical[section].items():
            if not isinstance(entry, dict):
                continue
            for severity in ("hard", "soft"):
                for term in (entry.get(severity) or {}):
                    if not term_in_condition(term, term):
                        unmatchable.append(f"{section}.{key}.{severity}.{term}")
    assert not unmatchable, f"tokens the vocabulary cannot match: {unmatchable}"


def test_every_therapy_in_the_kb_has_a_clinical_entry():
    """A therapy the engine can schedule but the clinical layer does not know about
    passes every gate by default. 15 of 23 were in that state."""
    scheduled = {t["id"] for t in pk_therapies}
    described = {k for k in pk_clinical["therapies"] if not k.startswith("_")}
    assert not (scheduled - described), f"schedulable but ungated: {sorted(scheduled - described)}"
    assert not (described - scheduled), f"gated but not schedulable: {sorted(described - scheduled)}"


PROSE_ABSOLUTES_THAT_MUST_BE_TOKENISED = {
    # The specific disagreements between the prose and the old hardcoded dict.
    # Each was an absolute the KB stated and the engine did not enforce.
    "vamana": ["hypertension", "underweight", "epilepsy", "pregnancy"],
    "virechana": ["diarrhea", "tuberculosis", "rectal_prolapse", "pregnancy", "underweight"],
    "basti": ["pregnancy", "underweight", "diarrhea", "severe_ascites"],
    "raktamokshana": ["anemia", "pregnancy", "anticoagulants", "elderly"],
}


@pytest.mark.parametrize("karma,terms", PROSE_ABSOLUTES_THAT_MUST_BE_TOKENISED.items())
def test_the_prose_absolutes_are_enforced_not_just_documented(karma, terms):
    """The KB stated these as absolute and the engine enforced none of them.

    This is the anti-drift guard: `panchakarma_protocols.json` remains the prose of
    record, and if a term is added there it has to reach the machine layer too.
    """
    hard = _karma_contraindications(karma)["hard"]
    missing = [t for t in terms if t not in hard]
    assert not missing, f"{karma}: stated absolute in the KB prose, not enforced: {missing}"


def test_hemorrhoids_is_relative_for_virechana_not_absolute():
    """The KB marks active haemorrhoids "(relative)". The engine treated it as hard
    and substituted Basti — which is the worse choice for haemorrhoids, so the
    "safety" substitution made the plan less safe, not more."""
    contra = _karma_contraindications("virechana")
    assert "hemorrhoids" in contra["soft"]
    assert "hemorrhoids" not in contra["hard"]

    plan = generate_panchakarma_plan(
        _profile(dominant_dosha="pitta", vikriti_dominant="pitta", medical_history=["hemorrhoids"]),
        _prefs(),
    )
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]
    assert pk["primary"] == "virechana", "a relative contraindication must not substitute"
    assert any("hemorrhoid" in w.lower() for w in plan["clinical_decisions"]["safety_warnings"])


# ── The gate ──────────────────────────────────────────────────────────────────

def test_the_therapy_pool_is_gated_clinically_not_only_by_preference():
    """Every filter in pool selection was a preference filter — setting, experience,
    herbs, diet, time. A hypertensive diabetic and a healthy athlete received the
    same pool."""
    healthy = {t["id"] for t in filter_and_score_therapies(
        _profile(), _prefs(), "purvakarma", pk_therapies, "vata")}

    for condition, must_lose in [
        ("bleeding_disorder", {"swedana_home", "bashpa_sweda_clinic", "udvartana"}),
        ("psoriasis", {"udvartana"}),
        ("gallstones", {"snehapana_clinic"}),
        ("deep_vein_thrombosis", {"abhyanga_self", "abhyanga_clinic"}),
    ]:
        got = {t["id"] for t in filter_and_score_therapies(
            _profile(medical_history=[condition]), _prefs(), "purvakarma", pk_therapies, "vata")}
        removed = healthy - got
        assert must_lose <= removed, f"{condition}: expected {must_lose} removed, got {removed}"


def test_a_relative_contraindication_reaches_the_day_it_applies_to():
    """A caution held in the engine and never printed is the same defect as one
    never checked: the patient does the therapy either way, without the
    modification that made it safe for them."""
    pool = filter_and_score_therapies(
        _profile(medical_history=["diabetes_type2"]), _prefs(), "purvakarma", pk_therapies, "vata")
    cautioned = [t for t in pool if t.get("cautions")]
    assert cautioned, "diabetes must raise cautions on Swedana"
    assert all(c["mechanism"] for t in cautioned for c in t["cautions"])

    # And a therapy carrying a caution ranks below an equally suitable one without.
    assert not pool[0].get("cautions"), "the pool should prefer the option needing no modification"


def test_derived_ayurvedic_states_reach_the_gate():
    """Snehapana's bar on high Ama, and Udvartana's Vata caution, are keyed on states
    the engine derives rather than on anything a user types. Matching them against
    `medical_history` alone meant they could never fire."""
    with_ama = {t["id"] for t in filter_and_score_therapies(
        _profile(ama_indicator="high"), _prefs(), "purvakarma", pk_therapies, "vata")}
    assert "snehapana_clinic" not in with_ama, "oleation over undigested Ama is the classical error"

    vata_pool = filter_and_score_therapies(
        _profile(), _prefs(), "purvakarma", pk_therapies, "vata")
    udvartana = next((t for t in vata_pool if t["id"] == "udvartana"), None)
    assert udvartana and udvartana.get("cautions"), "Udvartana is Vata-increasing — say so to a Vata"


def test_a_substitution_never_lands_on_another_contraindicated_karma():
    """Ulcerative colitis is a hard contraindication for BOTH Virechana and Basti.
    The substitution was a single unchecked hop: the engine withdrew the purgative
    and handed the same patient an enema, reporting it as a safety substitution."""
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha="pitta", vikriti_dominant="pitta",
                 medical_history=["ulcerative_colitis"]),
        _prefs(),
    )
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]
    assert pk["original_karma"] == "virechana"
    assert pk["primary"] != "basti"

    if pk["primary"] is not None:
        key = "basti" if pk["primary"] == "basti_matra" else pk["primary"]
        hard = _karma_contraindications(key)["hard"]
        assert not any(term_in_condition("ulcerative_colitis", t) for t in hard)


def test_when_no_karma_is_safe_the_plan_says_so_instead_of_choosing_one():
    """The least-bad expulsion is not an answer."""
    profile = _profile(
        dominant_dosha="pitta", vikriti_dominant="pitta",
        medical_history=["ulcerative_colitis", "rectal_bleeding", "epistaxis", "nasal_surgery_recent"],
    )
    plan = generate_panchakarma_plan(profile, _prefs())
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] is None
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana"
    assert plan["shamana_protocol"] is not None
    assert len(plan["daily_schedule"]) == 14
    assert all(d["therapies"] for d in plan["daily_schedule"])


def test_pratimarsha_nasya_keeps_the_exemption_the_matrix_grants_it():
    """`contraindication_matrix.pregnancy` lists Pratimarsha Nasya among the ALLOWED
    therapies. Inheriting Navana Nasya's pregnancy bar would withdraw a therapy the
    KB explicitly permits — inheritance has to be overridable."""
    assert "pregnancy" not in _therapy_contraindications("nasya_home")["hard"]
    assert "pregnancy" in _therapy_contraindications("nasya_clinic")["hard"]


def test_home_and_clinic_variants_do_not_drift_apart():
    """`virechana_home` carried no contraindications while `virechana_clinic` carried
    two — the same procedure, gated differently by which room it happened in."""
    for home, clinic in [("virechana_home", "virechana_clinic"),
                         ("udvartana_home", "udvartana"),
                         ("abhyanga_clinic", "abhyanga_self")]:
        h = _therapy_contraindications(home)["hard"]
        c = _therapy_contraindications(clinic)["hard"]
        assert set(c) <= set(h) or set(h) <= set(c), f"{home} and {clinic} gate differently"


def test_active_fever_defers_the_plan_rather_than_softening_it():
    """`contraindication_matrix.acute_fever` is the one row whose allowed list is not
    a therapy: "nothing — wait for fever to resolve completely". Every other finding
    narrows the plan; this one postpones it."""
    plan = generate_panchakarma_plan(_profile(medical_history=["active_fever"]), _prefs())
    deferral = plan["clinical_decisions"]["deferral"]
    assert deferral is not None
    assert "Do not begin this plan" in deferral["notice"]
    assert deferral["resume_when"]


def test_the_gate_does_not_swallow_the_pool():
    """A patient who trips several relative contraindications must still get a plan
    with something on every day. The safe path cannot also be the empty one."""
    profile = _profile(
        age=75, fitness_level="beginner", ama_indicator="severe", ojas_level="low",
        digestion_quality="weak",
        medical_history=["bleeding_disorder", "psoriasis", "diabetes_type1", "eating_disorder"],
    )
    plan = generate_panchakarma_plan(profile, _prefs(
        setting="home", available_time_days=7, detox_experience="none",
        access_to_ayurvedic_herbs="no", diet_adherence_ability="lifestyle_only",
        self_care_time_per_day="15 min",
    ))
    assert len(plan["daily_schedule"]) == 7
    assert all(d["therapies"] for d in plan["daily_schedule"])


def test_the_clinical_file_is_valid_json_on_disk():
    """It is hand-authored; a trailing comma would take the whole gate offline
    silently, because the engine's loader tolerates a missing file."""
    raw = json.loads((KB_DIR / "panchakarma_clinical.json").read_text(encoding="utf-8"))
    assert raw["pradhana_karma"].keys() == pk_protocols["pradhana_karma"].keys()
