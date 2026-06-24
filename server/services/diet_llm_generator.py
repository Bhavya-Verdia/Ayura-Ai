"""
LLM-primary diet plan generator.

The rule engine (diet_plan_engine.py) builds a structured Ayurvedic brief from the
user's profile. This module sends that brief to the LLM and receives a complete 7-day
plan with real Indian meal names, Pathya-Apathya, and classical text references.

The rule engine is retained as a fallback if the LLM call fails.
"""
import json
from datetime import datetime, timezone
from ai.llm_client import llm_client
from core.logger import logger

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

# ── Condition Pathya-Apathya hints (anchors for the LLM) ─────────────────────
# These encode classical knowledge so the LLM's output stays grounded in text.
# The LLM supplements these with its own knowledge.
_PATHYA_APATHYA_HINTS: dict[str, dict] = {
    "diabetes": {
        "ayurvedic_name": "Prameha / Madhumeha",
        "pathya": ["bitter gourd (Karela)", "fenugreek seeds (Methi)", "barley (Yava)", "moong dal (Mudga)", "amla (Amalaki)", "turmeric (Haridra)", "neem leaves (Nimba)"],
        "apathya": ["sugar", "jaggery in excess", "white rice", "maida/refined flour", "sweet fruits", "heavy dairy", "cold drinks"],
        "classical_ref": "Charaka Chikitsa Sthana 6 (Prameha Chikitsa); Ashtanga Hridayam Nidana 10",
    },
    "hypertension": {
        "ayurvedic_name": "Rakta Gata Vata / Uchcha Rakta Chapa",
        "pathya": ["garlic (Lasuna)", "amla", "pomegranate (Dadima)", "cucumber", "banana (Kadali)", "celery", "moong dal", "barley"],
        "apathya": ["excess salt", "pickles", "processed foods", "red meat", "alcohol", "excess chilli", "heavy fried foods"],
        "classical_ref": "Charaka Chikitsa 28 (Vatavyadhi); Ashtanga Hridayam Chikitsa 20",
    },
    "pcos": {
        "ayurvedic_name": "Artava Dushti / Pushpa Dushti",
        "pathya": ["flaxseeds (Atasi)", "fenugreek (Methi)", "spearmint (Pudina)", "amla", "sesame seeds", "moong dal", "millet (Shyamaka)"],
        "apathya": ["sugar", "refined carbs", "heavy dairy", "red meat", "soy in excess", "cold foods"],
        "classical_ref": "Charaka Chikitsa 30 (Yonivyapad); Astanga Samgraha",
    },
    "hypothyroid": {
        "ayurvedic_name": "Galaganda / Kapha-Vata Vyadhi",
        "pathya": ["coconut oil", "pumpkin seeds", "ginger (Shunthi)", "black pepper (Maricha)", "guggul-supported foods", "iodine-rich seaweeds (if available)"],
        "apathya": ["raw crucifers (cabbage, broccoli, cauliflower, kale)", "soy in excess", "gluten (if sensitive)", "refined sugar"],
        "classical_ref": "Charaka Nidana 11 (Galaganda); Sushruta Nidana 11",
    },
    "thyroid": {
        "ayurvedic_name": "Galaganda",
        "pathya": ["ginger", "black pepper", "coconut oil", "pumpkin seeds", "tulsi"],
        "apathya": ["raw crucifers", "soy"],
        "classical_ref": "Charaka Nidana 11; Sushruta Nidana 11",
    },
    "obesity": {
        "ayurvedic_name": "Sthoulya",
        "pathya": ["barley (Yava)", "old rice (Puranashali)", "moong dal (Mudga)", "honey (Madhu)", "bitter gourd", "drumstick (Shigru)", "horse gram (Kulatha)"],
        "apathya": ["new rice", "heavy wheat", "sugar", "excess dairy", "sweets", "cold foods", "sleeping after meals"],
        "classical_ref": "Charaka Sutra 21 (Sthoulya Nidana); Charaka Chikitsa 15",
    },
    "grahani": {
        "ayurvedic_name": "Grahani (Irritable Bowel / Malabsorption)",
        "pathya": ["Peya (thin rice gruel)", "Yavagu (thick gruel)", "pomegranate (Dadima)", "moong dal soup (thin)", "buttermilk (Takra) with ginger and rock salt", "bael fruit (Bilwa)"],
        "apathya": ["raw vegetables", "sour foods (curd, sour fruits)", "heavy dairy", "fried foods", "cold water", "incompatible food combinations (Viruddha Ahara)", "eating before previous meal is digested"],
        "classical_ref": "Charaka Chikitsa 15 (Grahani Chikitsa); Ashtanga Hridayam Nidana 8",
    },
    "ibs": {
        "ayurvedic_name": "Grahani / Atisara",
        "pathya": ["bael fruit (Bilwa)", "pomegranate", "Peya", "ginger tea", "moong dal soup", "cumin water (Jeeraka Jala)"],
        "apathya": ["raw vegetables", "gas-forming foods (cabbage, broccoli, beans)", "cold milk", "fried foods"],
        "classical_ref": "Charaka Chikitsa 15; Ashtanga Hridayam Chikitsa 9",
    },
    "arsha": {
        "ayurvedic_name": "Arsha (Haemorrhoids / Piles)",
        "pathya": ["horse gram (Kulatha)", "wheat (Godhuma) without bran loss", "old rice", "buttermilk", "drumstick (Shigru) flowers", "Haritaki (Chebulic myrobalan)", "pomegranate"],
        "apathya": ["excess spicy food", "fried food", "beans causing flatulence", "sitting for long hours after eating", "suppression of natural urges"],
        "classical_ref": "Charaka Chikitsa 14 (Arsha Chikitsa); Sushruta Nidana 2",
    },
    "anemia": {
        "ayurvedic_name": "Pandu Roga",
        "pathya": ["pomegranate (Dadima)", "amla (Amalaki)", "dates (Kharjura)", "beetroot", "spinach (Palaka) cooked with iron vessel or sesame", "sesame seeds (Tila)", "jaggery (Guda) with amla"],
        "apathya": ["clay eating", "excess raw food", "cold water", "curd with milk", "excess exercise during treatment"],
        "classical_ref": "Charaka Chikitsa 16 (Pandu Roga Chikitsa); Ashtanga Hridayam Chikitsa 13",
    },
    "fatty_liver": {
        "ayurvedic_name": "Yakrit Vikara / Yakrit Vriddhi",
        "pathya": ["turmeric (Haridra)", "amla", "kutki (Picrorhiza kurroa)", "moong dal", "leafy greens (cooked)", "bitter gourd", "garlic"],
        "apathya": ["alcohol (absolute contraindication)", "excess oil and fat", "processed foods", "sugar", "red meat", "cold foods"],
        "classical_ref": "Charaka Chikitsa 18 (Kamala Chikitsa); Sushruta Uttara 44",
    },
    "kidney_disease": {
        "ayurvedic_name": "Mutraghata / Mutrakrichra / Vrikkavikara",
        "pathya": ["old rice (Puranashali)", "moong dal (very well cooked)", "barley water (Yava Jala)", "apple", "cooked cabbage (low potassium)"],
        "apathya": ["banana (high potassium)", "tomato", "spinach in large amounts", "excess protein", "excess salt", "pickle", "sour fruits"],
        "classical_ref": "Charaka Chikitsa 26 (Mutraghata); Sushruta Nidana 3",
    },
    "amavata": {
        "ayurvedic_name": "Amavata (Rheumatoid Arthritis)",
        "pathya": ["ginger (Shunthi) — most important", "garlic (Lasuna)", "horse gram (Kulatha) soup", "castor oil (Eranda) with warm water", "moong dal with turmeric", "Rasona Kshira (garlic milk)"],
        "apathya": ["curd (Dadhi)", "fish", "black gram (Urad)", "new rice", "cold foods", "refrigerated food", "incompatible food combinations"],
        "classical_ref": "Madhava Nidana 25 (Amavata Nidana); Yogaratnakara Amavata Chikitsa",
    },
    "rheumatoid_arthritis": {
        "ayurvedic_name": "Amavata",
        "pathya": ["ginger", "garlic", "horse gram soup", "turmeric milk", "moong dal"],
        "apathya": ["curd", "black gram", "cold foods", "fried foods", "fermented foods"],
        "classical_ref": "Madhava Nidana 25",
    },
    "asthma": {
        "ayurvedic_name": "Tamaka Shwasa",
        "pathya": ["ginger (Shunthi)", "black pepper (Maricha)", "long pepper (Pippali)", "honey (Madhu)", "warm foods", "Tulsi tea", "light easily digestible foods"],
        "apathya": ["cold foods", "cold water", "curd", "banana", "ice cream", "fried foods", "excess sweet taste", "fish and dairy together"],
        "classical_ref": "Charaka Chikitsa 17 (Shwasa Chikitsa); Ashtanga Hridayam Chikitsa 4",
    },
    "migraine": {
        "ayurvedic_name": "Ardhavabhedaka / Suryavarta",
        "pathya": ["coriander seeds water", "amla", "pomegranate", "moong dal", "cucumber", "cooling foods for Pitta type"],
        "apathya": ["excess sour, salty, pungent foods", "red wine/alcohol", "aged cheese", "chocolate", "onion in excess", "skipping meals"],
        "classical_ref": "Charaka Sutra 20; Ashtanga Hridayam Uttara 23",
    },
    "psoriasis": {
        "ayurvedic_name": "Kitibha Kushtha / Mandal Kushtha",
        "pathya": ["neem (Nimba) preparations", "turmeric", "bitter gourd", "amla", "moong dal", "old rice", "cucumber"],
        "apathya": ["fish and milk together", "sour foods", "sesame + milk", "meat + milk", "salt + milk", "incompatible combinations"],
        "classical_ref": "Charaka Chikitsa 7 (Kushtha Chikitsa); Ashtanga Hridayam Chikitsa 19",
    },
    "constipation": {
        "ayurvedic_name": "Vibandha / Anaha",
        "pathya": ["warm water in morning", "castor oil (Eranda) in milk", "figs (Anjeer)", "flaxseeds", "psyllium husk", "triphala (Haritaki, Amalaki, Bibhitaki)", "ghee in food"],
        "apathya": ["dry, light foods in excess", "cold water", "suppressing the urge to defecate", "excess travel/exertion"],
        "classical_ref": "Charaka Sutra 28; Ashtanga Hridayam Chikitsa 9",
    },
    "acidity": {
        "ayurvedic_name": "Amlapitta",
        "pathya": ["coconut water (Narikela Jala)", "pomegranate", "coriander seeds water", "amla", "fennel (Shatapushpa)", "old rice", "ghee", "milk (warm)"],
        "apathya": ["sour foods", "fermented foods", "chilli", "garlic", "onion", "coffee", "alcohol", "eating before previous meal digests"],
        "classical_ref": "Charaka Chikitsa 15 (Amlapitta); Ashtanga Hridayam Chikitsa 10",
    },
    "thyroid_disorder": {
        "ayurvedic_name": "Galaganda",
        "pathya": ["coconut oil", "ginger", "black pepper", "pumpkin seeds", "selenium-rich foods"],
        "apathya": ["raw crucifers", "excess soy", "refined sugar"],
        "classical_ref": "Charaka Nidana 11",
    },
}

_COND_ALIASES = {
    "type2_diabetes": "diabetes", "prediabetes": "diabetes", "insulin_resistance": "diabetes",
    "bp": "hypertension", "high_blood_pressure": "hypertension",
    "polycystic_ovary": "pcos", "polycystic_ovarian_syndrome": "pcos",
    "hypothyroidism": "hypothyroid", "thyroidism": "thyroid",
    "overweight": "obesity", "weight_management": "obesity",
    "liver_disease": "fatty_liver", "nafld": "fatty_liver",
    "ckd": "kidney_disease", "kidney_failure": "kidney_disease",
    "iron_deficiency": "anemia", "iron_deficiency_anemia": "anemia",
    "ibd": "grahani", "crohns": "grahani", "ulcerative_colitis": "grahani",
    "irritable_bowel_syndrome": "ibs",
    "piles": "arsha", "hemorrhoids": "arsha", "haemorrhoids": "arsha",
    "rheumatoid": "amavata", "ra": "amavata",
    "acid_reflux": "acidity", "gerd": "acidity", "heartburn": "acidity",
    "skin_disease": "psoriasis", "eczema": "psoriasis",
}

# ── Agni descriptions ─────────────────────────────────────────────────────────
_AGNI_DESC = {
    "sama":    "balanced and strong — can handle a varied diet with regular timing",
    "manda":   "slow and sluggish (Kapha dominant) — needs light, warm, spiced, easily digestible foods; avoid heavy meals; fasting one meal helps kindle Agni",
    "tikshna": "sharp and intense (Pitta dominant) — must not skip meals; needs regular nourishment; avoid fasting; favour cooling foods",
    "vishama": "irregular and variable (Vata dominant) — needs grounding, consistent meal times; warm, moist, easily digestible foods; most sensitive to cold and irregular eating",
}

# ── Ama descriptions ──────────────────────────────────────────────────────────
_AMA_DESC = {
    "high":     "high toxic load — Ama is present and must be cleared first; all foods should be Deepaniya (Agni-kindling) and Pachana (Ama-digesting); avoid heavy, sour, cold, and incompatible foods",
    "moderate": "moderate Ama — dietary refinement needed; avoid Ama-producing combinations; favour ginger, cumin, turmeric",
    "low":      "minimal Ama — diet can be more varied",
    "none":     "no Ama — normal Ayurvedic diet appropriate",
}

# ── Season Ritucharya guidance ─────────────────────────────────────────────────
_SEASON_GUIDANCE = {
    "vasanta": "Vasanta Ritucharya (Spring): Kapha accumulated in winter now liquefies — kindle Agni with pungent, bitter, astringent foods. Avoid heavy dairy, excess sweet, oily foods. Favour: barley, bitter gourd, light grains. Classical reference: Ashtanga Hridayam Sutra 3",
    "grishma": "Grishma Ritucharya (Summer): Agni is naturally weak; body needs cooling, sweet, hydrating foods. Avoid pungent, sour, salty, hot foods. Favour: coconut water, cucumber, amla, sweet fruits, light rice. Reference: Charaka Sutra 6.27",
    "varsha":  "Varsha Ritucharya (Rainy Season): Agni is at its lowest; Vata is aggravated by cool, damp winds. Light, warm, freshly cooked foods essential. Avoid leafy greens (worm/bacteria risk), river water. Favour: moong dal, old rice, ginger, warm soups. Reference: Charaka Sutra 6.32",
    "sharad":  "Sharad Ritucharya (Autumn): Post-monsoon Pitta aggravation — cooling, sweet, astringent foods. Avoid excess sour, salty, pungent. Favour: bitter gourd, pomegranate, amla, light rice, ghee. This season is best for Virechana if Pitta is aggravated. Reference: Charaka Sutra 6.41",
    "hemanta": "Hemanta Ritucharya (Early Winter): Agni is strongest — can handle heavier, nourishing foods. Ideal season for Brimhana (nourishing) diet. Favour: wheat, sesame, ghee, milk, meat (if applicable), urad dal, jaggery. Reference: Charaka Sutra 6.7",
    "shishira": "Shishira Ritucharya (Late Winter): Similar to Hemanta; deep Agni, need for Snehana (oleation) diet. Sour, salty, oily foods appropriate. Favour: ghee, sesame, warming spices, nourishing grains. Reference: Ashtanga Hridayam Sutra 3",
}

# ── Macro targets ─────────────────────────────────────────────────────────────
def _target_calories(user_profile: dict, diet_prefs: dict) -> int:
    age = int(user_profile.get("age") or 30)
    gender = (user_profile.get("gender") or "male").lower()
    bmi = (user_profile.get("bmi_category") or "normal").lower()
    goal = diet_prefs.get("diet_goal") or "general_wellness"

    base = 1800 if gender == "female" else 2000
    if bmi in ("overweight", "obese"):
        base -= 300
    if bmi == "underweight":
        base += 200
    if age > 60:
        base -= 100
    if age < 20:
        base += 100
    if goal == "weight_loss":
        base -= 300
    elif goal == "muscle_support":
        base += 200

    return max(1200, min(3000, base))


# ── Brief builder ─────────────────────────────────────────────────────────────
def _build_brief(user_profile: dict, diet_prefs: dict) -> str:
    dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
    vikriti = (user_profile.get("vikriti_dominant") or dominant_dosha).lower()
    vikriti_secondary = (user_profile.get("vikriti_secondary") or "").lower()
    agni = (user_profile.get("agni_type") or "sama").lower()
    ama = (user_profile.get("ama_indicator") or "none").lower()
    ojas = (user_profile.get("ojas_level") or "moderate").lower()
    koshtha = (user_profile.get("koshtha") or "").lower()
    age = user_profile.get("age") or "unknown"
    gender = (user_profile.get("gender") or "not specified").title()
    is_pregnant = user_profile.get("pregnancy_or_nursing") or False
    season = (user_profile.get("current_season") or "").lower()
    stress = (user_profile.get("stress_level") or "moderate").lower()
    sleep = (user_profile.get("sleep_quality") or "moderate").lower()
    bmi = (user_profile.get("bmi_category") or "normal").lower()
    name = user_profile.get("name") or user_profile.get("full_name") or "the patient"

    diet_type = diet_prefs.get("dietary_type") or "vegetarian"
    allergies = diet_prefs.get("food_allergies") or []
    intolerances = diet_prefs.get("food_intolerances") or []
    gut = diet_prefs.get("gut_health_issue") or "healthy"
    goal = diet_prefs.get("diet_goal") or "general_wellness"
    fasting_days = diet_prefs.get("fasting_days") or []
    if_window = diet_prefs.get("intermittent_fasting") or "no"
    water = diet_prefs.get("water_intake") or "1-2L"

    conditions = user_profile.get("medical_history") or []
    # Normalize conditions
    norm_conditions = []
    for c in conditions:
        key = c.lower().replace(" ", "_")
        norm_conditions.append(_COND_ALIASES.get(key, key))

    # Build condition Pathya-Apathya block
    cond_blocks = []
    seen = set()
    for cond in norm_conditions:
        canon = _COND_ALIASES.get(cond, cond)
        if canon in seen:
            continue
        seen.add(canon)
        hint = _PATHYA_APATHYA_HINTS.get(canon)
        if hint:
            block = (
                f"  • {cond.replace('_', ' ').title()} ({hint['ayurvedic_name']}):\n"
                f"    Pathya: {', '.join(hint['pathya'][:6])}\n"
                f"    Apathya: {', '.join(hint['apathya'][:5])}\n"
                f"    Ref: {hint['classical_ref']}"
            )
        else:
            block = (
                f"  • {cond.replace('_', ' ').title()} — use your classical Ayurvedic knowledge "
                f"to determine Pathya-Apathya. Cite the relevant Samhita chapter."
            )
        cond_blocks.append(block)

    cond_section = "\n".join(cond_blocks) if cond_blocks else "  • None reported"
    season_guidance = _SEASON_GUIDANCE.get(season, "No specific season provided — use general Ayurvedic diet principles.")

    hard_constraints = []
    hard_constraints.append(f"Dietary type: {diet_type} (STRICTLY honour — never recommend non-{diet_type} items)")
    if allergies:
        hard_constraints.append(f"ALLERGIES (absolutely avoid): {', '.join(allergies)}")
    if intolerances:
        hard_constraints.append(f"Intolerances (avoid): {', '.join(intolerances)}")
    if fasting_days:
        hard_constraints.append(f"Fasting days: {', '.join(fasting_days)} — only Phalahar (fruits, milk, nuts) on these days")
    if if_window != "no":
        hard_constraints.append(f"Intermittent fasting: {if_window} window — adjust meal timing accordingly")
    if is_pregnant:
        hard_constraints.append(
            "PREGNANCY / NURSING — absolutely avoid: papaya (raw/ripe), pineapple, excess fenugreek seeds, "
            "excess aloe vera, high-dose turmeric, hot spices in large amounts, liver/organ meat, "
            "unpasteurised dairy; all meals must be Satvic, warm, and nourishing (Garbhini Paricharya)"
        )

    target_cal = _target_calories(user_profile, diet_prefs)

    koshtha_line = ""
    if koshtha:
        _KOSHTHA_DESC = {
            "krura": "Krura Koshtha (hard bowel — constipation tendency) — use more ghee, warm water, soaked dried fruits; avoid dry/astringent foods",
            "mridu": "Mridu Koshtha (soft bowel — loose stool tendency) — favour astringent, binding foods; avoid excess oil, sour, and heavy dairy",
            "madhyama": "Madhyama Koshtha (balanced bowel) — general Ayurvedic diet applies",
        }
        koshtha_line = f"\n  Koshtha (bowel constitution): {_KOSHTHA_DESC.get(koshtha, koshtha.title())}"

    brief = f"""PATIENT: {name} | Age: {age} | Gender: {gender}{' | PREGNANT/NURSING' if is_pregnant else ''}

PRAKRITI & VIKRITI:
  Prakriti (constitutional): {dominant_dosha.title()}
  Vikriti (current imbalance): {vikriti.title()}{(' + ' + vikriti_secondary.title()) if vikriti_secondary else ''}
  (If Prakriti ≠ Vikriti, treat the Vikriti preferentially while supporting Prakriti)

DIGESTIVE FIRE (AGNI):
  Type: {agni.title()} — {_AGNI_DESC.get(agni, 'balanced')}{koshtha_line}

AMA STATUS:
  Level: {ama.title()} — {_AMA_DESC.get(ama, 'none present')}

OJAS & VITALITY:
  Ojas level: {ojas.title()}
  Stress: {stress.title()} | Sleep quality: {sleep.title()}
  BMI category: {bmi.title()}

CURRENT SEASON (RITUCHARYA):
  {season_guidance}

MEDICAL CONDITIONS (Pathya-Apathya required for each):
{cond_section}

GUT HEALTH: {gut.replace('_', ' ').title()}

HARD DIETARY CONSTRAINTS (never violate these):
  {chr(10).join(f'  {i+1}. {c}' for i, c in enumerate(hard_constraints))}

THERAPEUTIC GOAL: {goal.replace('_', ' ').title()}
WATER INTAKE: {water} per day
TARGET CALORIES: approximately {target_cal} kcal/day"""

    return brief


# ── Allergen term lookup for post-LLM safety scan ────────────────────────────
_ALLERGEN_TERMS: dict[str, list[str]] = {
    "gluten": ["wheat", "gluten", "maida", "atta", "bread", "roti", "chapati", "poha", "semolina",
               "suji", "rava", "barley", "oats", "seitan", "naan", "paratha"],
    "dairy": ["milk", "curd", "yogurt", "ghee", "butter", "cream", "paneer", "cheese", "lassi",
              "buttermilk", "kheer", "raita", "mawa", "khoa"],
    "nuts_tree": ["almond", "cashew", "walnut", "pistachio", "pine nut", "hazelnut", "chestnut",
                  "badam", "kaju", "akhrot"],
    "peanuts": ["peanut", "groundnut", "mungphali"],
    "soy": ["soy", "tofu", "tempeh", "edamame", "soybean"],
    "eggs": ["egg", "omelet", "omelette", "anda"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "scallop"],
    "fish": ["fish", "salmon", "tuna", "mackerel", "pomfret", "rohu", "hilsa", "sardine"],
    "sesame": ["sesame", "til", "tahini", "gingelly"],
    "mustard": ["mustard", "sarson", "rai"],
}


def _flag_allergens(weekly_plan: dict, allergies: list[str], intolerances: list[str]) -> dict:
    """Scan key_ingredients and meal_name for allergen terms and flag meals."""
    allergen_terms: set[str] = set()
    for a in (allergies or []):
        allergen_terms.update(_ALLERGEN_TERMS.get(a, [a.lower()]))
    if not allergen_terms:
        return weekly_plan
    for day_data in weekly_plan.values():
        if not isinstance(day_data, dict):
            continue
        for meal_key in ("breakfast", "lunch", "snack", "dinner"):
            meal = day_data.get(meal_key)
            if not isinstance(meal, dict):
                continue
            text = (meal.get("meal_name", "") + " " + " ".join(meal.get("key_ingredients", []))).lower()
            found = [t for t in allergen_terms if t in text]
            if found:
                meal["allergen_warning"] = True
                meal["allergen_terms"] = found
    return weekly_plan


# ── System and user prompts ───────────────────────────────────────────────────
SYSTEM_PROMPT = """\
You are a senior Vaidya (M.D. Ayurveda, BAMS+) and clinical nutritionist with mastery of \
Charaka Samhita, Ashtanga Hridayam, Sushruta Samhita, Madhava Nidana, and Bhavaprakasha. \
You generate clinically precise, highly personalised Ayurvedic diet plans.

RULES — these are non-negotiable:
1. Generate REAL Indian meal names. Write "Moong Dal Khichdi with ajwain-hing tadka" — \
   not food lists like "Moong Dal + Rice + Ajwain".
2. Every meal must have an Ayurvedic rationale citing Rasa (taste), Guna (quality), \
   Virya (potency), Vipaka (post-digestive effect).
3. For every medical condition, provide classical Pathya-Apathya with Samhita references.
4. Flag all Viruddha Ahara (incompatible food combinations) relevant to this patient.
5. STRICTLY honour all hard constraints — dietary type, allergies, intolerances.
6. Use the patient's Agni type to determine meal heaviness and frequency.
7. High Ama = all meals must be Deepaniya + Pachana; no heavy, sour, or fermented foods.
8. Each day should have a therapeutic theme (e.g., "Ama Pachana", "Agni Deepana", "Ojas Building").
9. Include a special Ayurvedic drink (Kashaya, Kwatha, herbal milk, or medicinal water) \
   for each day with timing and rationale.
10. Meals should reflect genuine Indian culinary tradition — realistic, preparable at home.
11. Structure the plan as a 4-week Ayurvedic progression: \
    Week 1 (Ama Pachana): Light, Deepaniya-Pachana foods — clear Ama. Avoid heavy, sour, fermented. \
    Week 2 (Agni Deepana): Kindle Agni with warming spices. Gradually richer meals. \
    Week 3 (Brimhana): Nourishing foods — Ojas-building. Ghee, nuts, root vegetables where appropriate. \
    Week 4 (Rasayana): Rejuvenating, seasonal, maintenance. Introduce Rasayana ingredients (amla, ashwagandha milk, dates). \
    Week 1 must be FULL DETAIL (all meal fields). Weeks 2-4 are COMPACT (meal names only as strings).

Respond ONLY with valid JSON. No preamble. No markdown fences. No explanation outside JSON.
"""

USER_PROMPT_TEMPLATE = """\
Generate a complete 4-week personalised Ayurvedic diet plan for this patient:

{brief}

Return this exact JSON structure — no extra keys, no preamble, no markdown fences:
{{
  "plan_title": "string — personalised title, e.g. 'Vata-Pacifying 4-Week Renewal Plan for Ravi'",
  "plan_description": "string — 2-3 sentences: clinical rationale, dosha logic, conditions addressed",
  "pathya_apathya": {{
    "pathya": ["food/preparation — 1 sentence Ayurvedic reason"],
    "apathya": ["food/preparation — 1 sentence reason to avoid"],
    "viruddha_ahara_warnings": ["combination to avoid — classical reason"],
    "classical_reference": "primary Samhita reference(s) for this case"
  }},
  "weeks": [
    {{
      "week_number": 1,
      "phase": "Ama Pachana",
      "phase_description": "string — 1-2 sentences on this week's therapeutic focus",
      "daily_plan": {{
        "Monday": {{
          "theme": "string — 2-3 word therapeutic theme",
          "breakfast": {{
            "meal_name": "string — real Indian dish name",
            "description": "string — what it is + brief preparation in 1 sentence",
            "key_ingredients": ["ingredient 1", "ingredient 2"],
            "portion": "string — realistic serving e.g. '1 katori (150ml) with 1 tsp ghee'",
            "ayurvedic_note": "string — Rasa-Guna-Virya-Vipaka reasoning in 1-2 sentences",
            "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}
          }},
          "lunch": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "snack": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "dinner": {{"meal_name": "string", "description": "string", "key_ingredients": [], "portion": "string", "ayurvedic_note": "string", "macros_approx": {{"calories": 0, "protein_g": 0, "carbs_g": 0, "fat_g": 0}}}},
          "special_drink": {{
            "name": "string — e.g. 'CCF Tea (Cumin-Coriander-Fennel)'",
            "when": "string — e.g. 'Morning on empty stomach'",
            "recipe": "string — brief recipe in 1 sentence",
            "rationale": "string — therapeutic reason"
          }}
        }},
        "Tuesday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Wednesday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Thursday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Friday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Saturday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}},
        "Sunday": {{"theme": "string", "breakfast": {{}}, "lunch": {{}}, "snack": {{}}, "dinner": {{}}, "special_drink": {{}}}}
      }}
    }},
    {{
      "week_number": 2,
      "phase": "Agni Deepana",
      "phase_description": "string — 1-2 sentences on this week's therapeutic focus",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "Indian meal name", "lunch": "Indian meal name", "snack": "Indian meal name", "dinner": "Indian meal name", "special_drink": "drink name — timing"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }},
    {{
      "week_number": 3,
      "phase": "Brimhana",
      "phase_description": "string",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }},
    {{
      "week_number": 4,
      "phase": "Rasayana",
      "phase_description": "string",
      "daily_plan": {{
        "Monday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Tuesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Wednesday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Thursday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Friday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Saturday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}},
        "Sunday": {{"theme": "string", "breakfast": "string", "lunch": "string", "snack": "string", "dinner": "string", "special_drink": "string"}}
      }}
    }}
  ],
  "condition_coaching": "string — 2-3 sentences specific to their conditions and how this diet addresses them",
  "hydration_guidance": "string — specific guidance for their dosha, water intake, and gut issue",
  "fasting_guidance": "string — Ayurvedic guidance on their fasting pattern (empty string if none)",
  "seasonal_note": "string — how this plan aligns with Ritucharya (empty string if season unknown)",
  "ahar_vidhi": "string — 2-3 key Ahar Vidhi (eating rules) specific to this patient's Agni and Dosha",
  "motivational_note": "string — 1 personalised, clinically grounded sentence"
}}
"""


# ── Main generator ────────────────────────────────────────────────────────────
async def generate_diet_plan_llm(
    user_profile: dict,
    diet_prefs: dict,
) -> dict | None:
    """
    Returns a complete diet plan dict or None on failure (caller falls back to rule engine).
    """
    try:
        brief = _build_brief(user_profile, diet_prefs)
        prompt = USER_PROMPT_TEMPLATE.replace("{brief}", brief)

        response_text = await llm_client.generate(
            prompt=prompt,
            system_prompt=SYSTEM_PROMPT,
            json_mode=True,
        )

        data = json.loads(response_text)
        if "error" in data:
            raise ValueError(f"LLM returned error: {data['error']}")
        if "weeks" not in data or not isinstance(data["weeks"], list):
            raise ValueError("LLM response missing 'weeks' array")

        dominant_dosha = (user_profile.get("dominant_dosha") or "vata").lower()
        agni_type = (user_profile.get("agni_type") or "sama").lower()
        conditions = user_profile.get("medical_history") or []
        norm_conds = []
        for c in conditions:
            k = c.lower().replace(" ", "_")
            norm_conds.append(_COND_ALIASES.get(k, k))

        user_id = str(user_profile.get("id") or user_profile.get("_id") or "anon")

        _DAY_ALIASES = {
            "monday": "monday", "tuesday": "tuesday", "wednesday": "wednesday",
            "thursday": "thursday", "friday": "friday", "saturday": "saturday", "sunday": "sunday",
            "mon": "monday", "tue": "tuesday", "wed": "wednesday",
            "thu": "thursday", "fri": "friday", "sat": "saturday", "sun": "sunday",
        }

        # Tag fasting days only on week 1 (full detail) and run allergen check on it
        fasting_days_raw = diet_prefs.get("fasting_days") or []
        fasting_set = {d.lower() for d in fasting_days_raw}
        weeks = data["weeks"]
        week1_daily = weeks[0].get("daily_plan", {}) if weeks else {}
        for day_name, day_data in week1_daily.items():
            if isinstance(day_data, dict):
                canonical = _DAY_ALIASES.get(day_name.lower(), day_name.lower())
                day_data["is_fasting"] = canonical in fasting_set
        allergies = diet_prefs.get("food_allergies") or []
        intolerances = diet_prefs.get("food_intolerances") or []
        week1_daily = _flag_allergens(week1_daily, allergies, intolerances)
        if weeks:
            weeks[0]["daily_plan"] = week1_daily

        # weekly_plan alias → week 1 daily for backward-compat with any existing refs
        weekly_plan = week1_daily

        result = {
            "plan_id": f"diet_{user_id}_{int(datetime.now(timezone.utc).timestamp())}",
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "generation_method": "llm_primary",
            "enriched": True,
            "enrichment_model": llm_client.provider,
            "user_summary": {
                "dominant_dosha": dominant_dosha,
                "agni_type": agni_type,
                "diet_goal": diet_prefs.get("diet_goal", "general_wellness"),
                "dietary_type": diet_prefs.get("dietary_type", "vegetarian"),
                "gut_issue": diet_prefs.get("gut_health_issue", "healthy"),
                "intermittent_fasting": diet_prefs.get("intermittent_fasting", "no"),
                "water_intake": diet_prefs.get("water_intake"),
                "active_condition_protocols": list(set(norm_conds)),
                "current_season": (user_profile.get("current_season") or "").lower() or None,
            },
            "plan_title": data.get("plan_title", "Personalised Ayurvedic Diet Plan"),
            "plan_description": data.get("plan_description", ""),
            "pathya_apathya": data.get("pathya_apathya", {}),
            "weekly_plan": weekly_plan,
            "diet_weeks": weeks,
            "condition_coaching": data.get("condition_coaching", ""),
            "hydration_guidance": data.get("hydration_guidance", ""),
            "fasting_guidance": data.get("fasting_guidance", ""),
            "seasonal_note": data.get("seasonal_note", ""),
            "ahar_vidhi": data.get("ahar_vidhi", ""),
            "motivational_note": data.get("motivational_note", ""),
            # Deterministic Ayurvedic blocks — same as rule engine, no LLM call needed
            "meal_timing": _MEAL_TIMING.get(dominant_dosha, _MEAL_TIMING.get("vata", {})),
            "spice_guide": _DOSHA_SPICES.get(dominant_dosha, _DOSHA_SPICES.get("vata", [])),
            "ayurvedic_tips": _AYUR_TIPS.get(dominant_dosha, ""),
            "disclaimer": (
                "This plan is generated by an AI Vaidya and is for wellness and educational purposes. "
                "Classical text references are approximate and should be verified. "
                "Consult a qualified Ayurvedic practitioner before beginning any therapeutic diet, "
                "especially with existing medical conditions."
            ),
        }

        # ── Deterministic Ahara safety layer (Viruddha + allergens, all 4 weeks) ──
        # Runs after LLM generation so safety never depends on the model self-reporting.
        from services.ahara_safety import apply_ahara_safety
        result = apply_ahara_safety(result, allergies, intolerances)

        return result

    except Exception as e:
        logger.error(f"LLM diet generation failed: {e}")
        return None
