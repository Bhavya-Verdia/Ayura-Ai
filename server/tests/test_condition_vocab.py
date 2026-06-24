"""Tests for the normalized condition vocabulary + precise matcher (audit fix #8)."""
from engine.condition_vocab import (
    term_in_condition, normalize_condition, normalize_conditions,
)


class TestTermInCondition:
    def test_whole_word_match(self):
        assert term_in_condition("heart_disease", "heart")
        assert term_in_condition("heart disease", "heart")
        assert term_in_condition("coronary heart disease", "heart disease")

    def test_no_false_substring_match(self):
        # The bug this fixes: 'heart' must NOT match 'heartburn'
        assert not term_in_condition("heartburn", "heart")
        assert not term_in_condition("hypotension", "hypertension")
        assert not term_in_condition("hypertension", "hypotension")

    def test_case_insensitive(self):
        # The PK _contra bug: capitalised condition silently bypassed the set
        assert term_in_condition("Anemia", "anemia")
        assert term_in_condition("ANEMIA", "anemia")

    def test_anemia_within_longer_phrase(self):
        assert term_in_condition("iron deficiency anemia", "anemia")
        assert term_in_condition("iron_deficiency_anemia", "anemia")

    def test_prefix_stem(self):
        assert term_in_condition("epilepsy", "epilep*")
        assert term_in_condition("epileptic", "epilep*")
        assert not term_in_condition("epilepsy", "epileptic")  # bare word, no stem

    def test_empty_inputs(self):
        assert not term_in_condition("", "heart")
        assert not term_in_condition("heart_disease", "")


class TestNormalize:
    def test_aliases_map_to_canonical(self):
        assert normalize_condition("high blood pressure") == "hypertension"
        assert normalize_condition("BP") == "hypertension"
        assert normalize_condition("Type 2 Diabetes") == "diabetes_type2"
        assert normalize_condition("heartburn") == "acid_reflux"
        assert normalize_condition("amavata") == "rheumatoid_arthritis"

    def test_unknown_condition_cleaned(self):
        assert normalize_condition("Some Rare Disease") == "some_rare_disease"

    def test_dedup_preserves_order(self):
        out = normalize_conditions(["high blood pressure", "htn", "diabetes"])
        assert out == ["hypertension", "diabetes_type2"]


class TestSafetyGatesUseVocab:
    def test_medicine_contra_no_false_positive(self):
        from services.remedy_engine import _check_medicine_safety
        # A medicine contraindicated in 'heart_disease' must NOT block a 'heartburn' patient
        med = {"contraindications": ["heart_disease"], "pregnancy_safe": True,
               "drug_interactions": [], "ingredients": []}
        safe, _ = _check_medicine_safety(med, False, [], [], ["heartburn"])
        assert safe is True
        # ...but MUST block a genuine heart_disease patient
        safe2, _ = _check_medicine_safety(med, False, [], [], ["heart_disease"])
        assert safe2 is False

    def test_medicine_contra_matches_alias_phrase(self):
        from services.remedy_engine import _check_medicine_safety
        med = {"contraindications": ["anemia"], "pregnancy_safe": True,
               "drug_interactions": [], "ingredients": []}
        safe, _ = _check_medicine_safety(med, False, [], [], ["iron deficiency anemia"])
        assert safe is False

    def test_disease_signal_resolves_synonyms(self):
        from engine.dosha_analyzer import disease_signal
        # synonyms / classical names resolve to canonical central entries
        for syn in ["high_blood_pressure", "diabetes", "gerd", "vatarakta",
                    "pandu_roga", "ckd", "piles", "ibs_c", "tamaka_shwasa"]:
            assert disease_signal(syn) is not None, f"{syn} should resolve"
        # truly unknown conditions still return None (→ LLM fallback path)
        assert disease_signal("wilsons_disease") is None
        assert disease_signal("") is None

    def test_pk_karma_contra_case_insensitive(self):
        from services.panchakarma_engine import _validate_karma_safety
        pradhana = {"primary": "virechana"}
        # virechana hard-contra includes 'anemia' — capitalised must still flag + substitute
        result, warnings = _validate_karma_safety(pradhana, ["Anemia"])
        assert result["primary"] != "virechana"
        assert any("anemia" in w.lower() for w in warnings)


class TestAharaSafetyAllStructures:
    def test_rule_engine_four_week_plan_scanned(self):
        from services.ahara_safety import apply_ahara_safety
        plan = {"four_week_plan": [{"week": 1, "days": [
            {"day_name": "Monday", "meals": {
                "breakfast": [{"name": "Banana Milkshake"}, {"name": "Paneer Toast"}],
                "lunch": [{"name": "Dal Rice"}],
            }},
        ]}]}
        out = apply_ahara_safety(plan, allergies=["dairy"], intolerances=[])
        # Viruddha (milk+banana) and dairy allergen both detected on the list structure
        assert any("banana" in v["combination"].lower() for v in out["viruddha_ahara_detected"])
        assert out["allergen_safe"] is False
        assert any("milk" in a["matched_terms"] for a in out["safety_alerts"])
        # per-item flag set on the milkshake
        assert plan["four_week_plan"][0]["days"][0]["meals"]["breakfast"][0].get("allergen_warning") is True
