import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.yoga_plan_engine import generate_yoga_plan

PROFILES = [
    {
        "name": "Profile 1 - Vata beginner, stress_relief, 30 min morning",
        "user": {
            "id": "p1", "age": 25, "gender": "female", "dominant_dosha": "vata",
            "injuries_or_limitations": [], "pregnancy_or_nursing": False
        },
        "prefs": {
            "yoga_goal": "stress_relief", "yoga_experience": "beginner",
            "yoga_style_preference": ["hatha"], "time_available_minutes": 30,
            "time_of_day_preference": "morning"
        }
    },
    {
        "name": "Profile 2 - Pitta intermediate, flexibility, 45 min hatha",
        "user": {
            "id": "p2", "age": 30, "gender": "male", "dominant_dosha": "pitta",
            "injuries_or_limitations": [], "pregnancy_or_nursing": False
        },
        "prefs": {
            "yoga_goal": "flexibility", "yoga_experience": "intermediate",
            "yoga_style_preference": ["hatha"], "time_available_minutes": 45,
            "time_of_day_preference": "evening"
        }
    },
    {
        "name": "Profile 3 - Kapha advanced, strength, 60 min power flow",
        "user": {
            "id": "p3", "age": 35, "gender": "female", "dominant_dosha": "kapha",
            "injuries_or_limitations": [], "pregnancy_or_nursing": False
        },
        "prefs": {
            "yoga_goal": "strength", "yoga_experience": "advanced",
            "yoga_style_preference": ["power"], "time_available_minutes": 60,
            "time_of_day_preference": "morning"
        }
    },
    {
        "name": "Profile 4 - Vata with bad_knee + hypertension, healing, 20 min",
        "user": {
            "id": "p4", "age": 55, "gender": "male", "dominant_dosha": "vata",
            "injuries_or_limitations": ["bad_knee", "hypertension"], "pregnancy_or_nursing": False
        },
        "prefs": {
            "yoga_goal": "healing", "yoga_experience": "intermediate",
            "yoga_style_preference": ["restorative"], "time_available_minutes": 20,
            "time_of_day_preference": "both"
        }
    },
    {
        "name": "Profile 5 - Pregnant Pitta, 30 min restorative",
        "user": {
            "id": "p5", "age": 28, "gender": "female", "dominant_dosha": "pitta",
            "injuries_or_limitations": [], "pregnancy_or_nursing": True
        },
        "prefs": {
            "yoga_goal": "stress_relief", "yoga_experience": "beginner",
            "yoga_style_preference": ["restorative"], "time_available_minutes": 30,
            "time_of_day_preference": "evening"
        }
    }
]

def main():
    print("=== TESTING YOGA PLAN ENGINE ===")
    
    passed = 0
    total = len(PROFILES)
    
    for p in PROFILES:
        print(f"\n───────────────────────────────────────")
        print(f"Testing: {p['name']}")
        print(f"───────────────────────────────────────")
        
        plan = generate_yoga_plan(p["user"], p["prefs"])
        
        day1 = [d for d in plan["weekly_schedule"] if not d["rest"]][0]["session"]
        
        w_len = len(day1["warmup"])
        m_len = len(day1["main_sequence"])
        c_len = len(day1["cooldown"])
        
        prana_names = [pr["technique_name"] for pr in day1["pranayama_section"]]
        prana_ids = [pr["technique_id"] for pr in day1["pranayama_section"]]
        
        w_poses = [x["pose_name"] for x in day1["warmup"]]
        m_poses = [x["pose_name"] for x in day1["main_sequence"]]
        c_poses = [x["pose_name"] for x in day1["cooldown"]]
        
        savasana_last = False
        if c_len > 0 and (c_poses[-1] == "Corpse Pose" or c_poses[-1] == "Reclining Butterfly" or c_poses[-1] == "Reclining Hero"):
            savasana_last = True
            
        print(f"Pranayama selected: {', '.join(prana_names)}")
        print(f"Day 1 sequence:")
        print(f"  Warmup ({w_len} poses): {', '.join(w_poses)}")
        print(f"  Main ({m_len} poses): {', '.join(m_poses)}")
        print(f"  Cooldown ({c_len} poses): {', '.join(c_poses)}")
        print(f"  Ends with Savasana/Resting: {'YES' if savasana_last else 'NO'}")
        print(f"Dosha theme: {day1['dosha_theme']}")
        print(f"Pregnancy warning present: {'YES' if 'PREGNANCY WARNING' in plan['disclaimer'] else 'NO'}")
        
        # Validations
        valid = True
        
        if not savasana_last:
            print("❌ Savasana/Resting is not last!")
            valid = False
            
        if p["user"]["id"] == "p5":
            if "PREGNANCY WARNING" not in plan['disclaimer']:
                print("❌ Pregnancy warning missing!")
                valid = False
                
        if p["user"]["id"] == "p4":
            # Check for hypertension contraindications
            all_poses = w_poses + m_poses + c_poses
            bad = [x for x in all_poses if "stand" in x.lower() and "head" in x.lower()] # simple check
            if bad:
                print("❌ Found contraindicated poses!")
                valid = False
                
        if p["user"]["id"] == "p3": # Kapha gets energizing
            if not any("energ" in theme.lower() for theme in [day1['dosha_theme']]):
                print("❌ Kapha theme mismatch")
                valid = False
                
        if valid:
            print("✅ Profile Passed")
            passed += 1
            
    print(f"\n=======================")
    print(f"PASSED: {passed}/{total}")
    print(f"FAILED: {total - passed}/{total}")

if __name__ == "__main__":
    main()
