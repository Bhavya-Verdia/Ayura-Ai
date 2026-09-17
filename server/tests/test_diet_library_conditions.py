"""
The authored library's per-condition claims, on the path users actually get.

`diet_foods.json` holds 370 (condition, food) Apathya claims and 338 Pathya claims.
`apathya_for` gated `diet_plan_engine` — the **fallback** — and nothing else;
`pathya_for` gated nothing at all. On the LLM-primary path the floor was a separately
hand-written table, and measured against the library 333 of the 370 exclusions were
unenforced there: an acidity patient could be served green tea, lemon water, curd,
dry ginger and black pepper, every one of them authored as Apathya for acidity. The
fallback was clinically stricter than the primary path.

Deriving scan terms from food names is the part that goes wrong, so most of what is
asserted here is about what must *not* fire.
"""
import copy

import pytest

from services.ahara_safety import _CONDITION_APATHYA_TERMS, apply_condition_food_safety
from services.diet_condition_foods import (
    _by_id, condition_food_rules, library_conditions,
)


def _plan(meal_name, ingredients=()):
    return {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": meal_name, "key_ingredients": list(ingredients)},
    }}}]}


def _foods(condition):
    return {a["food"] for a in condition["condition_safety_alerts"]}


# --------------------------------------------------------------------------
# The claims reach the primary path at all
# --------------------------------------------------------------------------

def test_the_library_gates_the_llm_path_not_only_the_fallback():
    """Green tea is authored Apathya for acidity and the curated table does not name
    it. Before this, an acidity patient's plan could serve it and report
    `condition_food_safe: True`."""
    out = apply_condition_food_safety(_plan("Green Tea with lemon"), ["acidity"])
    assert out["condition_food_safe"] is False
    assert "green tea" in _foods(out)


@pytest.mark.parametrize("condition,meal", [
    ("acidity", "Nimbu Jala (lemon water)"),
    ("acidity", "Shunthi Kwatha — dry ginger tea"),
    ("hypothyroid", "Cabbage and Cauliflower Sabzi"),
    ("fatty_liver", "Khichdi finished with ghee"),
    ("diabetes", "Sooji Halwa with dates"),
])
def test_authored_apathya_fires_on_the_primary_path(condition, meal):
    out = apply_condition_food_safety(_plan(meal), [condition])
    assert out["condition_food_safe"] is False, f"{meal} passed for {condition}"


def test_the_curated_table_is_not_replaced_by_the_library():
    """The two were authored separately and each names foods the other does not, so
    the floor is their union. `maida` is curated-only for diabetes."""
    out = apply_condition_food_safety(_plan("Maida Paratha"), ["diabetes"])
    assert "maida" in _foods(out)


def test_every_library_condition_yields_at_least_one_usable_term():
    thin = [c for c in library_conditions()
            if condition_food_rules(c)["apathya_names"]
            and not condition_food_rules(c)["apathya_terms"]]
    assert not thin, f"conditions whose claims produce no matchable term: {thin}"


# --------------------------------------------------------------------------
# What must not fire — the prep-state distinctions the library exists to keep
# --------------------------------------------------------------------------

def test_a_term_is_not_borrowed_across_a_prep_state_split():
    """`banana` (ripe) and `raw_banana` disagree about constipation. A term "banana"
    speaks for both and throws the distinction away — the scan flagged a ripe banana
    for a constipated patient, where the library contraindicates only the unripe one."""
    assert "banana" not in condition_food_rules("constipation")["apathya_terms"]
    assert "raw banana" in condition_food_rules("constipation")["apathya_terms"]


def test_a_shared_term_survives_when_its_foods_agree():
    """Ambiguity alone is not disqualifying. Ghee is entered twice, as a dairy and as
    an oil, and both rows agree it is Apathya in fatty liver."""
    assert "cow's ghee" in condition_food_rules("fatty_liver")["apathya_terms"]


def test_a_shared_term_is_dropped_when_its_foods_disagree():
    """`kidney_beans` and `rajma` are the same bean entered under two categories and
    disagree about diabetes; `chana_dal`/`chhole` and `lentils_brown`/`masoor_dal`
    disagree too. Until a Vaidya rules, no shared term speaks for a condition its own
    rows cannot agree on."""
    assert "kidney beans" not in condition_food_rules("diabetes")["apathya_terms"]


def test_a_modifier_is_not_a_food_name():
    """A parenthetical is usually the English translation — 'Shunthi (Dry Ginger)' —
    but 'Tofu (Firm)' is a variant, and taking that half yielded the term "firm",
    which fired on a hypothyroid patient for a word describing texture."""
    for condition in library_conditions():
        assert "firm" not in condition_food_rules(condition)["apathya_terms"]


@pytest.mark.parametrize("condition,meal", [
    ("diabetes", "Kadali Kanda Sabzi (raw banana curry)"),
    ("diabetes", "Raw Mango Chutney"),
    ("asthma", "Raw Banana Kofta"),
])
def test_the_permitted_sibling_is_exempted_by_name(condition, meal):
    """The curated table's bare `banana` and `mango` still fire on an unqualified
    mention — a meal that just says "banana" is usually the ripe one — but the
    permitted form is exempted rather than the term being narrowed away."""
    out = apply_condition_food_safety(_plan(meal), [condition])
    assert out["condition_food_safe"] is True, f"{meal} flagged for {condition}"


def test_the_ripe_form_still_fires():
    """The exemption must not disarm the term it qualifies."""
    out = apply_condition_food_safety(_plan("Banana Sheera"), ["diabetes"])
    assert "banana" in _foods(out)


# --------------------------------------------------------------------------
# Conditions the app recognises but the library could not be reached for
# --------------------------------------------------------------------------

@pytest.mark.parametrize("app_condition,library_key,meal", [
    ("piles", "arsha", "Rajma Chawal"),
    ("hemorrhoids", "arsha", "Rajma Chawal"),
    ("constipation_chronic", "constipation", "Green Tea"),
])
def test_a_classical_library_key_is_reachable_from_the_app_vocabulary(
        app_condition, library_key, meal):
    """`hemorrhoids` and `constipation_chronic` are canonical app conditions with no
    library key of their own, while the library holds the same diseases under their
    classical names. A patient who entered "piles" reached none of the 15 Apathya
    claims authored for Arsha.

    Asserted end to end rather than on `condition_food_rules` directly, because the
    canonicalisation is now the caller's and a unit-level check would pass while the
    patient still got nothing.
    """
    from services.ahara_safety import _canon_condition
    assert _canon_condition(app_condition) == library_key
    out = apply_condition_food_safety(_plan(meal), [app_condition])
    assert out["condition_food_safe"] is False, f"{meal} passed for {app_condition}"


def test_grahani_claims_are_reachable():
    """`grahani` is reachable from no app condition. Its Apathya set is a strict
    subset of `ibs`'s and its Pathya list adds 11 foods `ibs` does not carry, so the
    library's own tagging treats it as the classical label for the same territory —
    and those 11 recommendations reached nobody."""
    ibs = condition_food_rules("ibs")
    grahani_only = set(condition_food_rules("grahani")["pathya_names"])
    assert grahani_only <= set(ibs["pathya_names"])
    assert len(ibs["pathya_names"]) > 10


# --------------------------------------------------------------------------
# Over-restriction
# --------------------------------------------------------------------------

def test_a_condition_never_excludes_its_own_recommendation():
    """A food Apathya under one of a condition's keys and Pathya under another is not
    offered as a recommendation — the restriction wins, the same direction
    `_CONDITION_PRIORITY` resolves a multi-condition conflict."""
    for condition in library_conditions():
        rules = condition_food_rules(condition)
        assert not (set(rules["apathya_names"]) & set(rules["pathya_names"]))


def test_no_condition_is_left_with_nothing_to_eat():
    """`apathya_for` acting as a filter is measured against the no-condition baseline,
    not against zero. Even the most heavily restricted condition must leave the
    library with a workable number of foods."""
    total = len(_by_id())
    for condition in library_conditions():
        excluded = len(condition_food_rules(condition)["apathya_names"])
        assert total - excluded >= 90, (
            f"{condition} excludes {excluded} of {total} foods")


def test_the_curated_terms_do_not_contradict_the_library():
    """A curated term that matches a food the library *recommends* for the same
    condition is a guaranteed false positive. Two existed: `banana` for diabetes
    (raw banana is authored Pathya there) and `coconut water` for kidney disease.

    The coconut-water one is left firing on purpose and is listed here as known:
    tender coconut water is high in potassium, which is exactly what renal diets
    restrict, so the curated term is right and the library row is the one to review.
    """
    import re
    from services.diet_condition_foods import _norm, _surfaces

    known = {("kidney_disease", "coconut water")}
    contradictions = set()
    for condition, proto in _CONDITION_APATHYA_TERMS.items():
        pathya = set(condition_food_rules(condition)["pathya_names"])
        if not pathya:
            continue
        exempt = {_norm(e) for e in (proto.get("exempt") or ())}
        for term in proto["terms"]:
            pattern = re.compile(rf"(?<!\w){re.escape(_norm(term))}(?!\w)")
            for food in _by_id().values():
                if food["name"] not in pathya:
                    continue
                if not any(pattern.search(s) for s in _surfaces(food)):
                    continue
                # An exemption covering this food resolves the contradiction: the
                # term still fires on an unqualified mention, and the recommended
                # sibling is let through by name.
                if any(e in s for e in exempt for s in _surfaces(food)):
                    continue
                contradictions.add((condition, term))
    assert contradictions == known, f"new contradictions: {contradictions - known}"


def test_the_scan_never_raises_on_a_condition_the_library_has_never_heard_of():
    out = apply_condition_food_safety(
        copy.deepcopy(_plan("Moong Dal Khichdi")), ["a_disease_that_does_not_exist"])
    assert out["condition_safety_checked"] is True


def test_the_number_of_withheld_claims_is_pinned():
    """A name owned by several foods can only speak for a condition all of them agree
    about, so where they disagree the claim is authored and does not fire. Most of
    these are the rule working — "banana" is withheld for diabetes because only the
    ripe row carries it, and the raw row is a different food.

    The count is pinned rather than the list, because the number moving is the
    signal: a new collision means a newly authored claim has gone quiet, which is the
    failure this module exists to make visible rather than silent. If this figure
    rises after a library change, check whether the new row's name collides with an
    existing one before accepting it.
    """
    from services.diet_condition_foods import withheld_claims
    assert len(withheld_claims()) == 69
