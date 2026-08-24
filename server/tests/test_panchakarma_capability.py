"""What the patient said they can do, applied to the cleanse and not only the extras.

`panchakarma_therapies.json` states, per row, what the patient has to supply:
`diet_strictness` and `herb_requirement`. `filter_and_score_therapies` reads both —
and is only ever called with `"purvakarma"` and `"paschat"`, so all nine `pradhana`
rows sat outside the only gate that read their fields.

The result was a plan that honoured the preference on the periphery and ignored it
at the centre. A patient who answered "lifestyle changes only" had the Kitchari
mono-diet withheld from their rotating therapies and was then handed a seven-stage
Samsarjana Krama opening on Peya — rice boiled at 1:14 and strained — and nothing in
the plan acknowledged the answer. A patient who answered that they cannot obtain
Ayurvedic formulations was prescribed Madanaphala Phanta.
"""
import json

import pytest

from services.panchakarma_engine import (
    THERAPIES_PATH,
    _KARMA_ROWS,
    generate_panchakarma_plan,
    pk_therapies,
)


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
        setting="home", available_time_days=14, detox_experience="experienced",
        access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
        self_care_time_per_day="1 hour", panchakarma_goal="detox",
    )
    base.update(over)
    return base


# ── The mapping must not drift from the KB ────────────────────────────────────

def test_every_pradhana_row_belongs_to_exactly_one_karma():
    """A row nothing maps is a row the gate silently exempts.

    This is the same failure that left 19 of 32 Aushadha entries unreachable: the
    data and the code that reads it drift apart, and nothing fails.
    """
    kb_pradhana = {t["id"] for t in pk_therapies if t["phase"] == "pradhana"}
    mapped = [r for rows in _KARMA_ROWS.values() for r in rows]

    assert set(mapped) <= {t["id"] for t in pk_therapies}, "mapped a row the KB does not have"
    assert kb_pradhana <= set(mapped), f"unmapped Pradhana rows: {kb_pradhana - set(mapped)}"


def test_the_gate_can_never_strand_a_patient_with_no_route():
    """Some Karma must survive the most restrictive answers, in every setting.

    Pratimarsha Nasya is the one that does — `nasya_home` asks for no therapeutic
    diet and no specific formulation. If the KB ever changes so that nothing
    survives, the engine falls back to Shamana rather than picking a route the
    patient has said they cannot follow; this test is what says that fallback is a
    backstop and not the normal path.
    """
    for setting in ("home", "clinic", "both"):
        plan = generate_panchakarma_plan(
            _profile(),
            _prefs(setting=setting, diet_adherence_ability="lifestyle_only",
                   access_to_ayurvedic_herbs="no"),
        )
        assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] is not None, \
            f"no Karma survived the most restrictive answers in {setting}"


# ── Diet adherence ────────────────────────────────────────────────────────────

def test_lifestyle_only_withdraws_a_home_karma_that_needs_a_therapeutic_diet():
    """At home nobody but the patient runs the diet, so the answer decides."""
    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting="home", diet_adherence_ability="lifestyle_only"))
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]

    assert pk["capability_substitution"] is True
    assert pk["original_karma"] == "virechana"
    assert "samsarjana" in pk["reason"].lower(), "the reason must name what it is protecting"


def test_partial_adherence_does_not_cost_the_patient_the_karma():
    """`partial` rates difficulty; `lifestyle_only` states refusal.

    The therapy pool excludes `strict` rows from a `partial` answer, and it can
    afford to — dropping a supporting therapy costs the patient a massage. Applying
    the same rule to the Karma would cost them the treatment, and `partial` is the
    schema default, so it would cost the median user the treatment.
    """
    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting="home", diet_adherence_ability="partial"))
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]

    assert pk["primary"] == "virechana"
    assert not pk.get("capability_substitution")


def test_a_preference_substitution_stays_inside_the_patients_setting():
    """The fallback table names the classical route, not the setting's form of it.

    Answering the withdrawal of a home patient's Virechana with clinical Niruha
    Basti — which has no home row at all — would be a preference substitution that
    quietly promotes them to a procedure requiring a Vaidya.
    """
    plan = generate_panchakarma_plan(
        _profile(dominant_dosha="vata", vikriti_dominant="vata"),
        _prefs(setting="home", diet_adherence_ability="lifestyle_only"))
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] in ("nasya", "basti_matra")


def test_a_clinic_administered_karma_is_exempt_but_the_plan_says_so():
    """The clinic serves the diet, so the answer describes nothing the patient does.

    That makes it exempt, not unmentionable: a plan that neither honours an answer
    nor refers to it reads as though the question was never asked.
    """
    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting="clinic", diet_adherence_ability="lifestyle_only"))

    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] == "virechana"
    assert plan["samsarjana_krama"], "the ladder is part of the treatment"

    notice = plan["samsarjana_notice"]
    assert notice and "lifestyle only" in notice
    assert "clinic" in notice.lower(), "the notice must say who prepares the meals"


def test_a_patient_who_can_follow_the_diet_gets_no_notice():
    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting="clinic", diet_adherence_ability="strict"))
    assert plan["samsarjana_notice"] is None


# ── Herb access ───────────────────────────────────────────────────────────────

def test_no_herb_access_never_costs_the_patient_the_cleanse():
    """Every home Karma row is `readily_available`; only the compendium is not.

    So this answer is a procurement problem, not an eligibility one, and treating it
    as an eligibility one would withhold a cleanse the KB says needs Triphala.
    """
    kb = json.loads(THERAPIES_PATH.read_text(encoding="utf-8"))
    home_rows = [t for t in kb if t["phase"] == "pradhana" and "home" in t["setting_required"]]
    assert home_rows
    assert all(t["herb_requirement"] == "readily_available" for t in home_rows)

    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting="home", access_to_ayurvedic_herbs="no"))
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] is not None


@pytest.mark.parametrize("setting", ["home", "clinic"])
def test_formulations_are_named_to_someone_who_said_they_cannot_get_them(setting):
    """Named, not withheld — but never silently.

    Substituting on availability would change the medicine for a reason that is not
    clinical; the compendium picks for Vikriti, Koshtha and Bala.
    """
    plan = generate_panchakarma_plan(
        _profile(), _prefs(setting=setting, access_to_ayurvedic_herbs="no"))

    notice = plan["procurement_notice"]
    assert notice, "the plan must acknowledge the answer it did not act on"

    named = {v["name"] for v in plan["aushadha"].values()
             if isinstance(v, dict) and v.get("name")}
    assert named
    assert all(n in notice for n in named), "every formulation must appear in the notice"


def test_a_patient_who_can_obtain_herbs_gets_no_notice():
    plan = generate_panchakarma_plan(_profile(), _prefs(access_to_ayurvedic_herbs="yes"))
    assert plan["procurement_notice"] is None


def _eligibility(plan: dict) -> dict:
    return plan["clinical_decisions"]["shodhana_or_shamana"]


def test_a_shamana_verdict_says_which_kind_of_withholding_it_is():
    """`clinically_ineligible` was written five times and read nowhere — not by the
    engine, not by the client. So a patient who could qualify by changing one answer
    read the same wall as a patient a Vaidya has to clear, and a patient whose
    diagnosis simply could not be assessed read that they were unfit.

    The view now branches on it, which means it has to keep being correct: a
    clinical bar sets it True, and the two non-clinical routes to Shamana set it
    False and say why.
    """
    clinical = generate_panchakarma_plan(
        _profile(age=78, medical_history=["cancer"], ojas_level="low"),
        _prefs(setting="clinic"))
    elig = _eligibility(clinical)
    assert elig["type"] == "shamana"
    assert elig["clinically_ineligible"] is True

    by_preference = generate_panchakarma_plan(
        _profile(), _prefs(setting="home", diet_adherence_ability="lifestyle_only",
                           access_to_ayurvedic_herbs="no"))
    pref_elig = _eligibility(by_preference)
    if pref_elig["type"] == "shamana":
        assert pref_elig["clinically_ineligible"] is False, \
            "a preference-driven Shamana must not be reported as a clinical bar"
        assert not pref_elig.get("unassessed_condition")
