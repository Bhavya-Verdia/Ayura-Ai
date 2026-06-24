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

        # Collect a uniform list of (week_label, day_label, slot, meal) across ALL diet
        # structures: LLM diet_weeks, LLM weekly_plan, and rule-engine four_week_plan.
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
                found = sorted({t for t in allergen_terms if t in text})
                if found:
                    if isinstance(meal, dict):
                        meal["allergen_warning"] = True
                        meal["allergen_terms"] = found
                        meal["requires_substitution"] = True
                    elif isinstance(meal, list):
                        for item in meal:
                            if isinstance(item, dict) and any(t in _meal_text(item) for t in found):
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
