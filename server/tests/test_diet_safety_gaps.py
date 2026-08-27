"""Four places the deterministic Ahara safety layer stopped short.

`ahara_safety` exists on one premise, stated in its own docstring: food safety must
never depend on the model self-reporting. It kept that premise for four meal slots
and a curated condition list, and dropped it everywhere else. Each gap below was
found by probing what a declared field actually decides, and each was reachable by
an ordinary user answering the onboarding questions truthfully.

1. The daily drink was in none of the three scans. `SYSTEM_PROMPT` rule 9 makes it
   mandatory, so it is on every day of every plan, and `DietView` renders its name,
   recipe and rationale.
2. All four `food_intolerances` values were inert — no term list, so the scan
   searched meal text for the literal word "lactose".
3. `dietary_type`, annotated CRITICAL in the schema, had no check on the
   LLM-primary path at all.
4. Pregnancy had no floor: `pregnancy_or_nursing` is a profile flag, not a
   `medical_history` entry, so it reached the condition scan by no route.
"""
import pytest

from services.ahara_safety import (
    ALLERGEN_TERMS,
    _CONDITION_APATHYA_TERMS,
    _collect_meal_units,
    apply_ahara_safety,
    apply_condition_food_safety,
    apply_dietary_type_safety,
)

SAFE_MEALS = {
    "breakfast": {"meal_name": "Vegetable Upma", "key_ingredients": ["semolina", "carrot"]},
    "lunch": {"meal_name": "Moong Dal Khichdi with Ghee", "key_ingredients": ["moong dal", "rice", "ghee"]},
    "snack": {"meal_name": "Roasted Makhana", "key_ingredients": ["makhana"]},
    "dinner": {"meal_name": "Lauki Sabzi with Roti", "key_ingredients": ["bottle gourd", "wheat"]},
}
CCF_TEA = {"name": "CCF Tea", "when": "Morning", "rationale": "Deepana",
           "recipe": "Cumin, coriander and fennel seeds steeped in hot water"}


def _plan(meals=None, drink=None, week2=None):
    day = dict(meals if meals is not None else SAFE_MEALS)
    if drink is not None:
        day["special_drink"] = drink
    weeks = [{"week_number": 1, "daily_plan": {"Monday": day}}]
    if week2 is not None:
        weeks.append({"week_number": 2, "daily_plan": {"Monday": week2}})
    return {"diet_weeks": weeks}


# ── 1. The daily drink ────────────────────────────────────────────────────────

BADAM_MILK = {
    "name": "Badam Milk with Saffron", "when": "Bedtime", "rationale": "Ojas-building",
    "recipe": "Warm cow's milk with soaked almonds, cardamom and saffron",
}


def test_the_drink_is_a_collected_slot():
    slots = {slot for _w, _d, slot, _m in _collect_meal_units(_plan(drink=CCF_TEA))}
    assert "special_drink" in slots


def test_the_bedtime_drink_is_allergen_scanned():
    """The reported case: dairy AND tree-nut allergies declared, "Badam Milk —
    warm cow's milk with soaked almonds" prescribed nightly, plan reporting
    allergen_safe: True with zero alerts."""
    out = apply_ahara_safety(_plan(drink=BADAM_MILK), ["dairy", "nuts_tree"], [])
    assert out["allergen_safe"] is False
    assert any(a["meal_slot"] == "special_drink" for a in out["safety_alerts"])


def test_the_compact_week_drink_is_scanned_too():
    """Weeks 2-4 carry the drink as a bare string, not a dict."""
    week2 = {"breakfast": "Poha", "lunch": "Dal Rice", "snack": "Fruit",
             "dinner": "Khichdi", "special_drink": "Haldi Doodh (golden milk) — bedtime"}
    out = apply_ahara_safety(_plan(drink=CCF_TEA, week2=week2), ["dairy"], [])
    assert any(a["week"] == "Week 2" and a["meal_slot"] == "special_drink"
               for a in out["safety_alerts"])


def test_a_drinks_ingredients_live_in_its_recipe():
    """A drink has no `key_ingredients`; `recipe` is the only place its contents
    appear, so `_meal_text` has to read it."""
    hidden = {"name": "Evening Tonic", "when": "6 PM", "rationale": "Nourishing",
              "recipe": "Almond and cashew paste simmered in milk"}
    out = apply_ahara_safety(_plan(drink=hidden), ["nuts_tree"], [])
    assert out["allergen_safe"] is False


def test_a_drinks_rationale_is_not_scanned():
    """`rationale` and `when` are explanatory prose. Scanning them would flag the
    very drink whose note says it avoids the allergen.

    Asserted on the drink slot alone: the default day's Khichdi is cooked in ghee,
    so a plan-level `allergen_safe` would be False for a reason that is not this one.
    """
    plan = _plan(
        meals={"lunch": {"meal_name": "Lauki Sabzi", "key_ingredients": ["bottle gourd"]}},
        drink={"name": "Ginger Tea", "when": "Morning",
               "recipe": "Fresh ginger steeped in water",
               "rationale": "Chosen instead of milk because dairy is avoided here"},
    )
    out = apply_ahara_safety(plan, ["dairy"], [])
    assert not [a for a in out["safety_alerts"] if a["meal_slot"] == "special_drink"]
    assert out["allergen_safe"] is True


def test_the_drink_is_condition_scanned_and_dietary_type_scanned():
    """One collector feeds all three scans, so fixing it fixes all three."""
    sweet_lassi = {"name": "Mango Lassi", "when": "Afternoon", "rationale": "Cooling",
                   "recipe": "Yogurt blended with mango and sugar"}
    out = apply_condition_food_safety(_plan(drink=sweet_lassi), ["type2_diabetes"])
    assert any(a["meal_slot"] == "special_drink" for a in out["condition_safety_alerts"])

    out = apply_dietary_type_safety(_plan(drink=BADAM_MILK), "vegan")
    assert any(a["meal_slot"] == "special_drink" for a in out["dietary_type_alerts"])


# ── 2. Intolerances ───────────────────────────────────────────────────────────

SCHEMA_INTOLERANCES = ("lactose", "fructose", "histamine", "fodmap")


def test_every_schema_intolerance_has_a_term_list():
    """`ALLERGEN_TERMS.get(key, [key])` makes a missing key fail open: the scan
    looks for the word "lactose" in the meal text and finds nothing, forever."""
    missing = [i for i in SCHEMA_INTOLERANCES if i not in ALLERGEN_TERMS]
    assert not missing, f"declared but inert: {missing}"


@pytest.mark.parametrize("intolerance,meal,ingredient", [
    ("lactose", "Paneer Paratha with Curd", "paneer"),
    ("fructose", "Mango Shrikhand with Honey", "honey"),
    ("histamine", "Idli with Coconut Chutney", "idli"),
    ("fodmap", "Rajma Chawal with Onion Salad", "rajma"),
])
def test_a_declared_intolerance_actually_fires(intolerance, meal, ingredient):
    plan = _plan({"lunch": {"meal_name": meal, "key_ingredients": [ingredient]}})
    out = apply_ahara_safety(plan, [], [intolerance])
    assert out["allergen_safe"] is False, f"{intolerance} did not fire on {meal}"


def test_ghee_is_not_flagged_for_lactose():
    """Clarified butter is all but lactose-free and is the dairy Ayurveda
    prescribes most. Flagging it would train the user to ignore the warning."""
    plan = _plan({"lunch": {"meal_name": "Khichdi with Ghee", "key_ingredients": ["ghee", "rice"]}})
    assert apply_ahara_safety(plan, [], ["lactose"])["allergen_safe"] is True


# ── 3. Dietary type ───────────────────────────────────────────────────────────

@pytest.mark.parametrize("dtype,meal,expect_flag", [
    ("vegetarian", "Butter Chicken with Naan", True),
    ("vegetarian", "Paneer Butter Masala", False),
    ("vegan", "Paneer Butter Masala", True),
    ("vegan", "Chana Masala with Rice", False),
    ("eggetarian", "Masala Omelette", False),
    ("eggetarian", "Mutton Rogan Josh", True),
    ("pescatarian", "Fish Curry with Rice", False),
    ("pescatarian", "Chicken Biryani", True),
    ("non_vegetarian", "Chicken Biryani", False),
])
def test_the_declared_dietary_type_is_checked_not_requested(dtype, meal, expect_flag):
    plan = _plan({"lunch": {"meal_name": meal, "key_ingredients": []}})
    out = apply_dietary_type_safety(plan, dtype)
    assert out["dietary_type_safe"] is not expect_flag
    assert out["dietary_type_checked"] is True


def test_non_vegetarian_is_checked_rather_than_skipped():
    """`dietary_type_checked` must be True even when nothing is forbidden, so
    "no rules apply" is distinguishable from "the scan never ran"."""
    out = apply_dietary_type_safety(_plan(), "non_vegetarian")
    assert out["dietary_type_checked"] is True and out["dietary_type_safe"] is True


def test_dietary_type_never_raises_on_a_malformed_plan():
    out = apply_dietary_type_safety({"diet_weeks": [None, {"daily_plan": "nonsense"}]}, "vegan")
    assert out["dietary_type_checked"] is True


# ── 4. Pregnancy ──────────────────────────────────────────────────────────────

def test_pregnancy_has_a_floor_of_its_own():
    """`build_brief` lists the abortifacient risks to the model as a hard
    constraint and nothing checked the answer."""
    assert "pregnancy" in _CONDITION_APATHYA_TERMS
    plan = _plan({
        "breakfast": {"meal_name": "Raw Papaya Salad", "key_ingredients": ["raw papaya", "pineapple"]},
        "snack": {"meal_name": "Aloe Vera Juice", "key_ingredients": ["aloe vera"]},
    })
    out = apply_condition_food_safety(plan, [], pregnant=True)
    assert out["condition_food_safe"] is False
    assert {"papaya", "pineapple", "aloe vera"} <= {a["food"] for a in out["condition_safety_alerts"]}


def test_pregnancy_floor_is_off_when_not_pregnant():
    plan = _plan({"breakfast": {"meal_name": "Papaya Bowl", "key_ingredients": ["papaya"]}})
    assert apply_condition_food_safety(plan, [], pregnant=False)["condition_food_safe"] is True


# ── False positives ───────────────────────────────────────────────────────────

def test_an_ordinary_day_stays_clean_on_every_new_scan():
    """A floor that flags everything is a floor nobody reads."""
    assert apply_ahara_safety(_plan(drink=CCF_TEA), [], [])["allergen_safe"] is True
    assert apply_dietary_type_safety(_plan(drink=CCF_TEA), "vegetarian")["dietary_type_safe"] is True
    assert apply_condition_food_safety(_plan(drink=CCF_TEA), [], pregnant=True)["condition_food_safe"] is True


def test_the_existing_false_friends_still_hold():
    """`eggplant`/`eggless` must not trip an egg allergy, `lentil` must not trip
    sesame's `til` — the guards the drink scan now runs through too."""
    plan = _plan({
        "breakfast": {"meal_name": "Baingan Bharta (eggplant)", "key_ingredients": ["eggplant"]},
        "snack": {"meal_name": "Eggless Banana Cake", "key_ingredients": ["banana"]},
        "dinner": {"meal_name": "Masoor Lentil Soup", "key_ingredients": ["lentil"]},
    })
    assert apply_ahara_safety(plan, ["eggs", "sesame"], [])["allergen_safe"] is True
