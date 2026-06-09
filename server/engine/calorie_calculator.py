"""
Ayura AI - Calorie & Macro Calculator
Tier 1: Pure computation using Harris-Benedict BMR + activity multipliers.
"""


class CalorieCalculator:

    ACTIVITY_MULTIPLIERS = {
        "sedentary": 1.2,
        "light": 1.375,
        "moderate": 1.55,
        "active": 1.725,
        "very_active": 1.9,
    }

    GOAL_ADJUSTMENTS = {
        "weight_loss": -500,
        "gradual_weight_loss": -250,
        "muscle_gain": +300,
        "general_wellness": 0,
        "flexibility": 0,
        "balance": 0,
        "detox": -200,
    }

    def calculate(
        self,
        gender: str,
        age: int,
        weight_kg: float,
        height_cm: float,
        activity_level: str,
        goal: str,
    ) -> dict:
        bmr = self._bmr(gender, age, weight_kg, height_cm)
        tdee = bmr * self.ACTIVITY_MULTIPLIERS.get(activity_level, 1.55)
        adjustment = self.GOAL_ADJUSTMENTS.get(goal, 0)
        target_calories = max(1200, round(tdee + adjustment))

        macros = self._macros(target_calories, goal)
        return {
            "bmr": round(bmr),
            "tdee": round(tdee),
            "target_calories": target_calories,
            "adjustment": adjustment,
            "macros": macros,
            "meal_distribution": self._meal_distribution(target_calories),
        }

    def _bmr(self, gender: str, age: int, weight_kg: float, height_cm: float) -> float:
        if gender == "female":
            return 447.593 + (9.247 * weight_kg) + (3.098 * height_cm) - (4.330 * age)
        return 88.362 + (13.397 * weight_kg) + (4.799 * height_cm) - (5.677 * age)

    def _macros(self, calories: int, goal: str) -> dict:
        if goal == "muscle_gain":
            protein_pct, carb_pct, fat_pct = 0.30, 0.45, 0.25
        elif goal == "weight_loss":
            protein_pct, carb_pct, fat_pct = 0.35, 0.40, 0.25
        else:
            protein_pct, carb_pct, fat_pct = 0.25, 0.50, 0.25

        return {
            "protein_g": round((calories * protein_pct) / 4),
            "carbs_g": round((calories * carb_pct) / 4),
            "fat_g": round((calories * fat_pct) / 9),
        }

    def _meal_distribution(self, calories: int) -> dict:
        return {
            "breakfast": round(calories * 0.25),
            "lunch": round(calories * 0.35),
            "snack": round(calories * 0.10),
            "dinner": round(calories * 0.30),
        }


calorie_calculator = CalorieCalculator()

