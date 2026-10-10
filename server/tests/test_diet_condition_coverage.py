"""
Every condition the app recognises has a dietary rule, and both surfaces agree on
which condition it is.

`engine/condition_vocab` accepts 38 canonical conditions. Twenty-one had no entry in
`PATHYA_APATHYA_HINTS`, no entry in `_CONDITION_APATHYA_TERMS`, and no claim in the
authored food library, so the brief told the model to "use your classical Ayurvedic
knowledge" and the deterministic floor was whatever `classify_condition_apathya_llm`
invented. Gout and kidney stones were among them — the two conditions here where diet
is most of the treatment.

Separately, the feature had two canonical-condition tables that disagreed on 22
inputs. That is not cosmetic: `uncurated_conditions()` skips the LLM classifier
whenever the *brief* recognises a condition, so an input the brief canonicalised and
the scan did not received the curated floor from neither table and the classifier from
neither path — the same shape as the eight conditions PR #62 found between these two
tables, reopened by a second alias map nobody thought of as one.
"""
import copy

import pytest

from engine.condition_vocab import CONDITION_ALIASES
from services.ahara_safety import (
    _CONDITION_APATHYA_TERMS, _canon_condition, apply_condition_food_safety,
)
from services.diet_brief_builder import (
    PATHYA_APATHYA_HINTS, normalize_condition_key, uncurated_conditions,
)
from services.diet_condition_foods import condition_food_rules

_VOCAB_INPUTS = sorted(
    set(CONDITION_ALIASES)
    | {a.replace(" ", "_") for aliases in CONDITION_ALIASES.values() for a in aliases}
)


def _plan(meal_name):
    return {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": meal_name, "key_ingredients": []},
    }}}]}


# --------------------------------------------------------------------------
# Coverage
# --------------------------------------------------------------------------

@pytest.mark.parametrize("condition", sorted(CONDITION_ALIASES))
def test_every_recognised_condition_has_a_dietary_rule(condition):
    canon = _canon_condition(condition)
    has_hint = canon in PATHYA_APATHYA_HINTS
    has_terms = bool((_CONDITION_APATHYA_TERMS.get(canon) or {}).get("terms"))
    has_library = bool(condition_food_rules(canon)["apathya_names"])
    assert has_hint and has_terms, (
        f"{condition} -> {canon}: hint={has_hint} scan={has_terms} library={has_library}"
    )


@pytest.mark.parametrize("condition,meal", [
    ("gout", "Mutton Curry with Rice"),
    ("gout", "Prawn Masala"),
    ("kidney_stones", "Palak Paneer"),
    ("gallstones", "Puri Bhaji with butter"),
    ("heart_disease", "Mutton Biryani with papad"),
    ("hyperthyroidism", "Strong Filter Coffee"),
    ("osteoarthritis", "Curd Rice, chilled"),
    ("sciatica", "Rajma Chawal with curd"),
    ("anxiety", "Cold Brew Coffee"),
    ("epilepsy", "Reheated leftover Pulao"),
    ("eczema", "Fish Curry with curd"),
    ("sinusitis", "Banana Milkshake with ice cream"),
    ("recurrent_uti", "Red Chilli Pickle with rice"),
    ("glaucoma", "Salted Papad and strong tea"),
    ("vertigo", "Tamarind Rice with papad"),
    ("long_covid", "Deep-fried Samosa, refrigerated"),
])
def test_an_authored_condition_actually_fires(condition, meal):
    out = apply_condition_food_safety(_plan(meal), [condition])
    assert out["condition_food_safe"] is False, f"{meal} passed for {condition}"


def test_hyperthyroidism_is_the_mirror_of_hypothyroidism_not_a_copy():
    """The goitrogenic brassicas restricted in Galaganda with hypofunction are Pathya
    where function is excessive. A condition table that treated "thyroid" as one
    entry would have got this backwards for half the patients who have it."""
    hypo = " ".join(_CONDITION_APATHYA_TERMS["hypothyroid"]["terms"])
    hyper = " ".join(_CONDITION_APATHYA_TERMS["hyperthyroidism"]["terms"])
    assert "cabbage" in hypo, "the hypofunction entry restricts the brassicas"
    assert "cabbage" not in hyper and "broccoli" not in hyper
    assert "cabbage, cauliflower and broccoli" in PATHYA_APATHYA_HINTS["hyperthyroidism"]["pathya"]
    # And the library agrees on the restricted side, which is where it came from.
    assert "cabbage" in condition_food_rules("hypothyroid")["apathya_terms"]


def test_low_blood_pressure_does_not_restrict_salt():
    """Every other cardiovascular entry here restricts sodium. This is the one where
    that advice is inverted, and a term list copied from hypertension would have told
    a hypotensive patient to cut the thing they need."""
    terms = _CONDITION_APATHYA_TERMS["low_blood_pressure"]["terms"]
    assert not [t for t in terms if "salt" in t]
    assert any("salt" in p for p in PATHYA_APATHYA_HINTS["low_blood_pressure"]["pathya"])


def test_a_condition_without_a_classical_counterpart_says_so():
    """Long COVID and hypotension have no Nidana of their own. Inventing a Samhita
    chapter for them would make every other `classical_ref` here worth less."""
    for condition in ("long_covid", "low_blood_pressure"):
        hint = PATHYA_APATHYA_HINTS[condition]
        assert hint.get("modern_extrapolated") is True
        assert "no classical Nidana" in hint["classical_ref"]


# --------------------------------------------------------------------------
# One canonicaliser
# --------------------------------------------------------------------------

@pytest.mark.parametrize("value", _VOCAB_INPUTS)
def test_the_brief_and_the_scan_agree_on_the_disease(value):
    assert _canon_condition(value) == normalize_condition_key(value)


def test_no_condition_is_curated_in_the_brief_and_enforced_by_nothing():
    """`uncurated_conditions()` skips the classifier when the brief has a hint, so a
    condition the brief recognises and the scan does not gets no floor at all."""
    uncovered = sorted(c for c in PATHYA_APATHYA_HINTS
                       if _canon_condition(c) not in _CONDITION_APATHYA_TERMS)
    assert not uncovered


def test_no_hint_is_unreachable():
    """A hint whose key canonicalises onto a different key can never be selected.
    `grahani`, `rheumatoid_arthritis` and `thyroid_disorder` were all in that state —
    authored prose that no patient could reach."""
    unreachable = sorted(k for k in PATHYA_APATHYA_HINTS if _canon_condition(k) != k)
    assert not unreachable


@pytest.mark.parametrize("alias,target", [
    ("piles", "arsha"), ("hemorrhoids", "arsha"), ("iron_deficiency", "anemia"),
    ("ulcerative_colitis", "ibs"), ("crohns", "ibs"), ("rheumatoid", "amavata"),
    ("skin_disease", "psoriasis"), ("thyroidism", "thyroid"),
    ("constipation_chronic", "constipation"),
])
def test_the_aliases_that_had_a_floor_on_only_one_side(alias, target):
    assert _canon_condition(alias) == target
    assert target in _CONDITION_APATHYA_TERMS
    assert not uncurated_conditions([alias]), (
        f"{alias} is recognised by the brief, so it is skipped by the classifier — "
        "it must reach a curated floor instead")


def test_eczema_is_no_longer_treated_as_psoriasis():
    """Vicharchika was canonicalised onto psoriasis, so an eczema patient was given a
    different disease's Pathya. It is authored in its own right now."""
    assert _canon_condition("eczema") == "eczema"
    assert PATHYA_APATHYA_HINTS["eczema"]["ayurvedic_name"].startswith("Vicharchika")


# --------------------------------------------------------------------------
# Over-restriction and term hygiene
# --------------------------------------------------------------------------

def test_no_condition_flags_a_neutral_day():
    from tests.test_diet_safety_gaps import CCF_TEA, SAFE_MEALS

    for condition in PATHYA_APATHYA_HINTS:
        day = {**copy.deepcopy(SAFE_MEALS), "special_drink": CCF_TEA}
        plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": day}}]}
        out = apply_condition_food_safety(plan, [condition])
        assert out["condition_food_safe"] is True, (
            f"{condition} flags a plain day: "
            f"{sorted({a['food'] for a in out['condition_safety_alerts']})}")


def test_no_scan_term_contradicts_its_own_conditions_pathya():
    """A term that matches the same entry's own recommendation is a guaranteed false
    positive and teaches the patient to ignore the warnings."""
    from services.ahara_safety import _term_in_text

    bad = []
    for condition, proto in _CONDITION_APATHYA_TERMS.items():
        hint = PATHYA_APATHYA_HINTS.get(condition)
        if not hint:
            continue
        pathya = " ; ".join(hint["pathya"]).lower()
        exempt = [e.lower() for e in (proto.get("exempt") or ())]
        for term in proto["terms"]:
            if _term_in_text(term, pathya) and not any(e in pathya for e in exempt):
                bad.append((condition, term))
    assert not bad


def test_no_scan_term_describes_a_behaviour():
    """The Apathya prose beside these includes behaviours — "sleeping during the day",
    "holding the urge to urinate". Deriving terms from that phrasing is how a scan
    ends up searching meal text for `sitting` and `travel`."""
    behaviours = {"sleeping", "sleep", "sitting", "standing", "travel", "holding",
                  "suppression", "skipping", "exertion", "fasting", "walking"}
    bad = [(c, t) for c, p in _CONDITION_APATHYA_TERMS.items() for t in p["terms"]
           if set(t.split()) & behaviours]
    assert not bad


def test_the_authored_protocols_are_in_the_vaidya_packet():
    """These are ~500 clinical claims authored in one pass and reviewed by nobody. The
    packet is the instrument that gets them in front of a BAMS; a claim that acts on a
    patient's plan and appears in no reviewable artifact is the state this project has
    been working out of, not into."""
    import csv
    from pathlib import Path

    path = (Path(__file__).resolve().parent.parent / "data" / "golden"
            / "vaidya_diet_condition_protocols.csv")
    rows = list(csv.DictReader(path.open(encoding="utf-8")))
    conditions = {r["condition"] for r in rows}
    for newly_authored in ("gout", "kidney_stones", "hyperthyroidism", "long_covid"):
        assert newly_authored in conditions
    assert {r["condition"] for r in rows} == set(PATHYA_APATHYA_HINTS)
    # The reviewer has to be able to tell which rejections change a served meal.
    assert {r["enforced_by_scan"] for r in rows if r["kind"] == "apathya"} <= {"yes", "no"}
