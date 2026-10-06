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


# ── The long view: every block, not the last six weeks ───────────────────────
#
# `gym_history` reads 42 days of logs, which is right for a load (a set from
# March says little about May) and wrong for anything about training AGE. Three
# months of consistent blocks is what moves a beginner on, and by month three
# the first month had dropped out of the window. Block history reads every gym
# plan the person has had, against every set logged on it.

_HISTORY_PLANS = 24          # two years of monthly blocks
# Consistent blocks before a beginner is offered intermediate programming. Three
# four-week blocks is the twelve weeks over which novice linear progression
# ordinarily runs out (Rippetoe & Baker, Practical Programming, 3rd ed.).
LEVEL_UP_AFTER_BLOCKS = 3
_ADULT_FROM = 18


async def block_history(db, user_id: str) -> list[dict]:
    """One row per gym plan that had anything logged, oldest first.

    Each row is `block_summary` plus `best_lifts` ({exercise_id: {name, one_rm,
    source}}) and `finished`. Plans regenerated before a set was logged — form
    corrections — are skipped: they are not blocks anyone trained."""
    records = [r async for r in db.plan_history.find(
        {"user_id": user_id, "plan_type": "gym"}).sort("generated_at", -1).limit(_HISTORY_PLANS)]
    records.reverse()
    if not records:
        return []
    ids = [r.get("_id") for r in records]
    entries = [e async for e in db.workout_logs.find({"user_id": user_id, "plan_id": {"$in": ids}})]
    by_plan: dict = {}
    for e in entries:
        by_plan.setdefault(e.get("plan_id"), []).append(e)

    rows = []
    for i, record in enumerate(records):
        logs = by_plan.get(record.get("_id")) or []
        if not logs:
            continue
        data = record.get("plan_data") or {}
        plan = dict(data.get("gym_plan") or data)
        # The log's plan_id is the record's id; the plan body may carry its own.
        plan["plan_id"] = record.get("_id")
        summary = block_summary(plan, logs)
        lifts = logged_lifts(logs)
        names = {e.get("exercise_id"): e.get("exercise_name") for e in logs}
        is_latest = i == len(records) - 1
        generated = record.get("generated_at")
        rows.append({
            **summary,
            "generated_at": generated.isoformat() if isinstance(generated, datetime) else generated,
            "finished": (not is_latest) or _block_finished(record, plan, logs),
            "best_lifts": {k: {**v, "name": names.get(k) or k} for k, v in lifts.items()},
        })
    return rows


def consecutive_progressed(history: list[dict]) -> int:
    """Finished blocks in a row, most recent backwards, that were mostly done."""
    n = 0
    for row in reversed([r for r in history if r.get("finished")]):
        if not row.get("progress"):
            break
        n += 1
    return n


def level_up_offer(history: list[dict], profile: dict) -> dict | None:
    """Whether to offer a beginner intermediate programming, and why.

    An OFFER, never a change: the level decides the split and which movements
    are prescribed, and the person accepts it. Not made to anyone under 18
    (youth programming stays whole-body), in pregnancy, or without evidence —
    at least one lift that measurably went up across the run."""
    level = str((profile or {}).get("fitness_level") or "beginner").lower()
    if level != "beginner" or (profile or {}).get("pregnancy_or_nursing"):
        return None
    try:
        if int((profile or {}).get("age") or 0) < _ADULT_FROM:
            return None
    except (TypeError, ValueError):
        return None
    run = consecutive_progressed(history)
    if run < LEVEL_UP_AFTER_BLOCKS:
        return None
    window = [r for r in history if r.get("finished")][-run:]
    first, last = window[0].get("best_lifts") or {}, window[-1].get("best_lifts") or {}
    gains = sorted(
        ({"exercise": last[k]["name"],
          "change_percent": round((last[k]["one_rm"] / first[k]["one_rm"] - 1) * 100)}
         for k in last if k in first and first[k].get("one_rm")
         and last[k]["one_rm"] > first[k]["one_rm"] * 1.01),
        key=lambda g: -g["change_percent"])
    if not gains:
        return None
    return {"to": "intermediate", "blocks": run, "gains": gains[:3],
            "reason": (f"You have finished {run} blocks in a row and your lifts went up across "
                       "them. Intermediate programming splits the week so each session can "
                       "do more for fewer muscles, and prescribes harder movements.")}


# ── The end of a block, said to the person ───────────────────────────────────
#
# Week four was the last page of the plan and nothing came after it: someone
# who did not think to press "regenerate" repeated the deload week indefinitely.
# Once a plan is four weeks old, and is still the latest gym plan, one
# notification says the block is done.

_BLOCK_LENGTH_DAYS = 28
# A plan older than this was abandoned rather than finished; a notification
# about it a year later is noise.
_NOTIFY_WINDOW_DAYS = 10


async def notify_finished_blocks(db, now: datetime | None = None) -> int:
    from services.notification_service import create_and_deliver_notification

    now = now or datetime.now(timezone.utc)
    due_before = now - timedelta(days=_BLOCK_LENGTH_DAYS)
    due_after = due_before - timedelta(days=_NOTIFY_WINDOW_DAYS)
    sent = 0
    async for record in db.plan_history.find({
            "plan_type": "gym", "block_end_notified": {"$exists": False},
            "generated_at": {"$lte": due_before, "$gte": due_after}}):
        user_id = record.get("user_id")
        newer = await db.plan_history.find_one({
            "user_id": user_id, "plan_type": "gym",
            "generated_at": {"$gt": record.get("generated_at")}}, {"_id": 1})
        if not newer:
            data = record.get("plan_data") or {}
            plan = data.get("gym_plan") or data
            block = int((plan.get("user_summary") or {}).get("block") or 1)
            logs = [e async for e in db.workout_logs.find(
                {"user_id": user_id, "plan_id": record.get("_id")})]
            summary = block_summary({**plan, "plan_id": record.get("_id")}, logs) or {}
            if summary.get("progress"):
                body = (f"You logged {summary['sessions_logged']} of "
                        f"{summary['sessions_planned']} sessions. Block {block + 1} is ready "
                        "to build on it — open your gym plan to start it.")
            else:
                body = ("Your four weeks are up. Open your gym plan to start the next block — "
                        "it will repeat this one's structure until more of it is logged.")
            try:
                await create_and_deliver_notification(
                    db, user_id=user_id, title=f"Gym block {block} complete", body=body,
                    notif_type="reminder", url="/dashboard")
                sent += 1
            except Exception:  # noqa: BLE001 — one user's delivery must not stop the rest
                continue
        # Marked either way: a superseded plan is never due again.
        await db.plan_history.update_one({"_id": record.get("_id")},
                                         {"$set": {"block_end_notified": now}})
    return sent
