"""
Dinacharya (Daily Routine) Engine
Produces a fully personalised 7-day Ayurvedic daily routine.

Personalisation signals used:
  Tier A: dominant_dosha · secondary_dosha · vikriti · agni_type · age · gender
  Tier B: season · conditions · medicines · allergies · occupation_type · gym_schedule · yoga_schedule
  Fasting: intermittent_fasting window · fasting_days

Every time of day is computed from two anchors — the wake time and the bedtime —
and the slots between are placed by their own length. The engine used to print a
fixed clock time on every slot and move only the wake row, so a "late" riser was
woken at 7:30 AM with rituals scheduled at 6:15, and a Kapha adult was given
6½ hours in bed. 23% of all days in a 600-plan sweep ran backwards.
"""
import re

from datetime import datetime, timezone

from engine.condition_vocab import normalize_condition
from engine.movement_risk import condition_risk_tags, medication_classes
from services.plan_id import new_plan_id

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
_DOSHAS = ("vata", "pitta", "kapha")


def _dosha_key(value, default="vata") -> str:
    """`Vata`, `vata-pitta` and `VATA` are all Vata. An unrecognised value used to
    fall through to the Kapha timeline — the `else` branch — while the week table
    fell back to Vata, so one plan carried two constitutions."""
    v = str(value or "").strip().lower()
    for d in _DOSHAS:
        if v.startswith(d):
            return d
    return default


# ── Agni ──────────────────────────────────────────────────────────────────────
_AGNI_CANON = {"sama": "sama", "vata": "vishama", "vishama": "vishama",
               "pitta": "tikshna", "tikshna": "tikshna", "kapha": "manda", "manda": "manda"}


def _agni_notes(agni_type: str, trikatu_ok: bool, steady_meals: bool) -> dict:
    """Per-slot Agni guidance.

    `trikatu_ok` is the formulary's answer for this person (pregnancy, acid reflux
    and an ulcer all bar it). `steady_meals` is set when a meal must not be skipped
    — insulin or a sulfonylurea lowers glucose whether or not they have eaten, and
    "skip it if you are not hungry" is a hypoglycaemia instruction for them.
    """
    kindle = ("Take 1/4 tsp Trikatu churna or sip ginger tea 15 min before to kindle fire."
              if trikatu_ok else "Sip warm ginger tea 15 min before to kindle fire.")
    allies = "Trikatu and ginger are your daily digestive allies." if trikatu_ok else \
        "Warm ginger tea is your daily digestive ally."
    manda_snack = ("Manda Agni: keep the afternoon snack small and light — your medicine needs "
                   "food on time, so do not skip it."
                   if steady_meals else
                   "Manda Agni: skip the afternoon snack if not genuinely hungry. Kapha/Manda types "
                   "accumulate Ama from snacking before previous meal is digested.")
    notes = {
        "manda": {
            "breakfast": "Manda Agni: delay breakfast by 45–60 min past your usual wake time. Start with hot ginger water first. Smaller, lighter portions only — heavy breakfast worsens slow Agni.",
            "lunch":     f"Manda Agni: lunch is the main meal but keep portions moderate. {kindle} Eat only when genuinely hungry.",
            "snack":     manda_snack,
            "dinner":    "Manda Agni: very light dinner — thin soup or khichdi only. Eat early so overnight digestion is complete by morning.",
            "general":   f"Your Agni type is Manda (slow/sluggish). Eat only when previous meal is fully digested — no snacking between meals unless genuinely hungry. Largest meal at 12–1 PM. {allies}",
        },
        "tikshna": {
            "breakfast": "Tikshna Agni: eat breakfast on time — skipping aggravates your sharp Agni and leads to burning, acidity, and irritability. Cooling, sweet foods preferred.",
            "lunch":     "Tikshna Agni: never skip or delay lunch beyond 1 PM. Your Bhuta Agni begins digesting Dhatu tissue when the stomach is empty. Eat until 80% full — not more.",
            "snack":     "Tikshna Agni: a small snack in the afternoon prevents low-blood-sugar Pitta anger. Coconut water, sweet fruit, or fennel-coriander tea.",
            "dinner":    "Tikshna Agni: lighter than lunch but not minimal. Cooling foods. Avoid spicy, fermented food — Tikshna Agni at night drives Pitta hyperacidity.",
            "general":   "Your Agni type is Tikshna (sharp/intense). Never skip meals — your digestive fire burns internal Dhatus when empty. Eat cooling, sweet, properly cooked food. Avoid fasting unless medically supervised.",
        },
        "vishama": {
            "breakfast": "Vishama Agni: eat breakfast at the same time every single day regardless of hunger level — regularity anchors irregular Vata Agni. Warm, small, easily digestible.",
            "lunch":     "Vishama Agni: same time every day for lunch. Take CCF tea (cumin-coriander-fennel) 15 min before to prepare irregular Agni.",
            "snack":     "Vishama Agni: a small warm snack helps prevent Agni spikes between meals. Soaked dates or warm broth — nothing raw or cold.",
            "dinner":    "Vishama Agni: eat dinner at the same time every day. Inconsistent meal timing is the primary trigger for Vishama Agni worsening.",
            "general":   "Your Agni type is Vishama (irregular/variable). Meal time regularity is your primary medicine — eating at the same times daily is more important than what you eat. Avoid raw, cold, and heavy food.",
        },
        "sama": {
            "breakfast": None, "lunch": None, "snack": None, "dinner": None,
            "general":   "Your Agni is Sama (balanced) — maintain your current meal timing. Avoid excess fasting or overeating to keep it balanced.",
        },
    }
    return notes.get(agni_type, notes["sama"])


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
# A herbal drink names the formulary entry it is made from, so the drink is held
# to the medicines plan's own safety layers (see `_evening_drink`). Triphala went
# to every Kapha user every night, pregnancy included; Ashwagandha milk to every
# Vata user, a ten-year-old and a thyrotoxic patient included.
_EVENING_RITUALS_BASE = {
    "vata": [
        {"name": "Padabhyanga",       "instruction": "Warm sesame oil foot massage 5–10 min before bed. Connects Apana Vata to earth — the most grounding Vata sleep practice.",                                                  "icon": "foot", "duration_min": 10},
        {"name": "Ashwagandha Milk",  "instruction": "1 cup warm milk + 1/4 tsp ashwagandha + a pinch of nutmeg. Nourishes Ojas, sedates Vata, ensures deep restorative sleep.",                                                  "icon": "milk", "duration_min": 5, "herb": "Ashwagandha Churna"},
    ],
    "pitta": [
        {"name": "Shiro Abhyanga",   "instruction": "Cool coconut oil on crown for 5 min — releases accumulated Pitta heat from Shira. Reduces heat-driven insomnia.",                                                             "icon": "head", "duration_min": 5},
        {"name": "Brahmi Milk",      "instruction": "1 cup warm milk + 1/4 tsp Brahmi powder + mishri. Cools Pitta Manas and promotes Prajna (calm clarity) in sleep.",                                                           "icon": "milk", "duration_min": 5, "herb": "Brahmi Churna"},
    ],
    "kapha": [
        {"name": "Post-Dinner Walk", "instruction": "10-min slow walk after dinner — mandatory to prevent food converting to Ama overnight. Non-negotiable for Kapha.",                                                             "icon": "walk", "duration_min": 10},
        {"name": "Triphala Tea",     "instruction": "1 tsp Triphala in warm water, 1 hour before bed. Ensures clear Kapha bowels for morning. The most important Kapha sleep practice.",                                           "icon": "tea",  "duration_min": 3, "herb": "Triphala Churna"},
    ],
}

# What each herbal evening drink becomes when its herb is withheld: the ritual of
# a warm drink before sleep stays, the medicine leaves it.
_PLAIN_DRINK = {
    "Ashwagandha Churna": ("Warm Milk", "1 cup warm milk with a pinch of cardamom. A warm, unmedicated drink keeps the settling ritual before sleep."),
    "Brahmi Churna":      ("Warm Milk", "1 cup warm milk with a pinch of cardamom. A warm, unmedicated drink keeps the settling ritual before sleep."),
    "Triphala Churna":    ("Warm Water", "1 cup warm water with a slice of fresh ginger, sipped an hour before bed."),
}
_DAIRY_FREE_DRINK = ("Warm Spiced Water",
                     "1 cup warm water with a pinch of cardamom and cinnamon. Milk is left out for your "
                     "declared allergy or diet.")


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
                r["withheld"] = True
            elif name in ("Jihva Nirlekhana",):
                r["instruction"] += " Vriddha Avastha: 7 strokes is sufficient — do not scrape aggressively."
            elif r.get("icon") == "bath":
                r["instruction"] += " Vriddha Avastha: ensure water is comfortably warm, never hot. Use a bath chair if balance is a concern."
        elif age_band == "balya":
            if name in ("Kavala Gandusha", "Garshana", "Nasya"):
                r["instruction"] = "Children (under 16): skip this practice — resume from age 16 under guidance of a Vaidya."
                r["withheld"] = True
        elif age_band == "madhyama":
            if name == "Abhyanga":
                r["duration_min"] = 20
                r["instruction"] += " Madhyama Avastha (40–60): Abhyanga becomes increasingly important for joint health and to slow Vata-Pitta accumulation of midlife."
        result.append(r)
    return result

# ── Pregnancy ────────────────────────────────────────────────────────────────
#
# This engine handled twenty condition tokens — hypertension, diabetes, PCOS,
# thyroid, IBS — and had no concept of pregnancy at all; the word did not appear
# in the file. Every other engine in this app treats it as a first-class gate:
# the gym library authors `pregnancy_safe` per movement, the yoga engine keeps
# per-trimester pose pools, and `panchakarma_engine` refuses outright —
#
#     if user_profile.get("pregnancy_or_nursing", False):
#         reasons_shamana.append("Pregnancy / nursing — Shodhana contraindicated")
#
# Virechana IS Shodhana. A pregnant practitioner's autumn Ritucharya read
# "Virechana (Pitta purge) classically recommended" and listed "Virechana
# (supervised)" among the season's practices, while spring offered "Vamana if
# supervised" and monsoon "Basti karma". Therapeutic purgation, emesis and enema,
# recommended to a pregnant woman by the one engine that had never been told to
# ask. Nasya reached her every morning in the daily ritual list.
#
# The panchakarma engine's refusal is a rule in Python; the KB rows for those
# same therapies carry `contraindications: []`, so nothing reading the data
# rather than calling that engine gets a warning. Both halves are fixed.
#
# Over-blocking is acceptable here and a missed block is not, which is the same
# posture the yoga engine takes with forceful pranayama.
_SHODHANA_TERMS = ("vamana", "virechana", "basti", "nasya", "shodhana",
                   "purge", "purgation", "emesis", "enema")

# Seasonal guidance written for pregnancy, rather than the general text with the
# unsafe clauses cut out of it — a sentence with a hole in it reads as an
# oversight, and the seasons genuinely call for different advice here.
_PREGNANCY_SEASON_NOTES = {
    "vasanta":  "Spring Kapha season: gentle daily movement and light, warm meals. Dry brushing is fine; skip Vamana and any Shodhana — cleansing therapies are not undertaken during pregnancy.",
    "grishma":  "Summer Pitta season: stay cool and well hydrated, coconut oil Abhyanga with gentle strokes, avoid afternoon heat. Sheetali is safe; avoid forceful breathing practices.",
    "varsha":   "Monsoon Vata season: daily gentle Abhyanga, boil all drinking water, favour warm cooked food. Basti and all Shodhana are set aside until after delivery and recovery.",
    "sharad":   "Autumn Pitta season: cooling foods, moonbathing, bitter-astringent tastes. Virechana is classically indicated this season and is contraindicated in pregnancy — it is omitted here.",
    "hemanta":  "Early Winter: the nourishment season, which suits pregnancy well. Warm sesame Abhyanga with gentle strokes, nourishing food, rest. Keep exercise moderate rather than strong.",
    "shishira": "Late Winter: keep warm at all times, gentle sesame Abhyanga, warm cooked food. Avoid cold, dry and light foods.",
}

_PREGNANCY_PRACTICES = {
    "vasanta":  ["Gentle daily walking", "Light, warm meals", "Garshana (light, if comfortable)", "No Shodhana during pregnancy"],
    "grishma":  ["Coconut oil Abhyanga — gentle strokes", "Stay cool and hydrated", "Sheetali Pranayama (no retention)", "Rest through the afternoon heat"],
    "varsha":   ["Daily gentle Abhyanga", "Boil all drinking water", "Warm, easily digested food", "No Basti or other Shodhana"],
    "sharad":   ["Moonbathing", "Cooling, bitter-astringent foods", "Gentle evening walk", "No Virechana during pregnancy"],
    "hemanta":  ["Nourishing warm food", "Gentle sesame Abhyanga", "Moderate movement, not strong exercise", "Early, restful nights"],
    "shishira": ["Keep the body warm at all times", "Gentle sesame Abhyanga", "Warm cooked food", "Avoid cold and dry foods"],
}


def _pregnancy_state(user_profile: dict) -> tuple[bool, bool]:
    """(pregnant, nursing). `pregnancy_or_nursing` alone means pregnant, as in the
    yoga engine. Nursing is not pregnancy: Nasya and a moderate run are both fine
    while breastfeeding, and the two used to be one flag here."""
    status = (user_profile.get("pregnancy_status") or "").strip().lower()
    if status == "nursing":
        return False, True
    if status == "pregnant":
        return True, False
    return bool(user_profile.get("pregnancy_or_nursing")), False


def _apply_pregnancy_modifications(rituals: list, dosha: str) -> tuple:
    """Withhold what pregnancy rules out of the daily ritual list, and say so.

    Same shape as `_apply_age_modifications`, which already withholds Nasya and
    Kavala Gandusha from children — the hook existed, pregnancy was simply never
    one of the cases.
    """
    out, notices = [], []
    for ritual in rituals:
        r = dict(ritual)
        name = r.get("name", "")
        if name == "Nasya":
            r["instruction"] = (
                "Set aside during pregnancy. Nasya is classically contraindicated; "
                "resume after delivery under a Vaidya's guidance.")
            r["duration_min"] = 0
            r["withheld"] = True
            notices.append("Nasya is withheld — classically contraindicated in pregnancy.")
        elif name == "Abhyanga":
            r["instruction"] = (
                "Gentle full-body warm oil self-massage, long light strokes. Avoid deep "
                "pressure on the abdomen and lower back entirely, and have someone else "
                "apply it if reaching is uncomfortable.")
            notices.append("Abhyanga is softened — no deep pressure on the abdomen or low back.")
        elif name == "Garshana":
            r["instruction"] = (
                "Light dry brushing on the limbs only, avoiding the abdomen. Stop if the "
                "skin is sensitive — it often is during pregnancy.")
        elif r.get("icon") == "bath":
            r["instruction"] += (" In pregnancy keep the water warm, not hot — a hot bath "
                                 "raises core temperature.")
        out.append(r)
    return out, notices


# ── Secondary dosha modifications ─────────────────────────────────────────────
def _secondary_dosha_note(primary: str, secondary: str, ashwagandha_ok: bool = True) -> str:
    """Returns a note appended to the dinacharya_protocol about dual-dosha adaptations."""
    night = ("Ashwagandha milk at night addresses both simultaneously." if ashwagandha_ok
             else "A warm, settling drink at the same hour every night addresses both.")
    pairs = {
        ("vata", "pitta"):  "Vata-Pitta dual constitution: use sesame oil for Abhyanga but add a Shiro Abhyanga (cool coconut oil on crown) at night. Favour bitter-sweet tastes. Ensure afternoon rest — Pitta crashing into Vata depletes Ojas fastest.",
        ("vata", "kapha"):  "Vata-Kapha dual constitution: use warm sesame oil (Vata approach) but add Garshana twice a week. Exercise should be moderate — not the extreme of either dosha. Prioritise warmth and consistency.",
        ("pitta", "vata"):  f"Pitta-Vata dual constitution: cooling coconut Abhyanga in summer, sesame in winter. Meal timing is critical for both — never skip (Pitta) and always at regular times (Vata). {night}",
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

# ── Exercise limits from health status ────────────────────────────────────────
# The default week gave every Kapha adult "Run / HIIT / Vigorous Gym" three days a
# week whatever they had declared — heart disease, a hernia, glaucoma, pregnancy,
# knee osteoarthritis. The gym and yoga engines gate every movement; this engine
# names exercise in a label and gated none of it. Age 60+ was the only limit.
#
# "moderate" is the talk test: you can speak in sentences. "gentle" is walking and
# gentle yoga. These are conservative defaults, not a prescription — the note on
# the slot says who should set the real number.
_GENTLE_CONDITIONS = {
    "heart_disease": "heart disease", "atrial_fibrillation": "atrial fibrillation",
    "copd": "COPD", "chronic_fatigue_syndrome": "ME/CFS",
}
_MODERATE_CONDITIONS = {
    "hypertension": "high blood pressure", "fibromyalgia": "fibromyalgia",
    "anemia": "anaemia", "hyperthyroidism": "an overactive thyroid",
    "obesity": "obesity", "multiple_sclerosis": "multiple sclerosis",
    "parkinson": "Parkinson's", "chronic_kidney_disease": "kidney disease",
}
_MODERATE_RISK_TAGS = {
    "intracranial_pressure": "raised eye or head pressure",
    "abdominal_pressure": "a condition that straining makes worse",
    "seizure_risk": "epilepsy",
}
_LOW_IMPACT_CONDITIONS = {
    "osteoarthritis", "rheumatoid_arthritis", "gout", "osteoporosis", "obesity",
    "sciatica", "lumbar_spondylosis", "ankylosing_spondylitis", "peripheral_neuropathy",
    "varicose_veins", "fibromyalgia",
}
_LOW_IMPACT_INJURY_WORDS = ("knee", "ankle", "hip", "foot", "feet", "back", "shin", "achilles")

_MODERATE_LABEL = {
    "vigorous": ("moderate", "Brisk Walk or Cycling — moderate pace", "40 min"),
    "cardio":   ("moderate", "Brisk Walk or Cycling — moderate pace", "40 min"),
    "strength": ("strength", "Light Strength Training — moderate effort, breathe out on every effort", "30 min"),
    "moderate": ("moderate", "Brisk Walk or Gentle Yoga — moderate pace", "40 min"),
}
_GENTLE_LABEL = ("walk", "Gentle Walk or Gentle Yoga", "20–30 min")


def _exercise_limits(conditions: set[str], is_pregnant: bool, age: int,
                     injuries: list[str], bmi_category: str | None) -> dict:
    """The ceiling and impact limit this person's health status puts on exercise."""
    reasons: list[str] = []
    cap = "full"
    for c, label in _GENTLE_CONDITIONS.items():
        if c in conditions:
            cap = "gentle"
            reasons.append(label)
    if cap != "gentle":
        for c, label in _MODERATE_CONDITIONS.items():
            if c in conditions:
                cap = "moderate"
                reasons.append(label)
        tags = condition_risk_tags(sorted(conditions))
        for tag, label in _MODERATE_RISK_TAGS.items():
            if tag in tags:
                cap = "moderate"
                reasons.append(label)
        if is_pregnant:
            cap = "moderate"
            reasons.append("pregnancy")
    low_impact = bool(conditions & _LOW_IMPACT_CONDITIONS) or is_pregnant \
        or str(bmi_category or "").lower() == "obese" \
        or any(w in str(i).lower() for i in injuries for w in _LOW_IMPACT_INJURY_WORDS)
    no_swim_alone = "seizure_risk" in condition_risk_tags(sorted(conditions))
    return {"cap": cap, "low_impact": low_impact, "no_swim_alone": no_swim_alone,
            "reasons": list(dict.fromkeys(reasons))}


def _limit_exercise(ex_info: dict, limits: dict) -> dict:
    """Apply the ceiling to one day of the default week. Gym and yoga plans pulled in
    by integration are left alone: those engines gate every movement themselves."""
    t = ex_info.get("ex_type")
    if ex_info.get("is_rest") or t in ("gym", "rest", "walk"):
        return ex_info
    if t == "play":
        # A child's running games are right for a child, not for a pregnant teenager.
        if limits["cap"] == "full":
            return ex_info
        t = "moderate"
    label = ex_info.get("ex_label") or ""
    if limits["cap"] == "gentle" and t in ("vigorous", "cardio", "strength", "moderate", "yoga"):
        new_type, new_label, dur = _GENTLE_LABEL
        if t == "yoga":
            new_label = "Gentle Yoga"
        ex_info = {**ex_info, "ex_type": new_type, "ex_label": new_label, "ex_duration": dur, "limited": True}
    elif limits["cap"] == "moderate" and t in _MODERATE_LABEL:
        new_type, new_label, dur = _MODERATE_LABEL[t]
        ex_info = {**ex_info, "ex_type": new_type, "ex_label": new_label, "ex_duration": dur, "limited": True}
    elif limits["cap"] == "moderate" and t == "yoga" and "power" in label.lower():
        ex_info = {**ex_info, "ex_label": "Steady Yoga — moderate pace", "limited": True}
    label = ex_info.get("ex_label") or ""
    if limits["low_impact"] and re.search(r"\b(run|hiit|circuit|sport|hike)\b", label, re.I):
        ex_info = {**ex_info, "ex_type": "moderate", "ex_label": "Cycling or Swimming — low impact",
                   "limited": True}
    if limits["no_swim_alone"] and "swim" in (ex_info.get("ex_label") or "").lower():
        ex_info = {**ex_info, "ex_label": re.sub(r"\s*(Swimming or |or Swimming|Swimming)\s*", " ",
                                                 ex_info["ex_label"]).strip(" —-") or "Cycling",
                   "limited": True}
    return ex_info


# ── Occupation modifier for exercise slot ────────────────────────────────────
_OCCUPATION_EX_NOTE = {
    "sedentary":        "Sedentary occupation: your exercise slot is non-negotiable — counterbalances 8+ hours of desk sitting that creates Sira Granthi (stiffness in channels).",
    "moderately_active":"Moderately active occupation: exercise complements your daily activity. Ensure at least 30 min dedicated movement beyond occupational activity.",
    "very_active":      "Very active occupation: your formal exercise slot may be reduced — prioritise recovery (Abhyanga, Yoga Nidra) to prevent Vata depletion from excess Vyayama.",
}

# ── Withheld practices in the timeline ───────────────────────────────────────
def _strip_withheld_practices(timeline: list, is_pregnant: bool) -> list:
    """The timeline carries its OWN copy of the ritual description — "Nasya with
    warm mustard oil", once per day — so gating the ritual list and the seasonal
    guidance left a third copy untouched, seven times over.

    The same instruction living in more than one structure is exactly how the
    prose escaped a gate everywhere else in this codebase. Withheld here rather
    than rewritten, because the timeline entry is a pointer to the protocol panel
    and the protocol panel is already correct."""
    if not is_pregnant:
        return timeline
    out = []
    for slot in timeline:
        entry = dict(slot)
        # `ex_label` is a fourth copy of the same instruction — "Full Rest —
        # Extended Abhyanga + Nasya" — and the first version of this gate read
        # only `description`, so it survived. Four structures carried the same
        # sentence; three gates were not enough.
        label = entry.get("ex_label") or ""
        if "nasya" in label.lower():
            entry["ex_label"] = re.sub(r"\s*\+?\s*Nasya", "", label, flags=re.I).strip(" +—-")
        desc = entry.get("description") or ""
        if "nasya" in desc.lower():
            entry["description"] = re.sub(
                r",?\s*[^,.]*nasya[^,.]*", "", desc, flags=re.I).strip(" ,.") + \
                ". Nasya is withheld during pregnancy — see the Dinacharya panel."
        if "abhyanga" in (entry.get("activity") or "").lower():
            entry["description"] = (entry.get("description") or "") + \
                " Keep strokes gentle; avoid pressure on the abdomen and low back."
        out.append(entry)
    return out


# ── Wake and sleep ────────────────────────────────────────────────────────────
# `wake_preference` (early / natural / late) is honoured because the classical
# time is an ideal and the user's life is a fact — shift work, small children, a
# partner on a different schedule. What it must not do is honour the preference
# and keep the classical LABEL: 7:00 AM is not Brahma Muhurta, and calling it that
# is the same fault as a card that disagrees with the schedule under it.
#
# The form promises a band for each answer ("Late — 6:30–7:30 AM"), and the old
# +60 minutes did not keep it: a Kapha "late" riser was woken at 5:30.
_WAKE_BANDS = {"early": (4 * 60 + 30, 5 * 60 + 30), "late": (6 * 60 + 30, 7 * 60 + 30)}
_WAKE_SHIFT_MINUTES = {"early": -45, "natural": 0, "late": +60}

# Brahma Muhurta is roughly the 96 minutes before sunrise; practically, before 6 AM.
# Kapha Kala runs 6–10 AM, which is what the Kapha routine exists to get ahead of.
_BRAHMA_MUHURTA_ENDS_MIN = 6 * 60

# Bedtime: no later than the classical hour, and never so early that it is not a
# real evening. The classical rise is not bought with lost sleep — the American
# Academy of Sleep Medicine puts adults at 7 hours or more, teenagers at 8-10 and
# children of 6-12 at 9-12. A child is not woken at 4:30 AM to keep a Kapha hour.
_CLASSICAL_BED = {"vata": 22 * 60 + 30, "pitta": 22 * 60, "kapha": 22 * 60}


def _sleep_need_minutes(age: int, dosha: str) -> int:
    if age < 13:
        return 9 * 60 + 30
    if age < 18:
        return 8 * 60 + 30
    if age >= 65:
        return 7 * 60 + 30
    return {"vata": 8 * 60, "pitta": 7 * 60 + 30, "kapha": 7 * 60}.get(dosha, 7 * 60 + 30)


def _earliest_bed(age: int) -> int:
    return 20 * 60 + 30 if age < 13 else 21 * 60


def _minutes(t: str) -> int:
    h, m = map(int, t.split(":"))
    return h * 60 + m


def _shift_wake(t: str, delta_min: int) -> str:
    h, m = map(int, t.split(":"))
    total = h * 60 + m + delta_min
    return f"{total // 60}:{total % 60:02d}"


def _hm(total: int) -> str:
    return f"{total // 60}:{total % 60:02d}"


def _clock(total: int) -> str:
    """Minutes after midnight → '7:05 AM'."""
    total %= 24 * 60
    h, m = divmod(total, 60)
    suffix = "AM" if h < 12 else "PM"
    return f"{(h % 12) or 12}:{m:02d} {suffix}"


def _wake_for_preference(base_wake: str, preference: str | None) -> tuple[str, str, str | None]:
    """(wake_time, label, notice) for the user's stated preference.

    The label degrades honestly: a wake time past 6 AM is no longer Brahma Muhurta
    and stops being called it.
    """
    pref = (preference or "natural").lower()
    wake_min = _minutes(base_wake) + _WAKE_SHIFT_MINUTES.get(pref, 0)
    if pref in _WAKE_BANDS:
        lo, hi = _WAKE_BANDS[pref]
        wake_min = min(max(wake_min, lo), hi)
    wake = _hm(wake_min)
    late = wake_min >= _BRAHMA_MUHURTA_ENDS_MIN

    label = "Wake up" if late else "Brahma Muhurta — Wake up"
    notice = None
    if late and pref == "late":
        notice = (
            f"You asked for a later start, so this routine wakes you at {wake} AM. "
            "That is past Brahma Muhurta, the pre-dawn window the morning practices "
            "are built around, so expect less of their benefit. Everything else in "
            "the day shifts with it."
        )
    return wake, label, notice


def _day_anchors(dosha: str, season: str, age: int, preference: str | None) -> dict:
    """The one wake time and bedtime the protocol card and all seven days share.

    These were computed twice — the card shifted the wake 30 minutes for anyone
    over 60 and the timeline did not, so every senior's plan showed two wake times.
    """
    sd = _SEASON_MAP.get((season or "sharad").lower(), _DEFAULT_SEASON)
    base = sd["wake"].get(dosha, "6:00")
    if _age_band(age) == "vriddha":
        base = _shift_wake(base, +30)
    wake, label, notice = _wake_for_preference(base, preference)
    wake_min = _minutes(wake)
    need = _sleep_need_minutes(age, dosha)
    bed = min(_CLASSICAL_BED.get(dosha, 22 * 60), wake_min + 24 * 60 - need)
    sleep_notice = None
    if bed < _earliest_bed(age):
        bed = _earliest_bed(age)
        wake_min = bed + need - 24 * 60
        wake = _hm(wake_min)
        late = wake_min >= _BRAHMA_MUHURTA_ENDS_MIN
        label = "Wake up" if late else "Brahma Muhurta — Wake up"
        who = "a child" if age < 13 else "a teenager" if age < 18 else "you"
        sleep_notice = (
            f"This routine wakes you at {_clock(wake_min)} rather than earlier, so that "
            f"{who} still gets about {need / 60:g} hours of sleep with a bedtime of "
            f"{_clock(bed)}. Sleep is not traded for the pre-dawn hour.")
    return {"wake": wake_min, "bed": bed, "label": label, "wake_notice": notice,
            "sleep_notice": sleep_notice, "sleep_hours": round((wake_min + 24 * 60 - bed) / 60, 1)}


# ── The user's own times ──────────────────────────────────────────────────────
# Every slot carries a stable `id`, and a user can set any of them to their own
# time, for every day or for one weekday. A set slot is placed exactly there; the
# slots after it flow from its end, as they flow from any other. Wake and sleep are
# the day's anchors, so setting either moves everything tied to them.
#
# The user's time wins. Where it costs something — less sleep than their age
# needs, dinner close to bed, a workout straight after a meal — the slot says so;
# it is not refused, because the routine is theirs to live and a plan that will not
# fit someone's working hours is a plan nobody follows.

SLOT_IDS = ("wake", "rituals", "abhyanga", "morning_ex", "breakfast", "work", "lunch",
            "midday_rest", "after_lunch_walk", "snack", "evening_ex", "dinner",
            "after_dinner_walk", "wind_down", "night_drink", "sleep")


# A slot can be left out of the day as well as moved. Not the day's anchors, and
# not lunch or dinner: a routine with no main meal is not one this app can stand
# behind. Breakfast can go, except where a medicine or pregnancy needs it eaten.
SKIP = "off"
_WEEKDAY_KEYS = ("monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday")
UNSKIPPABLE = {"wake", "sleep", "lunch", "dinner"}


def parse_hhmm(value) -> int | None:
    """'07:30' / '7:30' / '19:05' -> minutes after midnight; None when not a time."""
    m = re.fullmatch(r"\s*(\d{1,2}):(\d{2})\s*", str(value or ""))
    if not m:
        return None
    h, mi = int(m.group(1)), int(m.group(2))
    return h * 60 + mi if h < 24 and mi < 60 else None


def clean_custom_times(times) -> dict[str, str]:
    """Only known slot ids with real times survive; anything else is dropped."""
    out = {}
    for k, v in (times or {}).items() if isinstance(times, dict) else ():
        k = str(k)
        known = k in SLOT_IDS or re.fullmatch(r"(morning|evening)_ex_\d", k)
        if known and v == SKIP and k not in UNSKIPPABLE:
            out[k] = SKIP
        elif known and parse_hhmm(v) is not None:
            t = parse_hhmm(v)
            out[k] = f"{t // 60:02d}:{t % 60:02d}"
    return out


# Things the user adds to their own day — a commute, school pickup, a class. They
# are the user's words and are shown only to the user; they never reach the model.
ITEM_CATEGORIES = {
    "activity": ("custom", "work"), "work": ("work", "work"), "exercise": ("exercise", "walk"),
    "meal": ("meal", "meal"), "self_care": ("self_care", "ritual"), "rest": ("rest", "rest"),
}
MAX_ITEMS = 20


def clean_custom_items(items) -> list[dict]:
    """The user's own items, each with a real time, a bounded length and known days."""
    out = []
    for it in (items if isinstance(items, list) else [])[:MAX_ITEMS]:
        if not isinstance(it, dict):
            continue
        t = parse_hhmm(it.get("time"))
        title = re.sub(r"\s+", " ", str(it.get("title") or "")).strip()[:60]
        iid = str(it.get("id") or "")
        if t is None or not title or not re.fullmatch(r"custom_[a-z0-9]{4,16}", iid):
            continue
        try:
            dur = min(max(int(it.get("duration_minutes") or 30), 5), 600)
        except (TypeError, ValueError):
            dur = 30
        out.append({
            "id": iid, "title": title, "time": f"{t // 60:02d}:{t % 60:02d}", "duration_minutes": dur,
            "category": it.get("category") if it.get("category") in ITEM_CATEGORIES else "activity",
            "days": [d for d in (it.get("days") or []) if d in _WEEKDAY_KEYS],
            "note": str(it.get("note") or "").strip()[:200],
        })
    return out


def _item_slot(it: dict) -> dict:
    kind, icon = ITEM_CATEGORIES[it["category"]]
    return {"id": it["id"], "at": ("clock", it["time"]), "min": it["duration_minutes"],
            "activity": it["title"], "description": it["note"], "type": kind, "icon": icon,
            "custom": True, "duration_minutes": it["duration_minutes"], "category": it["category"],
            "days": it["days"]}


def _override_anchors(anchors: dict, times: dict, age: int, dosha: str) -> dict:
    """The day's wake and bed with the user's own times applied."""
    if not ({"wake", "sleep"} & set(times)):
        return anchors
    out = dict(anchors)
    need = _sleep_need_minutes(age, dosha)
    if "wake" in times:
        out["wake"] = parse_hhmm(times["wake"])
        out["label"] = "Wake up" if out["wake"] >= _BRAHMA_MUHURTA_ENDS_MIN else "Brahma Muhurta — Wake up"
        out["wake_notice"] = None
        if "sleep" not in times:
            # Bedtime follows a wake time the user moved, as it follows the computed one.
            out["bed"] = max(min(_CLASSICAL_BED.get(dosha, 22 * 60), out["wake"] + 24 * 60 - need),
                             _earliest_bed(age))
    if "sleep" in times:
        bed = parse_hhmm(times["sleep"])
        out["bed"] = bed + 24 * 60 if bed < 12 * 60 else bed   # 00:30 is after midnight
    out["sleep_hours"] = round((out["wake"] + 24 * 60 - out["bed"]) / 60, 1)
    out["sleep_notice"] = None
    if out["sleep_hours"] * 60 < need - 5:
        who = "a child" if age < 13 else "a teenager" if age < 18 else "you"
        out["sleep_notice"] = (
            f"With the times you set, this is about {out['sleep_hours']:g} hours in bed. "
            f"{who[0].upper() + who[1:]} need{'s' if who != 'you' else ''} about {need / 60:g}. "
            "Sleep is the one thing in this routine not worth trading for an earlier start.")
    return out


def _kapha_wake_description(wake: str) -> str:
    """Kapha's wake instruction, which cannot be printed unchanged at every hour.

    It reads "Rise BEFORE Kapha Kala (6-10 AM) ... Non-negotiable." Once a wake
    preference puts the time inside that window, printing it unchanged asserts the
    opposite of the schedule beside it — and calls the thing it is doing
    non-negotiable while doing it.
    """
    if _minutes(wake) < _BRAHMA_MUHURTA_ENDS_MIN:
        return ("Rise BEFORE Kapha Kala (6–10 AM). Waking inside it causes grogginess "
                "all day. Non-negotiable.")
    return (f"You have asked to wake later, so this rises at {wake} AM — inside Kapha "
            "Kala (6–10 AM), the window Kapha routines exist to get ahead of. Expect "
            "morning heaviness. If you can move it earlier by even 30 minutes, that is "
            "the single highest-value change in this plan for your constitution.")


# ── Per-dosha day template ────────────────────────────────────────────────────
# `at` says what a slot is anchored to, `min` how long it takes. The resolver
# places each slot at its anchor or, if the slot before it runs on, straight after
# it — so a day can be compressed but never run backwards.
#   ("wake", n)   n minutes after waking
#   ("clock", t)  a classical clock time (meals at Agni's peak), or later if pushed
#   ("dinner",)   the dosha's dinner hour, or earlier to leave room before bed
#   ("dinner", n) n minutes after dinner (negative: before)
#   ("bed", n)    n minutes before bedtime (n negative)
def _template(dosha: str, wake_label: str, wake: str) -> list:
    """The dosha's day, each slot with a stable `id` the user can set a time on."""
    slots = _template_slots(dosha, wake_label, wake)
    care = 0
    for x in slots:
        kind, act = x["type"], x["activity"].lower()
        if kind == "morning_routine":
            x["id"] = "wake"
        elif kind == "self_care":
            x["id"] = ("rituals", "abhyanga")[min(care, 1)]
            care += 1
        elif kind == "meal":
            x["id"] = x["meal_type"]
        elif kind == "exercise":
            x["id"] = ("morning_ex" if x.get("morning") else "evening_ex" if x.get("evening")
                       else "after_lunch_walk" if "shatapadi" in act else "after_dinner_walk")
        elif kind == "rest":
            x["id"] = "midday_rest"
        elif kind == "wind_down":
            x["id"] = "night_drink" if x.get("icon") == "milk" else "wind_down"
        else:
            x["id"] = kind
    return slots


def _template_slots(dosha: str, wake_label: str, wake: str) -> list:
    if dosha == "vata":
        return [
            {"at": ("wake", 0),   "min": 15, "activity": wake_label, "description": "Rise gently. Lie still for 2 minutes. Set an intention before leaving bed. Same time every day — regularity is the #1 Vata medicine.", "type": "morning_routine", "icon": "sun"},
            {"at": ("wake", 15),  "min": 30, "activity": "Dinacharya Rituals", "description": "Warm water, tongue scraping, Nasya, Kavala Gandusha. See Dinacharya Protocol for full details.", "type": "self_care", "icon": "ritual"},
            {"at": ("wake", 45),  "min": 40, "activity": "Abhyanga + Warm Bath", "description": "Warm sesame oil self-massage (15–20 min) followed by warm shower.", "type": "self_care", "icon": "massage"},
            {"at": ("wake", 90),  "min": 30, "activity": "Morning Movement", "description": "See today's specific activity above.", "type": "exercise", "icon": "yoga", "morning": True},
            {"at": ("clock", "8:15"), "min": 30, "activity": "Breakfast", "description": "Warm, moist, well-cooked. Never skip — Vata crashes hard without morning fuel.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
            {"at": ("clock", "10:00"), "min": 60, "activity": "Deep Work", "description": "Vata creativity and mental clarity peak mid-morning. Schedule analytical and creative work here. Sip warm ginger tea.", "type": "work", "icon": "work"},
            {"at": ("clock", "13:00"), "min": 30, "activity": "Lunch", "description": "Largest meal — Agni peaks 10 AM–2 PM. Eat seated, in calm surroundings. No distraction.", "type": "meal", "meal_type": "lunch", "icon": "meal"},
            {"at": ("clock", "13:30"), "min": 15, "activity": "Vishranti — Seated Rest", "description": "15 min seated rest (not lying down). Allows Samana Vata to complete digestion undisturbed.", "type": "rest", "icon": "rest"},
            {"at": ("clock", "16:00"), "min": 15, "activity": "Snack", "description": "Small warm snack prevents the Vata 4 PM energy crash. Soaked dates, warm milk, or light soup.", "type": "meal", "meal_type": "snack", "icon": "meal"},
            {"at": ("dinner", -90), "min": 30, "activity": "Evening Movement", "description": "Light walk or restorative yoga. Sandhya Kala movement settles accumulated Vata.", "type": "exercise", "icon": "walk", "evening": True},
            {"at": ("dinner",), "dinner_clock": "19:00", "min": 30, "activity": "Dinner", "description": "Warm, lighter than lunch. Vata digestion weakens after sunset — eat at the same hour every evening.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
            {"at": ("bed", -120), "min": 30, "activity": "Wind-Down — Digital Sunset", "description": "Dim lights. No screens. Padabhyanga (foot oil massage). Light reading or journaling.", "type": "wind_down", "icon": "moon"},
            {"at": ("bed", -75), "min": 15, "activity": "Ashwagandha Milk", "description": "1 cup warm milk + 1/4 tsp ashwagandha + a pinch of nutmeg. Grounds Vata, nourishes Ojas.", "type": "wind_down", "icon": "milk", "herb": "Ashwagandha Churna"},
            {"at": ("bed", 0), "min": 0, "activity": "Sleep", "description": "Sleeping past 11 PM severely aggravates Vata.", "type": "sleep", "icon": "sleep"},
        ]
    if dosha == "pitta":
        return [
            {"at": ("wake", 0),   "min": 15, "activity": wake_label, "description": "Rise before Pitta Kala peaks. Splash cool water on face and eyes.", "type": "morning_routine", "icon": "sun"},
            {"at": ("wake", 15),  "min": 30, "activity": "Dinacharya Rituals", "description": "Cool water, tongue scraping (yellow Pitta Ama), rose water Anjana, ghee Nasya, Kavala. See Protocol panel.", "type": "self_care", "icon": "ritual"},
            {"at": ("wake", 45),  "min": 45, "activity": "Morning Movement", "description": "See today's specific activity below.", "type": "exercise", "icon": "yoga", "morning": True},
            {"at": ("wake", 105), "min": 30, "activity": "Abhyanga + Cool Shower", "description": "Coconut or sunflower oil, cooler strokes. Followed by a genuinely cool shower.", "type": "self_care", "icon": "massage"},
            {"at": ("clock", "8:00"), "min": 30, "activity": "Breakfast", "description": "Cooling, sweet, properly nourishing. Pitta morning Agni is strong — breakfast is mandatory.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
            {"at": ("clock", "10:30"), "min": 60, "activity": "Deep Work", "description": "Pitta focus and precision peak mid-morning. Schedule critical decisions here. Never work through lunch.", "type": "work", "icon": "work"},
            {"at": ("clock", "12:30"), "min": 30, "activity": "Lunch", "description": "Largest meal — peak Agni. Never delay or skip. Eat until 80% full (Trishtha Bhaga Niyama).", "type": "meal", "meal_type": "lunch", "icon": "meal"},
            {"at": ("clock", "13:00"), "min": 15, "activity": "Short Rest", "description": "10–15 min in a cool space. Prevents Pitta post-lunch irritability and heat headache.", "type": "rest", "icon": "rest"},
            {"at": ("clock", "15:30"), "min": 15, "activity": "Snack", "description": "Coconut water, sweet fruit, or fennel-coriander tea. Prevents low-blood-sugar Pitta anger.", "type": "meal", "meal_type": "snack", "icon": "meal"},
            {"at": ("dinner", -60), "min": 30, "activity": "Evening Movement", "description": "Cooling activity. Avoid vigorous exercise in Pitta Kala (2–6 PM).", "type": "exercise", "icon": "walk", "evening": True},
            {"at": ("dinner",), "dinner_clock": "18:30", "min": 30, "activity": "Dinner", "description": "Cooling, lighter than lunch. No spicy, fermented, or fried food — aggravates Pitta overnight.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
            {"at": ("bed", -120), "min": 30, "activity": "Wind-Down", "description": "Cool environment. Coconut oil on crown (Shiro Abhyanga). Read fiction — not work.", "type": "wind_down", "icon": "moon"},
            {"at": ("bed", -60), "min": 15, "activity": "Brahmi Milk", "description": "1 cup warm milk + 1/4 tsp Brahmi + mishri. Cools Pitta Manas before sleep.", "type": "wind_down", "icon": "milk", "herb": "Brahmi Churna"},
            {"at": ("bed", 0), "min": 0, "activity": "Sleep", "description": "Sleeping past 11 PM enters nocturnal Pitta Kala — worsens morning heat.", "type": "sleep", "icon": "sleep"},
        ]
    return [
        {"at": ("wake", 0),   "min": 15, "activity": wake_label, "description": _kapha_wake_description(wake), "type": "morning_routine", "icon": "sun"},
        {"at": ("wake", 15),  "min": 15, "activity": "Dinacharya Rituals", "description": "Hot ginger-lemon water, heavy tongue scraping (white Kapha Ama), Nasya with warm mustard oil.", "type": "self_care", "icon": "ritual"},
        {"at": ("wake", 30),  "min": 50, "activity": "Morning Movement", "description": "See today's specific activity below. Minimum 45 min with sweating — non-negotiable for Kapha.", "type": "exercise", "icon": "gym", "morning": True},
        {"at": ("wake", 105), "min": 35, "activity": "Garshana + Abhyanga + Bath", "description": "5 min dry brushing → 10 min warm mustard oil → energising shower with Udwartana (chickpea flour + turmeric).", "type": "self_care", "icon": "massage"},
        {"at": ("clock", "8:30"), "min": 30, "activity": "Breakfast (Light)", "description": "Keep it light. Warm spiced porridge or fruit. Skip if not genuinely hungry — Kapha morning appetite is naturally low.", "type": "meal", "meal_type": "breakfast", "icon": "meal"},
        {"at": ("clock", "10:30"), "min": 60, "activity": "Work", "description": "Kapha steadiness and endurance peak after morning exercise. Sustained, methodical tasks.", "type": "work", "icon": "work"},
        {"at": ("clock", "13:00"), "min": 30, "activity": "Lunch — Main Meal", "description": "Pungent, bitter, astringent-tasting, warm and spiced. Avoid heavy-oily food. Moderate portion.", "type": "meal", "meal_type": "lunch", "icon": "meal"},
        {"at": ("clock", "13:30"), "min": 10, "activity": "Shatapadi (100 Steps)", "description": "Classical post-meal walk from Ashtanga Hridayam, Sutrasthana — prevents Kapha Ama formation from sluggish digestion.", "type": "exercise", "icon": "walk"},
        {"at": ("clock", "16:30"), "min": 15, "activity": "Snack (Optional)", "description": "Only if genuinely hungry. Ginger tea or light fruit. Kapha has lowest snack requirement.", "type": "meal", "meal_type": "snack", "icon": "meal"},
        {"at": ("dinner",), "dinner_clock": "18:00", "min": 30, "activity": "Dinner — Light and Early", "description": "Light soup, stir-fried vegetables, thin dal. Kapha digestion slows sharply at night.", "type": "meal", "meal_type": "dinner", "icon": "meal"},
        {"at": ("dinner", 45), "min": 10, "activity": "Post-Dinner Walk", "description": "10 min mandatory — prevents overnight Ama. Different from the post-lunch Shatapadi.", "type": "exercise", "icon": "walk"},
        {"at": ("bed", -90), "min": 30, "activity": "Wind-Down", "description": "Triphala in warm water (1 tsp). Light reading. No heavy eating after this point.", "type": "wind_down", "icon": "moon", "herb": "Triphala Churna"},
        {"at": ("bed", 0), "min": 0, "activity": "Sleep", "description": "Excess sleep increases Kapha Tamas — keep to the hours below and rise on time.", "type": "sleep", "icon": "sleep"},
    ]


def _resolve_times(slots: list, wake: int, bed: int, dinner_gap: int = 150,
                   pins: dict[str, int] | None = None) -> list:
    """Give every slot a time, in order, none earlier than the end of the one before.

    Dinner is the classical hour, brought earlier when it would fall inside
    `dinner_gap` minutes of bed — Ashtanga Hridayam has dinner well before sleep,
    and acid reflux needs three hours, not the twenty minutes a child's bedtime
    left after a 7 PM dinner.
    """
    dinner_clock = next((_minutes(s["dinner_clock"]) for s in slots if s.get("dinner_clock")), 19 * 60)
    dinner = min(dinner_clock, bed - dinner_gap)
    pins = pins or {}
    if "dinner" in pins:
        dinner = pins["dinner"]
    out, prev_end = [], None
    for s in slots:
        kind = s["at"][0]
        if s.get("id") in pins:
            t = pins[s["id"]]
            entry = {k: v for k, v in s.items() if k not in ("at", "min", "dinner_clock")}
            entry.update(_t=t, _end=t + int(s.get("min") or 0), user_set=True)
            out.append(entry)
            prev_end = entry["_end"]
            continue
        if kind == "wake":
            t = wake + s["at"][1]
        elif kind == "clock":
            t = _minutes(s["at"][1])
        elif kind == "dinner":
            t = dinner + (s["at"][1] if len(s["at"]) > 1 else 0)
        else:  # bed
            t = bed + s["at"][1]
        if prev_end is not None:
            t = max(t, prev_end)
        t = -(-t // 5) * 5
        if s.get("meal_type") == "dinner":
            dinner = t
        entry = {k: v for k, v in s.items() if k not in ("at", "min", "dinner_clock")}
        entry["_t"] = t
        entry["_end"] = t + int(s.get("min") or 0)
        out.append(entry)
        prev_end = entry["_end"]
    if pins:
        out.sort(key=lambda e: e["_t"])
        _note_conflicts(out, bed, dinner_gap)
    # The bed row is the anchor; if the evening ran on past it, say so by moving
    # bed rather than printing a 10 PM sleep after a 10:15 wind-down.
    for e in out:
        e["time"] = _clock(e["_t"])
    return out


_MAIN_MEALS = {"breakfast", "lunch", "dinner"}


def _note_conflicts(out: list, bed: int, dinner_gap: int) -> None:
    """What a time the user set costs, said on the slot rather than refused."""
    sleep = next((e for e in out if e["type"] == "sleep"), None)
    if sleep and sleep["_t"] > bed and not sleep.get("user_set"):
        # The evening ran past bedtime because of a time the user set. Sleep is
        # what gave, so say so where they will look for it.
        sleep["schedule_notes"] = [
            f"Later than planned ({_clock(bed)}), because the times you set ran the evening on. "
            "Move one of them earlier to get the sleep back."]
    bed = sleep["_t"] if sleep else bed
    for i, e in enumerate(out):
        if not e.get("user_set"):
            continue
        notes = []
        before = out[i - 1] if i else None
        after = out[i + 1] if i + 1 < len(out) else None
        for other in (before, after):
            if not other or "sleep" in (other["type"], e["type"]):
                continue
            if (other["_t"] < e["_end"] and e["_t"] < other["_end"]) or other["_t"] == e["_t"]:
                notes.append(f"Overlaps with {other['activity']} at {_clock(other['_t'])}. "
                             "Move one of them, or do them back to back.")
                break
        if e.get("meal_type") == "dinner" and bed - e["_t"] < dinner_gap:
            notes.append(f"This leaves {(bed - e['_t']) / 60:g} hours before bed. Ayurveda keeps "
                         f"dinner about {dinner_gap / 60:g} hours before sleep, so it is digested "
                         "first.")
        if e.get("meal_type") == "lunch" and not (11 * 60 <= e["_t"] <= 14 * 60):
            notes.append("Agni is strongest from about 10 AM to 2 PM, which is why lunch is the "
                         "main meal. At this hour keep it lighter, and make it the bigger meal "
                         "again on days you can.")
        if e["type"] == "exercise" and "walk" not in e.get("activity", "").lower():
            meal = next((m for m in reversed(out[:i]) if m.get("meal_type") in _MAIN_MEALS), None)
            if meal and e["_t"] - meal["_t"] < 90:
                notes.append(f"This is soon after {meal['activity'].split(' —')[0].lower()}. "
                             "Leave an hour or two after a meal before a workout.")
        if notes:
            e["schedule_notes"] = notes


def _sleep_line(hours: float, age: int) -> str:
    if age < 13:
        return f"About {hours:g} hours — children need 9–12 hours (AASM)."
    if age < 18:
        return f"About {hours:g} hours — teenagers need 8–10 hours (AASM)."
    return f"About {hours:g} hours in bed."


def _place_sessions(slots: list, sessions: dict) -> list:
    """One exercise slot per planned session, tagged `ex_slot` ("morning0", ...).

    The template has one morning slot, and an evening one for Vata and Pitta only,
    so a day with a gym session and a yoga session had room for one of them: the
    gym won and the yoga plan disappeared from every shared day. A second session
    in the same part of the day follows the first. An evening session is placed so
    it ends half an hour before dinner rather than running into it, and Kapha,
    whose template has no evening slot, gets one when a plan needs it.
    """
    evening = [m for m in sessions.get("evening") or [] if m]
    if evening and not any(s.get("evening") for s in slots):
        at = next(i for i, s in enumerate(slots) if s.get("meal_type") == "dinner")
        slots = slots[:at] + [{"id": "evening_ex", "at": ("dinner",), "min": 30, "activity": "Evening Movement",
                               "description": "", "type": "exercise", "icon": "walk",
                               "evening": True}] + slots[at:]
    # Vata's template bathes before its gentle morning movement. Before a planned
    # session that is a shower followed by an hour of sweating, so the session
    # moves ahead of the bath, as it already sits in the Pitta and Kapha days.
    if any(sessions.get("morning") or []):
        m = next((i for i, x in enumerate(slots) if x.get("morning")), None)
        b = next((i for i, x in enumerate(slots) if x.get("type") == "self_care"
                  and "bath" in x.get("activity", "").lower()), None)
        if m is not None and b is not None and b < m:
            slots = list(slots)
            ex = {**slots.pop(m), "at": slots[b]["at"]}
            slots.insert(b, ex)
    out = []
    for s in slots:
        part = "morning" if s.get("morning") else "evening" if s.get("evening") else None
        if s.get("type") != "exercise" or not part:
            out.append(s)
            continue
        mins = [m for m in sessions.get(part) or [] if m]
        if not mins:
            out.append({**s, "ex_slot": f"{part}0"})
            continue
        at = s["at"] if part == "morning" else ("dinner", -(sum(mins) + 30))
        out.extend({**s, "at": at, "min": m, "ex_slot": f"{part}{n}",
                    "id": s["id"] if n == 0 else f"{s['id']}_{n + 1}"} for n, m in enumerate(mins))
    return out


def _get_base_timeline(dosha: str, season: str, if_window: str, agni_type: str, occupation: str,
                       wake_preference: str | None = None, age: int = 30,
                       agni_notes: dict | None = None, ex_minutes: int | None = None,
                       dinner_gap: int = 150, anchors: dict | None = None,
                       sessions: dict | None = None, pins: dict | None = None,
                       items: list | None = None, skip: set | None = None) -> list:
    anchors = anchors or _day_anchors(dosha, season, age, wake_preference)
    wake = _hm(anchors["wake"])
    slots = _template(dosha, anchors["label"], wake)
    if ex_minutes:
        for s in slots:
            if s.get("morning"):
                s["min"] = ex_minutes
    slots = _place_sessions(slots, sessions or {})
    # Slots the day leaves out go before the times are laid out. Removed after,
    # the conflict notes still named them: a user's cricket that replaced the
    # Evening Movement said it overlapped the Evening Movement.
    if skip:
        slots = [s for s in slots if s.get("id") not in skip]
    if items:
        # Put each item where it falls in the day as first laid out, so the slots
        # after it flow from its end instead of colliding with it.
        first = _resolve_times(slots, anchors["wake"], anchors["bed"], dinner_gap, pins)
        placed = [(e["_t"], e["id"]) for e in first]
        for it in sorted(items, key=lambda i: pins[i["id"]], reverse=True):
            after = next((sid for t, sid in placed if t > pins[it["id"]]), None)
            at = next((i for i, x in enumerate(slots) if x["id"] == after), len(slots))
            slots.insert(at, _item_slot(it))
    timeline = _resolve_times(slots, anchors["wake"], anchors["bed"], dinner_gap, pins)
    for s in timeline:
        if s["type"] == "sleep":
            hours = round((anchors["wake"] + 24 * 60 - s["_t"]) / 60, 1)
            s["description"] = f"{_sleep_line(hours, age)} {s['description']}"

    notes = agni_notes or _agni_notes(agni_type or "sama", True, False)
    for s in timeline:
        mt = s.get("meal_type")
        if mt and notes.get(mt):
            s["agni_note"] = notes[mt]

    if occupation and occupation != "moderately_active":
        for s in timeline:
            if s.get("type") == "exercise" and s.get("icon") in ("yoga", "gym", "walk"):
                s["occupation_note"] = _OCCUPATION_EX_NOTE.get(occupation, "")
                break
    return timeline


def _apply_if_window(timeline: list, if_window: str) -> list:
    """Place the first meal where the eating window actually opens.

    The window was a note on breakfast — "delay breakfast to fit your fasting
    schedule" — beside a breakfast printed at 8:15 and a dinner at 7 PM, which is a
    12-hour window whatever the user chose. Now the first meal moves to dinner's
    end minus the window, and breakfast merges into lunch when the window is that
    short.
    """
    hours = {"12:12": 12, "14:10": 10, "16:8": 8}.get(if_window or "no")
    if not hours:
        return timeline
    dinner = next((s for s in timeline if s.get("meal_type") == "dinner"), None)
    lunch = next((s for s in timeline if s.get("meal_type") == "lunch"), None)
    if not dinner or not lunch:
        return timeline
    opens = dinner["_t"] + 30 - hours * 60
    out = []
    for s in timeline:
        if s.get("meal_type") == "breakfast" and opens > s["_t"] and s.get("user_set"):
            s.setdefault("schedule_notes", []).append(
                f"You set this before your {if_window} eating window opens at {_clock(opens)}. "
                "Either move it, or this is not a fasting window today.")
        elif s.get("meal_type") == "breakfast" and opens > s["_t"]:
            if opens >= lunch["_t"] - 90:
                lunch.setdefault("_notes", []).append(
                    f"Intermittent fasting ({if_window}): this is your first meal. Break the fast "
                    "with warm, light food.")
                continue
            s = {**s, "_t": opens, "time": _clock(opens), "activity": "Breakfast — First Meal"}
            s.setdefault("_notes", [])
            s["_notes"] = s["_notes"] + [f"Intermittent fasting ({if_window}): your eating window "
                                         f"opens at {_clock(opens)}. Warm water or herbal tea "
                                         "until then; break the fast with warm, light food."]
        out.append(s)
    out.sort(key=lambda e: e["_t"])
    return out


# ── Condition-specific notes ──────────────────────────────────────────────────
# Keyed by the canonical condition the onboarding vocabulary produces. The table
# used to be keyed by `diabetes`, `type_2_diabetes`, `hypothyroid` and `thyroid` —
# none of which onboarding sends (it sends `diabetes_type2`, `hypothyroidism`) — so
# a diabetic's routine said nothing about diabetes. 8 of the 70 onboarding
# conditions changed anything; 62 changed nothing at all.
#
# These are daily-life notes: what changes about waking, bathing, eating, moving
# and sleeping. Each one is a standard instruction, with its source where the
# instruction is clinical rather than classical.
_SLOT_TARGETS = {
    "wake":      lambda s: s.get("type") == "morning_routine",
    "rituals":   lambda s: s.get("activity", "").startswith("Dinacharya Rituals"),
    "bath":      lambda s: "abhyanga" in s.get("activity", "").lower(),
    "exercise":  lambda s: s.get("type") == "exercise" and s.get("morning"),
    "meals":     lambda s: s.get("meal_type") in ("lunch", "dinner"),
    "breakfast": lambda s: s.get("meal_type") == "breakfast",
    "dinner":    lambda s: s.get("meal_type") == "dinner",
    "work":      lambda s: s.get("type") == "work",
    "wind_down": lambda s: s.get("type") == "wind_down" and s.get("icon") == "moon",
    "sleep":     lambda s: s.get("type") == "sleep",
}

_CONDITION_SLOT_NOTES: dict[str, list[tuple[str, str]]] = {
    "diabetes_type2": [
        ("meals", "Prameha: a 10-minute walk straight after this meal is the most effective way to blunt the rise in blood glucose it brings."),
        ("exercise", "Diabetes: if you use insulin or a sulfonylurea, check your glucose before exercise and carry fast carbohydrate (ADA Standards of Care)."),
    ],
    "diabetes_type1": [
        ("meals", "Type 1 diabetes: match this meal's insulin to what you actually eat, and walk for 10 minutes afterwards."),
        ("exercise", "Type 1 diabetes: check glucose before exercise. Below 5.6 mmol/L (100 mg/dL) eat 15–30 g of carbohydrate first; above 13.9 mmol/L (250 mg/dL) with ketones, do not exercise (ADA)."),
    ],
    "metabolic_syndrome": [("meals", "A 10-minute walk after this meal lowers the glucose and triglyceride rise it brings.")],
    "obesity": [("meals", "A 10-minute walk after this meal — the classical Shatapadi — is part of the plan, not optional.")],
    "hypertension": [
        ("exercise", "High blood pressure: keep intensity moderate and never hold your breath. Skip exercise if a reading is 180/110 or above and call your doctor."),
        ("bath", "High blood pressure: avoid very hot and very cold water — both swing blood pressure. Lukewarm is right."),
    ],
    "heart_disease": [
        ("exercise", "Heart disease: stop at once for chest pain or pressure, unusual breathlessness, dizziness or palpitations. Ask your cardiologist for a target heart rate."),
        ("bath", "Heart disease: lukewarm water only — a cold plunge or a very hot bath both strain the heart."),
    ],
    "atrial_fibrillation": [("exercise", "Atrial fibrillation: your pulse is not a reliable effort gauge, so use the talk test. Stop for dizziness, chest pain or breathlessness.")],
    "low_blood_pressure": [
        ("wake", "Low blood pressure: sit on the edge of the bed for a minute before standing, and drink a glass of water first."),
        ("bath", "Low blood pressure: a hot shower drops blood pressure further. Keep it warm and sit down if you feel faint."),
    ],
    "anemia": [("wake", "Anaemia: rise slowly — light-headedness on standing is common until your levels are treated.")],
    "insomnia": [("wind_down", "Nidra: no screens from this point. Dim all lights. Padabhyanga (warm oil on the soles) is the most effective Ayurvedic sleep induction. Get up at the same time every day, even after a bad night (CBT-I).")],
    "sleep_apnea": [("sleep", "Sleep apnoea: sleep on your side, use your CPAP every night if prescribed, and avoid alcohol and sedating drinks in the evening.")],
    "anxiety": [("work", "Manovahasrotas: every 90 minutes take 3 slow belly breaths (4-count inhale, 8-count exhale). Prevents Prana Vata accumulating in the mind.")],
    "depression": [("wake", "Depression: get outside into morning daylight within an hour of waking, even for 10 minutes, and keep the wake time fixed on weekends.")],
    "bipolar": [("sleep", "Bipolar disorder: keep this bedtime and wake time every day. Lost sleep is one of the commonest triggers of a mood episode — never cut it short for the morning routine.")],
    "adhd": [("work", "ADHD: work in timed blocks of 25–45 minutes with a short movement break between them.")],
    "ptsd": [("wind_down", "PTSD: keep the evening predictable and the room dim; slow exhale-led breathing settles arousal before sleep.")],
    "ibs": [("meals", "Grahani: eat at the same times daily, slowly and seated. Prefer warm CCF tea (cumin-coriander-fennel) over a solid snack if the stomach is unsettled.")],
    "ibd_crohns": [("meals", "Crohn's: during a flare, small soft meals and plenty of fluid; follow your gastroenterologist's diet over any general advice here.")],
    "ulcerative_colitis": [("meals", "Ulcerative colitis: during a flare, small soft meals and plenty of fluid; follow your gastroenterologist's diet over any general advice here.")],
    "acid_reflux": [
        ("dinner", "Amlapitta: dinner here is at least three hours before bed — lying down sooner sends acid up. Do not lie down after any meal."),
        ("sleep", "Acid reflux: raise the head of the bed by 15–20 cm and sleep on your left side."),
    ],
    "constipation_chronic": [("wake", "Constipation: sit for the bowel at the same time every morning after the warm water, without straining.")],
    "hemorrhoids": [("wake", "Arsha: never strain on the toilet — keep a footstool under your feet, and do not sit there longer than five minutes.")],
    "fatty_liver": [("dinner", "Fatty liver: no alcohol, and nothing after dinner — the overnight fast is part of the treatment.")],
    "kidney_stones": [("wake", "Kidney stones: drink water steadily through the day — enough that your urine stays pale (about 2.5 L unless your doctor has set a limit).")],
    "recurrent_uti": [("wake", "Recurrent UTI: drink water through the day and never hold urine — Mutra Vega Dharana is classically a cause.")],
    "chronic_kidney_disease": [("wake", "Kidney disease: keep to the fluid limit your nephrologist has set — it overrides every 'drink water' line in this routine.")],
    "migraine": [("meals", "Migraine: do not skip or delay this meal — missed meals and irregular sleep are two of the commonest triggers.")],
    "epilepsy": [
        ("sleep", "Epilepsy: lost sleep is a leading seizure trigger. Keep this bedtime, and do not cut sleep for an early start."),
        ("bath", "Epilepsy: shower rather than bathe, and do not lock the bathroom door."),
    ],
    "vertigo": [("wake", "Vertigo: sit up slowly, pause on the edge of the bed, then stand. Keep a light on for night-time trips to the bathroom.")],
    "parkinson": [("wake", "Parkinson's: plan the morning routine for when your medicine has started working, and sit to dress and oil the feet.")],
    "multiple_sclerosis": [("bath", "Multiple sclerosis: heat can bring symptoms on for a while — keep bath and oil warm, not hot.")],
    "peripheral_neuropathy": [("bath", "Neuropathy: test the water with your elbow, not your feet, and check your feet for cuts after the oil massage.")],
    "osteoporosis": [("bath", "Osteoporosis: oiled feet and a wet floor are a fall risk — use a non-slip mat and wipe your soles before you stand.")],
    "osteoarthritis": [("exercise", "Sandhivata: warm up for 5 minutes and oil the joints before moving. Mild discomfort that settles by the next morning is fine.")],
    "rheumatoid_arthritis": [("exercise", "Amavata: on flare days rest the inflamed joints and move the rest. Morning stiffness eases with warmth — a warm bath before exercise helps.")],
    "gout": [("wake", "Vatarakta: drink water through the day and avoid alcohol, especially beer.")],
    "fibromyalgia": [("exercise", "Fibromyalgia: start well below what you think you can do, and increase slowly. A worse 24–48 hours afterwards means too much.")],
    "chronic_fatigue_syndrome": [("exercise", "ME/CFS: pace your activity and stop well before you tire. NICE (2021) advises against fixed, stepped-up exercise programmes.")],
    "asthma": [("exercise", "Shwasa: keep your reliever inhaler with you, warm up gradually, and avoid exercising in cold air or after heavy meals.")],
    "copd": [("exercise", "COPD: pace with pursed-lip breathing and stop to rest before you are breathless. Pulmonary rehabilitation is the evidence-based programme.")],
    "chronic_bronchitis": [("exercise", "Chronic bronchitis: avoid cold, smoky or dusty air while exercising.")],
    "allergic_rhinitis": [("rituals", "Allergic rhinitis: skip Nasya on a day with a fever or an acute cold, and rinse the face after being outdoors in pollen season.")],
    "sinusitis": [("rituals", "Sinusitis: skip Nasya during an acute infection or fever. Steam inhalation is safe meanwhile.")],
    "hypothyroidism": [("wake", "Hypothyroidism: take your thyroid tablet on waking with plain water, 30–60 minutes before breakfast, milk or tea.")],
    "hashimoto": [("wake", "Hashimoto's: take your thyroid tablet on waking with plain water, 30–60 minutes before breakfast, milk or tea.")],
    "hyperthyroidism": [("bath", "Overactive thyroid: heat is poorly tolerated — keep bath water and the room cool.")],
    "pcos": [("exercise", "PCOS: exercise on most days is one of the most effective treatments — consistency matters more than intensity.")],
    "endometriosis": [("sleep", "Endometriosis: a warm compress on the lower abdomen in the evening eases pain on bad days.")],
    "menorrhagia": [("wake", "Heavy periods: rise slowly on heavy days, and ask your doctor to check your iron.")],
    "dysmenorrhea": [("exercise", "Artava: ease the intensity on days 1–3 of your period. Apana Vata moves downwards then — no inversions.")],
    "psoriasis": [("bath", "Psoriasis: oil is good for the plaques, but use lukewarm water, pat dry, and skip any scrubbing on lesions.")],
    "eczema": [("bath", "Eczema: lukewarm water only, short showers, and oil on damp skin straight after. Skip dry brushing.")],
    "urticaria": [("bath", "Urticaria: hot water and friction both trigger hives — lukewarm water, no dry brushing.")],
    "rosacea": [("bath", "Rosacea: keep the face out of hot water and steam, and skip facial oil massage on flare days.")],
    "acne_severe": [("bath", "Acne: keep body oil off the face; wash the face with a gentle cleanser instead.")],
    "lupus": [("exercise", "Lupus: exercise early or late in the day out of direct sun, and rest on flare days.")],
    "varicose_veins": [("work", "Varicose veins: do not sit or stand still for more than an hour — walk or raise your legs.")],
    "celiac": [("breakfast", "Coeliac disease: everything here must be gluten-free, including oats unless labelled gluten-free.")],
    "high_cholesterol": [("meals", "High cholesterol: a 10-minute walk after meals and daily movement both raise HDL.")],
    "pregnancy": [("exercise", "Pregnancy: keep to an effort where you can still talk, and from the second trimester do not exercise lying flat on your back. Stop and call your midwife for bleeding, fluid leaking, dizziness, chest pain or calf pain (ACOG Committee Opinion 804).")],
    "tinnitus": [("wind_down", "Tinnitus: a quiet background sound in the bedroom makes it less noticeable at night.")],
    "cervical_spondylosis": [("rituals", "Cervical spondylosis: for Nasya, lie on your back with a pillow under the shoulders rather than tipping the head back while standing.")],
    "gallstones": [("meals", "Gallstones: eat at regular times and do not skip meals — long gaps and crash dieting both make stones more likely to cause pain.")],
    "uterine_fibroids": [("wake", "Fibroids: if your periods are heavy, rise slowly on those days and ask your doctor to check your iron.")],
    "scleroderma": [("bath", "Scleroderma: cold brings on Raynaud's attacks — keep the water warm, never cold, and dry and oil the hands and feet straight after.")],
    "vitiligo": [("exercise", "Vitiligo: the white patches burn easily — exercise outdoors early or late, with sunscreen on exposed patches.")],
}

# Conditions whose canonical key differs from the table above.
_NOTE_ALIASES = {"hypothyroid": "hypothyroidism", "irritable_bowel": "ibs", "arthritis": "osteoarthritis"}


def _canonical_conditions(conditions) -> set[str]:
    out = set()
    for c in conditions or []:
        raw = str(c).strip().lower().replace(" ", "_")
        if not raw:
            continue
        canon = normalize_condition(raw) or raw
        out.add(_NOTE_ALIASES.get(canon, canon))
        out.add(raw)
    return out


# Notes for what medicines change about the day.
_MEDICATION_SLOT_NOTES: dict[str, list[tuple[str, str]]] = {
    "thyroid_hormone": [("wake", "Thyroid tablet: take it on waking with plain water, 30–60 minutes before breakfast, milk, tea or any herb.")],
    "insulin_or_sulfonylurea": [
        ("breakfast", "Your diabetes medicine lowers glucose whether or not you eat — do not skip this meal."),
        ("exercise", "Carry fast carbohydrate when you exercise; your medicine can bring glucose down during it."),
    ],
    "anticoagulants": [("bath", "Blood thinner: firm massage and dry brushing bruise easily on it — keep the strokes light.")],
    "antiplatelets": [("bath", "Antiplatelet medicine: keep massage strokes light; you bruise more easily on it.")],
    "antihypertensives": [("wake", "Blood-pressure medicine: sit up slowly and stand after a pause — it can drop your pressure as you rise.")],
    "diuretics": [("wake", "Water tablet: take it in the morning, not later in the day, so it does not wake you at night.")],
    "lithium": [("exercise", "Lithium: sweating raises its level in your blood — drink water through exercise and hot weather.")],
}


def _apply_condition_notes(timeline: list, conditions: list, gender: str, age: int,
                           med_classes: set | None = None) -> list:
    cset = _canonical_conditions(conditions)
    ab = _age_band(age)
    med_classes = set(med_classes or ())
    # One note per instruction. The condition and the medicine that treats it say
    # the same thing — hypothyroidism and the thyroid tablet, diabetes and insulin —
    # and four conditions each asked for the same walk after the same meal.
    skip_conditions = set()
    if "thyroid_hormone" in med_classes:
        skip_conditions |= {"hypothyroidism", "hashimoto"}
    skip_meds = set()
    if cset & {"diabetes_type2", "diabetes_type1"}:
        skip_meds.add("insulin_or_sulfonylurea:exercise")
    wanted: list[tuple[str, str]] = []
    for c in sorted(cset):
        if c not in skip_conditions:
            wanted += _CONDITION_SLOT_NOTES.get(c, [])
    for mc in sorted(med_classes):
        wanted += [(t, x) for t, x in _MEDICATION_SLOT_NOTES.get(mc, [])
                   if f"{mc}:{t}" not in skip_meds]
    if ab == "vriddha":
        wanted.append(("exercise", "Vriddha Avastha: all exercise at 50% intensity. Prioritise joint mobility and balance over cardiovascular intensity. Daily Abhyanga before exercise is mandatory."))

    for s in timeline:
        notes = list(s.pop("_notes", []))
        for target, text in wanted:
            if not _SLOT_TARGETS[target](s) or text in notes:
                continue
            if "10-minute walk" in text and any("10-minute walk" in n for n in notes):
                continue
            notes.append(text)
        if notes:
            s["condition_notes"] = notes
            s["condition_note"] = " | ".join(notes)
    return timeline


# ── Herbs, oils and foods ─────────────────────────────────────────────────────
# The routine names three herbal drinks, Trikatu, Chyawanprash, sesame and mustard
# oil, ghee, milk and a seasonal food list. None passed a gate: a sesame-allergic
# Vata user was told to put sesame oil in the nose, on the skin and in the mouth
# every morning, and a dairy-allergic one to drink milk every night.
_ROUTINE_HERBS = ("Ashwagandha Churna", "Brahmi Churna", "Triphala Churna",
                  "Trikatu Churna", "Chyawanprash")

_OIL_ALLERGENS = {"sesame": "sesame", "mustard": "mustard"}


def _declared_allergens(user_profile: dict, prefs: dict) -> list[str]:
    """Profile allergies ∪ the diet form's allergies and intolerances, plus dairy and
    honey for a vegan. One list, as `diet_allergies` builds for the diet plan."""
    diet = prefs.get("diet") or {}
    out = []
    for src in (user_profile.get("allergies"), diet.get("food_allergies"), diet.get("food_intolerances")):
        if isinstance(src, str):
            src = [src]
        out += [str(a).strip().lower() for a in (src or []) if str(a).strip()]
    if str(diet.get("dietary_type") or "").lower() == "vegan":
        out += ["dairy", "honey"]
    if "lactose" in out:
        out.append("dairy")
    return list(dict.fromkeys(out))


def _herb_verdicts(user_profile: dict, age: int) -> dict:
    """formulation → reason it is withheld (None = cleared), via the formulary."""
    from services.remedy_engine import screen_formulation
    out = {}
    for name in _ROUTINE_HERBS:
        if age < 16:
            out[name] = "Herbs in a child's routine are set by a Vaidya in person."
            continue
        try:
            bar, _ = screen_formulation(name, user_profile)
        except Exception:
            bar = "It could not be checked against your health record."
        # The formulary's reasons name its own tokens ("Interacts with
        # blood_thinners"); the person reads this sentence.
        out[name] = bar.replace("_", " ") if bar else bar
    return out


def _swap_oils(text: str, allergens: list[str]) -> str:
    """Name an oil the person can use. 'mustard or sesame oil' with a sesame allergy
    is 'mustard oil'; 'sesame oil' alone becomes sunflower oil."""
    for key, word in _OIL_ALLERGENS.items():
        if key not in allergens:
            continue
        text = re.sub(rf"\b{word} or (\w+) oil", r"\1 oil", text, flags=re.I)
        text = re.sub(rf"\b(\w+) or {word} oil", r"\1 oil", text, flags=re.I)
        text = re.sub(rf"\b{word} oil\b", "sunflower oil", text, flags=re.I)
        text = re.sub(rf"\b{word} Abhyanga\b", "sunflower oil Abhyanga", text, flags=re.I)
        text = re.sub(rf"\b{word}\b(?= in winter)", "sunflower", text, flags=re.I)
        text = re.sub(rf"\bwarm {word}\b", "warm sunflower oil", text, flags=re.I)
    if "dairy" in allergens:
        text = re.sub(r"\bghee or (\w+) oil", r"\1 oil", text, flags=re.I)
        text = re.sub(r" If Vata constipation persists, add 1 tsp warm ghee to the morning water\.", "", text)
    return text


def _dairy_free(text: str) -> str:
    return re.sub(r"\b(warm )?milk\b", "warm oat milk", text, flags=re.I) if text else text


def _screen_food_list(items: list, conditions: list, allergens: list, is_pregnant: bool) -> tuple[list, list]:
    """(kept, withheld) — a food list held to the diet plan's own Pathya card rule."""
    if not items:
        return items, []
    from services.ahara_safety import apply_advisory_safety
    card = {"pathya_apathya": {"pathya": list(items)}}
    apply_advisory_safety(card, list(conditions), allergens, pregnant=is_pregnant)
    # The diet card's reason is written for a clinician ("names 'ghee', which is
    # Apathya here — The patient declared this"); this one is read by the patient.
    withheld = [{"item": w["item"],
                 "reason": f"contains {w['food']} — {str(w['condition']).replace('Declared ', 'your declared ')}"}
                for w in card.get("withheld_recommendations") or []]
    return card["pathya_apathya"]["pathya"], withheld


# The day's own lines name food too — the snack's options, the Agni notes, the tea at
# the desk — and none of it passed a gate: a diabetic's meal card withheld dates
# while every 4 PM row of the week still said "Soaked dates, warm milk, or light
# soup". Each option is screened on its own, as a card entry would be; screening the
# sentence whole matched "sugar" inside "low-blood-sugar".
# (phrase, its options as written, what is said when every option is withheld)
_SLOT_FOOD_LISTS = (
    ("Soaked dates, warm milk, or light soup", ("Soaked dates", "warm milk", "light soup"), "Light soup"),
    ("Coconut water, sweet fruit, or fennel-coriander tea",
     ("Coconut water", "sweet fruit", "fennel-coriander tea"), "Fennel-coriander tea"),
    ("Soaked dates or warm broth", ("Soaked dates", "warm broth"), "Warm broth"),
    ("Ginger tea or light fruit", ("Ginger tea", "light fruit"), "Warm water"),
    ("Warm spiced porridge or fruit", ("Warm spiced porridge", "fruit"), "Warm spiced porridge"),
)
# (phrase, the food it names, what replaces it when that food is withheld)
_SLOT_FOOD_SWAPS = (
    ("Sip warm ginger tea 15 min before to kindle fire.", "ginger tea",
     "Sip CCF tea (cumin-coriander-fennel) 15 min before to kindle fire."),
    (" or sip ginger tea", "ginger tea", ""),
    ("Sip warm ginger tea.", "ginger tea", "Sip warm water."),
    ("Start with hot ginger water first.", "ginger", "Start with warm water first."),
    ("Hot ginger-lemon water", "ginger lemon water", "Hot water"),
    ("1 glass hot water with grated ginger and lemon.", "ginger lemon water", "1 glass hot water."),
    ("the hot ginger-lemon water", "ginger lemon water", "the hot water"),
    ("Warm ginger tea is your daily digestive ally.", "ginger tea",
     "Warm CCF tea (cumin-coriander-fennel) is your daily digestive ally."),
    ("Trikatu and ginger are your daily digestive allies.", "ginger",
     "Trikatu is your daily digestive ally."),
)


def _join_options(items: list) -> str:
    return items[0] if len(items) == 1 else (
        f"{items[0]} or {items[1]}" if len(items) == 2 else f"{', '.join(items[:-1])}, or {items[-1]}")


def _screen_slot_text(text: str, conditions: list, allergens: list, is_pregnant: bool,
                      withheld: list) -> str:
    """The food a line of the day names, held to the meal card's rule. Withheld
    options are appended to `withheld` as {item, reason}."""
    if not text:
        return text
    for phrase, options, fallback in _SLOT_FOOD_LISTS:
        if phrase not in text:
            continue
        kept, out = _screen_food_list(list(options), conditions, allergens, is_pregnant)
        if not out:
            continue
        withheld += out
        kept = [k.lower() if i and k[0].isupper() else k for i, k in enumerate(kept)]
        text = text.replace(phrase, (kept[0][0].upper() + _join_options(kept)[1:]) if kept else fallback)
    for phrase, food, replacement in _SLOT_FOOD_SWAPS:
        if phrase not in text:
            continue
        _, out = _screen_food_list([food], conditions, allergens, is_pregnant)
        if out:
            withheld += out
            text = text.replace(phrase, replacement)
    return text


# ── Build dinacharya protocol block ──────────────────────────────────────────
def _build_dinacharya_protocol(dosha: str, secondary: str, vikriti: str, season: str,
                                conditions: list, gender: str, age: int, agni_type: str,
                                is_pregnant: bool = False, wake_preference: str | None = None,
                                anchors: dict | None = None, herbs: dict | None = None,
                                allergens: list | None = None, ctx: dict | None = None) -> dict:
    ab = _age_band(age)
    sd = _SEASON_MAP.get((season or "sharad").lower(), _DEFAULT_SEASON)
    anchors = anchors or _day_anchors(dosha, season, age, wake_preference)
    herbs = herbs or {}
    allergens = allergens or []
    ctx = ctx or {}
    cset = ctx.get("conditions") or _canonical_conditions(conditions)
    med_classes = ctx.get("med_classes") or set()

    rituals = [dict(r) for r in _MORNING_RITUALS_BASE.get(dosha, _MORNING_RITUALS_BASE["vata"])]
    rituals = _apply_age_modifications(rituals, ab, dosha)
    pregnancy_notices: list = []
    if is_pregnant:
        rituals, pregnancy_notices = _apply_pregnancy_modifications(rituals, dosha)
        pregnancy_notices.append(
            "Shodhana — Vamana, Virechana, Basti and Nasya — is set aside for the "
            "whole of pregnancy. Seasonal guidance here is written accordingly.")

    withheld: list[dict] = []
    skin = cset & {"psoriasis", "eczema", "urticaria", "rosacea"}
    bleeds = med_classes & {"anticoagulants", "antiplatelets"}
    high_ama = str(ctx.get("ama") or "").lower() in ("high", "severe")
    for r in rituals:
        if r.get("withheld"):
            continue
        if r["name"] == "Garshana" and (skin or bleeds):
            why = (f"dry brushing aggravates {sorted(skin)[0]}" if skin
                   else "it bruises on a blood thinner")
            r.update(withheld=True, duration_min=0,
                     instruction=f"Skipped for you — {why}. Go straight to the oil.")
            withheld.append({"practice": "Garshana", "reason": why})
        elif r["name"] == "Abhyanga" and high_ama and not is_pregnant:
            r.update(instruction=("Udwartana instead of oil today: a dry massage with warm barley or "
                                  "chickpea flour, upward strokes. Oil is classically withheld while "
                                  "Ama is high (Ashtanga Hridayam Su. 2) — return to Abhyanga once "
                                  "the tongue coating clears."))
            withheld.append({"practice": "Abhyanga", "reason": "Ama is high — Udwartana replaces oil until it clears"})
        elif r["name"] == "Abhyanga" and bleeds:
            r["instruction"] = r["instruction"].replace("short vigorous strokes", "light strokes") + \
                " Keep the pressure light on your blood thinner — firm massage bruises."
        elif r["name"] == "Nasya" and (cset & {"sinusitis", "allergic_rhinitis"}):
            r["instruction"] += " Skip it on any day with a fever, an acute cold or a sinus infection."
        r["instruction"] = _swap_oils(r["instruction"], allergens)
        r["instruction"] = _screen_slot_text(r["instruction"], conditions, allergens, is_pregnant,
                                             ctx.setdefault("slot_withheld", []))

    evening = []
    for r in (dict(x) for x in _EVENING_RITUALS_BASE.get(dosha, _EVENING_RITUALS_BASE["vata"])):
        herb = r.pop("herb", None)
        if herb and herbs.get(herb):
            plain_name, plain_text = _PLAIN_DRINK[herb]
            withheld.append({"practice": r["name"], "reason": herbs[herb]})
            r["name"], r["instruction"] = plain_name, plain_text
        if "dairy" in allergens and r.get("icon") == "milk":
            r["name"], r["instruction"] = _DAIRY_FREE_DRINK
        if "mishri" in r["instruction"] and cset & {"diabetes_type2", "diabetes_type1", "metabolic_syndrome"}:
            r["instruction"] = r["instruction"].replace(" + mishri", "")
        r["instruction"] = _swap_oils(r["instruction"], allergens)
        r["instruction"] = _screen_slot_text(r["instruction"], conditions, allergens, is_pregnant,
                                             ctx.setdefault("slot_withheld", []))
        evening.append(r)

    shodhana_ok = not is_pregnant and 16 <= age < 70
    season_notes = _PREGNANCY_SEASON_NOTES if is_pregnant else {
        "vasanta":  "Spring Kapha season: prioritise Garshana, vigorous exercise, light meals. Avoid Divaswapna (daytime napping).",
        "grishma":  "Summer Pitta season: coconut Abhyanga, avoid afternoon exercise in heat, Sheetali Pranayama, limit spicy food.",
        "varsha":   "Monsoon Vata season: daily Abhyanga is essential. Boil all drinking water. Sour-salty-sweet foods protect Vata.",
        "sharad":   ("Autumn Pitta season: Virechana (Pitta purge) classically recommended. Moonbathing beneficial. Avoid spicy food."
                     if shodhana_ok else
                     "Autumn Pitta season: moonbathing, cooling bitter foods, avoid spicy food. Seasonal cleansing therapies are not undertaken at your age."),
        "hemanta":  "Early Winter: maximum nourishment season. Heavy sesame Abhyanga. Strong exercise. Nourish Shukra Dhatu.",
        "shishira": "Late Winter: keep body warm at all times. Sesame Abhyanga essential. Avoid cold, dry, and light foods.",
    }
    season_note = season_notes.get((season or "sharad").lower(), "")
    if ctx.get("exercise_cap", "full") != "full" or ab == "vriddha":
        season_note = re.sub(r"\bStrong exercise", "Exercise within your limits", season_note)
        season_note = re.sub(r"\bvigorous exercise", "exercise within your limits", season_note)
    if any(r["name"] == "Garshana" and r.get("withheld") for r in rituals) or \
            (dosha != "kapha" and (skin or bleeds or ab in ("balya", "vriddha"))):
        season_note = season_note.replace("prioritise Garshana, ", "prioritise ")
    season_note = _swap_oils(season_note, allergens)

    principles = {
        "vata": "Regularity is medicine for Vata. Same wake time, same meal times, same sleep time every day. Vata thrives on rhythm and collapses under chaos.",
        "pitta": "Moderation is medicine for Pitta. Never skip meals, avoid afternoon heat exercise, take a true midday rest. Pitta destroyed by pushing past limits.",
        "kapha": "Movement is medicine for Kapha. No Divaswapna (daytime sleep). Early rising, regular exercise, and light early dinner are non-negotiable daily anchors.",
    }
    agni_general = (ctx.get("agni_notes") or _agni_notes(agni_type or "sama", True, False)).get("general", "")

    sec_note = _secondary_dosha_note(dosha, secondary, not herbs.get("Ashwagandha Churna")) \
        if secondary and secondary != dosha else ""
    sec_note = _swap_oils(sec_note, allergens)

    return {
        "wake_time":             _clock(anchors["wake"]),
        "wake_notice":           anchors["wake_notice"],
        "sleep_notice":          anchors["sleep_notice"],
        "sleep_time":            _clock(anchors["bed"]),
        "sleep_hours":           anchors["sleep_hours"],
        "age_band":              ab,
        "agni_type":             agni_type or "sama",
        "agni_source":           ctx.get("agni_source"),
        "agni_general_guidance": agni_general,
        "morning_rituals":       rituals,
        "pregnancy_notices":     pregnancy_notices,
        "evening_rituals":       evening,
        "withheld_practices":    withheld,
        "season_label":          sd["label"],
        "season_practice_note":  season_note,
        "agni_level":            sd["agni"],
        "key_principle":         principles.get(dosha, ""),
        "dual_dosha_note":       sec_note,
    }


# ── Seasonal Ritucharya block ─────────────────────────────────────────────────
def _build_seasonal_ritucharya(season: str, dosha: str, is_pregnant: bool = False,
                               age: int = 30, herbs: dict | None = None,
                               conditions: list | None = None, allergens: list | None = None,
                               exercise_cap: str = "full", skip_garshana: bool = False) -> dict:
    s = (season or "sharad").lower()
    sd = _SEASON_MAP.get(s, _DEFAULT_SEASON)
    herbs = herbs or {}
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
    shodhana_ok = not is_pregnant and 16 <= age < 70
    practices = _PREGNANCY_PRACTICES if is_pregnant else {
        "shishira": ["Daily sesame Abhyanga","Hot food and drink always","Chyawanprash / Ashwagandha Rasayana","Keep body warm"],
        "vasanta":  ["Garshana (dry brushing) daily","Vigorous Vyayama","Trikatu and bitter herbs","Vamana if supervised"],
        "grishma":  ["Coconut / Chandana Abhyanga","Avoid afternoon exertion","Sheetali Pranayama","Moonbathing (Chandrakirana)"],
        "varsha":   ["Daily Abhyanga is essential","Ginger-rock salt before meals","Basti karma (if supervised)","Avoid cold food strictly"],
        "sharad":   ["Virechana (supervised)","Moonbathing","Amalaki Rasayana","Bitter-astringent food emphasis"],
        "hemanta":  ["Maximum nourishment","Heaviest Abhyanga with warm sesame oil","Strong exercise","Rest and early nights"],
    }
    chosen = []
    withheld = []
    for p in practices.get(s, []):
        low = p.lower()
        if not is_pregnant and not shodhana_ok and any(t in low for t in ("vamana", "virechana", "basti")):
            withheld.append({"item": p, "reason": "Cleansing therapies are not undertaken under 16 or past 70."})
            continue
        if "chyawanprash" in low and herbs.get("Chyawanprash"):
            withheld.append({"item": "Chyawanprash", "reason": herbs["Chyawanprash"]})
            p = re.sub(r"Chyawanprash /\s*", "", p)
        if "ashwagandha" in low and herbs.get("Ashwagandha Churna"):
            withheld.append({"item": "Ashwagandha Rasayana", "reason": herbs["Ashwagandha Churna"]})
            p = re.sub(r"\s*/?\s*Ashwagandha Rasayana", "", p).strip(" /")
            if not p:
                continue
        if "trikatu" in low and herbs.get("Trikatu Churna"):
            withheld.append({"item": "Trikatu", "reason": herbs["Trikatu Churna"]})
            p = "Bitter herbs and greens"
        if "garshana" in low and skip_garshana:
            withheld.append({"item": p, "reason": "Dry brushing is left out of your routine (see the morning protocol)."})
            continue
        if (exercise_cap != "full" or age >= 60) and re.search(r"vigorous|strong exercise", low):
            p = "Daily exercise within your limits"
        chosen.append(_swap_oils(p, allergens or []))

    rec, food_withheld = _screen_food_list(foods.get(s, []), conditions or [], allergens or [], is_pregnant)
    return {
        "season":             sd["label"],
        "agni_level":         sd["agni"],
        "dominant_dosha":     sd["peak_dosha"],
        "recommended_foods":  rec,
        "foods_to_avoid":     avoids.get(s, []),
        "seasonal_practices": chosen,
        "withheld":           withheld + [{"item": w["item"], "reason": w["reason"]} for w in food_withheld],
    }


# ── Meal guidance per dosha ───────────────────────────────────────────────────
def _build_meal_guidance(dosha: str, season: str, agni_type: str, agni_notes: dict | None = None,
                         conditions: list | None = None, allergens: list | None = None,
                         is_pregnant: bool = False, meal_times: dict | None = None) -> dict:
    s = (season or "sharad").lower()
    sd = _SEASON_MAP.get(s, _DEFAULT_SEASON)
    agni = sd["agni"]
    agni_notes_list = agni_notes or _agni_notes(agni_type or "sama", True, False)

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
            "dinner":    {"ideal_time": "6:00–7:00 PM",  "favour": ["light cooling soup","steamed vegetables","moong dal","mild coconut curry"], "avoid": ["spicy food at night","wine","heavy fried food"]},
        },
        "kapha": {
            "general": "Light, dry, warm, spiced, and pungent food in small portions. Avoid dairy, sweets, and oily food — they directly increase Kapha and Ama.",
            "breakfast": {"ideal_time": "8:00–9:00 AM", "favour": ["light spiced porridge","ginger tea","warm fruit","rye or barley bread"], "avoid": ["dairy","sweet yoghurt","cold food","bananas","heavy breakfast"]},
            "lunch":     {"ideal_time": "12:30–1:30 PM", "favour": ["lentil soup","stir-fried bitter vegetables","barley or millet","warm spiced rice (minimal ghee)"], "avoid": ["heavy oily food","excess wheat","sweet desserts","cold water at meals"]},
            "snack":     {"ideal_time": "4:00–4:30 PM",  "favour": ["ginger tea","apple or pear","light roasted chickpeas","warm broth"], "avoid": ["biscuits","dairy snacks","sweets","chips"]},
            "dinner":    {"ideal_time": "6:00–6:30 PM",  "favour": ["light vegetable soup","dal water","steamed greens","small portion of grains"], "avoid": ["heavy dinner","late eating","oily food","sweet desserts"]},
        },
    }
    guidance = {k: (dict(v) if isinstance(v, dict) else v) for k, v in base.get(dosha, base["vata"]).items()}
    withheld = []
    for meal in ("breakfast", "lunch", "snack", "dinner"):
        m = guidance[meal]
        kept, out = _screen_food_list(m["favour"], conditions or [], allergens or [], is_pregnant)
        m["favour"] = kept
        withheld += [{"meal": meal, "item": w["item"], "reason": w["reason"]} for w in out]
        # The card printed its own clock beside a timeline that had moved: "Dinner
        # 6:30–7:30 PM" over a dinner the timeline put at 6 PM for an early bed.
        if meal_times and meal_times.get(meal):
            m["ideal_time"] = meal_times[meal]
    # Every seasonal note names its season. "Agni is strong" alone (Sharad and Shishira)
    # read as a statement about the person, printed beside "Your Agni type is Vishama".
    season_name = sd["label"].split(" (")[0]
    agni_seasonal_notes = {
        "strongest": f"In {season_name}, digestive fire is at its seasonal peak — heavier, nourishing meals generally suit the season.",
        "strong":    f"In {season_name}, digestive fire is generally strong — well-cooked, moderately heavy meals suit the season.",
        "mild":      f"In {season_name}, digestive fire is generally mild — keep meals lighter and avoid heavy, oily food.",
        "weak":      f"In {season_name}, digestive fire is generally weak despite the heat — prefer easily digestible, cooling foods.",
        "very_weak": f"In {season_name}, digestive fire is generally very weak — cooked, light, easily digestible food only. No raw food.",
    }
    note = agni_seasonal_notes.get(agni, "")
    # The season's tendency must not override the person's own Agni: a strong season
    # does not make Manda or Vishama Agni able to take heavier meals.
    own = (agni_type or "").lower()
    if note and agni in ("strongest", "strong") and own in ("manda", "vishama"):
        label = {"manda": "Manda (slow)", "vishama": "Vishama (irregular)"}[own]
        note += (f" That is the season, not you: your own Agni is {label}, so your digestion comes first — "
                 "keep meals regular and moderate rather than heavier.")
    guidance["seasonal_note"] = note
    guidance["agni_note"] = agni_notes_list.get("general", "")
    guidance["withheld"] = withheld
    return guidance


# ── Extract gym/yoga schedule from plan history ───────────────────────────────
_WEEKDAYS = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]


def _weekday_index(day: dict) -> int | None:
    """Map a plan day's name to a 0–6 index, or None if it isn't a known weekday.
    Returning None (vs raising) lets one malformed day be skipped without the bare
    except below discarding the ENTIRE week's schedule."""
    name = str(day.get("day_name", "")).strip().lower()
    return _WEEKDAYS.index(name) if name in _WEEKDAYS else None


def _extract_gym_schedule(gym_plan_data: dict) -> dict:
    """The gym plan's week one, one entry per weekday.

    The gym engine marks a rest day `type: "recovery"` with focus "Rest &
    Recovery". This read only `type == "rest"`, so every rest day reached the
    routine as "Gym — Rest & Recovery, 45–60 min" — a workout on the day the plan
    prescribed rest. The quoted length was a literal for every session too; the
    gym plan carries its own.
    """
    try:
        week1 = (gym_plan_data.get("four_week_plan") or [{}])[0]
        result = {}
        for d in week1.get("days", []) or []:
            idx = _weekday_index(d)
            if idx is None:
                continue
            is_rest = d.get("type") in ("rest", "recovery") or bool(d.get("is_rest_day"))
            focus   = d.get("focus", "Workout")
            mins    = d.get("estimated_duration_minutes")
            result[idx] = {
                "ex_type":  "rest" if is_rest else "gym",
                "ex_label": "Gym Rest Day" if is_rest else f"Gym — {focus}",
                "ex_duration": None if is_rest else (f"{int(mins)} min" if mins else "45–60 min"),
                "ex_minutes": None if is_rest else (int(mins) if mins else 60),
                "is_rest":  is_rest,
                "gym_focus": None if is_rest else focus,
            }
        return result
    except Exception:
        return {}


def _extract_yoga_schedule(yoga_plan_data: dict) -> dict:
    try:
        week1 = (yoga_plan_data.get("four_week_plan") or [{}])[0]
        result = {}
        for d in week1.get("days", []) or []:
            idx = _weekday_index(d)
            if idx is None:
                continue
            is_rest = d.get("rest", False)
            session = d.get("session") or {}
            theme   = session.get("dosha_theme", "Yoga Practice")
            # `or 30` (not .get default) so an explicit null duration doesn't crash int()
            dur     = session.get("total_duration_minutes") or 30
            result[idx] = {
                "ex_type":  "rest" if is_rest else "yoga",
                "ex_label": "Yoga Rest Day" if is_rest else f"Yoga — {theme}",
                "ex_duration": None if is_rest else f"{int(dur)} min",
                "ex_minutes": None if is_rest else int(dur),
                "is_rest":  is_rest,
            }
        return result
    except Exception:
        return {}


# ── Build 7-day routine ───────────────────────────────────────────────────────
DAY_NAMES = ["Monday","Tuesday","Wednesday","Thursday","Friday","Saturday","Sunday"]


def _ex_minutes(ex_info: dict) -> int | None:
    if ex_info.get("ex_minutes"):
        return ex_info["ex_minutes"]
    m = re.match(r"(\d+)", str(ex_info.get("ex_duration") or ""))
    return int(m.group(1)) if m else None


def _build_weekly_routine(dosha: str, secondary: str, season: str, if_window: str,
                           conditions: list, gender: str, age: int,
                           agni_type: str, occupation: str,
                           fasting_days: list,
                           gym_schedule: dict, yoga_schedule: dict,
                           is_pregnant: bool = False,
                           wake_preference: str | None = None,
                           ctx: dict | None = None) -> list:
    ctx = ctx or {}
    ab        = _age_band(age)
    fasting   = {d.lower().strip() for d in (fasting_days or [])}
    anchors   = ctx.get("anchors") or _day_anchors(dosha, season, age, wake_preference)
    limits    = ctx.get("limits") or {"cap": "full", "low_impact": False, "no_swim_alone": False, "reasons": []}
    herbs     = ctx.get("herbs") or {}
    allergens = ctx.get("allergens") or []
    yoga_evening = ctx.get("yoga_time") == "evening"
    gym_time = "evening" if ctx.get("gym_time") == "evening" else "morning"
    dinner_gap = 180 if "acid_reflux" in (ctx.get("conditions") or set()) else 150
    week_plan = _DEFAULT_WEEK.get(dosha, _DEFAULT_WEEK["vata"])
    # The week's exercise labels are a FOURTH structure carrying the same
    # instruction — "Full Rest — Extended Abhyanga + Nasya". The timeline gate
    # reads `description`; this one lives in `ex_label`, in a separate table, and
    # survived three previous gates. Four copies of one sentence.
    if is_pregnant or ab == "balya":
        week_plan = [{**d, "ex_label": re.sub(r"\s*\+?\s*Nasya", "", d.get("ex_label", ""),
                                              flags=re.I).strip(" +—-")}
                     for d in week_plan]

    weekly = []
    for i, day_meta in enumerate(week_plan):
        day_name   = day_meta["day_name"]
        is_fasting = day_name.lower() in fasting

        # Each linked plan's session gets its own slot. Gym and yoga used to compete
        # for one: gym won every shared day, so a morning yoga practitioner who also
        # lifted saw their yoga plan on rest days only. Yoga goes where the yoga form
        # put it; gym where the routine form did. Two sessions in the same part of
        # the day run back to back, gym first, so the yoga is the cool-down.
        gym_day = gym_schedule.get(i)
        yoga_day = yoga_schedule.get(i)
        planned = {"morning": [], "evening": []}
        if gym_day and not gym_day["is_rest"]:
            planned[gym_time].append(gym_day)
        if yoga_day and not yoga_day["is_rest"]:
            planned["evening" if yoga_evening else "morning"].append(yoga_day)
        from_plan = bool(planned["morning"] or planned["evening"])
        morning_walk = from_plan and not planned["morning"]
        if from_plan:
            ex_info = planned["morning"][0] if planned["morning"] else {
                "ex_type": "walk", "ex_label": "Morning Walk (15–20 min)", "ex_duration": "15–20 min",
                "is_rest": False,
                "note": (f"Your {' and '.join(x['ex_type'] for x in planned['evening'])} "
                         f"{'sessions are' if len(planned['evening']) > 1 else 'session is'} in "
                         "the evening today; a short walk keeps the morning rhythm.")}
        elif gym_day or yoga_day:
            ex_info = gym_day or yoga_day
        else:
            ex_info = {
                "ex_type":    day_meta["ex_type"],
                "ex_label":   day_meta["ex_label"],
                "ex_duration": day_meta.get("ex_duration"),
                "is_rest":    day_meta["is_rest"],
            }

        # Age band exercise override
        if not from_plan and ab in _AGE_EXERCISE_OVERRIDE:
            override = _AGE_EXERCISE_OVERRIDE[ab]
            if ex_info.get("ex_type") in override:
                new_type, new_label, new_dur = override[ex_info["ex_type"]]
                ex_info = {**ex_info, "ex_type": new_type, "ex_label": new_label, "ex_duration": new_dur,
                           "replaced": True}
        if not from_plan:
            ex_info = _limit_exercise(ex_info, limits)

        if from_plan:
            sessions = {part: [_ex_minutes(x) or 30 for x in planned[part]] for part in planned}
        else:
            minutes = None if ex_info.get("is_rest") else _ex_minutes(ex_info)
            sessions = {"morning": [minutes] if minutes else []}
        notes = ctx.get("agni_notes")
        own_day = (ctx.get("custom_times_by_day") or {}).get(day_name.lower()) or {}
        day_times = {**(ctx.get("custom_times") or {}), **own_day}
        day_anchors = _override_anchors(anchors, {k: v for k, v in own_day.items() if k in ("wake", "sleep")},
                                        age, dosha)
        pins = {}
        for k, v in day_times.items():
            if k in ("wake", "sleep") or v == SKIP:
                continue
            t = parse_hhmm(v)
            pins[k] = t + 24 * 60 if t < day_anchors["wake"] else t   # 00:15 is tonight, not this morning
        day_items = [it for it in ctx.get("custom_items") or ()
                     if not it["days"] or day_name.lower() in it["days"]]
        for it in day_items:
            t = parse_hhmm(it["time"])
            pins[it["id"]] = t + 24 * 60 if t < day_anchors["wake"] else t
        skipped = {k for k, v in day_times.items() if v == SKIP}
        if not planned["evening"] and any(it["category"] == "exercise" for it in day_items):
            skipped.add("evening_ex")   # their own exercise replaces the routine's walk
        kept_breakfast = bool(ctx.get("steady_meals") and "breakfast" in skipped)
        if kept_breakfast:
            skipped.discard("breakfast")
        day_tl = _get_base_timeline(dosha, season, if_window, agni_type, occupation,
                                    wake_preference, age, notes, None, dinner_gap, day_anchors, sessions,
                                    pins, day_items, skipped)
        # Something the user added as exercise is held to the same limits as the
        # routine's own exercise; the engine cannot read what "cricket" involves,
        # but it can say what pace this person should keep.
        if limits["reasons"]:
            for s in day_tl:
                if s.get("custom") and s.get("category") == "exercise":
                    s.setdefault("schedule_notes", []).append(
                        f"Keep this at a pace you can talk through, because of "
                        f"{', '.join(limits['reasons'])}."
                        + (" Never swim alone." if limits.get("no_swim_alone") else ""))
        for s in day_tl:
            if s.get("id") in ("wake", "sleep") and s["id"] in day_times:
                s["user_set"] = True
        if kept_breakfast:
            for s in day_tl:
                if s.get("id") == "breakfast":
                    s.setdefault("schedule_notes", []).append(
                        "Kept in, although you asked to leave it out: "
                        + ("your diabetes medicine needs food on time."
                           if "insulin_or_sulfonylurea" in (ctx.get("med_classes") or ())
                           else "meals are not skipped in pregnancy."))
        day_tl = _strip_withheld_practices(day_tl, is_pregnant)

        def _inject(info: dict, slot_key: str, planned_session: bool, after: dict | None = None) -> None:
            for s in day_tl:
                if s.get("ex_slot") != slot_key:
                    continue
                if info.get("is_rest"):
                    # The day's label ("Abhyanga Focus Day") is its theme, and the
                    # Abhyanga is already its own slot. Naming it here too put two
                    # Abhyanga rows in one morning, each with the bath notes.
                    s["activity"] = "Rest — no structured exercise"
                    s["description"] = ("Give the self-massage more time than usual today, then "
                                        "meditation or restorative practice.")
                    if "moonbathing" in info["ex_label"].lower():
                        s["description"] += " In the evening, sit out in the moonlight for a while."
                    s["type"] = "rest"
                    s["icon"] = "rest"
                    return
                s["activity"] = info["ex_label"]
                desc = s.get("description", "")
                # The template's sentence describes the template's activity —
                # "Minimum 45 min with sweating — non-negotiable for Kapha" sat
                # under a 72-year-old's gentle walk.
                if info.get("note"):
                    desc = info["note"]
                elif planned_session and after:
                    desc = (f"From your plan, straight after your {after['ex_type']} session — "
                            "it doubles as the cool-down.")
                elif planned_session:
                    desc = "From your plan."
                elif info.get("limited") or info.get("replaced"):
                    desc = "Today's session."
                desc = re.sub(r"See today's specific activity (above|below)\.\s*", "", desc) or "Today's session."
                if info.get("ex_duration") and not info.get("note"):
                    desc = f"{info['ex_duration']}. {desc}"
                if info.get("limited") and limits["reasons"]:
                    desc += (f" Kept at a pace you can talk through, because of "
                             f"{', '.join(limits['reasons'])}.")
                if limits.get("no_swim_alone") and slot_key == "morning0":
                    desc += " Never swim alone."
                if (planned_session and info.get("ex_type") == "gym" and slot_key.startswith("evening")
                        and dosha == "pitta" and s["_t"] < 18 * 60):
                    desc += (" This falls in Pitta Kala (2–6 PM), the hottest part of the day for "
                             "your constitution — train in a cool space, or move it to the morning.")
                s["description"] = desc
                if info.get("gym_focus"):
                    s["gym_focus"] = info["gym_focus"]
                if planned_session:
                    s["icon"] = "gym" if info.get("ex_type") == "gym" else "yoga"
                return

        # `time_of_day_preference` was read by the yoga plan and nowhere here, so an
        # evening practitioner's routine put their session at dawn.
        _inject(ex_info, "morning0", from_plan and not morning_walk)
        for part in ("morning", "evening"):
            for n, info in enumerate(planned[part]):
                if part == "morning" and n == 0:
                    continue
                _inject(info, f"{part}{n}", True, planned[part][n - 1] if n else None)

        # A ritual the panel withholds — Nasya in pregnancy and for a child, Kavala
        # for a child, Garshana on psoriasis — must not be named in the timeline's
        # own one-line summary of the rituals, which carries a separate copy.
        for s in day_tl:
            if s.get("type") != "self_care" or s.get("custom"):
                continue
            for name in ctx.get("withheld_rituals") or ():
                key = name.split()[0]
                s["activity"] = re.sub(rf"\b{key}\s*\+\s*", "", s["activity"])
                for word in (key, "dry brushing") if key == "Garshana" else (key,):
                    if word.lower() in s["description"].lower():
                        s["description"] = re.sub(rf",?\s*[^,.→]*\b{word}\b[^,.→]*(→\s*)?", "",
                                                  s["description"], flags=re.I).strip(" ,") or s["description"]
            s["description"] = s["description"].replace("..", ".")
            if not s["description"].endswith("."):
                s["description"] += "."
        if age < 18:
            for s in day_tl:
                if s.get("type") == "work":
                    s["activity"] = "School / Study"
                    s["description"] = "Hardest study and homework in the morning hours, when focus is best."

        # Herbal drinks and oils in the timeline — the same verdict as the panel.
        for s in day_tl:
            if s.get("custom"):
                continue   # the user's own words are not rewritten
            herb = s.pop("herb", None)
            if herb and herbs.get(herb):
                plain_name, plain_text = _PLAIN_DRINK[herb]
                if s.get("icon") == "milk":
                    s["activity"], s["description"] = plain_name, plain_text
                else:
                    s["description"] = re.sub(r"Triphala in warm water \(1 tsp\)\.\s*", "Warm water with ginger. ", s["description"])
            if "dairy" in allergens and s.get("icon") == "milk":
                s["activity"], s["description"] = _DAIRY_FREE_DRINK
            s["description"] = _screen_slot_text(
                s.get("description") or "", ctx.get("food_conditions") or [], allergens,
                is_pregnant, ctx.setdefault("slot_withheld", []))
            if "mishri" in s.get("description", "") and ctx.get("conditions", set()) & {"diabetes_type2", "diabetes_type1", "metabolic_syndrome"}:
                s["description"] = s["description"].replace(" + mishri", "")
            s["description"] = _swap_oils(s.get("description") or "", allergens)
            if s.get("meal_type") == "breakfast" and ctx.get("steady_meals"):
                s["description"] = s["description"].replace(
                    " Skip if not genuinely hungry — Kapha morning appetite is naturally low.",
                    " Keep it small, but do not skip it." + (" Your diabetes medicine needs food on time."
                                                            if "insulin_or_sulfonylurea" in ctx.get("med_classes", ()) else ""))
            if ctx.get("high_ama") and "abhyanga" in s.get("activity", "").lower() and not is_pregnant:
                s["description"] = ("Udwartana (dry flour massage) in place of oil while Ama is high, "
                                    "then a warm shower.")

        # Fasting day
        if is_fasting:
            for s in day_tl:
                if s.get("type") == "meal":
                    s.setdefault("_notes", []).append("Fasting day — follow your fasting protocol. Light fruit, warm water, or herbal tea only.")

        day_tl = _apply_if_window(day_tl, if_window)
        # Condition + gender + age notes
        day_tl = _apply_condition_notes(day_tl, conditions, gender, age, ctx.get("med_classes"))
        for s in day_tl:
            s.pop("_t", None)
            s.pop("_end", None)
            s.pop("morning", None)
            s.pop("evening", None)
            s.pop("ex_slot", None)

        weekly.append({
            "day":            i,
            "day_name":       day_name,
            "is_fasting_day": is_fasting,
            "is_rest_day":    ex_info.get("is_rest", False) and not from_plan,
            "exercise_type":  ex_info.get("ex_type", "") if not from_plan else
                              "+".join(x["ex_type"] for x in planned["morning"] + planned["evening"]),
            "exercise_label": ex_info.get("ex_label", "") if not from_plan else
                              " · ".join(x["ex_label"] for x in planned["morning"] + planned["evening"]),
            "wake_time":      _clock(day_anchors["wake"]),
            "sleep_time":     _clock(day_anchors["bed"]),
            "sleep_notice":   day_anchors["sleep_notice"] if own_day.keys() & {"wake", "sleep"} else None,
            "user_set":       sorted(own_day),
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


def _fasting_withheld(user_profile: dict, prefs: dict, conditions: set, med_classes: set) -> str | None:
    """Why no fasting day or eating window applies, using the diet plan's own rule.

    The routine planned a fruit-only Monday and a 16:8 window for anyone who asked:
    a twelve-year-old, a pregnant woman, a diabetic on insulin."""
    from services.diet_brief_builder import fasting_withheld_reason
    diet = {**(prefs.get("diet") or {}), "fasting_days": ["requested"]}
    reason = fasting_withheld_reason(user_profile, diet)
    if not reason and "insulin_or_sulfonylurea" in med_classes:
        reason = ("Your diabetes medicine lowers blood glucose whether or not you have eaten, "
                  "so fasting days and a shortened eating window are left out. Agree any fast "
                  "with your doctor first.")
    if not reason and _pregnancy_state(user_profile)[1]:
        reason = ("Breastfeeding — fasting days and a shortened eating window are left out. "
                  "Mother and baby both need the energy every day.")
    return reason


# ── Main public function ──────────────────────────────────────────────────────
def generate_routine_plan(user_profile: dict, prefs: dict, diet_foods_db=None,
                           gym_plan_data: dict = None, yoga_plan_data: dict = None) -> dict:
    dosha      = _dosha_key(user_profile.get("dominant_dosha"))
    secondary  = _dosha_key(user_profile.get("secondary_dosha"), "") if user_profile.get("secondary_dosha") else ""
    vikriti    = _dosha_key(user_profile.get("vikriti_dominant"), dosha)
    conditions = list(user_profile.get("medical_history") or [])
    season     = (user_profile.get("current_season") or "").lower()
    if season not in _SEASON_MAP:
        from services.panchakarma_engine import _current_ritu
        season = _current_ritu(user_profile.get("current_season"))
        season = season if season in _SEASON_MAP else "sharad"
    name       = user_profile.get("name", "")
    try:
        age    = int(user_profile.get("age") or 30)
    except (TypeError, ValueError):
        age    = 30
    gender     = (user_profile.get("gender") or "").lower()

    # Routine-specific prefs (Tier C) — fall back to diet prefs for legacy
    rp = prefs.get("routine") or prefs.get("diet") or {}
    if_window   = rp.get("intermittent_fasting", "no") or "no"
    fasting_days = rp.get("fasting_days") or []
    if isinstance(fasting_days, str):
        fasting_days = [d.strip() for d in fasting_days.split(",") if d.strip()]
    occupation  = rp.get("occupation_type") or "moderately_active"

    # Agni: the user's own answer on this form, else the assessed one. The form
    # defaulted to "sama", so every user who left it alone overrode a measured
    # Manda or Tikshna Agni with "balanced" — and the enricher, which read the
    # profile, coached the other one.
    self_report = (rp.get("agni_type_self_report") or "").lower()
    assessed = _AGNI_CANON.get(str(user_profile.get("agni_type") or "").lower().split("+")[0])
    if self_report in ("", "assessed") or (self_report == "sama" and assessed):
        agni_type, agni_source = (assessed or "sama"), ("assessment" if assessed else "default")
    else:
        agni_type, agni_source = self_report, "your answer"

    is_pregnant, is_nursing = _pregnancy_state(user_profile)
    cset = _canonical_conditions(conditions)
    med_classes = medication_classes(user_profile)
    allergens = _declared_allergens(user_profile, prefs)
    herbs = _herb_verdicts(user_profile, age)
    injuries = list(rp.get("injuries") or []) + [str(user_profile.get("injuries_or_limitations") or "")]
    limits = _exercise_limits(cset, is_pregnant, age, injuries, user_profile.get("bmi_category"))
    # Pregnancy is the other reason a meal is not skipped "if not hungry".
    steady_meals = "insulin_or_sulfonylurea" in med_classes or is_pregnant

    fast_reason = _fasting_withheld(user_profile, prefs, cset, med_classes) \
        if (fasting_days or if_window != "no") else None
    requested_fasting = list(fasting_days)
    if fast_reason:
        fasting_days, if_window = [], "no"
    unmatched_fasting = [d for d in fasting_days if d.lower().strip() not in _WEEKDAYS]
    fasting_notice = None
    if fast_reason:
        fasting_notice = fast_reason
    elif unmatched_fasting:
        fasting_notice = (f"{', '.join(unmatched_fasting)} is not a fixed weekday, so it is not "
                          "marked on the week. Treat that day as a fasting day when it falls.")

    custom = clean_custom_times(rp.get("custom_times"))
    by_day = {d: t for d, v in (rp.get("custom_times_by_day") or {}).items()
              if d in _WEEKDAYS and (t := clean_custom_times(v))}
    anchors = _override_anchors(_day_anchors(dosha, season, age, rp.get("wake_preference")),
                                custom, age, dosha)
    agni_notes = _agni_notes(agni_type, not herbs.get("Trikatu Churna"), steady_meals)
    slot_withheld: list = []
    agni_notes = {k: _screen_slot_text(v, conditions, allergens, is_pregnant, slot_withheld)
                  for k, v in agni_notes.items()}
    yoga_time = None
    if yoga_plan_data:
        yoga_time = ((yoga_plan_data.get("user_summary") or {}).get("time_of_day_preference")
                     or rp.get("yoga_time_of_day"))
    ctx = {
        "conditions": cset, "med_classes": med_classes, "allergens": allergens, "herbs": herbs,
        "limits": limits, "anchors": anchors, "agni_notes": agni_notes, "agni_source": agni_source,
        "steady_meals": steady_meals, "exercise_cap": limits["cap"], "yoga_time": yoga_time,
        "gym_time": rp.get("gym_time_of_day"),
        "custom_times": custom, "custom_times_by_day": by_day,
        "custom_items": clean_custom_items(rp.get("custom_items")),
        "ama": user_profile.get("ama_indicator"),
        "high_ama": str(user_profile.get("ama_indicator") or "").lower() in ("high", "severe"),
        "food_conditions": conditions, "is_pregnant": is_pregnant, "slot_withheld": slot_withheld,
    }

    # Tier B: parse gym/yoga schedules
    gym_sched  = _extract_gym_schedule(gym_plan_data or {}) if gym_plan_data else {}
    yoga_sched = _extract_yoga_schedule(yoga_plan_data or {}) if yoga_plan_data else {}

    dinacharya = _build_dinacharya_protocol(dosha, secondary, vikriti, season, conditions,
                                            gender, age, agni_type, is_pregnant,
                                            rp.get("wake_preference"), anchors, herbs, allergens, ctx)
    ctx["withheld_rituals"] = [r["name"] for r in dinacharya["morning_rituals"] if r.get("withheld")]
    note_conditions = conditions + (["pregnancy"] if is_pregnant else [])
    weekly     = _build_weekly_routine(dosha, secondary, season, if_window, note_conditions, gender, age,
                                        agni_type, occupation, fasting_days, gym_sched, yoga_sched,
                                        is_pregnant, rp.get("wake_preference"), ctx)
    meal_times = {s["meal_type"]: s["time"] for s in weekly[0]["timeline"] if s.get("meal_type")}
    seasonal   = _build_seasonal_ritucharya(season, dosha, is_pregnant, age, herbs, conditions,
                                            allergens, limits["cap"],
                                            "Garshana" in ctx["withheld_rituals"]
                                            or _age_band(age) in ("balya", "vriddha")
                                            or bool(cset & {"psoriasis", "eczema", "urticaria", "rosacea"})
                                            or bool(med_classes & {"anticoagulants", "antiplatelets"}))
    meal_guide = _build_meal_guidance(dosha, season, agni_type, agni_notes, conditions, allergens,
                                      is_pregnant, meal_times)
    # What the day's own lines left out is listed with the card's. The list is shown
    # without its meal, so Kapha's "ginger tea" at breakfast and at the snack read as
    # one line twice; and a day line adds nothing when the card already gives that
    # food and that reason ("soaked dates or figs" covers the snack's "Soaked dates").
    listed, items, reasons = [], set(), set()
    for w in meal_guide["withheld"]:
        if (w["item"].lower(), w["reason"]) not in items:
            items.add((w["item"].lower(), w["reason"]))
            reasons.add(w["reason"])
            listed.append(w)
    for w in slot_withheld:
        if w["reason"] not in reasons:
            reasons.add(w["reason"])
            listed.append({"meal": "day", "item": w["item"], "reason": w["reason"]})
    meal_guide["withheld"] = listed
    summary    = _weekly_summary(weekly)

    ab_label = {"balya": "Child (Balya)", "yuva": "Youth / Adult (Yuva)", "madhyama": "Middle Age (Madhyama)", "vriddha": "Senior (Vriddha)"}

    return {
        # The id is the plan_history _id. A time edit rebuilds in milliseconds with no
        # model call, so two edits inside one second collided on a seconds-only id.
        "plan_id":      new_plan_id("routine", user_profile.get('id', 'x')),
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
            "agni_source":    agni_source,
            "occupation_type": occupation,
        },
        "dinacharya_protocol": dinacharya,
        "weekly_routine":      weekly,
        "seasonal_ritucharya": seasonal,
        "meal_guidance":       meal_guide,
        "weekly_summary":      summary,
        "exercise_limits":     limits if (limits["cap"] != "full" or limits["low_impact"]) else None,
        "fasting_notice":      fasting_notice,
        "custom_times":        custom,
        "custom_times_by_day": by_day,
        "custom_items":        ctx["custom_items"],
        "requested_fasting":   requested_fasting if fast_reason else None,
        "enriched":            False,
        "disclaimer": "This Dinacharya plan is for educational wellness guidance. Consult a qualified Vaidya before beginning herbal protocols, especially with pre-existing conditions.",
    }
