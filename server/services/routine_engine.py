"""
Dinacharya (Daily Routine) Engine
Produces a fully personalised 7-day Ayurvedic daily routine.

Personalisation signals used:
  Tier A: dominant_dosha · secondary_dosha · vikriti · agni_type · age · gender
  Tier B: season · conditions · occupation_type · gym_schedule · yoga_schedule
  Fasting: intermittent_fasting window · fasting_days
"""

from datetime import datetime, timezone

# ── Season → Ritucharya metadata ──────────────────────────────────────────────
_SEASON_MAP = {
    "shishira": {"label": "Shishira (Late Winter)",  "wake": {"vata": "6:30", "pitta": "5:45", "kapha": "5:00"}, "agni": "strong",    "peak_dosha": "vata"},
    "vasanta":  {"label": "Vasanta (Spring)",         "wake": {"vata": "6:00", "pitta": "5:30", "kapha": "4:45"}, "agni": "mild",      "peak_dosha": "kapha"},
    "grishma":  {"label": "Grishma (Summer)",         "wake": {"vata": "6:00", "pitta": "5:00", "kapha": "5:00"}, "agni": "weak",      "peak_dosha": "pitta"},
    "varsha":   {"label": "Varsha (Monsoon)",         "wake": {"vata": "6:30", "pitta": "5:30", "kapha": "5:15"}, "agni": "very_weak", "peak_dosha": "vata"},
    "sharad":   {"label": "Sharad (Autumn)",          "wake": {"vata": "5:45", "pitta": "5:15", "kapha": "4:45"}, "agni": "strong",    "peak_dosha": "pitta"},
    "hemanta":  {"label": "Hemanta (Early Winter)",   "wake": {"vata": "6:00", "pitta": "5:30", "kapha": "4:30"}, "agni": "strongest", "peak_dosha": "kapha"},
}
_DEFAULT_SEASON = _SEASON_MAP["sharad"]

# ── Agni-type meal timing adjustments ─────────────────────────────────────────
_AGNI_NOTES = {
    "manda": {
        "breakfast": "Manda Agni: delay breakfast by 45–60 min past your usual wake time. Start with hot ginger water first. Smaller, lighter portions only — heavy breakfast worsens slow Agni.",
        "lunch":     "Manda Agni: lunch is the main meal but keep portions moderate. Take 1/4 tsp Trikatu churna or sip ginger tea 15 min before to kindle fire. Eat only when genuinely hungry.",
        "snack":     "Manda Agni: skip the afternoon snack if not genuinely hungry. Kapha/Manda types accumulate Ama from snacking before previous meal is digested.",
        "dinner":    "Manda Agni: very light dinner — thin soup or khichdi only. Finish eating by 6 PM so overnight digestion is complete by morning.",
        "general":   "Your Agni type is Manda (slow/sluggish). Eat only when previous meal is fully digested — no snacking between meals unless genuinely hungry. Largest meal at 12–1 PM. Trikatu and ginger are your daily digestive allies.",
    },
    "tikshna": {
        "breakfast": "Tikshna Agni: eat breakfast on time — skipping aggravates your sharp Agni and leads to burning, acidity, and irritability. Cooling, sweet foods preferred.",
        "lunch":     "Tikshna Agni: never skip or delay lunch beyond 1 PM. Your Bhuta Agni begins digesting Dhatu tissue when the stomach is empty. Eat until 80% full — not more.",
        "snack":     "Tikshna Agni: a small snack at 3:30–4 PM prevents low-blood-sugar Pitta anger. Coconut water, sweet fruit, or fennel-coriander tea.",
        "dinner":    "Tikshna Agni: lighter than lunch but not minimal. Cooling foods. Avoid spicy, fermented food — Tikshna Agni at night drives Pitta hyperacidity.",
        "general":   "Your Agni type is Tikshna (sharp/intense). Never skip meals — your digestive fire burns internal Dhatus when empty. Eat cooling, sweet, properly cooked food. Avoid fasting unless medically supervised.",
    },
    "vishama": {
        "breakfast": "Vishama Agni: eat breakfast at the same time every single day regardless of hunger level — regularity anchors irregular Vata Agni. Warm, small, easily digestible.",
        "lunch":     "Vishama Agni: same time every day for lunch. Take CCF tea (cumin-coriander-fennel) 15 min before to prepare irregular Agni.",
        "snack":     "Vishama Agni: a small warm snack helps prevent Agni spikes between meals. Soaked dates or warm broth — nothing raw or cold.",
        "dinner":    "Vishama Agni: finish dinner by 7 PM maximum, same time every day. Inconsistent meal timing is the primary trigger for Vishama Agni worsening.",
        "general":   "Your Agni type is Vishama (irregular/variable). Meal time regularity is your primary medicine — eating at the same times daily is more important than what you eat. Avoid raw, cold, and heavy food.",
    },
    "sama": {
        "breakfast": None, "lunch": None, "snack": None, "dinner": None,
        "general":   "Your Agni is Sama (balanced) — maintain your current meal timing. Avoid excess fasting or overeating to keep it balanced.",
    },
}

# ── Age band ──────────────────────────────────────────────────────────────────
def _age_band(age: int) -> str:
    if age < 16: return "balya"
    if age < 40: return "yuva"
    if age < 60: return "madhyama"
    return "vriddha"

# ── Morning rituals base ──────────────────────────────────────────────────────
_MORNING_RITUALS_BASE = {
    "vata": [
        {"name": "Ushna Pana",       "instruction": "Drink 1 glass warm (not hot) water to gently stimulate bowels and clear overnight Ama.",                                                                                       "icon": "water",   "duration_min": 2},
        {"name": "Mala-Mutra Visarjana (Shaucha)", "instruction": "Answer nature's calls without delay — the warm water aids elimination. Never strain or suppress the urge (Vega Dharana aggravates Apana Vata; CS Sutrasthana 7). If Vata constipation persists, add 1 tsp warm ghee to the morning water.", "icon": "elimination", "duration_min": 5},
        {"name": "Danta Dhavana",    "instruction": "Brush with licorice (Yashtimadhu) or neem twig. Avoid harsh mint pastes — Vata mouth is dry and sensitive.",                                                                 "icon": "tooth",   "duration_min": 3},
        {"name": "Jihva Nirlekhana", "instruction": "Copper tongue scraper, 7–14 strokes back-to-front. Vata coating is thin, brownish, and may leave a metallic taste.",                                                         "icon": "tongue",  "duration_min": 2},
        {"name": "Nasya",            "instruction": "2 drops warm sesame oil per nostril; tilt head back 1 min. Lubricates dry Vata Pranavaha Srotas (respiratory channels).",                                                    "icon": "nose",    "duration_min": 3},
        {"name": "Kavala Gandusha",  "instruction": "Oil pulling with 1 tbsp warm sesame oil, 5–10 min. Strengthens gums, reduces Vata dryness and cracking in the oral cavity.",                                                 "icon": "mouth",   "duration_min": 10},
        {"name": "Abhyanga",         "instruction": "Full-body warm sesame oil self-massage for 15–20 min. Long strokes on limbs, circular on joints. The most grounding Vata practice of the day.",                              "icon": "massage", "duration_min": 20},
        {"name": "Snanam",           "instruction": "Warm (not hot) shower after Abhyanga. Hot water worsens Vata head-lightness and depletes Ojas.",                                                                              "icon": "bath",    "duration_min": 10},
    ],
    "pitta": [
        {"name": "Sheeta Pana",      "instruction": "1–2 glasses cool room-temperature water. Pitta wakes warm — cooling water settles morning fire before it spikes.",                                                            "icon": "water",   "duration_min": 2},
        {"name": "Mala-Mutra Visarjana (Shaucha)", "instruction": "Empty bladder and bowels on waking — do not suppress the urge (Adharaniya Vega; CS Sutrasthana 7). Pitta types often have urgent, loose morning stools (Drava/Mridu Koshtha) — this is normal Pitta Apana, not a problem.", "icon": "elimination", "duration_min": 5},
        {"name": "Danta Dhavana",    "instruction": "Neem twig or bitter tooth powder. Neem is Sheeta and anti-inflammatory — ideal for Pitta bleeding gums and sensitivity.",                                                    "icon": "tooth",   "duration_min": 3},
        {"name": "Jihva Nirlekhana", "instruction": "Copper scraper, 7–14 strokes. Pitta coating is yellow-orange with a slight bitter taste — a sign of Pitta Ama in the Kledaka Kapha.",                                        "icon": "tongue",  "duration_min": 2},
        {"name": "Anjana",           "instruction": "Rose water eye wash — pour into cupped palm, blink eyes in it 5–10 times. Soothes Pitta-sensitive, light-sensitive, or bloodshot eyes.",                                    "icon": "eye",     "duration_min": 2},
        {"name": "Nasya",            "instruction": "1–2 drops ghee or coconut oil per nostril. Sheeta Nasya pacifies sharp Pitta heat in Shira (head region).",                                                                  "icon": "nose",    "duration_min": 3},
        {"name": "Kavala Gandusha",  "instruction": "Oil pulling with coconut or sunflower oil, 5–10 min. Cools oral tissues and reduces Pitta inflammation and ulcers.",                                                          "icon": "mouth",   "duration_min": 10},
        {"name": "Abhyanga",         "instruction": "Coconut or sunflower oil, cooler strokes. Avoid vigorous friction in Pitta season. Focus on crown (Murdha) and soles of feet.",                                              "icon": "massage", "duration_min": 15},
        {"name": "Snanam",           "instruction": "Cool or lukewarm shower. A genuinely cool shower after Abhyanga is the most effective Pitta settling morning practice.",                                                       "icon": "bath",    "duration_min": 8},
    ],
    "kapha": [
        {"name": "Ushna Pana",       "instruction": "1 glass hot water with grated ginger and lemon. Kindling Agni is the first Kapha morning task — before anything else.",                                                      "icon": "water",   "duration_min": 3},
        {"name": "Mala-Mutra Visarjana (Shaucha)", "instruction": "Eliminate on waking — the hot ginger-lemon water stimulates sluggish Kapha bowels. Never suppress natural urges (CS Sutrasthana 7). A complete morning bowel movement is essential to clear overnight Kapha Ama.", "icon": "elimination", "duration_min": 5},
        {"name": "Danta Dhavana",    "instruction": "Neem twig or Trikatu-based tooth powder — pungent and bitter. Kapha accumulates heavy Ama overnight; aggressive cleaning is required.",                                      "icon": "tooth",   "duration_min": 4},
        {"name": "Jihva Nirlekhana", "instruction": "Heavy white coating on your tongue is Kapha Ama. Scrape 7–14 strokes until clean. The coating thickness is your daily Ama-meter.",                                          "icon": "tongue",  "duration_min": 3},
        {"name": "Nasya",            "instruction": "2 drops warm Anu Taila or mustard oil per nostril. Clears Kapha mucus from nasal passages before exercise.",                                                                  "icon": "nose",    "duration_min": 3},
        {"name": "Kavala Gandusha",  "instruction": "Oil pulling with mustard or sesame oil, 5 min. Stimulates salivary glands, removes sticky Kapha mucus.",                                                                     "icon": "mouth",   "duration_min": 5},
        {"name": "Garshana",         "instruction": "Dry brushing with raw silk gloves or a natural bristle brush before oil. Breaks up stagnant subcutaneous Kapha and activates lymph.",                                        "icon": "brush",   "duration_min": 5},
        {"name": "Abhyanga",         "instruction": "Warm mustard or sesame oil, short vigorous strokes. Kapha needs heat and stimulation — not gentle long strokes.",                                                             "icon": "massage", "duration_min": 10},
        {"name": "Snanam",           "instruction": "Warm, energising shower. Use Udwartana (chickpea flour + turmeric) instead of soap to stimulate subcutaneous Kapha tissue.",                                                  "icon": "bath",    "duration_min": 8},
    ],
}

# ── Evening rituals ───────────────────────────────────────────────────────────
_EVENING_RITUALS_BASE = {
    "vata": [
        {"name": "Padabhyanga",       "instruction": "Warm sesame oil foot massage 5–10 min before bed. Connects Apana Vata to earth — the most grounding Vata sleep practice.",                                                  "icon": "foot", "duration_min": 10},
        {"name": "Ashwagandha Milk",  "instruction": "1 cup warm milk + 1/4 tsp ashwagandha + 1/4 tsp nutmeg. Nourishes Ojas, sedates Vata, ensures deep restorative sleep.",                                                    "icon": "milk", "duration_min": 5},
    ],
    "pitta": [
        {"name": "Shiro Abhyanga",   "instruction": "Cool coconut oil on crown for 5 min — releases accumulated Pitta heat from Shira. Reduces heat-driven insomnia.",                                                             "icon": "head", "duration_min": 5},
        {"name": "Brahmi Milk",      "instruction": "1 cup warm milk + 1/4 tsp Brahmi powder + mishri. Cools Pitta Manas and promotes Prajna (calm clarity) in sleep.",                                                           "icon": "milk", "duration_min": 5},
    ],
    "kapha": [
        {"name": "Post-Dinner Walk", "instruction": "10-min slow walk after dinner — mandatory to prevent food converting to Ama overnight. Non-negotiable for Kapha.",                                                             "icon": "walk", "duration_min": 10},
        {"name": "Triphala Tea",     "instruction": "1 tsp Triphala in warm water, 1 hour before bed. Ensures clear Kapha bowels for morning. The most important Kapha sleep practice.",                                           "icon": "tea",  "duration_min": 3},
    ],
}

# ── Age-band modifications to rituals ─────────────────────────────────────────
def _apply_age_modifications(rituals: list, age_band: str, dosha: str) -> list:
    result = []
    for r in rituals:
        r = dict(r)
        name = r["name"]
        if age_band == "vriddha":
            if name == "Abhyanga":
                r["duration_min"] = 25
                r["instruction"] += " Vriddha Avastha (60+): 25–30 min Abhyanga is the most critical longevity practice — Vata accumulates with age and oil is the primary Rasayana countermeasure."
            elif name == "Garshana":
                r["instruction"] = "Vriddha Avastha: skip dry brushing — skin is thin and delicate. Replace with very gentle circular oil massage instead."
            elif name in ("Jihva Nirlekhana",):
                r["instruction"] += " Vriddha Avastha: 7 strokes is sufficient — do not scrape aggressively."
            elif r.get("icon") == "bath":
                r["instruction"] += " Vriddha Avastha: ensure water is comfortably warm, never hot. Use a bath chair if balance is a concern."
        elif age_band == "balya":
            if name in ("Kavala Gandusha", "Garshana", "Nasya"):
                r["instruction"] = "Children (under 16): skip this practice — resume from age 16 under guidance of a Vaidya."
        elif age_band == "madhyama":
            if name == "Abhyanga":
                r["duration_min"] = 20
                r["instruction"] += " Madhyama Avastha (40–60): Abhyanga becomes increasingly important for joint health and to slow Vata-Pitta accumulation of midlife."
        result.append(r)
    return result

# ── Secondary dosha modifications ─────────────────────────────────────────────
def _secondary_dosha_note(primary: str, secondary: str) -> str:
    """Returns a note appended to the dinacharya_protocol about dual-dosha adaptations."""
    pairs = {
        ("vata", "pitta"):  "Vata-Pitta dual constitution: use sesame oil for Abhyanga but add a Shiro Abhyanga (cool coconut oil on crown) at night. Favour bitter-sweet tastes. Ensure afternoon rest — Pitta crashing into Vata depletes Ojas fastest.",
        ("vata", "kapha"):  "Vata-Kapha dual constitution: use warm sesame oil (Vata approach) but add Garshana twice a week. Exercise should be moderate — not the extreme of either dosha. Prioritise warmth and consistency.",
        ("pitta", "vata"):  "Pitta-Vata dual constitution: cooling coconut Abhyanga in summer, sesame in winter. Meal timing is critical for both — never skip (Pitta) and always at regular times (Vata). Ashwagandha milk at night addresses both simultaneously.",
        ("pitta", "kapha"): "Pitta-Kapha dual constitution: moderate vigorous exercise (Kapha needs it but Pitta can overheat with too much). Use sunflower oil for Abhyanga — neutral, not too heating. Avoid heavy oily food AND spicy food.",
        ("kapha", "vata"):  "Kapha-Vata dual constitution: vigorous morning exercise (Kapha) but warm-up slowly and don't exercise in cold wind (Vata). Warm mustard oil for Abhyanga but also add Padabhyanga at night (Vata). Never skip breakfast.",
        ("kapha", "pitta"): "Kapha-Pitta dual constitution: vigorous exercise but keep it cool — swim or cycle rather than run in heat. Cool sesame or sunflower oil for Abhyanga. Avoid the extremes: neither heavy-oily (Kapha) nor spicy-fried (Pitta).",
    }
    return pairs.get((primary, secondary), "")

# ── Default week schedules (Tier B, no gym/yoga integration) ─────────────────
_DEFAULT_WEEK = {
    "vata": [
        {"day_name": "Monday",    "ex_type": "yoga",    "ex_label": "Gentle Yoga — Grounding Sequence",         "ex_duration": "30 min",  "is_rest": False},
        {"day_name": "Tuesday",   "ex_type": "walk",    "ex_label": "Morning Walk (30 min)",                    "ex_duration": "30 min",  "is_rest": False},
        {"day_name": "Wednesday", "ex_type": "yoga",    "ex_label": "Pranayama + Restorative Yoga",             "ex_duration": "30 min",  "is_rest": False},
        {"day_name": "Thursday",  "ex_type": "rest",    "ex_label": "Abhyanga Focus Day (longer oil massage)",  "ex_duration": None,       "is_rest": True},
        {"day_name": "Friday",    "ex_type": "yoga",    "ex_label": "Gentle Movement + Nadi Shodhana",          "ex_duration": "30 min",  "is_rest": False},
        {"day_name": "Saturday",  "ex_type": "walk",    "ex_label": "Nature Walk (45 min)",                     "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Sunday",    "ex_type": "rest",    "ex_label": "Full Rest — Extended Abhyanga + Nasya",    "ex_duration": None,       "is_rest": True},
    ],
    "pitta": [
        {"day_name": "Monday",    "ex_type": "strength","ex_label": "Strength Training / Power Yoga",           "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Tuesday",   "ex_type": "cardio",  "ex_label": "Cooling Cardio — Swimming or Cycling",     "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Wednesday", "ex_type": "yoga",    "ex_label": "Cooling Yoga — Moon Salutations + Twists", "ex_duration": "40 min",  "is_rest": False},
        {"day_name": "Thursday",  "ex_type": "strength","ex_label": "Strength Training",                        "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Friday",    "ex_type": "cardio",  "ex_label": "Nature Hike or Brisk Walk (shaded)",       "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Saturday",  "ex_type": "yoga",    "ex_label": "Restorative Yoga (long holds)",            "ex_duration": "40 min",  "is_rest": False},
        {"day_name": "Sunday",    "ex_type": "rest",    "ex_label": "Rest — Shiro Abhyanga + Moonbathing",      "ex_duration": None,       "is_rest": True},
    ],
    "kapha": [
        {"day_name": "Monday",    "ex_type": "vigorous","ex_label": "Run / HIIT / Vigorous Gym",                "ex_duration": "50 min",  "is_rest": False},
        {"day_name": "Tuesday",   "ex_type": "vigorous","ex_label": "Cycling or Power Yoga",                    "ex_duration": "50 min",  "is_rest": False},
        {"day_name": "Wednesday", "ex_type": "moderate","ex_label": "Moderate Strength Training",               "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Thursday",  "ex_type": "vigorous","ex_label": "Run / HIIT / Circuit Training",            "ex_duration": "50 min",  "is_rest": False},
        {"day_name": "Friday",    "ex_type": "moderate","ex_label": "Power Yoga + Brisk Walk",                  "ex_duration": "45 min",  "is_rest": False},
        {"day_name": "Saturday",  "ex_type": "vigorous","ex_label": "Vigorous Gym or Outdoor Sport",            "ex_duration": "55 min",  "is_rest": False},
        {"day_name": "Sunday",    "ex_type": "walk",    "ex_label": "Active Rest — Long Walk (no gym)",         "ex_duration": "40 min",  "is_rest": False},
    ],
}

# ── Vriddha/age exercise label modification ───────────────────────────────────
_AGE_EXERCISE_OVERRIDE = {
    "vriddha": {
        "vigorous": ("walk",    "Gentle Walk (30 min) — Vriddha Avastha: vigorous exercise contraindicated; moderate daily walking is the classical prescription", "30 min"),
        "strength": ("yoga",    "Gentle Yoga / Stretching — Vriddha Avastha: maintain mobility and lubricate joints with restorative movement",                      "30 min"),
        "cardio":   ("walk",    "Slow Walk in Nature (30 min) — paced for Vriddha Avastha joint health",                                                             "30 min"),
        "moderate": ("yoga",    "Gentle Yoga or Walking — Vriddha Avastha: all exercise should leave you energised, not depleted",                                   "30 min"),
    },
    "balya": {
        "vigorous": ("play",    "Active Play / Running Games — Balya Avastha: unstructured vigorous activity is ideal",                                              "45 min"),
        "strength": ("play",    "Active Play — children do not require structured strength training",                                                                  "45 min"),
    },
}

# ── Occupation modifier for exercise slot ────────────────────────────────────
_OCCUPATION_EX_NOTE = {
    "sedentary":        "Sedentary occupation: your exercise slot is non-negotiable — counterbalances 8+ hours of desk sitting that creates Sira Granthi (stiffness in channels).",
    "moderately_active":"Moderately active occupation: exercise complements your daily activity. Ensure at least 30 min dedicated movement beyond occupational activity.",
    "very_active":      "Very active occupation: your formal exercise slot may be reduced — prioritise recovery (Abhyanga, Yoga Nidra) to prevent Vata depletion from excess Vyayama.",
}

# ── Per-dosha base timeline ────────────────────────────────────────────────────
def _get_base_timeline(dosha: str, season: str, if_window: str, agni_type: str, occupation: str) -> list:
    sd = _SEASON_MAP.get((season or "sharad").lower(), _DEFAULT_SEASON)
    wake = sd["wake"].get(dosha, "6:00")
    agni_notes = _AGNI_NOTES.get(agni_type or "sama", _AGNI_NOTES["sama"])

    if dosha == "vata":
        slots = [
            {"time": wake + " AM",  "activity": "Brahma Muhurta — Wake up",         "description": "Rise gently. Lie still for 2 minutes. Set an intention before leaving bed. Same time every day — regularity is the #1 Vata medicine.", "type": "morning_routine", "icon": "sun"},
            {"time": "6:15 AM",     "activity": "Dinacharya Rituals",               "description": "Warm water, tongue scraping, Nasya, Kavala Gandusha. See Dinacharya Protocol for full details.", "type": "self_care", "icon": "ritual"},
            {"time": "6:45 AM",     "activity": "Abhyanga + Warm Bath",             "description": "Warm sesame oil self-massage (15–20 min) followed by warm shower.", "type": "self_care", "icon": "massage"},
            {"time": "7:30 AM",     "activity": "Morning Movement",                  "description": "See today's specific activity above.", "type": "exercise", "icon": "yoga"},
            {"time": "8:15 AM",     "activity": "Breakfast",                         "description": "Warm, moist, well-cooked. Never skip — Vata crashes hard without morning fuel.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
            {"time": "10:00 AM",    "activity": "Deep Work",                         "description": "Vata creativity and mental clarity peak mid-morning. Schedule analytical and creative work here. Sip warm ginger tea.", "type": "work", "icon": "work"},
            {"time": "1:00 PM",     "activity": "Lunch",                             "description": "Largest meal — Agni peaks 10 AM–2 PM. Eat seated, in calm surroundings. No distraction.", "type": "meal", "meal_type": "lunch", "icon": "meal"},
            {"time": "1:30 PM",     "activity": "Vishranti — Seated Rest",           "description": "15 min seated rest (not lying down). Allows Samana Vata to complete digestion undisturbed.", "type": "rest", "icon": "rest"},
            {"time": "4:00 PM",     "activity": "Snack",                             "description": "Small warm snack prevents the Vata 4 PM energy crash. Soaked dates, warm milk, or light soup.", "type": "meal", "meal_type": "snack", "icon": "meal"},
            {"time": "5:30 PM",     "activity": "Evening Movement",                  "description": "Light walk or restorative yoga. Sandhya Kala movement settles accumulated Vata.", "type": "exercise", "icon": "walk"},
            {"time": "7:00 PM",     "activity": "Dinner",                            "description": "Warm, lighter than lunch. Finish by 7:30 PM — Vata digestion weakens after sunset.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
            {"time": "8:30 PM",     "activity": "Wind-Down — Digital Sunset",        "description": "Dim lights. No screens. Padabhyanga (foot oil massage). Light reading or journaling.", "type": "wind_down", "icon": "moon"},
            {"time": "9:00 PM",     "activity": "Ashwagandha Milk",                  "description": "1 cup warm milk + 1/4 tsp ashwagandha + 1/4 tsp nutmeg. Grounds Vata, nourishes Ojas.", "type": "wind_down", "icon": "milk"},
            {"time": "10:30 PM",    "activity": "Sleep",                             "description": "7–9 hours. Sleeping past 11 PM severely aggravates Vata.", "type": "sleep", "icon": "sleep"},
        ]
    elif dosha == "pitta":
        slots = [
            {"time": wake + " AM",  "activity": "Brahma Muhurta — Wake up",         "description": "Rise before Pitta Kala peaks. Splash cool water on face and eyes.", "type": "morning_routine", "icon": "sun"},
            {"time": "5:45 AM",     "activity": "Dinacharya Rituals",               "description": "Cool water, tongue scraping (yellow Pitta Ama), rose water Anjana, ghee Nasya, Kavala. See Protocol panel.", "type": "self_care", "icon": "ritual"},
            {"time": "6:15 AM",     "activity": "Morning Movement",                  "description": "See today's specific activity below.", "type": "exercise", "icon": "yoga"},
            {"time": "7:30 AM",     "activity": "Abhyanga + Cool Shower",           "description": "Coconut or sunflower oil, cooler strokes. Followed by a genuinely cool shower.", "type": "self_care", "icon": "massage"},
            {"time": "8:00 AM",     "activity": "Breakfast",                         "description": "Cooling, sweet, properly nourishing. Pitta morning Agni is strong — breakfast is mandatory.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
            {"time": "10:30 AM",    "activity": "Deep Work",                         "description": "Pitta focus and precision peak mid-morning. Schedule critical decisions here. Never work through lunch.", "type": "work", "icon": "work"},
            {"time": "12:30 PM",    "activity": "Lunch",                             "description": "Largest meal — peak Agni. Never delay or skip. Eat until 80% full (Trishtha Bhaga Niyama).", "type": "meal", "meal_type": "lunch", "icon": "meal"},
            {"time": "1:00 PM",     "activity": "Short Rest",                        "description": "10–15 min in a cool space. Prevents Pitta post-lunch irritability and heat headache.", "type": "rest", "icon": "rest"},
            {"time": "3:30 PM",     "activity": "Snack",                             "description": "Coconut water, sweet fruit, or fennel-coriander tea. Prevents low-blood-sugar Pitta anger.", "type": "meal", "meal_type": "snack", "icon": "meal"},
            {"time": "5:30 PM",     "activity": "Evening Movement",                  "description": "Cooling activity. Avoid vigorous exercise in Pitta Kala (2–6 PM).", "type": "exercise", "icon": "walk"},
            {"time": "6:30 PM",     "activity": "Dinner",                            "description": "Cooling, lighter than lunch. No spicy, fermented, or fried food — aggravates Pitta overnight.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
            {"time": "8:00 PM",     "activity": "Wind-Down",                         "description": "Cool environment. Coconut oil on crown (Shiro Abhyanga). Read fiction — not work.", "type": "wind_down", "icon": "moon"},
            {"time": "9:00 PM",     "activity": "Brahmi Milk",                       "description": "1 cup warm milk + 1/4 tsp Brahmi + mishri. Cools Pitta Manas before sleep.", "type": "wind_down", "icon": "milk"},
            {"time": "10:00 PM",    "activity": "Sleep",                             "description": "Minimum 7 hours. Sleeping past 11 PM enters nocturnal Pitta Kala — worsens morning heat.", "type": "sleep", "icon": "sleep"},
        ]
    else:  # kapha
        slots = [
            {"time": wake + " AM",  "activity": "Brahma Muhurta — Wake up",         "description": "Rise BEFORE Kapha Kala (6–10 AM). Waking inside it causes grogginess all day. Non-negotiable.", "type": "morning_routine", "icon": "sun"},
            {"time": "5:15 AM",     "activity": "Dinacharya Rituals",               "description": "Hot ginger-lemon water, heavy tongue scraping (white Kapha Ama), Nasya with warm mustard oil.", "type": "self_care", "icon": "ritual"},
            {"time": "5:30 AM",     "activity": "Morning Movement",                  "description": "See today's specific activity below. Minimum 45 min with sweating — non-negotiable for Kapha.", "type": "exercise", "icon": "gym"},
            {"time": "6:45 AM",     "activity": "Garshana + Abhyanga + Bath",        "description": "5 min dry brushing → 10 min warm mustard oil → energising shower with Udwartana (chickpea flour + turmeric).", "type": "self_care", "icon": "massage"},
            {"time": "8:30 AM",     "activity": "Breakfast (Light)",                 "description": "Keep it light. Warm spiced porridge or fruit. Skip if not genuinely hungry — Kapha morning appetite is naturally low.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
            {"time": "10:30 AM",    "activity": "Work",                              "description": "Kapha steadiness and endurance peak after morning exercise. Sustained, methodical tasks.", "type": "work", "icon": "work"},
            {"time": "1:00 PM",     "activity": "Lunch — Main Meal",                 "description": "Pungent, bitter, astringent-tasting, warm and spiced. Avoid heavy-oily food. Moderate portion.", "type": "meal", "meal_type": "lunch", "icon": "meal"},
            {"time": "1:30 PM",     "activity": "Shatapadi (100 Steps)",             "description": "Classical post-meal walk from Ashtanga Hridayam, Sutrasthana — prevents Kapha Ama formation from sluggish digestion.", "type": "exercise", "icon": "walk"},
            {"time": "4:30 PM",     "activity": "Snack (Optional)",                  "description": "Only if genuinely hungry. Ginger tea or light fruit. Kapha has lowest snack requirement.", "type": "meal", "meal_type": "snack", "icon": "meal"},
            {"time": "6:00 PM",     "activity": "Dinner — Light and Early",          "description": "Finish by 6:30 PM. Light soup, stir-fried vegetables, thin dal. Kapha digestion slows sharply at night.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
            {"time": "7:00 PM",     "activity": "Post-Dinner Walk",                  "description": "10 min mandatory — prevents overnight Ama. Different from the post-lunch Shatapadi.", "type": "exercise", "icon": "walk"},
            {"time": "8:30 PM",     "activity": "Wind-Down",                         "description": "Triphala in warm water (1 tsp). Light reading. No heavy eating after this point.", "type": "wind_down", "icon": "moon"},
            {"time": "10:00 PM",    "activity": "Sleep",                             "description": "Only 6–7 hours needed. Excess sleep increases Kapha Tamas. Do not sleep past 6 AM.", "type": "sleep", "icon": "sleep"},
        ]

    # Apply Agni notes to meal slots
    for s in slots:
        mt = s.get("meal_type")
        if mt:
            note = agni_notes.get(mt)
            if note:
                s["agni_note"] = note

    # Apply IF window note to breakfast
    if if_window and if_window != "no":
        lbl = {"12:12": "12-hour", "14:10": "14-hour", "16:8": "16-hour"}.get(if_window, if_window)
        for s in slots:
            if s.get("meal_type") == "breakfast":
                s["condition_note"] = f"Intermittent fasting ({lbl} window): delay breakfast to fit your fasting schedule. Break fast with warm, light food only."
            if s.get("meal_type") == "snack" and if_window == "16:8":
                existing = s.get("condition_note", "")
                s["condition_note"] = (existing + " | " if existing else "") + "16:8: skip if outside eating window."

    # Occupation exercise note
    if occupation and occupation != "moderately_active":
        for s in slots:
            if s.get("type") == "exercise" and s.get("icon") in ("yoga", "gym", "walk"):
                s["occupation_note"] = _OCCUPATION_EX_NOTE.get(occupation, "")
                break

    return slots


# ── Condition-specific notes ──────────────────────────────────────────────────
def _apply_condition_notes(timeline: list, conditions: list, gender: str, age: int) -> list:
    cset = {c.lower() for c in (conditions or [])}
    ab = _age_band(age)

    for s in timeline:
        t  = s.get("type", "")
        mt = s.get("meal_type", "")
        notes = []

        if ("diabetes" in cset or "type_2_diabetes" in cset) and mt in ("lunch", "dinner"):
            notes.append("Prameha protocol: 10-min walk immediately after this meal — the most effective post-prandial glucose management practice in classical Ayurveda.")
        if ("hypertension" in cset or "high_blood_pressure" in cset) and t == "exercise":
            notes.append("Hridaya Roga protocol: keep intensity moderate. Sitali and Sitkari Pranayama are preferred over vigorous Kapalbhati. No Kumbhaka (breath-holding).")
        if ("insomnia" in cset or "sleep_disorder" in cset) and t == "wind_down":
            notes.append("Nidra protocol: no screens after 8 PM. Dim all lights from now. Padabhyanga (warm sesame oil on soles) is the most effective Ayurvedic sleep induction.")
        if ("ibs" in cset or "irritable_bowel" in cset) and mt == "snack":
            notes.append("Grahani protocol: prefer warm CCF tea (cumin-coriander-fennel) over solid snack if stomach is unsettled.")
        if ("anxiety" in cset or "stress" in cset) and t == "work":
            notes.append("Manovahasrotas protocol: every 90 minutes, take 3 slow belly breaths (4-count inhale, 8-count exhale). Prevents Prana Vata accumulation in the mind.")
        if ("arthritis" in cset or "joint_pain" in cset) and t == "exercise":
            notes.append("Sandhi Vata protocol: mandatory 5-min warm-up before any movement. Never exercise cold. Prioritise oil massage before exercise, not after.")
        if ("pcos" in cset or "pcod" in cset) and t == "exercise":
            notes.append("PCOS/PCOD protocol: morning vigorous exercise (before 8 AM) is the most effective hormonal regulator. Consistency 5–6 days/week reduces androgen levels significantly.")
        if ("hypothyroid" in cset or "thyroid" in cset) and t == "exercise":
            notes.append("Thyroid protocol: vigorous morning exercise stimulates thyroid metabolism. Include brisk walking and resistance training — both activate thyroid function.")
        if ("asthma" in cset or "respiratory" in cset) and t == "exercise":
            notes.append("Shwasa protocol: Anuloma Viloma (alternate nostril breathing) before exercise prepares Pranavaha Srotas. Avoid exercising in cold air or after heavy meals.")

        # Gender-specific notes
        if gender == "female":
            if ("menstrual_irregularity" in cset or "dysmenorrhea" in cset) and t in ("exercise",):
                notes.append("Artava protocol: reduce exercise intensity on days 1–3 of menstruation. No inversions or core work during menstrual phase — Apana Vata is in its natural downward movement.")

        # Vriddha modifications on exercise
        if ab == "vriddha" and t == "exercise":
            notes.append("Vriddha Avastha: all exercise at 50% intensity. Prioritise joint mobility and balance over cardiovascular intensity. Daily Abhyanga before exercise is mandatory.")

        if notes:
            existing = s.get("condition_note", "")
            s["condition_note"] = (" | ".join([existing] + notes) if existing else " | ".join(notes))

    return timeline


# ── Build dinacharya protocol block ──────────────────────────────────────────
def _build_dinacharya_protocol(dosha: str, secondary: str, vikriti: str, season: str,
                                conditions: list, gender: str, age: int, agni_type: str) -> dict:
    ab = _age_band(age)
    sd = _SEASON_MAP.get((season or "sharad").lower(), _DEFAULT_SEASON)
    wake = sd["wake"].get(dosha, "6:00") + " AM"
    sleep_time = "10:30 PM" if dosha == "vata" else "10:00 PM"
    if ab == "vriddha": wake = _shift_wake(sd["wake"].get(dosha, "6:00"), +30) + " AM"

    rituals = [dict(r) for r in _MORNING_RITUALS_BASE.get(dosha, _MORNING_RITUALS_BASE["vata"])]
    rituals = _apply_age_modifications(rituals, ab, dosha)

    evening = [dict(r) for r in _EVENING_RITUALS_BASE.get(dosha, _EVENING_RITUALS_BASE["vata"])]

    season_notes = {
        "vasanta":  "Spring Kapha season: prioritise Garshana, vigorous exercise, light meals. Avoid Divaswapna (daytime napping).",
        "grishma":  "Summer Pitta season: coconut Abhyanga, avoid afternoon exercise in heat, Sheetali Pranayama, limit spicy food.",
        "varsha":   "Monsoon Vata season: daily Abhyanga is essential. Boil all drinking water. Sour-salty-sweet foods protect Vata.",
        "sharad":   "Autumn Pitta season: Virechana (Pitta purge) classically recommended. Moonbathing beneficial. Avoid spicy food.",
        "hemanta":  "Early Winter: maximum nourishment season. Heavy sesame Abhyanga. Strong exercise. Nourish Shukra Dhatu.",
        "shishira": "Late Winter: keep body warm at all times. Sesame Abhyanga essential. Avoid cold, dry, and light foods.",
    }
    principles = {
        "vata": "Regularity is medicine for Vata. Same wake time, same meal times, same sleep time every day. Vata thrives on rhythm and collapses under chaos.",
        "pitta": "Moderation is medicine for Pitta. Never skip meals, avoid afternoon heat exercise, take a true midday rest. Pitta destroyed by pushing past limits.",
        "kapha": "Movement is medicine for Kapha. No Divaswapna (daytime sleep). Early rising, vigorous exercise, and light early dinner are non-negotiable daily anchors.",
    }
    agni_general = _AGNI_NOTES.get(agni_type or "sama", _AGNI_NOTES["sama"]).get("general", "")

    sec_note = _secondary_dosha_note(dosha, secondary) if secondary and secondary != dosha else ""

    return {
        "wake_time":             wake,
        "sleep_time":            sleep_time,
        "age_band":              ab,
        "agni_type":             agni_type or "sama",
        "agni_general_guidance": agni_general,
        "morning_rituals":       rituals,
        "evening_rituals":       evening,
        "season_label":          sd["label"],
        "season_practice_note":  season_notes.get((season or "sharad").lower(), ""),
        "agni_level":            sd["agni"],
        "key_principle":         principles.get(dosha, ""),
        "dual_dosha_note":       sec_note,
    }


def _shift_wake(t: str, delta_min: int) -> str:
    h, m = map(int, t.split(":"))
    total = h * 60 + m + delta_min
    return f"{total // 60}:{total % 60:02d}"


# ── Seasonal Ritucharya block ─────────────────────────────────────────────────
def _build_seasonal_ritucharya(season: str, dosha: str) -> dict:
    s = (season or "sharad").lower()
    sd = _SEASON_MAP.get(s, _DEFAULT_SEASON)
    foods = {
        "shishira": ["sesame","jaggery","ghee","warm soups","root vegetables","milk"],
        "vasanta":  ["honey","bitter gourd","neem leaves","barley","light grains","ginger"],
        "grishma":  ["coconut water","cucumber","pomegranate","coriander water","buttermilk","sweet fruit"],
        "varsha":   ["ginger","turmeric","rock salt","sour foods","honey","old rice"],
        "sharad":   ["pomegranate","coconut","bitter foods","white rice","ghee","Amalaki"],
        "hemanta":  ["sesame","sugarcane","wheat","ghee","milk","urad dal"],
    }
    avoids = {
        "shishira": ["cold water","raw salads","dry foods","astringent foods"],
        "vasanta":  ["dairy","daytime sleep","cold drinks","heavy oily food"],
        "grishma":  ["spicy food","hot soups","vigorous afternoon exercise","alcohol"],
        "varsha":   ["raw food","unboiled water","heavy fermented food","river bathing"],
        "sharad":   ["hot-spicy food","fermented food","heavy oily food","daytime sleep"],
        "hemanta":  ["fasting","dry foods","cold exposure","light or cold food"],
    }
    practices = {
        "shishira": ["Daily sesame Abhyanga","Hot food and drink always","Chyawanprash / Ashwagandha Rasayana","Keep body warm"],
        "vasanta":  ["Garshana (dry brushing) daily","Vigorous Vyayama","Trikatu and bitter herbs","Vamana if supervised"],
        "grishma":  ["Coconut / Chandana Abhyanga","Avoid afternoon exertion","Sheetali Pranayama","Moonbathing (Chandrakirana)"],
        "varsha":   ["Daily Abhyanga is essential","Ginger-rock salt before meals","Basti karma (if supervised)","Avoid cold food strictly"],
        "sharad":   ["Virechana (supervised)","Moonbathing","Amalaki Rasayana","Bitter-astringent food emphasis"],
        "hemanta":  ["Maximum nourishment","Heaviest Abhyanga with warm sesame oil","Strong exercise","Vajikara tonic herbs"],
    }
    return {
        "season":             sd["label"],
        "agni_level":         sd["agni"],
        "dominant_dosha":     sd["peak_dosha"],
        "recommended_foods":  foods.get(s, []),
        "foods_to_avoid":     avoids.get(s, []),
        "seasonal_practices": practices.get(s, []),
    }


# ── Meal guidance per dosha ───────────────────────────────────────────────────
def _build_meal_guidance(dosha: str, season: str, agni_type: str) -> dict:
    s = (season or "sharad").lower()
    sd = _SEASON_MAP.get(s, _DEFAULT_SEASON)
    agni = sd["agni"]
    agni_notes_list = _AGNI_NOTES.get(agni_type or "sama", _AGNI_NOTES["sama"])

    base = {
        "vata": {
            "general": "Warm, moist, well-cooked, slightly oily (Snigdha) food at regular times. Cold, raw, and dry foods are the primary Vata aggravants.",
            "breakfast": {"ideal_time": "7:30–8:30 AM", "favour": ["warm oatmeal with ghee","stewed fruit","warm spiced milk","soaked almonds","rice porridge (Kanji)"], "avoid": ["cold smoothies","dry toast","raw muesli","skipping breakfast"]},
            "lunch":     {"ideal_time": "12:30–1:30 PM", "favour": ["warm dal and rice","cooked vegetables with ghee","warm soup","wheat chapati"], "avoid": ["salads","raw vegetables","cold leftovers"]},
            "snack":     {"ideal_time": "4:00–4:30 PM",  "favour": ["warm milk with spices","soaked dates or figs","warm herbal tea"], "avoid": ["popcorn","chips","crackers","cold drinks"]},
            "dinner":    {"ideal_time": "6:30–7:30 PM",  "favour": ["light soup","khichdi","soft cooked grains","warm vegetables"], "avoid": ["heavy meals after 7:30 PM","raw salads","cold desserts"]},
        },
        "pitta": {
            "general": "Cooling, sweet, bitter, and astringent foods. Never skip meals. Avoid spicy, fermented, and fried. Pitta's greatest enemy is hunger.",
            "breakfast": {"ideal_time": "7:30–8:30 AM", "favour": ["sweet fruit","coconut milk oats","pomegranate juice","mild spiced tea","ghee on whole grain bread"], "avoid": ["spicy food","coffee","fermented food","hot sauce"]},
            "lunch":     {"ideal_time": "12:00–1:00 PM", "favour": ["cooling dal (moong)","basmati rice with ghee","cucumber raita","mint chutney","bitter greens"], "avoid": ["red chilli","excess tomatoes","heavy fried food","alcohol"]},
            "snack":     {"ideal_time": "3:30–4:00 PM",  "favour": ["coconut water","sweet fruit","fennel-coriander tea","dates"], "avoid": ["spicy namkeen","coffee","citrus in excess"]},
            "dinner":    {"ideal_time": "6:00–7:00 PM",  "favour": ["light cooling soup","steamed vegetables","moong dal","mild coconut curry"], "avoid": ["spicy food at night","wine","heavy red meat"]},
        },
        "kapha": {
            "general": "Light, dry, warm, spiced, and pungent food in small portions. Avoid dairy, sweets, and oily food — they directly increase Kapha and Ama.",
            "breakfast": {"ideal_time": "8:00–9:00 AM", "favour": ["light spiced porridge","ginger tea","warm fruit","rye or barley bread"], "avoid": ["dairy","sweet yoghurt","cold food","bananas","heavy breakfast"]},
            "lunch":     {"ideal_time": "12:30–1:30 PM", "favour": ["lentil soup","stir-fried bitter vegetables","barley or millet","warm spiced rice (minimal ghee)"], "avoid": ["heavy oily food","excess wheat","sweet desserts","cold water at meals"]},
            "snack":     {"ideal_time": "4:00–4:30 PM",  "favour": ["ginger tea","apple or pear","light roasted chickpeas","warm broth"], "avoid": ["biscuits","dairy snacks","sweets","chips"]},
            "dinner":    {"ideal_time": "6:00–6:30 PM",  "favour": ["light vegetable soup","dal water","steamed greens","small portion of grains"], "avoid": ["heavy dinner","eating after 7 PM","oily food","sweet desserts"]},
        },
    }
    guidance = base.get(dosha, base["vata"])
    agni_seasonal_notes = {
        "strongest": "Winter Agni is at peak — heavier, nourishing meals are appropriate.",
        "strong":    "Agni is strong — well-cooked moderately heavy meals work well.",
        "mild":      "Spring Agni is mild — keep meals lighter. Avoid heavy oily food.",
        "weak":      "Summer Agni is weak despite the heat — prefer easily digestible, cooling foods.",
        "very_weak": "Monsoon Agni is very weak — cooked, light, easily digestible food only. No raw food.",
    }
    guidance["seasonal_note"] = agni_seasonal_notes.get(agni, "")
    guidance["agni_note"] = agni_notes_list.get("general", "")
    return guidance


# ── Extract gym/yoga schedule from plan history ───────────────────────────────
def _extract_gym_schedule(gym_plan_data: dict) -> dict:
    try:
        week1 = (gym_plan_data.get("four_week_plan") or [{}])[0]
        days  = week1.get("days", [])
        dn = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        result = {}
        for d in days:
            idx = dn.index(d.get("day_name","").lower())
            is_rest = (d.get("type") == "rest") or d.get("is_rest_day", False)
            focus   = d.get("focus", "Workout")
            result[idx] = {
                "ex_type":  "rest" if is_rest else "gym",
                "ex_label": "Gym Rest Day" if is_rest else f"Gym — {focus}",
                "ex_duration": None if is_rest else "45–60 min",
                "is_rest":  is_rest,
                "gym_focus": None if is_rest else focus,
            }
        return result
    except Exception:
        return {}


def _extract_yoga_schedule(yoga_plan_data: dict) -> dict:
    try:
        week1 = (yoga_plan_data.get("four_week_plan") or [{}])[0]
        days  = week1.get("days", [])
        dn = ["monday","tuesday","wednesday","thursday","friday","saturday","sunday"]
        result = {}
        for d in days:
            idx = dn.index(d.get("day_name","").lower())
            is_rest = d.get("rest", False)
            theme   = (d.get("session") or {}).get("dosha_theme", "Yoga Practice")
            dur     = (d.get("session") or {}).get("total_duration_minutes", 30)
            result[idx] = {
                "ex_type":  "rest" if is_rest else "yoga",
                "ex_label": "Yoga Rest Day" if is_rest else f"Yoga — {theme}",
                "ex_duration": None if is_rest else f"{int(dur)} min",
                "is_rest":  is_rest,
            }
        return result
    except Exception:
        return {}


# ── Build 7-day routine ───────────────────────────────────────────────────────
DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]

def _build_weekly_routine(dosha: str, secondary: str, season: str, if_window: str,
                           conditions: list, gender: str, age: int,
                           agni_type: str, occupation: str,
                           fasting_days: list,
                           gym_schedule: dict, yoga_schedule: dict) -> list:
    ab        = _age_band(age)
    fasting   = {d.lower().strip() for d in (fasting_days or [])}
    week_plan = _DEFAULT_WEEK.get(dosha, _DEFAULT_WEEK["vata"])
    base_tl   = _get_base_timeline(dosha, season, if_window, agni_type, occupation)

    weekly = []
    for i, day_meta in enumerate(week_plan):
        day_name   = day_meta["day_name"]
        is_fasting = day_name.lower() in fasting

        # Determine exercise for this day
        ex_info = None
        if i in gym_schedule:
            ex_info = gym_schedule[i]
        elif i in yoga_schedule:
            ex_info = yoga_schedule[i]
        else:
            ex_info = {
                "ex_type":    day_meta["ex_type"],
                "ex_label":   day_meta["ex_label"],
                "ex_duration": day_meta.get("ex_duration"),
                "is_rest":    day_meta["is_rest"],
            }

        # Age band exercise override
        if ab in _AGE_EXERCISE_OVERRIDE:
            override = _AGE_EXERCISE_OVERRIDE[ab]
            if ex_info.get("ex_type") in override:
                new_type, new_label, new_dur = override[ex_info["ex_type"]]
                ex_info = {**ex_info, "ex_type": new_type, "ex_label": new_label, "ex_duration": new_dur}

        # Build day timeline
        day_tl = [dict(s) for s in base_tl]

        # Inject exercise info into the first exercise slot
        for s in day_tl:
            if s.get("type") == "exercise" and s.get("icon") in ("yoga","gym","walk"):
                if ex_info.get("is_rest"):
                    s["activity"] = ex_info["ex_label"]
                    s["description"] = "Rest from structured exercise today. Focus on Abhyanga, meditation, and restorative practices."
                    s["type"] = "rest"
                    s["icon"] = "rest"
                else:
                    s["activity"] = ex_info["ex_label"]
                    if ex_info.get("ex_duration"):
                        s["description"] = f"{ex_info['ex_duration']}. {s.get('description', '')}"
                    if ex_info.get("gym_focus"):
                        s["gym_focus"] = ex_info["gym_focus"]
                break  # only override first exercise slot

        # Fasting day
        if is_fasting:
            for s in day_tl:
                if s.get("type") == "meal":
                    s["condition_note"] = "Fasting day — follow your fasting protocol. Light fruit, warm water, or herbal tea only."

        # Condition + gender + age notes
        day_tl = _apply_condition_notes(day_tl, conditions, gender, age)

        weekly.append({
            "day":            i,
            "day_name":       day_name,
            "is_fasting_day": is_fasting,
            "is_rest_day":    ex_info.get("is_rest", False),
            "exercise_type":  ex_info.get("ex_type", ""),
            "exercise_label": ex_info.get("ex_label", ""),
            "timeline":       day_tl,
        })

    return weekly


# ── Weekly summary ────────────────────────────────────────────────────────────
def _weekly_summary(weekly: list) -> dict:
    exercise_days, rest_days, fasting_days = 0, [], []
    for d in weekly:
        if d.get("is_rest_day"):
            rest_days.append(d["day_name"])
        elif d.get("exercise_type") not in ("rest", None, ""):
            exercise_days += 1
        if d.get("is_fasting_day"):
            fasting_days.append(d["day_name"])
    return {
        "total_exercise_days": exercise_days,
        "rest_days":           rest_days,
        "fasting_days":        fasting_days,
    }


# ── Main public function ──────────────────────────────────────────────────────
def generate_routine_plan(user_profile: dict, prefs: dict, diet_foods_db=None,
                           gym_plan_data: dict = None, yoga_plan_data: dict = None) -> dict:
    dosha      = user_profile.get("dominant_dosha", "vata")
    secondary  = user_profile.get("secondary_dosha") or ""
    vikriti    = user_profile.get("vikriti_dominant") or dosha
    conditions = user_profile.get("medical_history") or []
    season     = (user_profile.get("current_season") or "sharad").lower()
    name       = user_profile.get("name", "")
    age        = int(user_profile.get("age") or 30)
    gender     = user_profile.get("gender", "male")

    # Routine-specific prefs (Tier C) — fall back to diet prefs for legacy
    rp = prefs.get("routine") or prefs.get("diet") or {}
    if_window   = rp.get("intermittent_fasting", "no")
    fasting_days = rp.get("fasting_days") or []
    if isinstance(fasting_days, str):
        fasting_days = [d.strip() for d in fasting_days.split(",") if d.strip()]
    agni_type   = rp.get("agni_type_self_report") or "sama"
    occupation  = rp.get("occupation_type") or "moderately_active"

    # Tier B: parse gym/yoga schedules
    gym_sched  = _extract_gym_schedule(gym_plan_data or {}) if gym_plan_data else {}
    yoga_sched = _extract_yoga_schedule(yoga_plan_data or {}) if yoga_plan_data else {}

    dinacharya = _build_dinacharya_protocol(dosha, secondary, vikriti, season, conditions, gender, age, agni_type)
    weekly     = _build_weekly_routine(dosha, secondary, season, if_window, conditions, gender, age,
                                        agni_type, occupation, fasting_days, gym_sched, yoga_sched)
    seasonal   = _build_seasonal_ritucharya(season, dosha)
    meal_guide = _build_meal_guidance(dosha, season, agni_type)
    summary    = _weekly_summary(weekly)

    ab_label = {"balya": "Child (Balya)", "yuva": "Youth / Adult (Yuva)", "madhyama": "Middle Age (Madhyama)", "vriddha": "Senior (Vriddha)"}

    return {
        "plan_id":      f"routine_{user_profile.get('id','x')}_{int(datetime.now(timezone.utc).timestamp())}",
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "user_summary": {
            "name":           name,
            "dominant_dosha": dosha,
            "secondary_dosha": secondary,
            "vikriti":        vikriti,
            "age":            age,
            "age_band":       ab_label.get(_age_band(age), ""),
            "gender":         gender,
            "current_season": season,
            "agni_type":      agni_type,
            "occupation_type": occupation,
        },
        "dinacharya_protocol": dinacharya,
        "weekly_routine":      weekly,
        "seasonal_ritucharya": seasonal,
        "meal_guidance":       meal_guide,
        "weekly_summary":      summary,
        "enriched":            False,
        "disclaimer": "This Dinacharya plan is for educational wellness guidance. Consult a qualified Vaidya before beginning herbal protocols, especially with pre-existing conditions.",
    }
