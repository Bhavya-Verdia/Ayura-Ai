"""Synthetic signup monitor: does a new user get through onboarding right now?

Run inside the API container by .github/workflows/monitor.yml:

    docker compose exec -T api python scripts/synthetic_signup_check.py

Nobody completed onboarding from 2026-09-22 to 2026-10-18 and nothing said so:
the server was healthy, every test passed, and the save failed only for the
input Chrome in India sends (Asia/Calcutta). This walks the same path a new user
does, through the public URL (nginx, TLS and all), with that payload:

    register -> verify -> login -> onboarding -> Prakriti assessment -> profile -> delete

It mints the verification token itself (it runs where the secret lives), so no
inbox is involved, and it always deletes its account, including any a crashed
earlier run left behind. The address is @example.com, which email_service never
sends to. Prints one JSON line; exits 1 on the first failing step.
"""
import json
import os
import sys
import time
import uuid
from datetime import datetime, timedelta, timezone

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import httpx  # noqa: E402

from config import settings  # noqa: E402
from engine.dosha_analyzer import _TRAIT_WEIGHTS  # noqa: E402
from services.auth_service import create_access_token, create_verification_token  # noqa: E402

BASE = os.environ.get("SYNTHETIC_BASE_URL", "https://ayuraai.in/api").rstrip("/")
PREFIX = "synthetic-monitor-"
DOMAIN = "@example.com"

# What Onboarding.jsx sends, with the timezone Chrome reports in India.
ONBOARDING = {
    "name": "Synthetic Monitor", "gender": "female", "age": 34, "height_cm": 162, "weight_kg": 64,
    "medical_history": ["acidity"], "current_symptoms": ["heartburn_acidity"], "allergies": ["dairy"],
    "current_medications": [], "goal": "general_wellness", "dominant_dosha": "pitta",
    "pregnancy_or_nursing": False, "fitness_level": "beginner", "activity_level": "light",
    # SYNTHETIC_TIMEZONE exists to prove the check fails the way the real bug did.
    "timezone": os.environ.get("SYNTHETIC_TIMEZONE", "Asia/Calcutta"),
}


class StepFailed(Exception):
    pass


def _expect(r: httpx.Response, step: str, codes=(200, 201)):
    if r.status_code not in codes:
        raise StepFailed(f"{step}: HTTP {r.status_code} {r.text[:300]}")
    return r


def _delete_with_token(user_id: str, email: str) -> int:
    token = create_access_token(user_id, email)
    return httpx.delete(f"{BASE}/privacy/account", cookies={settings.ACCESS_TOKEN_COOKIE: token},
                        headers={"Origin": settings.FRONTEND_URL}, timeout=30).status_code


def sweep_leftovers() -> int:
    """Delete synthetic accounts an earlier, crashed run left behind."""
    try:
        from pymongo import MongoClient
        db = MongoClient(settings.MONGO_URL, serverSelectionTimeoutMS=5000)[settings.MONGO_DB]
        cutoff = datetime.now(timezone.utc) - timedelta(minutes=30)
        stale = list(db.users.find({"email": {"$regex": f"^{PREFIX}.*{DOMAIN.replace('.', '[.]')}$"},
                                    "created_at": {"$lt": cutoff}}, {"_id": 1, "email": 1}))
        return sum(_delete_with_token(u["_id"], u["email"]) == 200 for u in stale)
    except Exception:
        return 0


def main() -> int:
    email = f"{PREFIX}{uuid.uuid4().hex[:10]}{DOMAIN}"
    password = f"Synthetic!{uuid.uuid4().hex[:12]}"
    timings: dict[str, float] = {}
    result = {"ok": False, "base": BASE, "at": datetime.now(timezone.utc).isoformat(timespec="seconds")}
    c = httpx.Client(timeout=90, headers={"Origin": settings.FRONTEND_URL})
    user_id = None

    def step(name, fn):
        t = time.monotonic()
        out = fn()
        timings[name] = round(time.monotonic() - t, 2)
        return out

    try:
        step("register", lambda: _expect(c.post(f"{BASE}/auth/register", json={
            "name": "Synthetic Monitor", "email": email, "password": password, "consent_given": True}), "register"))
        step("verify", lambda: _expect(c.post(f"{BASE}/auth/verify-email",
                                              json={"token": create_verification_token(email)}), "verify"))
        login = step("login", lambda: _expect(c.post(f"{BASE}/auth/login",
                                                     json={"email": email, "password": password}), "login"))
        user_id = login.json().get("user_id")
        step("onboarding", lambda: _expect(c.put(f"{BASE}/profile/me", json=ONBOARDING), "onboarding"))
        traits = {t: "pitta" for t in _TRAIT_WEIGHTS}
        step("assessment", lambda: _expect(c.post(f"{BASE}/profile/dosha-assessment", json={
            "physical_traits": traits, "current_symptoms": ["heartburn_acidity"], "medical_history": ["acidity"]}),
            "assessment"))
        me = step("profile", lambda: _expect(c.get(f"{BASE}/profile/me"), "profile")).json()
        if not me.get("onboarding_complete"):
            raise StepFailed("profile: onboarding_complete is not true after a successful save")
        if me.get("dominant_dosha") != "pitta" or not me.get("dosha_scores"):
            raise StepFailed(f"profile: assessment not stored (dominant={me.get('dominant_dosha')})")
        result["ok"] = True
    except StepFailed as e:
        result["failed"] = str(e)
    except Exception as e:  # network, DNS, TLS: the path a user takes is broken too
        result["failed"] = f"{type(e).__name__}: {e}"[:400]
    finally:
        try:
            gone = c.delete(f"{BASE}/privacy/account").status_code
            if gone != 200 and user_id:
                gone = _delete_with_token(user_id, email)
        except Exception:
            gone = "error"
        result["account_deleted"] = gone == 200
        result["leftovers_swept"] = sweep_leftovers()
        result["timings_s"] = timings
    print(json.dumps(result))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    sys.exit(main())
