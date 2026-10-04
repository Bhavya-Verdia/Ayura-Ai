"""What the practitioner actually lifted, and what the next block learns from it.

Until this, every gym plan was a document: four weeks written from estimates,
with nothing to say whether a set was ever done or what it weighed — and
regenerating after week four started again from the same estimates. A coach
changes week two after watching week one. This is the record that lets the plan
do the same:

  * `logged_lifts` turns logged sets into a measured one-rep max per exercise,
    which `gym_plan_engine._load_calibration` uses IN PLACE of the bodyweight
    estimate for that exercise.
  * `block_summary` says how much of the last block was done, which decides
    whether the next one builds on it or repeats it.

Logs live in `db.workout_logs`, one document per (plan, week, day, exercise),
so logging a set twice edits it rather than duplicating it.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone

# How hard the set felt, as reps left in reserve. "Right" is what the plan asks
# for — the last two reps hard — so it is the default when nothing is said.
EFFORT_RIR = {"easy": 3, "right": 2, "hard": 0}
_DEFAULT_RIR = 2
# Epley stops being a reasonable estimator well before twenty reps; a set of 25
# says more about endurance than about strength.
_MAX_REPS_FOR_ESTIMATE = 15
# How far back a logged set still describes the practitioner.
RECENT_DAYS = 42
# Below this share of planned sessions, the next block repeats rather than
# progresses: there is not enough of the last one to build on.
_ADHERENCE_TO_PROGRESS = 0.5


def log_key(user_id: str, plan_id: str, week: int, day: int, exercise_id: str) -> str:
    return f"{user_id}:{plan_id}:{week}:{day}:{exercise_id}"


def _one_rm(kg: float, reps: int, rir: int) -> float:
    return float(kg) * (1.0 + (int(reps) + rir) / 30.0)


def best_set(entry: dict):
    """(one_rm, kg, reps) of the strongest loaded set in a log entry, or None."""
    rir = EFFORT_RIR.get(entry.get("effort"), _DEFAULT_RIR)
    best = None
    for s in entry.get("sets") or []:
        try:
            kg, reps = float(s.get("kg") or 0), int(s.get("reps") or 0)
        except (TypeError, ValueError):
            continue
        if kg <= 0 or reps <= 0 or reps > _MAX_REPS_FOR_ESTIMATE:
            continue
        est = _one_rm(kg, reps, rir)
        if best is None or est > best[0]:
            best = (est, kg, reps)
    return best


def logged_lifts(entries) -> dict:
    """{exercise_id: {one_rm, source}} — the strongest recent set per exercise.

    The strongest rather than the latest: a deload week's lighter sets are
    logged too, and they are not a measurement of what the practitioner can do.
    """
    out: dict = {}
    for entry in entries or []:
        found = best_set(entry)
        if not found:
            continue
        one_rm, kg, reps = found
        ex = entry.get("exercise_id")
        if ex and (ex not in out or one_rm > out[ex]["one_rm"]):
            kg_text = f"{kg:.1f}".rstrip("0").rstrip(".")
            out[ex] = {"one_rm": round(one_rm, 2), "source": f"{kg_text} kg × {reps}"}
    return out


def planned_sessions(plan: dict) -> int:
    return sum(1 for week in plan.get("four_week_plan") or []
               for day in week.get("days") or [] if day.get("main_workout"))


def block_summary(plan: dict | None, entries) -> dict | None:
    """How much of a block was done, and what it showed.

    None when there is no previous plan to summarise."""
    if not plan:
        return None
    entries = [e for e in entries or [] if e.get("plan_id") == plan.get("plan_id")]
    sessions = {(e.get("week"), e.get("day")) for e in entries if e.get("sets")}
    planned = planned_sessions(plan)
    adherence = len(sessions) / planned if planned else 0.0

    # First and best logged estimate per exercise across the block — what moved.
    first: dict = {}
    best: dict = {}
    names: dict = {}
    for e in sorted(entries, key=lambda e: (e.get("week") or 0, e.get("day") or 0)):
        found = best_set(e)
        if not found:
            continue
        ex = e.get("exercise_id")
        names[ex] = e.get("exercise_name") or ex
        first.setdefault(ex, found[0])
        best[ex] = max(best.get(ex, 0.0), found[0])
    progressed = sorted(
        ({"exercise": names[ex], "change_percent": round((best[ex] / first[ex] - 1) * 100)}
         for ex in best if first.get(ex) and best[ex] > first[ex] * 1.01),
        key=lambda r: -r["change_percent"])
    previous_block = int((plan.get("user_summary") or {}).get("block") or 1)
    return {
        "block": previous_block,
        "plan_id": plan.get("plan_id"),
        "sessions_logged": len(sessions),
        "sessions_planned": planned,
        "adherence": round(adherence, 2),
        "progress": adherence >= _ADHERENCE_TO_PROGRESS,
        "exercises_measured": len(best),
        "progressed": progressed[:5],
    }


def fingerprint(entries) -> str:
    """Changes whenever a set is logged or edited, so the plan cache — which
    otherwise keys on profile and preferences — rebuilds a plan whose loads come
    from logs that have since moved."""
    stamps = sorted(str(e.get("updated_at") or "") for e in entries or [])
    return f"{len(stamps)}:{stamps[-1] if stamps else ''}"


def recent_cutoff(now: datetime | None = None) -> datetime:
    return (now or datetime.now(timezone.utc)) - timedelta(days=RECENT_DAYS)


# A plan regenerated in its first fortnight — new equipment, a changed goal — is
# a correction, not a finished block, and "you logged 2 of 12 sessions" would be
# a false account of it. A block counts as finished three weeks after it was
# written, or once anything in its third week is logged.
_BLOCK_DAYS = 21


def _block_finished(record: dict, plan: dict | None, entries) -> bool:
    if not plan:
        return False
    generated = record.get("generated_at")
    if isinstance(generated, datetime):
        if generated.tzinfo is None:
            generated = generated.replace(tzinfo=timezone.utc)
        if datetime.now(timezone.utc) - generated >= timedelta(days=_BLOCK_DAYS):
            return True
    return any(e.get("plan_id") == plan.get("plan_id") and (e.get("week") or 0) >= 3
               for e in entries)


async def gym_history(db, user_id: str) -> dict:
    """Everything plan generation needs from the log, in one read.

    {logged_lifts, previous_block, fingerprint}. Never raises: a logging outage
    must not stop someone getting a plan — it gets the estimate instead."""
    try:
        cursor = db.workout_logs.find(
            {"user_id": user_id, "updated_at": {"$gte": recent_cutoff()}})
        entries = [e async for e in cursor]
        previous = await db.plan_history.find_one(
            {"user_id": user_id, "plan_type": "gym"}, sort=[("generated_at", -1)])
        prev_plan = None
        if previous:
            data = previous.get("plan_data") or {}
            prev_plan = data.get("gym_plan") or data
        summary = None
        if entries and previous and _block_finished(previous, prev_plan, entries):
            summary = block_summary(prev_plan, entries)
        return {"logged_lifts": logged_lifts(entries), "previous_block": summary,
                "fingerprint": fingerprint(entries)}
    except Exception:  # noqa: BLE001
        return {"logged_lifts": {}, "previous_block": None, "fingerprint": "unavailable"}
