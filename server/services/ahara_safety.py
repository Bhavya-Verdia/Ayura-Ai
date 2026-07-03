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
            str(meal.get("name", "")),          # rule-engine food items use 'name'
            str(meal.get("description", "")),
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
            for slot in _MEAL_SLOTS:
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
    "diabetes": {
        "name": "Diabetes (Prameha / Madhumeha)",
        "reason": "High-glycaemic / sweet — Apathya in Prameha.",
        "terms": ["sugar", "jaggery", "white rice", "maida", "refined flour",
                  "gulab jamun", "jalebi", "halwa", "laddu", "barfi", "ice cream",
                  "cold drink", "soft drink", "soda", "mango", "banana", "grapes"],
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
}

# Normalise common variants to the keys above (mirrors diet COND_ALIASES so this
# module stays self-contained and can't circular-import).
_COND_CANON: dict[str, str] = {
    "type2_diabetes": "diabetes", "type_2_diabetes": "diabetes", "diabetes_type2": "diabetes",
    "diabetes_type1": "diabetes", "prediabetes": "diabetes", "insulin_resistance": "diabetes",
    "madhumeha": "diabetes", "prameha": "diabetes", "sugar": "diabetes",
    "bp": "hypertension", "high_blood_pressure": "hypertension", "high_bp": "hypertension",
    "polycystic_ovary": "pcos", "polycystic_ovarian_syndrome": "pcos",
    "hypothyroidism": "hypothyroid", "hashimoto": "hypothyroid", "thyroid_disorder": "thyroid",
    "obese": "obesity", "overweight": "obesity", "weight_management": "obesity",
    "liver_disease": "fatty_liver", "nafld": "fatty_liver",
    "cholesterol": "high_cholesterol", "dyslipidemia": "high_cholesterol",
    "hyperlipidemia": "high_cholesterol", "high_lipids": "high_cholesterol",
    "ckd": "kidney_disease", "kidney_failure": "kidney_disease", "chronic_kidney_disease": "kidney_disease",
    "acid_reflux": "acidity", "gerd": "acidity", "heartburn": "acidity", "amlapitta": "acidity",
    "irritable_bowel_syndrome": "ibs", "grahani": "ibs",
}


def _canon_condition(cond: str) -> str:
    key = str(cond).strip().lower().replace(" ", "_").replace("-", "_")
    return _COND_CANON.get(key, key)


# ── LLM Apathya classifier for uncurated / rare conditions ────────────────────
# Gives EVERY condition — including rare ones with no hardcoded entry above — a
# deterministic food-safety floor, by asking the LLM once (per condition) for its
# contraindicated foods, then scanning meals for those exactly like the curated
# conditions. Cached per-condition; validated; fail-safe. Mirrors the dosha
# feature's rare-disease classifier (engine/dosha_analyzer).
_CONDITION_APATHYA_CACHE: dict[str, dict | None] = {}


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
        # Keep only concrete, matchable food words; drop empties and long phrases.
        if s and len(s) <= 30 and s not in terms:
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
    try:
        resp = await llm_client.generate(
            prompt=user_prompt, system_prompt=system_prompt,
            max_tokens=700, temperature=0.2, json_mode=True,
        )
        parsed = json.loads(resp) if resp else {}
    except Exception as exc:
        logger.warning(f"LLM Apathya classification failed ({exc}); {len(todo)} conditions unscanned.")
        parsed = {}

    parsed_norm = {_norm(str(k)).replace(" ", "").replace("_", ""): v
                   for k, v in (parsed or {}).items()} if isinstance(parsed, dict) else {}
    for lbl, canon in label_to_canon.items():
        key = _norm(lbl).replace(" ", "").replace("_", "")
        entry = _validate_apathya_classification(parsed_norm.get(key), lbl)
        _CONDITION_APATHYA_CACHE[canon] = entry  # cache hit OR miss (None)
        if entry:
            out[canon] = entry
    return out


def apply_condition_food_safety(
    plan: dict, medical_history: list[str], extra_terms: dict | None = None,
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
        extra_terms = extra_terms or {}
        active: dict[str, dict] = {}
        for cond in (medical_history or []):
            canon = _canon_condition(cond)
            proto = _CONDITION_APATHYA_TERMS.get(canon) or extra_terms.get(canon)
            if proto:
                active[canon] = proto
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
                for term in proto["terms"]:
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
