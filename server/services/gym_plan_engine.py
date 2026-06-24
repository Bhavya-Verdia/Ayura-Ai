import json
import hashlib
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
EXERCISES_PATH = BASE_DIR / "data" / "knowledge_base" / "gym_exercises.json"

gym_exercises = []
if EXERCISES_PATH.exists():
    with open(EXERCISES_PATH, "r", encoding="utf-8") as f:
        gym_exercises = json.load(f)


# ── Warmup / Cooldown libraries ───────────────────────────────────────────────

_WARMUP = {
    "upper": [
        "Arm circles — 10 forward, 10 backward",
        "Cross-body shoulder stretch — 30 sec each side",
        "Shoulder roll — 10 slow rotations",
        "Band pull-apart or doorway chest stretch — 15 reps",
        "Cat-cow — 8 reps",
        "Wrist circles — 10 each direction",
    ],
    "lower": [
        "Hip circles — 10 each direction",
        "Leg swings — 10 forward/back each leg",
        "Bodyweight squat — 10 slow reps",
        "Ankle circles — 10 each direction",
        "Glute bridge — 12 reps",
        "Walking lunge — 8 each leg",
    ],
    "core": [
        "Cat-cow — 10 reps",
        "Dead bug — 8 each side",
        "Hip flexor stretch — 30 sec each side",
        "Bird dog — 8 each side",
        "High knees — 30 sec",
    ],
    "full": [
        "Jumping jacks — 30 sec",
        "Arm circles — 10 each direction",
        "Hip circles — 10 each direction",
        "Bodyweight squat — 10 reps",
        "High knees — 30 sec",
        "Inchworm — 5 reps",
    ],
    "cardio": [
        "Brisk walk or light jog — 3 min",
        "Leg swings — 10 each leg",
        "Ankle circles — 10 each direction",
        "Hip circles — 10 each direction",
        "Dynamic quad stretch — 8 each leg",
    ],
}

_COOLDOWN = {
    "upper": [
        "Doorway chest stretch — 30 sec",
        "Cross-body shoulder stretch — 30 sec each side",
        "Overhead tricep stretch — 30 sec each arm",
        "Lat stretch in doorway — 30 sec each side",
        "Child's pose — 60 sec",
        "Deep belly breathing — 5 breaths",
    ],
    "lower": [
        "Standing quad stretch — 30 sec each leg",
        "Seated hamstring stretch — 30 sec each leg",
        "Pigeon pose or figure-four stretch — 45 sec each side",
        "Calf stretch against wall — 30 sec each leg",
        "Supine spinal twist — 30 sec each side",
        "Child's pose — 60 sec",
    ],
    "core": [
        "Supine spinal twist — 30 sec each side",
        "Child's pose — 60 sec",
        "Hip flexor stretch (lunge) — 30 sec each side",
        "Cobra stretch — 30 sec",
        "Deep belly breathing — 5 breaths",
    ],
    "full": [
        "Child's pose — 60 sec",
        "Supine spinal twist — 30 sec each side",
        "Quad stretch — 30 sec each leg",
        "Shoulder cross-body stretch — 30 sec each arm",
        "Deep belly breathing — 5 breaths",
    ],
    "cardio": [
        "Walk at easy pace — 3 min",
        "Standing quad stretch — 30 sec each leg",
        "Standing calf stretch — 30 sec each leg",
        "Seated hamstring stretch — 30 sec each leg",
        "Deep belly breathing — 5 breaths",
    ],
}

_FOCUS_WARMUP_TYPE = {
    "full_body": "full", "push": "upper", "pull": "upper",
    "chest_triceps": "upper", "back_biceps": "upper",
    "chest": "upper", "back": "upper", "shoulders": "upper",
    "shoulders_core": "upper", "arms": "upper",
    "legs": "lower", "legs_core": "lower",
    "shoulders_arms": "upper", "core_cardio": "cardio",
}


def _warmup_for(focus: str) -> list:
    return _WARMUP.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _WARMUP["full"])


def _cooldown_for(focus: str) -> list:
    return _COOLDOWN.get(_FOCUS_WARMUP_TYPE.get(focus, "full"), _COOLDOWN["full"])


# ── Goal-based prescription ───────────────────────────────────────────────────

_GOAL_WEEKS = {
    "strength": [
        {"sets": 3, "reps": "3-5",  "rest_seconds": 180, "note": "Focus on form. Choose a weight you can barely complete 5 clean reps with."},
        {"sets": 4, "reps": "3-5",  "rest_seconds": 180, "note": "Add 2.5–5 kg vs Week 1 on main lifts if all reps were clean."},
        {"sets": 4, "reps": "4-5",  "rest_seconds": 180, "note": "Peak intensity week — push for personal bests on compound lifts."},
        {"sets": 2, "reps": "3-5",  "rest_seconds": 180, "note": "Deload — reduce weight 20%, focus on perfect technique."},
    ],
    "muscle_gain": [
        {"sets": 3, "reps": "8-10",  "rest_seconds": 90, "note": "Foundation — last 2 reps of each set should feel challenging."},
        {"sets": 3, "reps": "10-12", "rest_seconds": 75, "note": "Volume build — same weight as W1, push for extra reps."},
        {"sets": 4, "reps": "10-12", "rest_seconds": 60, "note": "Peak volume — highest workload week, add weight if form is solid."},
        {"sets": 2, "reps": "8-10",  "rest_seconds": 90, "note": "Deload — reduce weight 15%, prioritise mind-muscle connection."},
    ],
    "fat_loss": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 45, "note": "Keep rest short to maintain elevated heart rate. Moderate weight."},
        {"sets": 3, "reps": "15-20", "rest_seconds": 35, "note": "Cut rest by 10 sec vs Week 1 to increase metabolic demand."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 30, "note": "Peak metabolic week — minimum rest, circuit style if possible."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 45, "note": "Deload — slightly fewer reps, full rest, let connective tissue recover."},
    ],
    "endurance": [
        {"sets": 3, "reps": "15-20", "rest_seconds": 30, "note": "Light weight, high reps. Focus on breathing rhythm throughout."},
        {"sets": 4, "reps": "15-20", "rest_seconds": 25, "note": "Add 1 set vs Week 1. Cut rest to challenge aerobic capacity."},
        {"sets": 4, "reps": "18-22", "rest_seconds": 20, "note": "Peak endurance week — go to near-failure on each set."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 30, "note": "Deload — reduce volume, maintain movement quality."},
    ],
    "general_fitness": [
        {"sets": 3, "reps": "10-12", "rest_seconds": 60, "note": "Balanced foundation. Should feel moderately challenging by last rep."},
        {"sets": 3, "reps": "12-15", "rest_seconds": 50, "note": "Increase reps or reduce rest slightly vs Week 1."},
        {"sets": 4, "reps": "12-15", "rest_seconds": 45, "note": "Peak week — add 1 set to all exercises."},
        {"sets": 2, "reps": "10-12", "rest_seconds": 60, "note": "Deload — back to Week 1 volume, let the body consolidate gains."},
    ],
}


def _get_goal_prescription(goal: str, week: int) -> dict:
    return _GOAL_WEEKS.get(goal, _GOAL_WEEKS["general_fitness"])[min(week - 1, 3)]


# ── Weight / Load Guidance ────────────────────────────────────────────────────
# (lo, hi) in kg. Dumbbell = per-hand weight. Cable/machine = stack weight.
# Female ranges are ~60-65% of male — reflects average population, not a ceiling.

_WEIGHT_GUIDE = {
    "barbell": {
        "chest":     {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (35,55),  "female": (20,35)},
                      "intermediate": {"male": (55,90), "female": (35,55)},
                      "advanced":  {"male": (90,140), "female": (55,85)}},
        "back":      {"untrained": {"male": (30,50),  "female": (20,35)},
                      "beginner":  {"male": (50,80),  "female": (30,50)},
                      "intermediate": {"male": (80,130), "female": (50,80)},
                      "advanced":  {"male": (130,200),"female": (80,120)}},
        "legs":      {"untrained": {"male": (30,50),  "female": (20,35)},
                      "beginner":  {"male": (50,80),  "female": (30,55)},
                      "intermediate": {"male": (80,130), "female": (50,85)},
                      "advanced":  {"male": (130,200),"female": (80,130)}},
        "shoulders": {"untrained": {"male": (15,30),  "female": (8,18)},
                      "beginner":  {"male": (28,48),  "female": (15,30)},
                      "intermediate": {"male": (46,72), "female": (28,46)},
                      "advanced":  {"male": (70,100), "female": (44,68)}},
        "core":      {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (30,50),  "female": (15,30)},
                      "intermediate": {"male": (50,80), "female": (28,48)},
                      "advanced":  {"male": (80,120), "female": (46,72)}},
    },
    "dumbbell": {
        "chest":     {"untrained": {"male": (6,10),  "female": (3,6)},
                      "beginner":  {"male": (10,16), "female": (5,10)},
                      "intermediate": {"male": (16,26), "female": (8,16)},
                      "advanced":  {"male": (26,40), "female": (14,24)}},
        "back":      {"untrained": {"male": (8,12),  "female": (4,8)},
                      "beginner":  {"male": (12,20), "female": (6,12)},
                      "intermediate": {"male": (18,30), "female": (10,18)},
                      "advanced":  {"male": (28,44), "female": (16,28)}},
        "legs":      {"untrained": {"male": (8,14),  "female": (6,10)},
                      "beginner":  {"male": (12,20), "female": (8,14)},
                      "intermediate": {"male": (20,32), "female": (12,22)},
                      "advanced":  {"male": (30,50), "female": (18,34)}},
        "shoulders": {"untrained": {"male": (4,8),   "female": (2,5)},
                      "beginner":  {"male": (6,12),  "female": (3,8)},
                      "intermediate": {"male": (10,18), "female": (6,12)},
                      "advanced":  {"male": (18,28), "female": (10,18)}},
        "biceps":    {"untrained": {"male": (5,8),   "female": (2,5)},
                      "beginner":  {"male": (8,14),  "female": (4,8)},
                      "intermediate": {"male": (12,20), "female": (6,12)},
                      "advanced":  {"male": (18,30), "female": (10,18)}},
        "triceps":   {"untrained": {"male": (5,8),   "female": (2,5)},
                      "beginner":  {"male": (7,12),  "female": (3,7)},
                      "intermediate": {"male": (10,18), "female": (5,11)},
                      "advanced":  {"male": (16,26), "female": (9,17)}},
        "core":      {"untrained": {"male": (4,8),   "female": (2,5)},
                      "beginner":  {"male": (6,12),  "female": (3,7)},
                      "intermediate": {"male": (10,18), "female": (5,11)},
                      "advanced":  {"male": (16,26), "female": (9,17)}},
        "full_body": {"untrained": {"male": (6,10),  "female": (3,6)},
                      "beginner":  {"male": (8,14),  "female": (4,8)},
                      "intermediate": {"male": (12,22), "female": (6,14)},
                      "advanced":  {"male": (20,34), "female": (12,22)}},
    },
    "machine": {
        "chest":     {"untrained": {"male": (20,35),  "female": (10,20)},
                      "beginner":  {"male": (30,50),  "female": (15,28)},
                      "intermediate": {"male": (48,78), "female": (26,48)},
                      "advanced":  {"male": (76,120), "female": (44,72)}},
        "back":      {"untrained": {"male": (25,40),  "female": (14,24)},
                      "beginner":  {"male": (36,56),  "female": (20,36)},
                      "intermediate": {"male": (54,84), "female": (30,54)},
                      "advanced":  {"male": (82,130), "female": (50,82)}},
        "legs":      {"untrained": {"male": (30,55),  "female": (20,38)},
                      "beginner":  {"male": (50,85),  "female": (30,56)},
                      "intermediate": {"male": (82,130), "female": (52,86)},
                      "advanced":  {"male": (128,200),"female": (76,128)}},
        "shoulders": {"untrained": {"male": (14,28),  "female": (8,16)},
                      "beginner":  {"male": (24,44),  "female": (12,26)},
                      "intermediate": {"male": (40,68), "female": (22,42)},
                      "advanced":  {"male": (64,100), "female": (36,66)}},
    },
    "cable": {
        "chest":     {"untrained": {"male": (10,20),  "female": (5,12)},
                      "beginner":  {"male": (16,30),  "female": (8,18)},
                      "intermediate": {"male": (26,44), "female": (14,28)},
                      "advanced":  {"male": (40,64),  "female": (24,42)}},
        "back":      {"untrained": {"male": (15,26),  "female": (8,16)},
                      "beginner":  {"male": (22,38),  "female": (12,24)},
                      "intermediate": {"male": (34,56), "female": (18,36)},
                      "advanced":  {"male": (54,86),  "female": (32,56)}},
        "shoulders": {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (30,50),  "female": (18,32)}},
        "biceps":    {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (28,46),  "female": (16,30)}},
        "triceps":   {"untrained": {"male": (8,14),   "female": (4,8)},
                      "beginner":  {"male": (12,20),  "female": (6,12)},
                      "intermediate": {"male": (16,28), "female": (9,18)},
                      "advanced":  {"male": (24,40),  "female": (14,26)}},
        "core":      {"untrained": {"male": (8,16),   "female": (4,9)},
                      "beginner":  {"male": (12,22),  "female": (6,13)},
                      "intermediate": {"male": (18,32), "female": (10,20)},
                      "advanced":  {"male": (28,46),  "female": (16,30)}},
        "legs":      {"untrained": {"male": (15,30),  "female": (10,20)},
                      "beginner":  {"male": (26,46),  "female": (16,30)},
                      "intermediate": {"male": (40,68), "female": (24,44)},
                      "advanced":  {"male": (64,100), "female": (38,66)}},
    },
    "kettlebell": {
        "full_body": {"untrained": {"male": (8,12),  "female": (4,8)},
                      "beginner":  {"male": (12,20), "female": (6,12)},
                      "intermediate": {"male": (20,32), "female": (10,20)},
                      "advanced":  {"male": (28,48), "female": (16,32)}},
        "legs":      {"untrained": {"male": (8,16),  "female": (6,10)},
                      "beginner":  {"male": (14,24), "female": (8,16)},
                      "intermediate": {"male": (22,36), "female": (14,24)},
                      "advanced":  {"male": (32,56), "female": (20,36)}},
    },
}

_BODYWEIGHT_PROGRESSIONS = {
    "chest":     "Bodyweight · Progress: easier (incline) → standard → decline → archer push-up → single-arm",
    "back":      "Bodyweight · Progress: band-assisted → negative → full pull-up/chin-up → weighted",
    "legs":      "Bodyweight · Progress: squat → split squat → Bulgarian split squat → pistol squat",
    "core":      "Bodyweight · Increase difficulty by slowing tempo or adding pauses",
    "shoulders": "Bodyweight · Add resistance band or light dumbbell when movement feels easy",
    "biceps":    "Bodyweight (band or towel row) · Add resistance band to increase difficulty",
    "triceps":   "Bodyweight · Progress: incline → flat → decline dips / push-up variations",
    "full_body": "Bodyweight · Increase reps first, then add load (weighted vest / resistance band)",
    "cardio":    "Effort-based · Increase duration or intensity (speed, incline) each week",
}


def _primary_muscle_group(ex: dict) -> str:
    """Map an exercise's primary muscle to a weight-guide key."""
    primary = [m.lower() for m in ex.get("primary_muscles", [])]
    for m in primary:
        if "chest" in m or "pectoral" in m:    return "chest"
        if "lat" in m or "back" in m or "trap" in m: return "back"
        if "quad" in m or "hamstring" in m or "glute" in m or "calf" in m or "leg" in m: return "legs"
        if "shoulder" in m or "deltoid" in m:  return "shoulders"
        if "bicep" in m:                        return "biceps"
        if "tricep" in m:                       return "triceps"
        if "abdominal" in m or "core" in m or "abs" in m: return "core"
    return "full_body"


def _get_weight_range(ex: dict, strength_level: str, gender: str) -> str:
    """Return a starter weight range string or bodyweight progression note."""
    eq = ex.get("equipment", "bodyweight").lower()
    cat = ex.get("category", "strength").lower()

    # Cardio and timed exercises don't need weight
    if cat == "cardio":
        return "Effort-based — see intensity note"

    # Bodyweight exercises: return progression ladder
    if eq in ("bodyweight", "other"):
        muscle = _primary_muscle_group(ex)
        return _BODYWEIGHT_PROGRESSIONS.get(muscle, "Bodyweight · Add band/vest to progress")

    # Map equipment aliases
    eq_key = eq
    if eq in ("dumbbells", "dumbbell"):      eq_key = "dumbbell"
    elif eq in ("barbell",):                  eq_key = "barbell"
    elif eq in ("machine",):                  eq_key = "machine"
    elif eq in ("cable", "cables"):           eq_key = "cable"
    elif eq in ("kettlebell", "kettlebells"): eq_key = "kettlebell"
    elif eq in ("bands", "resistance_bands"): return "Light–heavy band · choose resistance that makes last 2 reps challenging"
    else:                                     return "Moderate resistance · adjust to feel challenging by last rep"

    muscle = _primary_muscle_group(ex)
    gender_key = "female" if str(gender).lower() in ("female", "f", "woman") else "male"
    lvl = strength_level if strength_level in ("untrained", "beginner", "intermediate", "advanced") else "beginner"

    equip_data = _WEIGHT_GUIDE.get(eq_key, {})
    # Try exact muscle, then fall back to full_body or chest
    muscle_data = equip_data.get(muscle) or equip_data.get("full_body") or equip_data.get("chest")
    if not muscle_data:
        return "Moderate weight · adjust so last 2 reps are challenging"

    level_data = muscle_data.get(lvl, {})
    lo, hi = level_data.get(gender_key, (0, 0))
    if lo == 0:
        return "Moderate weight · adjust so last 2 reps are challenging"

    unit_note = " per hand" if eq_key == "dumbbell" else ""
    return f"{lo}–{hi} kg{unit_note} · adjust so last 2 reps are hard but form stays perfect"


# ── Ayurvedic Rest Day Recovery ───────────────────────────────────────────────

_REST_DAY_RECOVERY = {
    "vata": {
        "title": "Vata Rest Day — Ground & Restore",
        "activities": [
            "Abhyanga (warm sesame oil self-massage) — 15–20 min, long slow strokes toward the heart",
            "Restorative yoga — Child's Pose, Supta Baddha Konasana, Legs-Up-The-Wall (5 min each)",
            "Nadi Shodhana pranayama — 10 min alternate nostril breathing to calm the nervous system",
            "Warm herbal bath with calming herbs (Ashwagandha, Brahmi, or Jatamansi)",
            "Light walk (20–30 min) in nature, preferably midday when Vata is naturally pacified",
        ],
        "nutrition_note": "Warm, oily, nourishing foods. Ghee, warm milk, root vegetables. Avoid cold, raw, or dry foods on rest days.",
        "sleep_note": "Aim for 8–9 hrs. Apply warm oil to feet (Padabhyanga) before bed. Asleep by 10pm.",
        "ayurvedic_note": "Vata recovers through stillness and warmth — resist the urge to stay active on rest days.",
    },
    "pitta": {
        "title": "Pitta Rest Day — Cool & Release",
        "activities": [
            "Moon salutation sequence — 3–5 rounds, slow and cooling (opposite of Sun Salutation's heat)",
            "Coconut oil self-massage — focus on scalp and soles of feet to dissipate excess heat",
            "Sheetali pranayama (cooling breath through rolled tongue) — 10 min",
            "Swimming or gentle water activity — Pitta is cooled by water",
            "Evening walk at sunset — avoid direct midday sun on rest days",
        ],
        "nutrition_note": "Cooling, sweet, bitter foods. Coconut water, pomegranate, fresh coriander, mint. Avoid spicy, sour, salty foods.",
        "sleep_note": "Aim for 7–8 hrs. Keep bedroom cool (below 22°C). Avoid screen heat before bed.",
        "ayurvedic_note": "Pitta's drive to push harder on rest days is the enemy — active recovery should feel cooling, not challenging.",
    },
    "kapha": {
        "title": "Kapha Rest Day — Energise & Stimulate",
        "activities": [
            "Brisk walk — minimum 30 min at vigorous pace (Kapha needs movement even on rest days)",
            "Dry brushing (Garshana with raw silk gloves) — stimulates lymphatic circulation",
            "Kapalabhati pranayama — 5–10 min energising breath (fires up Agni and reduces Ama)",
            "Sun salutations — 5 rounds at moderate pace to maintain metabolic rate",
            "Avoid all napping — daytime sleep strongly aggravates Kapha",
        ],
        "nutrition_note": "Light, warm, spiced foods. Ginger-lemon tea, light dal, steamed vegetables. Avoid heavy, oily, cold, or sweet foods.",
        "sleep_note": "7 hrs maximum. Wake before 6am — the Kapha period (6-10am) brings heaviness if you sleep through it.",
        "ayurvedic_note": "Kapha's rest day is still active — complete stillness leads to lethargy and weight gain for this type.",
    },
}


# ── Exercise filtering ────────────────────────────────────────────────────────

def filter_exercises(user_profile, gym_prefs, exercises):
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}

    level_map = {
        "beginner":     ["beginner"],
        "intermediate": ["beginner", "intermediate"],
        "advanced":     ["beginner", "intermediate", "advanced"],
    }
    user_level = user_profile.get("fitness_level", "beginner") or "beginner"
    allowed_levels = level_map.get(user_level, ["beginner"])

    # Beginners doing bodyweight-only: also allow intermediate bodyweight exercises
    # so pull/push days don't end up empty (chin-ups, rows are marked intermediate)
    if user_level == "beginner" and is_bodyweight_only:
        allowed_levels = ["beginner", "intermediate"]

    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    gym_goal = gym_prefs.get("gym_goal", "general_fitness")
    injuries = set(user_profile.get("injuries_or_limitations") or [])
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)

    scored = []
    for ex in exercises:
        eq = ex.get("equipment", "bodyweight").lower()
        if eq not in available_eq and eq != "bodyweight":
            continue
        if ex.get("level", "intermediate") not in allowed_levels:
            continue
        if not ex.get("goal_suitability", {}).get(gym_goal, False):
            continue
        if injuries.intersection(set(ex.get("contraindications", []))):
            continue
        if is_pregnant and not ex.get("pregnancy_safe", False):
            continue

        score = 0
        dosha_suit = ex.get("dosha_suitability", {}).get(dominant_dosha, "moderate")
        if dosha_suit == "good":     score += 2
        elif dosha_suit == "moderate": score += 1
        elif dosha_suit == "avoid":  score -= 2
        if user_level == "beginner" and ex.get("level") == "beginner":
            score += 1
        scored.append((score, ex))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [ex for _, ex in scored[:200]]


# ── Muscle group split ────────────────────────────────────────────────────────

def split_by_muscle_group(exercises):
    split = {k: [] for k in ["chest", "triceps", "biceps", "back", "shoulders", "legs", "core", "full_body", "cardio"]}
    for ex in exercises:
        if ex.get("category") == "cardio":
            split["cardio"].append(ex)
            continue
        primary = [m.lower() for m in ex.get("primary_muscles", [])]
        assigned = False
        for m in primary:
            if "chest" in m or "pectoral" in m:
                split["chest"].append(ex); assigned = True; break
            elif "tricep" in m:
                split["triceps"].append(ex); assigned = True; break
            elif "bicep" in m:
                split["biceps"].append(ex); assigned = True; break
            elif m in ["lats", "middle back", "lower back", "traps", "back"]:
                split["back"].append(ex); assigned = True; break
            elif "shoulder" in m or "deltoid" in m:
                split["shoulders"].append(ex); assigned = True; break
            elif m in ["quadriceps", "hamstrings", "glutes", "calves", "adductors", "abductors", "legs", "quad", "calf"]:
                split["legs"].append(ex); assigned = True; break
            elif "abdominal" in m or "core" in m or "abs" in m or "hip flex" in m:
                split["core"].append(ex); assigned = True; break
        if not assigned:
            split["full_body"].append(ex)
    return split


# ── Weekly schedule builder ───────────────────────────────────────────────────

def _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level):
    if is_bodyweight_only and fitness_level == "beginner":
        if workout_days <= 2:
            return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
        elif workout_days == 3:
            return ["full_body", "rest", "full_body", "rest", "full_body", "rest", "rest"]
        else:
            return ["full_body", "rest", "full_body", "rest", "full_body", "core_cardio", "rest"]

    if workout_days == 2:
        return ["full_body", "rest", "full_body", "rest", "rest", "rest", "rest"]
    elif workout_days == 3:
        return ["push", "rest", "pull", "rest", "legs_core", "rest", "rest"]
    elif workout_days == 4:
        return ["chest_triceps", "rest", "back_biceps", "legs", "rest", "shoulders_core", "rest"]
    elif workout_days == 5:
        return ["chest", "back", "rest", "legs", "shoulders_arms", "core_cardio", "rest"]
    elif workout_days == 6:
        return ["chest_triceps", "back_biceps", "legs", "shoulders", "arms", "core_cardio", "rest"]
    return ["full_body", "full_body", "full_body", "rest", "rest", "rest", "rest"]


def _focus_to_keys(focus):
    if "full_body" in focus:        return ["full_body", "chest", "back", "legs", "core"]
    elif "push" in focus:           return ["chest", "shoulders", "triceps"]
    elif "pull" in focus:           return ["back", "biceps"]
    elif focus == "legs":           return ["legs"]
    elif "legs_core" in focus:      return ["legs", "core"]
    elif "chest_triceps" in focus:  return ["chest", "triceps"]
    elif "back_biceps" in focus:    return ["back", "biceps"]
    elif focus == "chest":          return ["chest"]
    elif focus == "back":           return ["back"]
    elif "shoulders_core" in focus: return ["shoulders", "core"]
    elif "shoulders_arms" in focus: return ["shoulders", "biceps", "triceps"]
    elif focus == "shoulders":      return ["shoulders"]
    elif "arms" in focus:           return ["biceps", "triceps"]
    elif "core_cardio" in focus:    return ["core", "cardio"]
    return ["full_body"]


# ── Exercise selection ────────────────────────────────────────────────────────

def _deterministic_select(pool, n, seed_key):
    seed = int(hashlib.md5(seed_key.encode()).hexdigest(), 16) % (2**31)
    rng = random.Random(seed)
    unique_pool = list({ex["id"]: ex for ex in pool}.values())
    rng.shuffle(unique_pool)
    return unique_pool[:n]


def _target_count(duration, goal):
    if duration <= 20:   base = 3
    elif duration <= 30: base = 4
    else:                base = 5
    if goal == "strength":
        base = min(base, 4)
    return base


# ── Day plan builder ──────────────────────────────────────────────────────────

def build_day_plan(day_num, day_name, focus, muscle_split, gym_prefs, user_profile,
                   week=1, user_id="default", strength_level="beginner", gender="male",
                   dosha="vata"):
    if focus == "rest":
        recovery = _REST_DAY_RECOVERY.get(dosha, _REST_DAY_RECOVERY["vata"])
        return {
            "day": day_num, "day_name": day_name,
            "focus": "Rest & Recovery", "type": "recovery",
            "warmup": [], "main_workout": [], "cooldown": [],
            "estimated_duration_minutes": 0, "calories_burned_estimate": 0,
            "rest_day_recovery": recovery,
        }

    duration = gym_prefs.get("workout_duration_minutes", 45)
    goal = gym_prefs.get("gym_goal", "general_fitness")
    level = user_profile.get("fitness_level", "beginner") or "beginner"
    if level not in ["beginner", "intermediate", "advanced"]:
        level = "beginner"

    target = _target_count(duration, goal)
    rx = _get_goal_prescription(goal, week)

    pool = []
    for k in _focus_to_keys(focus):
        pool.extend(muscle_split.get(k, []))

    if len(pool) < 3:
        pool = muscle_split.get("full_body", [])
    if len(pool) < 3:
        pool = [ex for group in muscle_split.values() for ex in group]

    seed_key = f"{user_id}-{focus}-d{day_num}-w{week}"
    selected = _deterministic_select(pool, target, seed_key)

    main_workout = []
    total_cals = 0
    for ex in selected:
        sets = rx["sets"]
        reps = rx["reps"]
        rest = rx["rest_seconds"]

        try:
            parts = str(reps).split("-")
            reps_val = sum(int(p) for p in parts if p.isdigit()) / max(len(parts), 1)
        except Exception:
            reps_val = 10

        cpm = ex.get("calories_per_minute", 5.0)
        time_per_rep = 2 if ex.get("category") == "cardio" else 4
        total_cals += (sets * reps_val * time_per_rep / 60.0) * cpm

        main_workout.append({
            "exercise_id": ex.get("id"),
            "exercise_name": ex.get("name"),
            "category": ex.get("category", "strength"),
            "primary_muscles": ex.get("primary_muscles", []),
            "equipment": ex.get("equipment", "bodyweight"),
            "sets": sets,
            "reps": reps,
            "rest_seconds": rest,
            "weight_range": _get_weight_range(ex, strength_level, gender),
            "week_note": rx.get("note", ""),
            "notes": ex.get("modification", ""),
            "instructions": ex.get("instructions", []),
        })

    return {
        "day": day_num,
        "day_name": day_name,
        "focus": focus.replace("_", " ").title(),
        "type": "cardio" if "cardio" in focus else "strength",
        "warmup": _warmup_for(focus),
        "main_workout": main_workout,
        "cooldown": _cooldown_for(focus),
        "estimated_duration_minutes": duration,
        "calories_burned_estimate": int(total_cals + 20),
    }


# ── Ayurvedic tips ────────────────────────────────────────────────────────────

def get_ayurvedic_tips(dosha):
    if dosha == "pitta":
        return {
            "best_time_to_workout": "Early morning or evening (avoid midday heat)",
            "pre_workout": "Coconut water or cool water; avoid working out in anger or stress",
            "post_workout": "Cool shower, coconut water; avoid overheating",
            "recovery": "Moon salutation on rest days; cultivate non-competitive mindset",
        }
    elif dosha == "kapha":
        return {
            "best_time_to_workout": "6–10am (Kapha time — exercise fights morning heaviness)",
            "pre_workout": "Dry ginger tea; no heavy breakfast before workout",
            "post_workout": "Stimulating pranayama (Kapalabhati), light protein meal",
            "recovery": "Stay active on rest days — minimum 30-min walk; avoid napping after workout",
        }
    else:
        return {
            "best_time_to_workout": "10am–2pm (avoid early-morning cold and late-night stimulation)",
            "pre_workout": "Warm sesame oil self-massage (Abhyanga); eat a small warm meal 1 hr before",
            "post_workout": "Rest 10 min; warm water; avoid cold shower immediately after",
            "recovery": "Prioritize 8 hrs sleep; warm oil massage on rest days; avoid over-exertion",
        }


# ── Vyayama Shakti (classical exercise-capacity principle) ────────────────────

def _vyayama_shakti(dosha: str, age, strength_level: str) -> dict:
    """Classical Vyayama (exercise) dosage principle — Charaka Sutrasthana 7.
    Exercise to Ardhabala (half of maximum capacity); the sign to stop is sweating
    on forehead/nose/joints with onset of mouth-breathing. Over-exercise (Ativyayama)
    depletes Ojas and aggravates Vata."""
    try:
        age_i = int(age or 30)
    except (TypeError, ValueError):
        age_i = 30
    if age_i >= 60 or dosha == "vata" or strength_level == "beginner":
        capacity = ("Keep intensity well within Ardhabala — work to roughly half capacity and stop "
                    "at the first forehead sweat. Vata constitution, beginner strength, and older age "
                    "all lower exercise tolerance; over-exertion here directly depletes Ojas.")
    elif dosha == "kapha" and strength_level in ("intermediate", "advanced") and age_i < 50:
        capacity = ("You have higher Vyayama Shakti — you may work up toward the Ardhabala ceiling with "
                    "good sustained volume. Kapha specifically benefits from exercising until a genuine sweat breaks.")
    else:
        capacity = ("Moderate capacity — work to about half-strength. Pitta types must avoid exercising in "
                    "heat or with a competitive mindset, which pushes past Ardhabala into Pitta aggravation.")
    return {
        "principle": ("Exercise should be performed only to Ardhabala — half of one's maximum capacity "
                      "(Charaka Sutrasthana 7). The classical signal to STOP is sweating on the forehead, "
                      "nose, and joints together with the onset of mouth-breathing."),
        "your_capacity": capacity,
        "signs_adequate": "Sweat on forehead, nose and armpits; lightness in the body; comfortably increased breathing.",
        "signs_overexertion": ("Breathlessness, dizziness, tremor, excessive thirst, joint pain or cough mark "
                               "Ativyayama (over-exercise) — reduce intensity immediately."),
        "bala_note": ("Exercise capacity (Bala) here is estimated from fitness level and age as a practical proxy — "
                      "not a full classical Bala Pareeksha, which also weighs Sara, Samhanana, Satmya, Sattva, and season."),
    }


# ── Main entry point ──────────────────────────────────────────────────────────

def generate_gym_plan(user_profile, gym_prefs, gym_exercises_db=None):
    ge = gym_exercises_db if gym_exercises_db is not None else gym_exercises
    filtered = filter_exercises(user_profile, gym_prefs, ge)
    muscle_split = split_by_muscle_group(filtered)

    workout_days = gym_prefs.get("workout_days_per_week", 4)
    available_eq = {eq.lower() for eq in gym_prefs.get("available_equipment", ["bodyweight"])}
    available_eq.add("bodyweight")
    is_bodyweight_only = available_eq <= {"bodyweight", "bands", "jump_rope"}
    fitness_level = user_profile.get("fitness_level", "beginner") or "beginner"
    strength_level = gym_prefs.get("strength_level", fitness_level)
    gender = user_profile.get("gender", "male") or "male"

    schedule_focus = _build_weekly_schedule(workout_days, is_bodyweight_only, fitness_level)
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    user_id = str(user_profile.get("id") or user_profile.get("_id") or "default")
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    goal = gym_prefs.get("gym_goal", "general_fitness")

    four_week_plan = []
    for week in range(1, 5):
        week_days = [
            build_day_plan(
                i + 1, days_of_week[i], focus, muscle_split, gym_prefs, user_profile,
                week=week, user_id=user_id, strength_level=strength_level,
                gender=gender, dosha=dominant_dosha,
            )
            for i, focus in enumerate(schedule_focus)
        ]
        four_week_plan.append({
            "week": week,
            "theme": {1: "Foundation", 2: "Volume Build", 3: "Intensity Peak", 4: "Deload & Reset"}[week],
            "prescription": _get_goal_prescription(goal, week),
            "days": week_days,
        })

    disclaimer = (
        "PREGNANCY DISCLAIMER: Consult your doctor before starting any exercise program during pregnancy. "
        "Avoid high impact, twisting, and heavy lifting."
        if is_pregnant else
        "This plan is for general wellness guidance only. Consult a physician before beginning any new exercise program."
    )

    return {
        "plan_id": f"gym_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "bmi_category": user_profile.get("bmi_category", "unknown"),
            "fitness_level": fitness_level,
            "strength_level": strength_level,
            "gym_goal": goal,
            "workout_days": workout_days,
            "duration_per_session": gym_prefs.get("workout_duration_minutes", 45),
        },
        "weekly_schedule": four_week_plan[0]["days"],
        "four_week_plan": four_week_plan,
        "ayurvedic_tips": get_ayurvedic_tips(dominant_dosha),
        "vyayama_shakti": _vyayama_shakti(dominant_dosha, user_profile.get("age"), strength_level),
        "progressive_overload_guide": {
            "week_1": _GOAL_WEEKS[goal][0]["note"] if goal in _GOAL_WEEKS else "",
            "week_2": _GOAL_WEEKS[goal][1]["note"] if goal in _GOAL_WEEKS else "",
            "week_3": _GOAL_WEEKS[goal][2]["note"] if goal in _GOAL_WEEKS else "",
            "week_4": _GOAL_WEEKS[goal][3]["note"] if goal in _GOAL_WEEKS else "",
        },
        "disclaimer": disclaimer,
    }
