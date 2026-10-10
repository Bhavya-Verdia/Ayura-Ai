"""The end-of-week diet check-in, and what it changes in the weeks still to come.

The meal log says whether a meal was eaten. It cannot say why a meal was left, and
a skipped paneer could mean a busy morning or a night of bloating. A dietitian asks
at each review, and so does this:

  * HUNGER — hungry between meals, about right, or too much food. ±150 kcal, never
    a deficit for a child or in pregnancy (`diet_energy` holds that, as it does for
    the log's own step), and the floors still apply.
  * DIGESTION — bloating, acidity and constipation are conditions the diet path
    already has protocols, scan floors and library claims for, so the next weeks are
    composed and screened under them. Loose stools have no food protocol here; the
    brief is told to keep meals light and well cooked.
  * TROUBLE FOODS — picked from what the patient was actually served that week, with
    what happened. A food named here is left out of the remaining weeks and the next
    plan for six weeks: it is the patient's own report, not a guess from the log.
  * WARNING SIGNS — swelling of the lips, face or tongue, wheezing or a tight throat,
    widespread hives, repeated vomiting, blood or black stools. None of these is
    answered by a different menu. The screen says to see a doctor, and the food can
    go onto the allergy list the patient declared, only if they tick it.

Nothing is rebuilt from here. `proposal` says what would change, and the patient
asks for the rebuild (`POST /api/plans/diet/rebuild`), because a rebuild uses a
plan generation and changing a plan unasked reads as a different plan.
"""
from __future__ import annotations

from datetime import datetime

HUNGER = ("hungry", "right", "too_much")
DIGESTION = ("bloating", "acidity", "constipation", "loose_stools")
# The digestion answers that are diet-path conditions, with their canonical key.
DIGESTION_CONDITIONS = {"bloating": "bloating", "acidity": "acidity",
                        "constipation": "constipation"}
PROBLEMS = ("bloating", "acidity", "loose_stools", "nausea", "itching_rash", "did_not_like")
RED_FLAGS = ("swelling", "breathing", "hives", "vomiting", "blood_in_stool")
HUNGER_STEP_KCAL = 150
MAX_TROUBLE_FOODS = 8


def week_foods(plan: dict, week: int) -> list[dict]:
    """[{id, name}] the patient was served in that week, for the "which food" picker.
    Salt, oils and spices are left out: nobody blames the jeera for a bad night."""
    from services.diet_nutrition import SEASONINGS, name_of, role
    seen: dict[str, str] = {}
    for w in plan.get("diet_weeks") or []:
        if w.get("week_number") != week:
            continue
        for day in (w.get("daily_plan") or {}).values():
            if not isinstance(day, dict):
                continue
            for meal in day.values():
                if not isinstance(meal, dict):
                    continue
                for c in meal.get("components") or []:
                    fid = c.get("food")
                    if not fid or fid in seen or fid in SEASONINGS or fid in ("salt", "rock_salt"):
                        continue
                    if role(fid) == "fat":
                        continue
                    seen[fid] = name_of(fid)
    return sorted(({"id": k, "name": v, "allergies": allergy_keys_for(k)}
                   for k, v in seen.items()), key=lambda f: f["name"])


def allergy_keys_for(fid: str) -> list[str]:
    """The declared-allergy keys whose screen would remove this food — what the
    patient can add after a reaction. Read off the same screen the plan uses, so the
    key added is one that actually removes the food."""
    from schemas.preferences_schema import FOOD_ALLERGIES
    from services.diet_allowed_foods import _candidates, screen_foods
    food = next((f for f in _candidates() if f["id"] == fid), None)
    if not food:
        return []
    return sorted(k for k in FOOD_ALLERGIES
                  if screen_foods([food], allergies=[k], intolerances=[], dietary_type=None,
                                  conditions=[]))


def proposal(checkin: dict | None, profile: dict) -> dict:
    """What the remaining weeks would change, each with its reason, before anything
    is rebuilt. {} when there is no check-in. Editing a check-in clears `rebuilt_at`,
    so a changed answer can be rebuilt again."""
    if not checkin:
        return {}
    from services.diet_nutrition import name_of
    week = int(checkin.get("week") or 0)
    from_week = week + 1
    changes: list[dict] = []

    foods = [t["food"] for t in checkin.get("trouble_foods") or [] if t.get("food")]
    if foods:
        changes.append({"kind": "exclude", "foods": [name_of(f) for f in foods]})
    for d in checkin.get("digestion") or []:
        if d in DIGESTION_CONDITIONS:
            changes.append({"kind": "digestion", "condition": d})
        elif d == "loose_stools":
            changes.append({"kind": "light_meals"})
    kcal = hunger_adjust(checkin, profile)
    if kcal:
        changes.append({"kind": "energy", "kcal": kcal})

    return {
        "week": week, "from_week": from_week, "changes": changes,
        "see_doctor": bool(checkin.get("red_flags")),
        "rebuild_available": bool(changes) and from_week <= 4
                             and not checkin.get("rebuilt_at"),
    }


def hunger_adjust(checkin: dict | None, profile: dict) -> int:
    """±150 kcal from the hunger answer. Never a cut for a child, in pregnancy or
    breastfeeding, or for an underweight patient."""
    hunger = (checkin or {}).get("hunger")
    if hunger == "hungry":
        return HUNGER_STEP_KCAL
    if hunger == "too_much":
        age = profile.get("age")
        if (profile.get("pregnancy_or_nursing") or (isinstance(age, (int, float)) and age < 18)
                or profile.get("bmi_category") == "underweight"):
            return 0
        return -HUNGER_STEP_KCAL
    return 0


def signals(checkins: list[dict], profile: dict) -> dict:
    """What the check-ins add to the diet log's adaptation.

    Trouble foods from every check-in in the window, because the patient said so.
    Digestion and hunger from the latest only: they describe how the last week went,
    and last month's bloating is not this week's."""
    if not checkins:
        return {}

    def when(c):
        t = c.get("updated_at")
        return t if isinstance(t, datetime) else datetime.min

    ordered = sorted(checkins, key=when)
    trouble: list[str] = []
    for c in reversed(ordered):
        for t in c.get("trouble_foods") or []:
            if t.get("food") and t["food"] not in trouble:
                trouble.append(t["food"])
    latest = ordered[-1]
    out: dict = {}
    if trouble:
        out["trouble_foods"] = trouble[:MAX_TROUBLE_FOODS * 2]
    digestion = [d for d in latest.get("digestion") or [] if d in DIGESTION]
    if digestion:
        out["digestion"] = sorted(digestion)
    kcal = hunger_adjust(latest, profile)
    if kcal:
        out["hunger_adjust_kcal"] = kcal
    return out
