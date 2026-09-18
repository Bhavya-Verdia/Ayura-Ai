"""
The diet feature's nutrition arithmetic.

Before this, `target_calories` was `1800 if female else 2000` nudged by BMI category
and goal — it read neither height, weight nor activity level — and nothing anywhere
compared the stated target with what the plan delivered. Two live generations came
back at 585-720 kcal against a stated 1200, and 1240-1410 against a stated 2400 for an
*underweight* patient. `engine/calorie_calculator.py`, documented in CLAUDE.md as a
Tier-1 core engine, was called by nothing but its own unit test.

Each test here was checked by breaking the thing it guards: reverting the floor, the
surplus cap, the fasting exemption and the portion-text scaling each turned the
corresponding test red.
"""
import copy

import pytest

from engine.calorie_calculator import CalorieCalculator
from services.diet_energy import energy_target, _protein_basis_weight

ACTIVITY_MULTIPLIERS = CalorieCalculator.ACTIVITY_MULTIPLIERS
from services.diet_portion_reconciler import (
    MAX_FACTOR, reconcile_plan_energy, scale_portion_text,
)


def _profile(**over):
    base = dict(
        age=40, gender="female", height_cm=160, weight_kg=60,
        activity_level="moderate", bmi_category="normal",
    )
    base.update(over)
    return base


def _prefs(**over):
    base = dict(diet_goal="general_wellness", dietary_type="vegetarian")
    base.update(over)
    return base


# --------------------------------------------------------------------------
# The target reads the patient's body
# --------------------------------------------------------------------------

def test_activity_level_changes_the_target():
    """Two women of the same weight and BMI category, one sedentary and one very
    active, were both told 1200 kcal. Activity level was collected and read by
    nothing on the diet path."""
    sedentary = energy_target(
        _profile(weight_kg=82, height_cm=178, bmi_category="overweight",
                 activity_level="sedentary"), _prefs(diet_goal="weight_loss"))
    very_active = energy_target(
        _profile(weight_kg=82, height_cm=178, bmi_category="overweight",
                 activity_level="very_active"), _prefs(diet_goal="weight_loss"))
    assert very_active["target_calories"] > sedentary["target_calories"] + 800


def test_weight_and_height_change_the_target():
    small = energy_target(_profile(height_cm=150, weight_kg=45), _prefs())
    large = energy_target(_profile(height_cm=190, weight_kg=90), _prefs())
    assert large["target_calories"] > small["target_calories"] + 500


def test_a_profile_without_measurements_is_estimated_and_says_so():
    """A profile that skipped the body-measurement step still needs a number, but the
    plan must not present an estimate as a measurement."""
    result = energy_target(_profile(height_cm=None, weight_kg=None), _prefs())
    assert result["basis"] == "estimated"
    assert result["target_calories"] > 0
    assert any("estimated" in note for note in result["notes"])


# --------------------------------------------------------------------------
# Floors, surpluses and the states that override the stated goal
# --------------------------------------------------------------------------

def test_a_deficit_never_lands_below_resting_requirement():
    """`max(1200, ...)` is gender-blind and sits under most adults' BMR. A weight-loss
    goal on an obese patient produced 1200 kcal against a BMR of 1486."""
    result = energy_target(
        _profile(age=52, gender="female", height_cm=157, weight_kg=84,
                 activity_level="sedentary", bmi_category="obese"),
        _prefs(diet_goal="weight_loss"))
    assert result["target_calories"] >= result["bmr"]
    assert result["target_calories"] >= result["floor_calories"]
    assert any("resting requirement" in note for note in result["notes"])


def test_weight_loss_still_produces_a_deficit_when_there_is_room_for_one():
    """The floor must not swallow the goal: an overweight patient with headroom
    should still be given a deficit against maintenance."""
    result = energy_target(
        _profile(age=35, gender="male", height_cm=175, weight_kg=95,
                 activity_level="moderate", bmi_category="obese"),
        _prefs(diet_goal="weight_loss"))
    assert result["target_calories"] < result["tdee"]


def test_underweight_is_read_from_bmi_not_from_the_goal():
    """`diet_goal` has no weight-gain value, so an underweight patient cannot state
    the surplus they need; a weight-loss goal entered by one must not be honoured."""
    result = energy_target(
        _profile(age=26, gender="male", height_cm=178, weight_kg=52,
                 activity_level="active", bmi_category="underweight"),
        _prefs(diet_goal="weight_loss"))
    assert result["target_calories"] > result["tdee"]
    assert any("weight-loss deficit was not applied" in n for n in result["notes"])


def test_the_combined_surplus_is_bounded():
    """`muscle_support` and underweight are the same physiological ask. Stacked, they
    put a 52 kg man at 3170 kcal — a number nobody eats."""
    result = energy_target(
        _profile(age=26, gender="male", height_cm=178, weight_kg=52,
                 activity_level="active", bmi_category="underweight"),
        _prefs(diet_goal="muscle_support"))
    assert result["target_calories"] - result["tdee"] <= 500


def test_pregnancy_adds_energy_and_refuses_a_deficit():
    result = energy_target(
        _profile(age=30, weight_kg=60, height_cm=162, pregnancy_or_nursing=True),
        _prefs(diet_goal="weight_loss"))
    assert result["target_calories"] > result["tdee"]
    assert any("no energy deficit" in note for note in result["notes"])


def test_protein_floor_uses_adjusted_weight_for_an_obese_patient():
    """Lean mass does not scale with fat mass: actual scale weight put an 84 kg woman
    at an 84 g/day floor where adjusted body weight gives 66 g."""
    assert _protein_basis_weight(84, 157, "obese") == pytest.approx(66.1, abs=1.0)
    # An underweight patient's requirement is never scaled down toward their deficit.
    assert _protein_basis_weight(52, 178, "underweight") == 52


# --------------------------------------------------------------------------
# Portion scaling
# --------------------------------------------------------------------------

@pytest.mark.parametrize("text,factor,expected", [
    ("1.5 katori (250 ml) with 1 tsp ghee", 1.6, "2.5 katori (400 ml) with 1.5 tsp ghee"),
    ("3 medium idlis with 2 tbsp chutney", 1.6, "5 medium idlis with 3 tbsp chutney"),
    ("150g cooked (1 katori)", 2.0, "300 g cooked (2 katori)"),
])
def test_portion_text_scales_every_quantity(text, factor, expected):
    assert scale_portion_text(text, factor) == expected


def test_portion_text_leaves_non_quantities_alone():
    """Only a number followed by a known unit is a quantity. A cooking time is not."""
    out = scale_portion_text("1 glass (200 ml) milk, simmer for 10 minutes", 1.5)
    assert "10 minutes" in out
    assert "300 ml" in out


def test_an_unparseable_portion_comes_back_unchanged():
    assert scale_portion_text("a handful", 1.8) == "a handful"
    assert scale_portion_text("", 1.8) == ""
    assert scale_portion_text(None, 1.8) is None


# --------------------------------------------------------------------------
# Reconciliation
# --------------------------------------------------------------------------

def _llm_plan(kcal_per_meal, fasting=False):
    def meal(name, kcal):
        return {
            "meal_name": name, "portion": "1 katori (200 ml)",
            "macros_approx": {"calories": kcal, "protein_g": kcal // 20,
                              "carbs_g": kcal // 5, "fat_g": kcal // 40},
        }
    return {
        "diet_weeks": [{
            "week_number": 1,
            "daily_plan": {"Monday": {
                "breakfast": meal("Upma", kcal_per_meal),
                "lunch": meal("Khichdi", kcal_per_meal),
                "snack": meal("Makhana", kcal_per_meal),
                "dinner": meal("Soup", kcal_per_meal),
                "is_fasting": fasting,
            }},
        }],
    }


def _energy(target=2000, protein_floor=60):
    return {
        "target_calories": target, "band": (int(target * 0.88), int(target * 1.12)),
        "meal_budget": {"breakfast": int(target * 0.25), "lunch": int(target * 0.35),
                        "snack": int(target * 0.10), "dinner": int(target * 0.30)},
        "protein_floor_g": protein_floor,
    }


def test_a_short_day_is_raised_toward_target():
    plan = reconcile_plan_energy(_llm_plan(150), _energy(2000))
    report = plan["energy_reconciliation"]
    assert report["days_adjusted"] == 1
    day = report["days"][0]
    assert day["before_kcal"] == 600
    assert day["after_kcal"] > day["before_kcal"]


def test_the_portion_text_is_raised_with_the_macros():
    """Raising `macros_approx` alone produces a plan that lies to the person cooking
    it — the macro bar would read 2000 kcal over a portion that delivers 600."""
    plan = reconcile_plan_energy(_llm_plan(150), _energy(2000))
    lunch = plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]
    assert lunch["portion"] != "1 katori (200 ml)"
    assert lunch["macros_approx"]["calories"] > 150
    assert lunch["portion_adjusted"] > 1


def test_a_day_already_in_band_is_left_alone():
    plan = reconcile_plan_energy(_llm_plan(500), _energy(2000))
    assert plan["energy_reconciliation"]["days_adjusted"] == 0
    assert plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["portion"] == "1 katori (200 ml)"


def test_a_fasting_day_is_never_scaled_up():
    """Upavasa and Phalahar are the therapy. Raising a fasting day to a full day's
    energy would undo the thing the day is for."""
    plan = reconcile_plan_energy(_llm_plan(100, fasting=True), _energy(2000))
    report = plan["energy_reconciliation"]
    assert report["fasting_days_exempt"] == 1
    assert report["days_adjusted"] == 0
    assert plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["macros_approx"]["calories"] == 100


def test_an_unreachable_target_reports_a_residual_instead_of_pretending():
    """Past roughly double, portions stop being plausible meals. What the cap cannot
    reach has to be said, not rounded away."""
    plan = reconcile_plan_energy(_llm_plan(100), _energy(3000))
    report = plan["energy_reconciliation"]
    day = report["days"][0]
    assert day["after_kcal"] <= 400 * MAX_FACTOR
    assert day["residual_shortfall_kcal"] > 0
    assert report["residual_notes"]


def test_protein_is_checked_even_when_the_calories_are_fine():
    """Scaling toward a kcal budget cannot fix composition — a day can hit its
    calories on rice alone."""
    plan = _llm_plan(500)
    for slot in ("breakfast", "lunch", "snack", "dinner"):
        plan["diet_weeks"][0]["daily_plan"]["Monday"][slot]["macros_approx"]["protein_g"] = 4
    plan = reconcile_plan_energy(plan, _energy(2000, protein_floor=80))
    report = plan["energy_reconciliation"]
    assert report["days_adjusted"] == 0          # energy was already in band
    assert report["days_below_protein_floor"]    # and the shortfall was still caught


def test_the_rule_engine_shape_is_reconciled_too():
    """The engine fills category quotas with no target at all — measured at 580-1031
    kcal against a 1490 target. Which path ran must not change what the patient is
    told to eat."""
    plan = {"four_week_plan": [{
        "week": 1,
        "days": [{
            "day_name": "Monday",
            "meals": {slot: [{
                "id": "rice", "portion": "150g cooked (1 katori)",
                "macros": {"calories": 150.0, "protein_g": 3.0, "carbs_g": 30.0},
            }] for slot in ("breakfast", "lunch", "snack", "dinner")},
            "daily_macros": {"calories": 600.0, "protein_g": 12.0},
        }],
    }]}
    before = copy.deepcopy(plan)
    plan = reconcile_plan_energy(plan, _energy(2000))
    assert plan["energy_reconciliation"]["days_adjusted"] == 1
    item = plan["four_week_plan"][0]["days"][0]["meals"]["lunch"][0]
    before_item = before["four_week_plan"][0]["days"][0]["meals"]["lunch"][0]
    assert item["macros"]["calories"] > before_item["macros"]["calories"]
    assert item["portion"] != before_item["portion"]
    # The day-level totals the engine shape carries are recomputed, not left stale.
    assert plan["four_week_plan"][0]["days"][0]["daily_macros"]["calories"] > 600


def test_weeks_without_macros_are_reported_as_unmeasured_not_as_passing():
    """Weeks 2-4 of an LLM plan are meal names. Counting them as checked would claim
    a verification that never happened."""
    plan = _llm_plan(500)
    plan["diet_weeks"].append({
        "week_number": 2,
        "daily_plan": {"Monday": {"breakfast": "Poha", "lunch": "Dal chawal"}},
    })
    plan = reconcile_plan_energy(plan, _energy(2000))
    assert plan["energy_reconciliation"]["days_quantified"] == 1


@pytest.mark.parametrize("plan", [
    {"diet_weeks": "not a list"},
    {"diet_weeks": [{"week_number": 1, "daily_plan": "nope"}]},
    {"four_week_plan": [{"week": 1, "days": [None]}]},
    {},
])
def test_a_malformed_plan_shape_is_skipped_not_raised(plan):
    """The shapes drift — `weekly_plan`, `diet_weeks`, `four_week_plan` have all been
    the live one. A correction layer must survive meeting a shape it cannot read."""
    out = reconcile_plan_energy(plan, _energy(2000))
    assert out["energy_reconciliation"]["days_adjusted"] == 0


def test_reconciliation_reports_failure_rather_than_losing_the_plan():
    """If the correction itself breaks, the plan still ships and says it was not
    checked — an energy pass must never be able to destroy a generated plan."""
    plan = reconcile_plan_energy(_llm_plan(150), {"target_calories": 2000})  # no band
    assert plan["energy_reconciliation"] == {"checked": False}
    assert plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["meal_name"] == "Khichdi"


def test_the_brief_states_the_per_meal_budget():
    """The brief used to end on a daily number with no per-meal anchor, and the model
    divided it by eye."""
    from services.diet_brief_builder import build_brief
    brief = build_brief(
        _profile(age=52, gender="female", height_cm=157, weight_kg=84,
                 activity_level="sedentary", bmi_category="obese"),
        _prefs(diet_goal="weight_loss"))
    assert "ENERGY PRESCRIPTION" in brief
    assert "Per-meal budget" in brief
    assert "Minimum protein" in brief


# --------------------------------------------------------------------------
# Duplicated tables are how this feature's safety layers drift apart
# --------------------------------------------------------------------------

def test_there_is_one_allergen_term_table():
    """`diet_brief_builder` held its own copy of `ALLERGEN_TERMS`, and the copies had
    drifted: the copy there was missing all four `food_intolerances` values, so
    `flag_allergens` resolved `lactose` through `.get(key, [key])` and scanned meal
    text for the literal word "lactose" — the failure PR #61 fixed in
    `apply_ahara_safety` and only there. It also disagreed on 8 of its 10 keys."""
    from services import ahara_safety, diet_brief_builder
    assert diet_brief_builder.ALLERGEN_TERMS is ahara_safety.ALLERGEN_TERMS


def test_both_diet_entry_points_run_the_same_pipeline():
    """The per-feature route and the holistic worker each held a copy of the
    generate-then-check sequence, and the holistic fallback ran only
    `apply_ahara_safety` — so which endpoint a user came through decided how much of
    the safety model applied to their plan."""
    from pathlib import Path
    routes = Path(__file__).resolve().parent.parent / "routes"
    for name in ("plans.py", "plan_runner.py"):
        source = (routes / name).read_text(encoding="utf-8")
        assert "build_diet_plan" in source, f"{name} must use the shared diet builder"
        assert "generate_diet_plan_llm" not in source, (
            f"{name} calls the LLM generator directly — it would skip the fallback's "
            "safety and energy layers")


# ── The activity level the app actually collects ──────────────────────────────

def test_activity_level_is_the_largest_single_lever_in_the_plan():
    """Onboarding sent `activity_level: 'moderate'` as a literal for every user it
    ever created, and nine of the twelve in production had no value at all. The
    energy prescription calls itself "a clinical target, not a suggestion" and reads
    this field as the basis of it — so a desk-bound patient was prescribed the
    maintenance intake of someone training five days a week."""
    base = dict(dominant_dosha="vata", age=30, gender="male", height_cm=175,
                weight_kg=70, bmi_category="normal", medical_history=[])
    prefs = {"diet_goal": "general_wellness", "dietary_type": "vegetarian",
             "food_allergies": [], "food_intolerances": [],
             "gut_health_issue": "healthy", "intermittent_fasting": "no",
             "water_intake": "2-3L", "fasting_days": []}

    targets = {a: energy_target({**base, "activity_level": a}, prefs)["target_calories"]
               for a in ("sedentary", "light", "moderate", "active", "very_active")}

    assert sorted(targets.values()) == list(targets.values()), targets
    assert targets["very_active"] - targets["sedentary"] > 1000, targets
    # The hardcoded value was the middle one, so the error was silent in both
    # directions rather than obviously wrong in one.
    assert energy_target(base, prefs)["target_calories"] == targets["moderate"]


def test_onboarding_collects_every_activity_level_the_engine_scores():
    """The question and the multipliers live on opposite sides of the front/back
    boundary with no shared schema — the same gap `test_dosha_instrument` exists to
    close. A level the form stops offering silently becomes unreachable; one it
    offers that the engine does not know falls back to a default."""
    import re
    from pathlib import Path

    jsx = (Path(__file__).resolve().parents[2] / "client" / "src" / "pages"
           / "Onboarding.jsx").read_text(encoding="utf-8")
    block = re.search(r"How active is your usual week\?(.*?)</div>\s*</div>", jsx, re.S)
    assert block, "Onboarding.jsx no longer asks for an activity level"
    offered = set(re.findall(r"id:\s*'([a-z_]+)'", block.group(1)))
    assert offered == set(ACTIVITY_MULTIPLIERS), (
        f"onboarding offers {sorted(offered)}; the engine scores "
        f"{sorted(ACTIVITY_MULTIPLIERS)}"
    )
