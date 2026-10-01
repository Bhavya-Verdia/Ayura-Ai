"""Two coverage gaps: who the plan is for, and what they called their disease.

**Age.** The profile accepts 10-120 and the energy model treated all of it as one
adult. Mifflin-St Jeor and Harris-Benedict are derived from and validated on adults; a
10-year-old at 150 cm / 45 kg was handed 1990 kcal from the adult formula with nothing
in the brief to say a child was being fed, a weight-loss goal was honoured for a
twelve-year-old, and the protein floor was the table's lowest (0.8 g/kg) for the two
groups that can least afford it — the growing and the old.

**Aliases.** `_COND_CANON` was an exact-match table, so `crohns` resolved to IBS and
`crohns disease` resolved to nothing. Onboarding has a free-text "Not listed? Add
here" field, so the curated floor a user got was decided by how they phrased it.
"""

import pytest

from services.ahara_safety import _canon_condition
from services.diet_brief_builder import (
    PATHYA_APATHYA_HINTS,
    build_brief,
    fasting_days_for,
)
from services.diet_energy import energy_target


def _profile(age, **over):
    p = {"dominant_dosha": "vata", "agni_type": "sama", "gender": "female", "age": age,
         "height_cm": 150, "weight_kg": 45, "activity_level": "moderate",
         "bmi_category": "normal", "medical_history": [], "current_season": "varsha"}
    p.update(over)
    return p


def _prefs(**over):
    p = {"dietary_type": "vegetarian", "diet_goal": "general_wellness",
         "food_allergies": [], "food_intolerances": [], "gut_health_issue": "healthy",
         "intermittent_fasting": "no", "water_intake": "2-3L", "fasting_days": []}
    p.update(over)
    return p


# ── Age ───────────────────────────────────────────────────────────────────────

@pytest.mark.parametrize("age", [10, 14, 17])
def test_a_child_is_not_put_in_an_energy_deficit(age):
    """Childhood weight management is a supervised clinical decision. The same
    restriction that is merely uncomfortable for an adult costs a 12-year-old
    growth."""
    adult = energy_target(_profile(30, weight_kg=70, height_cm=160),
                          _prefs(diet_goal="weight_loss"))
    child = energy_target(_profile(age, weight_kg=70, height_cm=160),
                          _prefs(diet_goal="weight_loss"))
    assert child["target_calories"] > adult["target_calories"]
    assert any("under 18" in n.lower() for n in child["notes"])


@pytest.mark.parametrize("age", [10, 14, 17])
def test_a_child_uses_the_paediatric_equation(age):
    """Schofield (WHO/FAO) for this band, not the adult Mifflin-St Jeor."""
    e = energy_target(_profile(age), _prefs())
    assert any("schofield" in n.lower() for n in e["notes"])
    assert any("paediatrician" in n.lower() for n in e["notes"])


def test_the_adult_equation_resumes_at_eighteen():
    assert not any("schofield" in n.lower()
                   for n in energy_target(_profile(18), _prefs())["notes"])


@pytest.mark.parametrize("age,floor_per_kg", [(12, 1.0), (35, 0.8), (78, 1.1)])
def test_the_protein_floor_follows_the_age_stage(age, floor_per_kg):
    """Requirement rises at both ends of life — growth at one, sarcopenia at the
    other — and both were on the table's lowest floor."""
    e = energy_target(_profile(age), _prefs())
    assert e["protein_floor_g"] == pytest.approx(45 * floor_per_kg, abs=1)


@pytest.mark.parametrize("age,marker", [(12, "BALYA"), (78, "VRIDDHA")])
def test_the_brief_names_the_age_stage(age, marker):
    """Vayah changes the prescription before any dosha does, and the brief described
    a ten-year-old and a seventy-eight-year-old identically."""
    brief = build_brief(_profile(age), _prefs())
    assert f"VAYAH (AGE STAGE) — {marker}" in brief


def test_an_adult_gets_no_age_block():
    assert "VAYAH" not in build_brief(_profile(35), _prefs())


@pytest.mark.parametrize("age", [10, 17])
def test_fasting_is_withheld_from_a_child_everywhere(age):
    """The brief is a request; the engine is deterministic. `diet_plan_engine` reads
    `fasting_days` itself and builds a Phalahar day, and the LLM path stamps
    `is_fasting` from the same list — so withholding it in the brief alone leaves a
    twelve-year-old a fruit-only Monday in a plan whose brief forbids fasting them."""
    from services.diet_plan_engine import generate_diet_plan

    prefs = _prefs(fasting_days=["Monday"], intermittent_fasting="16:8")
    assert fasting_days_for(_profile(age), prefs) == []

    plan = generate_diet_plan(_profile(age), prefs, None)
    assert not [d for w in plan["four_week_plan"] for d in w["days"]
                if d.get("is_fasting_day")]

    brief = build_brief(_profile(age), prefs)
    assert "NO FASTING" in brief
    assert "16:8 window" not in brief


def test_an_adult_keeps_their_fasting_days():
    from services.diet_plan_engine import generate_diet_plan

    prefs = _prefs(fasting_days=["Monday"])
    assert fasting_days_for(_profile(35), prefs) == ["Monday"]
    plan = generate_diet_plan(_profile(35), prefs, None)
    assert [d for w in plan["four_week_plan"] for d in w["days"] if d.get("is_fasting_day")]


def test_both_generation_paths_withhold_a_childs_fasting_days():
    import inspect
    from services import diet_llm_generator as g

    assert "fasting_days_for" in inspect.getsource(g.generate_diet_plan_llm)
    from services import diet_plan_engine as e
    assert "_fasting_days_for" in inspect.getsource(e.generate_diet_plan)


# ── Condition phrasing ────────────────────────────────────────────────────────

@pytest.mark.parametrize("typed,expected", [
    ("crohns", "ibs"), ("crohns disease", "ibs"), ("crohn's disease", "ibs"),
    ("ulcerative colitis", "ibs"), ("ibd", "ibs"),
    ("piles", "arsha"), ("fissure", "arsha"),
    ("acid reflux", "acidity"), ("gerd", "acidity"), ("gastritis", "acidity"),
    ("sugar", "diabetes"), ("sugar problem", "diabetes"), ("blood sugar", "diabetes"),
    ("thyroid problem", "hypothyroid"), ("hypo thyroid", "hypothyroid"),
    ("PCOD", "pcos"), ("low bp", "low_blood_pressure"), ("bp high", "hypertension"),
    ("kidney stone", "kidney_stones"), ("renal calculi", "kidney_stones"),
    ("gouty arthritis", "gout"), ("uric acid", "gout"),
    ("migraines", "migraine"), ("gall stone", "gallstones"),
    ("cholesterol", "high_cholesterol"), ("slip disc", "sciatica"),
    ("rheumatoid arthritis", "amavata"), ("iron deficiency", "anemia"),
    # Sanskrit, which condition_vocab knew and the diet path could not reach.
    ("apasmara", "epilepsy"), ("ardhavabhedaka", "migraine"), ("bhrama", "vertigo"),
])
def test_a_phrasing_does_not_decide_which_floor_you_get(typed, expected):
    assert _canon_condition(typed) == expected
    assert expected in PATHYA_APATHYA_HINTS


@pytest.mark.parametrize("typed", ["heart disease", "kidney disease", "fatty liver"])
def test_a_real_key_ending_in_a_qualifier_is_not_shortened(typed):
    """Stripping runs only after both exact lookups fail, so `heart_disease` is
    matched whole and never reduced to `heart`."""
    key = _canon_condition(typed)
    assert key in PATHYA_APATHYA_HINTS
    assert key.replace("_", " ").startswith(typed.split()[0])


@pytest.mark.parametrize("junk", ["", "   ", "none", "nothing", "healthy", "test",
                                  "problem", "disease", "issues", "my heart", "stone"])
def test_junk_does_not_resolve_to_a_protocol(junk):
    """A false positive here applies a whole disease's Apathya to someone who does not
    have it — the opposite failure, and the worse one."""
    assert _canon_condition(junk) not in PATHYA_APATHYA_HINTS


def test_the_normalizer_only_ever_adds():
    """Differential guard. The composed lookup must not take a rule away from an
    input that already had one, nor silently reassign it to a different disease."""
    import engine.condition_vocab as cv
    from services import ahara_safety as A

    def old(cond):
        key = str(cond).strip().lower().replace(" ", "_").replace("-", "_")
        return A._COND_CANON.get(key, key)

    inputs = set(A._COND_CANON) | set(A._COND_CANON.values()) | set(PATHYA_APATHYA_HINTS)
    inputs |= set(cv.CONDITION_ALIASES)
    for v in cv.CONDITION_ALIASES.values():
        if isinstance(v, (set, list, tuple)):
            inputs |= set(v)

    for raw in {str(i) for i in inputs if i}:
        before, after = old(raw), _canon_condition(raw)
        if before in PATHYA_APATHYA_HINTS:
            assert after == before, f"{raw!r}: {before} -> {after}"


# ── How deeply a condition was actually screened ──────────────────────────────

def test_a_thin_floor_is_reported_as_a_thin_floor():
    """Twenty-one conditions have been judged against every one of the library's 150
    foods; nineteen have a curated term list and nothing more. Both produced the same
    "every meal checked — none found" badge, so a gout patient (27 terms, no per-food
    claims) read the same reassurance as an acidity patient (101 terms, 95 of them
    authored food by food) while being materially less protected."""
    from services.ahara_safety import apply_condition_food_safety

    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {
        "Mon": {"lunch": {"meal_name": "Khichdi", "key_ingredients": []}}}}]}

    thin = apply_condition_food_safety(dict(plan), ["gout"], {}, False)
    assert thin["conditions_screened_by_terms_only"] == ["gout"]
    assert thin["conditions_without_food_floor"] == []

    deep = apply_condition_food_safety(dict(plan), ["acidity"], {}, False)
    assert deep["conditions_screened_by_terms_only"] == []

    # A condition with no floor at all is still reported separately — "we could not
    # derive a rule" and "we checked, less thoroughly" are different statements.
    none = apply_condition_food_safety(dict(plan), ["lupus"], {}, False)
    assert none["conditions_without_food_floor"] == ["lupus"]
    assert none["conditions_screened_by_terms_only"] == []


def test_the_view_renders_both_kinds_of_partial_check():
    from pathlib import Path

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "components"
           / "planViews" / "DietView.jsx").read_text(encoding="utf-8")
    assert "conditions_screened_by_terms_only" in jsx
    assert "conditions_without_food_floor" in jsx


# ── Sex, for the users who are not one of two ─────────────────────────────────

def test_other_and_unset_take_the_mean_of_the_two_equations():
    """Onboarding offers male / female / other and the schema accepts all three, but
    the BMR was `if female else male` — so `other`, and everyone who answered nothing,
    silently got the male equation (2410 kcal against 2190 on the same body) while
    `_SEX_FLOOR` handed them the *female* floor. Half of one and half of the other,
    chosen by nobody."""
    male = energy_target(_profile(30, gender="male", height_cm=168, weight_kg=62), _prefs())
    female = energy_target(_profile(30, gender="female", height_cm=168, weight_kg=62), _prefs())
    for unknown in ("other", None, ""):
        got = energy_target(
            _profile(30, gender=unknown, height_cm=168, weight_kg=62), _prefs())
        assert female["target_calories"] < got["target_calories"] < male["target_calories"]
        assert female["floor_calories"] < got["floor_calories"] < male["floor_calories"]
        # And it says so, rather than presenting an average as a measurement.
        assert any("average of the two standard equations" in n for n in got["notes"])


def test_a_stated_sex_gets_no_estimate_disclaimer():
    for sex in ("male", "female"):
        e = energy_target(_profile(30, gender=sex), _prefs())
        assert not any("average of the two" in n for n in e["notes"])


def test_the_paediatric_equation_is_sex_neutral_too():
    """Schofield is banded by sex the same way, and had the same `.get(gender, male)`
    fallthrough."""
    male = energy_target(_profile(14, gender="male"), _prefs())["target_calories"]
    female = energy_target(_profile(14, gender="female"), _prefs())["target_calories"]
    other = energy_target(_profile(14, gender="other"), _prefs())["target_calories"]
    assert female < other < male
