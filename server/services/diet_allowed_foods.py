"""The foods a plan may be built from, for this patient.

Every safety scan in `ahara_safety` runs AFTER generation, and what it found was
shipped as a note — "Substitute before following this meal" — on the meal itself.
Measured on sixteen live plans: a vegan was given ghee 34 times, a coeliac gluten
and oats 15 times, a diabetic kidney patient sugar or jaggery 13 times. A note is
not a fix, and most people do not read it.

The plan is now composed from components, so the scans can be run on the
INGREDIENTS before a single meal exists: each candidate food is put through the
same allergen, dietary-type and condition scans as a one-food meal, and a food
that any of them flags is not offered to the model at all. One set of rules, run
in both places — the list and the post-generation check cannot disagree, because
they are the same check.
"""
from __future__ import annotations

from services.diet_nutrition import EXTRAS, SEASONINGS, _library

_SLOTS = ("breakfast", "lunch", "snack", "dinner", "special_drink")
_DAYS_PER_WEEK = 7


def _candidates() -> list[dict]:
    return list(_library().values()) + list(EXTRAS.values())


def screen_foods(foods: list[dict], *, allergies, intolerances, dietary_type,
                 conditions, extra_terms=None, pregnant=False) -> dict[str, str]:
    """{food id: reason} for every food a scan flags for this patient."""
    from services.ahara_safety import (apply_ahara_safety, apply_condition_food_safety,
                                       apply_dietary_type_safety)

    per_week = _DAYS_PER_WEEK * len(_SLOTS)
    weeks, where = [], {}
    for i, f in enumerate(foods):
        w, rest = divmod(i, per_week)
        d, s = divmod(rest, len(_SLOTS))
        while len(weeks) <= w:
            weeks.append({"week_number": len(weeks) + 1, "daily_plan": {}})
        day = weeks[w]["daily_plan"].setdefault(f"D{d}", {})
        day[_SLOTS[s]] = {"meal_name": f.get("name") or f["id"],
                          "key_ingredients": [f["id"].replace("_", " ")]}
        where[(f"Week {w + 1}", f"D{d}", _SLOTS[s])] = f["id"]

    plan = {"diet_weeks": weeks}
    plan = apply_ahara_safety(plan, list(allergies or []), list(intolerances or []))
    plan = apply_dietary_type_safety(plan, dietary_type)
    plan = apply_condition_food_safety(plan, list(conditions or []),
                                       extra_terms=extra_terms or {}, pregnant=pregnant)
    flagged: dict[str, str] = {}
    for key, label in (("safety_alerts", "allergy or intolerance"),
                       ("dietary_type_alerts", "dietary type"),
                       ("condition_safety_alerts", None)):
        for a in plan.get(key) or []:
            fid = where.get((a.get("week"), a.get("day"), a.get("meal_slot")))
            if fid and fid not in flagged:
                flagged[fid] = label or f"Apathya in {a.get('condition', 'a declared condition')}"
    # The extras carry their own allergen tags (groundnut oil for a peanut allergy),
    # which a name scan can miss.
    declared = {str(a).lower() for a in allergies or []}
    for f in foods:
        if f["id"] in EXTRAS and declared & set(f.get("allergens") or []):
            flagged.setdefault(f["id"], "allergy or intolerance")
        if f["id"] in EXTRAS and str(dietary_type or "").lower() == "vegan" and not f.get("vegan"):
            flagged.setdefault(f["id"], "dietary type")
    return flagged


def allowed_foods(user_profile: dict, diet_prefs: dict, extra_terms=None) -> dict:
    """{"allowed": [food rows], "excluded": {id: reason}} for this patient."""
    from services.diet_brief_builder import diet_allergies, diet_conditions

    from services.diet_clinical_notes import preference_protocols, screen_protocols

    foods = _candidates()
    # Medicine-food interactions that are "avoid this food" go through the same scans
    # as a condition's Apathya, keyed as pseudo-conditions.
    meds = {**screen_protocols(user_profile), **preference_protocols(diet_prefs)}
    excluded = screen_foods(
        foods,
        allergies=diet_allergies(user_profile, diet_prefs),
        intolerances=diet_prefs.get("food_intolerances") or [],
        dietary_type=diet_prefs.get("dietary_type"),
        conditions=diet_conditions(user_profile, diet_prefs) + list(meds),
        extra_terms={**(extra_terms or {}), **meds},
        pregnant=bool(user_profile.get("pregnancy_or_nursing")),
    )
    conditions = diet_conditions(user_profile, diet_prefs)
    if _is_renal(conditions):
        for fid in high_potassium_ids(foods):
            excluded.setdefault(fid, "high in potassium (kidney disease)")
    # Foods the patient said caused trouble, in a weekly check-in. By id: the
    # patient picked the food from their own plan, so there is nothing to match.
    for fid in (user_profile.get("diet_log") or {}).get("trouble_foods") or []:
        excluded.setdefault(fid, "you reported trouble after eating it")
    allowed = [f for f in foods if f["id"] not in excluded]
    return {"allowed": allowed, "excluded": excluded}


# Kidney disease: the fruits, vegetables and drinks with 300 mg or more of potassium
# per 100 g are left out — kiwi, banana, guava, dates, potato, yam, arbi, spinach,
# drumstick, coconut water and the like, the foods every Indian renal diet sheet
# names. Measured on the reviewer personas, a CKD patient was served kiwi, which no
# scan caught because no list named it; this reads the composition table instead of
# a list, so a food added later is screened too. It is deliberately not a full
# hyperkalaemia diet: whether that is needed depends on the blood potassium, which
# the app does not have, and KDOQI 2020 advises against restricting without it. The
# seasonings (ginger, garlic) are used in grams and stay.
_RENAL_K_PER_100G = 300
_K_SCREENED_CATEGORIES = {"fruit", "vegetable", "beverage"}
_DRIED_FRUIT = {"dates", "figs", "raisins"}
_EXTRA_VEGETABLES = {"okra_bhindi", "brinjal_baingan", "tinda", "parwal"}
_USED_AS_SEASONING = {"ginger", "garlic"}


def high_potassium_ids(foods: list[dict]) -> set[str]:
    from services.diet_nutrition import micronutrients

    table = micronutrients()
    out = set()
    for f in foods:
        fid = f["id"]
        if fid in SEASONINGS or fid in _USED_AS_SEASONING:
            continue
        if f.get("category") not in _K_SCREENED_CATEGORIES and fid not in _DRIED_FRUIT \
                and fid not in _EXTRA_VEGETABLES:
            continue
        k = (table.get(fid) or {}).get("potassium_mg")
        if k is not None and k >= _RENAL_K_PER_100G:
            out.add(fid)
    return out


def _is_renal(conditions) -> bool:
    from services.diet_energy import _RENAL
    from services.ahara_safety import _canon_condition

    return any((_canon_condition(c) or str(c).lower()) in _RENAL
               or str(c).lower().replace(" ", "_") in _RENAL for c in conditions or [])


def food_list_for_prompt(allowed: list[dict]) -> str:
    """One line per allowed food, grouped, with the per-100 g figures the model needs
    to size a portion and the STATE the grams refer to."""
    groups: dict[str, list[str]] = {}
    for f in sorted(allowed, key=lambda f: (f.get("category", ""), f["id"])):
        per = f.get("nutrition_per_100g") or {}
        state = f.get("prep_state") or ("seasoning" if f["id"] in SEASONINGS else "as named")
        groups.setdefault(f.get("category") or "other", []).append(
            f"  {f['id']} — {f.get('name')} [{state}] {round(per.get('calories') or 0)} kcal, "
            f"{per.get('protein_g', 0)} g protein /100 g")
    return "\n".join(f"{cat.upper()}:\n" + "\n".join(lines) for cat, lines in groups.items())
