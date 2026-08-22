"""Sahayoga Dravya and Rasayana — the formulations that passed no safety gate at all.

The seven adjuvant formulations added alongside the Pradhana Karma, and the Rasayana
the plan tells the patient to continue for months afterwards, were selected on an
indication match and handed over with nothing checked. Shilajit went to patients
with chronic kidney disease, Guggulu to patients on thyroxine, Ashwagandha to
hyperthyroid patients, and Sarpagandha — a reserpine source and a documented cause
of drug-induced depression — to anyone whose conditions included hypertension.

`raktavaha_aushadha` carried its own `caution` field reading "avoid in hypotension".
Nothing read it.
"""
import json
from pathlib import Path

import pytest

from engine.condition_vocab import term_in_condition
from services.panchakarma_engine import (
    _gate_formulation,
    _select_aushadha,
    generate_panchakarma_plan,
    pk_clinical,
    pk_protocols,
)

HERBS = pk_clinical["herbs"]
ADJUVANTS = pk_protocols["aushadha_compendium"]["sahayoga_dravya"]
RASAYANA = pk_protocols["paschat_karma"]["rasayana_integration"]["rasayana_by_condition"]


def _profile(**over):
    base = dict(
        id="t", age=45, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
        fitness_level="intermediate", medical_history=[],
        ama_indicator="none", ojas_level="medium", digestion_quality="moderate",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = dict(
        setting="clinic", available_time_days=21, detox_experience="experienced",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
        self_care_time_per_day="2+ hours", panchakarma_goal="detox",
    )
    base.update(over)
    return base


def _aushadha(profile, prefs=None):
    return generate_panchakarma_plan(profile, prefs or _prefs())["aushadha"]


# ── The herb table ────────────────────────────────────────────────────────────

def test_every_component_of_every_formulation_has_a_safety_entry():
    """A component with no entry passes the gate by default — silently, and
    indistinguishably from one that was checked and cleared."""
    missing = {}
    for entry in ADJUVANTS:
        for key in entry.get("components", []):
            if key not in HERBS:
                missing.setdefault(entry["id"], []).append(key)
    for key, entry in RASAYANA.items():
        for component in entry.get("components", []):
            if component not in HERBS:
                missing.setdefault(f"rasayana.{key}", []).append(component)
    assert not missing, f"components with no safety entry: {missing}"


def test_every_formulation_declares_its_components():
    """The `name` is display prose — "Guduchi + Haridra + Amalaki (Triphala Churna)
    + Shilajit" — and cannot be gated as text."""
    for entry in ADJUVANTS:
        assert entry.get("components"), f"{entry['id']} has no components"
    for key, entry in RASAYANA.items():
        assert entry.get("components"), f"rasayana.{key} has no components"


def test_every_herb_entry_states_a_mechanism_and_is_matchable():
    bad = []
    for herb, entry in HERBS.items():
        assert entry.get("display"), f"{herb} has no display name"
        for severity in ("hard", "soft"):
            for token, mechanism in (entry.get(severity) or {}).items():
                if not term_in_condition(token, token):
                    bad.append((herb, token, "unmatchable"))
                if not mechanism or len(mechanism) < 25:
                    bad.append((herb, token, "no mechanism"))
    assert not bad, bad


def test_the_herb_table_is_marked_unreviewed():
    assert "NOT CLINICALLY REVIEWED" in pk_clinical["_herbs_note"]


# ── The gate ──────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("herb,condition", [
    ("ashwagandha", "hyperthyroidism"),
    ("shilajit", "chronic_kidney_disease"),
    ("guggulu", "pregnancy"),
    ("sarpagandha", "depression"),
    ("sarpagandha", "hypotension"),
    ("kapikacchu", "parkinson"),
    ("kutaja", "constipation_chronic"),
])
def test_a_hard_contraindication_withholds_that_component(herb, condition):
    gate = _gate_formulation([herb], [condition], [])
    assert herb not in gate["kept"]
    assert gate["withheld"], f"{herb} not withheld for {condition}"
    assert gate["withheld"][0]["reasons"][0]["mechanism"]


def test_withholding_one_component_keeps_the_rest_of_the_formulation():
    """A contraindication against one constituent is a reason to withhold that
    constituent, not the four-herb preparation around it. Dropping the whole thing
    would deny a psoriasis patient their Kushtha Chikitsa because one component
    interacts with their warfarin."""
    aushadha = _aushadha(_profile(medical_history=["anxiety", "hyperthyroidism"]))
    manovaha = aushadha["manovaha_aushadha"]

    withheld = [w["herb"] for w in manovaha["components_withheld"]]
    assert any("Ashwagandha" in h for h in withheld)
    assert manovaha["name"], "the rest of the formulation must survive"


def test_a_formulation_falls_entirely_only_when_nothing_is_left():
    """And when it does, it is recorded rather than silently absent — a missing
    adjuvant looks identical to one that was never indicated, and the Vaidya needs
    to know it was considered and rejected."""
    gate = _gate_formulation(["ashwagandha"], ["hyperthyroidism"], [])
    assert not gate["kept"]

    aushadha = _aushadha(_profile(medical_history=["ibs", "constipation_chronic"]))
    dropped = {w["id"] for w in aushadha.get("withheld_aushadha", [])}
    kept = {k for k in aushadha if k.endswith("_aushadha")}
    # Whichever way it lands, a formulation is never both present and empty.
    assert not (dropped & kept)


def test_sarpagandha_is_withheld_from_a_patient_with_a_psychiatric_history():
    """The sharpest case in the table. Reserpine depletes central monoamines and is
    a documented cause of drug-induced depression including suicidality; the
    formulation was given on a hypertension match with no check of psychiatric
    history at all."""
    aushadha = _aushadha(_profile(medical_history=["hypertension", "depression"]))
    raktavaha = aushadha["raktavaha_aushadha"]
    withheld = [w["herb"] for w in raktavaha["components_withheld"]]
    assert any("Sarpagandha" in h for h in withheld)

    # And it survives, with a caution, where there is no psychiatric history.
    plain = _aushadha(_profile(medical_history=["hypertension"]))["raktavaha_aushadha"]
    assert not [w for w in plain.get("components_withheld", []) if "Sarpagandha" in w["herb"]]
    assert any("Sarpagandha" in c["herb"] for c in plain.get("component_cautions", []))


def test_pregnancy_reaches_the_gate_even_though_it_is_not_a_condition():
    """`pregnancy_or_nursing` is a profile flag, not a `medical_history` entry, and
    the herb table keys on conditions — so without the injection the pregnancy bars
    on Guggulu, Vasaka, Manjistha and Shatapushpa could never fire."""
    result = _select_aushadha(
        "vata", ["osteoarthritis"], "basti", "clinic", pk_protocols, pregnancy=True)
    herb = (result["rasayana"] or {}).get("herb")
    assert herb != "Laksha Guggulu", "Guggulu is a uterine stimulant"


# ── Drug interactions ─────────────────────────────────────────────────────────

def test_a_major_interaction_withholds_rather_than_warns():
    """The interaction KB's own recommendation for Haridra on Warfarin reads "AVOID
    turmeric/curcumin supplements". Printing AVOID beside a formulation the plan
    still tells the patient to take is an ungated contraindication wearing a label."""
    gate = _gate_formulation(
        ["guduchi", "haridra", "amalaki", "shilajit"], ["diabetes_type2"], ["warfarin"])
    assert "haridra" not in gate["kept"]
    assert any("Haridra" in w["herb"] for w in gate["withheld"])


def test_a_moderate_interaction_is_kept_with_the_warning():
    """Moderate means proceed with monitoring, and removing the herb would be
    over-reading the KB."""
    gate = _gate_formulation(["amalaki"], [], ["warfarin"])
    assert "amalaki" in gate["kept"]
    assert any("Amalaki" in i.get("herb", "") for i in gate["interactions"])


def test_the_interaction_check_is_not_disabled_by_a_display_gloss():
    """The interaction KB keys are compound ("turmeric_haridra_high_dose") and the
    checker matches by substring either way round, so the bare token "haridra"
    matches while "Haridra (Turmeric)" matches nothing. Passing display names
    silently disabled the whole check and every result came back clean."""
    gate = _gate_formulation(["haridra"], [], ["warfarin"])
    assert gate["interactions"], "a gloss in parentheses must not disable the check"


def test_no_medications_means_no_interaction_noise():
    gate = _gate_formulation(["guduchi", "haridra", "amalaki"], [], [])
    assert gate["kept"] == ["guduchi", "haridra", "amalaki"]
    assert not gate["interactions"]


# ── Rasayana ──────────────────────────────────────────────────────────────────

def test_the_rasayana_is_skipped_rather_than_trimmed():
    """A Rasayana is one `herb` string — "Shilajit + Guggulu" — so dropping Shilajit
    from the component list does not change what the patient reads. A trimmed
    Rasayana still tells a CKD patient to take Shilajit."""
    aushadha = _aushadha(_profile(
        dominant_dosha="kapha", vikriti_dominant="kapha",
        medical_history=["diabetes_type2", "chronic_kidney_disease"]))
    herb = aushadha["rasayana"].get("herb") or ""
    assert "Shilajit" not in herb


def test_a_substituted_rasayana_says_it_was_substituted():
    aushadha = _aushadha(_profile(
        dominant_dosha="kapha", vikriti_dominant="kapha",
        medical_history=["obesity", "chronic_kidney_disease"]))
    rasayana = aushadha["rasayana"]
    if rasayana.get("herb"):
        assert rasayana.get("substitution_note"), "a silent swap is a swap the Vaidya cannot check"


def test_when_no_rasayana_is_safe_the_plan_says_so():
    """Picking the least-bad one to fill the field is not an answer — this is the
    prescription the plan tells the patient to continue for MONTHS after the course
    ends, long after anyone is watching."""
    everything = [
        "hyperthyroidism", "chronic_kidney_disease", "gout", "hemochromatosis",
        "psychosis", "parkinson", "fibroids", "ibd_crohns", "acute_pancreatitis",
        "high_ama", "diabetes_type2",
    ]
    aushadha = _select_aushadha(
        "vata", everything, "basti", "clinic", pk_protocols, pregnancy=True)
    rasayana = aushadha["rasayana"]
    if not rasayana.get("herb"):
        assert rasayana["unavailable_reason"]
        assert "Vaidya" in rasayana["unavailable_reason"]


def test_a_clean_profile_still_gets_its_adjuvant_and_rasayana():
    """Every test above withholds something; this is the counterweight. The gate
    must not quietly empty the feature."""
    aushadha = _aushadha(_profile(medical_history=["psoriasis"]))
    assert "kushtha_aushadha" in aushadha
    assert not aushadha["kushtha_aushadha"].get("components_withheld")
    assert aushadha["rasayana"].get("herb")
    assert not aushadha.get("withheld_aushadha")


def test_the_authoring_script_is_reproducible():
    """The herb table and the component lists are generated; re-running must be a
    no-op, so the committed KB and the authoring record cannot drift."""
    import subprocess

    root = Path(__file__).resolve().parent.parent
    before = {
        name: (root / "data" / "knowledge_base" / name).read_text(encoding="utf-8")
        for name in ("panchakarma_clinical.json", "panchakarma_protocols.json")
    }
    subprocess.run(
        [str(root / "venv" / "bin" / "python"), str(root / "scripts" / "author_herb_safety.py")],
        cwd=root, check=True, capture_output=True,
    )
    for name, text in before.items():
        assert (root / "data" / "knowledge_base" / name).read_text(encoding="utf-8") == text, \
            f"{name} changed on a re-run of the authoring script"


def test_the_adjuvants_reach_the_vaidya_packet():
    """183 contraindications went into the packet; the herb table is 77 more claims
    gating the same patients and must not be reviewed by a different route."""
    csv_path = (Path(__file__).resolve().parent.parent / "data" / "golden"
                / "vaidya_panchakarma_contraindications.csv")
    assert csv_path.exists()
    body = csv_path.read_text(encoding="utf-8")
    assert "sarpagandha" in body.lower(), "the herb table is missing from the packet"
    assert "ashwagandha" in body.lower()


def test_the_herb_table_and_the_formulations_agree_on_what_is_in_them():
    """Component lists are authored separately from the display names; a herb named
    in the prose but absent from the components is ungated."""
    unaccounted = {}
    for entry in ADJUVANTS:
        displays = [HERBS[c]["display"].split(" (")[0].lower() for c in entry["components"]]
        for word in ("sarpagandha", "shilajit", "ashwagandha", "guggulu"):
            if word in entry["name"].lower() and word not in " ".join(displays):
                unaccounted.setdefault(entry["id"], []).append(word)
    assert not unaccounted, f"named in the formulation but not gated: {unaccounted}"


def test_the_clinical_file_is_still_valid_json():
    raw = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
         / "panchakarma_clinical.json").read_text(encoding="utf-8"))
    assert raw["herbs"] and raw["pradhana_karma"] and raw["therapies"]
