"""
Ayura AI - Dosha Analyzer Engine
Tier 1: Analyzes dosha scores to detect imbalances and provide Ayurvedic context.
"""
from datetime import datetime


class DoshaAnalyzer:
    """Analyzes dosha scores for imbalance detection and profiling."""

    BALANCED_SCORE = 33.33

    def analyze(self, dosha_scores: dict) -> dict:
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

        if dominant[1] > 50:
            constitution = dominant[0]
        elif dominant[1] - secondary[1] < 10:
            constitution = f"{dominant[0]}-{secondary[0]}"
        else:
            constitution = dominant[0]

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


# ── Trait weights — based on classical Ayurvedic diagnostic hierarchy ──────────
# Body frame and digestion are primary indicators (most reliable, least affected by
# external factors). Hair texture is the least reliable due to styling and products.
_TRAIT_WEIGHTS: dict[str, float] = {
    "body_frame":       2.0,   # primary structural indicator
    "digestion":        2.0,   # agni — most diagnostic of all vikriti indicators
    "temperature":      1.5,   # strong constitutional signal
    "sleep":            1.5,   # highly consistent pattern
    "energy":           1.0,
    "skin":             1.0,
    "hair":             0.75,  # affected by products/diet — least reliable
    # Mental / behavioral traits (Manas Prakriti) — often more reliable than physical appearance
    "stress_response":  1.8,
    "memory":           1.8,
    "decision_making":  1.6,
    "emotional_nature": 1.6,
    "speech":           1.2,
    # Behavioral micro-patterns — high diagnostic value when present
    "eating_habits":    1.4,
    "walk_pace":        1.0,
    "anger_style":      1.5,
    # Ashtavidha Pareeksha — classical 8-fold examination indicators
    "agni_type":        2.0,   # Agni assessment — core Ayurvedic diagnostic (Agni Pareeksha)
    "stool_pattern":    1.5,   # Mala Pareeksha — strong digestive channel signal
    "eye_quality":      1.2,   # Drik Pareeksha — Ashtavidha examination
    "voice_quality":    1.0,   # Shabda Pareeksha — Ashtavidha examination
    "nadi_rhythm":      1.8,   # Nadi Pareeksha — foremost Ashtavidha examination (self-report approximation)
    "mutra_pattern":    1.1,   # Mutra Pareeksha — urine characteristics (Ashtavidha)
}


# ── Symptom → fractional dosha weights ────────────────────────────────────────
# Each symptom distributes across doshas in proportion to clinical prevalence.
# Totals per symptom do not need to equal 1 — they're used for proportional scoring.
_SYMPTOM_DOSHA_WEIGHTS: dict[str, dict[str, float]] = {
    "anxiety_worry":           {"vata": 0.85, "pitta": 0.15, "kapha": 0.00},
    "dry_skin_constipation":   {"vata": 0.90, "pitta": 0.05, "kapha": 0.05},
    "trouble_sleeping":        {"vata": 0.70, "pitta": 0.25, "kapha": 0.05},
    "bloating_gas":            {"vata": 0.65, "pitta": 0.10, "kapha": 0.25},
    "joint_stiffness":         {"vata": 0.80, "pitta": 0.10, "kapha": 0.10},
    "brain_fog":               {"vata": 0.35, "pitta": 0.15, "kapha": 0.50},
    # Ama (metabolic toxin) indicators — classical Ayurvedic pathology
    "coated_tongue_ama":       {"vata": 0.20, "pitta": 0.20, "kapha": 0.60},
    "morning_heaviness":       {"vata": 0.15, "pitta": 0.10, "kapha": 0.75},
    "heartburn_acidity":       {"vata": 0.05, "pitta": 0.90, "kapha": 0.05},
    "skin_rashes":             {"vata": 0.05, "pitta": 0.85, "kapha": 0.10},
    "irritability":            {"vata": 0.10, "pitta": 0.85, "kapha": 0.05},
    "weight_gain":             {"vata": 0.00, "pitta": 0.10, "kapha": 0.90},
    "low_energy":              {"vata": 0.20, "pitta": 0.05, "kapha": 0.75},
    "congestion":              {"vata": 0.05, "pitta": 0.05, "kapha": 0.90},
}

# Kept for backward compatibility with older route code
_SYMPTOM_DOSHA_MAP: dict[str, str] = {
    s: max(weights, key=weights.get)
    for s, weights in _SYMPTOM_DOSHA_WEIGHTS.items()
}


_TRAIT_DESCRIPTIONS = {
    "body_frame": {
        "vata": "Naturally slim and light, hard to gain weight",
        "pitta": "Medium athletic build, gains and loses weight fairly easily",
        "kapha": "Larger solid frame, gains weight easily",
    },
    "skin": {
        "vata": "Dry, rough, or cracking — especially hands, lips, heels",
        "pitta": "Warm, reactive, prone to breakouts, redness, or sensitivity",
        "kapha": "Smooth, cool, moist, and soft",
    },
    "digestion": {
        "vata": "Irregular — sometimes fast, sometimes slow, often bloated or gassy",
        "pitta": "Strong and fast — gets intensely hungry, uncomfortable when meals are delayed",
        "kapha": "Slow and steady — can skip meals easily, rarely feels intense hunger",
    },
    "sleep": {
        "vata": "Light sleeper — wakes easily, sometimes can't fall asleep, anxious or vivid dreams",
        "pitta": "Moderate — falls asleep easily, wakes sometimes, feels rested in 6-7 hours",
        "kapha": "Deep, heavy sleeper — hard to wake, needs 8+ hours, often feels groggy",
    },
    "temperature": {
        "vata": "Dislikes cold intensely, always seeking warmth, hands and feet often cold",
        "pitta": "Dislikes heat, prefers cool or air-conditioned spaces",
        "kapha": "Comfortable in most temperatures, slight preference for warmth",
    },
    "hair": {
        "vata": "Fine, dry, frizzy, or brittle — prone to split ends and dandruff",
        "pitta": "Fine, silky, gets oily quickly — prone to premature graying or thinning",
        "kapha": "Thick, wavy, naturally oily and strong — grows well",
    },
    "energy": {
        "vata": "Energy in intense bursts that drop quickly — poor stamina",
        "pitta": "Good consistent energy, especially mid-day — driven and purposeful",
        "kapha": "Slow to start but excellent endurance once going",
    },
    "stress_response": {
        "vata": "Tends toward anxiety, worry, freeze, or scatter under pressure",
        "pitta": "Gets sharp, irritable, or confrontational — pushes through aggressively",
        "kapha": "Withdraws, goes quiet, feels heavy or stuck — slow to process",
    },
    "memory": {
        "vata": "Quick to learn and connect ideas, but details fade quickly",
        "pitta": "Sharp and accurate — learns systematically and retains precisely",
        "kapha": "Slow to absorb but once learned, remembers permanently",
    },
    "decision_making": {
        "vata": "Changes mind often — many options, difficulty committing",
        "pitta": "Decides fast and commits firmly — rarely second-guesses",
        "kapha": "Deliberates very carefully for a long time — extremely hard to reverse",
    },
    "speech": {
        "vata": "Talks fast, jumps topics, enthusiastic and expressive",
        "pitta": "Precise, direct, articulate — gets to the point; can seem blunt",
        "kapha": "Slow, calm, melodious — measured and considerate",
    },
    "emotional_nature": {
        "vata": "Enthusiastic and creative but variable — quick to excite, quick to worry",
        "pitta": "Intense and passionate — feels things deeply, prone to frustration",
        "kapha": "Calm and nurturing — stable and steady, but prone to attachment",
    },
    "eating_habits": {
        "vata": "Eats quickly, irregularly, often standing or distracted — forgets to eat or overeats",
        "pitta": "Eats at precise mealtimes, focused on the meal, finishes efficiently — strong appetite",
        "kapha": "Eats slowly, enjoys food socially, lingers at meals — strong appetite but slow metabolism",
    },
    "walk_pace": {
        "vata": "Fast, light, variable — quick steps, slightly scattered, changes pace often",
        "pitta": "Purposeful, medium pace, heel-to-toe — walks with intention and direction",
        "kapha": "Slow, steady, grounded — stable stride, unhurried, difficult to rush",
    },
    "anger_style": {
        "vata": "Gets agitated and anxious quickly, but the feeling passes fast — often forgets what upset them",
        "pitta": "Gets sharply angry, may say cutting things — holds it briefly but expresses it clearly",
        "kapha": "Slow to anger, but once there, holds the grudge for a very long time — rarely forgets",
    },
    "agni_type": {
        "vata": "Vishama Agni — irregular digestive fire; variable appetite, alternating digestion, intermittent bloating",
        "pitta": "Tikshna Agni — sharp/intense digestive fire; strong appetite, fast digestion, acidity or loose stools if excessive",
        "kapha": "Manda Agni — slow digestive fire; low appetite, heavy feeling after meals, slow metabolism",
        "sama": "Sama Agni — balanced digestive fire; consistent appetite, good absorption, regular elimination",
    },
    "stool_pattern": {
        "vata": "Irregular, sometimes constipated, dry, hard pellets, or with gas and bloating — variable frequency",
        "pitta": "Regular, soft, formed, sometimes loose, may have urgency or slight burning — once or twice daily",
        "kapha": "Regular but slow, heavy, formed, well-structured — once daily, takes effort sometimes",
    },
    "eye_quality": {
        "vata": "Small, dry, irregular blinking, may twitch; restless gaze; dull or muddy appearance",
        "pitta": "Sharp, penetrating, moderate size, slightly reddish; bright and intense; prone to sensitivity to light",
        "kapha": "Large, moist, pleasant, steady gaze; clear and lustrous; whites are white, rarely reddened",
    },
    "voice_quality": {
        "vata": "Thin, low volume, sometimes cracking or hoarse; speaks quickly; runs out of breath mid-sentence",
        "pitta": "Clear, sharp, moderate volume; articulate and commands attention; can be cutting when emotional",
        "kapha": "Deep, resonant, melodious; slow and steady; pleasant and soothing to listen to",
    },
    "nadi_rhythm": {
        "vata": "Irregular, thin, thready, fast — moves like a snake (Sarpa gati); hard to feel, disappears under pressure",
        "pitta": "Strong, bounding, sharp, moderate speed — moves like a frog (Manduka gati); feels prominent and forceful",
        "kapha": "Slow, broad, wave-like, steady — moves like a swan (Hamsa gati); feels deep and stable under light pressure",
    },
    "mutra_pattern": {
        "vata": "Scanty, variable frequency, sometimes dark or cloudy; occasional burning; gets dehydrated easily",
        "pitta": "Yellow or amber-coloured, concentrated, strong odour; may have burning sensation; frequent in hot weather",
        "kapha": "Pale, large volume, turbid or slightly cloudy; infrequent but heavy; foamy sometimes",
    },
}

_SYMPTOM_DESCRIPTIONS = {
    "anxiety_worry": "Anxiety, worry, or racing thoughts",
    "dry_skin_constipation": "Dry skin, constipation, or joint stiffness",
    "trouble_sleeping": "Trouble sleeping or feeling scattered/ungrounded",
    "bloating_gas": "Bloating, gas, or irregular digestion",
    "heartburn_acidity": "Heartburn, acidity, or stomach inflammation",
    "skin_rashes": "Skin rashes, acne, or feeling overheated",
    "irritability": "Irritability, frustration, or impatience",
    "weight_gain": "Weight gain or feeling heavy/sluggish",
    "low_energy": "Low energy, motivation, or mild depression",
    "congestion": "Congestion, mucus, or slow metabolism",
    "joint_stiffness": "Joint stiffness, dryness, or body aches",
    "brain_fog": "Brain fog or difficulty concentrating",
    "coated_tongue_ama": "Thick white/yellow coating on tongue in morning (Ama on Jihva)",
    "morning_heaviness": "Body feels heavy, dull, or unrefreshed despite adequate sleep (Ama in channels)",
    "feeling_balanced": "Feeling generally balanced — no major complaints",
}


def _confidence_score(confidence: str) -> int:
    return {"high": 85, "medium": 60, "low": 35}.get(confidence, 35)


def _confidence_from_checkins(base_confidence: int, checkin_count: int) -> int:
    """Gradually raise confidence as weekly check-ins accumulate.

    Caps at 92 to reflect that no self-report model reaches certainty.
    Each check-in adds a diminishing increment — first few matter most.
    """
    if checkin_count <= 0:
        return base_confidence
    bonus = min(30, int(4 * (checkin_count ** 0.65)))
    return min(92, base_confidence + bonus)


def _seasonal_dosha() -> tuple[str, float]:
    """Returns (aggravated_dosha, boost_fraction) based on Ayurvedic 6-Ritu calendar.

    The 6 Ritu (seasons) and their classical dosha-aggravation cycle:
    - Shishira (Jan-Feb): Vata Prakopa — cold dry winds aggravate Vata
    - Vasanta (Mar-Apr): Kapha Prakopa — warmth liquefies accumulated Kapha
    - Grishma (May-Jun): Pitta Sanchaya — heat begins accumulating Pitta
    - Varsha (Jul-Aug): Vata Prakopa peak — monsoon/cold food weakens Agni
    - Sharad (Sep-Oct): Pitta Prakopa — accumulated Pitta peaks in autumn heat
    - Hemanta (Nov-Dec): Kapha Sanchaya — cold starts accumulating Kapha

    Source: Charaka Samhita, Sutrasthana 6 (Tasyashitiya Adhyaya)
    """
    month = datetime.now().month
    if month in (1, 2):     # Shishira — Vata Prakopa
        return "vata", 0.09
    elif month in (3, 4):   # Vasanta — Kapha Prakopa (peak)
        return "kapha", 0.10
    elif month in (5, 6):   # Grishma — Pitta Sanchaya
        return "pitta", 0.07
    elif month in (7, 8):   # Varsha — Vata Prakopa peak
        return "vata", 0.10
    elif month in (9, 10):  # Sharad — Pitta Prakopa (peak)
        return "pitta", 0.10
    else:                   # Hemanta (Nov-Dec) — Kapha Sanchaya
        return "kapha", 0.07


def _apply_seasonal_correction(vikriti: dict) -> dict:
    """Boost the seasonal dosha by up to 8%, then renormalize to sum 100."""
    dosha, boost = _seasonal_dosha()
    adjusted = dict(vikriti)
    adjusted[dosha] = round(adjusted.get(dosha, 33) * (1 + boost))
    total = sum(adjusted.values()) or 1
    return {d: round(v / total * 100) for d, v in adjusted.items()}


def _compute_ama_score(symptoms: list[str], digestion_score: int | None = None) -> str:
    """Estimate Ama (metabolic toxin) level from symptoms and digestion quality.

    Ama forms when Agni (digestive fire) is impaired. Classical indicators:
    coated tongue, morning heaviness, body odor, lethargy, and joint stiffness.
    Returns 'low', 'moderate', or 'high'.
    """
    score = 0
    ama_symptoms = {
        "coated_tongue_ama": 3,
        "morning_heaviness":  3,
        "brain_fog":          2,
        "bloating_gas":       2,
        "joint_stiffness":    1,
        "low_energy":         1,
        "weight_gain":        1,
        "congestion":         1,
    }
    for sym in symptoms:
        score += ama_symptoms.get(sym, 0)
    if digestion_score is not None and digestion_score <= 2:
        score += 2
    if score >= 6:
        return "high"
    elif score >= 3:
        return "moderate"
    return "low"


def _classify_prakriti_7_types(prakriti: dict) -> dict:
    """Classify Prakriti into one of the 7 classical types per Charaka Samhita Vimana Sthana 8.

    The 7 types (Sapta Prakriti):
    1. Vata        — single dosha dominant (gap ≥15 from second)
    2. Pitta       — single dosha dominant
    3. Kapha       — single dosha dominant
    4. Vata-Pitta  — Vata and Pitta both elevated (gap<15)
    5. Pitta-Kapha — Pitta and Kapha both elevated
    6. Vata-Kapha  — Vata and Kapha both elevated
    7. Sama Tridosha — all three roughly equal (all within 10 of each other)
    """
    sorted_d = sorted(prakriti.items(), key=lambda x: x[1], reverse=True)
    d1, s1 = sorted_d[0]
    d2, s2 = sorted_d[1]
    _d3, s3 = sorted_d[2]

    CLASSICAL_NAMES = {
        "vata": "Vata Prakriti",
        "pitta": "Pitta Prakriti",
        "kapha": "Kapha Prakriti",
        "vata_pitta": "Vata-Pitta Prakriti (Dvidoshaja)",
        "pitta_vata": "Pitta-Vata Prakriti (Dvidoshaja)",
        "pitta_kapha": "Pitta-Kapha Prakriti (Dvidoshaja)",
        "kapha_pitta": "Kapha-Pitta Prakriti (Dvidoshaja)",
        "vata_kapha": "Vata-Kapha Prakriti (Dvidoshaja)",
        "kapha_vata": "Kapha-Vata Prakriti (Dvidoshaja)",
        "tridoshic": "Sama Tridosha Prakriti (Sannipata)",
    }

    if s1 - s3 <= 10:
        type_key = "tridoshic"
    elif s1 - s2 >= 15:
        type_key = d1
    else:
        type_key = f"{d1}_{d2}"

    return {
        "prakriti_classical_type": type_key,
        "prakriti_classical_name": CLASSICAL_NAMES.get(type_key, f"{d1.title()} Prakriti"),
    }


# Classical dosha-guna mappings (Charaka Samhita, Sutrasthana 1.59-61)
_DOSHA_PRIMARY_GUNAS: dict[str, list[str]] = {
    "vata":  ["Ruksha (dry)", "Laghu (light)", "Sheeta (cold)", "Khara (rough)", "Chala (mobile)"],
    "pitta": ["Ushna (hot)", "Tikshna (sharp)", "Sara (flowing)", "Laghu (light)", "Snigdha (slightly oily)"],
    "kapha": ["Guru (heavy)", "Manda (slow)", "Snigdha (oily)", "Sthira (stable)", "Sheeta (cold)"],
}


def _get_primary_gunas(prakriti_dominant: str, prakriti_secondary: str | None = None) -> list[str]:
    """Return the primary gunas characterising this Prakriti type."""
    gunas = list(_DOSHA_PRIMARY_GUNAS.get(prakriti_dominant, []))
    if prakriti_secondary and prakriti_secondary != prakriti_dominant:
        for g in _DOSHA_PRIMARY_GUNAS.get(prakriti_secondary, [])[:2]:
            if g not in gunas:
                gunas.append(g)
    return gunas[:5]


# ── Disease → Dosha signal map (classical Ayurvedic etiology) ────────────────
# Source: Charaka Samhita Nidana Sthana, Ashtanga Hridayam Nidana Sthana.
# Each entry: p=primary dosha, w=weight 1-3, s2=secondary dosha, w2=secondary weight,
#             s=affected Srotas, c=classical Ayurvedic name
_DISEASE_DOSHA_SIGNAL: dict[str, dict] = {
    # ── Musculoskeletal ──────────────────────────────────────────────────────
    "ankylosing_spondylitis":  {"p": "vata", "w": 3.0, "s": "Asthivaha Srotas",    "c": "Asthi-Majja Gata Vata",             "d": "asthi_majja"},
    "osteoarthritis":          {"p": "vata", "w": 2.5, "s": "Asthivaha Srotas",    "c": "Sandhivata",                         "d": "asthi"},
    "rheumatoid_arthritis":    {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Asthivaha Srotas",    "c": "Amavata (Vata + Kapha)",            "d": "mamsa_rakta"},
    "arthritis":               {"p": "vata", "w": 2.0, "s": "Asthivaha Srotas",    "c": "Sandhivata / Amavata",               "d": "asthi"},
    "gout":                    {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Raktavaha Srotas",    "c": "Vatarakta (Pitta + Vata)",          "d": "asthi"},
    "fibromyalgia":            {"p": "vata", "w": 2.5, "s": "Mamsavaha Srotas",    "c": "Mamsagata Vata",                     "d": "mamsa"},
    "sciatica":                {"p": "vata", "w": 2.5, "s": "Majjavaha Srotas",    "c": "Gridhrasi (Vata)",                   "d": "asthi_majja"},
    "osteoporosis":            {"p": "vata", "w": 2.5, "s": "Asthivaha Srotas",    "c": "Asthi Kshaya (Vata)",                "d": "asthi"},
    "cervical_spondylosis":    {"p": "vata", "w": 2.0, "s": "Asthivaha Srotas",    "c": "Griva Shoola (Vata)",                "d": "asthi_majja"},
    "lumbar_spondylosis":      {"p": "vata", "w": 2.0, "s": "Asthivaha Srotas",    "c": "Kati Shoola (Vata)",                 "d": "asthi_majja"},
    "frozen_shoulder":         {"p": "vata", "w": 1.8, "s": "Mamsavaha Srotas",    "c": "Avabahuka (Vata)",                   "d": "mamsa"},
    "carpal_tunnel":           {"p": "vata", "w": 1.5, "s": "Mamsavaha Srotas",    "c": "Vataja Shoola",                      "d": "mamsa"},
    # ── Neurological ─────────────────────────────────────────────────────────
    "parkinson":               {"p": "vata", "w": 3.0, "s": "Majjavaha Srotas",    "c": "Kampavata",                          "d": "majja"},
    "multiple_sclerosis":      {"p": "vata", "w": 2.5, "s2": "pitta", "w2": 1.5,  "s": "Majjavaha Srotas",    "c": "Avrita Vata (Vata + Pitta)",        "d": "majja"},
    "epilepsy":                {"p": "vata", "w": 2.5, "s": "Manovaha Srotas",     "c": "Apasmara (Vata)",                    "d": "majja"},
    "migraine":                {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Manovaha Srotas",     "c": "Ardha Avabhedaka (Pitta)",          "d": "majja"},
    "peripheral_neuropathy":   {"p": "vata", "w": 2.0, "s": "Majjavaha Srotas",    "c": "Vataja Shoola (Majja)",              "d": "majja"},
    "tinnitus":                {"p": "vata", "w": 2.0, "s": "Manovaha Srotas",     "c": "Karnanada (Vata)",                   "d": "majja"},
    "vertigo":                 {"p": "vata", "w": 2.0, "s": "Manovaha Srotas",     "c": "Bhrama (Vata)",                      "d": "majja"},
    "chronic_fatigue_syndrome":{"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,  "s": "Rasavaha Srotas",     "c": "Bala Kshaya (Vata + Kapha)",        "d": "rasa"},
    "bells_palsy":             {"p": "vata", "w": 2.5, "s": "Majjavaha Srotas",    "c": "Ardita (Vata)",                      "d": "majja"},
    "restless_leg_syndrome":   {"p": "vata", "w": 2.0, "s": "Mamsavaha Srotas",    "c": "Vataja Shoola",                      "d": "mamsa"},
    # ── Psychiatric / Mental Health ───────────────────────────────────────────
    "anxiety":                 {"p": "vata", "w": 2.5, "s": "Manovaha Srotas",     "c": "Vataja Chittodvega",                 "d": "majja"},
    "depression":              {"p": "kapha","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Manovaha Srotas",     "c": "Kaphaja / Vataja Vishada",          "d": "majja"},
    "bipolar":                 {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Manovaha Srotas",     "c": "Vata-Pittaja Unmada",               "d": "majja"},
    "ocd":                     {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.0,   "s": "Manovaha Srotas",     "c": "Vataja Unmada",                     "d": "majja"},
    "ptsd":                    {"p": "vata", "w": 2.5, "s": "Manovaha Srotas",     "c": "Vataja Bhaya / Shoka",               "d": "majja"},
    "adhd":                    {"p": "vata", "w": 2.5, "s": "Manovaha Srotas",     "c": "Vataja Chanchalta",                  "d": "majja"},
    "insomnia":                {"p": "vata", "w": 2.0, "s": "Manovaha Srotas",     "c": "Anidra (Vata)",                      "d": "majja"},
    # ── Cardiovascular ────────────────────────────────────────────────────────
    "hypertension":            {"p": "pitta","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Raktavaha Srotas",    "c": "Raktagata Vata (Pitta + Vata)",     "d": "rasa_rakta"},
    "heart_disease":           {"p": "kapha","w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Raktavaha Srotas",    "c": "Kaphaja Hridroga",                  "d": "rasa_rakta"},
    "atrial_fibrillation":     {"p": "vata", "w": 2.5, "s": "Raktavaha Srotas",    "c": "Vataja Hridroga",                    "d": "rasa_rakta"},
    "heart_failure":           {"p": "kapha","w": 2.5, "s": "Raktavaha Srotas",    "c": "Kaphaja Hridroga",                   "d": "rasa_rakta"},
    "varicose_veins":          {"p": "vata", "w": 1.5, "s2": "pitta", "w2": 1.0,   "s": "Raktavaha Srotas",    "c": "Siragata Vata",                     "d": "rakta"},
    "anemia":                  {"p": "pitta","w": 2.0, "s": "Raktavaha Srotas",    "c": "Pandu (Pitta / Rakta)",              "d": "rakta"},
    "low_blood_pressure":      {"p": "vata", "w": 2.0, "s": "Raktavaha Srotas",    "c": "Raktakshaya (Vata)",                 "d": "rasa"},
    # ── Respiratory ───────────────────────────────────────────────────────────
    "asthma":                  {"p": "kapha","w": 2.5, "s2": "vata", "w2": 1.5,    "s": "Pranavaha Srotas",    "c": "Tamaka Shwasa (Kapha + Vata)",      "d": "rasa"},
    "copd":                    {"p": "vata", "w": 2.5, "s2": "kapha", "w2": 1.5,   "s": "Pranavaha Srotas",    "c": "Vataja Shwasa",                     "d": "rasa"},
    "chronic_bronchitis":      {"p": "kapha","w": 2.5, "s": "Pranavaha Srotas",    "c": "Kaphaja Kasa",                       "d": "rasa"},
    "allergic_rhinitis":       {"p": "kapha","w": 2.0, "s2": "vata", "w2": 1.0,    "s": "Pranavaha Srotas",    "c": "Kaphaja Pratishyaya",               "d": "rasa"},
    "sinusitis":               {"p": "kapha","w": 2.0, "s": "Pranavaha Srotas",    "c": "Dushta Pratishyaya (Kapha)",         "d": "rasa"},
    "sleep_apnea":             {"p": "kapha","w": 2.5, "s": "Pranavaha Srotas",    "c": "Kaphavrita Pranavata",               "d": "meda"},
    "pulmonary_fibrosis":      {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Pranavaha Srotas",    "c": "Vataja-Kaphaja Shwasa",             "d": "rasa"},
    # ── Gastrointestinal ─────────────────────────────────────────────────────
    "acid_reflux":             {"p": "pitta","w": 2.5, "s": "Annavaha Srotas",     "c": "Amlapitta (Pitta)",                  "d": "rasa"},
    "peptic_ulcer":            {"p": "pitta","w": 2.5, "s": "Annavaha Srotas",     "c": "Pittaja Shotha (Annavaha)",          "d": "rasa"},
    "ibd_crohns":              {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Purishavaha Srotas",  "c": "Pittaja Atisara",                   "d": "rasa_mamsa"},
    "ulcerative_colitis":      {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Purishavaha Srotas",  "c": "Raktaja Atisara (Pitta)",           "d": "rakta"},
    "ibs":                     {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.0,   "s": "Purishavaha Srotas",  "c": "Grahani (Vataja)",                  "d": "rasa"},
    "liver_disease":           {"p": "pitta","w": 2.5, "s": "Raktavaha Srotas",    "c": "Yakrit Roga (Pitta)",                "d": "rakta"},
    "fatty_liver":             {"p": "kapha","w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Medovaha Srotas",     "c": "Medoroga with Yakrit (Kapha + Pitta)","d": "meda"},
    "gallstones":              {"p": "pitta","w": 2.5, "s2": "kapha", "w2": 1.0,   "s": "Purishavaha Srotas",  "c": "Pittashma (Pitta + Kapha)",         "d": "meda"},
    "hemorrhoids":             {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Purishavaha Srotas",  "c": "Arsha (Vataja + Pittaja)",          "d": "rakta"},
    "constipation_chronic":    {"p": "vata", "w": 2.5, "s": "Purishavaha Srotas",  "c": "Vibandha (Vata)",                    "d": "rasa"},
    "celiac":                  {"p": "vata", "w": 1.5, "s2": "pitta", "w2": 1.5,   "s": "Annavaha Srotas",     "c": "Grahani (Vata-Pitta)",              "d": "rasa"},
    "pancreatitis":            {"p": "pitta","w": 2.5, "s": "Annavaha Srotas",     "c": "Pittaja Gulma",                      "d": "rasa"},
    # ── Endocrine / Metabolic ─────────────────────────────────────────────────
    "diabetes_type1":          {"p": "pitta","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Medovaha Srotas",     "c": "Sahaja Prameha (Pitta + Vata)",     "d": "rasa"},
    "diabetes_type2":          {"p": "kapha","w": 2.5, "s2": "pitta", "w2": 1.0,   "s": "Medovaha Srotas",     "c": "Kaphaja Prameha",                   "d": "meda"},
    "hypothyroidism":          {"p": "kapha","w": 2.5, "s": "Medovaha Srotas",     "c": "Kaphaja Galaganda",                  "d": "rasa"},
    "hyperthyroidism":         {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Raktavaha Srotas",    "c": "Pittaja Galaganda",                 "d": "rasa"},
    "pcos":                    {"p": "kapha","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Artavavaha Srotas",   "c": "Kaphaja Artava Dushti + Vataja",    "d": "shukra"},
    "obesity":                 {"p": "kapha","w": 2.5, "s": "Medovaha Srotas",     "c": "Sthoulya (Kapha)",                   "d": "meda"},
    "high_cholesterol":        {"p": "kapha","w": 2.5, "s": "Medovaha Srotas",     "c": "Medoroga (Kapha)",                   "d": "meda"},
    "metabolic_syndrome":      {"p": "kapha","w": 2.5, "s2": "pitta", "w2": 1.0,   "s": "Medovaha Srotas",     "c": "Sthoulya + Prameha (Kapha)",        "d": "meda"},
    "underweight":             {"p": "vata", "w": 2.0, "s": "Rasavaha Srotas",     "c": "Karshya (Vata)",                     "d": "rasa"},
    "adrenal_fatigue":         {"p": "vata", "w": 2.0, "s": "Rasavaha Srotas",     "c": "Oja Kshaya (Vata)",                  "d": "rasa"},
    "hashimoto":               {"p": "kapha","w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Rasavaha Srotas",     "c": "Kaphaja-Pittaja Galaganda",         "d": "rasa_mamsa"},
    # ── Dermatological ────────────────────────────────────────────────────────
    "psoriasis":               {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.5,    "s": "Raktavaha Srotas",    "c": "Eka Kushtha / Kitibha (Pitta + Vata)","d": "rakta"},
    "eczema":                  {"p": "pitta","w": 2.0, "s2": "kapha", "w2": 1.0,   "s": "Raktavaha Srotas",    "c": "Vicharchika (Pitta)",               "d": "rakta"},
    "acne_severe":             {"p": "pitta","w": 2.0, "s": "Raktavaha Srotas",    "c": "Pittaja Mukhadushika",                "d": "rakta"},
    "urticaria":               {"p": "pitta","w": 2.0, "s2": "vata", "w2": 1.0,    "s": "Raktavaha Srotas",    "c": "Udarda (Pitta + Vata)",             "d": "rakta"},
    "vitiligo":                {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.0,   "s": "Raktavaha Srotas",    "c": "Shvitra (Vata + Pitta)",            "d": "rakta"},
    "rosacea":                 {"p": "pitta","w": 2.5, "s": "Raktavaha Srotas",    "c": "Pittaja Twak Roga",                  "d": "rakta"},
    "alopecia":                {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Raktavaha Srotas",    "c": "Khalitya (Vata + Pitta)",           "d": "rakta"},
    # ── Urological / Renal ────────────────────────────────────────────────────
    "kidney_stones":           {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Mutravaha Srotas",    "c": "Mutrasmari (Vata + Kapha)",         "d": "majja"},
    "recurrent_uti":           {"p": "pitta","w": 2.0, "s": "Mutravaha Srotas",    "c": "Pittaja Mutrakrichra",               "d": "rakta"},
    "chronic_kidney_disease":  {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Mutravaha Srotas",    "c": "Mutra Kshaya (Vata + Kapha)",       "d": "majja"},
    "urinary_incontinence":    {"p": "vata", "w": 2.0, "s": "Mutravaha Srotas",    "c": "Mutragata Vata",                     "d": "majja"},
    "interstitial_cystitis":   {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.0,    "s": "Mutravaha Srotas",    "c": "Pittaja Mutrakrichra",              "d": "rakta"},
    "bph":                     {"p": "kapha","w": 2.0, "s2": "vata", "w2": 1.0,    "s": "Mutravaha Srotas",    "c": "Kaphaja Mutraghata",                "d": "shukra"},
    # ── Gynecological / Reproductive ─────────────────────────────────────────
    "endometriosis":           {"p": "vata", "w": 2.5, "s2": "pitta", "w2": 1.5,   "s": "Artavavaha Srotas",   "c": "Vataja Artava Dushti + Raktaja",    "d": "shukra"},
    "uterine_fibroids":        {"p": "kapha","w": 2.5, "s": "Artavavaha Srotas",   "c": "Kaphaja Granthi",                    "d": "shukra"},
    "dysmenorrhea":            {"p": "vata", "w": 2.5, "s": "Artavavaha Srotas",   "c": "Vataja Artava Krichra",              "d": "shukra"},
    "amenorrhea":              {"p": "vata", "w": 2.0, "s": "Artavavaha Srotas",   "c": "Nashta Artava (Vata)",               "d": "shukra"},
    "menorrhagia":             {"p": "pitta","w": 2.5, "s": "Artavavaha Srotas",   "c": "Raktapradar (Pitta)",                "d": "rakta"},
    "infertility":             {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Artavavaha / Shukravaha", "c": "Vandhyatva (Vata + Kapha)",     "d": "shukra"},
    "erectile_dysfunction":    {"p": "vata", "w": 2.5, "s": "Shukravaha Srotas",   "c": "Klaibya (Vataja)",                   "d": "shukra"},
    # ── Autoimmune ───────────────────────────────────────────────────────────
    "lupus":                   {"p": "pitta","w": 2.5, "s2": "vata", "w2": 1.5,    "s": "Raktavaha Srotas",    "c": "Pitta-Vata Janya Shotha",           "d": "rasa_mamsa"},
    "scleroderma":             {"p": "vata", "w": 2.5, "s2": "pitta", "w2": 1.5,   "s": "Raktavaha Srotas",    "c": "Twak Granthita (Vata + Pitta)",     "d": "rasa_mamsa"},
    # ── ENT ──────────────────────────────────────────────────────────────────
    "chronic_tonsillitis":     {"p": "kapha","w": 2.0, "s2": "pitta", "w2": 1.0,   "s": "Annavaha Srotas",     "c": "Tundikeri (Kapha)",                 "d": "rasa"},
    "nasal_polyps":            {"p": "kapha","w": 2.0, "s": "Pranavaha Srotas",    "c": "Nasa Arsha (Kapha)",                 "d": "rasa"},
    "hearing_loss":            {"p": "vata", "w": 2.0, "s": "Manovaha Srotas",     "c": "Badhirya (Vata)",                    "d": "majja"},
    "menieres_disease":        {"p": "vata", "w": 2.5, "s": "Manovaha Srotas",     "c": "Bhrama + Karnanada (Vata)",          "d": "majja"},
    # ── Ophthalmological ─────────────────────────────────────────────────────
    "glaucoma":                {"p": "vata", "w": 2.0, "s2": "pitta", "w2": 1.5,   "s": "Drishti Srotas",      "c": "Adhimantha (Vata + Pitta)",         "d": "majja"},
    "cataracts":               {"p": "kapha","w": 2.0, "s2": "vata", "w2": 1.0,    "s": "Drishti Srotas",      "c": "Linganasha (Kapha)",                "d": "majja"},
    "dry_eye":                 {"p": "vata", "w": 2.0, "s": "Drishti Srotas",      "c": "Sushkakshipaka (Vata)",              "d": "rasa"},
    "macular_degeneration":    {"p": "pitta","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Drishti Srotas",      "c": "Timira (Pitta + Vata)",             "d": "rakta"},
    # ── Hematological ────────────────────────────────────────────────────────
    "sickle_cell":             {"p": "pitta","w": 2.0, "s2": "vata", "w2": 2.0,    "s": "Raktavaha Srotas",    "c": "Rakta Dushti (Pitta + Vata)",       "d": "rakta"},
    "thalassemia":             {"p": "pitta","w": 2.0, "s2": "vata", "w2": 1.5,    "s": "Raktavaha Srotas",    "c": "Rakta Kshaya (Pitta + Vata)",       "d": "rakta"},
    # ── Chronic Infections ───────────────────────────────────────────────────
    "long_covid":              {"p": "vata", "w": 2.0, "s2": "kapha", "w2": 1.5,   "s": "Rasavaha Srotas",     "c": "Tridoshaja Bala Kshaya",            "d": "rasa"},
    "hepatitis_chronic":       {"p": "pitta","w": 2.5, "s": "Raktavaha Srotas",    "c": "Yakrit Shotha (Pitta)",              "d": "rakta"},
    "hiv":                     {"p": "vata", "w": 2.5, "s": "Rasavaha Srotas",     "c": "Oja Kshaya (Vata)",                  "d": "rasa"},
}


_DHATU_THERAPY: dict[str, dict] = {
    "rasa":        {"name": "Rasa Dhatu (Plasma/Lymph)",          "kshaya_therapy": "Dipana-Pachana → Brimhana (nourishing plasma)",                                       "vriddhi_therapy": "Langhana (lightening)",                                     "rasayana": "Ashwagandha, Shatavari, Amalaki"},
    "rakta":       {"name": "Rakta Dhatu (Blood)",                 "kshaya_therapy": "Raktavardhana: iron-rich foods, Punarnava, Manjistha",                                "vriddhi_therapy": "Raktamokshana (bloodletting) if indicated",                 "rasayana": "Manjistha, Guduchi, Amalaki"},
    "mamsa":       {"name": "Mamsa Dhatu (Muscle)",                "kshaya_therapy": "Brimhana: protein-rich Pathya, Ashwagandha, Bala",                                   "vriddhi_therapy": "Vyayama (exercise) + Langhana",                            "rasayana": "Ashwagandha, Bala, Kapikacchu"},
    "meda":        {"name": "Meda Dhatu (Adipose)",                "kshaya_therapy": "Brimhana with Ghrita",                                                               "vriddhi_therapy": "Lekhana (reducing): Guggulu, Triphala, exercise, fasting", "rasayana": "Guggulu, Shilajit, Triphala"},
    "asthi":       {"name": "Asthi Dhatu (Bone)",                  "kshaya_therapy": "Brimhana: Ashwagandha, sesame, ghee, warm milk, calcium-rich Pathya",                "vriddhi_therapy": "Shodhana if excess (rare)",                                 "rasayana": "Laksha Guggulu, Ashwagandha, sesame"},
    "majja":       {"name": "Majja Dhatu (Bone Marrow/Nerves)",    "kshaya_therapy": "Medhya Rasayana: Brahmi, Shankhapushpi, Ashwagandha, Bala Taila Abhyanga",          "vriddhi_therapy": "Shodhana (Nasya, Basti)",                                  "rasayana": "Brahmi, Shankhapushpi, Jyotishmati"},
    "shukra":      {"name": "Shukra/Artava Dhatu (Reproductive)",  "kshaya_therapy": "Vajikarna: Shatavari, Kapikacchu, Ashwagandha, warm milk with ghee",                "vriddhi_therapy": "Shodhana if indicated",                                     "rasayana": "Shatavari, Kapikacchu, Ashwagandha"},
    "asthi_majja": {"name": "Asthi + Majja Dhatu (Bone + Nerves)", "kshaya_therapy": "Brimhana: Ashwagandha, Bala Taila Abhyanga, Dashmoola Basti, sesame ghee",         "vriddhi_therapy": "Shodhana: Kati/Greeva Basti",                              "rasayana": "Mahayogaraj Guggulu, Ashwagandha"},
    "mamsa_rakta": {"name": "Mamsa + Rakta Dhatu (Muscle + Blood)","kshaya_therapy": "Raktashodhana + Brimhana: Guduchi, Neem, Manjistha, Ashwagandha",                  "vriddhi_therapy": "Shodhana: Virechana, Raktamokshana",                       "rasayana": "Guduchi, Manjistha, Triphala"},
    "rasa_rakta":  {"name": "Rasa + Rakta Dhatu (Plasma + Blood)", "kshaya_therapy": "Brimhana: Shatavari, Amalaki, Punarnava",                                           "vriddhi_therapy": "Langhana + Raktashodhana",                                 "rasayana": "Arjuna, Punarnava, Amalaki"},
    "rasa_mamsa":  {"name": "Rasa + Mamsa Dhatu (Plasma + Muscle)","kshaya_therapy": "Shodhana then Rasayana: Guduchi, Ashwagandha, Bala",                               "vriddhi_therapy": "Virechana + Langhana",                                     "rasayana": "Guduchi Satva, Ashwagandha, Bala"},
    "meda_rakta":  {"name": "Meda + Rakta Dhatu (Fat + Blood)",    "kshaya_therapy": "Brimhana selectively",                                                               "vriddhi_therapy": "Lekhana + Raktashodhana: Guggulu, Manjistha, Triphala",    "rasayana": "Guggulu, Triphala, Arjuna"},
}


def _dhatu_from_conditions(conditions: list[str]) -> list[dict]:
    """Return unique affected Dhatu entries for a set of medical conditions."""
    seen: set[str] = set()
    result: list[dict] = []
    for cond in conditions:
        key = cond.lower().strip().replace(" ", "_").replace("-", "_")
        mapping = _DISEASE_DOSHA_SIGNAL.get(key)
        if not mapping:
            continue
        dhatu_key = mapping.get("d", "rasa")
        if dhatu_key not in seen:
            seen.add(dhatu_key)
            info = _DHATU_THERAPY.get(dhatu_key, _DHATU_THERAPY["rasa"])
            result.append({"key": dhatu_key, **info})
    return result


def _compute_ojas_score(
    ama_score: str,
    disease_count: int,
    agni_type: str | None,
) -> dict:
    """
    Ojas = essence of all 7 Dhatus formed by perfect Agni + zero Ama.
    Charaka Chikitsa 24: Ojas depletes via Dhatu Kshaya, Ama, chronic disease,
    physical/mental overexertion, grief, fasting.
    """
    score = 100
    score -= {"none": 0, "mild": 15, "moderate": 30, "severe": 50}.get(ama_score, 0)
    score -= min(disease_count * 8, 40)
    score -= {"sama": 0, "pitta": 10, "vata": 15, "kapha": 12}.get(agni_type or "vata", 10)
    score = max(0, min(100, score))

    if score >= 70:
        return {
            "score": score, "level": "high",
            "label": "High Ojas — Strong Immunity & Vitality",
            "description": "Excellent Dhatu quality. Strong natural immunity (Vyadhikshamatva), mental clarity, and resilience. Maintain with Rasayana and Sattvic lifestyle.",
            "color": "green",
            "recommendation": "Maintain with Rasayana herbs: Amalaki, Ashwagandha, Shatavari. Continue current lifestyle.",
        }
    elif score >= 40:
        return {
            "score": score, "level": "medium",
            "label": "Medium Ojas — Moderate Immunity",
            "description": "Dhatu quality is fair. Some Ama or Agni imbalance is reducing optimal Ojas formation. Address Agni first, then Rasayana.",
            "color": "amber",
            "recommendation": "Prioritise Dipana-Pachana to clear Ama, then Rasayana: Chyawanprash, Guduchi, Ashwagandha.",
        }
    else:
        return {
            "score": score, "level": "low",
            "label": "Low Ojas — Depleted Immunity",
            "description": "Significant Dhatu depletion or Ama burden. Risk of recurrent illness, chronic fatigue, poor healing. Rasayana therapy is primary treatment.",
            "color": "red",
            "recommendation": "RASAYANA PRIORITY: Chyawanprash daily, Ashwagandha + warm milk at night, Shatavari if female. Absolute rest, Sattvic food, no fasting.",
        }


def _medical_history_vikriti_signal(medical_conditions: list[str]) -> tuple[dict, list[str]]:
    """Convert diagnosed diseases into a weighted dosha signal for Vikriti.

    Chronic diagnosed diseases reveal the patient's susceptible dosha channels.
    Returns (normalised_signal, classical_notes) where signal sums to 100.
    Source: Charaka Samhita Nidana Sthana (disease etiology chapters).
    """
    if not medical_conditions:
        return {}, []

    raw = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    total_weight = 0.0
    classical_notes: list[str] = []

    for condition in medical_conditions:
        key = condition.lower().strip().replace(" ", "_").replace("-", "_")
        mapping = _DISEASE_DOSHA_SIGNAL.get(key)
        if not mapping:
            continue
        primary = mapping["p"]
        weight = mapping["w"]
        raw[primary] += weight
        if "s2" in mapping:
            raw[mapping["s2"]] += mapping.get("w2", weight * 0.5)
        total_weight += weight
        classical_notes.append(
            f"{condition.replace('_', ' ').title()}: {mapping['c']} ({mapping['s']})"
        )

    if total_weight == 0:
        return {}, []

    total_raw = sum(raw.values()) or 1
    signal = {d: round(v / total_raw * 100) for d, v in raw.items()}
    diff = 100 - sum(signal.values())
    if diff != 0:
        signal[max(signal, key=signal.get)] += diff

    return signal, classical_notes


def _anchor_to_prakriti(vikriti: dict, prakriti: dict, max_deviation: int = 28) -> dict:
    """Prevent vikriti from drifting implausibly far from prakriti.

    Ayurveda holds that constitutional type (prakriti) is fixed — while current
    imbalance (vikriti) can shift, extreme divergence is clinically implausible
    and produces poor plan recommendations. We cap per-dosha deviation at
    max_deviation percentage points from prakriti.
    """
    if not prakriti:
        return vikriti
    anchored = {}
    for d in ["vata", "pitta", "kapha"]:
        pk_val = prakriti.get(d, 33)
        vk_val = vikriti.get(d, 33)
        anchored[d] = max(pk_val - max_deviation, min(pk_val + max_deviation, vk_val))
    total = sum(anchored.values()) or 1
    result = {d: round(v / total * 100) for d, v in anchored.items()}
    diff = 100 - sum(result.values())
    if diff != 0:
        dominant = max(result, key=result.get)
        result[dominant] += diff
    return result


def _vikriti_secondary(vikriti: dict) -> str | None:
    """Return the secondary vikriti dosha if it's close to the dominant (gap < 18 points)."""
    sorted_v = sorted(vikriti.items(), key=lambda x: x[1], reverse=True)
    if sorted_v[0][1] - sorted_v[1][1] < 18:
        return sorted_v[1][0]
    return None


def _age_adjustment(scores: dict, age: int | None) -> dict:
    """Apply classical Ayurvedic age-dosha adjustments to vikriti only.

    In Ayurveda: Kapha dominates childhood, Pitta dominates adulthood, and
    Vata increases as we age (60+). These shifts affect vikriti tendency —
    not immutable Prakriti — so we apply a mild nudge only.
    """
    if not age:
        return scores
    adjusted = dict(scores)
    if age >= 60:
        # Vata increases in old age — gentle bump
        adjusted["vata"] = min(65, round(adjusted.get("vata", 33) * 1.10))
        adjusted["kapha"] = max(10, round(adjusted.get("kapha", 33) * 0.92))
    elif age < 18:
        # Kapha dominates in youth
        adjusted["kapha"] = min(55, round(adjusted.get("kapha", 33) * 1.06))
    # Normalise
    total = sum(adjusted.values()) or 1
    result = {d: round(v / total * 100) for d, v in adjusted.items()}
    diff = 100 - sum(result.values())
    if diff != 0:
        result[max(result, key=result.get)] += diff
    return result


def _lifestyle_pulse_signal(
    sleep: int | None,
    stress: int | None,
    digestion: int | None,
) -> dict[str, float]:
    """Convert weekly lifestyle ratings (1-5 scale) to a dosha-weighted signal.

    Each dimension maps to doshas that classical Ayurveda associates with it:
    - Poor sleep (1-2)    → vata (restless/anxious mind)
    - High stress (1-2)   → vata + pitta (anxiety and inflammation)
    - Poor digestion (1-2)→ vata (irregular) or kapha (sluggish) depending on value
    - Good sleep (4-5)    → mild kapha recovery signal
    Returns a normalised dict that can be blended into vikriti as a lifestyle slot.
    """
    raw = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    if sleep is not None:
        if sleep <= 2:
            raw["vata"] += 2.0
            raw["pitta"] += 0.5
        elif sleep >= 4:
            raw["kapha"] += 0.5
    if stress is not None:
        if stress <= 2:
            raw["vata"] += 1.5
            raw["pitta"] += 1.5
        elif stress == 3:
            raw["pitta"] += 0.5
    if digestion is not None:
        if digestion <= 2:
            raw["vata"] += 1.0
            raw["kapha"] += 1.0
        elif digestion >= 4:
            raw["pitta"] += 0.3
    total = sum(raw.values())
    if total == 0:
        return {}
    normalised = {d: round(v / total * 100) for d, v in raw.items()}
    diff = 100 - sum(normalised.values())
    if diff != 0:
        normalised[max(normalised, key=normalised.get)] += diff
    return normalised


def _symptom_persistence_weights(
    current_symptoms: list[str],
    history: list[dict] | None,
) -> dict[str, float]:
    """Compute per-symptom persistence multipliers from rolling vikriti history.

    A symptom appearing in the last 2 consecutive weeks gets 1.5x weight.
    A symptom appearing in the last 3+ consecutive weeks gets 2.0x weight.
    This makes chronic recurring symptoms carry more diagnostic weight than
    transient one-off complaints.
    """
    if not history or not current_symptoms:
        return {s: 1.0 for s in current_symptoms}

    multipliers: dict[str, float] = {}
    for symptom in current_symptoms:
        streak = 0
        for entry in reversed(history[-3:]):
            past_symptoms = entry.get("symptoms", [])
            if symptom in past_symptoms:
                streak += 1
            else:
                break
        if streak >= 3:
            multipliers[symptom] = 2.0
        elif streak >= 2:
            multipliers[symptom] = 1.5
        else:
            multipliers[symptom] = 1.0
    return multipliers


def _compute_symptom_signal(
    symptoms: list[str],
    persistence_weights: dict[str, float] | None = None,
) -> dict[str, float]:
    """Convert a symptom list into a normalised fractional dosha signal {0–100}.

    If persistence_weights is provided, chronic symptoms (higher multiplier) carry
    more diagnostic weight — they represent stable imbalance patterns, not noise.
    """
    meaningful = [s for s in symptoms if s != "feeling_balanced"]
    if not meaningful:
        return {}

    raw = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    for s in meaningful:
        weights = _SYMPTOM_DOSHA_WEIGHTS.get(s)
        if weights:
            multiplier = (persistence_weights or {}).get(s, 1.0)
            for d, w in weights.items():
                raw[d] += w * multiplier

    total = sum(raw.values()) or 1
    normalised = {d: round(v / total * 100) for d, v in raw.items()}
    diff = 100 - sum(normalised.values())
    if diff != 0:
        normalised[max(normalised, key=normalised.get)] += diff
    return normalised


def _blend_vikriti(
    old_vikriti: dict,
    new_signal: dict,
    symptom_count: int,
    prakriti: dict | None = None,
    lifestyle_signal: dict | None = None,
) -> dict:
    """Blend old vikriti with symptom signal + lifestyle pulse using adaptive weighting.

    The symptom signal weight scales with symptom count — a single symptom
    shouldn't overwrite weeks of accumulated data. If a lifestyle_signal is
    provided (from sleep/stress/digestion pulse), it takes a fixed 15% slot
    and the symptom signal takes the remainder of the new-signal budget.

    symptom_count → total new-signal weight (before lifestyle split):
        0    → 0.00 (drift back toward prakriti)
        1    → 0.10
        2    → 0.18
        3    → 0.25
        4    → 0.30
        5+   → 0.35 (cap)
    Lifestyle slot: 0.15 of the new-signal budget (when pulse data is present).
    """
    LIFESTYLE_SLOT = 0.15

    if symptom_count == 0 and not lifestyle_signal:
        anchor = prakriti if prakriti else {"vata": 33, "pitta": 33, "kapha": 34}
        blended_raw = {d: round(0.92 * old_vikriti.get(d, 33) + 0.08 * anchor.get(d, 33))
                       for d in ["vata", "pitta", "kapha"]}
    else:
        total_new_weight = min(0.35, round(0.10 + max(0, symptom_count - 1) * 0.08, 2))
        if lifestyle_signal:
            ls_weight = LIFESTYLE_SLOT * total_new_weight
            sym_weight = total_new_weight - ls_weight
        else:
            ls_weight = 0.0
            sym_weight = total_new_weight
        old_weight = 1.0 - total_new_weight

        blended_raw = {}
        for d in ["vata", "pitta", "kapha"]:
            val = old_weight * old_vikriti.get(d, 33)
            if new_signal:
                val += sym_weight * new_signal.get(d, 33)
            if lifestyle_signal:
                val += ls_weight * lifestyle_signal.get(d, 33)
            blended_raw[d] = round(val)

    total = sum(blended_raw.values()) or 1
    blended = {d: round(v / total * 100) for d, v in blended_raw.items()}
    diff = 100 - sum(blended.values())
    if diff != 0:
        blended[max(blended, key=blended.get)] += diff

    if prakriti:
        blended = _anchor_to_prakriti(blended, prakriti)

    return blended


def _rule_based_assessment(
    physical_traits: dict,
    current_symptoms: list[str],
    age: int | None = None,
    history: list[dict] | None = None,
    medical_history: list[str] | None = None,
) -> dict:
    """Weighted trait-count Prakriti + symptom-signal Vikriti (LLM fallback)."""
    prakriti_raw = {"vata": 0.0, "pitta": 0.0, "kapha": 0.0}
    for trait, val in physical_traits.items():
        if val == "sama" and trait == "agni_type":
            # Sama Agni = balanced fire — does not bias any dosha
            continue
        if val in prakriti_raw:
            weight = _TRAIT_WEIGHTS.get(trait, 1.0)
            prakriti_raw[val] += weight

    total_p = sum(prakriti_raw.values()) or 1
    prakriti = {d: round(v / total_p * 100) for d, v in prakriti_raw.items()}
    diff = 100 - sum(prakriti.values())
    if diff != 0:
        prakriti[max(prakriti, key=prakriti.get)] += diff

    # Cap at 55 for self-report (low confidence cannot justify extreme scores)
    dominant_p = max(prakriti, key=prakriti.get)
    if prakriti[dominant_p] > 55:
        excess = prakriti[dominant_p] - 55
        prakriti[dominant_p] = 55
        others = [d for d in prakriti if d != dominant_p]
        other_total = sum(prakriti[d] for d in others) or 1
        for d in others:
            prakriti[d] += round(excess * prakriti[d] / other_total)
        diff = 100 - sum(prakriti.values())
        if diff != 0:
            prakriti[others[0]] += diff

    meaningful_count = len([s for s in current_symptoms if s != "feeling_balanced"])
    persistence_weights = _symptom_persistence_weights(current_symptoms, history) if history else None

    if meaningful_count > 0:
        symptom_signal = _compute_symptom_signal(current_symptoms, persistence_weights)
        vikriti = _blend_vikriti(prakriti, symptom_signal, meaningful_count, prakriti)
    else:
        vikriti = dict(prakriti)

    if age:
        vikriti = _age_adjustment(vikriti, age)

    # Medical history — chronic disease channel involvement biases Vikriti (20% slot)
    med_signal, med_notes = _medical_history_vikriti_signal(medical_history or [])
    if med_signal:
        MEDICAL_SLOT = 0.20
        vikriti = {
            d: round((1 - MEDICAL_SLOT) * vikriti.get(d, 33) + MEDICAL_SLOT * med_signal.get(d, 33))
            for d in ["vata", "pitta", "kapha"]
        }
        _mt = sum(vikriti.values()) or 1
        vikriti = {d: round(v / _mt * 100) for d, v in vikriti.items()}
        _md = 100 - sum(vikriti.values())
        if _md != 0:
            vikriti[max(vikriti, key=vikriti.get)] += _md

    sorted_p = sorted(prakriti.items(), key=lambda x: x[1], reverse=True)
    sorted_v = sorted(vikriti.items(), key=lambda x: x[1], reverse=True)
    prakriti_dominant = sorted_p[0][0]
    prakriti_secondary = sorted_p[1][0]
    vikriti_dominant = sorted_v[0][0]

    if sorted_p[0][1] > 50:
        constitution_type = prakriti_dominant
    elif sorted_p[0][1] - sorted_p[1][1] < 10:
        constitution_type = f"{prakriti_dominant}_{prakriti_secondary}"
    else:
        constitution_type = prakriti_dominant

    fallback_explanations = {
        "vata": "Based on your answers, you lean toward a Vata constitution — naturally light, creative, and quick-moving. This is an initial estimate that will improve with weekly check-ins.",
        "pitta": "Based on your answers, you lean toward a Pitta constitution — naturally driven and metabolically strong. This is an initial estimate that will improve with weekly check-ins.",
        "kapha": "Based on your answers, you lean toward a Kapha constitution — naturally stable and resilient. This is an initial estimate that will improve with weekly check-ins.",
    }

    return {
        "prakriti": prakriti,
        "vikriti": vikriti,
        "prakriti_dominant": prakriti_dominant,
        "prakriti_secondary": prakriti_secondary,
        "vikriti_dominant": vikriti_dominant,
        "constitution_type": constitution_type,
        "confidence": "low",
        "confidence_score": 35,
        "explanation": fallback_explanations.get(prakriti_dominant, "Your constitution has been assessed based on your physical traits."),
        "immediate_focus": f"Your plans will be tuned to address your current {vikriti_dominant} imbalance.",
        "key_signals": [
            f"Dominant physical type: {prakriti_dominant}",
            f"Primary current symptom area: {vikriti_dominant}",
        ] + med_notes[:2],
        "contradictions": [],
        "primary_gunas": _get_primary_gunas(prakriti_dominant, prakriti_secondary),
        "prakriti_classical_type": _classify_prakriti_7_types(prakriti)["prakriti_classical_type"],
        "prakriti_classical_name": _classify_prakriti_7_types(prakriti)["prakriti_classical_name"],
        "manas_prakriti": None,
        "ama_indicator": _compute_ama_score(current_symptoms),
        "ojas": _compute_ojas_score(
            ama_score=_compute_ama_score(current_symptoms),
            disease_count=len(medical_history or []),
            agni_type=(physical_traits or {}).get("agni_type"),
        ),
    }


async def assess_dosha_with_llm(
    physical_traits: dict,
    current_symptoms: list[str],
    user_profile: dict | None = None,
) -> dict:
    """
    Holistic Prakriti + Vikriti assessment via LLM with rule-based fallback.

    physical_traits: {"body_frame": "vata"|"pitta"|"kapha", "skin": ...,
                      "digestion": ..., "sleep": ..., "temperature": ...}
    current_symptoms: list of symptom cluster IDs
    user_profile: optional context dict (age, gender, stress_level, etc.)
    """
    import json
    import logging
    from ai.llm_client import llm_client

    logger = logging.getLogger(__name__)

    # Weighted trait summary for LLM prompt — highlight primary indicators
    trait_lines = []
    for trait, value in physical_traits.items():
        desc = _TRAIT_DESCRIPTIONS.get(trait, {}).get(value, value)
        weight = _TRAIT_WEIGHTS.get(trait, 1.0)
        priority = " [PRIMARY INDICATOR]" if weight >= 2.0 else (" [STRONG INDICATOR]" if weight >= 1.5 else "")
        trait_lines.append(f"- {trait.replace('_', ' ').title()}{priority}: {desc}")

    meaningful_symptoms = [s for s in current_symptoms if s != "feeling_balanced"]
    if meaningful_symptoms:
        symptom_text = "\n".join(f"- {_SYMPTOM_DESCRIPTIONS.get(s, s)}" for s in meaningful_symptoms)
    else:
        symptom_text = "No specific complaints — feeling generally balanced"

    profile_section = ""
    if user_profile:
        parts = []
        if user_profile.get("age"):
            parts.append(f"Age: {user_profile['age']}")
        if user_profile.get("gender"):
            parts.append(f"Gender: {user_profile['gender']}")
        if user_profile.get("stress_level"):
            parts.append(f"Stress level: {user_profile['stress_level']}")
        if user_profile.get("sleep_quality"):
            parts.append(f"Sleep quality: {user_profile['sleep_quality']}")
        if user_profile.get("digestion_quality"):
            parts.append(f"Digestion quality: {user_profile['digestion_quality']}")
        if user_profile.get("fitness_level"):
            parts.append(f"Fitness level: {user_profile['fitness_level']}")
        if parts:
            profile_section = "\n\nUSER PROFILE CONTEXT (use to refine your assessment):\n" + "\n".join(f"- {p}" for p in parts)

    # Medical history → classical Ayurvedic disease names for LLM context
    medical_section = ""
    _med_conditions = (user_profile or {}).get("medical_history") or []
    if _med_conditions:
        _med_sig, _med_notes = _medical_history_vikriti_signal(_med_conditions)
        if _med_notes:
            medical_section = (
                "\n\nDIAGNOSED MEDICAL CONDITIONS (HIGH-WEIGHT Vikriti evidence — classical Ayurvedic etiology):\n"
                + "\n".join(f"- {n}" for n in _med_notes)
                + "\nThese chronic diagnoses indicate dosha channel involvement. Weight them HEAVILY in Vikriti scoring."
            )
        else:
            medical_section = f"\n\nMedical history (unclassified): {', '.join(_med_conditions)}"

    system_prompt = (
        "You are an expert Ayurvedic physician (Vaidya) trained in classical Prakriti and Vikriti "
        "assessment from Charaka Samhita, Sushruta Samhita, and Ashtanga Hridayam. "
        "You assess Shareera Prakriti (physical constitution) and Manas Prakriti (mental constitution) separately, "
        "and distinguish these from Vikriti (current imbalance). "
        "You use the Ashtavidha Pareeksha framework: Nadi, Mala, Mutra, Jihva, Shabda, Sparsha, Drik, Akriti. "
        "You are familiar with the 7 Prakriti types (Sapta Prakriti) and the 20 Gunas (Vimshatika Guna). "
        "Body frame, digestion/Agni, and stool pattern [PRIMARY] are most diagnostically reliable. "
        "Mental traits indicate Manas Prakriti — classify using Sattva/Rajas/Tamas tendency alongside dosha. "
        "Always reason step-by-step in the <reasoning> block before producing scores."
    )

    user_prompt = f"""Perform a holistic Ayurvedic constitution assessment following the classical Ashtavidha Pareeksha framework.

SHAREERA PRAKRITI INDICATORS (physical constitution — lifelong, relatively fixed):
{chr(10).join(trait_lines)}

CURRENT SYMPTOMS / VIKRITI INDICATORS (present imbalances to correct):
{symptom_text}{profile_section}{medical_section}

ASSESSMENT GUIDELINES:
1. Shareera Prakriti = physical constitution. Mental/behavioral traits = Manas Prakriti. Both contribute to overall Prakriti.
2. Agni type [PRIMARY INDICATOR] is as diagnostically important as body frame — Vishama=Vata, Tikshna=Pitta, Manda=Kapha, Sama=balanced.
3. Stool pattern (Mala Pareeksha), eye quality (Drik), voice (Shabda) are Ashtavidha indicators — weight them accordingly.
4. Manas Prakriti: classify mental tendency as Sattvic/Rajasic/Tamasic with dominant dosha.
   - Vata mental traits → Rajasic tendency (fear, anxiety, variability)
   - Pitta mental traits → Rajasic tendency (anger, ambition, competitiveness)
   - Kapha mental traits → Sattvic tendency (stability, patience, nurturing)
5. Vikriti must not deviate more than 28 points from any Prakriti value.
6. Both prakriti and vikriti scores must sum to exactly 100.
7. If Agni is Sama, do not use it to bias any dosha — it indicates balance.
8. Classify into one of the 7 classical Prakriti types (Sapta Prakriti).
9. List the dominant Gunas (from Vimshatika Guna, Charaka Sutrasthana 1.59-61).
10. Ojas Assessment (Charaka Chikitsa 24): Ojas = essence of all 7 Dhatus formed by perfect Agni + zero Ama. Score 0-100:
    - High (70-100): Sama Agni, no/mild Ama, no chronic diseases, strong vitality
    - Medium (40-69): Some Ama or mild disease burden, moderate Agni impairment
    - Low (0-39): High Ama, multiple chronic diseases, Vishama/Manda/Tikshna Agni, chronic fatigue, anxiety, poor immunity

First reason through the evidence:
<reasoning>
- What do PRIMARY indicators (body frame, Agni/digestion, stool pattern) suggest?
- What do mental/behavioral traits suggest for Manas Prakriti type and Guna tendency?
- What Ashtavidha signals (eye, voice) confirm or refine this?
- Do symptoms show Vikriti divergence from Prakriti?
- Which of the 7 Prakriti types does this person belong to?
- Are there contradictions? What Guna language best describes this person?
</reasoning>

Then respond with valid JSON only (no markdown, no ```):
{{
  "prakriti": {{"vata": <integer 0-100>, "pitta": <integer 0-100>, "kapha": <integer 0-100>}},
  "vikriti": {{"vata": <integer 0-100>, "pitta": <integer 0-100>, "kapha": <integer 0-100>}},
  "prakriti_dominant": "<vata|pitta|kapha>",
  "prakriti_secondary": "<vata|pitta|kapha>",
  "vikriti_dominant": "<vata|pitta|kapha>",
  "constitution_type": "<one of: vata, pitta, kapha, vata_pitta, pitta_kapha, kapha_vata, pitta_vata, kapha_pitta, vata_kapha, tridoshic>",
  "prakriti_classical_type": "<same format as constitution_type>",
  "confidence": "<low|medium|high>",
  "explanation": "<2-3 sentences explaining this person's constitution and current state in plain English, speaking directly to them using 'you'. Include the Guna character.>",
  "immediate_focus": "<1 sentence on what their wellness plans should prioritize RIGHT NOW>",
  "key_signals": ["<top signal 1>", "<signal 2>", "<signal 3>"],
  "contradictions": ["<describe any significant conflict, or leave empty array>"],
  "primary_gunas": ["<e.g. Ruksha (dry)>", "<Laghu (light)>", "<Chala (mobile)>"],
  "manas_prakriti": "<e.g. Rajasic Vata-Pitta Manas — quick-thinking but prone to anxiety and sharp reactions>",
  "ama_indicator": "<none|mild|moderate|high — estimate of Ama based on digestive symptoms and Agni type>",
  "ojas": {{"score": <integer 0-100>, "level": "<high|medium|low>", "label": "<descriptive label>", "description": "<1 sentence>", "recommendation": "<1 sentence Rasayana recommendation>"}}
}}"""

    try:
        response_text = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=system_prompt,
            max_tokens=1200,
            temperature=0.1,
            json_mode=False,
        )

        # Strip chain-of-thought reasoning block before extracting JSON
        text = response_text.strip()
        if "<reasoning>" in text and "</reasoning>" in text:
            text = text[text.index("</reasoning>") + len("</reasoning>"):].strip()
        # Strip markdown fences if present
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
            text = text.strip()
        # Find the JSON object boundaries
        start = text.find("{")
        end = text.rfind("}") + 1
        if start != -1 and end > start:
            text = text[start:end]

        result = json.loads(text)

        if "error" in result:
            raise ValueError(f"LLM provider error: {result['error']}")

        # Normalise scores to sum to 100
        for key in ("prakriti", "vikriti"):
            scores = result[key]
            total = sum(scores.values())
            if total > 0 and total != 100:
                factor = 100 / total
                corrected = {d: round(v * factor) for d, v in scores.items()}
                diff = 100 - sum(corrected.values())
                dominant = max(corrected, key=corrected.get)
                corrected[dominant] += diff
                result[key] = corrected

        result["confidence_score"] = _confidence_score(result.get("confidence", "low"))

        # Cap dominant dosha by confidence tier
        _max_dominant = {"high": 70, "medium": 60, "low": 50}
        confidence = result.get("confidence", "low")
        cap = _max_dominant.get(confidence, 50)
        for key in ("prakriti", "vikriti"):
            scores = result[key]
            dominant = max(scores, key=scores.get)
            if scores[dominant] > cap:
                excess = scores[dominant] - cap
                scores[dominant] = cap
                others = [d for d in scores if d != dominant]
                other_total = sum(scores[d] for d in others) or 1
                for d in others:
                    scores[d] += round(excess * scores[d] / other_total)
                diff = 100 - sum(scores.values())
                if diff != 0:
                    sec = sorted(others, key=lambda d: scores[d], reverse=True)[0]
                    scores[sec] += diff
                result[key] = scores

        # Enforce prakriti anchoring on vikriti even for LLM output
        result["vikriti"] = _anchor_to_prakriti(result["vikriti"], result["prakriti"])

        if result.get("confidence") == "low":
            existing = result.get("explanation", "")
            if existing and not existing.endswith("check-ins."):
                result["explanation"] = (
                    existing.rstrip(".") +
                    ". Your signals are balanced, so this is an initial estimate — "
                    "it will refine automatically with each weekly check-in."
                )
            result["immediate_focus"] = (
                (result.get("immediate_focus") or "") +
                " (Low confidence — complete more check-ins for a refined reading.)"
            ).strip()

        result["vikriti"] = _apply_seasonal_correction(result["vikriti"])
        result["vikriti_dominant"] = max(result["vikriti"], key=result["vikriti"].get)

        # 7-type classical Prakriti classification
        prakriti_7type = _classify_prakriti_7_types(result["prakriti"])
        if not result.get("prakriti_classical_type"):
            result["prakriti_classical_type"] = prakriti_7type["prakriti_classical_type"]
        result["prakriti_classical_name"] = prakriti_7type["prakriti_classical_name"]

        # Guna profile — use LLM output or compute from dominant
        if not result.get("primary_gunas"):
            result["primary_gunas"] = _get_primary_gunas(
                result.get("prakriti_dominant", "vata"),
                result.get("prakriti_secondary"),
            )

        # Ama indicator — use LLM estimate or compute from symptoms
        if not result.get("ama_indicator"):
            result["ama_indicator"] = _compute_ama_score(current_symptoms or [])

        # Ojas — use LLM estimate or compute from rule-based formula
        if not result.get("ojas") or not isinstance(result.get("ojas"), dict):
            result["ojas"] = _compute_ojas_score(
                ama_score=result["ama_indicator"],
                disease_count=len((user_profile or {}).get("medical_history") or []),
                agni_type=(physical_traits or {}).get("agni_type"),
            )

        # Ensure contradictions field is always present and clean
        if "contradictions" not in result:
            result["contradictions"] = []
        result["contradictions"] = [c for c in result["contradictions"] if c and c.strip()]

        return result

    except Exception as exc:
        logger.warning("LLM dosha assessment failed (%s), using rule-based fallback.", exc)
        fallback = _rule_based_assessment(
            physical_traits, current_symptoms,
            medical_history=(user_profile or {}).get("medical_history") or [],
        )
        fallback["vikriti"] = _apply_seasonal_correction(fallback["vikriti"])
        fallback["vikriti_dominant"] = max(fallback["vikriti"], key=fallback["vikriti"].get)
        if "contradictions" not in fallback:
            fallback["contradictions"] = []
        if "primary_gunas" not in fallback:
            fallback["primary_gunas"] = _get_primary_gunas(fallback.get("prakriti_dominant", "vata"))
        if "ama_indicator" not in fallback:
            fallback["ama_indicator"] = _compute_ama_score(current_symptoms or [])
        return fallback


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


# Per-question dosha weights for the legacy 20-question quiz (kept for backward compatibility)
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
