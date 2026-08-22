"""Aushadha selection — an entry nothing can select is not knowledge, it is decoration.

Across 5,400 generated plans covering every dosha, setting, goal, Koshtha and
condition, only 13 of 32 Aushadha compendium entries were ever chosen.
`_select_aushadha` matched on the `dosha` field alone and took the first hit, so of
the six Vata oils only Tila Taila — the first in the list — could ever be selected.
Ksheerabala, Mahanarayana, Bala, Dashamoola and Dhanvantara were authored, cited
with the rest of the KB, and unreachable.

The indication for each was already written down, in the `use` prose that no
matcher reads. These tests hold the line at: every entry reachable, every token
matchable, and every selection actually arriving on the plan.
"""
import itertools
import json
from pathlib import Path

import pytest

from engine.condition_vocab import term_in_condition
from services.panchakarma_engine import (
    _aushadha_name,
    _select_aushadha,
    _select_from_compendium,
    generate_panchakarma_plan,
    pk_protocols,
)

COMPENDIUM = pk_protocols["aushadha_compendium"]
RASAYANA = pk_protocols["paschat_karma"]["rasayana_integration"]["rasayana_by_condition"]
SECTIONS = ["oils_external", "ghrita_internal", "kashayam_basti", "virechana_drugs", "vamana_drugs"]

# The conditions the reachability sweep draws from — every condition named by any
# `indications` list, so the sweep cannot pass by simply not asking.
SWEEP_CONDITIONS = sorted({
    t
    for section in SECTIONS
    for entry in COMPENDIUM[section]
    for t in (entry.get("indications") or [])
} | {
    t for entry in RASAYANA.values() for t in (entry.get("indications") or [])
})


def _profile(**over):
    base = dict(
        id="t", age=40, gender="female", dominant_dosha="vata", vikriti_dominant="vata",
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


@pytest.fixture(scope="module")
def selected_names():
    """Every Aushadha name any patient can be given, swept across the input space."""
    names = set()
    for dosha, setting, koshtha, fitness, gender in itertools.product(
        ("vata", "pitta", "kapha"), ("home", "clinic"), ("krura", "sama", "mridu"),
        ("beginner", "intermediate", "advanced"), ("male", "female"),
    ):
        for condition in [[]] + [[c] for c in SWEEP_CONDITIONS]:
            plan = generate_panchakarma_plan(
                _profile(dominant_dosha=dosha, vikriti_dominant=dosha, koshtha=koshtha,
                         fitness_level=fitness, gender=gender, medical_history=condition),
                _prefs(setting=setting),
            )
            aushadha = plan["aushadha"]
            for key in ("abhyanga_oil", "internal_ghrita", "pradhana_aushadha",
                        "basti_kashayam", "basti_oil", "nasya_oil"):
                value = aushadha.get(key)
                if isinstance(value, dict) and value.get("name"):
                    names.add(value["name"])
            rasayana = aushadha.get("rasayana")
            if isinstance(rasayana, dict) and rasayana.get("herb"):
                names.add(rasayana["herb"])
    return names


@pytest.mark.parametrize("section", SECTIONS)
def test_every_compendium_entry_is_reachable(section, selected_names):
    """The load-bearing test of this file.

    An entry the selector cannot reach is indistinguishable from one that was never
    written — except that it looks like coverage in a review, which is worse.
    """
    unreachable = [
        e["name"] for e in COMPENDIUM[section] if e["name"] not in selected_names
    ]
    assert not unreachable, f"{section}: authored but unselectable: {unreachable}"


def test_every_rasayana_is_reachable_or_declares_itself_the_fallback(selected_names):
    """`rasayana_by_condition` is keyed BY CONDITION and was selected by dosha alone,
    so a PCOS patient and an osteoarthritis patient both got the generic dosha
    Rasayana while Shatavari and Laksha Guggulu — authored for exactly them — went
    unused. Three of eight keys were reachable.

    `general_immunity` remains reachable only as the fallback, and that is a design
    decision rather than an oversight, so it has to say so in the KB.
    """
    for key, entry in RASAYANA.items():
        if entry.get("herb") in selected_names:
            continue
        assert entry.get("fallback") is True, f"{key} is unreachable and does not declare itself a fallback"
        assert entry.get("fallback_note"), f"{key} declares fallback with no stated reason"


@pytest.mark.parametrize("section", SECTIONS)
def test_every_indication_token_is_matchable(section):
    """A token the matcher can never match is indistinguishable from an entry with
    no indication at all — it fails silently and looks authored."""
    bad = [
        (e["name"], t)
        for e in COMPENDIUM[section]
        for t in (e.get("indications") or [])
        if not term_in_condition(t, t)
    ]
    assert not bad, f"{section}: tokens the vocabulary cannot match: {bad}"


@pytest.mark.parametrize("section", SECTIONS)
def test_every_entry_declares_its_indications(section):
    """Absent means "unknown"; empty means "no specific indication, use as the dosha
    default". They are different claims and the field has to distinguish them."""
    missing = [e["name"] for e in COMPENDIUM[section] if "indications" not in e]
    assert not missing, f"{section}: no indications field: {missing}"


def test_the_emetics_carry_a_dose_and_say_what_it_is_titrated_against():
    """The Vamana drugs carried no dose at all, so the day action hardcoded its own
    text and the KB rows were decorative. Emetic dosing is titrated to Vega rather
    than fixed, and a bare number would be the more dangerous thing to write."""
    for entry in COMPENDIUM["vamana_drugs"]:
        assert entry.get("dose"), f"{entry['name']} has no dose"
        assert "Vega" in entry.get("dose_note", ""), f"{entry['name']} does not say what titrates it"


# ── Selection behaviour ───────────────────────────────────────────────────────

def test_the_indication_decides_within_the_dosha():
    """Six of the eleven external oils are Vata oils. Only the first was reachable."""
    oils = COMPENDIUM["oils_external"]
    plain = _select_from_compendium(oils, [], "vata")
    sciatic = _select_from_compendium(oils, ["sciatica"], "vata")
    arthritic = _select_from_compendium(oils, ["rheumatoid_arthritis"], "vata")

    assert plain["name"] != sciatic["name"] != arthritic["name"]
    assert plain["name"] != arthritic["name"]


def test_the_dosha_still_outranks_a_bare_indication_match():
    """An oil that aggravates the vitiated Dosha does not become correct through
    treating the complaint."""
    oils = COMPENDIUM["oils_external"]
    # Sarshapa Taila is indicated for obesity but is a Kapha oil.
    chosen = _select_from_compendium(oils, ["obesity"], "pitta")
    assert chosen.get("dosha") in ("pitta", "pitta_vata", "pitta_rakta", "all")


def test_koshtha_still_fixes_the_virechana_strength():
    """The indication decides within a strength band, never across one. Atiyoga in a
    Mridu Koshtha is the risk the Koshtha rule exists for, and an acidity diagnosis
    is not a reason to overrule it."""
    for koshtha, expected in (("mridu", "mild"), ("krura", "strong")):
        result = _select_aushadha(
            "pitta", ["acid_reflux"], "virechana", "clinic", pk_protocols, koshtha=koshtha)
        assert result["pradhana_aushadha"]["strength"] == expected


def test_the_indication_reaches_avipattikara_inside_its_band():
    """Avipattikara and Eranda are both "moderate". Taking the first match meant an
    acidity patient got castor oil while the drug authored for acidity went unused."""
    plain = _select_aushadha("pitta", [], "virechana", "clinic", pk_protocols)
    acidity = _select_aushadha("pitta", ["acid_reflux"], "virechana", "clinic", pk_protocols)
    assert plain["pradhana_aushadha"]["strength"] == acidity["pradhana_aushadha"]["strength"]
    assert acidity["pradhana_aushadha"]["name"].startswith("Avipattikara")


def test_the_emetic_strength_follows_bala_not_the_room():
    """Vamana is clinic-only, so keying the strength on the setting left the mild
    band permanently dead — and "which room you are in" is not what decides how hard
    to purge someone. CS Sutrasthana 15: Bala Pareeksha."""
    got = {
        fitness: _select_aushadha(
            "kapha", [], "vamana", "clinic", pk_protocols, bala=bala)["pradhana_aushadha"]["strength"]
        for fitness, bala in (("beginner", "manda"), ("intermediate", "madhyama"), ("advanced", "uttama"))
    }
    assert got == {"beginner": "mild", "intermediate": "moderate", "advanced": "strong"}


def test_gender_separates_the_two_reproductive_rasayanas():
    """Both list infertility; without gender the first would always win and half the
    users would get the wrong Rasayana for the same recorded condition."""
    female = _select_aushadha("vata", ["infertility"], "basti", "clinic", pk_protocols, gender="female")
    male = _select_aushadha("vata", ["infertility"], "basti", "clinic", pk_protocols, gender="male")
    assert female["rasayana"]["herb"] != male["rasayana"]["herb"]
    assert "Shatavari" in female["rasayana"]["herb"]


def test_a_condition_specific_rasayana_beats_the_dosha_default():
    plain = _select_aushadha("vata", [], "basti", "clinic", pk_protocols)
    joint = _select_aushadha("vata", ["osteoarthritis"], "basti", "clinic", pk_protocols)
    assert plain["rasayana"]["herb"] != joint["rasayana"]["herb"]


# ── The selection has to survive to the plan ──────────────────────────────────

def test_the_selected_oil_is_the_oil_the_schedule_prints():
    """The dict branches of the old formatting helpers discarded the value and
    returned a hardcoded default, so every Basti day printed "Tila Taila" whatever
    had been selected — a condition-specific choice made correctly and thrown away
    one line before it reached the patient."""
    plan = generate_panchakarma_plan(_profile(medical_history=["sciatica"]), _prefs())
    selected = _aushadha_name(plan["aushadha"].get("basti_oil"), "")
    assert selected

    printed = " ".join(
        str(t.get("pradhana_notes", "")) + t["name"]
        for day in plan["daily_schedule"] for t in day["therapies"]
    )
    assert selected in printed, f"{selected!r} was selected but never printed"


def _engine_user_facing_literals() -> list[str]:
    """Every string literal in the engine that is not a comment or a docstring.

    Comments naming a KB entry are how the code explains itself and must not fail
    this check; a literal that can reach a patient is the thing at issue.
    """
    import ast

    source = (Path(__file__).resolve().parent.parent / "services" / "panchakarma_engine.py").read_text()
    tree = ast.parse(source)
    docstrings = set()
    for node in ast.walk(tree):
        if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            doc = ast.get_docstring(node, clean=False)
            if doc:
                docstrings.add(doc)
    return [
        n.value for n in ast.walk(tree)
        if isinstance(n, ast.Constant) and isinstance(n.value, str) and n.value not in docstrings
    ]


def test_the_engine_does_not_hardcode_names_the_kb_already_holds():
    """Eleven oils existed as Python string literals AND as compendium rows with
    their own `use` text — two descriptions of Ksheerabala Taila that could drift,
    with the KB's version never reaching the user.

    Fallback defaults are exempt: `_aushadha_name(value, "Tila Taila")` names a KB
    entry, but it fires only when the compendium is empty and is a last resort
    rather than a second source of truth.
    """
    literals = [
        s for s in _engine_user_facing_literals()
        # A bare name is a fallback default; a sentence containing one is prose.
        if len(s.split()) > 4
    ]
    leaked = sorted({
        e["name"]
        for section in ("oils_external", "ghrita_internal", "kashayam_basti")
        for e in COMPENDIUM[section]
        for s in literals
        if e["name"].split(" (")[0] in s
    })
    assert not leaked, f"KB entry names embedded in engine prose: {leaked}"


def test_the_authoring_is_marked_unreviewed():
    raw = json.loads(
        (Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
         / "panchakarma_protocols.json").read_text(encoding="utf-8"))
    note = raw["aushadha_compendium"]["_authoring_note"]
    assert "NOT CLINICALLY REVIEWED" in note


# ── Procedural prose lives in the KB ──────────────────────────────────────────

PROCEDURES = json.loads(
    (Path(__file__).resolve().parent.parent / "data" / "knowledge_base"
     / "panchakarma_procedures.json").read_text(encoding="utf-8"))

PROCEDURE_KEYS = [k for k in PROCEDURES if not k.startswith("_")
                  and k not in ("shamana_regimen",)]


@pytest.mark.parametrize("key", PROCEDURE_KEYS)
def test_every_procedure_has_steps_and_a_benefit(key):
    """None of the 23 therapy rows carried an instructions field, so every how-to in
    the feature — emesis, purgation, two kinds of enema, nasal instillation,
    bloodletting — was a string literal in the engine."""
    spec = PROCEDURES[key]
    assert spec.get("steps"), f"{key} has no steps"
    assert spec.get("benefits"), f"{key} does not say what it is for"
    assert all(isinstance(s, str) and s.strip() for s in spec["steps"])


def test_every_placeholder_is_one_the_engine_supplies():
    """An unfilled placeholder would print a brace to a patient. `_render_procedure`
    drops a step it cannot fill rather than printing one, which turns the failure
    silent — so the guard has to be here."""
    import re

    # Every field name any call site passes to _render_procedure.
    supplied = {
        "drug_name", "dose", "dose_note", "koshtha_note", "oil_name", "kashayam_name",
        "position", "sequence_note", "total_volume", "temperature", "mix_order",
        "anuvasana_formula", "herb_name", "alternatives", "diet", "signs",
        "duration", "timing", "stage", "food", "recipe", "note",
    }
    unknown = {}
    for key, spec in PROCEDURES.items():
        if key.startswith("_") or key == "shamana_regimen":
            continue
        texts = list(spec.get("steps", [])) + [spec.get("name", ""), spec.get("timing", "")]
        texts += list((spec.get("conditional_steps") or {}).values())
        for text in texts:
            for placeholder in re.findall(r"\{(\w+)\}", str(text)):
                if placeholder not in supplied:
                    unknown.setdefault(key, set()).add(placeholder)
    assert not unknown, f"placeholders no call site supplies: {unknown}"


def test_no_step_reaches_a_patient_with_an_unfilled_brace():
    """The end-to-end version of the check above, across the plan shapes that use
    each procedure."""
    for profile, prefs in [
        (_profile(dominant_dosha="vata", vikriti_dominant="vata"), _prefs()),
        (_profile(dominant_dosha="pitta", vikriti_dominant="pitta"), _prefs()),
        (_profile(dominant_dosha="kapha", vikriti_dominant="kapha"), _prefs()),
        (_profile(dominant_dosha="vata", vikriti_dominant="vata"), _prefs(setting="home")),
        (_profile(ama_indicator="moderate"), _prefs()),
        (_profile(age=78), _prefs()),
    ]:
        plan = generate_panchakarma_plan(profile, prefs)
        for day in plan["daily_schedule"]:
            for therapy in day["therapies"]:
                text = str(therapy.get("pradhana_notes", "")) + therapy["name"]
                assert "{" not in text and "}" not in text, f"unfilled placeholder: {text[:120]}"


def test_the_shamana_regimen_comes_from_the_kb():
    regimen = PROCEDURES["shamana_regimen"]
    for dosha in ("vata", "pitta", "kapha"):
        assert regimen[dosha]["ahara"] and regimen[dosha]["vihara"]
        assert regimen[dosha]["principle"] and regimen[dosha]["sneha_matra"]

    plan = generate_panchakarma_plan(_profile(age=78), _prefs())
    chikitsa = plan["shamana_protocol"]["shamana_chikitsa"]
    assert chikitsa["ahara"] == regimen["vata"]["ahara"] or chikitsa["ahara"]


def test_the_engine_holds_no_procedural_prose_of_its_own():
    """The forcing function for the migration. A long user-facing sentence in the
    engine is prose that escaped the KB — where it cannot be reviewed by a vaidya,
    translated, or diffed as data."""
    long_literals = [
        s for s in _engine_user_facing_literals()
        if len(s.split()) > 25 and not s.startswith(("SAFETY", "CAUTION", "NO SAFE", "BRIMHANA", "SNEHANA"))
    ]
    # What remains must be explanatory plan-level text (verdicts, notices), never
    # step-by-step instruction. Instructions name an action to perform on a body.
    procedural = [
        s for s in long_literals
        if any(w in s.lower() for w in
               ("lie supine", "lie on the left", "administer", "drops in each nostril",
                "insert", "enema bulb", "retain 30", "count vegas"))
    ]
    assert not procedural, f"procedural prose still in the engine: {procedural}"


def test_the_sahayoga_adjuvants_moved_into_the_compendium():
    """Seven formulations were an if/elif chain of dict literals matched by raw
    substring — `"kidney" in m` — while every safety gate uses `term_in_condition`."""
    adjuvants = COMPENDIUM["sahayoga_dravya"]
    assert len(adjuvants) == 7
    for entry in adjuvants:
        assert entry.get("id") and entry.get("indications") and entry.get("use")
        for token in entry["indications"]:
            assert term_in_condition(token, token), f"{entry['id']}: unmatchable {token}"

    # And they still reach the plan.
    plan = generate_panchakarma_plan(_profile(medical_history=["psoriasis"]), _prefs())
    assert "kushtha_aushadha" in plan["aushadha"]
    clean = generate_panchakarma_plan(_profile(), _prefs())
    assert "kushtha_aushadha" not in clean["aushadha"]
