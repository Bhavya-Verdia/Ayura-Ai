"""What the patient actually ate, and what the next diet plan does about it.

The gym plan reads its log; the diet plan read nothing. Whether a meal was eaten,
skipped or swapped was never recorded, so the plan could not know that breakfast is
skipped every weekday, that the patient will not eat karela, or that weight has not
moved in a month of following a weight-loss plan.

One document per (plan, week, day, slot) in `db.meal_logs`; logging again edits it.
The meal's component ids are copied in at log time, so a log still means something
after the plan is regenerated.

`adaptation` turns the log into three changes a dietitian would make at a review, and
only on enough evidence to make them:

  * a SLOT skipped on at least half of 5+ logged days — keep that meal light and
    quick rather than keep planning one that is not eaten;
  * FOODS left in skipped or swapped meals at least 3 times and 60% of the times they
    were served — use them rarely and offer an alternative (a soft dislike, not an
    exclusion: a skipped meal has many reasons);
  * ENERGY, only with 70% of logged meals eaten and two weigh-ins 14+ days apart:
    a weight-loss plan losing under 0.2 kg a week comes down 150 kcal, one losing
    more than 1% of body weight a week goes up 150; a plan for an underweight patient
    that is not gaining goes up 150. The floors in `diet_energy` still hold. Low
    adherence changes no energy figure — the plan was not tested, so it is not wrong.

What joins the plan's cache key is this adaptation, not the log: logging a meal
must not bill a regeneration, and the answer only changes when a threshold is crossed.
"""
from __future__ import annotations

import hashlib
import json
import logging
from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone

logger = logging.getLogger("ayura")

STATUSES = ("eaten", "partly", "skipped", "swapped")
SLOTS = ("breakfast", "lunch", "snack", "dinner", "special_drink")
_WINDOW_DAYS = 42
_MIN_LOGGED = 14
_SLOT_MIN, _SLOT_SKIP = 5, 0.5
_FOOD_MIN, _FOOD_SKIP = 3, 0.6
_ADHERENCE_FOR_ENERGY = 0.7
_WEIGH_SPAN_DAYS = 14
_STEP_KCAL = 150


def log_key(user_id: str, plan_id: str, week: int, day: str, slot: str) -> str:
    return f"{user_id}:{plan_id}:{week}:{day}:{slot}"


def _score(status: str) -> float:
    return {"eaten": 1.0, "partly": 0.5}.get(status, 0.0)


def summarise(logs: list[dict]) -> dict:
    """Counts the screen shows: by status, by slot, and the share eaten."""
    by_status = Counter(l["status"] for l in logs)
    by_slot: dict = defaultdict(Counter)
    for l in logs:
        by_slot[l["slot"]][l["status"]] += 1
    n = len(logs)
    return {"meals_logged": n, "by_status": dict(by_status),
            "by_slot": {s: dict(c) for s, c in by_slot.items()},
            "adherence": round(sum(_score(l["status"]) for l in logs) / n, 2) if n else None}


def _weight_trend(weights: list[tuple[datetime, float]]) -> float | None:
    """kg per week, least squares, over weigh-ins spanning at least 14 days."""
    if len(weights) < 2:
        return None
    weights = sorted(weights)
    span = (weights[-1][0] - weights[0][0]).total_seconds() / 86400
    if span < _WEIGH_SPAN_DAYS:
        return None
    xs = [(t - weights[0][0]).total_seconds() / 86400 / 7 for t, _ in weights]
    ys = [w for _, w in weights]
    mx, my = sum(xs) / len(xs), sum(ys) / len(ys)
    den = sum((x - mx) ** 2 for x in xs)
    return sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / den if den else None


def adaptation(logs: list[dict], weights: list[tuple[datetime, float]], *,
               goal: str | None, bmi_category: str | None) -> dict:
    """The changes the next plan makes, each with its reason. {} on thin evidence."""
    if len(logs) < _MIN_LOGGED:
        return {}
    out: dict = {"meals_logged": len(logs)}
    summary = summarise(logs)
    adherence = summary["adherence"] or 0.0

    skipped_slots = []
    for slot, c in summary["by_slot"].items():
        total = sum(c.values())
        if total >= _SLOT_MIN and c.get("skipped", 0) / total >= _SLOT_SKIP:
            skipped_slots.append(slot)
    if skipped_slots:
        out["skipped_slots"] = sorted(skipped_slots)

    served, left = Counter(), Counter()
    for l in logs:
        for fid in set(l.get("foods") or []):
            served[fid] += 1
            if l["status"] in ("skipped", "swapped"):
                left[fid] += 1
    from services.diet_nutrition import SEASONINGS
    avoided = sorted((f for f, k in left.items() if f not in SEASONINGS
                      and k >= _FOOD_MIN and k / served[f] >= _FOOD_SKIP),
                     key=lambda f: (-left[f], f))[:6]
    if avoided:
        out["avoided_foods"] = avoided

    trend = _weight_trend(weights)
    latest = sorted(weights)[-1][1] if weights else None
    adjust, reason = 0, None
    if trend is not None and adherence >= _ADHERENCE_FOR_ENERGY:
        if bmi_category == "underweight":
            if trend < 0.1:
                adjust, reason = _STEP_KCAL, (
                    f"weight changed {trend:+.1f} kg a week with most meals eaten; an "
                    "underweight patient needs to gain")
        elif goal == "weight_loss":
            if trend > -0.2:
                adjust, reason = -_STEP_KCAL, (
                    f"weight changed {trend:+.1f} kg a week with {round(adherence * 100)}% "
                    "of meals eaten; a weight-loss plan aims for 0.25-1 kg a week")
            elif latest and trend < -0.01 * latest:
                adjust, reason = _STEP_KCAL, (
                    f"weight is falling {abs(trend):.1f} kg a week, faster than 1% of body "
                    "weight, which costs muscle")
    if adjust:
        out["energy_adjust_kcal"] = adjust
        out["energy_reason"] = reason
    if trend is not None:
        out["weight_trend_kg_per_week"] = round(trend, 2)
    out["adherence"] = round(adherence, 1)
    return out


def fingerprint(adapt: dict) -> str:
    """What changes the plan, and nothing else: logging one more meal must not."""
    keyed = {k: adapt.get(k) for k in ("skipped_slots", "avoided_foods", "energy_adjust_kcal")}
    return hashlib.sha256(json.dumps(keyed, sort_keys=True).encode()).hexdigest()[:16]


async def diet_history(db, user_id: str, *, goal: str | None,
                       bmi_category: str | None) -> dict:
    """{"adaptation", "summary", "fingerprint"}. Never raises: a logging outage must
    not stop a plan being built."""
    try:
        since = datetime.now(timezone.utc) - timedelta(days=_WINDOW_DAYS)
        logs = await db.meal_logs.find(
            {"user_id": user_id, "updated_at": {"$gte": since}}).to_list(length=2000)
        progress = await db.progress_logs.find(
            {"user_id": user_id, "date": {"$gte": since - timedelta(days=14)},
             "weight_kg": {"$gt": 0}}, {"date": 1, "weight_kg": 1}).to_list(length=500)
        weights = []
        for p in progress:
            d = p["date"]
            if isinstance(d, datetime):
                weights.append((d if d.tzinfo else d.replace(tzinfo=timezone.utc),
                                float(p["weight_kg"])))
        adapt = adaptation(logs, weights, goal=goal, bmi_category=bmi_category)
        return {"adaptation": adapt, "summary": summarise(logs), "fingerprint": fingerprint(adapt)}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"diet history unavailable: {e}")
        return {"adaptation": {}, "summary": summarise([]), "fingerprint": "unavailable"}


def brief_block(adapt: dict) -> str:
    """The log, as the brief tells it to the model."""
    if not adapt:
        return ""
    from services.diet_nutrition import name_of
    lines = [f"WHAT THE PATIENT'S MEAL LOG SHOWS ({adapt['meals_logged']} meals logged):"]
    for slot in adapt.get("skipped_slots") or []:
        lines.append(f"- {slot.replace('_', ' ')} is usually skipped: make it quick (under 10 "
                     "minutes) and light, something they will actually eat — do not drop it.")
    if adapt.get("avoided_foods"):
        names = ", ".join(name_of(f) for f in adapt["avoided_foods"])
        lines.append(f"- meals built on these were repeatedly left uneaten: {names}. Use them "
                     "rarely, and never as the centre of a meal.")
    if adapt.get("energy_adjust_kcal"):
        lines.append(f"- energy changed {adapt['energy_adjust_kcal']:+d} kcal: {adapt['energy_reason']}.")
    return "\n".join(lines) if len(lines) > 1 else ""
