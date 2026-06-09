"""
Ayura AI - BMI Calculator Engine
Tier 1: Pure computation — no ML needed.
"""


class BMICalculator:
    """Calculates BMI, categorizes it, and provides health context."""

    BMI_CATEGORIES = {
        "severely_underweight": (0, 16.0),
        "underweight": (16.0, 18.5),
        "normal": (18.5, 25.0),
        "overweight": (25.0, 30.0),
        "obese_class1": (30.0, 35.0),
        "obese_class2": (35.0, 40.0),
        "obese_class3": (40.0, 100.0),
    }

    def calculate(self, weight_kg: float, height_cm: float) -> dict:
        """Calculate BMI and return comprehensive health metrics."""
        if height_cm <= 0 or weight_kg <= 0:
            raise ValueError("Height and weight must be positive values.")

        height_m = height_cm / 100
        bmi = weight_kg / (height_m ** 2)
        category = self._categorize(bmi)

        return {
            "bmi": round(bmi, 1),
            "category": category,
            "health_risk": self._risk_level(category),
            "ideal_weight_range": self._ideal_range(height_m),
            "weight_to_lose_or_gain": self._weight_delta(weight_kg, height_m),
        }

    def _categorize(self, bmi: float) -> str:
        for cat, (low, high) in self.BMI_CATEGORIES.items():
            if low <= bmi < high:
                return cat
        return "obese_class3"

    def _risk_level(self, category: str) -> str:
        risks = {
            "severely_underweight": "high",
            "underweight": "moderate",
            "normal": "low",
            "overweight": "moderate",
            "obese_class1": "high",
            "obese_class2": "very_high",
            "obese_class3": "extreme",
        }
        return risks.get(category, "unknown")

    def _ideal_range(self, height_m: float) -> dict:
        return {
            "min_kg": round(18.5 * height_m ** 2, 1),
            "max_kg": round(24.9 * height_m ** 2, 1),
        }

    def _weight_delta(self, weight_kg: float, height_m: float) -> dict:
        ideal = self._ideal_range(height_m)
        if weight_kg < ideal["min_kg"]:
            return {"action": "gain", "amount_kg": round(ideal["min_kg"] - weight_kg, 1)}
        elif weight_kg > ideal["max_kg"]:
            return {"action": "lose", "amount_kg": round(weight_kg - ideal["max_kg"], 1)}
        return {"action": "maintain", "amount_kg": 0}


# Singleton instance
bmi_calculator = BMICalculator()


