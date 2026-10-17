"""Streaks and badges.

What these hold: a day is counted in the user's timezone; a streak is alive until the
day after a gap; an earned badge is never taken back; editing an old log does not move
its credit; and nothing is ever rewarded for an outcome or an intensity.
"""
import asyncio
from datetime import date, datetime, timedelta, timezone
from types import SimpleNamespace

import pytest

from services import rewards
from services.rewards import BADGES, evaluate, local_date, record_activity, streaks


# ── A small in-memory stand-in for the Motor collections rewards uses ─────────

class _Cursor:
    def __init__(self, docs):
        self._docs = docs

    def __aiter__(self):
        self._it = iter(self._docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def _match(doc, flt):
    for k, v in flt.items():
        if isinstance(v, dict) and "$gte" in v:
            if not (isinstance(doc.get(k), datetime) and doc[k] >= v["$gte"]):
                return False
        elif doc.get(k) != v:
            return False
    return True


class _Coll:
    def __init__(self):
        self.docs = []

    def find(self, flt=None, projection=None):
        return _Cursor([d for d in self.docs if _match(d, flt or {})])

    async def find_one(self, flt, projection=None):
        return next((d for d in self.docs if _match(d, flt)), None)

    async def count_documents(self, flt):
        return sum(1 for d in self.docs if _match(d, flt))

    async def insert_one(self, doc):
        self.docs.append(dict(doc))

    async def update_one(self, flt, update, upsert=False):
        doc = next((d for d in self.docs if _match(d, flt)), None)
        if doc is None:
            if not upsert:
                return
            doc = dict(flt)
            doc.update(update.get("$setOnInsert", {}))
            self.docs.append(doc)
        doc.update(update.get("$set", {}))
        for k, v in update.get("$addToSet", {}).items():
            doc.setdefault(k, [])
            if v not in doc[k]:
                doc[k].append(v)

    async def update_many(self, flt, update):
        for d in self.docs:
            if _match(d, flt):
                d.update(update.get("$set", {}))


class _DB:
    def __getattr__(self, name):
        coll = _Coll()
        setattr(self, name, coll)
        return coll


def _user(**kw):
    base = dict(id="u1", timezone="Asia/Kolkata", best_streak=0, prakriti_locked=False, dosha_scores=None)
    base.update(kw)
    return SimpleNamespace(**base)


def _run(coro):
    return asyncio.run(coro)


NOW = datetime(2026, 10, 17, 6, 0, tzinfo=timezone.utc)  # 11:30 in India


# ── Days and streaks ────────────────────────────────────────────────────────

def test_the_day_is_the_users_not_the_servers():
    # 20:00 UTC is 01:30 the next morning in India
    late = datetime(2026, 10, 16, 20, 0, tzinfo=timezone.utc)
    assert local_date(late, "Asia/Kolkata") == date(2026, 10, 17)
    assert local_date(late, None) == date(2026, 10, 16)


def test_a_streak_survives_until_the_day_after_a_gap():
    today = date(2026, 10, 17)
    days = {today - timedelta(days=i) for i in range(1, 4)}  # yesterday and two before
    s = streaks(days, today)
    assert s["current"] == 3 and not s["today_active"]   # alive at 07:00 before a log
    assert streaks(days - {today - timedelta(days=1)}, today)["current"] == 0


def test_best_is_the_longest_run_anywhere():
    today = date(2026, 10, 17)
    old_run = {date(2026, 9, 1) + timedelta(days=i) for i in range(9)}
    s = streaks(old_run | {today}, today)
    assert s["best"] == 9 and s["current"] == 1


# ── Evaluation ──────────────────────────────────────────────────────────────

def test_logging_earns_badges_once_and_announces_them_once():
    db = _DB()
    for i in range(3):
        _run(record_activity(db, "u1", "Asia/Kolkata", "meal", now=NOW - timedelta(days=i)))
    out = _run(evaluate(db, _user(), now=NOW))
    earned = {b["id"] for b in out["badges"] if b["earned"]}
    assert {"first_meal", "streak_3"} <= earned
    assert set(out["new"]) == earned
    assert out["streak"]["current"] == 3 and out["streak"]["today_active"]
    assert len(db.notifications.docs) == len(earned)

    _run(db.user_badges.update_many({"user_id": "u1", "seen_at": None}, {"$set": {"seen_at": NOW}}))
    again = _run(evaluate(db, _user(best_streak=3), now=NOW))
    assert again["new"] == []
    assert len(db.notifications.docs) == len(earned)   # not re-announced


def test_an_earned_badge_is_kept_after_its_evidence_is_gone():
    db = _DB()
    for i in range(3):
        _run(record_activity(db, "u1", "Asia/Kolkata", "meal", now=NOW - timedelta(days=i)))
    _run(evaluate(db, _user(), now=NOW))
    db.activity_days.docs.clear()
    later = _run(evaluate(db, _user(), now=NOW + timedelta(days=30)))
    assert next(b for b in later["badges"] if b["id"] == "streak_3")["earned"]


def test_editing_an_old_log_does_not_move_its_day():
    """Meal logs are edited in place, so updated_at moves; the day recorded at the
    time of logging keeps the original day's credit."""
    db = _DB()
    monday = NOW - timedelta(days=2)
    _run(record_activity(db, "u1", "Asia/Kolkata", "meal", now=monday))
    db.meal_logs.docs.append({"user_id": "u1", "updated_at": NOW, "week": 1})  # edited today
    out = _run(evaluate(db, _user(), now=NOW))
    active = {d["date"] for d in out["streak"]["last7"] if d["active"]}
    assert local_date(monday, "Asia/Kolkata").isoformat() in active


def test_logs_from_before_activity_days_existed_still_count():
    db = _DB()
    for i in range(7):
        db.progress_logs.docs.append({"user_id": "u1", "date": NOW - timedelta(days=i)})
    out = _run(evaluate(db, _user(), now=NOW))
    assert out["streak"]["current"] == 7
    assert next(b for b in out["badges"] if b["id"] == "streak_7")["earned"]


def test_the_assessment_and_a_first_plan_are_badges():
    db = _DB()
    db.plan_history.docs.append({"user_id": "u1"})
    out = _run(evaluate(db, _user(prakriti_locked=True), now=NOW))
    earned = {b["id"] for b in out["badges"] if b["earned"]}
    assert {"prakriti", "first_plan"} <= earned


def test_next_badge_is_the_closest_one():
    db = _DB()
    for i in range(5):
        _run(record_activity(db, "u1", "Asia/Kolkata", "practice", now=NOW - timedelta(days=i)))
    out = _run(evaluate(db, _user(), now=NOW))
    assert out["next"]["id"] == "streak_7"
    assert out["next"]["progress"] == {"have": 5, "need": 7}


def test_a_broken_streak_is_told_gently():
    db = _DB()
    for i in range(5, 10):
        _run(record_activity(db, "u1", "Asia/Kolkata", "meal", now=NOW - timedelta(days=i)))
    msg = _run(evaluate(db, _user(), now=NOW))["streak"]["message"]
    assert "best run is 5 days" in msg and "new one" in msg


def test_record_activity_never_raises():
    class Broken:
        @property
        def activity_days(self):
            raise RuntimeError("mongo down")
    _run(record_activity(Broken(), "u1", None, "meal"))


# ── What is never rewarded ──────────────────────────────────────────────────

_OUTCOME_WORDS = ("weight", "kg", "calorie", "kcal", "fast", "lose", "lost", "burn", "volume",
                  "heavier", "intensity", "sets")


def test_no_badge_rewards_an_outcome_or_an_intensity():
    """A streak of fasting days or of training through a warning sign is the badge a
    health app must not offer."""
    for b in BADGES:
        text = f"{b['id']} {b['title']} {b['desc']} {b['measure']}".lower()
        assert not any(w in text for w in _OUTCOME_WORDS), b["id"]


def test_every_badge_measure_is_one_the_evaluator_computes():
    db = _DB()
    ev, _ = _run(rewards._evidence(db, _user(), "Asia/Kolkata", date(2026, 10, 17)))
    for b in BADGES:
        assert b["measure"] in ev, b["id"]


def test_every_logging_route_records_activity():
    """A route that logs without recording would make that kind of logging count only
    until its first edit."""
    from pathlib import Path
    routes = Path(__file__).resolve().parents[1] / "routes"
    for name, kinds in {"progress.py": ["progress"], "meals.py": ["meal", "checkin"],
                        "workouts.py": ["workout", "checkin"], "practice.py": ["practice"],
                        "checkin.py": ["checkin"]}.items():
        src = (routes / name).read_text()
        for k in kinds:
            assert f'record_activity(db, user.id, user.timezone, "{k}")' in src, (name, k)


@pytest.mark.parametrize("bid", sorted({b["id"] for b in BADGES}))
def test_badges_have_an_icon_the_client_maps(bid):
    from pathlib import Path
    client = (Path(__file__).resolve().parents[2] / "client" / "src" / "components"
              / "RewardsBadges.jsx").read_text()
    icon = next(b["icon"] for b in BADGES if b["id"] == bid)
    assert icon in client, f"{bid}: icon {icon} is not imported by RewardsBadges.jsx"
