"""Remedies triage inputs — severity, duration and taste preference.

Flagged since 2026-08-19 as "declared, read by no code, collected by no UI" and left
as a product call. Re-probing found the picture was more specific than that, and in
one place worse:

  * The severity gate WORKS on the per-feature path — the Remedies page collects
    severity per symptom and sends it in the request body, and a severe symptom
    returns a doctor referral instead of a remedy.
  * It could not fire on the HOLISTIC path at all. That path built
    `{"symptoms": [...]}` with no severity and no duration, so every symptom
    defaulted to `mild` / `recent` inside `filter_remedies` and a user whose
    recorded symptom was severe was handed a home remedy for it.
  * `follow_up` was one fixed sentence for everybody.
  * `preference_taste_smell` was genuinely read by nothing anywhere.
"""
import pytest

from services.remedy_engine import (
    _REMEDIES_FALLBACK,
    build_remedy_plan,
    filter_remedies,
)


def _profile(**over):
    base = dict(
        id="t", age=40, gender="female", dominant_dosha="pitta", vikriti_dominant="pitta",
        medical_history=[], current_medications=[], allergies=[], pregnancy_or_nursing=False,
    )
    base.update(over)
    return base


def _plan(symptom_input, profile=None):
    profile = profile or _profile()
    return build_remedy_plan(filter_remedies(profile, symptom_input), profile, symptom_input)


# ── Severity ──────────────────────────────────────────────────────────────────

def test_a_severe_symptom_returns_a_referral_not_a_remedy():
    plan = _plan({"symptoms": ["acidity"], "severity": {"acidity": "severe"}, "duration": {}})
    assert plan["doctor_referrals"], "severe must escalate"
    assert not plan["symptoms_addressed"]


def test_severity_is_per_symptom_not_global():
    """The field is a dict — one symptom being severe must not withhold the remedy
    for a mild one, and must not fail to escalate itself."""
    plan = _plan({
        "symptoms": ["acidity", "headache"],
        "severity": {"acidity": "severe", "headache": "mild"},
        "duration": {},
    })
    assert len(plan["doctor_referrals"]) == 1
    assert len(plan["symptoms_addressed"]) == 1


def test_the_holistic_path_supplies_severity_from_stored_preferences():
    """The gap this file exists for. `_generate_feature_via_engine` built
    `{"symptoms": [...]}` and nothing else, so `filter_remedies` defaulted every
    symptom to `mild` and the escalation could not happen on a holistic plan.

    Asserted against the engine contract rather than the route, because the defect
    was the SHAPE of what the route passed.
    """
    without = _plan({"symptoms": ["acidity"]})
    assert not without["doctor_referrals"], "no severity means the default, mild"

    with_stored = _plan({"symptoms": ["acidity"], "severity": {"acidity": "severe"}})
    assert with_stored["doctor_referrals"], "stored severity must reach the gate"


# ── Duration and follow-up ────────────────────────────────────────────────────

@pytest.mark.parametrize("duration", ["recent", "weeks", "months", "chronic"])
def test_the_follow_up_reflects_how_long_it_has_been_going_on(duration):
    """It was one fixed sentence — "If symptoms persist beyond 7 days" — printed to
    everybody. Told to somebody whose symptom has run for three months it is advice
    eleven weeks out of date, and it reads as reassurance at the exact moment the
    plan should be escalating."""
    plan = _plan({"symptoms": ["acidity"], "severity": {}, "duration": {"acidity": duration}})
    advice = plan["follow_up"]
    assert advice

    if duration == "recent":
        assert "7 days" in advice
    else:
        assert "7 days" not in advice or "has passed" in advice
        assert "practitioner" in advice.lower()


def test_the_follow_up_is_keyed_to_the_longest_running_symptom():
    """Telling somebody with a three-month complaint and a three-day one to "wait a
    week" answers only the easier half."""
    plan = _plan({
        "symptoms": ["acidity", "headache"],
        "severity": {},
        "duration": {"acidity": "months", "headache": "recent"},
    })
    assert "months" in plan["follow_up"] or "not a self-care case" in plan["follow_up"]


def test_a_referral_leads_the_follow_up():
    plan = _plan({
        "symptoms": ["acidity"],
        "severity": {"acidity": "severe"},
        "duration": {"acidity": "chronic"},
    })
    assert plan["follow_up"].startswith("One or more of your symptoms needs medical attention now")


def test_every_duration_produces_distinct_advice():
    """Four buckets that all say the same thing would be the original defect in a
    longer form."""
    advice = {
        d: _plan({"symptoms": ["acidity"], "severity": {}, "duration": {"acidity": d}})["follow_up"]
        for d in ("recent", "weeks", "months", "chronic")
    }
    assert len(set(advice.values())) == 4


# ── Taste and smell ───────────────────────────────────────────────────────────

def test_a_taste_preference_flags_the_clash_without_removing_the_remedy():
    """Each symptom usually has one remedy per Dosha, so excluding on taste would
    often leave nothing — and a preference must not cost somebody their treatment."""
    plain = filter_remedies(_profile(), {"symptoms": ["acidity"]})
    fussy = filter_remedies(
        _profile(), {"symptoms": ["acidity"], "preference_taste_smell": ["no_bitter"]})

    assert len(plain) == len(fussy), "the remedy must survive the preference"
    assert fussy[0].get("taste_notices"), "and the clash must be stated"


def test_the_notice_names_the_ingredient_and_the_classical_masking():
    """Ayurveda has a real answer: Anupana — the vehicle a medicine is taken with —
    is chosen partly to make it palatable. Reporting the clash without it would be
    a complaint rather than help."""
    results = filter_remedies(
        _profile(), {"symptoms": ["acidity"], "preference_taste_smell": ["no_bitter"]})
    notice = results[0]["taste_notices"][0]
    assert "aloe vera" in notice
    assert "Anupana" in notice


def test_both_preference_kinds_can_fire():
    profile = _profile(dominant_dosha="vata")
    every_symptom = [r["symptom_id"] for r in _REMEDIES_FALLBACK]
    results = filter_remedies(profile, {
        "symptoms": every_symptom,
        "preference_taste_smell": ["no_bitter", "no_strong_smell"],
    })
    notices = [n for r in results for n in (r.get("taste_notices") or [])]
    assert any("bitter" in n for n in notices)
    assert any("strongly scented" in n for n in notices)


def test_no_preference_means_no_noise():
    """The notice has to mean something, so it cannot appear on every remedy."""
    results = filter_remedies(_profile(), {"symptoms": ["acidity", "headache"]})
    assert not any(r.get("taste_notices") for r in results)


def test_a_taste_preference_never_changes_which_remedy_is_chosen():
    """It is a preference, not a filter. The remedy is selected on Dosha and safety;
    taste only annotates it."""
    plain = filter_remedies(_profile(), {"symptoms": ["acidity"]})
    fussy = filter_remedies(
        _profile(), {"symptoms": ["acidity"], "preference_taste_smell": ["no_bitter"]})
    assert plain[0]["remedy"]["name"] == fussy[0]["remedy"]["name"]
