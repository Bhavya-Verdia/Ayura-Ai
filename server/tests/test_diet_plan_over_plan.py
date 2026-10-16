"""Diet plan over plan: the next plan continues a finished, followed one rather than
starting its progression again (`diet_log.previous_plans`, `diet_plan_arc._continue`)."""
from datetime import datetime, timedelta, timezone

import pytest

from services import diet_log as dl
from services.diet_plan_arc import choose_arc

NOW = datetime(2026, 10, 10, tzinfo=timezone.utc)
BALANCED = {"ama_indicator": "none", "ojas_level": "moderate", "bmi_category": "normal", "age": 35}
SAMATVA = "Samatva (balance-led)"


class _Q:
    def __init__(self, docs):
        self.docs = docs

    async def to_list(self, length=None):
        return list(self.docs)

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
        if isinstance(v, dict) and "$in" in v:
            if doc.get(k) not in v["$in"]:
                return False
        elif doc.get(k) != v:
            return False
    return True


class _Coll:
    def __init__(self, docs):
        self.docs = docs

    def find(self, filt=None, *_):
        return _Q([d for d in self.docs if _match(d, filt or {})])


class _DB:
    def __init__(self, plans, logs):
        self.plan_history = _Coll(plans)
        self.meal_logs = _Coll(logs)


def _plan(pid, days_ago, arc=SAMATVA):
    return {"_id": pid, "user_id": "u1", "plan_type": "diet",
            "generated_at": NOW - timedelta(days=days_ago),
            "plan_data": {"diet_plan": {"plan_id": pid, "therapeutic_arc": {
                "arc": arc, "weeks": [{"phase": "Agni Deepana"}, {"phase": "Rasayana"}]}}}}


def _logs(pid, n, status="eaten", week=2):
    return [{"user_id": "u1", "plan_id": pid, "week": week, "slot": "lunch", "status": status}] * n


@pytest.mark.asyncio
async def test_a_finished_followed_plan_is_continued_from():
    db = _DB([_plan("p1", 30)], _logs("p1", 20))
    prev = await dl.previous_plans(db, "u1", NOW)
    assert prev == {**prev, "plan_number": 2, "finished": True, "followed": True, "arc": SAMATVA}


@pytest.mark.asyncio
async def test_a_plan_regenerated_mid_way_is_not_finished_and_not_counted():
    # p1 was replaced after five days; p2 is three weeks in.
    db = _DB([_plan("p1", 26), _plan("p2", 21)], _logs("p2", 20))
    prev = await dl.previous_plans(db, "u1", NOW)
    assert prev["plan_number"] == 2 and prev["finished"]
    db = _DB([_plan("p1", 10)], _logs("p1", 20))
    assert not (await dl.previous_plans(db, "u1", NOW))["finished"]


@pytest.mark.asyncio
async def test_logging_week_four_finishes_a_plan_early_and_skipping_it_is_not_following_it():
    db = _DB([_plan("p1", 15)], _logs("p1", 14, week=4))
    assert (await dl.previous_plans(db, "u1", NOW))["finished"]
    db = _DB([_plan("p1", 30)], _logs("p1", 20, status="skipped"))
    assert not (await dl.previous_plans(db, "u1", NOW))["followed"]


def test_month_two_does_not_open_with_month_ones_first_week():
    first = choose_arc(dict(BALANCED), {})
    nxt = choose_arc({**BALANCED, "diet_log": {"continues": {
        "plan_number": 2, "followed": True, "arc": SAMATVA}}}, {})
    assert first["weeks"][0]["phase"] == "Agni Deepana"
    assert nxt["weeks"][0]["phase"] != "Agni Deepana" and nxt["continuation"] == "continued"
    assert nxt["plan_number"] == 2 and "Plan 2" in nxt["basis"]
    assert [w["week_number"] for w in nxt["weeks"]] == [1, 2, 3, 4]


def test_a_plan_not_followed_starts_again_and_says_why():
    nxt = choose_arc({**BALANCED, "diet_log": {"continues": {
        "plan_number": 2, "followed": False, "arc": SAMATVA, "meals_logged": 3}}}, {})
    assert nxt["weeks"][0]["phase"] == "Agni Deepana" and nxt["continuation"] == "repeated"


def test_ama_still_present_is_cleared_again_however_well_the_plan_was_followed():
    p = {**BALANCED, "ama_indicator": "high", "diet_log": {"continues": {
        "plan_number": 3, "followed": True, "arc": "Ama Pachana to Rasayana"}}}
    nxt = choose_arc(p, {})
    assert nxt["weeks"][0]["phase"] == "Ama Pachana" and nxt["continuation"] == "held"


def test_a_changed_state_starts_its_own_line_from_the_beginning():
    p = {**BALANCED, "bmi_category": "obese", "diet_log": {"continues": {
        "plan_number": 2, "followed": True, "arc": SAMATVA}}}
    nxt = choose_arc(p, {})
    assert nxt["arc"].startswith("Langhana") and nxt["continuation"] == "new_line"
    assert nxt["weeks"][0]["phase"] == "Agni Deepana"


def test_a_continued_reducing_plan_never_adds_a_nourishing_week():
    p = {**BALANCED, "bmi_category": "obese", "medical_history": ["diabetes"],
         "diet_log": {"continues": {"plan_number": 2, "followed": True,
                                    "arc": "Langhana-pradhana (reduction-led)"}}}
    phases = [w["phase"] for w in choose_arc(p, {})["weeks"]]
    assert "Brimhana" not in phases and phases[0] == "Langhana"


def test_pregnancy_is_never_continued_into_another_line():
    p = {**BALANCED, "pregnancy_or_nursing": True, "diet_log": {"continues": {
        "plan_number": 2, "followed": True, "arc": "Garbhini Paricharya"}}}
    arc = choose_arc(p, {})
    assert arc["arc"] == "Garbhini Paricharya" and arc["continuation"] == "held"


def test_the_continuation_does_not_move_the_cache_key():
    """It flips the day the next plan is written; in the key it would bill a
    regeneration under a plan that is still current."""
    base = {"meals_logged": 20, "skipped_slots": ["breakfast"]}
    assert dl.fingerprint(base) == dl.fingerprint({**base, "continues": {"plan_number": 2}})


# ── Month two is not month one again ─────────────────────────────────────────

_PROFILE = {"id": "u1", "age": 35, "gender": "female", "height_cm": 160, "weight_kg": 60,
            "bmi_category": "normal", "activity_level": "moderate", "dominant_dosha": "vata",
            "agni_type": "sama"}


def test_each_plan_carries_the_staple_rotation_on():
    from services.diet_allowed_foods import allowed_foods
    from services.diet_week_generator import _staples
    allowed = allowed_foods(dict(_PROFILE), {})["allowed"]
    first = [_staples(allowed, w) for w in (1, 2, 3, 4)]
    second = [_staples(allowed, w, plan_seq=2) for w in (1, 2, 3, 4)]
    assert second[0] != first[0]
    # The first plan is unchanged by this.
    assert first == [_staples(allowed, w, plan_seq=1) for w in (1, 2, 3, 4)]


def test_the_rule_engine_serves_a_different_month_to_an_unchanged_patient():
    from services.diet_plan_engine import generate_diet_plan

    def foods(seq):
        raw = generate_diet_plan({**_PROFILE, "diet_log": {"plan_seq": seq}}, {})
        return [[i["id"] for m in d["meals"].values() for i in m]
                for w in raw["four_week_plan"] for d in w["days"]]
    one, again, two = foods(1), foods(1), foods(2)
    assert one == again
    same = sum(a == b for a, b in zip(one, two))
    assert same < len(one) // 4, f"{same} of {len(one)} days identical"


@pytest.mark.asyncio
async def test_the_plan_sequence_counts_every_plan():
    db = _DB([_plan("p1", 60), _plan("p2", 30), _plan("p3", 2)], [])
    assert (await dl.previous_plans(db, "u1", NOW))["plans_before"] == 3
