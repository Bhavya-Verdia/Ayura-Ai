from datetime import datetime, timezone
import random
from services.diet_plan_engine import generate_diet_plan

def get_dosha_timeline(dosha):
    dosha = dosha.lower()
    if dosha == "vata":
        return [
            {"time": "06:30 AM", "activity": "Wake up. Gentle stretches.", "type": "morning_routine"},
            {"time": "07:00 AM", "activity": "Warm sesame oil massage (Abhyanga) & warm shower.", "type": "self_care"},
            {"time": "08:00 AM", "activity": "Breakfast", "type": "meal", "meal_type": "breakfast"},
            {"time": "10:00 AM", "activity": "Focus work. Drink warm ginger tea.", "type": "work"},
            {"time": "01:00 PM", "activity": "Lunch", "type": "meal", "meal_type": "lunch"},
            {"time": "04:00 PM", "activity": "Snack", "type": "meal", "meal_type": "snack"},
            {"time": "06:00 PM", "activity": "Gentle Yoga / Walking.", "type": "exercise"},
            {"time": "07:00 PM", "activity": "Dinner", "type": "meal", "meal_type": "dinner"},
            {"time": "09:30 PM", "activity": "Wind down. Warm milk with nutmeg.", "type": "wind_down"},
            {"time": "10:00 PM", "activity": "Sleep", "type": "sleep"}
        ]
    elif dosha == "pitta":
        return [
            {"time": "05:30 AM", "activity": "Wake up. Splash cold water on face.", "type": "morning_routine"},
            {"time": "06:00 AM", "activity": "Cooling Yoga / Moderate exercise.", "type": "exercise"},
            {"time": "07:30 AM", "activity": "Breakfast", "type": "meal", "meal_type": "breakfast"},
            {"time": "10:00 AM", "activity": "Focus work. Drink coconut water.", "type": "work"},
            {"time": "12:30 PM", "activity": "Lunch", "type": "meal", "meal_type": "lunch"},
            {"time": "03:30 PM", "activity": "Snack", "type": "meal", "meal_type": "snack"},
            {"time": "05:30 PM", "activity": "Relaxing walk in nature.", "type": "self_care"},
            {"time": "06:30 PM", "activity": "Dinner", "type": "meal", "meal_type": "dinner"},
            {"time": "09:00 PM", "activity": "Wind down. Read a book.", "type": "wind_down"},
            {"time": "10:00 PM", "activity": "Sleep", "type": "sleep"}
        ]
    else: # Kapha
        return [
            {"time": "05:00 AM", "activity": "Wake up early. Drink warm water with honey.", "type": "morning_routine"},
            {"time": "05:30 AM", "activity": "Vigorous exercise / Running.", "type": "exercise"},
            {"time": "07:00 AM", "activity": "Dry brushing (Garshana) & warm shower.", "type": "self_care"},
            {"time": "08:30 AM", "activity": "Breakfast (Light)", "type": "meal", "meal_type": "breakfast"},
            {"time": "01:00 PM", "activity": "Lunch (Main meal of the day)", "type": "meal", "meal_type": "lunch"},
            {"time": "04:30 PM", "activity": "Snack (Optional, prefer tea)", "type": "meal", "meal_type": "snack"},
            {"time": "06:30 PM", "activity": "Dinner (Light soup or veggies)", "type": "meal", "meal_type": "dinner"},
            {"time": "08:30 PM", "activity": "Wind down. Triphala tea.", "type": "wind_down"},
            {"time": "10:00 PM", "activity": "Sleep", "type": "sleep"}
        ]

def generate_routine_plan(user_profile, prefs, diet_foods_db=None):
    dosha = user_profile.get("dominant_dosha", "vata")
    diet_prefs = prefs.get("diet", {})
    
    # 1. Generate the base Diet Plan
    diet_plan = generate_diet_plan(user_profile, diet_prefs, diet_foods_db)
    
    # 2. Build the Timeline
    base_timeline = get_dosha_timeline(dosha)
    
    weekly_routine = []
    
    for day_data in diet_plan["weekly_schedule"]:
        daily_timeline = []
        meals = day_data["meals"]
        
        for slot in base_timeline:
            slot_copy = slot.copy()
            if slot_copy["type"] == "meal":
                meal_key = slot_copy["meal_type"]
                # Embed diet info
                if meal_key in meals:
                    slot_copy["diet_recommendation"] = meals[meal_key]
                else:
                    slot_copy["diet_recommendation"] = []
            daily_timeline.append(slot_copy)
            
        weekly_routine.append({
            "day": day_data["day"],
            "day_name": day_data["day_name"],
            "is_fasting_day": day_data["is_fasting_day"],
            "timeline": daily_timeline,
            "daily_macros_approx": meals.get("daily_macros_approx", {})
        })
        
    return {
        "plan_id": f"routine_{user_profile.get('id', 'unknown')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dosha,
        },
        "weekly_routine": weekly_routine,
        "ayurvedic_tips": diet_plan.get("ayurvedic_tips", ""),
        "disclaimer": "This daily routine is educational. Please consult a professional before beginning rigorous exercise or diet changes.",
        "enriched": False
    }
