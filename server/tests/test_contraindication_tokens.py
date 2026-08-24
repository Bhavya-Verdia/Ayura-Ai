"""
The medicines / home-remedy contraindication gate.

Every test here was written from a defect found by sweeping all 164 contraindication
tokens in the two knowledge bases against the 102 conditions the app can actually
record, and asking of each one: could this ever fire?

The answer was no for 140 of them. The gate compared strings, so a contraindication
authored under one of two names for a disease never matched the other; and roughly a
third of the tokens are not diagnoses at all — they are derived Ayurvedic states, ages,
current symptoms, or instructions about how to take the preparation, none of which can
appear in `medical_history`.
"""
import json
import os

import pytest

from engine.condition_vocab import CONDITION_ALIASES, term_in_condition
from engine.contraindication_tokens import (
    CONDITION_TOKENS,
    DERIVED_TOKENS,
    build_derived_states,
    classify,
    contraindication_hit,
    usage_notes,
)
from engine.dosha_analyzer import _DISEASE_DOSHA_SIGNAL
from services.remedy_engine import (
    _MEDICINES_KB,
    _REMEDIES_FALLBACK,
    _check_medicine_safety,
    filter_remedies,
    generate_medicines_plan,
)

_KB_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "knowledge_base")


def _all_tokens() -> set[str]:
    tokens: set[str] = set()

    def walk(node):
        if isinstance(node, dict):
            for key, value in node.items():
                if key == "contraindications" and isinstance(value, list):
                    tokens.update(str(t).lower() for t in value)
                else:
                    walk(value)
        elif isinstance(node, list):
            for item in node:
                walk(item)

    for name in ("ayurvedic_medicines.json", "home_remedies.json"):
        with open(os.path.join(_KB_DIR, name)) as fh:
            walk(json.load(fh))
    return tokens


def _profile(**kw) -> dict:
    base = dict(id="u1", dominant_dosha="vata", secondary_dosha="pitta",
                age=40, weight=70, height=170, gender="female",
                medical_history=[], current_medications=[], allergies=[])
    base.update(kw)
    return base


def _find_med(name: str) -> dict:
    med = next((m for m in _MEDICINES_KB if m.get("name") == name), None)
    assert med is not None, f"{name} missing from the medicines KB"
    return med


# ── Coverage: silence is not one of the options ──────────────────────────────

def test_every_contraindication_token_is_classified():
    """A token that is neither a condition, a derived state, a usage caution nor a
    red flag reaches the gate and does nothing — which is indistinguishable from
    having no contraindication at all. The same rule the Panchakarma coverage test
    enforces: an entry must declare which of the four it is."""
    unclassified = []
    for token in sorted(_all_tokens()):
        try:
            classify(token)
        except KeyError:
            unclassified.append(token)
    assert unclassified == [], (
        f"{len(unclassified)} contraindication tokens are unclassified and therefore "
        f"inert: {unclassified}"
    )


def test_authored_condition_mappings_name_real_conditions():
    """`CONDITION_ALIASES` once canonicalised to `hypotension` while the disease map
    called it `low_blood_pressure`, so the alias resolved to a key nothing could look
    up. A canonical name that does not exist fails exactly as silently."""
    known = set(CONDITION_ALIASES) | set(_DISEASE_DOSHA_SIGNAL)
    unknown = sorted({c for v in CONDITION_TOKENS.values() for c in v if c not in known})
    assert unknown == [], f"CONDITION_TOKENS names conditions that do not exist: {unknown}"


def test_each_token_kind_is_exclusive_where_it_matters():
    """A token may be both a disease and a derived state (`emaciation` is a diagnosis
    and a BMI). It may not be both a blocker and purely advisory text — that would
    mean the same string sometimes withholds a medicine and sometimes only mentions
    it."""
    from engine.contraindication_tokens import CAUTION_TOKENS
    overlap = (set(CAUTION_TOKENS) & set(CONDITION_TOKENS)) | (set(CAUTION_TOKENS) & set(DERIVED_TOKENS))
    assert overlap == set(), f"tokens are both a usage caution and a gate: {sorted(overlap)}"


# ── The synonym-blind matcher ────────────────────────────────────────────────

@pytest.mark.parametrize("medicine,condition,token", [
    # A hard contraindication on a cardiotonic for someone with low blood pressure.
    # The KB writes `hypotension`; onboarding records `low_blood_pressure`.
    ("Arjuna Churna", "low_blood_pressure", "hypotension"),
    # A mica bhasma for a patient in renal failure. KB: `renal_disease`.
    ("Abhraka Bhasma", "chronic_kidney_disease", "renal_disease"),
    # Ashwagandha raises thyroid hormone. KB: `hyperthyroid`.
    ("Ashwagandha Churna", "hyperthyroidism", "hyperthyroid"),
])
def test_contraindication_fires_under_the_name_the_app_records(medicine, condition, token):
    med = _find_med(medicine)
    assert token in med["contraindications"]
    # The old gate, kept as the record of why this was invisible: comparing the two
    # names as strings finds nothing, because they are two names for one disease.
    assert not (term_in_condition(condition, token) or term_in_condition(token, condition))
    safe, reason = _check_medicine_safety(med, False, [], [], [condition], None)
    assert safe is False, f"{medicine} was cleared for a patient with {condition}"
    assert condition in reason


def test_synonym_matching_does_not_collapse_opposite_conditions():
    """`hypotension` and `hypertension` are one letter apart and clinical opposites.
    Resolving synonyms must not blur them."""
    med = _find_med("Arjuna Churna")
    safe, _ = _check_medicine_safety(med, False, [], [], ["hypertension"], None)
    assert safe is True


def test_class_token_covers_its_members_only():
    """`autoimmune_disease` names a class; onboarding records the member diseases."""
    med = _find_med("Ashwagandha Churna")
    assert "autoimmune_disease" in med["contraindications"]
    blocked, _ = _check_medicine_safety(med, False, [], [], ["lupus"], None)
    assert blocked is False
    allowed, _ = _check_medicine_safety(med, False, [], [], ["osteoarthritis"], None)
    assert allowed is True


def test_severity_qualifier_maps_onto_the_unqualified_disease():
    """The KB says `uncontrolled_diabetes`; a profile has no field for control.
    Barring nobody was the previous behaviour."""
    med = _find_med("Chyawanprash")
    assert "uncontrolled_diabetes" in med["contraindications"]
    safe, _ = _check_medicine_safety(med, False, [], [], ["diabetes_type2"], None)
    assert safe is False


# ── Derived states: never in medical_history, so never matched ───────────────

def test_dosha_contraindication_fires_on_an_assessed_imbalance():
    med = _find_med("Trikatu Churna")
    assert "pitta_excess" in med["contraindications"]
    states = build_derived_states(_profile(dominant_dosha="pitta", vikriti_dominant="pitta"))
    safe, reason = _check_medicine_safety(med, False, [], [], [], states)
    assert safe is False and "Pitta" in reason


def test_dosha_contraindication_does_not_fire_on_constitution_alone():
    """Prakriti is not Vikriti. Standing one in for the other blocked 37 of 157
    formulations for every Pitta-built user with nothing out of balance."""
    med = _find_med("Trikatu Churna")
    states = build_derived_states(_profile(dominant_dosha="pitta"))
    safe, _ = _check_medicine_safety(med, False, [], [], [], states)
    assert safe is True
    # …but the KB's claim is not thrown away; it is surfaced.
    from engine.contraindication_tokens import assumed_state_notes
    notes = assumed_state_notes(med["contraindications"], states)
    assert notes and "has not been assessed" in notes[0]


def test_ama_blocks_a_nourishing_tonic():
    med = _find_med("Bala Churna")
    assert "ama_condition" in med["contraindications"]
    states = build_derived_states(_profile(), ama_level="high")
    safe, reason = _check_medicine_safety(med, False, [], [], [], states)
    assert safe is False and "Ama" in reason


def test_paediatric_contraindication_reaches_a_child():
    """Onboarding accepts age from 10. Only mineral bhasmas were age-gated, by a
    separate rule; `children` on a herbal churna gated nothing."""
    med = _find_med("Chitraka Churna")
    assert "children" in med["contraindications"]
    blocked, _ = _check_medicine_safety(med, False, [], [], [], build_derived_states(_profile(age=10)))
    adult, _ = _check_medicine_safety(med, False, [], [], [], build_derived_states(_profile(age=40)))
    assert blocked is False and adult is True


def test_derived_states_are_ignored_when_not_supplied():
    """Callers that pass no state must not get state-based blocks by accident."""
    med = _find_med("Trikatu Churna")
    safe, _ = _check_medicine_safety(med, False, [], [], [], None)
    assert safe is True


# ── Usage cautions and red flags: the half a filter can never deliver ────────

def test_usage_instructions_are_returned_as_text_not_swallowed():
    cautions, _ = usage_notes(["do_not_ingest", "authenticated_source_only"])
    assert len(cautions) == 2
    assert any("External use only" in c for c in cautions)


def test_red_flags_are_returned_even_when_nothing_is_blocked():
    _, flags = usage_notes(["stroke_symptoms_seek_emergency"])
    assert flags and "emergency" in flags[0].lower()


def test_selected_medicines_carry_their_usage_notes():
    plan = generate_medicines_plan(_profile(), {}, [])
    selected = (plan["primary_formulations"] + plan["supporting_formulations"]
                + plan["external_therapies"])
    assert selected, "no formulations selected — the fixture profile is wrong"
    for med in selected:
        assert "usage_cautions" in med and "red_flags" in med


# ── Home remedies: a whole authored safety layer that nothing read ───────────

def test_home_remedy_contraindications_are_enforced():
    """All 60 remedy entries carry the field, 41 non-empty, and `filter_remedies`
    never opened it. The hyperacidity remedy is barred during an active ulcer."""
    entry = next(r for r in _REMEDIES_FALLBACK if r["symptom_id"] == "hyperacidity")
    assert "active_ulcer" in entry["contraindications"]
    results = filter_remedies(_profile(medical_history=["peptic_ulcer"]),
                              {"symptoms": ["hyperacidity"]})
    assert results and results[0].get("action") == "consult_doctor"


def test_home_remedy_still_served_without_the_barring_condition():
    results = filter_remedies(_profile(), {"symptoms": ["hyperacidity"]})
    assert results and results[0].get("remedy")


def test_a_remedy_is_not_withheld_because_of_the_symptom_it_treats():
    """The fever remedy lists `high_fever_above_103`, which reads the reported fever.
    Gating on it would withhold the fever remedy from everyone with a fever."""
    results = filter_remedies(_profile(), {"symptoms": ["fever_mild"]})
    assert results and results[0].get("remedy"), "the fever remedy blocked itself"
    assert results[0]["red_flags"], "the temperature threshold must still be shown"


def test_a_second_reported_symptom_can_bar_a_remedy():
    """The constipation remedy is contraindicated in diarrhoea — reachable only from
    the symptoms the user reports, which the gate never saw."""
    results = filter_remedies(_profile(), {"symptoms": ["constipation", "diarrhea"]})
    constipation = next((r for r in results if r["symptom_id"] == "constipation"), None)
    assert constipation and constipation.get("action") == "consult_doctor"


def test_ingredient_block_matches_the_stored_condition_name():
    """`"hypertension" in condition` never matched `high_blood_pressure`, which is
    what the app stores when someone ticks the box."""
    for recorded in ("hypertension", "high_blood_pressure"):
        results = filter_remedies(
            _profile(medical_history=[recorded], dominant_dosha="kapha"),
            {"symptoms": ["bloating"]},
        )
        assert results, f"no result for {recorded}"


# ── The engine still produces a usable plan ──────────────────────────────────

@pytest.mark.parametrize("profile", [
    _profile(),
    _profile(dominant_dosha="pitta", vikriti_dominant="pitta"),
    _profile(medical_history=["chronic_kidney_disease"]),
    _profile(medical_history=["peptic_ulcer", "diabetes_type2"]),
    _profile(age=10),
])
def test_tightening_the_gate_does_not_empty_the_plan(profile):
    plan = generate_medicines_plan(profile, {}, [])
    selected = (plan["primary_formulations"] + plan["supporting_formulations"]
                + plan["external_therapies"])
    assert selected, f"no formulations survived for {profile['medical_history']}"


def test_blocked_medicines_say_why():
    plan = generate_medicines_plan(_profile(medical_history=["chronic_kidney_disease"]), {}, [])
    assert plan["blocked_medicines"], "nothing blocked for a CKD patient"
    assert all(b.get("reason") for b in plan["blocked_medicines"])


def test_contraindication_hit_reports_the_users_own_wording():
    """A blocked-medicine reason a user cannot connect to anything they typed is not
    an explanation."""
    hit = contraindication_hit("renal_disease", ["chronic_kidney_disease"], None)
    assert hit == "chronic_kidney_disease"
