from engine.condition_filter import condition_filter

def test_check_drug_herb_interactions():
    medications = ["warfarin", "lisinopril"]
    herbs = ["garlic", "ginseng", "ashwagandha"]

    result = condition_filter.check_drug_herb_interactions(medications, herbs)

    assert result["status"] == "warning"
    assert len(result["warnings"]) > 0

    # Blood thinner (warfarin) and garlic is high severity
    war_garlic_warning = next((w for w in result["warnings"] if w["medication_category"] == "blood_thinners" and w["herb"] == "garlic"), None)
    assert war_garlic_warning is not None
    assert war_garlic_warning["severity"] == "high"

def test_check_drug_herb_interactions_safe():
    medications = ["lisinopril"]
    herbs = ["chamomile"] # Not in interaction db

    result = condition_filter.check_drug_herb_interactions(medications, herbs)
    assert result["status"] == "safe"
    assert len(result["warnings"]) == 0

def test_map_symptoms_to_conditions():
    symptoms = ["severe joint pain", "acid reflux in the morning", "always tired"]
    result = condition_filter.map_symptoms_to_conditions(symptoms)

    assert "arthritis" in result
    assert result["arthritis"] > 0
    assert "acid_reflux" in result
    assert result["acid_reflux"] > 0
    assert "chronic_fatigue" in result
    assert result["chronic_fatigue"] > 0

def test_recommend_exercises_impact():
    # Overweight user with kapha should avoid high impact, prefer swimming/brisk walking
    res = condition_filter.recommend_exercises(
        dosha="kapha",
        bmi_category="obese",
        fitness_level="beginner",
        medical_history=["arthritis"],
        goal="weight_loss"
    )

    top_exercise = res[0]
    # Brisk Walking or Swimming should be at the top, HIIT should be lower due to impact
    assert top_exercise["name"] in ["Brisk Walking", "Swimming"]

    hiit = next((e for e in res if e["name"] == "HIIT"), None)
    assert hiit["score"] < top_exercise["score"]
