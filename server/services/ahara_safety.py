"""
Deterministic Ahara (food) safety layer.

Runs AFTER any LLM meal generation so that food-safety never depends on the
model self-reporting. Two independent checks:

1. Viruddha Ahara (incompatible food combinations) — Charaka Samhita Sutrasthana 26.
   We scan each generated meal's text for classically incompatible pairs that
   co-occur in the SAME meal (or, for time-sensitive rules like curd-at-night,
   in the relevant meal slot).

2. Allergen scan — scans every meal of every week (not just week 1) against the
   user's declared allergies/intolerances and produces unmissable plan-level
   alerts plus per-meal flags.

Both functions are pure and side-effecting on the passed structures; they never
raise — a safety layer must not be able to break plan generation.
"""
from __future__ import annotations

import re
from functools import lru_cache

# Words that merely START with a short allergen term but are NOT that allergen.
# Prefix matching alone would flag an egg allergy on "eggplant"/"eggless" or a
# mustard ("rai") allergy on "raita"/"raisin"; these are dropped explicitly.
_ALLERGEN_FALSE_FRIENDS: dict[str, frozenset[str]] = {
    "egg": frozenset({"eggplant", "eggplants", "eggless"}),
    "rai": frozenset({"raita", "raisin", "raisins"}),
}


@lru_cache(maxsize=512)
def _term_regex(term: str) -> "re.Pattern":
    # Left word-boundary, suffix allowed: "milk" matches "milk" AND "milkshake"
    # (a real dairy compound — missing it would be an unsafe false negative), while
    # "til" still won't match "lentil" (no boundary before "til" there). Residual
    # collisions are removed via _ALLERGEN_FALSE_FRIENDS so safe foods aren't flagged.
    return re.compile(rf"\b{re.escape(term)}\w*")


def _term_in_text(term: str, text: str) -> bool:
    friends = _ALLERGEN_FALSE_FRIENDS.get(term, frozenset())
    return any(m.group(0) not in friends for m in _term_regex(term).finditer(text))

# ── Allergen term lookup ──────────────────────────────────────────────────────
# Maps a declared allergy key → the ingredient/dish terms that imply it.
ALLERGEN_TERMS: dict[str, list[str]] = {
    "gluten": ["wheat", "gluten", "maida", "atta", "bread", "roti", "chapati", "poha",
               "semolina", "suji", "rava", "barley", "oats", "seitan", "naan", "paratha",
               "dalia", "vermicelli", "pasta", "couscous"],
    "dairy": ["milk", "curd", "yogurt", "yoghurt", "ghee", "butter", "cream", "paneer",
              "cheese", "lassi", "buttermilk", "kheer", "raita", "mawa", "khoa", "dahi"],
    "nuts_tree": ["almond", "cashew", "walnut", "pistachio", "pine nut", "hazelnut",
                  "chestnut", "badam", "kaju", "akhrot", "pista"],
    "peanuts": ["peanut", "groundnut", "mungphali", "moongphali"],
    "soy": ["soy", "tofu", "tempeh", "edamame", "soybean", "soya"],
    "eggs": ["egg", "omelet", "omelette", "anda", "bhurji"],
    "shellfish": ["shrimp", "prawn", "crab", "lobster", "scallop", "squid"],
    "fish": ["fish", "salmon", "tuna", "mackerel", "pomfret", "rohu", "hilsa",
             "sardine", "surmai", "bangda"],
    "sesame": ["sesame", "til", "tahini", "gingelly"],
    "mustard": ["mustard", "sarson", "rai"],

    # ── Intolerances ──────────────────────────────────────────────────────────
    # `DietPreferences.food_intolerances` declares exactly four values —
    # lactose / fructose / histamine / fodmap — and not one of them had an entry
    # here. `flag_allergens` and `apply_ahara_safety` both resolve an unknown key
    # with `ALLERGEN_TERMS.get(key, [key])`, so each fell back to searching meal
    # text for its own literal name: a lactose-intolerant patient was scanned for
    # the word "lactose", which no meal has ever contained. All four were declared,
    # sent to the LLM as a hard constraint, and enforced by nothing — measured on a
    # day of Paneer Paratha, Mango Lassi and Kheer, which returned
    # `allergen_safe: True`.
    #
    # AUTHORED, NOT CLINICALLY REVIEWED. These lists are a food-safety floor, not a
    # diagnosis, and they flag rather than remove — the same contract the allergy
    # terms above keep.
    "lactose": ["milk", "curd", "yogurt", "yoghurt", "cream", "paneer", "cheese",
                "lassi", "buttermilk", "kheer", "raita", "mawa", "khoa", "dahi",
                "payasam", "ice cream", "condensed milk"],
    # Ghee is deliberately absent: clarified butter is all but lactose-free, and
    # Ayurveda treats it as a distinct dravya from dugdha. Listing it would flag the
    # one dairy the classical texts prescribe most and train the user to ignore the
    # warning.
    "fructose": ["honey", "high fructose", "corn syrup", "agave", "mango", "apple",
                 "pear", "watermelon", "cherries", "dates", "raisin", "fig", "anjeer",
                 "jaggery", "fruit juice", "sugar"],
    "histamine": ["fermented", "idli", "dosa", "dhokla", "pickle", "achar", "vinegar",
                  "aged cheese", "cheese", "curd", "yogurt", "dahi", "kombucha",
                  "soy sauce", "leftover", "tomato", "spinach", "brinjal", "eggplant"],
    "fodmap": ["wheat", "atta", "roti", "chapati", "onion", "garlic", "rajma",
               "chole", "chickpea", "kidney bean", "cabbage", "cauliflower", "milk",
               "curd", "apple", "pear", "mango", "watermelon", "honey", "cashew",
               "pistachio"],
}

# ── Viruddha Ahara rules ──────────────────────────────────────────────────────
# Each rule fires when a term from EVERY group appears in the same meal text.
# `slots` (optional) restricts the rule to specific meal slots (e.g. curd at night).
_MILK = ["milk", "dudh", "kheer", "payasam", "badam milk", "golden milk", "haldi doodh"]
_SOUR = ["lemon", "lime", "citrus", "orange", "tamarind", "imli", "amla", "vinegar",
         "tomato", "pineapple", "kokum", "sour"]
_FISH_MEAT = ["fish", "chicken", "mutton", "egg", "prawn", "meat", "salmon", "rohu",
              "fish curry", "seafood"]
_CURD = ["curd", "yogurt", "yoghurt", "dahi", "raita"]
_HOT_BEVERAGE = ["hot water", "hot tea", "hot milk", "warm tea", "boiling", "hot chai"]

VIRUDDHA_RULES: list[dict] = [
    {
        "id": "milk_sour",
        "groups": [_MILK, _SOUR],
        "warning": "Milk with sour/acidic foods (citrus, tamarind, tomato, pineapple)",
        "reason": "Virya-Viruddha — opposing potencies curdle milk and produce Ama (Charaka Sutrasthana 26).",
    },
    {
        "id": "milk_fish_meat",
        "groups": [_MILK, _FISH_MEAT],
        "warning": "Milk with fish, meat, or egg",
        "reason": "Classical Viruddha Ahara — leads to Ama and skin disorders (Charaka Sutrasthana 26).",
    },
    {
        # The two Kushtha Viruddha combinations the psoriasis Apathya names and this
        # list did not carry. Charaka Chikitsa 7 gives Viruddha Ahara as a Nidana of
        # Kushtha, and the psoriasis brief hint lists "sesame + milk" and
        # "salt + milk" alongside the fish/meat pairs `milk_fish_meat` already covers.
        "id": "milk_sesame",
        "groups": [_MILK, ["sesame", "til", "tahini", "gingelly", "tilkut"]],
        "warning": "Milk with sesame",
        "reason": "Classical Viruddha Ahara — a stated Nidana of Kushtha (Charaka Chikitsa 7).",
    },
    {
        "id": "milk_salt",
        "groups": [_MILK, ["salted", "namkeen", "papad", "pickle", "rock salt"]],
        "warning": "Milk with salt",
        "reason": "Classical Viruddha Ahara — Rasa-Viruddha; named in the Kushtha Nidana (Charaka Chikitsa 7).",
    },
    {
        "id": "milk_banana",
        "groups": [_MILK, ["banana", "kela", "kadali"]],
        "warning": "Milk with banana",
        "reason": "Abhishyandi — channel-blocking; causes heaviness, congestion, and Ama.",
    },
    {
        "id": "milk_radish",
        "groups": [_MILK, ["radish", "mooli", "mula"]],
        "warning": "Milk with radish",
        "reason": "Virya-Viruddha — opposite potency combination.",
    },
    {
        "id": "honey_ghee_equal",
        "groups": [["honey", "madhu"], ["ghee", "ghrita", "clarified butter"]],
        "warning": "Honey with ghee (especially in equal quantity)",
        "reason": "Viruddha by measure (Samana Matra) — produces Ama (Charaka Sutrasthana 26.86).",
    },
    {
        "id": "honey_hot",
        "groups": [["honey", "madhu"], _HOT_BEVERAGE],
        "warning": "Honey added to hot/heated drinks",
        "reason": "Heated honey becomes Ama-forming and is considered toxic (Charaka Sutrasthana 27).",
    },
    {
        "id": "curd_at_night",
        "groups": [_CURD],
        "slots": ["dinner"],
        "warning": "Curd/yogurt at night",
        "reason": "Promotes Kapha and Ama after sunset; substitute with Takra (buttermilk) if needed.",
    },
]


def _norm(text: str) -> str:
    return (text or "").lower()


def _meal_text(meal) -> str:
    """Flatten a meal into a single lowercase searchable string.

    Handles all three shapes that appear across the diet generators:
      - str  (compact LLM weeks 2-4: "Moong Dal Khichdi")
      - dict (full LLM week 1: meal_name/description/key_ingredients)
      - list of food-item dicts (rule engine four_week_plan: [{name, id, ...}])
    """
    if isinstance(meal, str):
        return _norm(meal)
    if isinstance(meal, dict):
        parts = [
            str(meal.get("meal_name", "")),
            str(meal.get("name", "")),          # rule-engine food items AND drinks use 'name'
            str(meal.get("description", "")),
            # A special drink states its contents in `recipe` ("warm cow's milk with
            # soaked almonds"), which is the only place its ingredients appear — it
            # has no key_ingredients list. `rationale` and `when` are deliberately
            # NOT read: they are explanatory prose, and a note reading "avoids dairy"
            # would flag the very drink that avoids it. Same line `ayurvedic_note`
            # sits on the wrong side of for meals.
            str(meal.get("recipe", "")),
            " ".join(meal.get("key_ingredients", []) or []),
        ]
        return _norm(" ".join(parts))
    if isinstance(meal, list):
        parts = []
        for item in meal:
            if isinstance(item, dict):
                parts.append(str(item.get("name", "")))
                parts.append(" ".join(item.get("key_ingredients", []) or []))
            elif isinstance(item, str):
                parts.append(item)
        return _norm(" ".join(parts))
    return ""


def _group_hit(text: str, group: list[str]) -> bool:
    return any(term in text for term in group)


def scan_meal_for_viruddha(meal, slot: str) -> list[dict]:
    """Return a list of Viruddha-Ahara warnings for a single meal."""
    text = _meal_text(meal)
    if not text:
        return []
    hits: list[dict] = []
    for rule in VIRUDDHA_RULES:
        slots = rule.get("slots")
        if slots and slot not in slots:
            continue
        if all(_group_hit(text, group) for group in rule["groups"]):
            hits.append({
                "combination": rule["warning"],
                "reason": rule["reason"],
                "meal_slot": slot,
            })
    return hits


_MEAL_SLOTS = ("breakfast", "lunch", "snack", "dinner")

# The daily drink is a fifth consumed item and was in none of the three scans.
# `SYSTEM_PROMPT` rule 9 in `diet_llm_generator` makes it mandatory — "Include a
# special Ayurvedic drink ... for each day" — so it appears on every day of every
# LLM plan, `DietView` renders its name, timing, recipe and rationale, and until now
# `_collect_meal_units` returned only the four meal slots.
#
# The measured consequence: a patient declaring dairy AND tree-nut allergies could be
# prescribed "Badam Milk with Saffron — warm cow's milk with soaked almonds" at
# bedtime for 28 days, on a plan reporting `allergen_safe: True` with zero alerts.
# Milk plus a sour Kashaya is Viruddha Ahara by the same silence.
#
# It is a slot rather than a special case so that all three scans — allergen,
# Viruddha and condition-Apathya — pick it up from the one collector they share.
_DRINK_SLOT = "special_drink"
_CONSUMED_SLOTS = _MEAL_SLOTS + (_DRINK_SLOT,)


def _collect_meal_units(plan: dict) -> list[tuple[str, str, str, object]]:
    """Flatten every meal across ALL diet plan shapes into
    (week_label, day_label, slot, meal) tuples — LLM diet_weeks, LLM weekly_plan,
    and rule-engine four_week_plan. Shared by every deterministic safety check."""
    units: list[tuple[str, str, str, object]] = []

    def _add_daily(week_label, daily):
        if not isinstance(daily, dict):
            return
        for day_label, day_data in daily.items():
            if not isinstance(day_data, dict):
                continue
            for slot in _CONSUMED_SLOTS:
                if day_data.get(slot) is not None:
                    units.append((week_label, str(day_label), slot, day_data.get(slot)))

    # LLM multi-week
    for week in plan.get("diet_weeks", []) or []:
        if isinstance(week, dict):
            _add_daily(f"Week {week.get('week_number', '?')}", week.get("daily_plan", {}) or {})
    # LLM single weekly_plan (only if no diet_weeks)
    if not units and isinstance(plan.get("weekly_plan"), dict):
        _add_daily("Week 1", plan["weekly_plan"])
    # Rule-engine four_week_plan: [{week, days:[{day_name, meals:{slot:[items]}}]}]
    for week in plan.get("four_week_plan", []) or []:
        if not isinstance(week, dict):
            continue
        wk = f"Week {week.get('week', '?')}"
        for day in week.get("days", []) or []:
            if not isinstance(day, dict):
                continue
            meals = day.get("meals", {}) or {}
            day_label = str(day.get("day_name", day.get("day", "?")))
            for slot in _MEAL_SLOTS:
                if meals.get(slot) is not None:
                    units.append((wk, day_label, slot, meals.get(slot)))
    return units


def apply_ahara_safety(plan: dict, allergies: list[str], intolerances: list[str]) -> dict:
    """
    Mutates `plan` in place, adding deterministic Viruddha + allergen safety data.

    Adds:
      plan["viruddha_ahara_detected"]  → list of unique detected combinations (plan level)
      plan["safety_alerts"]            → unmissable list for allergens found in meals
      plan["allergen_safe"]            → bool (False if any allergen meal slipped through)
      per-meal: meal["viruddha_warnings"], meal["allergen_warning"], meal["allergen_terms"]
    """
    try:
        allergen_terms: set[str] = set()
        for a in (allergies or []) + (intolerances or []):
            allergen_terms.update(ALLERGEN_TERMS.get(str(a).lower(), [str(a).lower()]))

        viruddha_seen: dict[str, dict] = {}
        allergen_alerts: list[dict] = []

        units = _collect_meal_units(plan)

        for week_label, day_label, slot, meal in units:
            # Viruddha scan
            v_hits = scan_meal_for_viruddha(meal, slot)
            if v_hits and isinstance(meal, dict):
                meal["viruddha_warnings"] = [h["combination"] for h in v_hits]
            for h in v_hits:
                viruddha_seen.setdefault(h["combination"], h)

            # Allergen scan
            if allergen_terms:
                text = _meal_text(meal)
                found = sorted({t for t in allergen_terms if _term_in_text(t, text)})
                if found:
                    if isinstance(meal, dict):
                        meal["allergen_warning"] = True
                        meal["allergen_terms"] = found
                        meal["requires_substitution"] = True
                    elif isinstance(meal, list):
                        for item in meal:
                            item_text = _meal_text(item)
                            if isinstance(item, dict) and any(_term_in_text(t, item_text) for t in found):
                                item["allergen_warning"] = True
                    allergen_alerts.append({
                        "week": week_label,
                        "day": day_label,
                        "meal_slot": slot,
                        "matched_terms": found,
                        "message": (
                            f"{week_label} {day_label} {slot}: contains "
                            f"{', '.join(found)} which conflicts with a declared "
                            "allergy/intolerance. Substitute before following this meal."
                        ),
                    })

        plan["viruddha_ahara_detected"] = list(viruddha_seen.values())
        plan["safety_alerts"] = allergen_alerts
        plan["allergen_safe"] = (len(allergen_alerts) == 0)
        plan["ahara_safety_checked"] = True
    except Exception:
        # Safety layer must never break generation; mark unchecked and move on.
        plan["ahara_safety_checked"] = False
    return plan


# ── Condition-contraindicated food scan (Apathya) ─────────────────────────────
# On the LLM-primary path the model is *asked* to honour each condition's Apathya,
# but nothing deterministic enforced it — a high-GI food could slip into a
# diabetic's plan, or a high-potassium food into a CKD plan, with no catch. This
# gives the primary path the same food-safety floor the rule engine has, by
# scanning every generated meal for concrete foods classically forbidden for the
# user's conditions. High-signal, low-false-positive terms only; we FLAG (not
# delete) so a spurious match is a harmless warning, never a broken plan.
_CONDITION_APATHYA_TERMS: dict[str, dict] = {
    # ── Floors for the twenty-one conditions that had none ──────────────────────
    # Each mirrors an entry added to `PATHYA_APATHYA_HINTS`; the guard test
    # `test_every_brief_curated_condition_has_a_safety_floor` requires both.
    #
    # Only concrete, matchable food words belong here. The Apathya prose beside these
    # includes behaviours — "sleeping during the day", "holding the urge to urinate",
    # "standing up abruptly after eating" — and deriving terms from that phrasing is
    # how a scan ends up searching meals for `sitting` and `travel`. Terms broad
    # enough to match a prescribed food are left out for the same reason: `salt` is in
    # every meal and `tea` is the form half these conditions' medicines take, so the
    # entries say `extra salt`, `salted`, `black tea` and `strong tea` instead.
    "gout": {
        "name": "Gout (Vatarakta)",
        "reason": "Purine-rich, fermented and sour foods aggravate Rakta and Vata in Vatarakta.",
        "terms": ["red meat", "mutton", "beef", "pork", "liver", "organ meat", "kidney meat",
                  "prawn", "shrimp", "crab", "shellfish", "sardine", "anchovy", "mackerel",
                  "beer", "alcohol", "whisky", "wine", "urad dal", "masha", "curd", "dahi",
                  "pickle", "achar", "extra salt", "salted", "vinegar"],
    },
    "kidney_stones": {
        "name": "Kidney stones (Mutrashmari)",
        "reason": "High-oxalate and high-sodium foods feed stone formation in Mutrashmari.",
        "terms": ["spinach", "palak", "beetroot", "chocolate", "cocoa", "black tea",
                  "strong tea", "extra salt", "salted", "pickle", "papad", "red meat",
                  "organ meat", "rhubarb", "sweet potato", "cashew", "almond",
                  "peanut", "soya"],
    },
    "gallstones": {
        "name": "Gallstones (Pittashmari)",
        "reason": "A high-fat meal contracts the gallbladder; fried and rich foods provoke an attack.",
        "terms": ["deep fried", "deep-fried", "puri", "bhatura", "samosa", "pakora",
                  "butter", "cream", "cheese", "paneer", "egg yolk", "red meat",
                  "mutton", "vanaspati", "margarine", "mayonnaise"],
    },
    "heart_disease": {
        "name": "Heart disease (Hridroga)",
        "reason": "Sodium, saturated fat and alcohol burden the Hridaya and the Rasavaha srotas.",
        "terms": ["extra salt", "salted", "pickle", "achar", "papad", "processed",
                  "canned", "deep fried", "deep-fried", "butter", "cream", "cheese",
                  "vanaspati", "margarine", "red meat", "mutton", "beef", "bacon",
                  "sausage", "alcohol", "whisky", "beer", "wine"],
    },
    "hyperthyroidism": {
        "name": "Hyperthyroidism (Atyagni / Bhasmaka with Galaganda)",
        "reason": ("Stimulants and concentrated iodine drive an already excessive Agni. "
                   "Note this is the mirror of hypothyroidism: the goitrogenic brassicas "
                   "restricted there are Pathya here."),
        "terms": ["coffee", "espresso", "black tea", "strong tea", "energy drink",
                  "cola", "alcohol", "whisky", "beer", "wine", "chilli", "red chilli",
                  "seaweed", "kelp", "nori", "iodised salt"],
    },
    "osteoarthritis": {
        "name": "Osteoarthritis (Sandhigata Vata)",
        "reason": "Cold, dry and fermented foods increase Vata in the Sandhi.",
        "terms": ["curd", "dahi", "yogurt", "cold drink", "soft drink", "soda",
                  "ice cream", "chilled", "refrigerated", "raw salad", "rajma",
                  "kidney bean", "chana", "chickpea", "pickle", "vinegar"],
    },
    "sciatica": {
        "name": "Sciatica (Gridhrasi)",
        "reason": "Cold, dry and Vata-increasing foods aggravate Gridhrasi.",
        "terms": ["curd", "dahi", "yogurt", "cold drink", "soft drink", "soda",
                  "ice cream", "chilled", "refrigerated", "raw salad", "rajma",
                  "kidney bean", "chana", "chickpea", "pickle"],
    },
    "cervical_spondylosis": {
        "name": "Cervical spondylosis (Griva Sandhigata Vata)",
        "reason": "Cold, dry and fermented foods increase Vata in the cervical Sandhi.",
        "terms": ["curd", "dahi", "yogurt", "cold drink", "soft drink", "soda",
                  "ice cream", "chilled", "refrigerated", "raw salad", "pickle"],
    },
    "ankylosing_spondylitis": {
        "name": "Ankylosing spondylitis (Asthi-Majjagata Vata with Ama)",
        "reason": "Ama-forming and Vata-increasing foods drive the Asthi-Majjagata process.",
        "terms": ["curd", "dahi", "yogurt", "cold drink", "ice cream", "chilled",
                  "refrigerated", "fermented", "idli", "dosa", "dhokla", "urad dal",
                  "masha", "rajma", "kidney bean", "deep fried", "deep-fried", "pickle"],
    },
    "fibromyalgia": {
        "name": "Fibromyalgia (Mamsagata Vata with Ama)",
        "reason": "Cold, raw and fermented foods deepen Ama and aggravate Vata in Mamsa dhatu.",
        "terms": ["curd", "dahi", "yogurt", "cold drink", "ice cream", "chilled",
                  "refrigerated", "raw salad", "fermented", "coffee", "black tea",
                  "energy drink"],
    },
    "anxiety": {
        "name": "Anxiety (Chittodvega)",
        "reason": "Stimulants and dry, cold, irregular food aggravate Vata in the Manovaha srotas.",
        "terms": ["coffee", "espresso", "black tea", "strong tea", "energy drink",
                  "cola", "soft drink", "alcohol", "whisky", "beer", "wine",
                  "raw salad", "chilled"],
    },
    "depression": {
        "name": "Depression (Vishada)",
        "reason": "Heavy, cold and stale foods increase Kapha and Tamas in the Manovaha srotas.",
        "terms": ["alcohol", "whisky", "beer", "wine", "leftover", "stale", "reheated",
                  "ice cream", "cold drink", "soft drink", "deep fried", "deep-fried"],
    },
    "epilepsy": {
        "name": "Epilepsy (Apasmara)",
        "reason": "Alcohol, stale and incompatible foods disturb the Manovaha srotas in Apasmara.",
        "terms": ["alcohol", "whisky", "beer", "wine", "leftover", "stale", "reheated",
                  "fermented", "red meat", "mutton", "beef", "pork"],
    },
    "eczema": {
        "name": "Eczema (Vicharchika)",
        "reason": "Sour, salty and Viruddha foods provoke Kushtha; milk with fish is the classical pair.",
        "terms": ["curd", "dahi", "yogurt", "pickle", "achar", "vinegar", "tamarind",
                  "imli", "extra salt", "salted", "fish", "prawn", "shrimp", "brinjal",
                  "eggplant", "fermented"],
    },
    "sinusitis": {
        "name": "Sinusitis (Dushta Pratishyaya)",
        "reason": "Cold and Kapha-increasing foods thicken and retain Kapha in the Nasa srotas.",
        "terms": ["curd", "dahi", "yogurt", "banana", "cold drink", "soft drink",
                  "ice cream", "chilled", "refrigerated", "deep fried", "deep-fried",
                  "cheese", "paneer"],
        # The library keeps the ripe and unripe banana apart and only the ripe one is
        # Kapha-increasing; the same exemption the diabetes entry carries applies.
        "exempt": ["raw banana", "kadali kanda", "unripe banana"],
    },
    "common_cold": {
        "name": "Common cold (Pratishyaya)",
        "reason": "Cold and heavy foods increase Kapha and prolong Pratishyaya.",
        "terms": ["curd", "dahi", "yogurt", "banana", "cold drink", "soft drink",
                  "ice cream", "chilled", "refrigerated", "deep fried", "deep-fried",
                  "cheese"],
        "exempt": ["raw banana", "kadali kanda", "unripe banana"],
    },
    "recurrent_uti": {
        "name": "Recurrent UTI (Mutrakrichra)",
        "reason": "Pungent, sour and fermented foods aggravate Pitta in the Mutravaha srotas.",
        "terms": ["chilli", "red chilli", "pickle", "achar", "vinegar", "tamarind",
                  "imli", "alcohol", "whisky", "beer", "wine", "coffee", "espresso",
                  "fermented"],
    },
    "glaucoma": {
        "name": "Glaucoma (Adhimantha)",
        "reason": "Sodium, caffeine and alcohol raise intraocular pressure; Pitta-provoking food worsens Adhimantha.",
        "terms": ["extra salt", "salted", "pickle", "papad", "processed", "coffee",
                  "espresso", "black tea", "strong tea", "energy drink", "alcohol",
                  "whisky", "beer", "wine"],
    },
    "vertigo": {
        "name": "Vertigo (Bhrama)",
        "reason": "Sodium, stimulants and very sour foods aggravate Bhrama.",
        "terms": ["extra salt", "salted", "pickle", "papad", "coffee", "espresso",
                  "black tea", "strong tea", "alcohol", "whisky", "beer", "wine",
                  "vinegar", "tamarind", "imli"],
    },
    "low_blood_pressure": {
        "name": "Low blood pressure (Nyuna Rakta Chapa)",
        "reason": ("Alcohol and prolonged fasting lower pressure further. Salt is "
                   "deliberately absent from these terms: restricting it here would be "
                   "the opposite of the advice, and it is the one condition in this "
                   "table where that is true."),
        "terms": ["alcohol", "whisky", "beer", "wine"],
    },
    "long_covid": {
        "name": "Long COVID (post-viral Dhatu Kshaya with residual Ama)",
        "reason": "Heavy, cold and fermented foods deepen residual Ama while Agni is still weak.",
        "terms": ["deep fried", "deep-fried", "puri", "bhatura", "samosa", "pakora",
                  "cold drink", "soft drink", "ice cream", "chilled", "refrigerated",
                  "fermented", "leftover", "stale"],
    },
    "diabetes": {
        "name": "Diabetes (Prameha / Madhumeha)",
        "reason": "High-glycaemic / sweet — Apathya in Prameha.",
        "terms": ["sugar", "jaggery", "white rice", "maida", "refined flour",
                  "gulab jamun", "jalebi", "halwa", "laddu", "barfi", "ice cream",
                  "cold drink", "soft drink", "soda", "mango", "banana", "grapes"],
                  # The library splits these by ripeness and contraindicates only the
                  # ripe form: unripe banana and raw mango are low-glycaemic and raw
                  # banana is authored Pathya in Prameha. A bare "banana" flags the
                  # Kadali Kanda sabzi the same plan was told to serve. Narrowing the
                  # term to "ripe banana" would be worse — a meal that just says
                  # "banana" is usually the ripe one — so the term still fires and the
                  # permitted sibling is exempted by name.
                  "exempt": ["raw banana", "kadali kanda", "unripe banana",
                             "raw mango", "green mango", "kacha aam"],
    },
    "hypertension": {
        "name": "Hypertension (Uchcha Rakta Chapa)",
        "reason": "High-sodium / heating — raises Rakta Chapa.",
        "terms": ["pickle", "papad", "processed", "salted", "extra salt",
                  "red meat", "alcohol", "canned"],
    },
    "pcos": {
        "name": "PCOS (Artava Dushti)",
        "reason": "Refined carbs worsen insulin resistance.",
        "terms": ["sugar", "white rice", "maida", "refined flour", "jalebi", "cold drink"],
    },
    "hypothyroid": {
        "name": "Hypothyroidism (Galaganda)",
        "reason": "Goitrogenic raw crucifers / soy — Apathya in Galaganda.",
        "terms": ["raw cabbage", "coleslaw", "raw broccoli", "raw cauliflower",
                  "raw kale", "soy milk", "tofu", "soybean"],
    },
    "thyroid": {
        "name": "Thyroid (Galaganda)",
        "reason": "Goitrogenic raw crucifers / soy.",
        "terms": ["raw cabbage", "coleslaw", "raw broccoli", "raw cauliflower", "tofu", "soy milk"],
    },
    "kidney_disease": {
        "name": "Kidney disease (Vrikka Roga)",
        "reason": "High potassium/phosphorus — restrict in renal disease.",
        "terms": ["banana", "tomato", "potato", "avocado", "orange", "coconut water", "dry fruits"],
    },
    "fatty_liver": {
        "name": "Fatty liver (Yakrit Roga)",
        "reason": "Fried / alcohol / refined sugar burden the liver.",
        "terms": ["fried", "deep fried", "alcohol", "vanaspati", "sugar", "processed"],
    },
    "high_cholesterol": {
        "name": "High cholesterol (Medoroga)",
        "reason": "Fatty / fried / refined foods increase Meda-Rasa Dushti.",
        "terms": ["fried", "deep fried", "vanaspati", "dalda", "red meat",
                  "cheese", "butter", "cream", "sugar", "processed"],
    },
    "obesity": {
        "name": "Obesity (Sthaulya)",
        "reason": "Kapha-Meda increasing — reduce in Sthaulya.",
        "terms": ["fried", "deep fried", "sugar", "sweets", "cream", "cheese", "butter"],
    },
    "acidity": {
        "name": "Acidity / GERD (Amlapitta)",
        "reason": "Sour / pungent / fried aggravate Amlapitta.",
        "terms": ["deep fried", "pickle", "vinegar", "coffee", "tamarind", "extra chilli"],
    },
    "ibs": {
        "name": "IBS (Grahani)",
        "reason": "Heavy / gas-forming — aggravate Grahani.",
        "terms": ["deep fried", "rajma", "chole", "raw salad", "cabbage"],
    },
    # ── The eight that fell between the two tables ────────────────────────────
    # `PATHYA_APATHYA_HINTS` in diet_brief_builder curates 21 conditions and sends
    # each one's classical Pathya-Apathya to the model. This table curated 12. The
    # two were maintained separately, and `uncurated_conditions()` skips the LLM
    # Apathya classifier for anything the brief has a hint for — so a condition with
    # a brief hint and no entry here got the curated floor from neither table and the
    # classifier from neither path. It fell through the intersection, which is a hole
    # neither table's author could see by reading their own table.
    #
    # Verified before the fix: an Amavata patient served curd, pickle, deep-fried
    # pakora and rajma returned `condition_food_safe: True`. Curd is the textbook
    # Apathya of Amavata — Madhava Nidana 25 names it first.
    #
    # These are NOT auto-derived from the brief's phrases. `_food_headword` exists and
    # extracts one word per phrase, which is right for the conflict detector it was
    # built for and wrong here: "new rice" yields `rice`, which flags every khichdi,
    # and "black gram" yields `black`, which flags black pepper and black salt. It
    # also yields `sitting`, `suppression`, `travel` and `skipping` from the
    # behavioural Apathya entries. Deriving would have traded a coverage hole for a
    # false-positive flood, and a floor that flags everything is a floor nobody reads.
    #
    # So each is authored from the same classical Apathya the brief already states,
    # made specific enough to scan. AUTHORED, NOT CLINICALLY REVIEWED.
    "amavata": {
        "name": "Amavata (rheumatoid arthritis)",
        "reason": "Ama-forming and Srotas-blocking; curd is the first Apathya named.",
        "terms": ["curd", "dahi", "yogurt", "lassi", "raita", "black gram", "urad",
                  "fish", "fermented", "idli", "dosa", "deep fried", "ice cream",
                  "cold drink"],
        # "new rice" is deliberately not a term. The Apathya is new rice specifically,
        # and no scan can tell new rice from old in a meal name — `rice` would flag
        # every khichdi in the plan, including the ones prescribed for this patient.
    },
    "arsha": {
        "name": "Arsha (haemorrhoids)",
        "reason": "Pungent, fried and flatulent foods aggravate Arsha.",
        "terms": ["deep fried", "extra chilli", "pickle", "rajma", "chole", "urad",
                  "alcohol"],
    },
    "anemia": {
        "name": "Pandu Roga (anaemia)",
        "reason": "Sour, alkaline and Viruddha foods obstruct Rasa-Rakta formation.",
        "terms": ["clay", "alcohol", "raw salad", "cold drink"],
        # Curd-with-milk, the other classical Apathya here, is a combination rather
        # than an ingredient and is already caught by the `milk_sour` Viruddha rule.
    },
    "asthma": {
        "name": "Tamaka Shwasa (asthma)",
        "reason": "Cold, heavy and Kapha-increasing foods provoke Shwasa.",
        "terms": ["curd", "dahi", "banana", "ice cream", "cold drink", "deep fried",
                  "fish"],
        # Only the ripe banana is Kapha-increasing and authored Apathya here; the
        # unripe one is a vegetable. See the diabetes entry for why the term stays
        # broad and the sibling is exempted instead.
        "exempt": ["raw banana", "kadali kanda", "unripe banana"],
    },
    # Adhmana — the fourth `gut_health_issue` value, and the only one that was not
    # already a canonical condition. Its Samprapti is Vata obstructed by Ama in the
    # Pakvashaya, so the floor is the Vatala and gas-forming foods; it is not IBS's
    # sour-and-raw floor and not constipation's dry-and-cold one.
    #
    # `chana` and `rajma` are named rather than a blanket `legume`: moong is Pathya
    # here and a term broad enough to catch it would withhold the one pulse this
    # condition is meant to be fed. `soda` and `carbonated` are the same food by two
    # names, which is how meals actually spell it.
    "bloating": {
        "name": "Adhmana / Anaha (bloating, distension)",
        "reason": "Vatala and gas-forming foods distend the Pakvashaya where Vata is already obstructed by Ama.",
        "terms": ["raw salad", "cabbage", "cauliflower", "broccoli", "rajma",
                  "kidney beans", "chana", "carbonated", "soda", "cold water",
                  "curd"],
    },
    "constipation": {
        "name": "Vibandha (constipation)",
        "reason": "Dry, rough and cold foods harden the stool and increase Vata.",
        # Thin on purpose. Most of this condition's classical Apathya is behavioural —
        # suppressing the urge, excess travel, exertion — and belongs in the brief's
        # advice rather than in a scan of what is on the plate.
        "terms": ["raw salad", "cold drink"],
    },
    "migraine": {
        "name": "Ardhavabhedaka (migraine)",
        "reason": "Aged, fermented and sour foods are the classical and modern triggers.",
        "terms": ["aged cheese", "cheese", "chocolate", "red wine", "alcohol",
                  "pickle", "vinegar"],
    },
    "psoriasis": {
        "name": "Kitibha Kushtha (psoriasis)",
        "reason": "Viruddha Ahara is the stated Nidana of Kushtha; sour aggravates Rakta.",
        "terms": ["fish", "sour", "pickle", "vinegar", "curd"],
        # The rest of this condition's Apathya is combinations — fish+milk, meat+milk,
        # sesame+milk, salt+milk. Those are Viruddha rules, not single terms; the
        # first two already exist as `milk_fish_meat` and the other two are added
        # below.
    },
    # Pregnancy is not a `medical_history` entry — it arrives as the separate
    # `pregnancy_or_nursing` flag on the profile, so it reached this table through no
    # route at all. `build_brief` does list the abortifacient risks to the model as a
    # hard constraint ("absolutely avoid: papaya (raw/ripe), pineapple, excess
    # fenugreek seeds, excess aloe vera ...") — and nothing checked the answer, which
    # is the one thing this module exists to stop. Of the four gaps found together
    # this is the one whose failure is not an allergy but a pregnancy loss.
    #
    # AUTHORED, NOT CLINICALLY REVIEWED. Terms are kept specific enough to stay
    # believable: a floor that flags every meal teaches the user to scroll past it.
    "pregnancy": {
        "name": "Pregnancy / nursing (Garbhini)",
        "reason": (
            "Garbhini Paricharya bars uterine stimulants and sharp purgatives; "
            "raw papaya (papain) and aloe (anthraquinone) are the classical examples."
        ),
        "terms": ["papaya", "pineapple", "aloe vera", "fenugreek", "methi seeds",
                  "unpasteurised", "unpasteurized", "raw milk", "alcohol", "wine",
                  "liver", "ajwain water"],
    },
}

# Normalise common variants to the keys above (mirrors diet COND_ALIASES so this
# module stays self-contained and can't circular-import).
_COND_CANON: dict[str, str] = {
    # The one canonical-condition table for the diet feature.
    #
    # There were two. This one resolved the scan's conditions and `COND_ALIASES` in
    # `diet_brief_builder` resolved the brief's, and they disagreed on 22 inputs. The
    # disagreements were not harmless: `uncurated_conditions()` sends a condition to
    # the LLM Apathya classifier only when the BRIEF has no hint for it, so an input
    # the brief canonicalised and the scan did not got the curated floor from neither
    # table and the classifier from neither path. "piles", "hemorrhoids",
    # "iron_deficiency", "ulcerative_colitis", "crohns", "ibd", "rheumatoid",
    # "skin_disease" and "thyroidism" all sat in that hole — the same shape as the
    # eight conditions PR #62 found between these two tables, reopened by a second
    # alias map nobody thought of as one.
    #
    # Chains are resolved here rather than by double-passing at the call site, so one
    # lookup is always enough and an alias-of-an-alias cannot behave differently
    # depending on which caller resolved it.
    "acid_reflux": "acidity",
    "amlapitta": "acidity",
    "gerd": "acidity",
    "heartburn": "acidity",
    "amavata_roga": "amavata",
    "ra": "amavata",
    "rheumatoid": "amavata",
    "rheumatoid_arthritis": "amavata",
    "iron_deficiency": "anemia",
    "iron_deficiency_anemia": "anemia",
    "haemorrhoids": "arsha",
    "hemorrhoids": "arsha",
    "piles": "arsha",
    "constipation_chronic": "constipation",
    "diabetes_type1": "diabetes",
    "diabetes_type2": "diabetes",
    "insulin_resistance": "diabetes",
    "madhumeha": "diabetes",
    "prameha": "diabetes",
    "prediabetes": "diabetes",
    "sugar": "diabetes",
    "type2_diabetes": "diabetes",
    "type_2_diabetes": "diabetes",
    "liver_disease": "fatty_liver",
    "nafld": "fatty_liver",
    "cholesterol": "high_cholesterol",
    "dyslipidemia": "high_cholesterol",
    "high_lipids": "high_cholesterol",
    "hyperlipidemia": "high_cholesterol",
    "bp": "hypertension",
    "high_blood_pressure": "hypertension",
    "high_bp": "hypertension",
    "hashimoto": "hypothyroid",
    "hypothyroidism": "hypothyroid",
    "crohns": "ibs",
    "grahani": "ibs",
    "ibd": "ibs",
    "ibd_crohns": "ibs",
    "irritable_bowel_syndrome": "ibs",
    "ulcerative_colitis": "ibs",
    "chronic_kidney_disease": "kidney_disease",
    "ckd": "kidney_disease",
    "kidney_failure": "kidney_disease",
    "obese": "obesity",
    "overweight": "obesity",
    "weight_management": "obesity",
    "polycystic_ovarian_syndrome": "pcos",
    "polycystic_ovary": "pcos",
    "skin_disease": "psoriasis",
    "thyroid_disorder": "thyroid",
    "thyroidism": "thyroid",
    # Found by probing free-text phrasings a user actually types.
    "gouty_arthritis": "gout",
    "uric_acid": "gout",
    "high_uric_acid": "gout",
    "renal_stone": "kidney_stones",
    "renal_calculi": "kidney_stones",
    "gall_stone": "gallstones",
    "gall_bladder_stone": "gallstones",
    "spondylitis": "cervical_spondylosis",
    "slip_disc": "sciatica",
    "acidity_gas": "acidity",
    "gas_trouble": "bloating",
    "gastritis": "acidity",
    "piles_bleeding": "arsha",
    "fissure": "arsha",
    "sugar_disease": "diabetes",
    "bp_high": "hypertension",
    "bp_low": "low_blood_pressure",
    "cholesterol": "high_cholesterol",
    "thyroid_under": "hypothyroid",
    "thyroid_over": "hyperthyroidism",
}


# Qualifiers a person appends to a disease name that carry no diagnostic content.
# Onboarding has a free-text "Not listed? Add here" field, so the app receives
# "crohn's disease", "thyroid problem" and "sugar issue" — and `_COND_CANON` was an
# exact-match table, so `crohns` resolved to IBS and `crohns disease` resolved to
# nothing. The curated floor a user got was decided by how they phrased it.
_COND_QUALIFIERS = (
    "disease", "diseases", "disorder", "disorders", "syndrome", "problem",
    "problems", "condition", "conditions", "issue", "issues", "illness",
    "complaint", "complaints", "trouble",
)


def _canon_condition(cond: str) -> str:
    """The diet path's canonical key for a stored or free-text condition.

    Three sources, tried in order, because each knows something the others do not:

      1. `_COND_CANON` directly — the diet vocabulary, which maps to the keys this
         feature's tables are written in (`arsha`, `acidity`, `amavata`).
      2. `engine.condition_vocab.normalize_condition` — 193 aliases, compact forms
         and depluralization, mapping into ITS key space (`hemorrhoids`,
         `acid_reflux`, `hypothyroidism`), whose output is then run back through
         `_COND_CANON`. The two vocabularies are not interchangeable: it calls
         `arsha` `hemorrhoids` and the diet tables call `hemorrhoids` `arsha`, so
         this composes them rather than replacing one with the other.
      3. The same two again with trailing qualifiers stripped, so "crohn's disease"
         reaches what "crohns" already reached.

    Stripping is a last resort, after both exact lookups have failed, so a real key
    that happens to end in a qualifier — `heart_disease`, `kidney_disease` — is
    matched whole and never shortened to `heart`.
    """
    import re

    raw = str(cond or "")
    # Apostrophes are dropped rather than turned into separators: "crohn's" is
    # "crohns", not "crohn s".
    text = re.sub(r"[''`]", "", raw).strip().lower()
    text = re.sub(r"[^a-z0-9]+", " ", text).strip()
    if not text:
        return ""

    def _direct(t: str) -> str | None:
        key = t.replace(" ", "_")
        return _COND_CANON.get(key) or (key if key in _CONDITION_APATHYA_TERMS else None)

    def _viavocab(t: str) -> str | None:
        try:
            from engine.condition_vocab import normalize_condition
        except Exception:
            return None
        key = normalize_condition(t)
        if not key:
            return None
        return _COND_CANON.get(key) or (key if key in _CONDITION_APATHYA_TERMS else None)

    for candidate in (text, _strip_qualifier(text)):
        if not candidate:
            continue
        # The candidate, then its other number. `kidney stone` and `kidney stones`
        # are the same disease and a user writes either; `_COND_CANON` happened to
        # hold only the plural. Tried last so a real key is never reshaped first.
        for variant in (candidate, *_number_variants(candidate)):
            for lookup in (_direct, _viavocab):
                hit = lookup(variant)
                if hit:
                    return hit
    return text.replace(" ", "_")


def _number_variants(text: str) -> tuple[str, ...]:
    """The singular and plural of the last word, for a table that holds one of them.

    Only the last word, and only where a trailing `s` is plausibly a plural — `ibs`
    and `ss` endings are left alone, the same rule `condition_vocab._singularize`
    applies, for the same reason: `ibs` is not the plural of `ib`.
    """
    words = text.split()
    if not words:
        return ()
    last = words[-1]
    out = []
    if len(last) > 3 and last.endswith("s") and not last.endswith("ss"):
        out.append(" ".join(words[:-1] + [last[:-1]]))
    elif not last.endswith("s"):
        out.append(" ".join(words[:-1] + [last + "s"]))
    return tuple(out)


def _strip_qualifier(text: str) -> str:
    """"crohns disease" -> "crohns"; "heart disease" is left alone by the caller,
    which only reaches here after an exact lookup has already matched it."""
    words = text.split()
    while len(words) > 1 and words[-1] in _COND_QUALIFIERS:
        words = words[:-1]
    out = " ".join(words)
    return out if out != text else ""


# ── LLM Apathya classifier for uncurated / rare conditions ────────────────────
# Gives EVERY condition — including rare ones with no hardcoded entry above — a
# deterministic food-safety floor, by asking the LLM once (per condition) for its
# contraindicated foods, then scanning meals for those exactly like the curated
# conditions. Cached per-condition; validated; fail-safe. Mirrors the dosha
# feature's rare-disease classifier (engine/dosha_analyzer).
_CONDITION_APATHYA_CACHE: dict[str, dict | None] = {}


# Words that describe conduct rather than a food. The classifier is asked for foods
# and returns these anyway, because Apathya in the classical sources is a regimen:
# "day sleep", "suppression of urges", "eating before the previous meal is digested".
# As scan terms they search meal text for `sitting` and `travel` and match nothing, or
# worse, match a dish that happens to contain the word.
_BEHAVIOUR_WORDS = frozenset({
    "sleep", "sleeping", "nap", "daysleep", "sitting", "standing", "walking",
    "travel", "travelling", "traveling", "exertion", "exercise", "suppression",
    "suppressing", "holding", "skipping", "fasting", "overeating", "eating",
    "irregular", "late", "night", "stress", "anger", "bathing", "smoking",
})

# Terms with no food in them. Each of these matches most of the plans this app
# generates: `tea` is the form half of Ayurvedic medicine takes, `water` appears in
# every drink recipe, and `oil` is in every tadka. A term this broad does not warn a
# patient, it trains them to stop reading warnings.
_CONTENTLESS_TERMS = frozenset({
    "water", "food", "foods", "meal", "meals", "drink", "drinks", "beverage",
    "beverages", "liquid", "liquids", "snack", "snacks", "spice", "spices", "herb",
    "herbs", "oil", "oils", "fat", "fats", "tea", "juice", "diet", "nutrition",
    "anything", "everything", "all", "none", "any", "some", "other", "others",
    "hot", "cold", "warm", "heavy", "light", "sour", "sweet", "salty", "bitter",
    "pungent", "astringent", "raw", "fresh", "dry", "stale",
})


# Real foods whose bare name appears in almost every savoury meal, so a scan term
# made of it flags the whole plan. The authored tables say `extra salt` and `salted`
# for exactly this reason, and a term the model invents is held to the same standard.
# Note the asymmetry with `sugar`, which stays: a recipe mentions salt by default and
# sugar only when it is actually there.
_TOO_COMMON_TERMS = frozenset({"salt"})


def _term_is_usable(term: str) -> bool:
    """Whether a classifier-proposed term can be matched against meal text.

    The validator's comment has always said "keep only concrete, matchable food
    words" and the code checked length and nothing else, so `day sleep`, `tea` and
    `heavy` all became scan terms. The authored condition tables have to satisfy these
    same two rules — see `test_no_scan_term_describes_a_behaviour` — and a term the
    model invents is held to them too.
    """
    if not term or len(term) < 3 or len(term) > 30:
        return False
    words = set(re.split(r"[\s/&,+-]+", term))
    if words & _BEHAVIOUR_WORDS:
        return False
    if term in _CONTENTLESS_TERMS or term in _TOO_COMMON_TERMS:
        return False
    # A multi-word term made only of qualifiers ("cold heavy") names no food either.
    if words and words <= _CONTENTLESS_TERMS:
        return False
    return True


def _validate_apathya_classification(raw: dict, cond_label: str) -> dict | None:
    """Coerce an LLM Apathya classification into a safe scan entry, or None."""
    if not isinstance(raw, dict):
        return None
    terms_in = raw.get("apathya_foods") or raw.get("terms") or []
    if not isinstance(terms_in, list):
        return None
    terms = []
    for t in terms_in:
        s = str(t).strip().lower()
        if s and s not in terms and _term_is_usable(s):
            terms.append(s)
    terms = terms[:20]
    if not terms:
        return None
    name = str(raw.get("name") or cond_label).strip()[:80]
    reason = str(raw.get("reason") or "Contraindicated for this condition (AI-inferred).").strip()[:160]
    return {"name": name, "reason": reason, "terms": terms, "ai": True}


async def classify_condition_apathya_llm(conditions: list[str]) -> dict[str, dict]:
    """For conditions NOT in the curated scan map, ask the LLM for their
    contraindicated foods. Returns {canon_condition: scan_entry}. Failures cached
    as None so a genuinely unclassifiable term isn't re-asked. Never raises."""
    if not conditions:
        return {}
    import json
    from ai.llm_client import llm_client
    from core.logger import logger

    out: dict[str, dict] = {}
    todo: list[str] = []
    for c in conditions:
        canon = _canon_condition(c)
        if canon in _CONDITION_APATHYA_TERMS:
            continue  # already has a curated deterministic entry
        if canon in _CONDITION_APATHYA_CACHE:
            cached = _CONDITION_APATHYA_CACHE[canon]
            if cached:
                out[canon] = cached
        else:
            todo.append(c)
    if not todo:
        return out

    label_to_canon = {str(c).replace("_", " ").strip().title(): _canon_condition(c) for c in todo}
    listing = "\n".join(f"- {lbl}" for lbl in label_to_canon)
    system_prompt = (
        "You are an Ayurvedic clinical nutritionist. For each disease, list the concrete "
        "foods that are classically contraindicated (Apathya) — single words or short food "
        "names that would appear on a menu (e.g. 'sugar', 'white rice', 'fried', 'banana', "
        "'red meat', 'alcohol'). Respond with valid JSON only."
    )
    user_prompt = (
        f"List contraindicated foods for each condition:\n{listing}\n\n"
        'Respond as a JSON object keyed by the EXACT condition text, each value:\n'
        '{"name":"<condition + Ayurvedic name>","reason":"<short why>",'
        '"apathya_foods":["food1","food2", ...]}\n'
        "Only concrete food words. No prose outside JSON."
    )
    # 700 tokens was the budget for the whole batch. One condition's name, reason and
    # twenty food names is most of it, so a batch of six truncated mid-object, the
    # JSON failed to parse, and every condition in it came back unscanned — measured
    # on six real rare diseases, which produced zero entries. The budget now scales
    # with the request.
    budget = min(4000, 400 + 320 * len(todo))
    answered = False
    try:
        resp = await llm_client.generate(
            prompt=user_prompt, system_prompt=system_prompt,
            max_tokens=budget, temperature=0.2, json_mode=True,
        )
        parsed = json.loads(resp) if resp else {}
        answered = isinstance(parsed, dict)
    except Exception as exc:
        logger.warning(
            f"LLM Apathya classification failed ({exc}); {len(todo)} conditions "
            "unscanned. Not cached — this will be retried."
        )
        parsed = {}

    parsed_norm = {_norm(str(k)).replace(" ", "").replace("_", ""): v
                   for k, v in (parsed or {}).items()} if isinstance(parsed, dict) else {}
    for lbl, canon in label_to_canon.items():
        key = _norm(lbl).replace(" ", "").replace("_", "")
        entry = _validate_apathya_classification(parsed_norm.get(key), lbl)
        # A negative is cached only when the model actually answered and had nothing
        # usable for this condition. A transport error or a truncated response is not
        # evidence about the disease, and caching it as one turned a single bad
        # request into a permanent "no floor" for every condition in that batch, for
        # the life of the process.
        if answered:
            _CONDITION_APATHYA_CACHE[canon] = entry
        if entry:
            out[canon] = entry
        else:
            logger.info(
                f"no deterministic Apathya floor for {lbl!r} "
                f"({'model returned nothing usable' if answered else 'request failed'})"
            )
    return out


# ── Dietary type ──────────────────────────────────────────────────────────────
# `DietPreferences.dietary_type` is annotated in the schema as "CRITICAL, filters
# entire food selection". On the rule-engine path it does filter — one line, and
# only for `vegan`. On the LLM-primary path that actually serves users it was a
# sentence in the prompt: "Dietary type: vegetarian (STRICTLY honour ...)". Nothing
# read the generated plan back. The field the schema calls critical was enforced by
# asking the model politely, which is the arrangement `apply_ahara_safety` was
# written to end for allergies and never extended to cover.
_DIET_TYPE_FORBIDDEN: dict[str, list[str]] = {
    "vegetarian":     ["chicken", "mutton", "lamb", "beef", "pork", "meat", "fish",
                       "prawn", "shrimp", "crab", "egg", "omelette", "omelet", "keema",
                       "gelatin", "bacon", "ham"],
    "vegan":          ["chicken", "mutton", "lamb", "beef", "pork", "meat", "fish",
                       "prawn", "shrimp", "crab", "egg", "omelette", "omelet", "keema",
                       "gelatin", "bacon", "ham",
                       "milk", "curd", "yogurt", "yoghurt", "ghee", "butter", "cream",
                       "paneer", "cheese", "lassi", "buttermilk", "kheer", "raita",
                       "mawa", "khoa", "dahi", "honey"],
}

# Withdrawn dietary types, and anything else that reaches this scan without having
# passed the schema. The library has no animal-food row, so the app serves only
# vegetarian and vegan plans; an unrecognised type gets the vegetarian floor rather
# than none. It used to be the other way round — `non_vegetarian` mapped to no entry,
# and the `if not forbidden` branch below reported `dietary_type_safe = True` for it.
# That was right when the value was offered and meant "nothing to check". Now an
# unknown value means a stale or malformed preference, and answering "safe, checked"
# to one is the failure this module exists to prevent.
_DIETARY_TYPE_FALLBACK = "vegetarian"


def apply_dietary_type_safety(plan: dict, dietary_type: str | None) -> dict:
    """Flag any meal or drink that contradicts the declared dietary type.

    Adds:
      plan["dietary_type_alerts"] → plan-level list of {week, day, meal_slot, food}
      plan["dietary_type_safe"]   → bool
      per-meal: meal["dietary_type_warnings"]

    Flags rather than removes, like every other scan in this module: deleting the
    dinner from a day leaves the patient with no dinner, and a plan that silently
    drops meals is harder to notice than one that says what is wrong with them.
    """
    try:
        dtype = (dietary_type or _DIETARY_TYPE_FALLBACK).strip().lower()
        if dtype not in _DIET_TYPE_FORBIDDEN:
            dtype = _DIETARY_TYPE_FALLBACK
        forbidden = _DIET_TYPE_FORBIDDEN[dtype]

        alerts: list[dict] = []
        for week_label, day_label, slot, meal in _collect_meal_units(plan):
            text = _meal_text(meal)
            if not text:
                continue
            hits = [t for t in forbidden if _term_in_text(t, text)]
            if not hits:
                continue
            for term in hits:
                alerts.append({
                    "week": week_label, "day": day_label, "meal_slot": slot,
                    "food": term, "dietary_type": dtype,
                    "message": (
                        f"{week_label} {day_label} {slot}: contains '{term}', which is "
                        f"not {dtype.replace('_', ' ')}. Substitute before following this meal."
                    ),
                })
            if isinstance(meal, dict):
                meal["dietary_type_warnings"] = hits
                meal["requires_substitution"] = True

        plan["dietary_type_alerts"] = alerts
        plan["dietary_type_safe"] = (len(alerts) == 0)
        plan["dietary_type_checked"] = True
    except Exception:
        plan["dietary_type_checked"] = False
    return plan


def _active_condition_protocols(
    medical_history: list[str], extra_terms: dict | None = None,
    pregnant: bool = False,
) -> dict[str, dict]:
    """The Apathya protocols in force for this patient, keyed by canonical condition.

    Factored out of `apply_condition_food_safety` so that the meal scan and the
    advisory-prose scan cannot be built from different term sets. A second copy of
    this assembly is exactly how the curated table and the library table came to
    disagree before, and how the drink came to be in none of the three scans.
    """
    from services.diet_condition_foods import condition_food_rules

    extra_terms = extra_terms or {}
    active: dict[str, dict] = {}
    for cond in (medical_history or []):
        canon = _canon_condition(cond)
        proto = _CONDITION_APATHYA_TERMS.get(canon) or extra_terms.get(canon)
        # The authored library's own Apathya for this disease, which until it was
        # wired gated only `diet_plan_engine` — the fallback. Measured against the
        # curated table, 333 of the library's 370 (condition, food) exclusions were
        # unenforced on the LLM-primary path. The curated table is not replaced by
        # it — the two were authored separately and each names foods the other does
        # not, so the floor is their union.
        lib_terms = condition_food_rules(canon)["apathya_terms"]
        if lib_terms:
            if proto:
                proto = {
                    **proto,
                    "terms": sorted(set(proto.get("terms") or ()) | set(lib_terms)),
                }
            else:
                proto = {
                    "name": canon.replace("_", " ").title(),
                    "reason": "Apathya for this condition in the authored food library.",
                    "terms": sorted(lib_terms),
                }
        if proto:
            active[canon] = proto
    # `pregnancy_or_nursing` is a profile flag, not a history entry, so it has to be
    # added here or it reaches the scan by no route.
    if pregnant:
        active["pregnancy"] = _CONDITION_APATHYA_TERMS["pregnancy"]
    return active


def apply_condition_food_safety(
    plan: dict, medical_history: list[str], extra_terms: dict | None = None,
    pregnant: bool = False,
) -> dict:
    """Flag foods classically contraindicated for the user's conditions.

    `extra_terms` (keyed by canonical condition) supplies scan entries for
    conditions with no curated map entry — e.g. rare diseases classified by
    classify_condition_apathya_llm. Marked AI-inferred.

    Adds:
      plan["condition_safety_alerts"] → plan-level list of {condition, food, week, day, slot}
      plan["condition_food_safe"]     → bool (False if any contraindicated food found)
      per-meal: meal["condition_warnings"] = [{condition, food, reason}]
    Non-destructive: flags only, and never raises (safety layer must not break gen).
    """
    try:
        active = _active_condition_protocols(medical_history, extra_terms, pregnant)
        # A condition the app could give no deterministic floor for. Silence here
        # reads as "checked and clear", which is the opposite of what happened: the
        # curated tables do not cover it, the library has no claim about it, and the
        # classifier either failed or returned nothing usable.
        plan["conditions_without_food_floor"] = sorted(
            {str(c) for c in (medical_history or [])
             if _canon_condition(c) not in active}
        )
        # Depth, not just presence. Twenty-one conditions have been judged against
        # every one of the library's 150 foods individually; the other nineteen have
        # a curated term list and nothing more. Both currently produce the same
        # "every meal checked — none found" badge, so a gout patient (27 terms, no
        # per-food claims) reads the same reassurance as an acidity patient (101
        # terms, 95 of them authored food by food) while being materially less
        # protected. Saying which is which is the honest version of that badge.
        from services.diet_condition_foods import condition_food_rules as _rules
        plan["conditions_screened_by_terms_only"] = sorted(
            {str(c) for c in (medical_history or [])
             if _canon_condition(c) in active
             and not _rules(_canon_condition(c))["apathya_terms"]}
        )

        if not active:
            plan["condition_food_safe"] = True
            plan["condition_safety_alerts"] = []
            plan["condition_safety_checked"] = True
            return plan

        alerts: list[dict] = []
        for week_label, day_label, slot, meal in _collect_meal_units(plan):
            text = _meal_text(meal)
            if not text:
                continue
            meal_hits: list[dict] = []
            for canon, proto in active.items():
                _ai = " (AI-inferred)" if proto.get("ai") else ""
                # A term may name a food the library splits by preparation. The
                # permitted sibling is exempted by name rather than by narrowing the
                # term, so an unqualified mention still fires.
                _exempt = any(_term_in_text(e, text) for e in (proto.get("exempt") or ()))
                for term in proto["terms"]:
                    if _exempt and _term_in_text(term, text):
                        continue
                    if _term_in_text(term, text):
                        meal_hits.append({"condition": proto["name"] + _ai, "food": term, "reason": proto["reason"]})
                        alerts.append({
                            "week": week_label, "day": day_label, "meal_slot": slot,
                            "condition": proto["name"] + _ai, "food": term,
                            "message": (
                                f"{week_label} {day_label} {slot}: contains '{term}' — "
                                f"{proto['reason']} Substitute before following this meal."
                            ),
                        })
            if meal_hits and isinstance(meal, dict):
                meal["condition_warnings"] = meal_hits
                meal["requires_substitution"] = True

        plan["condition_safety_alerts"] = alerts
        plan["condition_food_safe"] = (len(alerts) == 0)
        plan["condition_safety_checked"] = True
    except Exception:
        plan["condition_safety_checked"] = False
    return plan


# ── The advisory prose, held to the same floor as the meals ───────────────────
# The three scans above read five consumed slots and nothing else. A diet plan also
# ships six free-text surfaces that *recommend food by name*, and `DietView` renders
# them: `pathya_apathya.pathya` under the heading "Pathya — Recommended", plus
# `hydration_guidance`, `condition_coaching`, `ahar_vidhi`, `seasonal_note` and
# `fasting_guidance`.
#
# Measured on an acidity patient: the word `curd` in a meal raised an alert and set
# `condition_food_safe = False`; the same word in the Pathya card passed untouched,
# alongside "Green tea" and "Lemon water on waking" — three foods the library itself
# authors as Apathya for that disease. It is PR #72's shape from the other side:
# there, prose was embedded for the model and shown to nobody; here it is written by
# the model, shown to the patient, and read by no gate.
#
# Two different remedies, because the surfaces are different:
#
#   * A `pathya` entry is a recommendation by construction — it exists to be
#     followed. A contradicted one is WITHHELD, moved off the card into
#     `withheld_recommendations` with its reason. Leaving it on screen under
#     "Recommended" next to an alert saying the opposite is worse than removing it;
#     this is the lesson of #57 and #70 — say that it was withheld and why.
#
#   * Free prose is mixed: "avoid curd and sour fruit" is correct advice for exactly
#     the patient whose terms would match it. Rewriting a sentence is not something
#     this layer can do safely, so prose is FLAGGED, and only where the food is not
#     already governed by an avoid-word in its own clause. Flagging correct advice
#     is how a safety badge gets trained out of a reader.
_AVOID_MARKERS = (
    "avoid", "avoiding", "avoided", "no ", "not ", "never", "skip", "skipping",
    "limit", "limited", "reduce", "reducing", "minimise", "minimize", "cut out",
    "cut back", "stay away", "steer clear", "refrain", "abstain", "exclude",
    "omit", "restrict", "forbidden", "apathya", "contraindicated", "don't",
    "do not", "without", "instead of", "rather than", "in place of", "replace",
    "substitute", "swap", "less ",
    # Comparatives. A recommendation may name the food it displaces — "lighter than
    # white rice", "unlike maida" — and in "X than Y" the food after `than` is always
    # the one being moved away from.
    "than ", "unlike",
)

# Sentence-ish boundaries. A clause is the unit a negation governs: "take warm water,
# avoid curd" must not clear `warm water`, and must clear `curd`.
_CLAUSE_SPLIT = re.compile(r"[.;:!?\n]|\s+(?:but|however|whereas|while)\s+|,\s*(?=avoid|no |not |never|skip|limit|reduce|instead|rather|without|exclude|omit|restrict)")

_PROSE_FIELDS = (
    "condition_coaching", "hydration_guidance", "fasting_guidance",
    "seasonal_note", "ahar_vidhi", "plan_description",
)


def _governed_by_avoidance(text: str, term: str) -> bool:
    """True when every mention of `term` in `text` sits in a clause that tells the
    reader to avoid it."""
    clauses = [c for c in _CLAUSE_SPLIT.split(text.lower()) if c and c.strip()]
    mentions = [c for c in clauses if _term_in_text(term, c)]
    if not mentions:
        return False
    # The whole clause, not the text before the mention: "curd is best avoided" puts
    # the marker after the food and is still advice to avoid it. Scanning only the
    # prefix made the answer depend on where in the clause the word happened to fall
    # — it cleared "curd is best avoided" (prefix empty, so the whole clause was
    # scanned) and flagged "fresh curd is best avoided" (prefix "fresh ").
    #
    # What stops that clearing a genuine recommendation is the splitter: a comma
    # before an avoid-word is a clause boundary, so "curd is excellent, avoid
    # pickles" is two clauses and the curd one has no marker.
    return all(any(m in clause for m in _AVOID_MARKERS) for clause in mentions)


def apply_advisory_safety(
    plan: dict, medical_history: list[str], allergies: list[str] | None = None,
    intolerances: list[str] | None = None, extra_terms: dict | None = None,
    pregnant: bool = False,
) -> dict:
    """Hold the plan's food-recommending prose to the same floor as its meals.

    Adds:
      plan["withheld_recommendations"] → [{item, source, reason, condition}] removed
                                          from `pathya_apathya.pathya`
      plan["advisory_prose_alerts"]    → [{field, food, condition, message}]
      plan["advisory_safety_checked"]  → bool
    Never raises: a safety layer must not break generation.
    """
    try:
        active = _active_condition_protocols(medical_history, extra_terms, pregnant)
        allergen_terms: dict[str, str] = {}
        for a in list(allergies or []) + list(intolerances or []):
            key = str(a).lower()
            for t in ALLERGEN_TERMS.get(key, [key]):
                allergen_terms[t] = key

        def _hits(text: str, *, negation_aware: bool,
                  allergens_absolute: bool = False) -> list[dict]:
            out: list[dict] = []
            low = str(text or "").lower()
            if not low:
                return out
            for canon, proto in active.items():
                exempt = any(_term_in_text(e, low) for e in (proto.get("exempt") or ()))
                for term in proto["terms"]:
                    if not _term_in_text(term, low):
                        continue
                    if exempt:
                        continue
                    if negation_aware and _governed_by_avoidance(low, term):
                        continue
                    out.append({
                        "food": term,
                        "condition": proto["name"] + (" (AI-inferred)" if proto.get("ai") else ""),
                        "reason": proto["reason"],
                    })
            for term, declared in allergen_terms.items():
                if not _term_in_text(term, low):
                    continue
                # On the Pathya card an allergen is absolute: a declared allergen has
                # no business in a list of things to eat, in any phrasing. The
                # comparative markers are what makes this necessary — "nothing is
                # better than warm milk at bedtime" reads as displacement to the
                # clause rule and cleared for a dairy-allergic patient. Over-
                # withholding one entry costs a line of advice; the other way costs
                # more than that.
                #
                # Prose stays negation-aware, because there "avoid dairy" is the
                # correct sentence to write for exactly this patient and flagging it
                # is noise.
                if negation_aware and not allergens_absolute \
                        and _governed_by_avoidance(low, term):
                    continue
                out.append({
                    "food": term,
                    "condition": f"Declared {declared.replace('_', ' ')} allergy/intolerance",
                    "reason": "The patient declared this; it must not be recommended.",
                })
            return out

        # 1. The Pathya card — withheld, not merely flagged.
        withheld: list[dict] = []
        pa = plan.get("pathya_apathya")
        if isinstance(pa, dict) and isinstance(pa.get("pathya"), list):
            kept = []
            for item in pa["pathya"]:
                # Negation-aware here too. A `pathya` entry is a recommendation, but a
                # recommendation may name the food it *displaces*: a real one read
                # "Quinoa or brown rice congee in small portions — lighter than white
                # rice", and withholding it took correct advice off the card for
                # naming the thing it was steering the patient away from.
                found = _hits(str(item), negation_aware=True, allergens_absolute=True)
                if found:
                    withheld.append({
                        "item": item, "source": "pathya_apathya.pathya",
                        "condition": found[0]["condition"], "food": found[0]["food"],
                        "reason": (
                            f"Withheld: names '{found[0]['food']}', which is Apathya here — "
                            f"{found[0]['reason']}"
                        ),
                    })
                else:
                    kept.append(item)
            pa["pathya"] = kept
        plan["withheld_recommendations"] = withheld

        # 2. The free prose — flagged where it is not already telling them to avoid it.
        alerts: list[dict] = []
        for field in _PROSE_FIELDS:
            value = plan.get(field)
            if not isinstance(value, str):
                continue
            for hit in _hits(value, negation_aware=True):
                alerts.append({
                    "field": field, "food": hit["food"], "condition": hit["condition"],
                    "message": (
                        f"{field.replace('_', ' ')} recommends '{hit['food']}' — "
                        f"{hit['reason']} Do not follow this line without substituting."
                    ),
                })
        plan["advisory_prose_alerts"] = alerts
        plan["advisory_safety_checked"] = True
    except Exception:
        plan["advisory_safety_checked"] = False
    return plan
