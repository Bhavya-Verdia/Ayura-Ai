import sys
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.remedy_engine import generate_remedies_plan

PROFILES = [
    {
        "name": "Profile 1 - Pregnant Pitta with Acidity",
        "user": {
            "id": "p1", "dominant_dosha": "pitta", "pregnancy_or_nursing": True
        },
        "prefs": {
            "symptom_severity": {"acidity": "severe", "indigestion": "mild"},
            "ingredient_access": "kitchen_only",
            "preference_taste_smell": []
        },
        "target": "home_remedy"
    },
    {
        "name": "Profile 2 - Vata with Chronic Constipation, needs herbs",
        "user": {
            "id": "p2", "dominant_dosha": "vata", "pregnancy_or_nursing": False
        },
        "prefs": {
            "symptom_severity": {"constipation": "severe", "bloating": "moderate"},
            "ingredient_access": "can_buy_herbs",
            "preference_taste_smell": []
        },
        "target": "clinical_medicine"
    },
    {
        "name": "Profile 3 - Kapha with Cold/Cough, kitchen only, hates bitter",
        "user": {
            "id": "p3", "dominant_dosha": "kapha", "pregnancy_or_nursing": False
        },
        "prefs": {
            "symptom_severity": {"cold": "moderate", "cough": "mild"},
            "ingredient_access": "kitchen_only",
            "preference_taste_smell": ["no_bitter"]
        },
        "target": "home_remedy"
    }
]

def main():
    print("=== TESTING REMEDY ENGINE ===")
    
    passed = 0
    total = len(PROFILES)
    
    for p in PROFILES:
        print(f"\n───────────────────────────────────────")
        print(f"Testing: {p['name']} ({p['target']})")
        print(f"───────────────────────────────────────")
        
        plan = generate_remedies_plan(p["user"], p["prefs"], p["target"])
        
        print(f"Disclaimer: {plan['disclaimer']}")
        
        valid = True
        all_remedies = [r["id"] for r in plan["selected_remedies"]]
        print(f"Selected: {all_remedies}")
        
        if not all_remedies:
            print("⚠️ No remedies matched! This might be okay if filters are extremely strict.")
            
        if p["user"]["id"] == "p1":
            if "ajwain_water" in all_remedies:
                print(f"❌ Safety Violation! P1 received ajwain_water despite pregnancy filter.")
                valid = False
            for r in plan["selected_remedies"]:
                if r["id"] == "ginger_honey_tea":
                    print(f"❌ Safety Violation! P1 (Pitta/Acidity) received heating ginger.")
                    valid = False
                    
        if p["user"]["id"] == "p2":
            if "triphala_churna" not in all_remedies:
                print(f"❌ Missing Triphala for severe constipation.")
                valid = False
                
        if p["user"]["id"] == "p3":
            for r in plan["selected_remedies"]:
                if "bitter" in r["taste_profile"]:
                    print(f"❌ Taste Violation! P3 received bitter remedy: {r['id']}")
                    valid = False

        if valid:
            print("✅ Profile Passed")
            passed += 1
            
    print(f"\n=======================")
    print(f"PASSED: {passed}/{total}")
    print(f"FAILED: {total - passed}/{total}")

if __name__ == "__main__":
    main()
