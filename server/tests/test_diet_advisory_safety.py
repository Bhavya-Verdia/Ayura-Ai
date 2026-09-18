"""The plan's food-recommending prose is held to the same floor as its meals.

The three deterministic scans read five consumed slots. A diet plan also ships six
free-text surfaces that recommend food by name, and `DietView` renders all of them —
`pathya_apathya.pathya` under the heading "Pathya — Recommended" above the rest.

Measured on an acidity patient: the word `curd` in a meal raised an alert and set
`condition_food_safe = False`; the same word in the Pathya card passed untouched,
beside "Green tea" and "Lemon water on waking" — three foods the library itself
authors as Apathya for that disease.
"""

import pytest

from services.ahara_safety import apply_advisory_safety, apply_condition_food_safety


def _plan(**over):
    p = {
        "pathya_apathya": {
            "pathya": [
                "Curd (Dadhi) — cooling, soothes the stomach lining",
                "Coconut water (Narikela Jala) — Pitta-pacifying",
            ],
            "apathya": ["Chillies", "Curd at night", "Green tea"],
        },
    }
    p.update(over)
    return p


def test_the_pathya_card_is_held_to_the_same_floor_as_the_meals():
    """The reported case, both halves of it: the meal gate and the prose gate now
    reach the same conclusion about the same word."""
    meal_plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {
        "lunch": {"meal_name": "Curd rice", "key_ingredients": ["curd"]}}}}]}
    meals = apply_condition_food_safety(meal_plan, ["acidity"], {}, False)
    assert meals["condition_food_safe"] is False

    prose = apply_advisory_safety(_plan(), ["acidity"], [], [], {}, False)
    assert [w["food"] for w in prose["withheld_recommendations"]] == ["curd"]


def test_a_contradicted_recommendation_is_withheld_not_merely_flagged():
    """It leaves the card. A line reading "Recommended: Curd" beside an alert saying
    the opposite is worse than its absence — say it was withheld, and why."""
    out = apply_advisory_safety(_plan(), ["acidity"], [], [], {}, False)
    assert out["pathya_apathya"]["pathya"] == [
        "Coconut water (Narikela Jala) — Pitta-pacifying"
    ]
    w = out["withheld_recommendations"][0]
    assert w["source"] == "pathya_apathya.pathya"
    assert "Amlapitta" in w["reason"]


def test_the_apathya_list_is_never_touched():
    """It exists to name these foods. Scanning it would withhold the warning."""
    out = apply_advisory_safety(_plan(), ["acidity"], [], [], {}, False)
    assert out["pathya_apathya"]["apathya"] == ["Chillies", "Curd at night", "Green tea"]


def test_a_declared_allergy_is_not_recommended_in_prose_either():
    """`flag_allergens` reads meals. A dairy-allergic patient could still be told to
    take warm milk at bedtime by the card above them."""
    plan = {"pathya_apathya": {"pathya": ["Warm milk with nutmeg at bedtime"]}}
    out = apply_advisory_safety(plan, [], ["dairy"], [], {}, False)
    assert out["pathya_apathya"]["pathya"] == []
    assert "dairy" in out["withheld_recommendations"][0]["condition"]


@pytest.mark.parametrize("text,flagged", [
    # Recommends it — the defect.
    ("Sip warm lemon water through the day.", True),
    ("Avoid fried food. Take curd with lunch.", True),
    ("Take curd with lunch, avoid pickles.", True),
    ("Curd is excellent for you, avoid pickles.", True),
    ("No curd. Green tea is excellent for you.", True),
    # Tells them to avoid it — correct advice for exactly this patient, and flagging
    # it is how a safety badge gets trained out of a reader.
    ("Do not take curd at night.", False),
    ("Replace curd with buttermilk.", False),
    ("Curd is best avoided in Amlapitta.", False),
    ("Fresh curd is best avoided in Amlapitta.", False),
    ("Avoid curd, green tea and lemon water.", False),
    ("Limit curd to twice a week.", False),
    ("Warm milk is fine, but curd should be skipped.", False),
])
def test_free_prose_is_negation_aware(text, flagged):
    out = apply_advisory_safety({"condition_coaching": text}, ["acidity"], [], [], {}, False)
    assert bool(out["advisory_prose_alerts"]) is flagged, text


def test_the_marker_is_found_wherever_it_sits_in_the_clause():
    """The window used to be the text *before* the mention, so the answer depended on
    where in the clause the food word fell: "curd is best avoided" cleared (empty
    prefix, whole clause scanned) and "fresh curd is best avoided" flagged."""
    a = apply_advisory_safety({"ahar_vidhi": "Curd is best avoided."}, ["acidity"], [], [], {}, False)
    b = apply_advisory_safety({"ahar_vidhi": "Fresh curd is best avoided."}, ["acidity"], [], [], {}, False)
    assert not a["advisory_prose_alerts"] and not b["advisory_prose_alerts"]


def test_every_rendered_prose_field_is_scanned():
    """A field the UI renders and the scan does not read is the whole defect."""
    from services.ahara_safety import _PROSE_FIELDS
    for field in _PROSE_FIELDS:
        out = apply_advisory_safety({field: "Start the day with green tea."},
                                    ["acidity"], [], [], {}, False)
        assert out["advisory_prose_alerts"], f"{field} is not scanned"


def test_a_clean_plan_reports_clean():
    out = apply_advisory_safety(
        {"pathya_apathya": {"pathya": ["Coconut water (Narikela Jala)"]},
         "condition_coaching": "Eat warm, freshly cooked food at regular hours."},
        ["acidity"], [], [], {}, False)
    assert out["withheld_recommendations"] == []
    assert out["advisory_prose_alerts"] == []
    assert out["advisory_safety_checked"] is True


def test_a_patient_with_no_conditions_loses_nothing():
    out = apply_advisory_safety(_plan(), [], [], [], {}, False)
    assert len(out["pathya_apathya"]["pathya"]) == 2
    assert out["withheld_recommendations"] == []


def test_the_layer_never_breaks_generation():
    """Same contract as the scans it sits beside."""
    out = apply_advisory_safety({"pathya_apathya": {"pathya": "not a list"}},
                                ["acidity"], [], [], {}, False)
    assert out["advisory_safety_checked"] is True
    out2 = apply_advisory_safety({"condition_coaching": None}, ["acidity"], [], [], {}, False)
    assert out2["advisory_safety_checked"] is True


def test_both_generation_paths_apply_it():
    """The holistic worker and the per-feature route once ran different subsets of the
    safety model; `build_diet_plan` exists so that cannot happen. A new layer that
    only one path calls reopens it."""
    import inspect
    from services import diet_llm_generator as g

    llm_src = inspect.getsource(g.generate_diet_plan_llm)
    fallback_src = inspect.getsource(g.build_diet_plan)
    assert "apply_advisory_safety" in llm_src
    assert "apply_advisory_safety" in fallback_src
