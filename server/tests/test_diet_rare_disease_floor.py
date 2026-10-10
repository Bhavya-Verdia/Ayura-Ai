"""
The Apathya classifier for diseases outside the app's own vocabulary.

Three defects, found by running it on six real rare diseases and getting zero entries.

1. The whole batch shared a 700-token budget. One condition's name, reason and twenty
   food names is most of that, so six truncated mid-object, the JSON failed to parse,
   and every condition came back unscanned.
2. A transport or parse failure was cached as a negative, indistinguishable from "the
   model answered and had nothing for this disease" — so one bad request meant a
   permanent absence of a floor for every condition in that batch, for the life of
   the process.
3. The validator's comment said "keep only concrete, matchable food words" and the
   code checked length and nothing else. `day sleep`, `tea` and `heavy` all became
   scan terms.

The authored condition tables have to satisfy the same term rules — see
`test_no_scan_term_describes_a_behaviour` — and a term the model invents is now held
to them too.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

import services.ahara_safety as ahara
from services.ahara_safety import (
    _term_is_usable, _validate_apathya_classification, apply_condition_food_safety,
    classify_condition_apathya_llm,
)


@pytest.fixture(autouse=True)
def _clear_cache():
    ahara._CONDITION_APATHYA_CACHE.clear()
    yield
    ahara._CONDITION_APATHYA_CACHE.clear()


# --------------------------------------------------------------------------
# Term hygiene
# --------------------------------------------------------------------------

@pytest.mark.parametrize("term", [
    "day sleep", "sleeping during the day", "suppression of urges",
    "sitting for long hours", "skipping meals", "fasting", "travel",
])
def test_a_behaviour_is_not_a_scan_term(term):
    """Apathya in the classical sources is a regimen, so the model returns conduct
    when asked for foods. As scan terms these search meal text for `sitting`."""
    assert not _term_is_usable(term)


@pytest.mark.parametrize("term", [
    "tea", "water", "oil", "food", "heavy", "cold", "spices", "anything", "salt",
])
def test_a_term_with_no_food_in_it_is_rejected(term):
    """`tea` is the form half of Ayurvedic medicine takes, `water` is in every drink
    recipe, `oil` is in every tadka and `salt` is in every savoury meal. A term this
    broad does not warn a patient, it trains them to stop reading warnings."""
    assert not _term_is_usable(term)


@pytest.mark.parametrize("term", [
    "curd", "black tea", "red meat", "mustard oil", "deep fried", "extra salt",
    "salted", "wheat", "sugar", "white flour", "ice cream",
])
def test_a_real_food_term_survives(term):
    """The filters must not swallow the terms that do the work. `wheat` in particular:
    it is the whole point of a celiac floor, and it is a staple, so a rule that
    rejected staples would remove the one term that matters."""
    assert _term_is_usable(term)


def test_the_validator_drops_unusable_terms_but_keeps_the_entry():
    entry = _validate_apathya_classification(
        {"name": "X", "reason": "y",
         "apathya_foods": ["curd", "day sleep", "tea", "red meat", "salt"]},
        "X")
    assert entry["terms"] == ["curd", "red meat"]


def test_an_entry_with_nothing_usable_is_no_entry():
    entry = _validate_apathya_classification(
        {"name": "X", "reason": "y", "apathya_foods": ["day sleep", "tea", "heavy"]},
        "X")
    assert entry is None


# --------------------------------------------------------------------------
# The batch, and what a failure means
# --------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_the_token_budget_scales_with_the_batch():
    """A fixed 700 for the whole batch truncated at six conditions."""
    seen = {}

    async def _capture(**kwargs):
        seen["max_tokens"] = kwargs.get("max_tokens")
        return json.dumps({})

    with patch.object(ahara, "_CONDITION_APATHYA_CACHE", {}):
        with patch("ai.llm_client.llm_client") as m:
            m.generate = AsyncMock(side_effect=_capture)
            await classify_condition_apathya_llm([f"rare disease {i}" for i in range(6)])
    assert seen["max_tokens"] > 700


@pytest.mark.asyncio
async def test_a_failed_request_is_not_cached_as_an_answer():
    """One truncated response used to mean a permanent "no floor" for every condition
    in the batch. A transport error is not evidence about the disease."""
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(side_effect=RuntimeError("timeout"))
        result = await classify_condition_apathya_llm(["takayasu arteritis"])
    assert result == {}
    assert "takayasu_arteritis" not in ahara._CONDITION_APATHYA_CACHE

    # The retry succeeds, which the poisoned cache made impossible.
    good = json.dumps({"Takayasu Arteritis": {
        "name": "Takayasu Arteritis", "reason": "r",
        "apathya_foods": ["red meat", "fried foods"]}})
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(return_value=good)
        result = await classify_condition_apathya_llm(["takayasu arteritis"])
    assert "takayasu_arteritis" in result


@pytest.mark.asyncio
async def test_an_answered_negative_is_cached_so_it_is_not_re_asked():
    """The other half of the same rule: when the model did answer and had nothing
    usable, asking again costs a call and returns the same nothing."""
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(return_value=json.dumps({"Odd Syndrome": {
            "name": "Odd Syndrome", "reason": "r", "apathya_foods": ["day sleep"]}}))
        await classify_condition_apathya_llm(["odd syndrome"])
    assert ahara._CONDITION_APATHYA_CACHE.get("odd_syndrome") is None
    assert "odd_syndrome" in ahara._CONDITION_APATHYA_CACHE


# --------------------------------------------------------------------------
# Saying so when there is no floor
# --------------------------------------------------------------------------

def test_a_condition_with_no_floor_is_named_not_silently_passed():
    """Silence reads as "checked and clear", which is the opposite of what happened.
    `DietView` shows a partial all-clear off this field."""
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": "Moong Dal Khichdi", "key_ingredients": []}}}}]}
    out = apply_condition_food_safety(dict(plan), ["diabetes_type2", "odd_syndrome"])
    assert out["conditions_without_food_floor"] == ["odd_syndrome"]


def test_a_fully_covered_patient_has_an_empty_list_not_a_missing_key():
    """An absent key and an empty list read the same in the UI only by accident."""
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": "Moong Dal Khichdi", "key_ingredients": []}}}}]}
    out = apply_condition_food_safety(dict(plan), ["diabetes_type2"])
    assert out["conditions_without_food_floor"] == []


def test_a_patient_with_no_conditions_at_all_is_not_told_anything_is_unscanned():
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": "Moong Dal Khichdi", "key_ingredients": []}}}}]}
    out = apply_condition_food_safety(dict(plan), [])
    assert out["conditions_without_food_floor"] == []
    assert out["condition_food_safe"] is True
