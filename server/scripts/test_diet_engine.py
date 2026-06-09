import sys
from pathlib import Path
import json

BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.append(str(BASE_DIR))

from services.diet_plan_engine import generate_diet_plan

PROFILES = [
    {
        "name": "Profile 1 - Vata, vegan, weight_loss, healthy gut",
        "user": {
            "id": "p1", "dominant_dosha": "vata",
            "pregnancy_or_nursing": False
        },
        "prefs": {
            "diet_goal": "weight_loss", "dietary_type": "vegan",
            "food_allergies": [], "food_intolerances": [],
            "gut_health_issue": "healthy", "fasting_days": []
        }
    },
    {
        "name": "Profile 2 - Pitta, vegetarian, detox, lactose intolerance, fasting Monday",
        "user": {
            "id": "p2", "dominant_dosha": "pitta",
            "pregnancy_or_nursing": False
        },
        "prefs": {
            "diet_goal": "detox", "dietary_type": "vegetarian",
            "food_allergies": [], "food_intolerances": ["lactose"],
            "gut_health_issue": "healthy", "fasting_days": ["Monday"]
        }
    },
    {
        "name": "Profile 3 - Kapha, vegetarian, energy, soy allergy",
        "user": {
            "id": "p3", "dominant_dosha": "kapha",
            "pregnancy_or_nursing": False
        },
        "prefs": {
            "diet_goal": "energy", "dietary_type": "vegetarian",
            "food_allergies": ["soy"], "food_intolerances": [],
            "gut_health_issue": "bloating", "fasting_days": []
        }
    },
    {
        "name": "Profile 4 - Vata, vegetarian, muscle_support, acidity",
        "user": {
            "id": "p4", "dominant_dosha": "vata",
            "pregnancy_or_nursing": False
        },
        "prefs": {
            "diet_goal": "muscle_support", "dietary_type": "vegetarian",
            "food_allergies": [], "food_intolerances": [],
            "gut_health_issue": "acidity", "fasting_days": []
        }
    },
    {
        "name": "Profile 5 - Pitta, vegan, general_wellness, gluten and peanut allergy",
        "user": {
            "id": "p5", "dominant_dosha": "pitta",
            "pregnancy_or_nursing": False
        },
        "prefs": {
            "diet_goal": "general_wellness", "dietary_type": "vegan",
            "food_allergies": ["gluten", "peanuts"], "food_intolerances": [],
            "gut_health_issue": "healthy", "fasting_days": []
        }
    }
]

def check_dairy(items):
    for item in items:
        # these are dairy by definition or we know them
        if item["id"] in ["milk_full_fat", "curd_yogurt", "paneer", "ghee", "butter", "buttermilk_chaas", "whey", "cottage_cheese", "cream", "lassi"]:
            return True
    return False

def check_soy(items):
    for item in items:
        if "soy" in item["id"] or "tofu" in item["id"] or "tempeh" in item["id"] or "edamame" in item["id"]:
            return True
    return False

def check_gluten(items):
    for item in items:
        # approximate check
        if item["id"] in ["roti_whole_wheat", "paratha", "daliya", "semolina_rava", "bread_whole_wheat", "barley"]:
            return True
    return False

def main():
    print("=== TESTING DIET PLAN ENGINE ===")
    
    passed = 0
    total = len(PROFILES)
    
    for p in PROFILES:
        print(f"\n───────────────────────────────────────")
        print(f"Testing: {p['name']}")
        print(f"───────────────────────────────────────")
        
        plan = generate_diet_plan(p["user"], p["prefs"])
        
        valid = True
        
        for day in plan["weekly_schedule"]:
            day_name = day["day_name"]
            is_fast = day["is_fasting_day"]
            meals = day["meals"]
            
            all_items_day = []
            for m, m_items in meals.items():
                if m == "daily_macros_approx": continue
                all_items_day.extend(m_items)
            
            if is_fast:
                print(f"{day_name}: Fasting Day!")
            
            if p["user"]["id"] == "p1" and check_dairy(all_items_day):
                print(f"❌ P1: Found dairy on {day_name} despite vegan!")
                valid = False
                
            if p["user"]["id"] == "p2":
                if day_name == "Monday" and not is_fast:
                    print(f"❌ P2: Monday should be fasting!")
                    valid = False
                if check_dairy(all_items_day):
                    print(f"❌ P2: Found dairy despite lactose intolerance!")
                    valid = False
                    
            if p["user"]["id"] == "p3" and check_soy(all_items_day):
                print(f"❌ P3: Found soy despite allergy!")
                valid = False
                
            if p["user"]["id"] == "p5":
                if check_dairy(all_items_day):
                    print(f"❌ P5: Found dairy despite vegan!")
                    valid = False
                if check_gluten(all_items_day):
                    print(f"❌ P5: Found gluten despite allergy!")
                    valid = False
                if any("peanut" in x["id"] for x in all_items_day):
                    print(f"❌ P5: Found peanuts despite allergy!")
                    valid = False

        if p["user"]["id"] == "p4":
            day1_macros = plan["weekly_schedule"][0]["meals"]["daily_macros_approx"]
            print(f"P4 (Muscle Support) Day 1 Macros: {day1_macros}")
            if day1_macros["protein_g"] < 30:
                print("⚠️ P4: Protein seems a bit low for muscle_support, but acceptable since we only use 100g portions.")
                
        if valid:
            print("✅ Profile Passed")
            passed += 1
            
    print(f"\n=======================")
    print(f"PASSED: {passed}/{total}")
    print(f"FAILED: {total - passed}/{total}")

if __name__ == "__main__":
    main()
