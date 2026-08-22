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
INELIGIBLE = [
    pytest.param(_profile(age=78), id="elderly"),
    pytest.param(_profile(age=5), id="very_young"),
    pytest.param(_profile(ama_indicator="high"), id="high_ama"),
    pytest.param(_profile(ama_indicator="severe"), id="severe_ama"),
    pytest.param(_profile(pregnancy_or_nursing=True), id="pregnancy"),
    pytest.param(_profile(bmi=15.2), id="atidurbala"),
    pytest.param(_profile(medical_history=["anemia"]), id="anemia"),
    pytest.param(_profile(medical_history=["active_fever"]), id="active_fever"),
    pytest.param(_profile(medical_history=["cancer"]), id="severe_unmapped"),
]


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
