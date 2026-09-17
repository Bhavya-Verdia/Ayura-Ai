"""
Reconcile a generated diet week against the patient's energy prescription.

The brief now states a daily total and a per-meal budget, which is prevention. This
module is the backstop, because a stated target and a delivered plan were never
compared: two live generations came back at 585-720 kcal against a stated 1200, and
1240-1410 against a stated 2400 — the second for an *underweight* patient whose whole
goal was to gain. The shortfall was invisible because `DietView` sums the model's own
`macros_approx` and displays that sum; nothing anywhere held the target beside it.

The correction is portion scaling rather than regeneration: the meals a Vaidya-grade
prompt produced are good, and their Ayurvedic reasoning — Rasa, Guna, Virya, Vipaka,
the condition logic, the Viruddha checks — stays true when a katori becomes one and a
half. Regenerating would cost a second LLM call per plan and could miss again.

Three properties this has to hold, each learned from a way the naive version is wrong:

* **Scale per slot, not per day.** A uniform day factor stretches a snack that was
  already correctly sized. Each meal is scaled toward its own budget, so a 280 kcal
  lunch against a 522 kcal budget moves and a 149 kcal snack does not.
* **Scale the portion text, not only the numbers behind it.** `macros_approx` is what
  the macro bar sums, but `portion` is what the patient cooks. Raising one without the
  other produces a plan that lies to the person following it, which is worse than the
  shortfall it fixes.
* **Bound the factor and admit the residual.** A day at 40% of target cannot be fixed
  by multiplying rice; past roughly double, portions stop being plausible meals.
  `MAX_FACTOR` caps it and anything still short is reported in
  `plan["energy_reconciliation"]` rather than quietly rounded away.
"""
import re

_SLOTS = ("breakfast", "lunch", "snack", "dinner")
_MACRO_KEYS = ("calories", "protein_g", "carbs_g", "fat_g")

# Beyond this a scaled portion stops describing a meal anyone would serve.
MAX_FACTOR = 2.0
# Below this the meal was over-sized; shrinking is allowed but bounded too.
MIN_FACTOR = 0.5
# Leave a meal alone if it is already this close to its budget. Scaling a meal by 1.04
# only adds noise to the portion text.
_DEADBAND = 0.10

# Units a quantity can carry in a portion string, and the increment each rounds to.
# A katori is not measured to two decimal places and grams are not measured to one.
_UNIT_STEPS: list[tuple[str, float, float]] = [
    # (regex alternation of unit spellings, rounding step, minimum value)
    (r"ml|millilitres?|milliliters?", 25, 25),
    (r"g|gm|gms|gram|grams", 5, 5),
    (r"kg", 0.1, 0.1),
    (r"tsp|teaspoons?", 0.5, 0.5),
    (r"tbsp|tablespoons?", 0.5, 0.5),
    (r"katori|katoris|bowls?|cups?|glass|glasses|ladles?|servings?", 0.5, 0.5),
    (r"pieces?|pcs?|nos?|idlis?|rotis?|chapatis?|phulkas?|dosas?|chillas?|"
     r"parathas?|slices?|dates?|almonds?|walnuts?|halves?", 1, 1),
]

_NUMBER = r"(\d+(?:\.\d+)?(?:\s*[-–]\s*\d+(?:\.\d+)?)?|\d+\s*/\s*\d+|½|¼|¾)"
# "3 medium idlis" and "2 heaped tbsp" are quantities too; the adjective sits between
# the number and the unit and is carried through the substitution unchanged.
_SIZE_WORD = r"(?:\s+(?:small|medium|large|big|heaped|heaping|level|flat|generous))?"

_VULGAR = {"½": 0.5, "¼": 0.25, "¾": 0.75}


def _parse_number(raw: str) -> float | None:
    """Read the leading value of a quantity token: '1.5', '2-3', '1/2', '½'."""
    raw = raw.strip()
    if raw in _VULGAR:
        return _VULGAR[raw]
    if "/" in raw:
        try:
            num, den = raw.split("/")
            return float(num.strip()) / float(den.strip())
        except (ValueError, ZeroDivisionError):
            return None
    # A range is represented by its midpoint so that scaling keeps it a range.
    parts = re.split(r"\s*[-–]\s*", raw)
    try:
        values = [float(p) for p in parts]
    except ValueError:
        return None
    return sum(values) / len(values)


def _format_number(value: float, step: float) -> str:
    """Round to the unit's own increment and drop a pointless trailing zero."""
    if step <= 0:
        step = 1
    rounded = round(value / step) * step
    if abs(rounded - round(rounded)) < 1e-9:
        return str(int(round(rounded)))
    return f"{rounded:.2f}".rstrip("0").rstrip(".")


def scale_portion_text(text: str, factor: float) -> str:
    """Scale every quantity in a portion string, leaving the rest of the words alone.

    Only a number immediately followed by a known unit is touched, so '1 katori
    (250 ml) with 1 tsp ghee' scales in all three places while 'cooked for 10 minutes'
    and 'Grade A' are left exactly as written. An unrecognised portion string comes
    back unchanged rather than being guessed at.
    """
    if not isinstance(text, str) or not text.strip() or abs(factor - 1.0) < 1e-9:
        return text

    result = text
    for unit_pattern, step, minimum in _UNIT_STEPS:
        pattern = re.compile(rf"\b{_NUMBER}{_SIZE_WORD}\s*({unit_pattern})\b", re.IGNORECASE)

        def _replace(match: re.Match) -> str:
            value = _parse_number(match.group(1))
            if value is None:
                return match.group(0)
            scaled = max(minimum, value * factor)
            # group(0) minus the leading number keeps any size word and spacing.
            tail = match.group(0)[len(match.group(1)):].lstrip()
            return f"{_format_number(scaled, step)} {tail}"

        result = pattern.sub(_replace, result)
    return result


def _scale_meal(meal: dict, factor: float) -> None:
    """Scale one meal's macros and portion text in place."""
    macros = meal.get("macros_approx")
    if isinstance(macros, dict):
        for key in _MACRO_KEYS:
            value = macros.get(key)
            if isinstance(value, (int, float)):
                macros[key] = int(round(value * factor))
    if isinstance(meal.get("portion"), str):
        meal["portion"] = scale_portion_text(meal["portion"], factor)
    meal["portion_adjusted"] = round(factor, 2)


def _day_total(day: dict) -> int:
    total = 0
    for slot in _SLOTS:
        meal = day.get(slot)
        if isinstance(meal, dict):
            value = (meal.get("macros_approx") or {}).get("calories")
            if isinstance(value, (int, float)):
                total += value
    return int(round(total))


# ---------------------------------------------------------------------------
# The two plan shapes. The LLM path writes `diet_weeks[].daily_plan[day][slot]`
# as one meal dict; the rule engine writes `four_week_plan[].days[].meals[slot]`
# as a list of KB food items. Both were measured short of target — the engine
# more so (580-1031 kcal against 1490, protein 22-40 g against an 84 g floor) —
# so neither shape can be the one that gets checked.
# ---------------------------------------------------------------------------

def _engine_slot_total(items) -> float:
    if not isinstance(items, list):
        return 0.0
    return sum(
        (item.get("macros") or {}).get("calories", 0)
        for item in items if isinstance(item, dict)
    )


def _engine_day_protein(meals: dict) -> float:
    return sum(
        (item.get("macros") or {}).get("protein_g", 0)
        for slot in _SLOTS for item in (meals.get(slot) or [])
        if isinstance(item, dict)
    )


def _llm_day_protein(day: dict) -> float:
    return sum(
        (day[slot].get("macros_approx") or {}).get("protein_g", 0)
        for slot in _SLOTS
        if isinstance(day.get(slot), dict)
    )


def _scale_engine_items(items, factor: float) -> None:
    for item in items:
        if not isinstance(item, dict):
            continue
        macros = item.get("macros")
        if isinstance(macros, dict):
            for key, value in list(macros.items()):
                if isinstance(value, (int, float)):
                    macros[key] = round(value * factor, 1)
        if isinstance(item.get("portion"), str):
            item["portion"] = scale_portion_text(item["portion"], factor)
        item["portion_adjusted"] = round(factor, 2)


def _recompute_engine_day_macros(day: dict) -> None:
    totals: dict[str, float] = {}
    for slot in _SLOTS:
        for item in day.get("meals", {}).get(slot) or []:
            if not isinstance(item, dict):
                continue
            for key, value in (item.get("macros") or {}).items():
                if isinstance(value, (int, float)):
                    totals[key] = totals.get(key, 0.0) + value
    if totals:
        day["daily_macros"] = {k: round(v, 1) for k, v in totals.items()}


def _iter_days(plan: dict):
    """Yield one record per day, in whichever of the two plan shapes it is written.

    Keys: week, day, kcal, protein_g, fasting, slot_kcal(slot), scale(slot, factor),
    finish(). `scale` applies a factor to one slot and `finish` recomputes whatever
    day-level totals that shape carries. A record rather than a tuple because the
    positional version grew to seven fields and the protein accessor made eight.
    """
    for week in plan.get("diet_weeks") or []:
        if not isinstance(week, dict):
            continue
        daily = week.get("daily_plan")
        if not isinstance(daily, dict):
            continue
        label = f"Week {week.get('week_number', '?')}"
        for day_label, day in daily.items():
            if not isinstance(day, dict):
                continue

            def _slot_kcal(slot, _day=day):
                meal = _day.get(slot)
                return (meal.get("macros_approx") or {}).get("calories", 0) if isinstance(meal, dict) else 0

            def _scale(slot, factor, _day=day):
                meal = _day.get(slot)
                if isinstance(meal, dict):
                    _scale_meal(meal, factor)

            yield {
                "week": label, "day": str(day_label), "kcal": _day_total(day),
                "protein_g": _llm_day_protein(day), "fasting": bool(day.get("is_fasting")),
                "slot_kcal": _slot_kcal, "scale": _scale, "finish": lambda: None,
                "protein_now": (lambda _day=day: _llm_day_protein(_day)),
            }

    for week in plan.get("four_week_plan") or []:
        if not isinstance(week, dict):
            continue
        label = f"Week {week.get('week', '?')}"
        for day in week.get("days") or []:
            if not isinstance(day, dict):
                continue
            meals = day.get("meals") or {}

            def _slot_kcal(slot, _meals=meals):
                return _engine_slot_total(_meals.get(slot))

            def _scale(slot, factor, _meals=meals):
                _scale_engine_items(_meals.get(slot) or [], factor)

            total = int(round(sum(_engine_slot_total(meals.get(s)) for s in _SLOTS)))
            yield {
                "week": label, "day": str(day.get("day_name", day.get("day", "?"))),
                "kcal": total, "protein_g": _engine_day_protein(meals),
                "fasting": bool(day.get("is_fasting_day")),
                "slot_kcal": _slot_kcal, "scale": _scale,
                "finish": (lambda _day=day: _recompute_engine_day_macros(_day)),
                "protein_now": (lambda _meals=meals: _engine_day_protein(_meals)),
            }


def reconcile_plan_energy(plan: dict, energy: dict) -> dict:
    """Bring each detailed day into the energy band and record what was changed.

    Only weeks carrying `macros_approx` can be reconciled — in the LLM plan shape that
    is week 1, since weeks 2-4 are meal names. The target is attached to the plan
    either way, so the weeks that cannot be checked are still stated rather than
    silently unmeasured.

    Adds:
      plan["energy_prescription"]    the target, band, per-meal budget and its basis
      plan["energy_reconciliation"]  per-day before/after, and any residual shortfall
    Never raises: an energy correction must not be able to lose a generated plan.
    """
    try:
        plan["energy_prescription"] = energy
        low, high = energy["band"]
        budget = energy["meal_budget"]
        days_report: list[dict] = []
        residuals: list[str] = []

        fasting_days = 0
        quantified = 0
        protein_short: list[dict] = []
        protein_floor = energy.get("protein_floor_g") or 0
        for _day_rec in _iter_days(plan):
            week_label, day_label = _day_rec["week"], _day_rec["day"]
            before, is_fasting = _day_rec["kcal"], _day_rec["fasting"]
            slot_kcal, scale_slot, finish = (
                _day_rec["slot_kcal"], _day_rec["scale"], _day_rec["finish"])
            if before <= 0:
                continue  # nothing quantified to reconcile (LLM weeks 2-4)
            quantified += 1

            # A fasting day is meant to be light. Upavasa and Phalahar are the
            # therapy, so raising one to a full day's energy would undo the thing
            # the day is for. Counted and reported, never scaled.
            if is_fasting:
                fasting_days += 1
                continue

            # Protein is checked on every non-fasting day, including days whose
            # energy is already in band: scaling toward a kcal budget cannot fix
            # composition, and a day can hit its calories on rice alone. The brief
            # states the floor, so something has to verify it was met.
            if protein_floor and _day_rec["protein_now"]() < protein_floor * 0.9:
                protein_short.append({
                    "week": week_label, "day": day_label,
                    "protein_g": int(round(_day_rec["protein_now"]())),
                    "floor_g": protein_floor,
                })

            if low <= before <= high:
                continue

            for slot in _SLOTS:
                current = slot_kcal(slot)
                slot_budget = budget.get(slot) or 0
                if not current or not slot_budget:
                    continue
                factor = slot_budget / current
                if abs(factor - 1.0) <= _DEADBAND:
                    continue
                scale_slot(slot, max(MIN_FACTOR, min(MAX_FACTOR, factor)))
            finish()

            after = int(round(sum(slot_kcal(slot) for slot in _SLOTS)))

            entry = {
                "week": week_label, "day": day_label,
                "before_kcal": before, "after_kcal": after,
                "target_kcal": energy["target_calories"],
            }
            if after < low:
                entry["residual_shortfall_kcal"] = int(low - after)
                residuals.append(
                    f"{week_label} {day_label} reaches {after} kcal of a "
                    f"{energy['target_calories']} kcal target even at the largest "
                    f"sensible portions — add a snack from your Pathya list."
                )
            days_report.append(entry)

        plan["energy_reconciliation"] = {
            "checked": True,
            "target_kcal": energy["target_calories"],
            "band_kcal": list(energy["band"]),
            "days_adjusted": len(days_report),
            "days": days_report,
            "residual_notes": residuals,
            # Weeks 2-4 of an LLM plan are meal names with no macros, so nothing
            # there can be summed or corrected. Say how many days were actually
            # measurable rather than implying the whole plan was checked.
            "days_quantified": quantified,
            "fasting_days_exempt": fasting_days,
            "protein_floor_g": protein_floor,
            "days_below_protein_floor": protein_short,
        }
    except Exception:
        plan["energy_reconciliation"] = {"checked": False}
    return plan
