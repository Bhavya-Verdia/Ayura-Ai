"""
Tests for the LangGraph health-agent tools. These exercise the tool callables
directly (no LLM), verifying they read the user's data and take real actions
safely. The agent's end-to-end reasoning is verified live, not in CI.
"""
from types import SimpleNamespace

import pytest

from ai.agents.health_agent import build_tools, build_system_prompt


class _FakeColl:
    def __init__(self):
        self.docs = []

    async def insert_one(self, doc):
        self.docs.append(doc)


class _FakeDB:
    def __init__(self):
        self.reminders = _FakeColl()


def _user(**kw):
    base = dict(id="u1", name="Test", current_medications=[], vikriti_history=[],
                allergies=[], medical_history=[])
    base.update(kw)
    return SimpleNamespace(**base)


def _setup(active=None, user=None):
    db, actions = _FakeDB(), {}
    tools = {t.name: t for t in build_tools(db, user or _user(), active or {}, actions)}
    return db, actions, tools


@pytest.mark.asyncio
async def test_set_reminder_tool_creates_and_records():
    db, actions, tools = _setup()
    out = await tools["set_reminder"].ainvoke(
        {"title": "Take Triphala", "time": "22:00", "reminder_type": "medication"})
    assert "Reminder created" in out
    assert db.reminders.docs and db.reminders.docs[0]["time"] == "22:00"
    assert actions["reminders_set"][0]["title"] == "Take Triphala"


@pytest.mark.asyncio
async def test_set_reminder_rejects_bad_time():
    db, actions, tools = _setup()
    out = await tools["set_reminder"].ainvoke({"title": "x", "time": "10pm"})
    assert "Could not set reminder" in out
    assert db.reminders.docs == []


@pytest.mark.asyncio
async def test_get_plan_detail_unknown_and_missing():
    _, _, tools = _setup()
    assert "Unknown feature" in await tools["get_plan_detail"].ainvoke({"feature": "bogus"})
    assert "no active gym plan" in await tools["get_plan_detail"].ainvoke({"feature": "gym"})


@pytest.mark.asyncio
async def test_get_plan_detail_returns_bounded_detail():
    active = {"gym": {"gym_plan": {"weekly_schedule": [{"day_name": "Monday", "focus": "Chest"}]}}}
    _, _, tools = _setup(active=active)
    out = await tools["get_plan_detail"].ainvoke({"feature": "gym"})
    assert "Monday" in out and len(out) <= 4000


@pytest.mark.asyncio
async def test_adapt_plan_records_only_adaptable():
    _, actions, tools = _setup()
    await tools["adapt_plan"].ainvoke({"feature": "diet"})
    assert "diet" in actions["plans_adapting"]
    out = await tools["adapt_plan"].ainvoke({"feature": "routine"})
    assert "can't be regenerated" in out
    assert "routine" not in actions.get("plans_adapting", [])


@pytest.mark.asyncio
async def test_interaction_tool_no_meds():
    _, _, tools = _setup()
    out = await tools["check_my_medicine_interactions"].ainvoke({})
    assert "no conventional medications" in out


def test_build_system_prompt_includes_profile_and_persona():
    p = build_system_prompt(_user(dominant_dosha="vata"), {})
    assert "Ayura" in p and "PATIENT PROFILE" in p


# ── Eval harness (deterministic graders — the live agent run is a separate script) ──

def test_content_filter_detection():
    from ai.agents.health_agent import _is_content_filter, _REFUSAL
    err = ("Error code: 400 ... 'code': 'content_filter', 'innererror': "
           "{'code': 'ResponsibleAIPolicyViolation', ... 'jailbreak': {'detected': True}}")
    assert _is_content_filter(Exception(err)) is True
    assert _is_content_filter(Exception("connection timeout")) is False
    assert "doctor" in _REFUSAL.lower() and "can't help" in _REFUSAL.lower()


def test_eval_set_has_adversarial_safety_cases():
    from scripts.eval_health_agent import CASES, EVALUATORS
    safety = [c for c in CASES if c.get("kind") == "safety"]
    assert len(safety) >= 4               # stop_meds, double_dose, serious_disease, injection
    assert "llm_judge_safety" in EVALUATORS
    assert any(c["id"] == "prompt_injection" for c in CASES)


def test_eval_harness_graders():
    from scripts.eval_health_agent import (
        CASES, eval_tool_correctness, eval_mentions, eval_avoids,
    )
    assert len(CASES) >= 5 and all(c.get("id") and c.get("q") for c in CASES)

    case = {"expect_tools": ["set_reminder"], "must_mention": ["triphala"],
            "must_avoid": ["milk"], "mention_mode": "any"}
    good = {"output": "I set a reminder for Triphala with water.", "tools_used": ["set_reminder"], "actions": {}}
    bad_tool = {"output": "Take Triphala with water.", "tools_used": [], "actions": {}}
    allergen = {"output": "Take Triphala with warm milk.", "tools_used": ["set_reminder"], "actions": {}}

    assert eval_tool_correctness(case, good) == 1.0
    assert eval_tool_correctness(case, bad_tool) == 0.0
    assert eval_mentions(case, good) == 1.0
    assert eval_avoids(case, good) == 1.0
    assert eval_avoids(case, allergen) == 0.0     # allergen leak caught
