"""Kriya Kala — the sixth `shodhana_candidate_criteria` item reaching the plan.

`shodhana_eligibility.shodhana_candidate_criteria` lists six marks of a Shodhana
candidate. Five were implemented somewhere in the engine (Bala, Agni, Ama, Season,
Age 7-70); Kriya Kala was not, and the sub-key itself was read by no code and no
test. Meanwhile the stage was already being computed for every condition the patient
staged — `CheckIn.jsx` collects duration + trajectory, `vikriti_service`
maps the pair through `_KRIYA_KALA_MAP`, and `plan_runner` hands `disease_stages` to
every engine — and `panchakarma_enricher` required the narrative to justify the
verdict "in classical terms (Bala, Agni, Ama, Ritu, Kriya Kala)" while being told
four of those five.

These tests hold three things: that the stage reaches the plan, that it stays
ADVISORY (it is absent from `shamana_only_criteria`, so it must decide nothing), and
that the window stays pinned to the KB prose.
"""
import json
from pathlib import Path

import pytest

from services.panchakarma_engine import (
    _KRIYA_KALA_ORDER,
    _KRIYA_KALA_SHODHANA_WINDOW,
    _kriya_kala_assessment,
    generate_panchakarma_plan,
    pk_protocols,
)
from services.vikriti_service import _KRIYA_KALA_MAP

KB = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "panchakarma_protocols.json"


def _profile(**over):
    p = dict(
        age=32, gender="male", bmi=23.0,
        vikriti_dominant="kapha", dominant_dosha="kapha", vikriti_secondary=None,
        ojas_level="medium", fitness_level="intermediate", digestion_quality="moderate",
        ama_indicator="none", medical_history=[], current_medications=[],
        pregnancy_or_nursing=False, koshtha="sama",
    )
    p.update(over)
    return p


def _prefs(**over):
    f = dict(
        panchakarma_goal="detox", detox_experience="some", available_time_days=14,
        setting="clinic", self_care_time_per_day="1 hour",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
    )
    f.update(over)
    return f


def _stages(**pairs):
    """{condition: stage} → the `disease_stages` shape `vikriti_service` persists."""
    return {c: {"duration": "1-3y", "trajectory": "stable", "kriya_kala": s}
            for c, s in pairs.items()}


def _plan(stages=None, **over):
    prof = _profile(**over)
    if stages is not None:
        prof["disease_stages"] = stages
    return generate_panchakarma_plan(prof, _prefs())


def _elig(plan):
    return plan["clinical_decisions"]["shodhana_or_shamana"]


# ── The stage reaches the plan ─────────────────────────────────────────────────

def test_stage_reaches_the_eligibility_block():
    kk = _elig(_plan(_stages(asthma="vyakti")))["kriya_kala"]
    assert kk is not None
    assert kk["governing_stage"] == "vyakti"
    assert kk["governing_condition"] == "asthma"
    assert kk["alignment"] == "in_window"


def test_absent_when_nothing_is_staged():
    """The common case: `disease_stages` is only written for conditions the patient
    answered the selects for, so a null must be a clean null rather than a default
    stage the narrative would then cite as fact."""
    assert _elig(_plan(None))["kriya_kala"] is None
    assert _elig(_plan({}))["kriya_kala"] is None


def test_present_on_all_three_verdicts():
    """The stage describes the patient, not the verdict. A Shamana patient's disease
    has a stage too, and the enricher is required to cite it on whichever arm it
    narrates — so a verdict that dropped it would put the model back to inventing."""
    stages = _stages(asthma="sthana")
    shodhana = _elig(_plan(stages))
    mridu    = _elig(generate_panchakarma_plan(
        {**_profile(), "disease_stages": stages}, _prefs(setting="home")))
    shamana  = _elig(_plan(stages, age=78))
    assert shodhana["type"] == "shodhana"
    assert mridu["type"] == "mridu_shodhana"
    assert shamana["type"] == "shamana"
    for e in (shodhana, mridu, shamana):
        assert e["kriya_kala"]["governing_stage"] == "sthana"


# ── It is advisory — it must decide nothing ───────────────────────────────────

@pytest.mark.parametrize("stage", _KRIYA_KALA_ORDER)
def test_no_stage_changes_the_verdict(stage):
    """The guard on the judgement call. Kriya Kala appears in
    `shodhana_candidate_criteria` but NOT in `shamana_only_criteria`, which is what
    decides eligibility — so no stage, including Bheda, may block or restrict."""
    baseline = _elig(_plan(None))
    staged   = _elig(_plan(_stages(asthma=stage)))
    assert staged["type"] == baseline["type"]
    assert staged["shodhana_eligible"] == baseline["shodhana_eligible"]
    assert staged["clinically_ineligible"] == baseline["clinically_ineligible"]
    assert staged["blocking_reasons"] == baseline["blocking_reasons"]
    assert staged["restricting_reasons"] == baseline["restricting_reasons"]
    assert staged["reasons"] == baseline["reasons"]


@pytest.mark.parametrize("stage", _KRIYA_KALA_ORDER)
def test_no_stage_changes_the_schedule(stage):
    """Stronger than the verdict check: the whole plan, minus the advisory and the
    per-run identifiers, must come back identical to the unstaged baseline."""
    def scrub(p):
        p = json.loads(json.dumps(p, default=str))
        p.pop("plan_id", None); p.pop("generated_at", None)
        p["clinical_decisions"]["shodhana_or_shamana"].pop("kriya_kala", None)
        return p
    assert scrub(_plan(_stages(asthma=stage))) == scrub(_plan(None))


def test_advisory_flag_is_set():
    kk = _elig(_plan(_stages(asthma="bheda")))["kriya_kala"]
    assert kk["advisory_only"] is True
    assert kk["reviewed"] is False
    assert kk["source"] == "checkin_disease_stage"


@pytest.mark.parametrize("stage", ["sanchaya", "prakopa", "bheda"])
def test_out_of_window_note_says_the_plan_is_unchanged(stage):
    """A misalignment notice beside a verdict is read as a reason for it unless it
    says otherwise in itself — the same failure the Rajaswala deferral string had to
    avoid."""
    kk = _elig(_plan(_stages(asthma=stage)))["kriya_kala"]
    assert kk["alignment"] in ("premature", "advanced")
    assert "does not change this plan" in kk["note"]
    assert "Vaidya" in kk["note"]


# ── Which condition governs ───────────────────────────────────────────────────

def test_bheda_is_not_masked_by_an_in_window_condition():
    """Bheda governs whenever present. The window is a middle band, so "worst" is
    not well defined — but Bheda is the finding a Vaidya must see, and letting a
    conveniently in-window condition speak for the patient would bury it."""
    kk = _elig(_plan(_stages(asthma="vyakti", arthritis="bheda")))["kriya_kala"]
    assert kk["governing_stage"] == "bheda"
    assert kk["governing_condition"] == "arthritis"
    assert kk["alignment"] == "advanced"


def test_most_advanced_in_window_condition_governs():
    kk = _elig(_plan(_stages(a="prasara", b="vyakti", c="prakopa")))["kriya_kala"]
    assert kk["governing_stage"] == "vyakti"
    assert kk["alignment"] == "in_window"


def test_all_early_reads_as_premature():
    kk = _elig(_plan(_stages(a="sanchaya", b="prakopa")))["kriya_kala"]
    assert kk["alignment"] == "premature"
    assert kk["governing_stage"] == "prakopa"


def test_every_staged_condition_is_listed():
    kk = _elig(_plan(_stages(a="vyakti", b="sanchaya", c="bheda")))["kriya_kala"]
    assert {s["condition"] for s in kk["stages"]} == {"a", "b", "c"}
    assert {c["condition"] for c in kk["out_of_window_conditions"]} == {"b", "c"}


def test_unrecognised_stage_is_dropped_not_guessed():
    assert _kriya_kala_assessment({"disease_stages": {"a": {"kriya_kala": "wat"}}}) is None
    assert _kriya_kala_assessment({"disease_stages": {"a": {}}}) is None
    assert _kriya_kala_assessment({"disease_stages": "not a dict"}) is None
    mixed = _kriya_kala_assessment({"disease_stages": {
        "a": {"kriya_kala": "wat"}, "b": {"kriya_kala": "vyakti"}}})
    assert [s["condition"] for s in mixed["stages"]] == ["b"]


# ── Anti-drift against the KB and the producer ────────────────────────────────

def test_window_matches_the_kb_prose():
    """The guard that would have caught the original defect: the window lives in code
    and the criterion lives in prose, so a test has to hold them together."""
    criteria = json.loads(KB.read_text())["shodhana_eligibility"]["shodhana_candidate_criteria"]
    line = next(c for c in criteria if c.lower().startswith("kriya kala"))
    named = {s for s in _KRIYA_KALA_ORDER if s in line.lower()}
    assert named == set(_KRIYA_KALA_SHODHANA_WINDOW), (
        f"KB names {named}, code holds {set(_KRIYA_KALA_SHODHANA_WINDOW)}: {line}")


def test_kriya_kala_is_absent_from_shamana_only_criteria():
    """The load-bearing premise of the advisory-not-a-gate decision. If a Vaidya ever
    adds a stage to `shamana_only_criteria`, this fails and the decision is revisited
    rather than silently contradicted."""
    shamana_only = " ".join(
        pk_protocols["shodhana_eligibility"]["shamana_only_criteria"]).lower()
    for stage in _KRIYA_KALA_ORDER:
        assert stage not in shamana_only, (
            f"'{stage}' now appears in shamana_only_criteria — Kriya Kala is no longer "
            "advisory and _kriya_kala_assessment must gate the verdict")
    assert "kriya kala" not in shamana_only


def test_every_stage_the_producer_can_emit_is_consumable():
    """`bheda` reached production emittable and unreadable: `_KRIYA_KALA_MAP` produces
    it for 5y+ worsening and it appeared in no KB file and no engine. Every stage the
    check-in can produce must have a label and an alignment here."""
    for stage in set(_KRIYA_KALA_MAP.values()):
        assert stage in _KRIYA_KALA_ORDER, f"{stage} is emitted but unknown to the engine"
        kk = _kriya_kala_assessment({"disease_stages": _stages(a=stage)})
        assert kk is not None and kk["note"]
        assert kk["alignment"] in ("in_window", "premature", "advanced")


def test_all_six_candidate_criteria_are_implemented():
    """The probe that found this, frozen. Each criterion must name a mechanism that
    exists — the Kriya Kala line had none, and the sub-key it sits in was read by no
    code at all."""
    import inspect
    import services.panchakarma_engine as eng
    src = inspect.getsource(eng)
    criteria = pk_protocols["shodhana_eligibility"]["shodhana_candidate_criteria"]
    assert len(criteria) == 6
    mechanisms = {
        "bala":       "bala_type",
        "agni":       "agni_correction_needed",
        "ama":        "ama_correction_mandatory",
        "kriya kala": "_kriya_kala_assessment",
        "season":     "_get_ritu_context",
        "age":        "outside Shodhana range",
    }
    for key, token in mechanisms.items():
        assert any(c.lower().startswith(key) for c in criteria), f"KB no longer states {key}"
        assert token in src, f"criterion '{key}' has no implementation ({token} absent)"
