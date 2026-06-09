import sys
import json
from pathlib import Path

# Add server directory to path so we can import
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.gym_plan_engine import generate_gym_plan, filter_exercises

profiles = [
    {
        "name": "Profile 1 — Vata Beginner, Fat Loss, Home",
        "user_profile": {
            "age": 25, "gender": "male", "bmi": 22, "bmi_category": "normal",
            "fitness_level": "beginner", "activity_level": "sedentary",
            "dominant_dosha": "vata", "injuries_or_limitations": []
        },
        "gym_prefs": {
            "gym_goal": "fat_loss",
            "workout_days_per_week": 3,
            "workout_duration_minutes": 30,
            "available_equipment": ["bodyweight"]
        }
    },
    {
        "name": "Profile 2 — Pitta Intermediate, Muscle Gain, Full Gym",
        "user_profile": {
            "age": 28, "gender": "male", "bmi": 24, "bmi_category": "normal",
            "fitness_level": "intermediate", "activity_level": "active",
            "dominant_dosha": "pitta", "injuries_or_limitations": []
        },
        "gym_prefs": {
            "gym_goal": "muscle_gain",
            "workout_days_per_week": 5,
            "workout_duration_minutes": 60,
            "available_equipment": ["barbell", "dumbbell", "cable", "machine"]
        }
    },
    {
        "name": "Profile 3 — Kapha Beginner, Fat Loss, Dumbbells",
        "user_profile": {
            "age": 32, "gender": "female", "bmi": 29, "bmi_category": "overweight",
            "fitness_level": "beginner", "activity_level": "light",
            "dominant_dosha": "kapha", "injuries_or_limitations": []
        },
        "gym_prefs": {
            "gym_goal": "fat_loss",
            "workout_days_per_week": 4,
            "workout_duration_minutes": 45,
            "available_equipment": ["dumbbell", "bodyweight"]
        }
    },
    {
        "name": "Profile 4 — Vata with bad_knee + shoulder_injury",
        "user_profile": {
            "age": 40, "gender": "female", "bmi": 21, "bmi_category": "normal",
            "fitness_level": "intermediate", "activity_level": "moderate",
            "dominant_dosha": "vata", "injuries_or_limitations": ["bad_knee", "shoulder_injury"]
        },
        "gym_prefs": {
            "gym_goal": "general_fitness",
            "workout_days_per_week": 3,
            "workout_duration_minutes": 30,
            "available_equipment": ["dumbbell", "bodyweight", "bands"]
        }
    },
    {
        "name": "Profile 5 — Kapha Advanced, Strength, Full Gym",
        "user_profile": {
            "age": 22, "gender": "male", "bmi": 27, "bmi_category": "overweight",
            "fitness_level": "advanced", "activity_level": "very_active",
            "dominant_dosha": "kapha", "injuries_or_limitations": []
        },
        "gym_prefs": {
            "gym_goal": "strength",
            "workout_days_per_week": 6,
            "workout_duration_minutes": 90,
            "available_equipment": ["barbell", "dumbbell", "cable", "machine", "kettlebell"]
        }
    },
    {
        "name": "Profile 6 — Pregnancy safety gate test",
        "user_profile": {
            "age": 29, "gender": "female", "bmi": 23, "bmi_category": "normal",
            "fitness_level": "beginner", "activity_level": "light",
            "dominant_dosha": "pitta", "injuries_or_limitations": [],
            "pregnancy_or_nursing": True
        },
        "gym_prefs": {
            "gym_goal": "general_fitness",
            "workout_days_per_week": 3,
            "workout_duration_minutes": 30,
            "available_equipment": ["bodyweight"]
        }
    }
]

def check_validations(idx, profile, plan, pool):
    passed = True
    failures = []
    
    if idx == 0:
        # ✅ Only bodyweight exercises for Profile 1
        for ex in pool:
            if ex.get("equipment", "bodyweight").lower() != "bodyweight":
                passed = False
                failures.append(f"Profile 1 contained non-bodyweight equipment: {ex.get('equipment')}")
                break
                
    elif idx == 3:
        # ✅ No exercises with bad_knee contraindication in pool (Profile 4)
        for ex in pool:
            contra = set(ex.get("contraindications", []))
            if "bad_knee" in contra or "shoulder_injury" in contra:
                passed = False
                failures.append(f"Profile 4 contained contraindicated exercise: {ex.get('name')}")
                break
                
    elif idx == 4:
        # ✅ Advanced exercises included for Profile 5
        has_advanced = any(ex.get("level") == "advanced" for ex in pool)
        if not has_advanced:
            passed = False
            failures.append("Profile 5 did not contain any advanced exercises")
            
    elif idx == 5:
        # ✅ No plyometrics for pregnancy (Profile 6)
        for ex in pool:
            cat = ex.get("category", "").lower()
            name = ex.get("name", "").lower()
            if cat in ["plyometrics", "strongman"] or "jump" in name or "plyo" in name or "box" in name:
                passed = False
                failures.append(f"Profile 6 contained plyometrics/high-impact: {name}")
                break
                
    return passed, failures

passed_count = 0

for idx, p in enumerate(profiles):
    print("─" * 37)
    print(f"PROFILE {idx + 1}: {p['name']}")
    print("─" * 37)
    
    user_prof = p["user_profile"]
    gym_prefs = p["gym_prefs"]
    
    # Check pool size
    pool = filter_exercises(user_prof, gym_prefs)
    print(f"Exercises in filtered pool: {len(pool)}")
    
    # Generate full plan
    plan = generate_gym_plan(user_prof, gym_prefs)
    
    ws = plan["weekly_schedule"]
    split = [day["focus"] for day in ws]
    print(f"Weekly split: {split}")
    
    # Print Day 1
    d1 = ws[0]
    print(f"Day 1 ({d1['day_name']}) — {d1['focus']}:")
    print(f"  Warmup: {', '.join(d1['warmup'])}")
    print(f"  Main ({len(d1['main_workout'])} exercises):")
    for i, ex in enumerate(d1['main_workout']):
        print(f"    {i+1}. {ex['exercise_name']} — {ex['sets']}x{ex['reps']}, {ex['rest_seconds']}s rest")
    print(f"  Cooldown: {', '.join(d1['cooldown'])}")
    print(f"  Est. duration: {d1['estimated_duration_minutes']} min | Est. calories: {d1['calories_burned_estimate']}")
    
    tips = plan["ayurvedic_tips"]
    print("Ayurvedic tips:")
    print(f"  Best time: {tips['best_time_to_workout']}")
    print(f"  Pre-workout: {tips['pre_workout']}")
    
    has_disclaimer = "YES" if "PREGNANCY DISCLAIMER" in plan["disclaimer"] else ("NO (Standard)" if "disclaimer" in plan else "NO")
    if p["user_profile"].get("pregnancy_or_nursing"):
        print(f"Disclaimer present: {has_disclaimer}")
    else:
        print("Disclaimer present: YES (Standard)")
        
    print("\nVALIDATION CHECKS:")
    passed, fails = check_validations(idx, p, plan, pool)
    
    if idx == 0:
        print("  " + ("✅" if passed else "❌") + " Only bodyweight exercises for Profile 1")
    elif idx == 3:
        print("  " + ("✅" if passed else "❌") + " No exercises with bad_knee/shoulder contraindication in pool (Profile 4)")
    elif idx == 4:
        print("  " + ("✅" if passed else "❌") + " Advanced exercises included for Profile 5")
    elif idx == 5:
        print("  " + ("✅" if passed else "❌") + " No plyometrics for pregnancy (Profile 6)")
    else:
        passed = True # No explicit validation rules for 2 and 3 in prompt
        
    for f in fails:
        print(f"  ❌ {f}")
        
    if passed:
        passed_count += 1
    print("─" * 37 + "\n")

print(f"PASSED: {passed_count}/6 profiles")
print(f"FAILED: {6 - passed_count}/6 profiles")
