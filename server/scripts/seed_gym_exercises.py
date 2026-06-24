import json
import urllib.request
from collections import defaultdict
from pathlib import Path

URL = "https://raw.githubusercontent.com/yuhonas/free-exercise-db/main/dist/exercises.json"

# Setup output path
BASE_DIR = Path(__file__).resolve().parent.parent
OUTPUT_DIR = BASE_DIR / "data" / "knowledge_base"
OUTPUT_FILE = OUTPUT_DIR / "gym_exercises.json"

def get_category(exercise):
    body_part = exercise.get("bodyPart", "").lower()
    name = exercise.get("name", "").lower()
    
    if body_part == "cardio":
        return "cardio"
    if "stretch" in name or "yoga" in name:
        return "stretching"
    if "jump" in name or "plyo" in name or "bound" in name:
        return "plyometrics"
    return "strength"

def map_equipment(eq):
    mapping = {
        "body only": "bodyweight",
        "dumbbell": "dumbbell",
        "barbell": "barbell",
        "cable": "cable",
        "machine": "machine",
        "kettlebells": "kettlebell",
        "bands": "bands",
        "foam roll": "bodyweight",
        "exercise ball": "other",
        "medicine ball": "other",
        "e-z curl bar": "barbell"
    }
    return mapping.get(eq.lower(), "other") if eq else "other"

def get_dosha_suitability(category, equipment):
    dosha = {"vata": "moderate", "pitta": "moderate", "kapha": "moderate"}
    is_powerlifting = (equipment == "barbell" and category == "strength")
    
    # VATA (needs grounding, warmth, avoid excessive movement)
    if category in ["plyometrics", "cardio"]:
        dosha["vata"] = "avoid"
    elif is_powerlifting:
        dosha["vata"] = "moderate"
    elif category in ["strength", "stretching"]:
        dosha["vata"] = "good"
        
    # PITTA (needs cooling, non-competitive, moderate intensity)
    if is_powerlifting:
        dosha["pitta"] = "avoid"
    elif category == "plyometrics":
        dosha["pitta"] = "moderate"
    elif category in ["stretching", "cardio", "strength"]:
        dosha["pitta"] = "good"
        
    # KAPHA (needs energizing, high intensity, dynamic)
    if category == "stretching":
        dosha["kapha"] = "avoid"
    elif category in ["plyometrics", "cardio"]:
        dosha["kapha"] = "good"
    elif category == "strength":
        dosha["kapha"] = "good"
        
    return dosha

def get_goal_suitability(category, equipment):
    return {
        "fat_loss": True,
        "muscle_gain": category in ["strength", "powerlifting", "olympic_weightlifting"],
        "endurance": category in ["cardio", "plyometrics", "strength"],
        "strength": category in ["strength", "powerlifting", "olympic_weightlifting"],
        "general_fitness": True
    }

# Name-based biomechanical contraindication rules (movement pattern → injuries).
# Keeps the gym KB's contraindications complete so the injury filter works for every
# exercise — not just those whose muscle tag happened to trigger a rule.
_NAME_CONTRA_RULES = [
    (("crunch", "sit-up", "sit up", "situp", "abdominal", "oblique", "russian twist",
      "v-up", "leg raise", "knee raise", "hollow", "toe touch", "heel touch",
      "flutter kick", "scissor", "jackknife", "dragon flag", "windshield"),
     ["herniated_disc", "lower_back_pain", "pregnancy"]),
    (("plank", "mountain climber", "dead bug", "bird dog"), ["lower_back_pain", "pregnancy"]),
    (("deadlift", "good morning", "bent over", "bent-over", "t-bar", "rack pull",
      "hyperextension", "back extension", "romanian", "rdl", "pendlay"),
     ["herniated_disc", "lower_back_pain"]),
    (("squat", "lunge", "leg press", "step-up", "step up", "leg extension", "hack",
      "split squat", "pistol", "wall sit", "sissy", "leg curl"),
     ["bad_knee", "knee_replacement"]),
    (("overhead", "shoulder press", "military", "arnold", "upright row", "lateral raise",
      "front raise", "push press", "snatch", "jerk"), ["rotator_cuff", "shoulder_injury"]),
    (("bench press", "chest press", "push-up", "push up", "pushup", "dip", "chest fly",
      "pec deck", "incline press", "decline press", "fly"), ["rotator_cuff", "shoulder_injury"]),
    (("pull-up", "pull up", "pullup", "chin-up", "chin up", "pulldown", "row", "pullover"),
     ["shoulder_injury"]),
    (("jump", "box ", "burpee", "plyo", "sprint", "skater", "hop", "bound",
      "kettlebell swing", "thruster", "wall ball", "high knee", "jumping"),
     ["bad_knee", "bad_ankle", "heart_disease", "pregnancy"]),
    (("neck", "shrug"), ["cervical_spondylosis", "neck_injury"]),
    (("calf", "calve", "tibia"), ["bad_ankle"]),
    (("wrist", "forearm", "reverse curl"), ["wrist_injury"]),
    (("curl", "tricep", "skullcrusher", "skull crusher", "pushdown", "kickback"), ["elbow_injury"]),
    (("adductor", "abductor", "groin", "hip thrust", "glute"), ["hip_injury"]),
]
_VALSALVA_KEYS = ("deadlift", "squat", "leg press", "overhead", "military", "bench press",
                  "clean", "snatch", "jerk", "thruster")


def get_contraindications(name, target, secondary, equipment, category):
    contra = set()
    muscles_str = " ".join([target] + secondary).lower()
    hay = (name + " " + muscles_str).lower()

    # Muscle-based (original)
    if "lower back" in muscles_str or "spine" in muscles_str or "waist" in muscles_str:
        contra.update(["herniated_disc", "lower_back_pain", "osteoporosis"])
    if "quad" in muscles_str or "hamstring" in muscles_str or "knee" in muscles_str:
        contra.update(["bad_knee", "knee_replacement"])
    if "shoulder" in muscles_str or "deltoid" in muscles_str:
        contra.update(["shoulder_injury", "rotator_cuff"])
    if "neck" in muscles_str or "cervical" in muscles_str:
        contra.update(["neck_injury", "cervical_spondylosis"])

    # Name-based movement patterns
    for keys, contras in _NAME_CONTRA_RULES:
        if any(k in hay for k in keys):
            contra.update(contras)

    # Valsalva / heavy loading → blood pressure & cardiac
    if (equipment == "barbell" and category == "strength") or any(k in hay for k in _VALSALVA_KEYS):
        contra.update(["hypertension", "heart_disease"])
    if category == "plyometrics":
        contra.update(["bad_knee", "bad_ankle", "osteoporosis", "pregnancy"])

    return sorted(contra)

def get_cpm(category, equipment):
    if category == "cardio": return 10.0
    if category == "plyometrics": return 9.0
    if equipment == "barbell" and category == "strength": return 6.0
    if category == "strength":
        if equipment in ["dumbbell", "kettlebell"]: return 7.0
        return 5.0
    if category == "stretching": return 2.5
    return 5.0

def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    print(f"Downloading exercises from {URL}...")
    req = urllib.request.Request(URL, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response:
            data = json.loads(response.read().decode('utf-8'))
    except Exception as e:
        print(f"Failed to download: {e}")
        return
        
    print(f"Downloaded {len(data)} exercises. Transforming to Ayurvedic schema...")
    
    transformed = []
    
    # Stats
    stats_equipment = defaultdict(int)
    stats_level = defaultdict(int)
    stats_category = defaultdict(int)
    stats_dosha = {"vata": 0, "pitta": 0, "kapha": 0}
    
    for ex in data:
        category = get_category(ex)
        equipment = map_equipment(ex.get("equipment", ""))
        
        name = ex.get("name", "").lower()
        if "beginner" in name:
            level = "beginner"
        elif "advanced" in name or "expert" in name:
            level = "advanced"
        else:
            level = "intermediate"
            
        raw_eq = str(ex.get("equipment") or "").lower()
        raw_mech = str(ex.get("mechanic") or "").lower()
        
        if raw_eq == "body only":
            if category == "strength" and raw_mech == "compound":
                pass
            elif category == "stretching":
                level = "beginner"
            elif category == "cardio":
                level = "beginner"
            elif category == "strength" and raw_mech == "isolation":
                level = "beginner"
            
        dosha = get_dosha_suitability(category, equipment)
        
        primary = ex.get("primaryMuscles", [])
        secondary = ex.get("secondaryMuscles", [])
        
        item = {
            "id": ex.get("id"),
            "name": ex.get("name", "").title(),
            "category": category,
            "equipment": equipment,
            "level": level,
            "primary_muscles": primary,
            "secondary_muscles": secondary,
            "instructions": ex.get("instructions", []),
            "sets_reps": {
                "beginner":      {"sets": 3, "reps": "12-15", "rest_seconds": 90},
                "intermediate":  {"sets": 4, "reps": "10-12", "rest_seconds": 75},
                "advanced":      {"sets": 5, "reps": "6-10",  "rest_seconds": 60}
            },
            "dosha_suitability": dosha,
            "goal_suitability": get_goal_suitability(category, equipment),
            "contraindications": get_contraindications(ex.get("name", ""), primary[0] if primary else "", secondary, equipment, category),
            "calories_per_minute": get_cpm(category, equipment),
            "modification": "Reduce weight or switch to bodyweight if form breaks down."
        }
        
        transformed.append(item)
        
        # Update stats
        stats_equipment[equipment] += 1
        stats_level[level] += 1
        stats_category[category] += 1
        if dosha["vata"] == "good": stats_dosha["vata"] += 1
        if dosha["pitta"] == "good": stats_dosha["pitta"] += 1
        if dosha["kapha"] == "good": stats_dosha["kapha"] += 1

    # Save
    with open(OUTPUT_FILE, "w", encoding="utf-8") as f:
        json.dump(transformed, f, indent=2, ensure_ascii=False)
        
    print("\n--- SEEDING COMPLETE ---")
    print(f"Total exercises seeded: {len(transformed)}")
    print(f"By equipment: {dict(stats_equipment)}")
    print(f"By level: {dict(stats_level)}")
    print(f"By category: {dict(stats_category)}")
    print(f"By dosha suitability (good count): {stats_dosha}")
    print(f"Saved to: {OUTPUT_FILE}")

if __name__ == "__main__":
    main()
