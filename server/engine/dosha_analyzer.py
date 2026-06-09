"""
Ayura AI - Dosha Analyzer Engine
Tier 1: Analyzes dosha scores to detect imbalances and provide Ayurvedic context.
"""


class DoshaAnalyzer:
    """Analyzes dosha scores for imbalance detection and profiling."""

    BALANCED_SCORE = 33.33  # Perfect tridoshic balance

    def analyze(self, dosha_scores: dict) -> dict:
        """
        Analyze dosha scores and return comprehensive Ayurvedic profile.
        
        Args:
            dosha_scores: {"vata": float, "pitta": float, "kapha": float}
        
        Returns:
            Complete dosha analysis with imbalance detection
        """
        vata = dosha_scores.get("vata", 0)
        pitta = dosha_scores.get("pitta", 0)
        kapha = dosha_scores.get("kapha", 0)

        sorted_doshas = sorted(
            [("vata", vata), ("pitta", pitta), ("kapha", kapha)],
            key=lambda x: x[1], reverse=True,
        )

        dominant = sorted_doshas[0]
        secondary = sorted_doshas[1]
        tertiary = sorted_doshas[2]

        # Determine constitution type
        if dominant[1] > 50:
            constitution = dominant[0]
        elif dominant[1] - secondary[1] < 10:
            constitution = f"{dominant[0]}-{secondary[0]}"
        else:
            constitution = dominant[0]

        # Detect imbalance level
        imbalance = self._detect_imbalance(dominant[1])

        return {
            "dominant_dosha": dominant[0],
            "dominant_score": dominant[1],
            "secondary_dosha": secondary[0],
            "secondary_score": secondary[1],
            "tertiary_dosha": tertiary[0],
            "tertiary_score": tertiary[1],
            "constitution_type": constitution,
            "imbalance_level": imbalance,
            "imbalance_description": self._imbalance_description(dominant[0], imbalance),
            "balancing_priority": self._balancing_priority(dominant[0], imbalance),
            "is_dual_type": dominant[1] - secondary[1] < 10,
        }

    def _detect_imbalance(self, dominant_score: float) -> str:
        deviation = dominant_score - self.BALANCED_SCORE
        if deviation < 5:
            return "balanced"
        elif deviation < 15:
            return "mild"
        elif deviation < 25:
            return "moderate"
        else:
            return "severe"

    def _imbalance_description(self, dosha: str, level: str) -> str:
        if level == "balanced":
            return "Your doshas are well balanced. Maintain your current lifestyle."

        descriptions = {
            "vata": {
                "mild": "Slight Vata elevation — you may experience occasional dryness, restlessness, or irregular digestion.",
                "moderate": "Moderate Vata imbalance — anxiety, insomnia, joint dryness, and irregular appetite are likely present.",
                "severe": "Significant Vata aggravation — grounding, warming, and routine-based interventions are essential.",
            },
            "pitta": {
                "mild": "Slight Pitta elevation — watch for occasional acidity, skin sensitivity, or irritability.",
                "moderate": "Moderate Pitta imbalance — acid reflux, inflammation, and competitive/angry tendencies are likely present.",
                "severe": "Significant Pitta aggravation — cooling, calming interventions are essential. Avoid heat and spice.",
            },
            "kapha": {
                "mild": "Slight Kapha elevation — watch for sluggishness, mild congestion, or weight gain tendency.",
                "moderate": "Moderate Kapha imbalance — lethargy, weight gain, congestion, and attachment are likely present.",
                "severe": "Significant Kapha aggravation — stimulating, warming, and lightening interventions are essential.",
            },
        }
        return descriptions.get(dosha, {}).get(level, "")

    def _balancing_priority(self, dosha: str, level: str) -> list:
        priorities = {
            "vata": ["warming_foods", "regular_routine", "oil_massage", "gentle_exercise", "grounding_meditation"],
            "pitta": ["cooling_foods", "moderate_exercise", "avoid_overwork", "cooling_pranayama", "nature_walks"],
            "kapha": ["stimulating_exercise", "light_diet", "variety_in_routine", "early_rising", "warming_spices"],
        }
        return priorities.get(dosha, [])


# Singleton instance
dosha_analyzer = DoshaAnalyzer()

