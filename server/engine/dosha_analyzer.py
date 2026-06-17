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


# Per-question dosha weights: question_id -> {option_value -> {dosha: weight}}
# Based on classical Ayurvedic Prakriti assessment categories
DOSHA_QUIZ_SCORING: dict[str, dict[int, dict[str, float]]] = {
    "1": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "2": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "3": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "4": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "5": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "6": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "7": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "8": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "9": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "10": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "11": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "12": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "13": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "14": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "15": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "16": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "17": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "18": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "19": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
    "20": {1: {"vata": 2, "pitta": 0, "kapha": 0}, 2: {"vata": 1, "pitta": 1, "kapha": 0}, 3: {"vata": 0, "pitta": 2, "kapha": 0}, 4: {"vata": 0, "pitta": 1, "kapha": 1}, 5: {"vata": 0, "pitta": 0, "kapha": 2}},
}


def score_dosha_quiz(answers: dict) -> dict:
    """
    Calculate dosha scores from quiz answers.

    Args:
        answers: {"1": 3, "2": 5, ...} — question_id -> integer option 1-5

    Returns:
        {"vata": int, "pitta": int, "kapha": int,
         "dominant_dosha": str, "secondary_dosha": str, "dosha_confidence": int}
    """
    vata_raw = 0.0
    pitta_raw = 0.0
    kapha_raw = 0.0

    for q_id, rating in answers.items():
        try:
            r = int(rating)
        except (ValueError, TypeError):
            continue

        weights = DOSHA_QUIZ_SCORING.get(q_id, {})
        if not weights:
            if r <= 2:
                vata_raw += 1
            elif r == 3:
                pitta_raw += 1
            else:
                kapha_raw += 1
        else:
            option_weights = weights.get(r, {})
            vata_raw += option_weights.get("vata", 0)
            pitta_raw += option_weights.get("pitta", 0)
            kapha_raw += option_weights.get("kapha", 0)

    total = vata_raw + pitta_raw + kapha_raw or 1
    dosha_scores = {
        "vata": round(vata_raw / total * 100),
        "pitta": round(pitta_raw / total * 100),
        "kapha": round(kapha_raw / total * 100),
    }

    sorted_doshas = sorted(dosha_scores.items(), key=lambda x: x[1], reverse=True)
    dominant_dosha = sorted_doshas[0][0]
    secondary_dosha = sorted_doshas[1][0]
    top_score = sorted_doshas[0][1]
    second_score = sorted_doshas[1][1]
    dosha_confidence = min(100, int((top_score - second_score) * 2))

    return {
        **dosha_scores,
        "dominant_dosha": dominant_dosha,
        "secondary_dosha": secondary_dosha,
        "dosha_confidence": dosha_confidence,
    }

