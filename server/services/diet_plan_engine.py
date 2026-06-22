import hashlib
import json
import random
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent
FOODS_PATH = BASE_DIR / "data" / "knowledge_base" / "diet_foods.json"

diet_foods: list[dict] = []
if FOODS_PATH.exists():
    with open(FOODS_PATH, "r", encoding="utf-8") as f:
        diet_foods = json.load(f)

# ── Realistic Indian portion sizes per category ────────────────────────────────
_PORTION: dict[str, tuple[str, int]] = {
    "grain":         ("150g cooked (1 katori)", 150),
    "legume":        ("100g cooked (1 katori)", 100),
    "vegetable":     ("150g cooked (1 cup)", 150),
    "dairy":         ("150ml / 150g", 150),
    "vegan_protein": ("100g", 100),
    "fruit":         ("120g (1 medium)", 120),
    "nut_seed":      ("30g (1 handful)", 30),
    "spice":         ("5g (1 tsp)", 5),
    "oil":           ("10g (1 tsp)", 10),
    "beverage":      ("200ml (1 cup)", 200),
}

# Per-item overrides for condiment-type foods (oils, ghee, honey, etc.)
_ITEM_PORTIONS: dict[str, tuple[str, int]] = {
    "ghee":            ("1 tsp (5g)", 5),
    "coconut_oil":     ("1 tsp (5g)", 5),
    "sesame_oil":      ("1 tsp (5g)", 5),
    "mustard_oil":     ("1 tsp (5g)", 5),
    "olive_oil":       ("1 tsp (5g)", 5),
    "honey":           ("1 tsp (7g)", 7),
    "jaggery":         ("1 tsp (10g)", 10),
    "turmeric":        ("1 tsp (3g)", 3),
    "cumin_jeera":     ("1 tsp (3g)", 3),
    "cinnamon":        ("½ tsp (2g)", 2),
    "black_pepper":    ("½ tsp (2g)", 2),
    "fenugreek_seeds": ("1 tsp (5g)", 5),
    "ajwain":          ("1 tsp (3g)", 3),
    "flaxseeds":       ("1 tbsp (10g)", 10),
    "chia_seeds":      ("1 tbsp (10g)", 10),
    "hemp_seeds":      ("1 tbsp (10g)", 10),
}

# ── Condition-specific food rules ──────────────────────────────────────────────
_CONDITION_PROTOCOLS: dict[str, dict] = {
    "diabetes": {
        "avoid_ids": {"white_rice", "refined_flour", "maida", "sugar", "jaggery"},
        "avoid_categories": set(),
        "boost_ids": {"bitter_gourd", "fenugreek_seeds", "amla", "brown_rice",
                      "barley", "millet_bajra", "millet_jowar", "oats",
                      "turmeric", "cinnamon"},
        "score_adjust": {"grain": -1, "fruit": -1},
    },
    "hypertension": {
        "avoid_ids": {"pickle", "papad", "processed_cheese"},
        "avoid_categories": set(),
        "boost_ids": {"banana", "sweet_potato", "spinach", "amla",
                      "garlic", "flaxseeds", "beetroot", "cucumber",
                      "watermelon", "pomegranate"},
        "score_adjust": {},
    },
    "pcos": {
        "avoid_ids": {"white_rice", "refined_flour", "maida", "sugar"},
        "avoid_categories": set(),
        "boost_ids": {"flaxseeds", "fenugreek_seeds", "amla", "turmeric",
                      "brown_rice", "quinoa", "millet_bajra", "spinach"},
        "score_adjust": {"grain": -1},
    },
    "hypothyroid": {
        "avoid_ids": {"cabbage_raw", "broccoli_raw", "cauliflower_raw"},
        "avoid_categories": set(),
        "boost_ids": {"pumpkin_seeds", "ginger", "turmeric", "coconut_oil"},
        "score_adjust": {},
    },
    "thyroid": {
        "avoid_ids": {"cabbage_raw", "broccoli_raw", "cauliflower_raw"},
        "avoid_categories": set(),
        "boost_ids": {"pumpkin_seeds", "ginger", "turmeric"},
        "score_adjust": {},
    },
    "obesity": {
        "avoid_ids": set(),
        "avoid_categories": set(),
        "boost_ids": {"moong_dal", "toor_dal", "spinach", "bitter_gourd",
                      "cucumber", "oats", "flaxseeds", "amla"},
        "score_adjust": {"nut_seed": -1, "oil": -2, "dairy": -1},
    },
    "fatty_liver": {
        "avoid_ids": set(),
        "avoid_categories": {"oil"},
        "boost_ids": {"turmeric", "amla", "garlic", "leafy_greens", "moong_dal"},
        "score_adjust": {"dairy": -1},
    },
    "kidney_disease": {
        "avoid_ids": {"banana", "tomato", "potato", "avocado"},
        "avoid_categories": set(),
        "boost_ids": {"rice_white", "basmati_rice", "apple", "cabbage"},
        "score_adjust": {"legume": -2, "nut_seed": -1},
    },
    "anemia": {
        "avoid_ids": set(),
        "avoid_categories": set(),
        "boost_ids": {"spinach", "beet", "dates", "pomegranate", "amla",
                      "fenugreek_seeds", "sesame_seeds", "lentils"},
        "score_adjust": {},
    },
}

_COND_ALIASES: dict[str, str] = {
    "type2_diabetes": "diabetes", "type_2_diabetes": "diabetes",
    "insulin_resistance": "diabetes", "prediabetes": "diabetes",
    "bp": "hypertension", "high_blood_pressure": "hypertension",
    "polycystic_ovary": "pcos", "polycystic_ovarian_syndrome": "pcos",
    "hypothyroidism": "hypothyroid", "thyroidism": "thyroid",
    "overweight": "obesity", "weight_management": "obesity",
    "liver_disease": "fatty_liver", "nafld": "fatty_liver",
    "ckd": "kidney_disease", "kidney_failure": "kidney_disease",
    "iron_deficiency": "anemia",
}

# ── Ritucharya: seasonal scoring ───────────────────────────────────────────────
_SEASON_VIRYA: dict[str, str] = {
    "vasanta": "heating",
    "grishma": "cooling",
    "varsha": "heating",
    "sharad": "cooling",
    "hemanta": "heating",
    "shishira": "heating",
}
_SEASON_RASAS: dict[str, list[str]] = {
    "vasanta": ["pungent", "bitter", "astringent"],
    "grishma": ["sweet", "bitter", "astringent"],
    "varsha": ["sour", "salty", "sweet"],
    "sharad": ["sweet", "bitter", "astringent"],
    "hemanta": ["sweet", "sour", "salty"],
    "shishira": ["sweet", "sour", "salty"],
}

# ── Agni-type meal adjustments ─────────────────────────────────────────────────
_AGNI_ADJUST: dict[str, dict] = {
    "manda": {
        "avoid_agni_effect": {"heavy"},
        "preferred_agni_effect": {"easy"},
        "notes": "Skip heavy breakfast; prefer light, warm, well-spiced meals twice daily.",
    },
    "tikshna": {
        "avoid_agni_effect": set(),
        "preferred_agni_effect": {"moderate", "easy"},
        "notes": "Never skip meals; strong Agni needs regular cooling, substantial nourishment.",
    },
    "vishama": {
        "avoid_agni_effect": {"heavy"},
        "preferred_agni_effect": {"easy", "moderate"},
        "notes": "Eat at consistent times; warm, moist, grounding foods stabilise Vishama Agni.",
    },
    "sama": {
        "avoid_agni_effect": set(),
        "preferred_agni_effect": set(),
        "notes": "Balanced digestion — maintain with regular meal times and seasonal foods.",
    },
}

# ── Dinacharya meal timing per dosha ──────────────────────────────────────────
_MEAL_TIMING: dict[str, dict] = {
    "vata": {
        "breakfast": "7:00–8:00 AM — warm, cooked; before Vata peaks at 10 AM",
        "lunch": "12:00–1:00 PM — largest meal at solar peak",
        "snack": "4:00–5:00 PM — small nourishing snack before Vata evening spike",
        "dinner": "6:30–7:30 PM — warm, light; at least 2 hrs before sleep",
        "wake_up_drink": "Warm water with a pinch of rock salt and cumin",
        "bedtime_drink": "Warm golden milk with turmeric and cardamom",
        "general_note": "Regularity is the single most important Vata prescription. Eat at the same time every day.",
    },
    "pitta": {
        "breakfast": "7:30–8:30 AM — moderate, cooling breakfast",
        "lunch": "12:00–1:00 PM — substantial; Pitta digestion peaks at midday",
        "snack": "3:00–4:00 PM — cooling fruit or coconut water",
        "dinner": "7:00–8:00 PM — light, early; prevents overnight heat buildup",
        "wake_up_drink": "Room-temperature water with soaked dates or raisins",
        "bedtime_drink": "Cool milk with cardamom and fennel",
        "general_note": "Never skip lunch — Pitta Agni is strongest and must be fed at midday.",
    },
    "kapha": {
        "breakfast": "8:00–9:00 AM — light or skip; only eat if truly hungry",
        "lunch": "12:30–1:30 PM — main meal; spiced, warm, light grains and legumes",
        "snack": "4:00–5:00 PM — skip if not hungry; ginger tea instead",
        "dinner": "6:00–7:00 PM — very light, early; avoid heavy foods after dark",
        "wake_up_drink": "Warm water with honey, ginger, and lemon — kindles Kapha Agni",
        "bedtime_drink": "Warm ginger-cinnamon tea — prevents Kapha overnight accumulation",
        "general_note": "Less is more for Kapha. Never eat out of boredom or habit.",
    },
}

# ── Dosha spice guide ──────────────────────────────────────────────────────────
_DOSHA_SPICES: dict[str, list[dict]] = {
    "vata": [
        {"name": "Ginger", "sanskrit": "Shunthi",
         "use": "Fresh in morning tea and all cooked meals — kindles Agni, warms Vata"},
        {"name": "Cumin", "sanskrit": "Jeeraka",
         "use": "Toast and add to dal and rice — grounds Vata, aids digestion"},
        {"name": "Cardamom", "sanskrit": "Ela",
         "use": "In warm milk or chai — reduces bloating, calms nervous system"},
        {"name": "Ajwain", "sanskrit": "Ajamoda",
         "use": "In rotis and dals — powerful carminative for Vata bloating"},
        {"name": "Asafoetida", "sanskrit": "Hingu",
         "use": "Tiny pinch in tadka — prevents Vata gas; most important Vata spice"},
    ],
    "pitta": [
        {"name": "Coriander", "sanskrit": "Dhanyaka",
         "use": "Fresh or seeds — the best Pitta-pacifying spice; use liberally"},
        {"name": "Fennel", "sanskrit": "Shatapushpa",
         "use": "After meals — cooling, anti-inflammatory, aids digestion"},
        {"name": "Cardamom", "sanskrit": "Ela",
         "use": "In cool drinks and desserts — sweet, cooling"},
        {"name": "Turmeric", "sanskrit": "Haridra",
         "use": "In all cooking — anti-inflammatory; use moderately (mildly heating)"},
        {"name": "Saffron", "sanskrit": "Kumkuma",
         "use": "In warm milk — royal Pitta tonic, cooling and nourishing"},
    ],
    "kapha": [
        {"name": "Black Pepper", "sanskrit": "Maricha",
         "use": "In all meals — stimulates sluggish Kapha Agni, burns Ama"},
        {"name": "Dry Ginger", "sanskrit": "Shunthi",
         "use": "Powder in food and tea — Kapha's number-one spice"},
        {"name": "Turmeric", "sanskrit": "Haridra",
         "use": "Generous amounts — reduces Kapha mucus and inflammation"},
        {"name": "Cinnamon", "sanskrit": "Tvak",
         "use": "In morning tea and porridge — warms and stimulates Kapha metabolism"},
        {"name": "Fenugreek", "sanskrit": "Methi",
         "use": "Seeds in dal or sprouted — the best Kapha fat-burning seed"},
    ],
}

_AYUR_TIPS: dict[str, str] = {
    "vata": (
        "Favour warm, cooked, oily, and grounding foods. Use generous ghee. "
        "Eat at consistent times — regularity is the single most important Vata prescription. "
        "Avoid cold drinks, raw salads, and dry snacks."
    ),
    "pitta": (
        "Favour cooling, mildly spiced, lightly sweet foods. Include coconut, coriander, and fennel liberally. "
        "Never skip lunch — your Agni is strongest at midday. "
        "Avoid excess chilli, garlic, onion, vinegar, and fermented foods."
    ),
    "kapha": (
        "Favour light, warm, pungent, and spiced foods. Prefer honey over sugar. "
        "Skip or minimise breakfast if not genuinely hungry. "
        "Avoid heavy dairy, cold foods, sweets, and eating after 7 PM."
    ),
}


# ── Helpers ────────────────────────────────────────────────────────────────────
def _seeded_rng(user_id: str, week: int, day: int) -> random.Random:
    seed = int(hashlib.md5(f"{user_id}|{week}|{day}".encode()).hexdigest(), 16) % (2**32)
    return random.Random(seed)


def _build_condition_rules(medical_history: list[str]) -> dict:
    combined: dict = {
        "avoid_ids": set(),
        "avoid_categories": set(),
        "boost_ids": set(),
        "score_adjust": {},
        "active": [],
    }
    for cond in (medical_history or []):
        key = cond.lower().replace(" ", "_")
        key = _COND_ALIASES.get(key, key)
        if key in _CONDITION_PROTOCOLS:
            combined["active"].append(key)
            proto = _CONDITION_PROTOCOLS[key]
            combined["avoid_ids"].update(proto["avoid_ids"])
            combined["avoid_categories"].update(proto["avoid_categories"])
            combined["boost_ids"].update(proto["boost_ids"])
            for cat, adj in proto["score_adjust"].items():
                combined["score_adjust"][cat] = combined["score_adjust"].get(cat, 0) + adj
    return combined


# ── Food filter + scorer ───────────────────────────────────────────────────────
def filter_and_score_foods(user_profile: dict, diet_prefs: dict,
                            foods: list[dict], cond_rules: dict | None = None) -> list[dict]:
    dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
    vikriti = (user_profile.get("vikriti_dominant") or dominant_dosha).lower()
    dietary_type = (diet_prefs.get("dietary_type") or "vegetarian").lower()
    food_allergies = set(diet_prefs.get("food_allergies") or [])
    food_intolerances = set(diet_prefs.get("food_intolerances") or [])
    diet_goal = diet_prefs.get("diet_goal") or "general_wellness"
    gut_issue = diet_prefs.get("gut_health_issue") or "healthy"
    agni_type = (user_profile.get("agni_type") or "sama").lower()
    ama = (user_profile.get("ama_indicator") or "none").lower()
    ojas = (user_profile.get("ojas_level") or "moderate").lower()
    season = (user_profile.get("current_season") or "").lower()
    bmi_cat = (user_profile.get("bmi_category") or "normal").lower()
    stress = (user_profile.get("stress_level") or "moderate").lower()

    if cond_rules is None:
        cond_rules = _build_condition_rules(user_profile.get("medical_history") or [])

    allergy_map: dict[str, list[str]] = {
        "dairy": ["dairy"],
        "nuts_tree": ["nut_seed"],
        "soy": ["vegan_protein"],
        "gluten": ["grain"],
        "peanuts": [],
    }
    blocked_categories: set[str] = set()
    for alg in food_allergies:
        blocked_categories.update(allergy_map.get(alg, []))
    if "lactose" in food_intolerances:
        blocked_categories.add("dairy")
    blocked_categories.update(cond_rules["avoid_categories"])

    preferred_virya = _SEASON_VIRYA.get(season, "")
    preferred_rasas = set(_SEASON_RASAS.get(season, []))
    agni_info = _AGNI_ADJUST.get(agni_type, _AGNI_ADJUST["sama"])

    gluten_free_ids = {"oats", "quinoa", "millet_bajra", "millet_jowar",
                       "rice_white", "basmati_rice", "brown_rice", "white_rice",
                       "amaranth", "buckwheat"}

    scored: list[tuple[int, dict]] = []
    for food in foods:
        cat = food.get("category", "")
        fid = food.get("id", "")
        ayur = food.get("ayurvedic", {})

        # Hard filters
        if fid in cond_rules["avoid_ids"]:
            continue
        if cat in blocked_categories:
            if "gluten" in food_allergies and cat == "grain":
                if fid not in gluten_free_ids:
                    continue
            else:
                continue
        if "soy" in food_allergies and any(x in fid for x in ("soy", "tofu", "tempeh", "edamame")):
            continue
        if "peanuts" in food_allergies and "peanut" in fid:
            continue
        if dietary_type == "vegan" and not food.get("vegan", True):
            continue
        if ayur.get("agni_effect") in agni_info["avoid_agni_effect"]:
            continue

        score = 0
        dosha_eff = ayur.get("dosha_effect", {})

        # Dosha scoring
        primary_eff = dosha_eff.get(dominant_dosha, 0)
        vikriti_eff = dosha_eff.get(vikriti, 0) if vikriti != dominant_dosha else 0
        if primary_eff == -1: score += 3
        elif primary_eff == 0: score += 1
        elif primary_eff == 1: score -= 1
        if vikriti_eff == -1: score += 1

        # Seasonal scoring
        virya = ayur.get("virya", "")
        if preferred_virya and virya == preferred_virya:
            score += 2
        if preferred_rasas and set(ayur.get("rasa", [])).intersection(preferred_rasas):
            score += 1

        # Agni scoring
        agni_eff = ayur.get("agni_effect", "moderate")
        if agni_eff in agni_info["preferred_agni_effect"]:
            score += 2
        if ama in ("high", "moderate") and agni_eff == "heavy":
            score -= 2

        # Gut health scoring
        nut = food.get("nutrition_per_100g", {})
        fib = nut.get("fiber_g", 0)
        if gut_issue == "acidity":
            if virya == "heating": score -= 2
            if virya == "cooling": score += 2
        elif gut_issue in ("bloating", "ibs"):
            if agni_eff == "heavy": score -= 2
            if agni_eff == "easy": score += 2
        elif gut_issue == "constipation":
            if fib > 5: score += 2

        # Goal scoring
        if diet_goal == "weight_loss":
            if dosha_eff.get("kapha", 0) == -1: score += 1
            if nut.get("calories", 100) < 80: score += 1
        elif diet_goal == "muscle_support":
            if nut.get("protein_g", 0) > 10: score += 2
        elif diet_goal == "energy":
            if cat in ("grain", "fruit"): score += 1
        elif diet_goal == "detox":
            if agni_eff == "easy": score += 2
        elif diet_goal == "gut_health":
            if fib > 4: score += 2

        # BMI / ojas / stress
        if bmi_cat in ("overweight", "obese") and nut.get("calories", 100) < 80:
            score += 1
        if ojas == "low" and cat in ("dairy", "nut_seed", "fruit"):
            score += 1
        if stress in ("high", "very_high"):
            if any(b in ayur.get("best_for", []) for b in
                   ("anxiety", "stress", "nervous_system", "sleep")):
                score += 2

        # Condition boost
        if fid in cond_rules["boost_ids"]: score += 3
        score += cond_rules["score_adjust"].get(cat, 0)

        scored.append((score, food))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [f for _, f in scored[:90]]


# ── Meal assembly ──────────────────────────────────────────────────────────────
def _get_meal_foods(pool: list[dict], meal_type: str, cats: list[str],
                    rng: random.Random) -> list[dict]:
    candidates = [f for f in pool if meal_type in (f.get("meal_suitable") or [])]
    selected: list[dict] = []
    for cat in cats:
        items = [f for f in candidates if f.get("category") == cat and f not in selected]
        if items:
            selected.append(rng.choice(items))
    remaining = len(cats) - len(selected)
    if remaining > 0:
        available = sorted([f for f in candidates if f not in selected], key=lambda x: x["id"])
        rng.shuffle(available)
        selected.extend(available[:remaining])
    return selected


def _format_food(food: dict) -> dict:
    cat = food.get("category", "")
    fid = food.get("id", "")
    if fid in _ITEM_PORTIONS:
        portion_label, portion_g = _ITEM_PORTIONS[fid]
    else:
        portion_label, portion_g = _PORTION.get(cat, ("100g", 100))
    scale = portion_g / 100.0
    raw = food.get("nutrition_per_100g", {})
    return {
        "id": food["id"],
        "name": food["name"],
        "category": cat,
        "portion": portion_label,
        "macros": {
            "calories": round(raw.get("calories", 0) * scale, 1),
            "protein_g": round(raw.get("protein_g", 0) * scale, 1),
            "carbs_g": round(raw.get("carbs_g", 0) * scale, 1),
            "fat_g": round(raw.get("fat_g", 0) * scale, 1),
            "fiber_g": round(raw.get("fiber_g", 0) * scale, 1),
        },
        "ayurvedic": {
            "rasa": food.get("ayurvedic", {}).get("rasa", []),
            "virya": food.get("ayurvedic", {}).get("virya", ""),
        },
    }


_MEAL_CONFIGS: dict[str, dict[str, list[str]]] = {
    "full": {
        "breakfast": ["grain", "beverage"],
        "lunch":     ["grain", "legume", "vegetable"],
        "snack":     ["fruit", "nut_seed"],
        "dinner":    ["grain", "vegetable", "legume"],
    },
    "manda": {
        "breakfast": ["beverage", "fruit"],
        "lunch":     ["grain", "legume", "vegetable"],
        "snack":     ["fruit"],
        "dinner":    ["vegetable", "grain"],
    },
    "tikshna": {
        "breakfast": ["grain", "dairy", "beverage"],
        "lunch":     ["grain", "legume", "vegetable", "dairy"],
        "snack":     ["grain", "fruit"],
        "dinner":    ["grain", "legume", "vegetable"],
    },
    "fasting": {
        "breakfast": ["beverage", "fruit"],
        "lunch":     ["fruit", "dairy"],
        "snack":     ["nut_seed", "beverage"],
        "dinner":    ["dairy", "fruit"],
    },
}


def _build_day(pool: list[dict], is_fasting: bool, agni_type: str,
               rng: random.Random) -> dict:
    if is_fasting:
        config_key = "fasting"
        fasting_pool = [f for f in pool if f.get("category") in
                        ("fruit", "beverage", "dairy", "nut_seed")]
        active_pool = fasting_pool or pool
    elif agni_type == "manda":
        config_key, active_pool = "manda", pool
    elif agni_type == "tikshna":
        config_key, active_pool = "tikshna", pool
    else:
        config_key, active_pool = "full", pool

    config = _MEAL_CONFIGS[config_key]
    meals: dict[str, list[dict]] = {}
    totals: dict[str, float] = {
        "calories": 0.0, "protein_g": 0.0, "carbs_g": 0.0, "fat_g": 0.0, "fiber_g": 0.0
    }

    for meal_name, cats in config.items():
        items = _get_meal_foods(active_pool, meal_name, cats, rng)
        formatted = []
        for food in items:
            fmt = _format_food(food)
            formatted.append(fmt)
            for k in totals:
                totals[k] += fmt["macros"].get(k, 0)
        meals[meal_name] = formatted

    return {
        "meals": meals,
        "daily_macros": {k: round(v, 1) for k, v in totals.items()},
    }


# ── Main entry point ───────────────────────────────────────────────────────────
def generate_diet_plan(user_profile: dict, diet_prefs: dict,
                       diet_foods_db: list[dict] | None = None) -> dict:
    df = diet_foods_db if diet_foods_db is not None else diet_foods
    user_id = str(user_profile.get("id") or user_profile.get("_id") or "anon")
    dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
    agni_type = (user_profile.get("agni_type") or "sama").lower()
    season = (user_profile.get("current_season") or "").lower()
    fasting_days = {d.lower() for d in (diet_prefs.get("fasting_days") or [])}

    cond_rules = _build_condition_rules(user_profile.get("medical_history") or [])
    food_pool = filter_and_score_foods(user_profile, diet_prefs, df, cond_rules=cond_rules)

    days_of_week = ["Monday", "Tuesday", "Wednesday", "Thursday",
                    "Friday", "Saturday", "Sunday"]
    week_themes = ["Foundation", "Rhythm", "Deepen", "Consolidate"]
    spices = _DOSHA_SPICES.get(dominant_dosha, _DOSHA_SPICES["vata"])
    agni_info = _AGNI_ADJUST.get(agni_type, _AGNI_ADJUST["sama"])

    four_week_plan: list[dict] = []
    for week in range(1, 5):
        week_days: list[dict] = []
        for day_idx, day_name in enumerate(days_of_week):
            rng = _seeded_rng(user_id, week, day_idx)
            day_pool = list(food_pool)
            rng.shuffle(day_pool)

            is_fasting = day_name.lower() in fasting_days
            day_data = _build_day(day_pool, is_fasting, agni_type, rng)

            # Rotate spices across days
            day_spice = spices[day_idx % len(spices)]

            week_days.append({
                "day": day_idx + 1,
                "day_name": day_name,
                "is_fasting_day": is_fasting,
                "meals": day_data["meals"],
                "daily_macros": day_data["daily_macros"],
                "spice_of_day": day_spice,
            })

        four_week_plan.append({
            "week": week,
            "week_theme": week_themes[week - 1],
            "days": week_days,
            "agni_note": agni_info["notes"],
        })

    return {
        "plan_id": f"diet_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "dominant_dosha": dominant_dosha,
            "agni_type": agni_type,
            "diet_goal": diet_prefs.get("diet_goal", "general_wellness"),
            "dietary_type": diet_prefs.get("dietary_type", "vegetarian"),
            "gut_issue": diet_prefs.get("gut_health_issue", "healthy"),
            "intermittent_fasting": diet_prefs.get("intermittent_fasting", "no"),
            "water_intake": diet_prefs.get("water_intake"),
            "active_condition_protocols": cond_rules["active"],
            "current_season": season or None,
        },
        "four_week_plan": four_week_plan,
        "meal_timing": _MEAL_TIMING.get(dominant_dosha, _MEAL_TIMING["vata"]),
        "spice_guide": spices,
        "ayurvedic_tips": _AYUR_TIPS.get(dominant_dosha, _AYUR_TIPS["vata"]),
        "disclaimer": (
            "This plan uses approximate nutritional values and Ayurvedic food qualities. "
            "Adjust portions to your appetite. Consult a qualified nutritionist or Vaidya "
            "before making significant dietary changes, especially with existing conditions."
        ),
        "enriched": False,
    }
