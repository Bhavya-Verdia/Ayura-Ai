"""
Ayura AI - Medical Condition Safety Filter
Tier 1: Deterministic rules — safety-critical, no AI hallucination risk.
"""

import json
from pathlib import Path


class ConditionFilter:
    """Filters plans and recommendations based on medical constraints."""

    def __init__(self):
        constraints_path = Path(__file__).parent.parent / "data" / "knowledge_base" / "medical_constraints.json"
        with open(constraints_path, "r") as f:
            data = json.load(f)
        self.constraints = data.get("constraints", {})
        interactions_path = Path(__file__).parent.parent / "data" / "knowledge_base" / "drug_herb_interactions.json"
        with open(interactions_path, "r", encoding="utf-8") as f:
            interaction_data = json.load(f)
        self.drug_herb_interactions = interaction_data.get("interactions", [])
        self.general_interaction_warnings = interaction_data.get("generalWarnings", [])

    def get_constraints(self, medical_history: list[str]) -> dict:
        """
        Aggregate all constraints for a user's medical conditions.

        Returns unified avoid/prefer/modification rules for each plan type.
        """
        aggregated = {
            "gym": {"avoid": set(), "prefer": set(), "modifications": []},
            "yoga": {"avoid": set(), "prefer": set(), "modifications": []},
            "diet": {"avoid": set(), "prefer": set(), "modifications": []},
            "panchakarma": {"avoid": set(), "prefer": set(), "notes": []},
            "remedies": {"avoid": set(), "prefer": set(), "herb_interactions": []},
        }

        for condition in medical_history:
            rules = self.constraints.get(condition, {})
            for plan_type in aggregated:
                if plan_type in rules:
                    plan_rules = rules[plan_type]
                    aggregated[plan_type]["avoid"].update(plan_rules.get("avoid", []))
                    aggregated[plan_type]["prefer"].update(plan_rules.get("prefer", []))
                    for key in ["modifications", "notes", "herb_interactions"]:
                        if key in plan_rules:
                            aggregated[plan_type].setdefault(key, []).extend(plan_rules[key])

        # Convert sets to lists for JSON serialization
        for plan_type in aggregated:
            aggregated[plan_type]["avoid"] = list(aggregated[plan_type]["avoid"])
            aggregated[plan_type]["prefer"] = list(aggregated[plan_type]["prefer"])

        return aggregated


    def check_drug_herb_interactions(self, medications: list[str], herbs: list[str]) -> dict:
        """
        Feature 12: Deterministic Drug-Herb Interaction Checker.
        Checks for known interactions between user medications and proposed herbs.
        """
        interaction_db = {
            "blood_thinners": ["garlic", "ginger", "ginkgo", "ginseng", "turmeric"],
            "diabetes_meds": ["fenugreek", "bitter_melon", "gymnema", "cinnamon"],
            "blood_pressure_meds": ["licorice", "ginseng"],
            "antidepressants": ["st_johns_wort", "ashwagandha", "rhodiola"]
        }
        medication_aliases = {
            "warfarin": ["warfarin", "coumadin"],
            "metformin": ["metformin"],
            "lisinopril": ["lisinopril"],
            "levothyroxine": ["levothyroxine", "thyroxine", "synthroid"],
            "ssri_antidepressants": ["ssri", "prozac", "zoloft", "lexapro", "fluoxetine", "sertraline", "escitalopram"],
            "oral_contraceptives": ["oral contraceptive", "birth control", "contraceptive pill"],
        }

        user_med_categories = []
        for med in medications:
            med_lower = med.lower()
            if any(term in med_lower for term in ["warfarin", "aspirin", "heparin", "blood thinner", "plavix"]):
                user_med_categories.append("blood_thinners")
            if any(term in med_lower for term in ["metformin", "insulin", "glipizide"]):
                user_med_categories.append("diabetes_meds")
            if any(term in med_lower for term in ["lisinopril", "amlodipine", "losartan", "beta blocker"]):
                user_med_categories.append("blood_pressure_meds")
            if any(term in med_lower for term in ["ssri", "prozac", "zoloft", "lexapro", "antidepressant"]):
                user_med_categories.append("antidepressants")

        warnings = []
        normalized_herbs = {self._normalize_token(herb): herb for herb in herbs}
        for med in medications:
            med_norm = med.lower()
            for interaction in self.drug_herb_interactions:
                med_key = interaction.get("medication", "")
                aliases = medication_aliases.get(med_key, [med_key])
                if not any(alias in med_norm for alias in aliases):
                    continue
                for herb_info in interaction.get("herbs", []):
                    herb_key = self._normalize_token(herb_info.get("herb", ""))
                    matched_input = self._matching_herb(normalized_herbs, herb_key)
                    if matched_input and herb_info.get("severity") != "safe":
                        warnings.append({
                            "medication_category": interaction.get("medicationClass", med_key),
                            "herb": matched_input,
                            "severity": herb_info.get("severity", "moderate"),
                            "effect": herb_info.get("effect"),
                            "recommendation": herb_info.get("recommendation"),
                            "alternative": herb_info.get("alternative"),
                        })

        for med_cat in set(user_med_categories):
            risky_herbs = interaction_db.get(med_cat, [])
            for herb in herbs:
                herb_norm = self._normalize_token(herb)
                if herb_norm in risky_herbs:
                    warnings.append({
                        "medication_category": med_cat,
                        "herb": herb,
                        "severity": "high" if med_cat == "blood_thinners" else "medium"
                    })
        unique_warnings = []
        seen = set()
        for warning in warnings:
            key = (
                warning.get("medication_category"),
                self._normalize_token(warning.get("herb", "")),
                warning.get("severity"),
            )
            if key in seen:
                continue
            seen.add(key)
            unique_warnings.append(warning)
        return {
            "status": "warning" if unique_warnings else "safe",
            "warnings": unique_warnings,
            "general_warnings": self.general_interaction_warnings,
        }

    @staticmethod
    def _normalize_token(value: str) -> str:
        normalized = value.lower().replace("-", "_").replace(" ", "_").replace("'", "")
        for suffix in ("_high_dose", "_root", "_supplement", "_supplements"):
            normalized = normalized.replace(suffix, "")
        return normalized

    @staticmethod
    def _matching_herb(input_herbs: dict[str, str], herb_key: str) -> str | None:
        if herb_key in input_herbs:
            return input_herbs[herb_key]
        for input_key, original in input_herbs.items():
            if herb_key in input_key or input_key in herb_key:
                return original
        return None


    def predict_health_risks(self, bmi: float, age: int, gender: str, dosha: str, activity_level: str, medical_history: list[str] = None) -> dict[str, float]:
        """Rule-based health risk prediction."""
        risks = {}
        if bmi > 25:
            risks["obesity"] = 0.6 + (bmi - 25) * 0.05
        if age > 40 and activity_level == "sedentary":
            risks["cardiovascular"] = 0.5
        if dosha == "kapha" and activity_level == "sedentary":
            risks["diabetes"] = 0.4
        if dosha == "vata" and age > 50:
            risks["arthritis"] = 0.45
        if dosha == "pitta" and bmi > 25:
            risks["hypertension"] = 0.5

        return {k: min(1.0, round(v, 3)) for k, v in risks.items()}

    def map_symptoms_to_conditions(self, symptoms: list[str]) -> dict[str, float]:
        """Rule-based symptom mapping."""
        conditions = {}
        for s in symptoms:
            s_lower = s.lower()
            if any(term in s_lower for term in ["pain", "joint", "stiffness"]):
                conditions["arthritis"] = conditions.get("arthritis", 0) + 0.4
            if any(term in s_lower for term in ["acid", "burn", "digestion"]):
                conditions["acid_reflux"] = conditions.get("acid_reflux", 0) + 0.5
            if any(term in s_lower for term in ["tired", "fatigue", "sleep"]):
                conditions["chronic_fatigue"] = conditions.get("chronic_fatigue", 0) + 0.4
        return {k: min(1.0, round(v, 3)) for k, v in conditions.items()}

    def recommend_exercises(self, dosha: str, bmi_category: str, fitness_level: str, medical_history: list[str], goal: str = "") -> list[dict]:
        """Rule-based exercise ranking."""
        exercises = [
            {"name": "Brisk Walking", "vata_score": 80, "pitta_score": 70, "kapha_score": 90, "intensity": 2, "joint_friendly": 1, "impact": 1},
            {"name": "Swimming", "vata_score": 90, "pitta_score": 90, "kapha_score": 70, "intensity": 3, "joint_friendly": 1, "impact": 0},
            {"name": "HIIT", "vata_score": 30, "pitta_score": 50, "kapha_score": 90, "intensity": 5, "joint_friendly": 0, "impact": 3},
            {"name": "Yoga", "vata_score": 90, "pitta_score": 80, "kapha_score": 70, "intensity": 1, "joint_friendly": 1, "impact": 0},
            {"name": "Strength Training", "vata_score": 70, "pitta_score": 80, "kapha_score": 90, "intensity": 4, "joint_friendly": 0, "impact": 2},
        ]

        results = []
        for ex in exercises:
            score = ex[f"{dosha}_score"]
            if bmi_category in ["overweight", "obese"] or "arthritis" in medical_history:
                if ex["impact"] >= 2:
                    score -= 30
                if ex["joint_friendly"]:
                    score += 20
            if fitness_level == "beginner" and ex["intensity"] >= 4:
                score -= 20
            if goal == "weight_loss" and ex["intensity"] >= 3:
                score += 15
            results.append({"name": ex["name"], "score": min(100, max(0, score))})

        return sorted(results, key=lambda x: x["score"], reverse=True)

    def filter_by_allergies(self, user_profile: dict, items: list[dict]) -> list[dict]:
        """
        Remove items whose ingredients or tags overlap with the user's declared allergies.

        Matching is case-insensitive substring-based so that e.g. "nuts" matches "tree nuts"
        and "peanut butter" matches "peanuts".
        """
        allergies = [a.lower() for a in (user_profile.get("allergies") or [])]
        if not allergies:
            return items

        def _is_safe(item: dict) -> bool:
            # Check both ingredient names and tags
            candidates = []
            for ingredient in item.get("ingredients", []):
                candidates.append(ingredient.lower())
            for tag in item.get("tags", []):
                candidates.append(tag.lower())
            for allergen in allergies:
                for candidate in candidates:
                    if allergen in candidate or candidate in allergen:
                        return False
            return True

        return [item for item in items if _is_safe(item)]


# Singleton instance
condition_filter = ConditionFilter()
