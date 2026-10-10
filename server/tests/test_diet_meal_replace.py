"""Another dish in place of one meal (`services/diet_meal_swap`), and the regional
cuisine on the rule-engine path."""
import pytest

import services.diet_llm_generator as gen
from services import diet_nutrition as dn
from services.diet_clinical_notes import CUISINE_STAPLES
from services.diet_meal_swap import candidates, replace_meal, restore_meal
from services.diet_plan_engine import generate_diet_plan
from tests.diet_fake_llm import make_fake

_BASE = {"id": "u1", "age": 35, "gender": "female", "height_cm": 160, "weight_kg": 60,
         "bmi_category": "normal", "activity_level": "moderate", "dominant_dosha": "vata",
         "agni_type": "sama"}


@pytest.fixture
async def plan(monkeypatch):
    async def none(*a, **k):
        return []
    monkeypatch.setattr(gen.rag_pipeline, "query", none)
    monkeypatch.setattr(gen.llm_client, "generate", make_fake([]))
    p = await gen.generate_diet_plan_llm(dict(_BASE), {})
    # The fake names every lunch "lunch plate"; real plans name each dish.
    for w in p["diet_weeks"]:
        for d, day in w["daily_plan"].items():
            for s in ("breakfast", "lunch", "snack", "dinner"):
                day[s]["meal_name"] = f"{s} {w['week_number']} {d}"
    return p


def _all_ids():
    return set(dn.all_ids())


def _safe(_meal):
    return True


@pytest.mark.asyncio
async def test_a_meal_is_replaced_by_another_dish_of_the_same_kind_and_size(plan):
    before = plan["diet_weeks"][1]["daily_plan"]["Tuesday"]
    kcal = before["lunch"]["macros_approx"]["calories"]
    day = replace_meal(plan, 2, "Tuesday", "lunch", allowed_ids=_all_ids(), is_safe=_safe)
    new = day["lunch"]
    assert new["meal_name"].startswith("lunch ") and new["meal_name"] != "lunch 2 Tuesday"
    assert new["replaced_from"]["meal_name"] == "lunch 2 Tuesday"
    assert new["macros_approx"]["calories"] == pytest.approx(kcal, rel=0.1)
    # The other meals are untouched, and the day's totals follow the new one.
    assert day["dinner"] == before["dinner"]
    assert day["day_totals"]["calories"] == pytest.approx(
        before["day_totals"]["calories"] - kcal + new["macros_approx"]["calories"], abs=2)


@pytest.mark.asyncio
async def test_asking_again_steps_to_the_next_dish_and_undo_puts_the_first_back(plan):
    first = replace_meal(plan, 1, "Monday", "dinner", allowed_ids=_all_ids(), is_safe=_safe)
    plan["diet_weeks"][0]["daily_plan"]["Monday"] = first
    second = replace_meal(plan, 1, "Monday", "dinner", allowed_ids=_all_ids(), is_safe=_safe)
    assert second["dinner"]["meal_name"] != first["dinner"]["meal_name"]
    # The original is remembered through every replacement, not just the last.
    assert second["dinner"]["replaced_from"]["meal_name"] == "dinner 1 Monday"
    plan["diet_weeks"][0]["daily_plan"]["Monday"] = second
    back = restore_meal(plan, 1, "Monday", "dinner")
    assert back["dinner"]["meal_name"] == "dinner 1 Monday"
    assert "replaced_from" not in back["dinner"]


@pytest.mark.asyncio
async def test_a_dish_with_a_food_no_longer_allowed_is_never_offered(plan):
    """A food reported in a check-in, or an allergy added since the plan was written."""
    grain = next(c["food"] for c in plan["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["components"]
                 if dn.role(c["food"]) == "grain")
    assert replace_meal(plan, 1, "Monday", "lunch", allowed_ids=_all_ids() - {grain},
                        is_safe=_safe) is None


@pytest.mark.asyncio
async def test_a_dish_the_scans_reject_is_skipped(plan):
    seen = []

    def reject_first(meal):
        seen.append(meal["meal_name"])
        return len(seen) > 1
    day = replace_meal(plan, 1, "Monday", "lunch", allowed_ids=_all_ids(), is_safe=reject_first)
    assert day["lunch"]["meal_name"] == seen[1]


@pytest.mark.asyncio
async def test_a_fasting_meal_is_only_replaced_by_a_fasting_meal(plan):
    for w in plan["diet_weeks"]:
        w["daily_plan"]["Monday"]["is_fasting"] = True
    names = {m["meal_name"] for m in candidates(plan, 2, "Monday", "lunch")}
    assert names and all(n.endswith("Monday") for n in names)
    names = {m["meal_name"] for m in candidates(plan, 2, "Tuesday", "lunch")}
    assert not any(n.endswith("Monday") for n in names)


def test_restore_refuses_a_meal_that_was_never_replaced():
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {"lunch": {"meal_name": "x"}}}}]}
    with pytest.raises(LookupError):
        restore_meal(plan, 1, "Monday", "lunch")


# ── Cuisine on the rule-engine path ──────────────────────────────────────────

def test_every_regional_staple_is_a_real_food():
    ids = _all_ids()
    for cuisine, staples in CUISINE_STAPLES.items():
        assert set(staples) <= ids, (cuisine, set(staples) - ids)


@pytest.mark.parametrize("cuisine", sorted(CUISINE_STAPLES))
def test_the_rule_engine_leans_toward_the_chosen_cuisine(cuisine):
    """The brief named the cuisine; the engine, which cannot read a sentence, did not,
    so a plan that fell back to it lost the patient's cuisine silently."""
    def share(prefs):
        raw = generate_diet_plan(dict(_BASE), prefs)
        ids = [i["id"] for w in raw["four_week_plan"] for d in w["days"]
               for m in d["meals"].values() for i in m]
        return sum(i in CUISINE_STAPLES[cuisine] for i in ids) / len(ids)
    assert share({"cuisine_preference": cuisine}) > 1.5 * share({})
