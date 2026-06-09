import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FOODS_PATH = BASE_DIR / "data" / "knowledge_base" / "diet_foods.json"

diet_foods = []
if FOODS_PATH.exists():
    with open(FOODS_PATH, "r", encoding="utf-8") as f:
        diet_foods = json.load(f)

def filter_and_score_foods(user_profile, diet_prefs, diet_foods):
    scored_foods = []
    
    # User Profile Data
    dominant_dosha = user_profile.get("dominant_dosha", "vata") or "vata"
    is_pregnant = user_profile.get("pregnancy_or_nursing", False)
    
    # Preferences Data
    diet_goal = diet_prefs.get("diet_goal", "general_wellness")
    dietary_type = diet_prefs.get("dietary_type", "vegetarian")
    food_allergies = set(diet_prefs.get("food_allergies", []))
    food_intolerances = set(diet_prefs.get("food_intolerances", []))
    gut_issue = diet_prefs.get("gut_health_issue", "healthy")
    
    # Map allergies to categories
    allergy_map = {
        "dairy": ["dairy"],
        "peanuts": ["nut_seed"], # We rely on specific IDs for more granular but category is safe
        "nuts_tree": ["nut_seed"],
        "soy": ["legume", "vegan_protein"], # Soya chunks, soy milk
        "gluten": ["grain"] # Approximate for wheat
    }
    
    blocked_categories = set()
    for alg in food_allergies:
        if alg in allergy_map:
            blocked_categories.update(allergy_map[alg])
            
    if "lactose" in food_intolerances:
        blocked_categories.update(["dairy"])
        
    for food in diet_foods:
        cat = food.get("category", "")
        fid = food.get("id", "")
        
        # Hard Filters
        # 1. Dietary Type
        if dietary_type == "vegan" and not food.get("vegan", True):
            continue
            
        # 2. Allergies/Intolerances
        if cat in blocked_categories:
            # Exceptions for gluten-free grains
            if "gluten" in food_allergies and cat == "grain":
                if fid not in ["oats", "quinoa", "millet_bajra", "millet_jowar", "rice_white", "basmati_rice", "brown_rice", "amaranth", "buckwheat"]:
                    continue # Exclude wheat/roti/bread
            else:
                continue
                
        # Soy specific exclusions
        if "soy" in food_allergies and ("soy" in fid or "tofu" in fid or "tempeh" in fid or "edamame" in fid):
            continue
            
        # Peanuts
        if "peanuts" in food_allergies and "peanut" in fid:
            continue
            
        score = 0
        
        # Soft Scoring
        ayur = food.get("ayurvedic", {})
        
        # 1. Dosha
        d_effect = ayur.get("dosha_effect", {}).get(dominant_dosha, 0)
        if d_effect == -1: score += 2 # Pacifying
        elif d_effect == 0: score += 1 # Neutral
        elif d_effect == 1: score -= 1 # Aggravating
        
        # 2. Gut Health
        virya = ayur.get("virya", "cooling")
        agni = ayur.get("agni_effect", "moderate")
        fib = food.get("nutrition_per_100g", {}).get("fiber_g", 0)
        
        if gut_issue == "acidity":
            if virya == "heating": score -= 2
            if virya == "cooling": score += 2
        elif gut_issue in ["bloating", "ibs"]:
            if agni == "heavy": score -= 2
            if agni == "easy": score += 2
        elif gut_issue == "constipation":
            if fib > 5: score += 2
            if agni == "heavy": score -= 1
            
        # 3. Goal
        if diet_goal == "weight_loss":
            if ayur.get("dosha_effect", {}).get("kapha", 0) == -1: score += 1
            if food.get("nutrition_per_100g", {}).get("calories", 100) < 150: score += 1
        elif diet_goal == "muscle_support":
            if food.get("nutrition_per_100g", {}).get("protein_g", 0) > 10: score += 2
        elif diet_goal == "energy":
            if cat in ["grain", "fruit"]: score += 1
        elif diet_goal == "detox":
            if agni == "easy": score += 2
            
        scored_foods.append((score, food))
        
    scored_foods.sort(key=lambda x: x[0], reverse=True)
    # Take top 80 foods to build meals
    return [f for s, f in scored_foods[:80]]

def get_meal_foods(food_pool, meal_type, category_needs, count=2):
    # category_needs: list of preferred categories e.g. ["grain", "legume"]
    candidates = [f for f in food_pool if meal_type in f.get("meal_suitable", [])]
    
    selected = []
    # Try to fulfill category needs first
    for cat in category_needs:
        cat_items = [f for f in candidates if f.get("category") == cat and f not in selected]
        if cat_items:
            selected.append(random.choice(cat_items))
            
    # Fill remaining slots with generic items suitable for the meal
    remaining_slots = count - len(selected)
    if remaining_slots > 0:
        available = [f for f in candidates if f not in selected]
        if available:
            # Sort by name just to ensure deterministic-like random sample
            available.sort(key=lambda x: x["id"])
            random.shuffle(available)
            selected.extend(available[:remaining_slots])
            
    return selected

def build_daily_diet(food_pool, is_fasting, fasting_type="fruit_and_dairy"):
    day_plan = {}
    total_macros = {"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0, "fiber_g": 0}
    
    if is_fasting:
        # Fasting logic - lighter meals
        fasting_pool = [f for f in food_pool if f.get("category") in ["fruit", "beverage", "dairy", "nut_seed"]]
        if not fasting_pool: fasting_pool = food_pool # Fallback
        
        meals_config = {
            "breakfast": ["beverage", "fruit"],
            "lunch": ["fruit", "dairy"],
            "snack": ["nut_seed", "beverage"],
            "dinner": ["dairy", "fruit"]
        }
        for meal, cats in meals_config.items():
            items = get_meal_foods(fasting_pool, meal, cats, count=2)
            fmt_items = []
            for item in items:
                nut = item.get("nutrition_per_100g", {})
                fmt_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "portion": "100g",
                    "macros": nut
                })
                for k in total_macros: total_macros[k] += nut.get(k, 0)
            day_plan[meal] = fmt_items
    else:
        # Normal logic
        meals_config = {
            "breakfast": ["grain", "beverage"],
            "lunch": ["grain", "legume", "vegetable"],
            "snack": ["fruit", "nut_seed"],
            "dinner": ["grain", "vegetable"]
        }
        for meal, cats in meals_config.items():
            items = get_meal_foods(food_pool, meal, cats, count=len(cats))
            fmt_items = []
            for item in items:
                nut = item.get("nutrition_per_100g", {})
                fmt_items.append({
                    "id": item["id"],
                    "name": item["name"],
                    "portion": "100g",
                    "macros": nut
                })
                for k in total_macros: total_macros[k] += nut.get(k, 0)
            day_plan[meal] = fmt_items
            
    day_plan["daily_macros_approx"] = {k: round(v, 1) for k, v in total_macros.items()}
    return day_plan

def get_ayurvedic_diet_tips(dosha):
    if dosha == "vata":
        return "Focus on warm, cooked, grounding foods. Incorporate healthy fats like ghee or sesame oil. Avoid cold, dry, or raw foods like salads and iced drinks. Eat at regular, consistent times to ground Vata."
    elif dosha == "pitta":
        return "Focus on cooling, mildly spiced foods. Sweet, bitter, and astringent tastes are best. Avoid excess chili, garlic, onion, and fermented foods. Don't skip meals, especially lunch, as Pitta digestion is very strong."
    else:
        return "Focus on light, warm, and spicy foods. Pungent, bitter, and astringent tastes are best. Favor cooked vegetables and light grains. Avoid heavy dairy, sweets, and cold foods. Only eat when truly hungry."

def generate_diet_plan(user_profile, diet_prefs, diet_foods_db=None):
    df = diet_foods_db if diet_foods_db is not None else diet_foods
    food_pool = filter_and_score_foods(user_profile, diet_prefs, df)
    
    fasting_days = [d.lower() for d in diet_prefs.get("fasting_days", [])]
    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    
    weekly_schedule = []
    
    for i, day in enumerate(days_of_week):
        is_fast = day.lower() in fasting_days
        
        # Reshuffle the pool slightly per day to guarantee variety
        day_pool = list(food_pool)
        random.shuffle(day_pool)
        
        day_plan = build_daily_diet(day_pool, is_fast)
        
        weekly_schedule.append({
            "day": i + 1,
            "day_name": day,
            "is_fasting_day": is_fast,
            "meals": day_plan
        })
        
    return {
        "plan_id": f"diet_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": user_profile.get("dominant_dosha", "vata"),
            "diet_goal": diet_prefs.get("diet_goal", "general_wellness"),
            "dietary_type": diet_prefs.get("dietary_type", "vegetarian"),
            "fasting_protocol": diet_prefs.get("intermittent_fasting", "no")
        },
        "weekly_schedule": weekly_schedule,
        "ayurvedic_tips": get_ayurvedic_diet_tips(user_profile.get("dominant_dosha", "vata")),
        "disclaimer": "This meal plan is generated for wellness purposes and relies on approximate 100g macros. Consult a certified nutritionist before making drastic dietary changes.",
        "enriched": False
    }
