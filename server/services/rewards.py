"""
Ayura AI — Streaks and badges.

What is rewarded is **logging**: a meal, a workout set, a yoga practice, the day's
progress, or a check-in. Opening the app is not, because a reward for visiting teaches
visiting; a reward for logging builds the habit the plans depend on, and the log is
what the next plan learns from.

What is never rewarded is an outcome or an intensity: weight lost, calories cut, a
fast kept, sets added. In a health app those are the badges that push a person past
what is good for them — a streak of fasting days, or of training through a warning
sign. `test_rewards.py` holds the catalogue to that.

An active day is counted in the **user's own timezone**. The older progress streak used
the server's UTC date, which put an Indian user's midnight at 05:30.

Days come from two places, unioned: `db.activity_days`, written by every logging route
at the moment of logging (`record_activity`), and the timestamps already on the logs.
The second covers everything logged before this module existed; the first is needed
because meal and workout logs are edited in place, so their `updated_at` moves to the
day of the edit and would otherwise take the original day's credit with it.

Earned badges are kept in `db.user_badges` so one is never taken back when its
evidence ages out of the lookback window.
"""
from __future__ import annotations

import uuid
from datetime import date, datetime, timedelta, timezone
from typing import Optional
from zoneinfo import ZoneInfo

from core.logger import logger

LOOKBACK_DAYS = 400

# (collection, timestamp field, kind)
_SOURCES = (
    ("progress_logs", "date", "progress"),
    ("meal_logs", "updated_at", "meal"),
    ("workout_logs", "updated_at", "workout"),
    ("practice_sessions", "logged_at", "practice"),
    ("weekly_checkins", "timestamp", "checkin"),
    ("gym_checkins", "updated_at", "checkin"),
    ("diet_checkins", "updated_at", "checkin"),
)
KINDS = {k for _, _, k in _SOURCES}


def _tz(name: Optional[str]) -> ZoneInfo:
    try:
        return ZoneInfo(name or "UTC")
    except Exception:
        return ZoneInfo("UTC")


def local_date(ts: datetime, tz_name: Optional[str]) -> date:
    if ts.tzinfo is None:
        ts = ts.replace(tzinfo=timezone.utc)
    return ts.astimezone(_tz(tz_name)).date()


async def record_activity(db, user_id: str, tz_name: Optional[str], kind: str,
                          now: Optional[datetime] = None) -> None:
    """Mark today (in the user's timezone) as active. Never raises: a reward must not
    be the reason a meal or a workout failed to save."""
    try:
        day = local_date(now or datetime.now(timezone.utc), tz_name).isoformat()
        await db.activity_days.update_one(
            {"_id": f"{user_id}:{day}"},
            {"$set": {"user_id": user_id, "date": day},
             "$addToSet": {"kinds": kind}},
            upsert=True)
    except Exception as exc:  # pragma: no cover - logged, not raised
        logger.warning("record_activity failed for %s: %s", user_id, exc)


async def activity(db, user_id: str, tz_name: Optional[str], today: date) -> dict:
    """Active dates, and which kinds of logging each user has ever done."""
    since = datetime.now(timezone.utc) - timedelta(days=LOOKBACK_DAYS)
    dates: set[date] = set()
    kinds: set[str] = set()
    async for d in db.activity_days.find({"user_id": user_id}, {"date": 1, "kinds": 1}):
        try:
            dates.add(date.fromisoformat(d["date"]))
            kinds |= set(d.get("kinds") or [])
        except Exception:
            continue
    for coll, field, kind in _SOURCES:
        cursor = getattr(db, coll).find(
            {"user_id": user_id, field: {"$gte": since}}, {field: 1})
        async for doc in cursor:
            ts = doc.get(field)
            if isinstance(ts, datetime):
                dates.add(local_date(ts, tz_name))
                kinds.add(kind)
    return {"dates": {d for d in dates if d <= today}, "kinds": kinds}


def streaks(dates: set[date], today: date) -> dict:
    """The current run stays alive through today: it counts back from today if today
    is logged, otherwise from yesterday, so a streak does not read as broken at 07:00
    before the day's first log."""
    start = today if today in dates else today - timedelta(days=1)
    current, d = 0, start
    while d in dates:
        current += 1
        d -= timedelta(days=1)
    best, run, prev = 0, 0, None
    for d in sorted(dates):
        run = run + 1 if prev is not None and d - prev == timedelta(days=1) else 1
        best, prev = max(best, run), d
    return {"current": current, "best": max(best, current), "today_active": today in dates}


# ── The catalogue ───────────────────────────────────────────────────────────
# `measure` names a key of the evidence dict built in `evaluate`; `need` is how much
# of it earns the badge. Icons are lucide names, mapped to components in the client.
BADGES: tuple[dict, ...] = (
    {"id": "prakriti", "title": "Know your constitution", "icon": "Sparkles", "category": "start",
     "desc": "Complete the Prakriti assessment.", "measure": "assessed", "need": 1},
    {"id": "first_plan", "title": "First plan", "icon": "ScrollText", "category": "start",
     "desc": "Build your first plan.", "measure": "plans", "need": 1},
    {"id": "first_meal", "title": "First meal logged", "icon": "Salad", "category": "start",
     "desc": "Log a meal from your diet plan.", "measure": "kind_meal", "need": 1},
    {"id": "first_workout", "title": "First workout logged", "icon": "Dumbbell", "category": "start",
     "desc": "Log an exercise from your gym plan.", "measure": "kind_workout", "need": 1},
    {"id": "first_practice", "title": "First practice", "icon": "Flower2", "category": "start",
     "desc": "Finish a guided yoga practice.", "measure": "kind_practice", "need": 1},
    {"id": "first_checkin", "title": "First check-in", "icon": "ClipboardCheck", "category": "start",
     "desc": "Tell your plan how a week went.", "measure": "kind_checkin", "need": 1},
    {"id": "streak_3", "title": "Three days running", "icon": "Flame", "category": "rhythm",
     "desc": "Log something three days in a row.", "measure": "best_streak", "need": 3},
    {"id": "streak_7", "title": "A full week", "icon": "Flame", "category": "rhythm",
     "desc": "Log something seven days in a row.", "measure": "best_streak", "need": 7},
    {"id": "streak_21", "title": "A habit forming", "icon": "Flame", "category": "rhythm",
     "desc": "Log something 21 days in a row.", "measure": "best_streak", "need": 21},
    {"id": "mandala", "title": "A mandala", "icon": "Sun", "category": "rhythm",
     "desc": "48 days in a row — the traditional length of a practice.", "measure": "best_streak",
     "need": 48},
    {"id": "days_30", "title": "30 active days", "icon": "CalendarCheck", "category": "rhythm",
     "desc": "Any 30 days with a log. Missed days do not count against this one.",
     "measure": "active_days", "need": 30},
    {"id": "days_100", "title": "100 active days", "icon": "CalendarCheck", "category": "rhythm",
     "desc": "Any 100 days with a log.", "measure": "active_days", "need": 100},
    {"id": "checkins_4", "title": "Listening to your body", "icon": "ClipboardCheck",
     "category": "reflect", "desc": "Check in on four different weeks.", "measure": "checkin_weeks",
     "need": 4},
    {"id": "diet_month", "title": "Four weeks of meals", "icon": "Salad", "category": "complete",
     "desc": "Log a meal in the fourth week of a diet plan.", "measure": "diet_week4", "need": 1},
    {"id": "gym_block", "title": "A full training block", "icon": "Dumbbell", "category": "complete",
     "desc": "Log a workout in the fourth week of a gym block.", "measure": "gym_week4", "need": 1},
)
BADGE_IDS = {b["id"] for b in BADGES}


async def _evidence(db, user, tz_name: Optional[str], today: date) -> tuple[dict, dict]:
    act = await activity(db, user.id, tz_name, today)
    st = streaks(act["dates"], today)
    best_stored = int(getattr(user, "best_streak", 0) or 0)
    st["best"] = max(st["best"], best_stored)

    checkin_weeks: set = set()
    for coll, field in (("weekly_checkins", "timestamp"), ("gym_checkins", "updated_at"),
                        ("diet_checkins", "updated_at")):
        async for doc in getattr(db, coll).find({"user_id": user.id}, {field: 1}):
            ts = doc.get(field)
            if isinstance(ts, datetime):
                checkin_weeks.add(local_date(ts, tz_name).isocalendar()[:2])

    ev = {
        "assessed": 1 if (getattr(user, "prakriti_locked", False) or getattr(user, "dosha_scores", None)) else 0,
        "plans": await db.plan_history.count_documents({"user_id": user.id}),
        "best_streak": st["best"],
        "active_days": len(act["dates"]),
        "checkin_weeks": len(checkin_weeks),
        "diet_week4": 1 if await db.meal_logs.find_one({"user_id": user.id, "week": 4}, {"_id": 1}) else 0,
        "gym_week4": 1 if await db.workout_logs.find_one({"user_id": user.id, "week": 4}, {"_id": 1}) else 0,
    }
    for k in KINDS:
        ev[f"kind_{k}"] = 1 if k in act["kinds"] else 0
    return ev, {**st, "dates": act["dates"]}


def _message(st: dict) -> str:
    cur, best = st["current"], st["best"]
    if cur == 0 and best > 0:
        return f"Your best run is {best} day{'s' if best != 1 else ''}. Any log today starts a new one."
    if cur == 0:
        return "Log a meal, a workout, a practice or today's progress to start a streak."
    if not st["today_active"]:
        return f"{cur}-day streak — log something today to keep it."
    if cur >= best and cur >= 3:
        return f"{cur} days in a row — your best yet."
    return f"{cur} day{'s' if cur != 1 else ''} in a row."


async def evaluate(db, user, now: Optional[datetime] = None) -> dict:
    """Streak, badges (earned ones persisted), and what is new since last seen."""
    now = now or datetime.now(timezone.utc)
    tz_name = getattr(user, "timezone", None)
    today = local_date(now, tz_name)
    ev, st = await _evidence(db, user, tz_name, today)

    if st["best"] > int(getattr(user, "best_streak", 0) or 0):
        await db.users.update_one({"_id": user.id}, {"$set": {"best_streak": st["best"]}})

    stored = {d["badge_id"]: d async for d in db.user_badges.find({"user_id": user.id})}
    out, new = [], []
    for b in BADGES:
        have = int(ev.get(b["measure"], 0) or 0)
        earned_doc = stored.get(b["id"])
        if earned_doc is None and have >= b["need"]:
            earned_doc = {"_id": f"{user.id}:{b['id']}", "user_id": user.id, "badge_id": b["id"],
                          "earned_at": now, "seen_at": None}
            await db.user_badges.update_one({"_id": earned_doc["_id"]},
                                            {"$setOnInsert": earned_doc}, upsert=True)
            await db.notifications.insert_one({
                "_id": str(uuid.uuid4()), "user_id": user.id, "title": f"Badge earned: {b['title']}",
                "message": b["desc"], "type": "badge", "is_read": False, "created_at": now})
        if earned_doc is not None and not earned_doc.get("seen_at"):
            new.append(b["id"])
        out.append({
            "id": b["id"], "title": b["title"], "desc": b["desc"], "icon": b["icon"],
            "category": b["category"], "earned": earned_doc is not None,
            "earned_at": earned_doc["earned_at"].isoformat()
            if earned_doc is not None and isinstance(earned_doc.get("earned_at"), datetime) else None,
            "progress": {"have": min(have, b["need"]), "need": b["need"]},
        })

    locked = [b for b in out if not b["earned"]]
    nxt = max(locked, key=lambda b: b["progress"]["have"] / b["progress"]["need"], default=None)
    last7 = []
    for i in range(6, -1, -1):
        d = today - timedelta(days=i)
        last7.append({"date": d.isoformat(), "weekday": d.strftime("%a")[:2], "active": d in st["dates"]})
    return {
        "streak": {"current": st["current"], "best": st["best"], "today_active": st["today_active"],
                   "last7": last7, "message": _message(st)},
        "active_days": ev["active_days"],
        "earned_count": sum(1 for b in out if b["earned"]),
        "badges": out,
        "new": new,
        "next": nxt,
    }
