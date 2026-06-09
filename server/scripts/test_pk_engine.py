import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.panchakarma_engine import generate_panchakarma_plan

PROFILES = [
    {
        "name": "Profile 1 - Vata Home Detox, None experience, 7 days",
        "user": {
            "id": "p1", "dominant_dosha": "vata", "pregnancy_or_nursing": False
        },
        "prefs": {
            "panchakarma_goal": "detox", "detox_experience": "none",
            "setting": "home", "available_time_days": 7,
            "self_care_time_per_day": "30 min", "access_to_ayurvedic_herbs": "willing_to_buy",
            "diet_adherence_ability": "partial", "current_season": "Spring"
        }
    },
    {
        "name": "Profile 2 - Pitta Clinic Intensive, Experienced, 14 days",
        "user": {
            "id": "p2", "dominant_dosha": "pitta", "pregnancy_or_nursing": False
        },
        "prefs": {
            "panchakarma_goal": "rejuvenation", "detox_experience": "experienced",
            "setting": "clinic", "available_time_days": 14,
            "self_care_time_per_day": "2+ hours", "access_to_ayurvedic_herbs": "yes",
            "diet_adherence_ability": "strict", "current_season": "Fall"
        }
    },
    {
        "name": "Profile 3 - Kapha Home Lifestyle, None experience, 3 days",
        "user": {
            "id": "p3", "dominant_dosha": "kapha", "pregnancy_or_nursing": False
        },
        "prefs": {
            "panchakarma_goal": "seasonal_cleanse", "detox_experience": "none",
            "setting": "home", "available_time_days": 3,
            "self_care_time_per_day": "15 min", "access_to_ayurvedic_herbs": "no",
            "diet_adherence_ability": "lifestyle_only", "current_season": "Spring"
        }
    }
]

def main():
    print("=== TESTING PANCHAKARMA ENGINE ===")
    
    passed = 0
    total = len(PROFILES)
    
    for p in PROFILES:
        print(f"\n───────────────────────────────────────")
        print(f"Testing: {p['name']}")
        print(f"───────────────────────────────────────")
        
        plan = generate_panchakarma_plan(p["user"], p["prefs"])
        
        purva_days = plan["phase_breakdown"]["purvakarma_days"]
        pradhana_days = plan["phase_breakdown"]["pradhana_karma_days"]
        paschat_days = plan["phase_breakdown"]["paschat_karma_days"]
        
        print(f"Phases: Purva({purva_days}) -> Pradhana({pradhana_days}) -> Paschat({paschat_days})")
        print(f"Disclaimer: {plan['disclaimer']}")
        
        # Check all therapies for strictness
        valid = True
        all_therapies = []
        for day in plan["daily_schedule"]:
            for t in day["therapies"]:
                all_therapies.append(t["id"])
                
        # Unique therapies
        all_therapies = list(set(all_therapies))
        print(f"Selected Therapies: {', '.join(all_therapies)}")
        
        if p["prefs"]["setting"] == "home":
            # Must not contain clinical therapies
            clinical_therapies = ["vamana", "virechana_clinic", "basti_niruha", "basti_anuvasana", "raktamokshana", "nasya_clinic", "abhyanga_clinic"]
            for t in all_therapies:
                if t in clinical_therapies:
                    print(f"❌ Safety Violation! Home setting received clinical therapy: {t}")
                    valid = False
                    
        if p["prefs"]["detox_experience"] == "none":
            # Must not contain experienced therapies
            exp_therapies = ["vamana", "raktamokshana", "snehapana_clinic", "basti_home"]
            for t in all_therapies:
                if t in exp_therapies:
                    print(f"❌ Safety Violation! Beginner received advanced therapy: {t}")
                    valid = False

        if p["user"]["id"] == "p3":
            # 15 minutes max
            for day in plan["daily_schedule"]:
                for t in day["therapies"]:
                    if t["duration_minutes"] > 15:
                        print(f"❌ Time Violation! Received therapy over 15 mins: {t['name']} ({t['duration_minutes']}m)")
                        valid = False
                        
        if valid:
            print("✅ Profile Passed")
            passed += 1
            
    print(f"\n=======================")
    print(f"PASSED: {passed}/{total}")
    print(f"FAILED: {total - passed}/{total}")

if __name__ == "__main__":
    main()
