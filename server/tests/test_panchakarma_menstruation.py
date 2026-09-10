"""Rajaswala — `contraindication_matrix.menstruation` reaching the plan.

The matrix carries six clinical entries. Five were wired into the eligibility
verdict; `menstruation` was not, and the input it needs (`menstrual_phase`) was
collected on the weekly check-in, used to nudge the Pitta score, and then dropped
before anything persisted it. The result was that the one feature which schedules
emesis, purgation and bloodletting had no way to know.

These tests hold three things: that the gate fires, that it *lifts* (it is the only
eligibility input that expires — a gate that never opens is a lockout, not a safety
feature), and that the KB stays the source of the rule.
"""
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pytest

from services.panchakarma_engine import (
    _MENSTRUAL_OBSERVATION_DAYS,
    _menstruation_active,
    generate_panchakarma_plan,
    pk_protocols,
)

KB = Path(__file__).resolve().parent.parent / "data" / "knowledge_base" / "panchakarma_protocols.json"


def _now():
    return datetime.now(timezone.utc)


def _profile(**over):
    p = dict(
        age=32, gender="female", bmi=23.0,
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


def _plan(**over):
    return generate_panchakarma_plan(_profile(**over), _prefs())


# ── The gate fires ────────────────────────────────────────────────────────────

def test_menstruation_withholds_shodhana():
    plan = _plan(menstrual_phase=True, menstrual_phase_at=_now())
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana"


def test_the_three_blocked_karmas_are_not_scheduled():
    """The matrix blocks Vamana, strong Virechana and Raktamokshana by name. This
    profile (Kapha, clinic, eligible) is the textbook Vamana candidate and receives
    Vamana when not menstruating — so the absence below is the gate, not the pool."""
    without = _plan()
    assert without["clinical_decisions"]["pradhana_karma_selected"]["primary"] == "vamana"

    during = _plan(menstrual_phase=True, menstrual_phase_at=_now())
    assert during["clinical_decisions"]["pradhana_karma_selected"]["primary"] is None

    blocked = {"vamana", "virechana", "raktamokshana"}
    for day in during["daily_schedule"]:
        for therapy in day.get("therapies") or []:
            tid = (therapy.get("id") or "").lower()
            assert not any(b in tid for b in blocked), f"day {day['day']} still schedules {tid}"


def test_the_reason_says_it_is_temporary():
    """Shamana is otherwise reserved for cancer, Atidurbala and age — a woman reading
    the verdict must not conclude she is permanently ineligible."""
    reasons = _plan(menstrual_phase=True, menstrual_phase_at=_now())[
        "clinical_decisions"]["shodhana_or_shamana"]["blocking_reasons"]
    reason = next(r for r in reasons if "menstruation" in r.lower())
    assert "deferral, not a disqualification" in reason
    assert "check-in" in reason


def test_deferral_banner_uses_the_existing_shape():
    """Same keys the acute-fever deferral uses — `PanchakarmaView` renders exactly
    these and nothing else."""
    deferral = _plan(menstrual_phase=True, menstrual_phase_at=_now())["clinical_decisions"]["deferral"]
    assert deferral is not None
    assert set(deferral) == {"reason", "notice", "resume_when", "source"}
    assert "Rajaswala" in deferral["reason"]


def test_banner_does_not_leak_kb_ids_at_the_patient():
    """`allowed` is keyed by therapy id; the notice is read by a patient."""
    notice = _plan(menstrual_phase=True, menstrual_phase_at=_now())["clinical_decisions"]["deferral"]["notice"]
    assert "pratimarsha_nasya" not in notice
    assert "Pratimarsha Nasya" in notice


def test_delay_sentence_is_terminated():
    """The KB authors `delay` without a full stop and the engine concatenates it."""
    reasons = _plan(menstrual_phase=True, menstrual_phase_at=_now())[
        "clinical_decisions"]["shodhana_or_shamana"]["blocking_reasons"]
    reason = next(r for r in reasons if "menstruation" in r.lower())
    assert "Shodhana This is" not in reason
    assert "for Shodhana. This is" in reason


def test_fever_outranks_menstruation_in_the_single_banner():
    """Both can be true and there is one banner. Fever's wait is open-ended."""
    plan = _plan(medical_history=["active_fever"], menstrual_phase=True, menstrual_phase_at=_now())
    assert "fever" in plan["clinical_decisions"]["deferral"]["reason"].lower()
    # ...and the menstruation block is not lost by losing the banner.
    reasons = plan["clinical_decisions"]["shodhana_or_shamana"]["blocking_reasons"]
    assert any("menstruation" in r.lower() for r in reasons)


# ── The gate lifts ────────────────────────────────────────────────────────────

def test_reporting_the_end_of_the_period_lifts_it_immediately():
    plan = _plan(menstrual_phase=False, menstrual_phase_at=_now())
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shodhana"
    assert plan["clinical_decisions"]["deferral"] is None


def test_a_stale_observation_lifts_on_its_own():
    """One check-in must not bar a woman from Shodhana indefinitely."""
    stale = _now() - timedelta(days=_MENSTRUAL_OBSERVATION_DAYS + 2)
    plan = _plan(menstrual_phase=True, menstrual_phase_at=stale)
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shodhana"


@pytest.mark.parametrize("delta,expected", [
    (timedelta(0), True),
    (timedelta(days=1), True),
    # The window is inclusive of its last day and expires just past it.
    (timedelta(days=_MENSTRUAL_OBSERVATION_DAYS, minutes=-1), True),
    (timedelta(days=_MENSTRUAL_OBSERVATION_DAYS, minutes=1), False),
    (timedelta(days=30), False),
])
def test_observation_window_boundaries(delta, expected):
    at = _now() - delta
    assert _menstruation_active({"menstrual_phase": True, "menstrual_phase_at": at}) is expected


def test_absent_flag_changes_nothing():
    """The overwhelming majority of profiles have never checked in with this."""
    assert _menstruation_active({}) is False
    assert _menstruation_active({"menstrual_phase": None}) is False


# ── Shape tolerance ───────────────────────────────────────────────────────────

def test_undated_flag_is_honoured():
    """Failing open on a contraindication because a timestamp is missing is the
    wrong direction — profiles written before `menstrual_phase_at` existed, and
    callers passing the state directly, still gate."""
    assert _menstruation_active({"menstrual_phase": True}) is True
    assert _menstruation_active({"menstrual_phase": True, "menstrual_phase_at": "not-a-date"}) is True


def test_naive_datetime_does_not_raise():
    """Mongo hands back naive UTC datetimes; comparing to an aware `now` raises."""
    naive = datetime.now(timezone.utc).replace(tzinfo=None)
    assert _menstruation_active({"menstrual_phase": True, "menstrual_phase_at": naive}) is True


def test_iso_string_is_parsed():
    fresh = _now().isoformat()
    stale = (_now() - timedelta(days=_MENSTRUAL_OBSERVATION_DAYS + 2)).isoformat()
    assert _menstruation_active({"menstrual_phase": True, "menstrual_phase_at": fresh}) is True
    assert _menstruation_active({"menstrual_phase": True, "menstrual_phase_at": stale}) is False


# ── The KB stays the source ───────────────────────────────────────────────────

def test_every_contraindication_matrix_entry_is_wired():
    """The guard that would have caught this. `menstruation` sat in the matrix
    unread while its five siblings were implemented; nothing failed."""
    matrix = pk_protocols["contraindication_matrix"]
    entries = [k for k, v in matrix.items() if isinstance(v, dict)]
    src = (Path(__file__).resolve().parent.parent / "services" / "panchakarma_engine.py").read_text().lower()
    unwired = [k for k in entries if k.lower() not in src]
    assert not unwired, f"contraindication_matrix entries no code reads: {unwired}"


def test_rule_is_read_from_the_kb_not_hardcoded():
    """If the Vaidya changes the allowed list, the notice must change with it."""
    matrix = json.loads(KB.read_text())["contraindication_matrix"]["menstruation"]
    deferral = _plan(menstrual_phase=True, menstrual_phase_at=_now())["clinical_decisions"]["deferral"]
    for karma in matrix["blocked"]:
        assert karma in deferral["source"]
    for allowed in matrix["allowed"]:
        assert allowed.replace("_", " ").title() in deferral["notice"]
