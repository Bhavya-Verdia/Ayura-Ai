"""The diet plan's week, end to end, against a real backend and a real (local) database:
another dish in place of a meal, the weekly check-in, and the rebuild of the weeks
still to come — through the routes the app calls, landing in Mongo, and served back
by the plan endpoint without a new generation.

The unit tests call the services directly; this shows the stored plan is the one
that changed. Run it with no LLM keys: the plan is the rule engine's, and the rebuild
composes its weeks the same way, so nothing is billed.

It refuses to run unless the API and the database are both on localhost. The root
.env points at the production database, and this script writes users.

    mongod --dbpath /tmp/ayura-e2e --port 27099
    env MONGO_URL=mongodb://127.0.0.1:27099/ayura_local_e2e MONGO_DB=ayura_local_e2e \\
        JWT_SECRET_KEY=local-e2e-only SENTRY_DSN= VAPID_PRIVATE_KEY= \\
        AZURE_OPENAI_API_KEY= GEMINI_API_KEY= REDIS_URL= TRUSTED_HOSTS=127.0.0.1,localhost \\
        RATE_LIMIT_ENABLED=false python -m uvicorn main:app --port 8099
    python scripts/e2e_diet_week_local.py \\
        --api http://127.0.0.1:8099 --mongo mongodb://127.0.0.1:27099/ayura_local_e2e \\
        --jwt-secret local-e2e-only
"""
import argparse
import sys
import uuid
from datetime import datetime, timedelta, timezone
from urllib.parse import urlparse

import httpx
import jwt
from pymongo import MongoClient

_LOCAL = {"127.0.0.1", "localhost"}
_SLOTS = ("breakfast", "lunch", "snack", "dinner")


def _check(cond, label):
    print(("PASS " if cond else "FAIL ") + label)
    if not cond:
        _check.failed += 1


_check.failed = 0


def _foods(weeks, numbers):
    return {c["food"] for w in weeks if w["week_number"] in numbers
            for d in w["daily_plan"].values() for s in _SLOTS
            for c in (d.get(s) or {}).get("components") or []}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--api", required=True)
    ap.add_argument("--mongo", required=True)
    ap.add_argument("--jwt-secret", required=True)
    ap.add_argument("--days-in", type=int, default=9,
                    help="backdate the plan this many days, so week 2 is under way")
    ap.add_argument("--keep", action="store_true", help="leave the user in place (for a UI check)")
    a = ap.parse_args()
    if urlparse(a.api).hostname not in _LOCAL or urlparse(a.mongo).hostname not in _LOCAL:
        sys.exit("refusing: --api and --mongo must both be localhost")

    db = MongoClient(a.mongo).get_default_database()
    uid = f"e2e-{uuid.uuid4().hex[:8]}"
    now = datetime.now(timezone.utc)
    db.users.insert_one({
        "_id": uid, "email": f"{uid}@e2e.local", "name": "E2E Diner", "auth_provider": "local",
        "is_verified": True, "onboarding_complete": True, "gender": "female", "age": 34,
        "height_cm": 162, "weight_kg": 60, "bmi": 22.9, "bmi_category": "normal",
        "dominant_dosha": "vata", "agni_type": "sama", "activity_level": "moderate",
        "medical_history": [], "created_at": now, "updated_at": now,
    })
    token = jwt.encode({"sub": uid, "email": f"{uid}@e2e.local", "type": "access",
                        "onboarding_complete": True,
                        "exp": now + timedelta(hours=3)}, a.jwt_secret, algorithm="HS256")
    c = httpx.Client(base_url=a.api, cookies={"ayura_access": token}, timeout=300)

    try:
        r = c.post("/api/preferences/diet", json={
            "diet_goal": "general_wellness", "dietary_type": "vegan",
            "intermittent_fasting": "16:8", "cuisine_preference": "south_indian"})
        _check(r.status_code == 200, f"save diet preferences ({r.status_code})")
        r = c.post("/api/plans/diet", json={})
        _check(r.status_code == 200, f"generate the plan ({r.status_code})")
        plan = r.json()
        pid = plan["plan_id"]

        # The screened frame: a vegan Vata on 16:8.
        mt = plan.get("meal_timing") or {}
        _check(mt.get("eating_window") == "10:00 AM – 6:00 PM", f"16:8 window ({mt.get('eating_window')})")
        _check(mt.get("bedtime_drink") is None, "no bedtime drink inside a fasting window")
        rituals = {x["food"] for r_ in plan.get("daily_rituals") or [] for x in r_["components"]}
        _check("milk_full_fat" not in rituals, f"no dairy in a vegan's drinks ({sorted(rituals)})")
        day = plan["diet_weeks"][0]["daily_plan"]["Monday"]
        _check(bool(day.get("rituals")), "the drinks are on every day, and counted")

        # Backdate, so the plan is nine days old: week 2 is the current week.
        then = now - timedelta(days=a.days_in)
        db.plan_history.update_one({"_id": pid}, {"$set": {
            "generated_at": then, "plan_data.diet_plan.generated_at": then.isoformat()}})

        # Another dish, and back.
        before = day["lunch"]["meal_name"]
        r = c.post("/api/meals/replace", json={"plan_id": pid, "week": 1, "day": "Monday",
                                               "slot": "lunch"})
        _check(r.status_code == 200, f"replace a meal ({r.status_code} {r.text[:120]})")
        if r.status_code == 200:
            new = r.json()["day"]["lunch"]
            _check(new["meal_name"] != before, f"a different dish ({before} -> {new['meal_name']})")
            stored = db.plan_history.find_one({"_id": pid})["plan_data"]["diet_plan"]
            _check(stored["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["meal_name"]
                   == new["meal_name"], "the stored plan holds the new dish")
            r = c.post("/api/meals/replace", json={"plan_id": pid, "week": 1, "day": "Monday",
                                                   "slot": "lunch", "undo": True})
            _check(r.status_code == 200 and r.json()["day"]["lunch"]["meal_name"] == before,
                   "and back to the original")

        # The check-in.
        r = c.get("/api/meals/checkins", params={"plan_id": pid})
        _check(r.status_code == 200, f"read check-ins ({r.status_code})")
        offered = r.json()["week_foods"]["1"] if r.status_code == 200 else []
        _check(bool(offered), f"week 1's foods offered ({len(offered)})")
        week1 = plan["diet_weeks"][0]
        trouble = next((f["id"] for f in offered
                        if f["id"] in _foods([week1], {1}) and f["id"] not in ("water",)), None)
        r = c.post("/api/meals/checkins", json={
            "plan_id": pid, "week": 1, "hunger": "hungry", "digestion": ["bloating"],
            "trouble_foods": [{"food": trouble, "problem": "bloating"}]})
        _check(r.status_code == 200, f"save a check-in ({r.status_code} {r.text[:120]})")
        prop = r.json().get("proposal") or {}
        _check(prop.get("rebuild_available") and prop.get("from_week") == 2,
               f"proposes rebuilding weeks 2-4 ({prop})")

        # The rebuild.
        r = c.post("/api/plans/diet/rebuild", json={"plan_id": pid})
        _check(r.status_code == 200, f"rebuild weeks 2-4 ({r.status_code} {r.text[:160]})")
        if r.status_code == 200:
            rebuilt = r.json()
            _check(rebuilt["plan_id"] == pid, "same plan, same id")
            _check(rebuilt["diet_weeks"][0] == db.plan_history.find_one({"_id": pid})
                   ["plan_data"]["diet_plan"]["diet_weeks"][0], "week 1 stored as it was")
            _check(trouble not in _foods(rebuilt["diet_weeks"], {2, 3, 4}),
                   f"{trouble} is gone from weeks 2-4")
            _check("bloating" in rebuilt["user_summary"]["active_condition_protocols"],
                   "bloating is a protocol for the weeks to come")
            target = rebuilt["energy_prescription"]["target_calories"]
            _check(target == plan["energy_prescription"]["target_calories"] + 150,
                   f"hungry: +150 kcal ({plan['energy_prescription']['target_calories']} -> {target})")
            again = c.get("/api/meals/checkins", params={"plan_id": pid}).json()
            _check(not again["proposal"].get("rebuild_available"), "the rebuild is not offered twice")

            # Served back without a new generation.
            n = db.plan_history.count_documents({"user_id": uid, "plan_type": "diet"})
            r = c.post("/api/plans/diet", json={})
            _check(r.status_code == 200 and trouble not in _foods(r.json()["diet_weeks"], {2, 3, 4}),
                   "the plan endpoint serves the rebuilt plan")
            _check(db.plan_history.count_documents({"user_id": uid, "plan_type": "diet"}) == n,
                   "and did not generate a new one")
    finally:
        if not a.keep:
            for coll in ("users", "user_preferences", "plan_history", "meal_logs",
                         "diet_checkins", "usage_quota", "timeline", "audit_log"):
                db[coll].delete_many({"user_id": uid} if coll != "users" else {"_id": uid})
        else:
            print(f"kept user {uid}; token:\n{token}")
    print(f"\n{_check.failed} failed")
    sys.exit(1 if _check.failed else 0)


if __name__ == "__main__":
    main()
