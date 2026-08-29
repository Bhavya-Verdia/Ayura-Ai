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


# ── The KB's escalation line reaches the user ─────────────────────────────────
#
# `consult_doctor_if` is authored on all 60 home-remedy entries and was read by
# exactly one thing: `scripts/build_vectors.py`. It was embedded into the RAG corpus
# for the model and rendered to nobody. For 38 of the served remedies no other field
# carried the same information either — their `red_flags` are empty — so the sentence
# telling someone the home remedy has stopped being the right answer reached them
# through no channel at all.

def _kb():
    from services.remedy_engine import _REMEDIES_FALLBACK
    return _REMEDIES_FALLBACK


def _profile(**over):
    p = {"dominant_dosha": "pitta", "secondary_dosha": "vata"}
    p.update(over)
    return p


def test_every_kb_entry_still_carries_an_escalation_line():
    """The fix is only worth anything while the KB holds these. If an entry loses its
    line, the card silently renders without one."""
    missing = [r["symptom_id"] for r in _kb() if not (r.get("consult_doctor_if") or "").strip()]
    assert not missing, f"entries with no consult_doctor_if: {missing}"


def test_a_served_remedy_carries_its_escalation_line():
    from services.remedy_engine import filter_remedies
    for entry in _kb():
        sym = entry["symptom_id"]
        out = filter_remedies(_profile(), {"symptoms": [sym], "severity": {sym: "mild"}})
        if not out or out[0].get("action"):
            continue          # referred rather than served; covered below
        assert out[0].get("consult_doctor_if") == entry["consult_doctor_if"], \
            f"{sym}: served remedy did not carry its escalation line"


def test_a_referral_carries_the_specific_warning_not_only_the_generic_one():
    """A referral is where the specific trigger matters most, and the generic
    "requires immediate medical attention" is the one sentence that cannot carry it."""
    from services.remedy_engine import filter_remedies
    out = filter_remedies(_profile(), {"symptoms": ["migraine"], "severity": {"migraine": "severe"}})
    assert out and out[0]["action"] == "see_doctor"
    assert "vision loss" in out[0]["consult_doctor_if"]


def test_a_severe_symptom_the_kb_does_not_hold_is_still_referred():
    """The KB lookup moved above the severity gate so a referral could carry the
    escalation line. The gate must still fire for a symptom with no KB entry — that
    is precisely when a referral matters — and must not crash looking for a line
    that does not exist."""
    from services.remedy_engine import filter_remedies
    out = filter_remedies(_profile(), {"symptoms": ["not_a_known_symptom"],
                                       "severity": {"not_a_known_symptom": "severe"}})
    assert out and out[0]["action"] == "see_doctor"
    assert out[0]["consult_doctor_if"] == ""


def test_severity_gate_is_surfaced_as_a_label_and_gates_nothing():
    """`severity_gate` is NOT a ceiling on treatment, and reading it as one would be a
    safety error in the confident direction.

    The evidence is in the KB: `ojas_building` and `seasonal_detox` carry "mild" and
    have no severity at all; `diabetes_lifestyle` carries "moderate" while
    `hypothyroid_support` carries "mild", which as a ceiling would mean home-treating
    moderate diabetes but only mild hypothyroidism; and the graver complaints
    correlate WITH `use_with_caution` remedies rather than against them. It labels how
    serious the complaint is. So it is surfaced under an honest name and no remedy is
    withheld on it — a moderate report is served exactly as a mild one is.
    """
    from services.remedy_engine import filter_remedies
    mild_gated = next(r for r in _kb()
                      if r["severity_gate"] == "mild" and r["symptom_id"] == "headache")
    served = {}
    for sev in ("mild", "moderate"):
        out = filter_remedies(_profile(), {"symptoms": ["headache"], "severity": {"headache": sev}})
        assert out and not out[0].get("action"), f"headache was withheld at {sev}"
        served[sev] = out[0]["remedy"]["name"]
        assert out[0]["symptom_seriousness"] == mild_gated["severity_gate"]
    assert served["mild"] == served["moderate"]


# ── Severity is no longer a badge ─────────────────────────────────────────────

def test_moderate_severity_decided_nothing_and_now_does():
    """`severity` is a three-value field and `moderate` was inert: `severe` was a
    referral, and everything below it produced byte-identical output at every
    duration. The practitioner threshold is the only lever it has left — `severe` is
    already referred, and the KB holds exactly one remedy per (symptom, dosha) plus a
    universal, so there is no stronger preparation to escalate a moderate case to."""
    from services.remedy_engine import filter_remedies
    prof = {"dominant_dosha": "pitta", "secondary_dosha": "vata"}

    def triage(sev, dur):
        out = filter_remedies(prof, {"symptoms": ["headache"],
                                     "severity": {"headache": sev},
                                     "duration": {"headache": dur}})[0]
        return out.get("action"), out.get("requires_practitioner")

    # the cell the change exists for
    assert triage("mild", "weeks") == (None, False)
    assert triage("moderate", "weeks") == (None, True)

    # and nothing else moved
    assert triage("mild", "recent") == (None, False)
    assert triage("moderate", "recent") == (None, False)
    for dur in ("months", "chronic"):
        assert triage("mild", dur) == (None, True)
        assert triage("moderate", dur) == (None, True)
    for dur in ("recent", "weeks", "months", "chronic"):
        assert triage("severe", dur)[0] == "see_doctor"


def test_the_practitioner_note_says_which_trigger_fired():
    """The view printed "Chronic/long-duration symptom" whatever the cause, which is
    the wrong sentence for a moderate complaint of a fortnight."""
    from services.remedy_engine import filter_remedies
    prof = {"dominant_dosha": "pitta", "secondary_dosha": "vata"}

    weeks = filter_remedies(prof, {"symptoms": ["headache"],
                                   "severity": {"headache": "moderate"},
                                   "duration": {"headache": "weeks"}})[0]
    assert "moderate" in weeks["practitioner_reason"].lower()
    assert "weeks" in weeks["practitioner_reason"].lower()

    months = filter_remedies(prof, {"symptoms": ["headache"],
                                    "severity": {"headache": "mild"},
                                    "duration": {"headache": "months"}})[0]
    assert "months" in months["practitioner_reason"].lower()
    assert months["practitioner_reason"] != weeks["practitioner_reason"]


def test_no_reason_is_emitted_when_no_note_is_shown():
    """A reason without a note is dead text that a future view might render."""
    from services.remedy_engine import filter_remedies
    out = filter_remedies({"dominant_dosha": "pitta", "secondary_dosha": "vata"},
                          {"symptoms": ["headache"], "severity": {"headache": "mild"},
                           "duration": {"headache": "recent"}})[0]
    assert out["requires_practitioner"] is False
    assert out["practitioner_reason"] == ""


def test_every_severity_duration_pair_has_a_defined_outcome():
    """A triage matrix with an undefined cell is where a symptom falls through."""
    import itertools
    from services.remedy_engine import filter_remedies
    prof = {"dominant_dosha": "pitta", "secondary_dosha": "vata"}
    for sev, dur in itertools.product(["mild", "moderate", "severe"],
                                      ["recent", "weeks", "months", "chronic"]):
        out = filter_remedies(prof, {"symptoms": ["headache"],
                                     "severity": {"headache": sev},
                                     "duration": {"headache": dur}})
        assert out, f"{sev}/{dur} produced nothing at all"
        r = out[0]
        assert r.get("action") == "see_doctor" or "requires_practitioner" in r
