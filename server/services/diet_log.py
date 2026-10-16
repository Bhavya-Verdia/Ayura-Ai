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

The end-of-week check-in (`services/diet_checkin`) adds what the log cannot know:
foods the patient said caused trouble, how digestion went, and whether they were
hungry. Those apply from the first check-in, without the 14-meal threshold, because
they are reports rather than inferences.

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
               goal: str | None, bmi_category: str | None,
               checkin: dict | None = None) -> dict:
    """The changes the next plan makes, each with its reason. {} on thin evidence.

    `checkin` is `diet_checkin.signals(...)`, merged in whatever the log holds."""
    checkin = checkin or {}
    if len(logs) < _MIN_LOGGED:
        return {"meals_logged": len(logs), **checkin} if checkin else {}
    out: dict = {"meals_logged": len(logs), **checkin}
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
    keyed = {k: adapt.get(k) for k in ("skipped_slots", "avoided_foods", "energy_adjust_kcal",
                                        "trouble_foods", "digestion", "hunger_adjust_kcal")}
    # The key set grew with the check-in; a log-only adaptation keeps the hash it had,
    # so shipping the check-in does not bill every patient a regeneration.
    keyed = {k: v for k, v in keyed.items()
             if v is not None or k in ("skipped_slots", "avoided_foods", "energy_adjust_kcal")}
    return hashlib.sha256(json.dumps(keyed, sort_keys=True).encode()).hexdigest()[:16]


# ── Plan over plan ────────────────────────────────────────────────────────────
#
# Every diet plan chose its four-week progression afresh, so month two opened with
# month one's first phase again — a Samatva patient kindled Agni every four weeks
# for ever, a Langhana patient never got past the opening week. Gym counts blocks;
# this counts diet plans, and says whether the last one was finished and followed,
# which is what `diet_plan_arc` needs to continue rather than restart.

_FINISHED_DAYS = 21
_FOLLOWED_MEALS, _FOLLOWED_ADHERENCE = 14, 0.5


def _aware(t):
    if isinstance(t, datetime):
        return t if t.tzinfo else t.replace(tzinfo=timezone.utc)
    return None


async def previous_plans(db, user_id: str, now: datetime | None = None) -> dict | None:
    """The diet plans before the next one: {"plan_number" (of the next plan),
    "finished", "followed", "arc", "last_phase", "meals_logged", "adherence"} about the
    latest, or None when there is none.

    A plan is finished once 21 days passed before the next was written (or now, for
    the latest), or its fourth week was logged; earlier regenerations that nothing
    was eaten from do not count. It was followed when 14 meals were logged and at
    least half of them eaten as planned."""
    now = now or datetime.now(timezone.utc)
    docs = await db.plan_history.find(
        {"user_id": user_id, "plan_type": "diet"},
        {"generated_at": 1, "plan_data.diet_plan.plan_id": 1,
         "plan_data.diet_plan.therapeutic_arc": 1}).to_list(length=24)
    docs = sorted((d for d in docs if _aware(d.get("generated_at"))),
                  key=lambda d: _aware(d["generated_at"]))
    if not docs:
        return None
    pid = lambda d: ((d.get("plan_data") or {}).get("diet_plan") or {}).get("plan_id") or d.get("_id")  # noqa: E731
    ids = [pid(d) for d in docs]
    logs: dict = defaultdict(list)
    async for entry in db.meal_logs.find({"user_id": user_id, "plan_id": {"$in": ids}},
                                         {"plan_id": 1, "week": 1, "status": 1, "slot": 1}):
        logs[entry.get("plan_id")].append(entry)

    finished = []
    for i, d in enumerate(docs):
        until = _aware(docs[i + 1]["generated_at"]) if i + 1 < len(docs) else now
        days = (until - _aware(d["generated_at"])).days
        week4 = any(l.get("week") == 4 for l in logs[pid(d)])
        finished.append(days >= _FINISHED_DAYS or week4)

    latest = docs[-1]
    mine = logs[pid(latest)]
    s = summarise(mine)
    arc = ((latest.get("plan_data") or {}).get("diet_plan") or {}).get("therapeutic_arc") or {}
    weeks = arc.get("weeks") or []
    return {
        "plan_number": sum(finished) + 1,
        "plans_before": len(docs),
        "finished": finished[-1],
        "followed": bool(finished[-1] and s["meals_logged"] >= _FOLLOWED_MEALS
                         and (s["adherence"] or 0) >= _FOLLOWED_ADHERENCE),
        "arc": arc.get("arc"),
        "last_phase": weeks[-1]["phase"] if weeks else None,
        "meals_logged": s["meals_logged"],
        "adherence": s["adherence"],
    }


async def diet_history(db, user_id: str, *, goal: str | None,
                       bmi_category: str | None, profile: dict | None = None) -> dict:
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
        from services.diet_checkin import signals
        checkins = await db.diet_checkins.find(
            {"user_id": user_id, "updated_at": {"$gte": since}}).to_list(length=50)
        adapt = adaptation(logs, weights, goal=goal, bmi_category=bmi_category,
                           checkin=signals(checkins, {**(profile or {}),
                                                      "bmi_category": bmi_category}))
        # Only a finished plan is continued from; one regenerated mid-way is not a
        # step in a sequence. Deliberately NOT in the fingerprint: it flips the day
        # the next plan is written (that plan is the latest, and unfinished), and a
        # key that moves under a current plan bills a regeneration. The next plan is
        # asked for with force_regenerate, from the end-of-plan card or the dashboard.
        prev = await previous_plans(db, user_id)
        if prev and prev["finished"]:
            adapt = {**adapt, "continues": prev}
        # Which plan this is, finished or not: the staple rotation and the rule
        # engine's seed are offset by it, so month two does not open on month one's
        # grains and pulses. Not in the fingerprint either, for the same reason.
        if prev:
            adapt = {**adapt, "plan_seq": prev["plans_before"] + 1}
        return {"adaptation": adapt, "summary": summarise(logs), "fingerprint": fingerprint(adapt)}
    except Exception as e:  # noqa: BLE001
        logger.warning(f"diet history unavailable: {e}")
        return {"adaptation": {}, "summary": summarise([]), "fingerprint": "unavailable"}


def brief_block(adapt: dict) -> str:
    """The log, as the brief tells it to the model."""
    if not adapt:
        return ""
    from services.diet_nutrition import name_of
    lines = [f"WHAT THE PATIENT'S MEAL LOG AND WEEKLY CHECK-INS SHOW "
             f"({adapt.get('meals_logged', 0)} meals logged):"]
    if adapt.get("trouble_foods"):
        names = ", ".join(name_of(f) for f in adapt["trouble_foods"])
        lines.append(f"- the patient reported trouble after eating: {names}. They are not on "
                     "the food list; do not name them anywhere in the plan.")
    for d in adapt.get("digestion") or []:
        if d == "loose_stools":
            lines.append("- loose stools last week: keep meals light, warm and well cooked "
                         "(khichdi, moong, rice kanji, takra); no raw salads, no heavy pulses.")
        else:
            lines.append(f"- {d} last week: the {d} protocol above applies to every meal.")
    if adapt.get("hunger_adjust_kcal"):
        lines.append(f"- energy changed {adapt['hunger_adjust_kcal']:+d} kcal: the patient was "
                     + ("hungry between meals." if adapt["hunger_adjust_kcal"] > 0
                        else "served more than they could eat."))
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


# ── The end of the four weeks, said to the patient ───────────────────────────
#
# Week four was the last page of the plan and nothing came after it: the plan sat
# there in week six, and the meal log that was meant to shape the next one shaped
# nothing until the patient thought to regenerate. Once a plan is four weeks old and
# still the latest, one notification says so — as the gym block does.

_PLAN_DAYS = 28
# Older than this, the plan was abandoned rather than finished.
_NOTIFY_WINDOW_DAYS = 10


async def notify_finished_plans(db, now: datetime | None = None) -> int:
    from services.notification_service import create_and_deliver_notification

    now = now or datetime.now(timezone.utc)
    due_before = now - timedelta(days=_PLAN_DAYS)
    due_after = due_before - timedelta(days=_NOTIFY_WINDOW_DAYS)
    sent = 0
    async for record in db.plan_history.find({
            "plan_type": "diet", "plan_end_notified": {"$exists": False},
            "generated_at": {"$lte": due_before, "$gte": due_after}}):
        user_id = record.get("user_id")
        newer = await db.plan_history.find_one({
            "user_id": user_id, "plan_type": "diet",
            "generated_at": {"$gt": record.get("generated_at")}}, {"_id": 1})
        if not newer:
            plan = (record.get("plan_data") or {}).get("diet_plan") or {}
            logs = [entry async for entry in db.meal_logs.find(
                {"user_id": user_id, "plan_id": plan.get("plan_id") or record.get("_id")})]
            s = summarise(logs)
            if s["meals_logged"]:
                body = (f"You logged {s['meals_logged']} meals, "
                        f"{round((s['adherence'] or 0) * 100)}% eaten as planned. Your next "
                        "four weeks are built from them — open your diet plan to start.")
            else:
                body = ("Your four weeks are up. Open your diet plan to start the next four — "
                        "log a few meals as you go and the plan after that is built from them.")
            try:
                await create_and_deliver_notification(
                    db, user_id=user_id, title="Your diet plan's four weeks are done",
                    body=body, notif_type="reminder", url="/dashboard")
                sent += 1
            except Exception:  # noqa: BLE001 — one user's delivery must not stop the rest
                continue
        # Marked either way: a superseded plan is never due again.
        await db.plan_history.update_one({"_id": record.get("_id")},
                                         {"$set": {"plan_end_notified": now}})
    return sent
