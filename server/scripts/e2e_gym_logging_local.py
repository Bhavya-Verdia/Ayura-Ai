"""Gym logging end to end, against a real backend and a real (local) database.

The Playwright spec drives the logger through a mocked API, and the unit tests
call `workout_log` directly. Neither shows that a set posted over HTTP lands in
Mongo, comes back on the next plan, and moves the next block's loads. This
does, through the same routes the app calls.

It refuses to run unless the API and the database are both on localhost. The
root .env points at the production database, and this script writes users.

    mongod --dbpath /tmp/ayura-e2e --port 27099
    env MONGO_URL=mongodb://127.0.0.1:27099/ayura_local_e2e JWT_SECRET_KEY=local-e2e-only \\
        AZURE_OPENAI_API_KEY= GEMINI_API_KEY= REDIS_URL= TRUSTED_HOSTS=127.0.0.1,localhost \\
        RATE_LIMIT_ENABLED=false python -m uvicorn main:app --port 8099
    python scripts/e2e_gym_logging_local.py \\
        --api http://127.0.0.1:8099 --mongo mongodb://127.0.0.1:27099/ayura_local_e2e \\
        --jwt-secret local-e2e-only
"""
import argparse
import re
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import jwt
from pymongo import MongoClient

_LOCAL = {"127.0.0.1", "localhost"}


def _check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        _check.failed += 1


_check.failed = 0


def _kg(weight_range: str) -> float | None:
    m = re.search(r"(\d+(?:\.\d+)?)\s*(?:-|–)\s*(\d+(?:\.\d+)?)\s*kg", weight_range or "")
    return (float(m.group(1)) + float(m.group(2))) / 2 if m else None


def _rows(plan, week):
    for day in plan["four_week_plan"][week - 1]["days"]:
        for ex in day.get("main_workout") or []:
            yield day["day"], ex


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--mongo", required=True)
    ap.add_argument("--jwt-secret", required=True)
    a = ap.parse_args()
    if urlparse(a.api).hostname not in _LOCAL or urlparse(a.mongo).hostname not in _LOCAL:
        sys.exit("refusing: --api and --mongo must both be localhost")

    db = MongoClient(a.mongo).get_default_database()
    uid = f"e2e-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "_id": uid, "email": f"{uid}@e2e.local", "name": "E2E Lifter", "auth_provider": "local",
        "is_verified": True, "onboarding_complete": True, "gender": "male", "age": 30,
        "height_cm": 178, "weight_kg": 80, "bmi": 25.2, "bmi_category": "normal",
        "dominant_dosha": "vata", "fitness_level": "intermediate", "activity_level": "moderate",
        "medical_history": [], "created_at": now, "updated_at": now,
    })
    token = jwt.encode({"sub": uid, "email": f"{uid}@e2e.local", "type": "access",
                        "onboarding_complete": True,
                        "exp": now + timedelta(hours=1)}, a.jwt_secret, algorithm="HS256")
    c = httpx.Client(base_url=a.api, cookies={"ayura_access": token}, timeout=120)

    try:
        r = c.post("/api/preferences/gym", json={
            "gym_goal": "strength", "workout_days_per_week": 3, "workout_duration_minutes": 60,
            "available_equipment": ["bodyweight", "barbell", "dumbbells"],
            "strength_level": "intermediate", "cardio_preference": "light",
            "target_muscle_focus": "full_body"})
        _check(r.status_code == 200, f"save gym preferences ({r.status_code})")

        r = c.post("/api/plans/gym", json={})
        _check(r.status_code == 200, f"generate block 1 ({r.status_code})")
        plan1 = r.json()
        pid = plan1["plan_id"]
        _check(bool(db.plan_history.find_one({"_id": pid, "user_id": uid})),
               "block 1 is stored under the plan_id the client logs against")

        squat = next(ex for _, ex in _rows(plan1, 1) if ex["exercise_id"] == "barbell_squat")
        est = _kg(squat.get("weight_range"))
        print(f"     block 1 squat: {squat['sets']} x {squat['reps']} @ {squat.get('weight_range')}")

        # Bad input is refused, not stored.
        r = c.post("/api/workouts/logs", json={"plan_id": "not-mine", "week": 1, "day": 1,
                                               "exercise_id": "barbell_squat", "sets": [{"kg": 100, "reps": 5}]})
        _check(r.status_code == 404, f"a plan id the user does not own is refused ({r.status_code})")
        r = c.post("/api/workouts/logs", json={"plan_id": pid, "week": 1, "day": 1,
                                               "exercise_id": "made_up_lift", "sets": [{"kg": 100, "reps": 5}]})
        _check(r.status_code == 422, f"an unknown exercise is refused ({r.status_code})")
        r = c.post("/api/workouts/logs", json={"plan_id": pid, "week": 5, "day": 1,
                                               "exercise_id": "barbell_squat", "sets": []})
        _check(r.status_code == 422, f"week 5 of a 4-week block is refused ({r.status_code})")

        # Log weeks 1-3 of every rep-range lift at the bottom of its range, squatting
        # well above the estimate.
        heavy = round((est or 100) * 1.25 / 2.5) * 2.5
        posted = 0
        for week in (1, 2, 3):
            for day, ex in _rows(plan1, week):
                if not re.fullmatch(r"\d+\s*-\s*\d+", str(ex.get("reps", ""))):
                    continue
                low = int(str(ex["reps"]).split("-")[0])
                kg = heavy if ex["exercise_id"] == "barbell_squat" else (_kg(ex.get("weight_range")) or 0)
                r = c.post("/api/workouts/logs", json={
                    "plan_id": pid, "week": week, "day": day, "exercise_id": ex["exercise_id"],
                    "sets": [{"kg": kg, "reps": low}] * int(ex["sets"]), "effort": "right"})
                posted += r.status_code == 200
        stored = db.workout_logs.count_documents({"user_id": uid, "plan_id": pid})
        _check(posted > 0 and stored == posted, f"{posted} logs posted, {stored} stored")

        r = c.get("/api/workouts/logs", params={"plan_id": pid})
        _check(len(r.json()["logs"]) == stored, "the logs read back over HTTP")
        summary = c.get("/api/workouts/summary", params={"plan_id": pid}).json()
        print(f"     summary: {summary['sessions_logged']}/{summary['sessions_planned']} sessions, "
              f"progress={summary['progress']}")
        _check(summary["progress"] is True, "three logged weeks count as a finished block")

        # Editing a log to no sets deletes it.
        first_day, first_ex = next(_rows(plan1, 1))
        r = c.post("/api/workouts/logs", json={"plan_id": pid, "week": 1, "day": first_day,
                                               "exercise_id": first_ex["exercise_id"], "sets": []})
        _check(r.json().get("deleted") is True
               and db.workout_logs.count_documents({"user_id": uid, "plan_id": pid}) == stored - 1,
               "clearing a log removes it")

        # The next block is built from the log.
        r = c.post("/api/plans/gym", json={})
        plan2 = r.json()
        _check(plan2["plan_id"] != pid, "logging busts the plan cache: a new block is built")
        _check((plan2.get("user_summary") or {}).get("block") == 2, "it is block 2")
        _check(bool(plan2.get("block_notice")), f"block notice: {plan2.get('block_notice')!r}")
        squat2 = next(ex for _, ex in _rows(plan2, 1) if ex["exercise_id"] == "barbell_squat")
        est2 = _kg(squat2.get("weight_range"))
        print(f"     block 2 squat: {squat2['sets']} x {squat2['reps']} @ {squat2.get('weight_range')}"
              f" ({squat2.get('load_basis') or squat2.get('notes') or ''})")
        _check(est and est2 and est2 > est * 1.1,
               f"the logged squat ({heavy} kg) moved the estimate: {est} -> {est2} kg")
        _check("log" in str(squat2).lower(), "the load says it came from the log")

        # Erasure reaches the logs.
        r = c.delete("/api/privacy/account")
        _check(r.status_code == 200, f"delete account ({r.status_code})")
        _check(db.workout_logs.count_documents({"user_id": uid}) == 0, "no workout log survives erasure")
    finally:
        db.users.delete_one({"_id": uid})
        for coll in ("plan_history", "workout_logs", "user_preferences", "audit_log", "notifications"):
            db[coll].delete_many({"user_id": uid})

    print(f"\n{_check.failed} failed")
    sys.exit(1 if _check.failed else 0)


if __name__ == "__main__":
    main()
