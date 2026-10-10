"""The end-of-week diet check-in (`services/diet_checkin`) and the rebuild of the
weeks still to come (`diet_llm_generator.rebuild_diet_weeks`)."""
import hashlib
import json
from datetime import datetime, timedelta, timezone

import pytest

import services.diet_llm_generator as gen
from services import diet_checkin as ck
from services import diet_log as dl
from services.diet_allowed_foods import allowed_foods
from services.diet_brief_builder import diet_conditions
from services.diet_energy import energy_target
from tests.diet_fake_llm import make_fake

_BASE = {"id": "u1", "age": 35, "gender": "female", "height_cm": 160, "weight_kg": 60,
         "bmi_category": "normal", "activity_level": "moderate", "dominant_dosha": "vata",
         "agni_type": "sama"}
T0 = datetime(2026, 9, 1, tzinfo=timezone.utc)


def _checkin(week, days=0, **kw):
    return {"week": week, "hunger": "right", "digestion": [], "trouble_foods": [],
            "red_flags": [], "updated_at": T0 + timedelta(days=days), **kw}


# ── What a check-in says ─────────────────────────────────────────────────────

def test_trouble_foods_accumulate_but_digestion_and_hunger_are_the_latest_weeks():
    a = _checkin(1, 0, hunger="hungry", digestion=["bloating"],
                 trouble_foods=[{"food": "rajma", "problem": "bloating"}])
    b = _checkin(2, 7, trouble_foods=[{"food": "curd_yogurt", "problem": "acidity"}])
    s = ck.signals([a, b], {"age": 35})
    assert s["trouble_foods"] == ["curd_yogurt", "rajma"]
    # Last week's bloating is not this week's.
    assert "digestion" not in s and "hunger_adjust_kcal" not in s


@pytest.mark.parametrize("profile", [{"age": 12}, {"age": 30, "pregnancy_or_nursing": True},
                                     {"age": 30, "bmi_category": "underweight"}])
def test_too_much_food_never_cuts_a_child_a_pregnancy_or_an_underweight_patient(profile):
    assert ck.hunger_adjust({"hunger": "too_much"}, profile) == 0
    assert ck.hunger_adjust({"hunger": "hungry"}, profile) == 150


def test_the_proposal_names_each_change_and_offers_one_rebuild():
    c = _checkin(2, hunger="hungry", digestion=["acidity", "loose_stools"],
                 trouble_foods=[{"food": "rajma", "problem": "bloating"}])
    p = ck.proposal(c, {"age": 35})
    assert p["from_week"] == 3 and p["rebuild_available"]
    assert {ch["kind"] for ch in p["changes"]} == {"exclude", "digestion", "light_meals", "energy"}
    assert not ck.proposal({**c, "rebuilt_at": T0}, {"age": 35})["rebuild_available"]
    # Week four's check-in has no weeks left to change.
    assert not ck.proposal({**c, "week": 4}, {"age": 35})["rebuild_available"]


def test_a_red_flag_is_a_doctor_not_a_menu():
    p = ck.proposal(_checkin(1, red_flags=["swelling"]), {"age": 35})
    assert p["see_doctor"] and not p["rebuild_available"]


# ── What it changes ──────────────────────────────────────────────────────────

def test_a_check_in_applies_without_the_logs_fourteen_meal_threshold():
    a = dl.adaptation([], [], goal=None, bmi_category=None,
                      checkin={"trouble_foods": ["rajma"]})
    assert a["trouble_foods"] == ["rajma"]


def test_shipping_the_check_in_does_not_change_a_log_only_fingerprint():
    """Otherwise every patient's cached plan would be stale and bill a regeneration."""
    adapt = {"meals_logged": 20, "skipped_slots": ["breakfast"]}
    old = {k: adapt.get(k) for k in ("skipped_slots", "avoided_foods", "energy_adjust_kcal")}
    expected = hashlib.sha256(json.dumps(old, sort_keys=True).encode()).hexdigest()[:16]
    assert dl.fingerprint(adapt) == expected
    assert dl.fingerprint({**adapt, "trouble_foods": ["rajma"]}) != expected


def test_reported_foods_leave_the_food_list_and_digestion_becomes_a_protocol():
    profile = {**_BASE, "diet_log": {"trouble_foods": ["rajma"], "digestion": ["acidity"]}}
    screen = allowed_foods(profile, {})
    assert screen["excluded"]["rajma"] == "you reported trouble after eating it"
    assert "acidity" in diet_conditions(profile, {})
    assert "loose stools" in dl.brief_block({"digestion": ["loose_stools"]})


def test_hunger_moves_energy_by_at_most_150_with_the_log_step():
    base = energy_target(dict(_BASE), {})["target_calories"]
    hungry = energy_target({**_BASE, "diet_log": {"hunger_adjust_kcal": 150}}, {})
    assert hungry["target_calories"] == base + 150
    # The scale said too generous, the patient says hungry: they cancel, not compound.
    both = energy_target({**_BASE, "diet_log": {"hunger_adjust_kcal": 150,
                                                 "energy_adjust_kcal": -150}}, {})
    assert both["target_calories"] == base


def test_the_food_picker_offers_foods_not_seasonings():
    plan = {"diet_weeks": [{"week_number": 1, "daily_plan": {"Monday": {"lunch": {"components": [
        {"food": "moong_dal_yellow", "grams": 150}, {"food": "salt", "grams": 1.5},
        {"food": "ghee", "grams": 5}, {"food": "cumin_jeera", "grams": 1}]}}}}]}
    assert [f["id"] for f in ck.week_foods(plan, 1)] == ["moong_dal_yellow"]
    assert "dairy" in ck.allergy_keys_for("milk_full_fat")


# ── The rebuild ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_a_rebuild_keeps_the_weeks_eaten_and_rewrites_the_rest(monkeypatch):
    async def none(*a, **k):
        return []
    monkeypatch.setattr(gen.rag_pipeline, "query", none)
    monkeypatch.setattr(gen.llm_client, "generate", make_fake([]))
    old = await gen.generate_diet_plan_llm(dict(_BASE), {})
    grain = next(c["food"] for c in old["diet_weeks"][0]["daily_plan"]["Monday"]["lunch"]["components"]
                 if c["food"] in ("brown_rice", "millet_jowar", "quinoa"))

    calls = []
    monkeypatch.setattr(gen.llm_client, "generate", make_fake(calls))
    profile = {**_BASE, "diet_log": {"trouble_foods": [grain]}}
    new = await gen.rebuild_diet_weeks(old, profile, {}, from_week=2)

    assert new["diet_weeks"][0] == old["diet_weeks"][0]
    later = {c["food"] for w in new["diet_weeks"][1:] for d in w["daily_plan"].values()
             for s in ("breakfast", "lunch", "snack", "dinner") for c in d[s]["components"]}
    assert grain not in later
    assert [w["week_number"] for w in new["diet_weeks"]] == [1, 2, 3, 4]
    # Three weeks written, no overview, and the plan keeps its id and start date.
    assert sum("Write WEEK" in c for c in calls) == 3
    assert not any("Write WEEK 1" in c for c in calls)
    assert new["plan_id"] == old["plan_id"] and new["generated_at"] == old["generated_at"]


@pytest.mark.asyncio
async def test_week_one_cannot_be_rebuilt():
    with pytest.raises(ValueError):
        await gen.rebuild_diet_weeks({"diet_weeks": []}, dict(_BASE), {}, from_week=1)


# ── The end of the four weeks ────────────────────────────────────────────────

class _Cursor:
    def __init__(self, docs):
        self.docs = list(docs)

    def __aiter__(self):
        self._it = iter(self.docs)
        return self

    async def __anext__(self):
        try:
            return next(self._it)
        except StopIteration:
            raise StopAsyncIteration


def _match(doc, filt):
    for k, v in filt.items():
        have = doc.get(k)
        if isinstance(v, dict):
            if "$exists" in v and (k in doc) != v["$exists"]:
                return False
            if "$lte" in v and not (have is not None and have <= v["$lte"]):
                return False
            if "$gte" in v and not (have is not None and have >= v["$gte"]):
                return False
            if "$gt" in v and not (have is not None and have > v["$gt"]):
                return False
        elif have != v:
            return False
    return True


class _Coll:
    def __init__(self, docs=()):
        self.docs = [dict(d) for d in docs]

    def find(self, filt=None, *_):
        return _Cursor(d for d in self.docs if _match(d, filt or {}))

    async def find_one(self, filt=None, *_, **__):
        return next((d for d in self.docs if _match(d, filt or {})), None)

    async def update_one(self, filt, update, **_):
        for d in self.docs:
            if _match(d, filt):
                d.update(update.get("$set") or {})
                return


class _DB:
    def __init__(self, plans, logs):
        self.plan_history = _Coll(plans)
        self.meal_logs = _Coll(logs)


def _record(pid, days_ago, now, user="u1"):
    return {"_id": pid, "user_id": user, "plan_type": "diet",
            "generated_at": now - timedelta(days=days_ago),
            "plan_data": {"diet_plan": {"plan_id": f"diet_{pid}"}}}


@pytest.mark.asyncio
async def test_a_finished_plan_is_announced_once_and_a_superseded_or_abandoned_one_never():
    from unittest.mock import AsyncMock, patch
    now = datetime.now(timezone.utc)
    logs = [{"user_id": "u1", "plan_id": "diet_done", "slot": "lunch", "status": "eaten"}] * 20
    db = _DB([_record("done", 29, now), _record("old", 31, now, "u2"),
              _record("new", 3, now, "u2"), _record("ancient", 200, now, "u3")], logs)
    with patch("services.notification_service.create_and_deliver_notification",
               new=AsyncMock()) as send:
        assert await dl.notify_finished_plans(db, now) == 1
        kw = send.await_args.kwargs
        assert kw["user_id"] == "u1" and "20 meals" in kw["body"]
        assert await dl.notify_finished_plans(db, now) == 0


@pytest.mark.asyncio
async def test_a_rebuild_still_works_when_the_model_is_down(monkeypatch):
    async def none(*a, **k):
        return []
    monkeypatch.setattr(gen.rag_pipeline, "query", none)
    monkeypatch.setattr(gen.llm_client, "generate", make_fake([]))
    old = await gen.generate_diet_plan_llm(dict(_BASE), {})
    monkeypatch.setattr(gen.llm_client, "generate", make_fake([], always_fail={1, 2, 3, 4}))
    new = await gen.rebuild_diet_weeks(old, dict(_BASE), {}, from_week=2)
    assert new["diet_weeks"][0] == old["diet_weeks"][0]
    assert all(w.get("composed_by") == "rule_engine" for w in new["diet_weeks"][1:])
    assert new["energy_reconciliation"]["days_quantified"] == 28
