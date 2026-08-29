"""
Regression tests for the home-remedies engine.

Locks in two demo-hardening fixes:
  - filter_remedies has a bundled-JSON fallback, so it works even when the
    Mongo kb_ayurvedic_remedies collection is unseeded.
  - every symptom the onboarding picker can emit resolves to a remedy (the
    onboarding labels didn't match the KB's clinical symptom_ids, so ~half
    silently returned nothing until the alias map was added).
"""
import pytest

from services.remedy_engine import filter_remedies, _REMEDIES_FALLBACK

# Mirror of client/src/pages/Onboarding.jsx `SYMPTOMS`. Keep in sync — this test
# fails loudly if a new onboarding symptom has no remedy mapping.
ONBOARDING_SYMPTOMS = [
    "acidity", "bloating", "constipation", "insomnia", "joint_pain", "fatigue",
    "anxiety", "dry_skin", "skin_rash", "weight_gain", "hair_loss",
    "irregular_periods", "headache", "cough", "cold",
]

_PROFILE = {
    "dominant_dosha": "vata", "secondary_dosha": "pitta",
    "medical_history": [], "allergies": [], "current_medications": [],
}


def test_remedies_fallback_is_loaded():
    """The offline fallback KB must be present (so remedies never silently empty
    when Mongo is unseeded)."""
    assert len(_REMEDIES_FALLBACK) >= 50
    assert all(r.get("symptom_id") for r in _REMEDIES_FALLBACK)


@pytest.mark.parametrize("symptom", ONBOARDING_SYMPTOMS)
def test_every_onboarding_symptom_yields_a_remedy(symptom):
    results = filter_remedies(_PROFILE, {"symptoms": [symptom]})
    actionable = [r for r in results if r.get("action") != "see_doctor"]
    assert actionable, f"onboarding symptom '{symptom}' resolved to no remedy"


def test_unknown_symptom_degrades_safely():
    """An unmapped symptom must not crash — it just yields nothing."""
    assert filter_remedies(_PROFILE, {"symptoms": ["totally_unknown_xyz"]}) == []


# ── General guidelines: prose that used to pass no gate ──────────────────────

def test_dietary_guidance_is_gated_by_the_conditions_the_user_declared():
    """`build_remedy_plan` was handed the whole user profile and read only
    `dominant_dosha` from it, so the general guidelines were static per dosha.

    A diabetic was told to eat "sweet fruits" and someone with chronic kidney
    disease to drink "coconut water" — a potassium load. This engine already
    gates the remedy INGREDIENTS by condition (guggulu and honey withheld from a
    diabetic, salt from a hypertensive); only the prose beside them escaped.
    """
    from services.remedy_engine import build_remedy_plan

    def diet(dosha, history):
        plan = build_remedy_plan(
            [], {"id": "t", "dominant_dosha": dosha, "medical_history": history}, {})
        return plan["general_guidelines"]["diet_during_recovery"].lower()

    assert "sweet fruits" not in diet("pitta", ["type_2_diabetes"])
    assert "coconut water" not in diet("pitta", ["chronic_kidney_disease"])
    assert "spiced foods" not in diet("kapha", ["gerd"])
    assert "oily foods" not in diet("vata", ["gallstones"])

    # and an unaffected practitioner keeps the original guidance
    assert "coconut water" in diet("pitta", [])
    assert "sweet fruits" in diet("pitta", [])


def test_a_substitution_is_never_made_inside_the_avoid_clause():
    """Each guideline is "eat this. Avoid that." A term after "Avoid" is already
    being warned against, and substituting there inverts the advice — the first
    version of this gate produced "Avoid heavy, sweet, moist well-cooked foods
    with only a little ghee" for a Kapha with gallstones, which reads as a
    warning against the safer option."""
    from services.remedy_engine import build_remedy_plan

    plan = build_remedy_plan(
        [], {"id": "t", "dominant_dosha": "kapha",
             "medical_history": ["gallstones"]}, {})
    diet = plan["general_guidelines"]["diet_during_recovery"]
    assert diet == "Light, warm, spiced foods. Avoid heavy, sweet, oily foods."
    assert not plan["guideline_notices"]


def test_a_swapped_guideline_says_that_it_was_swapped():
    """Silently changing clinical guidance is its own problem."""
    from services.remedy_engine import build_remedy_plan

    plan = build_remedy_plan(
        [], {"id": "t", "dominant_dosha": "pitta",
             "medical_history": ["type_2_diabetes"]}, {})
    assert plan["guideline_notices"]
    assert "sweet fruits" in plan["guideline_notices"][0]


# ── Paediatric dosing, and the shared-KB mutation it exposed ──────────────────

import threading  # noqa: E402


def _child(**over):
    p = {"id": "c", "age": 11, "gender": "male", "dominant_dosha": "vata",
         "vikriti_dominant": "vata", "medical_history": ["constipation"],
         "agni_type": "sama"}
    p.update(over)
    return p


def test_a_child_is_never_served_an_adult_dose():
    """Onboarding accepts age from 10, so children reach this engine. Every
    formulation authored a `dosage_pediatric` — 95 of 157 — and it was read by the
    vector seeder and by the medicine card, as a footnote UNDER the adult dose. The
    `dosage_schedule`, which is the list a patient actually follows, used the adult
    figure at every age."""
    from services.remedy_engine import generate_medicines_plan
    import itertools
    for cond, dosha, age in itertools.product(
            ["constipation", "acidity", "cough", "anxiety", "low_immunity", "asthma"],
            ["vata", "pitta", "kapha"], [10, 11]):
        plan = generate_medicines_plan(
            _child(age=age, dominant_dosha=dosha, vikriti_dominant=dosha,
                   medical_history=[cond]), {}, [])
        meds = (plan.get("primary_formulations") or []) + (plan.get("supporting_formulations") or [])
        assert meds, f"child plan empty for {cond}/{dosha}/{age}"
        for m in meds:
            paed = (m.get("dosage_pediatric") or "").strip()
            assert paed, f"{m['id']} served to a child with no paediatric dose"
            assert m["dosage"] == paed, f"{m['id']} served the adult dose to a child"
            assert m.get("dosage_basis") == "paediatric"


def test_the_schedule_a_child_follows_carries_the_paediatric_dose():
    """The card and the schedule disagreeing is the actual harm: an 11-year-old read
    one figure on the card, another in the schedule, and a third in a note."""
    from services.remedy_engine import generate_medicines_plan
    plan = generate_medicines_plan(_child(), {}, [])
    served = {m["name"]: m for m in (plan.get("primary_formulations") or [])
              + (plan.get("supporting_formulations") or [])}
    printed = [line for slot in (plan.get("dosage_schedule") or []) for line in slot["medicines"]]
    assert printed
    for line in printed:
        name = line.split(" — ")[0]
        if name in served:
            assert served[name]["dosage_pediatric"] in line, \
                f"schedule line used a non-paediatric dose: {line}"


def test_a_formulation_with_no_paediatric_dose_is_withheld_and_said():
    """62 of 157 have no paediatric dose, and they were 29% of the medicine slots a
    child was served. Printing the adult figure is the one option that is definitely
    wrong; printing none asks a parent to guess. It is withheld into
    `blocked_medicines`, which the view already renders."""
    from services.remedy_engine import generate_medicines_plan
    plan = generate_medicines_plan(_child(), {}, [])
    reasons = [b["reason"] for b in (plan.get("blocked_medicines") or [])]
    assert any("No paediatric dose is established" in r for r in reasons), \
        "nothing was withheld for want of a paediatric dose"


def test_an_adult_plan_is_unchanged_by_the_paediatric_path():
    from services.remedy_engine import generate_medicines_plan
    adult = _child(age=40)
    plan = generate_medicines_plan(adult, {}, [])
    for m in (plan.get("primary_formulations") or []):
        assert m.get("dosage_basis") != "paediatric"
        assert "dosage_adult" not in m


def test_a_plan_build_does_not_write_to_the_shared_medicine_kb():
    """`_MEDICINES_KB` is a module-level singleton and the annotations are
    per-patient. Writing them onto the KB entry publishes one patient's data to
    every other request in the process."""
    from services.remedy_engine import generate_medicines_plan, _MEDICINES_KB
    before = {m["id"]: dict(m) for m in _MEDICINES_KB}
    generate_medicines_plan(_child(age=40), {"previous_ayurvedic_medicines": ["Triphala Churna"]}, [])
    changed = [i for i, m in ((m["id"], m) for m in _MEDICINES_KB) if before[i] != m]
    assert not changed, f"a plan build mutated shared KB entries: {changed[:5]}"


def test_two_concurrent_users_do_not_see_each_others_answers():
    """`generate_medicines_plan` is synchronous and FastAPI runs sync endpoints in a
    threadpool, so builds genuinely interleave. Before the copy, a user who declared
    nothing was shown a medicine badged "Tried before" from the other user's answers
    — about once in eighty builds, which is rare enough that no single-plan test
    catches it and no bug report reproduces it."""
    from services.remedy_engine import generate_medicines_plan
    base = {"age": 40, "gender": "female", "dominant_dosha": "vata",
            "vikriti_dominant": "vata", "medical_history": ["constipation"],
            "agni_type": "sama"}
    wrong = []

    def run(uid, tried, n):
        for _ in range(n):
            plan = generate_medicines_plan(
                {**base, "id": uid}, {"previous_ayurvedic_medicines": tried}, [])
            for m in (plan.get("primary_formulations") or []):
                expected = m["name"].lower() in [t.lower() for t in tried]
                if m.get("previously_tried") != expected:
                    wrong.append((uid, m["name"], m.get("previously_tried"), expected))

    threads = [threading.Thread(target=run, args=("A", ["Triphala Churna"], 40)),
               threading.Thread(target=run, args=("B", [], 40))]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert not wrong, f"one user's answers appeared in another's plan: {wrong[:3]}"
