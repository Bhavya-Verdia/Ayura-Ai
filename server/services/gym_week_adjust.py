"""Next week's weights, from last week's logged sets and check-in.

A gym plan is a four-week block written at once, and until this the log only
reached the NEXT block: someone whose week-one dumbbell press was logged "easy"
at the top of the range was shown the same weight for weeks two and three. A
coach changes week two after watching week one, and that is all this does.

What it changes, and what it does not:

  * The block's STRUCTURE stays as written — exercises, sets, reps, rest. A plan
    that reshuffles weekly cannot be measured against itself.
  * The LOAD moves, per exercise, by the rule a coach writes on the card —
    double progression with effort as the governor:
      - every set at the top of the range, or logged "easy"  -> one step up
      - sets inside the range, "about right"                 -> same weight, more reps
      - a set below the range                                -> same weight
      - below the range AND "very hard"                      -> about 10% down
  * The week's own intent is kept: a deload week is still lighter than the
    week before it, by the ratio the plan itself quoted between the two weeks.
  * The check-in can only hold or lower. "Too easy" with nothing logged does not
    raise a weight — the asymmetry is the point: lowering on a feeling is safe,
    raising on one is not.

Adjustments are computed on read from `db.workout_logs` and `db.gym_checkins`;
nothing is written back into the plan, so the plan in `plan_history` is still
the prescription that was made.
"""
from __future__ import annotations

import re

from services.gym_plan_engine import _BELL_SIZES, _fmt_kg, _parse_reps, _round_load

_STEP_DOWN = 0.90
_EMPTY_BAR_KG = 20.0

FEELINGS = ("too_easy", "right", "too_hard")
# Symptoms that end the question of load. Each is a reason to stop exercising
# and be seen (ACSM's Guidelines, 11th ed., signs to terminate exercise); none of
# them is something a lighter dumbbell answers.
RED_FLAGS = {
    "chest_pain": "chest pain or pressure",
    "fainting": "fainting or nearly fainting",
    "palpitations": "a racing or irregular heartbeat",
    "breathlessness": "breathlessness out of proportion to the effort",
}

_KG = re.compile(r"(\d+(?:\.\d+)?)\s*kg")
_RANGE_TOP = re.compile(r"(\d+(?:\.\d+)?)\s*[–-]\s*(\d+(?:\.\d+)?)\s*kg")
_HARDER = re.compile(r"Too easy\?\s*(?:Move to|Use|Try)\s*([^.]+)\.", re.I)
_EASIER = re.compile(r"Too hard\?\s*(?:Use|Move to|Try)\s*([^.]+)\.", re.I)


def _quoted_kg(weight_range: str | None) -> float | None:
    """The top of the plan's quoted range, or the first bell named."""
    text = str(weight_range or "")
    m = _RANGE_TOP.search(text)
    if m:
        return float(m.group(2))
    m = _KG.search(text)
    return float(m.group(1)) if m else None


def _week(plan: dict, n: int) -> dict | None:
    for w in plan.get("four_week_plan") or []:
        if w.get("week") == n:
            return w
    return None


def _prescribed(week: dict | None) -> dict:
    """{exercise_id: exercise} for a week; the first day it appears wins."""
    out: dict = {}
    for day in (week or {}).get("days") or []:
        for ex in day.get("main_workout") or []:
            out.setdefault(ex.get("exercise_id"), ex)
    return out


def _step_up(kg: float, kettlebell: bool) -> float:
    """The next weight up: the next bell, or one plate step — 1 kg below 20 kg,
    2.5 kg above, the same steps the plan quotes in."""
    if kettlebell:
        heavier = [b for b in _BELL_SIZES if b > kg]
        return float(heavier[0]) if heavier else kg
    return kg + (1.0 if kg < 20 else 2.5)


def _step_down(kg: float, kettlebell: bool, barbell: bool) -> float:
    if kettlebell:
        lighter = [b for b in _BELL_SIZES if b < kg]
        return float(lighter[-1]) if lighter else kg
    down = _round_load(kg * _STEP_DOWN)
    if down >= kg:
        down = kg - (1.0 if kg <= 20 else 2.5)
    if barbell and kg >= _EMPTY_BAR_KG:
        down = max(down, _EMPTY_BAR_KG)
    return max(down, 1.0)


def _scale(kg: float, ratio: float, kettlebell: bool) -> float:
    if abs(ratio - 1.0) < 0.01:
        return kg
    if kettlebell:
        target = kg * ratio
        return float(min(_BELL_SIZES, key=lambda b: abs(b - target)))
    return _round_load(kg * ratio)


def _week_ratio(prev_ex: dict, next_ex: dict, next_week: dict | None) -> float:
    """How much heavier or lighter the plan meant next week to be than last.

    Read from the plan's own two quotes for the exercise, so a deload stays a
    deload; when either is not a number, from the week's theme."""
    a, b = _quoted_kg(prev_ex.get("weight_range")), _quoted_kg(next_ex.get("weight_range"))
    if a and b:
        return max(0.7, min(1.15, b / a))
    theme = str((next_week or {}).get("theme") or "").lower()
    return 0.85 if "deload" in theme else 1.0


def _latest_entry(entries, week: int, exercise_id: str):
    found = [e for e in entries if e.get("week") == week and e.get("exercise_id") == exercise_id
             and e.get("sets")]
    return max(found, key=lambda e: e.get("day") or 0) if found else None


def _adjust_one(entry: dict, prev_ex: dict, next_ex: dict, next_week: dict | None,
                *, allow_rise: bool) -> dict | None:
    rng = _parse_reps(prev_ex.get("reps"))
    if not rng:
        return None
    lo, hi = rng
    sets = [s for s in entry.get("sets") or [] if int(s.get("reps") or 0) > 0]
    if not sets:
        return None
    effort = entry.get("effort") or "right"
    reps = [int(s["reps"]) for s in sets]
    all_top = all(r >= hi for r in reps)
    short = any(r < lo for r in reps)
    logged_text = ", ".join(
        (f"{_fmt_kg(float(s.get('kg') or 0))}×{s['reps']}" if float(s.get("kg") or 0) > 0
         else f"{s['reps']}") for s in sets)
    feel = {"easy": "felt easy", "hard": "felt very hard"}.get(effort, "felt about right")

    equipment = str(next_ex.get("equipment") or prev_ex.get("equipment") or "").lower()
    kg = max(float(s.get("kg") or 0) for s in sets)

    if kg <= 0:
        # Bodyweight: the load is the variant, and the library names both steps.
        notes = str(next_ex.get("notes") or prev_ex.get("notes") or "")
        if (all_top or effort == "easy") and effort != "hard" and allow_rise:
            m = _HARDER.search(notes)
            if m:
                return {"direction": "up", "text": f"Move to {m.group(1).strip()}",
                        "reason": f"Last week: {logged_text} — {feel}, at the top of the range."}
            return None
        if short and effort == "hard":
            m = _EASIER.search(notes)
            if m:
                return {"direction": "down", "text": f"Use {m.group(1).strip()}",
                        "reason": f"Last week: {logged_text} — {feel}, below the range."}
        return None

    kettlebell = "kettlebell" in equipment
    barbell = "barbell" in equipment
    if short and effort == "hard":
        direction, base = "down", _step_down(kg, kettlebell, barbell)
        why = "below the range — a lighter weight lets every set reach it"
    elif (all_top or effort == "easy") and effort != "hard" and not short:
        if allow_rise:
            direction, base = "up", _step_up(kg, kettlebell)
            why = "every set at the top of the range" if all_top else "with reps to spare"
        else:
            direction, base = "hold", kg
            why = "held this week because of your check-in"
    elif short:
        direction, base = "hold", kg
        why = "finish the range at this weight before adding more"
    else:
        direction, base = "hold", kg
        why = "same weight, aim for one more rep on each set"

    deload_week = "deload" in str((next_week or {}).get("theme") or "").lower()
    if deload_week and direction == "up":
        # Light weights round the plan's own deload away (4-5 kg quoted in both
        # weeks), so the ratio alone let a deload week add weight.
        base = kg
    ratio = _week_ratio(prev_ex, next_ex, next_week)
    target = _scale(base, ratio, kettlebell)
    if barbell and kg >= _EMPTY_BAR_KG:
        target = max(target, _EMPTY_BAR_KG)
    if direction != "down" and (target < kg or deload_week):
        # In a deload week the deload is the message. "Up" or "same weight"
        # beside a number lighter than the one just logged read as a mistake.
        direction = "deload"
        why = ("this is the plan's deload week, so it is lighter than what you lifted — "
               "keep every rep smooth")
    elif target > base:
        why += ", then a little heavier for the plan's peak week"
    quoted = str(next_ex.get("weight_range") or "")
    unit = (" per hand" if "per hand" in quoted
            else " in one hand" if "in one hand" in quoted else "")
    noun = "bell" if kettlebell else ""
    text = f"{_fmt_kg(target)} kg{(' ' + noun) if noun else ''}{unit}"
    return {"direction": direction, "load_kg": target, "text": text,
            "reason": f"Last week: {logged_text} — {feel}; {why}."}


def week_adjustments(plan: dict, entries, checkin: dict | None, week: int) -> dict:
    """What changes in `week` because of what happened in `week - 1`.

    {week, based_on_week, exercises: {exercise_id: {...}}, notices: [...],
     stop: str | None}."""
    out = {"week": week, "based_on_week": week - 1, "exercises": {}, "notices": [],
           "stop": None}
    if week < 2:
        return out
    prev_week, next_week = _week(plan, week - 1), _week(plan, week)
    if not prev_week or not next_week:
        return out
    checkin = checkin or {}
    entries = [e for e in entries or [] if e.get("plan_id") == plan.get("plan_id")]

    flags = [RED_FLAGS[f] for f in checkin.get("red_flags") or [] if f in RED_FLAGS]
    if flags:
        out["stop"] = (f"You reported {', '.join(flags)} last week. Stop training and see a "
                       "doctor before your next session — these are reasons to be examined, "
                       "not to lift lighter.")
        return out

    allow_rise = True
    if checkin.get("unwell"):
        allow_rise = False
        out["notices"].append(
            "You were unwell last week, so no weight goes up this week. If you have a fever, "
            "or symptoms below the neck — chest, aching muscles, an upset stomach — rest until "
            "a day after they clear.")
    if checkin.get("feeling") == "too_hard":
        allow_rise = False
        out["notices"].append(
            "Last week felt too hard, so this week holds every weight where it was.")
    if checkin.get("pain_areas"):
        out["notices"].append(
            "You reported pain last week. Leave out anything that brings it back, and rebuild "
            "the plan around it if it is still there.")

    prev = _prescribed(prev_week)
    nxt = _prescribed(next_week)
    for ex_id, next_ex in nxt.items():
        prev_ex = prev.get(ex_id)
        entry = _latest_entry(entries, week - 1, ex_id)
        if not prev_ex or not entry:
            continue
        adj = _adjust_one(entry, prev_ex, next_ex, next_week, allow_rise=allow_rise)
        if adj:
            if entry.get("effort") == "hard" and plan.get("intensity_notice"):
                adj["reason"] += (" Your plan keeps every set short of failure — stop with two "
                                  "reps left in the tank.")
            out["exercises"][ex_id] = adj

    logged_any = any(e.get("week") == week - 1 for e in entries)
    if checkin.get("feeling") == "too_easy" and not logged_any:
        out["notices"].append(
            "Last week felt too easy, but none of it was logged — log your sets this week and "
            "next week's weights will move from them.")
    return out
