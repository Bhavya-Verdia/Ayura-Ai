"""Panchakarma engine — plan-level behaviour.

The engine had no test file at all until this one. Its clinical reasoning layer was
never the weak part: the eligibility verdict, the Bala/Agni/Ama/Ojas assessment and
the per-Karma contraindication matrix were all computed correctly and then ignored
by the code that built the schedule. Every profile — age 78, severe Ama, low Ojas,
a cancer diagnosis, pregnancy — produced a byte-identical plan telling the patient
to take 30-60ml of castor oil on day six.

So these tests assert on the *plan*, not on the verdict. A test that checked
`eligibility["type"] == "shamana"` would have passed throughout.
"""
import pytest

from services.panchakarma_engine import generate_panchakarma_plan


def _profile(**over):
    base = dict(
        id="t", age=35, gender="female",
        dominant_dosha="pitta", vikriti_dominant="pitta",
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


def _all_text(plan) -> str:
    """Every string a patient could read off the schedule, lowercased."""
    parts = []
    for day in plan["daily_schedule"]:
        for t in day["therapies"]:
            parts += [str(t.get("name", "")), str(t.get("pradhana_notes", "")),
                      str(t.get("benefits", "")), str(t.get("timing", ""))]
    return " ".join(parts).lower()


# The instructions that must never reach a clinically ineligible patient. These are
# procedure names and the words the engine uses to instruct someone through one —
# a plan that avoids the word "Virechana" but still says "purgation begins in 4-8
# hours" has not withheld anything.
SHODHANA_INSTRUCTIONS = [
    "vamana", "virechana", "basti", "raktamokshana", "nasya",
    "purgation", "emesis", "enema", "vega", "castor oil", "trivrit",
    "madanaphala", "samsarjana", "snehapana",
]

# Profiles the KB's `shamana_only_criteria` and `contraindication_matrix` place
# outside Shodhana at any strength.
#
# High and severe Ama used to be listed here and are not, because the criterion
# they were read from is qualified: `shamana_only_criteria` bars "High Ama
# **without prior Deepana-Pachana**", exactly as it bars "Manda Agni **without
# correction**". They belong to CORRECTION_FIRST below. Listing them here is what
# these tests originally asserted, and the assertion passed while the engine issued
# a plan containing seven days of the very correction it had just ruled impossible.
INELIGIBLE = [
    pytest.param(_profile(age=78), id="elderly"),
    pytest.param(_profile(age=5), id="very_young"),
    pytest.param(_profile(pregnancy_or_nursing=True), id="pregnancy"),
    pytest.param(_profile(bmi=15.2), id="atidurbala"),
    pytest.param(_profile(medical_history=["anemia"]), id="anemia"),
    pytest.param(_profile(medical_history=["active_fever"]), id="active_fever"),
    pytest.param(_profile(medical_history=["cancer"]), id="severe_unmapped"),
]

# States the KB requires to be CORRECTED before Shodhana, not states that forbid it.
# Every one of them is a reason to schedule Deepana-Pachana first.
CORRECTION_FIRST = [
    pytest.param(_profile(ama_indicator="high"), "ama_correction_needed", id="high_ama"),
    pytest.param(_profile(ama_indicator="severe"), "ama_correction_needed", id="severe_ama"),
    pytest.param(_profile(digestion_quality="poor"), "agni_correction_needed", id="manda_agni"),
]


@pytest.mark.parametrize("profile,flag", CORRECTION_FIRST)
def test_a_correctable_state_is_corrected_rather_than_used_to_refuse(profile, flag):
    """The correction is scheduled AND the verdict waits for it.

    High Ama blocked Shodhana outright while the plan it produced still opened with
    a Deepana-Pachana phase: the correction ran, and the verdict taken before the
    correction still stood. A Kapha patient with high Ama, high Ojas, Uttama Bala
    and three prior courses — the textbook Vamana candidate, high Ama being the
    substance Vamana exists to expel — was told he was clinically ineligible.
    """
    plan = generate_panchakarma_plan(profile, _prefs(available_time_days=21))
    elig = plan["clinical_decisions"]["shodhana_or_shamana"]

    assert elig["type"] != "shamana", "a correctable state is not an eligibility bar"
    assert elig[flag], "the state must still be recorded as needing correction"

    phases = plan["phase_breakdown"]["phases"]
    assert phases[0]["key"] == "deepana_pachana", "the correction must come first"
    assert plan["phase_breakdown"]["deepana_pachana_days"] >= 3


def test_high_ama_earns_a_longer_correction_than_mild():
    """`ama_correction_first` gives a 3-7 day range; the grade decides where in it.

    The floor and the scheduled length have to be the same number. They were not:
    the phase was costed at five days and three were scheduled.
    """
    prefs = _prefs(available_time_days=10)
    mild = generate_panchakarma_plan(_profile(ama_indicator="mild"), prefs)
    high = generate_panchakarma_plan(_profile(ama_indicator="high"), prefs)

    assert high["phase_breakdown"]["deepana_pachana_days"] > \
        mild["phase_breakdown"]["deepana_pachana_days"]

    deepana = next(p for p in high["phase_breakdown"]["phases"] if p["key"] == "deepana_pachana")
    assert deepana["days"] == high["phase_breakdown"]["deepana_pachana_days"]


def test_the_ama_verdict_names_the_sign_that_gates_it_not_only_the_days():
    """Days are a guide; `signs_ama_cleared` is the gate, and the patient needs it."""
    plan = generate_panchakarma_plan(_profile(ama_indicator="high"), _prefs())
    elig = plan["clinical_decisions"]["shodhana_or_shamana"]

    assert elig["ama_correction_mandatory"] is True
    assert elig["ama_correction_signs"], "the signs must travel with the verdict"
    assert any("sign" in r.lower() for r in elig["reasons"]), \
        "the verdict must say the course waits on the signs, not on the day count"


@pytest.mark.parametrize("profile", INELIGIBLE)
@pytest.mark.parametrize("setting", ["home", "clinic", "both"])
def test_the_ineligible_are_given_no_shodhana_instruction_in_any_setting(profile, setting):
    """The verdict must reach the schedule, in every setting.

    `setting == "home"` used to return "shamana" before a single clinical criterion
    was examined, so a home user's age, Ama, Ojas and pregnancy were never checked
    at all — and the mild home purgation went out regardless.
    """
    plan = generate_panchakarma_plan(profile, _prefs(setting=setting))

    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana"
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] is None

    text = _all_text(plan)
    leaked = [w for w in SHODHANA_INSTRUCTIONS if w in text]
    assert not leaked, f"Shodhana instruction reached an ineligible patient: {leaked}"


@pytest.mark.parametrize("profile", INELIGIBLE)
def test_an_ineligible_patient_still_gets_a_usable_plan(profile):
    """Withholding the cleanse must not leave a hole where the plan was.

    The point of the Shamana arm is that these patients have a real imbalance and
    a real treatment for it; returning an empty schedule would make the safe path
    the useless one.
    """
    prefs = _prefs()
    plan = generate_panchakarma_plan(profile, prefs)

    assert len(plan["daily_schedule"]) == prefs["available_time_days"]
    assert all(d["therapies"] for d in plan["daily_schedule"])

    sp = plan["shamana_protocol"]
    assert sp is not None
    assert sp["blocking_reasons"], "the plan must say why purification was withheld"
    assert sp["shamana_chikitsa"]["ahara"]
    assert sp["shamana_chikitsa"]["vihara"]
    assert sp["brimhana"]["rasayana"]

    phases = [p["key"] for p in plan["phase_breakdown"]["phases"]]
    assert phases[-1] == "brimhana", "a Shamana plan ends in nourishment"


def test_ama_schedules_the_correction_it_demands():
    """`ama_correction_first` puts Deepana-Pachana "before starting Snehana".

    Mild/moderate Ama used to raise a banner saying Ama must be cleared first, above
    a schedule that began with Snehana on day one. The days are the assertion.
    """
    plan = generate_panchakarma_plan(_profile(ama_indicator="moderate"), _prefs())

    phases = [p["key"] for p in plan["phase_breakdown"]["phases"]]
    assert phases[0] == "deepana_pachana"
    assert phases.index("deepana_pachana") < phases.index("purvakarma")

    first_day = plan["daily_schedule"][0]
    assert "Deepana-Pachana" in first_day["phase"]
    assert first_day["therapies"][0]["is_deepana_pachana"] is True

    # Oleation cannot appear inside the phase whose purpose is to precede it.
    deepana_text = " ".join(
        t["name"] for d in plan["daily_schedule"] if "Deepana" in d["phase"] for t in d["therapies"]
    ).lower()
    assert "oleation" not in deepana_text and "snehapana" not in deepana_text


def test_manda_agni_schedules_dipana_before_the_cleanse():
    """`contraindication_matrix.manda_agni` requires Dipana for 5-7 days first."""
    plan = generate_panchakarma_plan(
        _profile(agni_type="manda", ama_indicator="none"), _prefs()
    )
    phases = [p["key"] for p in plan["phase_breakdown"]["phases"]]
    assert phases[0] == "deepana_pachana"


def test_low_ojas_keeps_the_nourishing_route_and_loses_the_expulsive_one():
    """Low Ojas restricts rather than blocks.

    Matra Basti IS the classical treatment for depletion — `atidurbala` in the
    contraindication matrix allows it by name — so barring it would withhold the
    indicated therapy. What must go is anything that expels.
    """
    depleted_vata = _profile(dominant_dosha="vata", vikriti_dominant="vata", ojas_level="low")
    plan = generate_panchakarma_plan(depleted_vata, _prefs())
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "mridu_shodhana"
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] == "basti_matra"

    # A Pitta maps to Virechana, which expels — that one must be substituted.
    depleted_pitta = _profile(ojas_level="low")
    plan = generate_panchakarma_plan(depleted_pitta, _prefs())
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]
    assert pk["primary"] in {"basti_matra", "nasya"}
    assert pk["original_karma"] == "virechana"
    assert "purgation" not in _all_text(plan)


def test_mridu_shodhana_is_mild_wherever_the_patient_booked():
    """A restricted patient who selects a clinic still gets the mild adaptations.

    Otherwise "Mridu Shodhana" is a label on a plan that schedules Niruha Basti at
    clinic strength — the verdict has to reach Karma selection, Basti subtype and
    drug strength, not just the badge.
    """
    beginner = _profile(dominant_dosha="vata", vikriti_dominant="vata", fitness_level="beginner")
    plan = generate_panchakarma_plan(beginner, _prefs(detox_experience="none"))

    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "mridu_shodhana"
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] == "basti_matra"
    assert plan["clinical_decisions"]["basti_subtype"]["subtype"] == "matra_basti"


def test_an_eligible_patient_still_gets_the_full_protocol():
    """The gates must not swallow the feature.

    Every test above withholds something; this one is the counterweight. A healthy,
    experienced patient in a clinic is exactly who full Shodhana is for.
    """
    plan = generate_panchakarma_plan(_profile(), _prefs())
    cd = plan["clinical_decisions"]

    assert cd["shodhana_or_shamana"]["type"] == "shodhana"
    assert cd["pradhana_karma_selected"]["primary"] == "virechana"
    assert plan["shamana_protocol"] is None
    assert plan["samsarjana_krama"], "post-Shodhana re-entry belongs on a Shodhana plan"
    assert plan["snehana_protocol"]["dose_schedule"], "Snehapana belongs on a Shodhana plan"

    pradhana_days = [d for d in plan["daily_schedule"] if "Pradhana" in d["phase"]]
    assert pradhana_days
    assert pradhana_days[0]["therapies"][0]["is_pradhana_karma"] is True


def test_the_day_count_matches_the_days_the_schedule_contains():
    """The phase strip and the calendar have to be the same plan.

    Asserted as a relationship rather than fixed numbers so that retuning the phase
    split cannot silently falsify it.
    """
    for days in (3, 5, 7, 10, 14, 21):
        for profile in (_profile(), _profile(age=78), _profile(ama_indicator="moderate")):
            plan = generate_panchakarma_plan(profile, _prefs(available_time_days=days))
            pb = plan["phase_breakdown"]
            phases, stated = pb["phases"], pb["total_days"]

            assert sum(p["days"] for p in phases) == stated
            assert len(plan["daily_schedule"]) == stated
            assert [d["day"] for d in plan["daily_schedule"]] == list(range(1, stated + 1))
            assert all(p["days"] >= 1 for p in phases), "a phase with zero days must not be shown"

            # The course may be longer than requested — a Shodhana has a floor — but
            # never silently. Overrunning the request without saying so is what made
            # a 3-day plan render as "3 days" above a five-day calendar.
            if stated != days:
                assert pb["duration_notice"], f"{days}d silently became {stated}d"
                assert str(days) in pb["duration_notice"]


def test_a_shamana_plan_does_not_advertise_the_therapy_it_withheld():
    """The Ritu calendar names a Shodhana for each season. On a plan that performs
    none, `ritu_warning` would be advice about a procedure that is not happening."""
    plan = generate_panchakarma_plan(_profile(age=78), _prefs())
    assert plan["clinical_decisions"]["ritu_warning"] is None
    assert "SHAMANA PROTOCOL" in plan["disclaimer"]


# ── Rare and unmapped conditions ──────────────────────────────────────────────

@pytest.mark.parametrize("condition", [
    "dialysis", "kidney_failure", "renal_failure", "hiv", "heart_failure",
])
def test_a_severe_condition_is_caught_even_when_the_vocabulary_knows_it(condition):
    """Severity was checked only across UNMAPPED conditions, so a severe diagnosis
    the vocabulary recognised cleared the check by being recognised.

    "dialysis", "kidney_failure" and "renal_failure" all normalise to
    chronic_kidney_disease, and "hiv" maps to itself. Every one of them was routed
    to a full Niruha Basti course with no Vaidya-review flag raised. Being mapped
    means the engine knows which Dosha the disease disturbs; it says nothing about
    whether the patient can withstand purification.
    """
    plan = generate_panchakarma_plan(_profile(medical_history=[condition]), _prefs())
    cd = plan["clinical_decisions"]

    assert cd["shodhana_or_shamana"]["type"] == "shamana"
    assert cd["pradhana_karma_selected"]["primary"] is None
    assert cd["vaidya_review_required"] is True
    assert any("VAIDYA REVIEW REQUIRED" in w for w in cd["safety_warnings"])
    assert not [w for w in SHODHANA_INSTRUCTIONS if w in _all_text(plan)]


@pytest.mark.parametrize("condition", [
    "wilsons_disease", "sjogrens", "sarcoidosis", "myasthenia_gravis", "behcets",
])
def test_an_unmapped_condition_gets_a_plan_that_admits_what_it_did_not_check(condition):
    """Every Aushadha gate matches condition TOKENS, so an unmapped condition matches
    none of them and therefore passes all of them. A Wilson's patient (copper
    accumulation) clears the Shilajit check because "wilsons_disease" is not a token
    any entry lists — the gate did not decide they were safe, it never saw them.

    The plan is still produced: withholding every medicine on an unrecognised word
    would strip the plan for a large and ordinary set of diagnoses. What it must not
    do is imply a clean check.
    """
    plan = generate_panchakarma_plan(_profile(medical_history=[condition]), _prefs())
    cd = plan["clinical_decisions"]

    assert cd["vaidya_review_required"] is True
    assert condition in cd["unmapped_conditions"]

    unverified = plan["aushadha"].get("unverified_against")
    assert unverified, "the plan must say the medicines were not checked against it"
    assert condition in unverified["conditions"]
    assert "NOT been checked" in unverified["notice"]

    # And it is still a usable plan, not an empty one.
    assert len(plan["daily_schedule"]) == plan["phase_breakdown"]["total_days"]
    assert all(d["therapies"] for d in plan["daily_schedule"])


def test_a_recognised_condition_carries_no_unverified_notice():
    """The counterweight: the notice must mean something, so it cannot appear on
    every plan."""
    for condition in ([], ["ankylosing_spondylitis"], ["diabetes_type2"], ["pcos"]):
        plan = generate_panchakarma_plan(_profile(medical_history=condition), _prefs())
        assert "unverified_against" not in plan["aushadha"]
        assert plan["clinical_decisions"]["vaidya_review_required"] is False


def test_ankylosing_spondylitis_gets_a_condition_specific_plan():
    """AS is the case the question was asked about. It is fully mapped, and the plan
    should reach the Asthi-Majja Gata Vata protocol rather than a generic Vata one:
    Basti (Ardhachikitsa for Vata), the AS-specific Kashayam, a joint-indicated oil
    and the bone/joint Rasayana."""
    plan = generate_panchakarma_plan(
        _profile(age=38, gender="male", dominant_dosha="vata", vikriti_dominant="vata",
                 medical_history=["ankylosing_spondylitis"]),
        _prefs(panchakarma_goal="specific_condition"))
    cd, aushadha = plan["clinical_decisions"], plan["aushadha"]

    assert cd["pradhana_karma_selected"]["primary"] in ("basti", "basti_matra")
    assert cd["vaidya_review_required"] is False

    generic = generate_panchakarma_plan(
        _profile(dominant_dosha="vata", vikriti_dominant="vata"), _prefs())["aushadha"]
    assert aushadha["basti_kashayam"]["name"] != generic["basti_kashayam"]["name"]
    assert aushadha["abhyanga_oil"]["name"] != generic["abhyanga_oil"]["name"]
    assert aushadha["rasayana"]["herb"] != generic["rasayana"]["herb"]


# ── Season ────────────────────────────────────────────────────────────────────

def test_the_ritu_agrees_with_the_seasonal_engine_the_rest_of_the_app_uses():
    """Panchakarma computed its own Ritu from `datetime.now().month` on whole-month
    boundaries while `engine/seasonal.py` — which yoga, diet and routine all read —
    uses mid-month transitions. The two disagreed on a QUARTER of the year: the first
    half of every odd month. On 10 March a user's yoga plan said Shishira and their
    Panchakarma plan said Vasanta, same day, same profile.

    It is not cosmetic. The Ritu selects the season's Shodhana from
    `ritu_shodhana_calendar`, so on that date a seasonal cleanse chose Vamana
    (Vasanta's Karma) while the rest of the app considered it still winter.
    """
    from datetime import date
    from unittest import mock

    import services.panchakarma_engine as engine
    from engine.seasonal import get_current_season

    alias = {"shishir": "shishira", "vasant": "vasanta", "hemant": "hemanta"}
    for month in range(1, 13):
        for day in (1, 10, 20, 28):
            with mock.patch("engine.seasonal.date") as fake:
                fake.today.return_value = date(2026, month, day)
                shared = get_current_season().name.lower()
                shared = alias.get(shared, shared)
                assert engine._current_ritu() == shared, f"{month:02d}-{day:02d}"


def test_the_season_preference_overrides_the_clock():
    """`current_season` was declared for exactly this and read by nothing. The
    server's clock is not necessarily in the user's hemisphere."""
    import services.panchakarma_engine as engine

    assert engine._current_ritu("grishma") == "grishma"
    assert engine._current_ritu("Vasant") == "vasanta"     # the seasonal engine's spelling
    assert engine._current_ritu("nonsense") == engine._current_ritu()  # falls back, never crashes

    plan = generate_panchakarma_plan(_profile(), _prefs(current_season="grishma"))
    assert plan["clinical_decisions"]["ritu_context"]["ritu"] == "grishma"


def test_an_extension_notice_accounts_for_every_day_it_added():
    """The phases the notice names must add up to the number in the same sentence.

    Deepana-Pachana was missing from this breakdown, so a patient who asked for 3
    days and was extended to 14 was told "Purvakarma 3, Virechana 1, Samsarjana 5"
    — five days short, in the sentence that quotes the total.
    """
    plan = generate_panchakarma_plan(
        _profile(ama_indicator="high"), _prefs(available_time_days=3))
    pb = plan["phase_breakdown"]

    notice = pb["duration_notice"]
    assert notice and notice.startswith("Extended from 3 to")

    named = {p["key"]: p["days"] for p in pb["phases"]}
    assert sum(named.values()) == pb["total_days"]
    assert named.get("deepana_pachana"), "the correction phase is part of the extension"
    assert "Deepana-Pachana" in notice, "a phase that added days must appear in the notice"


# ── The declared second Karma is deferred, not dropped ───────────────────────

def _deferral(plan):
    return (plan.get("clinical_decisions") or {}).get("secondary_karma_deferred")


def test_the_declared_secondary_karma_reaches_the_plan():
    """The classical mapping authors a second Karma per Vikriti — for Pitta,
    Raktamokshana, with a stated reason and a Charaka reference. The engine computed
    it into `pradhana_karma_selected["secondary"]` and then nothing read it, so a
    cited clinical claim vanished between the KB and the patient.

    It still is not scheduled — that needs a Vaidya — but it is now stated.
    """
    plan = generate_panchakarma_plan(_profile(vikriti_dominant="pitta"), _prefs())
    karma = (plan["clinical_decisions"]["pradhana_karma_selected"] or {}).get("secondary")
    if not karma:
        pytest.skip("no secondary declared for this Vikriti/route")
    d = _deferral(plan)
    assert d is not None, "a declared secondary Karma must not disappear silently"
    assert d["karma"] == karma
    assert d["reviewed"] is False


def test_the_deferral_never_claims_to_schedule_anything():
    """The whole point is that it is NOT performed. If this ever reports
    `scheduled: True`, the plan is telling a patient to undergo a second Pradhana
    Karma — bloodletting, for Pitta — that nothing sequenced, prepared or gated."""
    for dosha in ("vata", "pitta", "kapha"):
        plan = generate_panchakarma_plan(_profile(vikriti_dominant=dosha), _prefs())
        d = _deferral(plan)
        if d:
            assert d["scheduled"] is False
            assert d["karma"] != plan["clinical_decisions"]["pradhana_karma_selected"]["primary"]


def test_no_deferral_is_announced_for_a_karma_already_being_performed():
    """A seasonal override or a safety substitution can collapse the secondary onto
    the primary. Announcing a "deferred" Karma the plan already performs would be
    noise that reads as a second treatment."""
    from services.panchakarma_engine import _secondary_karma_deferral

    assert _secondary_karma_deferral({"primary": "vamana", "secondary": "vamana"}) is None
    assert _secondary_karma_deferral({"primary": "basti_matra", "secondary": "basti"}) is None
    assert _secondary_karma_deferral({"primary": "virechana", "secondary": None}) is None
    assert _secondary_karma_deferral(
        {"primary": "virechana", "secondary": "raktamokshana"})["karma"] == "raktamokshana"


def test_a_shamana_plan_defers_nothing():
    """No Pradhana Karma means no secondary either. A patient told they are not
    eligible for purification must not also be handed a second one to ask about."""
    plan = generate_panchakarma_plan(
        _profile(age=82, ama_indicator="severe", ojas_level="low",
                 medical_history=["heart_disease"]), _prefs())
    if plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana":
        assert _deferral(plan) is None
