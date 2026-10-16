"""Another dish in place of one meal, without rebuilding the plan.

The only ways out of a meal the patient would not eat were to log "ate something
else" or to regenerate the whole plan — a billed generation, four new weeks, and the
meal log no longer matching what was served. A dietitian asked "I don't like this"
offers another dish of the same kind.

The replacement comes from the patient's own plan: the same slot on another day,
a real dish the model wrote for this patient and the scans already passed. It is
held to the food list as it stands TODAY — a food reported in a check-in, or an
allergy added since, rules a dish out — and the whole scan set is run on it again,
as the plan's own repair pass does. It is resized to the replaced meal's energy, so
the day stays where the solver left it, and no portion goes past what one plate
holds. Repeated requests step through the alternatives in turn.

No LLM call, so nothing is billed. The meal it replaced is kept on the new one
(`replaced_from`), and putting it back is one request.
"""
from __future__ import annotations

import copy
import json

from services import diet_nutrition as dn

SLOTS = ("breakfast", "lunch", "snack", "dinner")
_MIN_FACTOR, _MAX_FACTOR = 0.6, 1.6


def _name(meal: dict) -> str:
    return str(meal.get("meal_name") or meal.get("name") or "").strip().lower()


def candidates(plan: dict, week: int, day: str, slot: str) -> list[dict]:
    """The other dishes this plan serves in the same slot, one of each, on days
    of the same kind (a fasting day's Phalahar only replaces a fasting meal)."""
    target_day = next(((w.get("daily_plan") or {}).get(day) for w in plan.get("diet_weeks") or []
                       if w.get("week_number") == week), None) or {}
    current = target_day.get(slot) or {}
    fasting = bool(target_day.get("is_fasting"))
    # Not today's other meals either: the same dish at lunch and dinner is no swap.
    taken = {_name(m) for m in target_day.values() if isinstance(m, dict)}
    taken.add(_name((current.get("replaced_from") or {})))
    seen, out = set(), []
    for w in plan.get("diet_weeks") or []:
        for d, dd in (w.get("daily_plan") or {}).items():
            if not isinstance(dd, dict) or bool(dd.get("is_fasting")) != fasting:
                continue
            m = dd.get(slot)
            if not isinstance(m, dict) or not dn.components_of(m):
                continue
            n = _name(m)
            if not n or n in taken or n in seen:
                continue
            seen.add(n)
            out.append(m)
    return sorted(out, key=_name)


def _resized(meal: dict, kcal: float, cap_scale: float) -> dict:
    new = {k: copy.deepcopy(v) for k, v in meal.items()
           if k not in ("replaced_from", "replace_count", "substituted")}
    comps = dn.components_of(new)
    have = dn.compute(comps)["nutrition"].get("calories") or 0
    if kcal and have:
        comps = dn.scale(comps, max(_MIN_FACTOR, min(_MAX_FACTOR, kcal / have)))
    for c in comps:
        if dn.role(c["food"]) != "seasoning":
            c["grams"] = min(c["grams"], dn.meal_cap(c["food"], cap_scale))
    new["components"] = comps
    return dn.apply_to_meal(new)


def replace_meal(plan: dict, week: int, day: str, slot: str, *, allowed_ids: set,
                 is_safe) -> dict | None:
    """The plan's day with `slot` replaced by the next acceptable dish, or None when
    no other dish in the plan is acceptable. `is_safe(meal)` runs the scans."""
    from services.ahara_safety import scan_meal_for_viruddha
    from services.diet_week_generator import _day_totals

    wk = next((w for w in plan.get("diet_weeks") or [] if w.get("week_number") == week), None)
    dd = ((wk or {}).get("daily_plan") or {}).get(day)
    if not isinstance(dd, dict) or not isinstance(dd.get(slot), dict):
        raise KeyError("no such meal")
    current = dd[slot]
    original = current.get("replaced_from") or current
    kcal = float((current.get("macros_approx") or {}).get("calories") or 0)
    target = ((plan.get("energy_prescription") or {}).get("target_calories")) or 2200
    cap_scale = target / 2200.0

    options = candidates(plan, week, day, slot)
    count = int(current.get("replace_count") or 0)
    for i in range(len(options)):
        pick = options[(count + i) % len(options)]
        if not all(c["food"] in allowed_ids for c in dn.components_of(pick)):
            continue
        new = _resized(pick, kcal, cap_scale)
        if scan_meal_for_viruddha(new, slot) or not is_safe(new):
            continue
        new["replaced_from"] = original
        new["replace_count"] = count + i + 1
        day_out = json.loads(json.dumps(dd))
        day_out[slot] = new
        day_out["day_totals"] = _day_totals(day_out)
        return day_out
    return None


def restore_meal(plan: dict, week: int, day: str, slot: str) -> dict:
    """The day with the meal first written for `slot` put back."""
    from services.diet_week_generator import _day_totals

    wk = next((w for w in plan.get("diet_weeks") or [] if w.get("week_number") == week), None)
    dd = ((wk or {}).get("daily_plan") or {}).get(day)
    if not isinstance(dd, dict) or not isinstance(dd.get(slot), dict):
        raise KeyError("no such meal")
    original = dd[slot].get("replaced_from")
    if not original:
        raise LookupError("this meal has not been replaced")
    day_out = json.loads(json.dumps(dd))
    day_out[slot] = original
    day_out["day_totals"] = _day_totals(day_out)
    return day_out
