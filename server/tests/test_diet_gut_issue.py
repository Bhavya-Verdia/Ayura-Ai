"""The diet form's own gut question reaches the engines that can act on it.

`gut_health_issue` is asked on the diet preferences form and every one of its four
values is a disease. Three — acidity, constipation, ibs — were already canonical keys
with a `PATHYA_APATHYA_HINTS` block, a `_CONDITION_APATHYA_TERMS` floor and authored
`apathya_for` / `pathya_for` claims on the library's 150 rows.

None of it reached them. The condition list every part of the diet path built came from
`medical_history` alone, and the answer given on the diet form was rendered into the
brief as the single line `GUT HEALTH: Acidity`. Measured on one patient: the same
disease declared on the diet form produced a 1,812-character brief naming 0 Apathya
foods; declared in `medical_history` it produced 3,789 and named 50.
"""

import pytest

from services.ahara_safety import (
    _CONDITION_APATHYA_TERMS,
    _canon_condition,
    apply_condition_food_safety,
)
from services.diet_brief_builder import (
    PATHYA_APATHYA_HINTS,
    _GUT_ISSUE_CONDITIONS,
    build_brief,
    diet_conditions,
)

_PROFILE = {
    "dominant_dosha": "pitta", "agni_type": "tikshna", "age": 34, "gender": "male",
    "height_cm": 175, "weight_kg": 72, "activity_level": "moderate",
    "bmi_category": "normal", "current_season": "grishma", "medical_history": [],
}


def _prefs(**over):
    base = {
        "dietary_type": "vegetarian", "diet_goal": "general_wellness",
        "food_allergies": [], "food_intolerances": [], "gut_health_issue": "healthy",
        "intermittent_fasting": "no", "water_intake": "2-3L", "fasting_days": [],
    }
    base.update(over)
    return base


@pytest.mark.parametrize("gut", sorted(_GUT_ISSUE_CONDITIONS))
def test_a_declared_gut_issue_is_a_condition_everywhere(gut):
    """The whole point: it is in the list the brief and the scan both read."""
    assert diet_conditions(_PROFILE, _prefs(gut_health_issue=gut)) == [
        _GUT_ISSUE_CONDITIONS[gut]
    ]


def test_healthy_declares_no_disease():
    assert diet_conditions(_PROFILE, _prefs(gut_health_issue="healthy")) == []
    assert diet_conditions(_PROFILE, _prefs(gut_health_issue="")) == []
    assert diet_conditions(_PROFILE, None) == []


def test_the_same_disease_in_both_places_is_carried_once():
    """`medical_history` wins the spelling; the gut answer must not duplicate the
    block, which would put the same Apathya list in the brief twice."""
    prof = {**_PROFILE, "medical_history": ["acidity"]}
    assert diet_conditions(prof, _prefs(gut_health_issue="acidity")) == ["acidity"]


def test_a_gut_issue_and_a_comorbidity_are_both_carried():
    prof = {**_PROFILE, "medical_history": ["diabetes"]}
    assert diet_conditions(prof, _prefs(gut_health_issue="ibs")) == ["diabetes", "ibs"]


@pytest.mark.parametrize("gut", ["acidity", "constipation", "ibs"])
def test_the_brief_carries_the_protocol_not_a_label(gut):
    """Before: the brief's only mention was `GUT HEALTH: Acidity`. The protocol block,
    the library's named Apathya foods and the classical reference were all absent."""
    brief = build_brief(_PROFILE, _prefs(gut_health_issue=gut))
    hint = PATHYA_APATHYA_HINTS[gut]
    assert hint["ayurvedic_name"] in brief
    assert hint["classical_ref"] in brief
    assert "DO NOT USE (library Apathya for this disease" in brief
    # And it is still identified as the presenting complaint, which the condition
    # list alone cannot say.
    assert "the presenting digestive complaint" in brief


def test_the_brief_grows_by_the_whole_protocol():
    """The measurement from the report, as a regression guard."""
    healthy = build_brief(_PROFILE, _prefs(gut_health_issue="healthy"))
    acidity = build_brief(_PROFILE, _prefs(gut_health_issue="acidity"))
    assert len(acidity) > len(healthy) + 1500


@pytest.mark.parametrize("gut,food,ingredient", [
    ("acidity", "curd", "curd"),
    ("ibs", "raw cabbage salad", "cabbage"),
    ("bloating", "rajma", "rajma"),
])
def test_the_scan_withholds_the_gut_issues_apathya(gut, food, ingredient):
    """The deterministic floor, not the prompt. This is what `medical_history`
    patients had and diet-form patients did not."""
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": f"Lunch with {food}", "key_ingredients": [ingredient]}}}}]}
    out = apply_condition_food_safety(
        plan, diet_conditions(_PROFILE, _prefs(gut_health_issue=gut)),
        extra_terms={}, pregnant=False)
    assert out["condition_food_safe"] is False
    assert ingredient in {a["food"] for a in out["condition_safety_alerts"]}


def test_bloating_is_authored_in_both_tables():
    """Adhmana was the one gut value that was not already a canonical condition. It is
    authored rather than aliased onto IBS or constipation: its Samprapti is Vata
    obstructed by Ama in the Pakvashaya, so its Apathya is the Vatala and gas-forming
    foods — not IBS's sour-and-raw list, and not constipation's dry-and-cold one."""
    assert "bloating" in PATHYA_APATHYA_HINTS
    assert _canon_condition("bloating") in _CONDITION_APATHYA_TERMS
    terms = set(_CONDITION_APATHYA_TERMS["bloating"]["terms"])
    assert {"rajma", "cabbage", "carbonated"} <= terms
    # Moong is this condition's Pathya. A blanket `legume`/`dal` term would withhold
    # the one pulse the protocol is built on.
    assert not any(t in terms for t in ("legume", "dal", "pulse", "beans"))


def test_bloating_apathya_is_not_a_copy_of_its_neighbours():
    """A mirror-not-copy check, the same rule hyperthyroidism is held to."""
    bloat = set(_CONDITION_APATHYA_TERMS["bloating"]["terms"])
    for other in ("ibs", "constipation", "acidity"):
        assert bloat != set(_CONDITION_APATHYA_TERMS[other]["terms"])


def test_the_rule_engine_fallback_sees_the_gut_issue_too():
    """The fallback path builds its own condition rules. It read `medical_history`
    alone, so the engine's Apathya filter — which carries library rows for acidity,
    IBS and constipation — withheld nothing from a diet-form patient."""
    from services.diet_plan_engine import diet_foods, filter_and_score_foods

    prefs = _prefs(gut_health_issue="acidity")
    pool = {f["id"] for f in filter_and_score_foods(_PROFILE, prefs, diet_foods)}
    # `apathya_for` is applied off `cond_rules["conditions"]`, so a food the library
    # authors as Apathya for Amlapitta must not survive the filter.
    apathya = {f["id"] for f in diet_foods
               if "acidity" in (f.get("apathya_for") or ())}
    assert apathya, "fixture assumption: the library carries acidity Apathya rows"
    assert not (pool & apathya), sorted(pool & apathya)

    # And the same patient without the gut answer keeps them — i.e. the exclusion is
    # caused by the diet form's answer and nothing else.
    open_pool = {f["id"] for f in filter_and_score_foods(
        _PROFILE, _prefs(gut_health_issue="healthy"), diet_foods)}
    assert open_pool & apathya
