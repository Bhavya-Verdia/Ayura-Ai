"""Defects found by the 2026-10-18 live sweep of every feature on production.

Each test reproduces what the sweep saw, from the shape the app really stores.
"""
from datetime import datetime, timedelta
from types import SimpleNamespace

import pytest

from ai.agents.health_agent import build_tools, build_system_prompt
from routes.export import handoff_plan_data
from schemas.plan_schema import PlanResponse
from services.chat_service import allergen_safety_note, summarize_user_health
from services.remedy_enricher import _DENIES_REMEDY

T0 = datetime(2026, 10, 18, 12, 0)


def _doc(plan_type, plan_data, minutes_ago):
    return {"plan_type": plan_type, "plan_data": plan_data, "generated_at": T0 - timedelta(minutes=minutes_ago)}


MEDICINES_PLAN = {
    "plan_id": "medicines_x",
    "primary_formulations": [{
        "name": "Avipattikar Churna", "primary_uses": ["hyperacidity"],
        "dosage": "3–5g with warm milk or honey twice daily", "timing": "after meals",
        "anupana": "Warm milk or honey", "selected_anupana": "warm water",
        "anupana_note": "Take it with warm water: the usual Anupana contains dairy.",
        "contraindications": ["hypokalemia", "pregnancy"], "drug_interactions": ["diuretics"],
        "usage_cautions": [], "red_flags": [],
    }],
    "supporting_formulations": [], "external_therapies": [],
}
REMEDIES_PLAN = {
    "plan_id": "remedy_x",
    "symptoms_addressed": [{
        "symptom_id": "acidity", "symptom_display": "Acid Reflux",
        "remedy": {"name": "Amalaki and Aloe Vera Coolant", "preparation": "Mix into water.",
                   "dosage": "Once daily in morning", "duration": "5-7 days"},
        "caution_notes": [], "medication_cautions": ["thyroid medication"], "usage_cautions": [],
        "drug_interaction_warning": None, "ayurvedic_rationale": "Amalaki cools Pitta.",
    }],
}


# ── 1. The Vaidya handoff carried only the newest plan ────────────────────────

def _dashboard_history():
    """As the sweep account's history read: one feature per doc, routine newest."""
    return [
        _doc("routine", {"routine_plan": {"weekly_routine": []}}, 0),
        _doc("routine", {"routine_plan": {"weekly_routine": []}}, 1),
        _doc("medicines", {"medicines": MEDICINES_PLAN}, 5),
        _doc("remedies", REMEDIES_PLAN, 6),
        _doc("panchakarma", {"panchakarma_plan": {"phase_breakdown": "x"}}, 7),
        _doc("diet", {"diet_plan": {"diet_weeks": [1, 2, 3, 4]}}, 8),
        _doc("yoga", {"yoga_plan": {"weekly_schedule": "x"}}, 9),
        _doc("gym", {"gym_plan": {"weekly_schedule": "x"}}, 10),
    ]


def test_the_handoff_carries_every_feature_when_the_routine_is_newest():
    data, _ = handoff_plan_data(_dashboard_history())
    assert set(data) == {"gym_plan", "yoga_plan", "diet_plan", "panchakarma_plan", "home_remedies", "medicines"}


def test_the_newest_plan_of_each_feature_wins():
    newer = _doc("diet", {"diet_plan": {"diet_weeks": ["new"]}}, 2)
    data, when = handoff_plan_data([newer, *_dashboard_history()[2:]])
    assert data["diet_plan"]["diet_weeks"] == ["new"]
    assert when == newer["generated_at"]


def test_a_holistic_plan_fills_what_per_feature_plans_do_not():
    holistic = _doc("holistic", {"gym_plan": {"old": True}, "yoga_plan": {"old": True}}, 30)
    data, _ = handoff_plan_data([_doc("gym", {"gym_plan": {"new": True}}, 1), holistic])
    assert data["gym_plan"] == {"new": True} and data["yoga_plan"] == {"old": True}


def test_remedies_stored_flat_reach_the_handoff_as_items():
    data, _ = handoff_plan_data([_doc("remedies", REMEDIES_PLAN, 0)])
    [item] = data["home_remedies"]
    assert item["remedy_name"] == "Amalaki and Aloe Vera Coolant"
    assert item["symptom_addressed"] == "Acid Reflux"
    assert "thyroid medication" in item["warnings"]


def test_medicines_reach_the_handoff_as_items_with_the_patients_anupana():
    data, _ = handoff_plan_data([_doc("medicines", {"medicines": MEDICINES_PLAN}, 0)])
    [item] = data["medicines"]
    assert item["medicine_name"] == "Avipattikar Churna"
    # The engine chose warm water for a dairy allergy; the catalogue default is milk.
    assert item["anupana"].startswith("warm water") and "dairy" in item["anupana"]
    assert any("diuretics" in w for w in item["warnings"])


def test_a_user_with_no_plans_gets_an_empty_handoff():
    assert handoff_plan_data([]) == ({}, None)


# ── 3. /plans/latest 500'd when the newest plan was a medicines plan ──────────

def test_plan_response_accepts_a_per_feature_medicines_plan():
    PlanResponse(user_summary={}, generated_at=T0, generation_method="rule_based", medicines=MEDICINES_PLAN)


# ── 4. A remedy rationale denied its own remedy ───────────────────────────────

def test_a_rationale_denying_its_remedy_is_recognised():
    said = ("The fatigue remedy is not included in this plan because the provided "
            "symptom list focuses on acid reflux management.")
    assert _DENIES_REMEDY.search(said)


@pytest.mark.parametrize("ordinary", [
    "Amalaki is classically cooling and Pitta-pacifying.",
    "Dairy is not included in the diet, so this uses water.",
    "Avoid if not tolerated, and keep it away from levothyroxine by four hours.",
])
def test_an_ordinary_rationale_is_not(ordinary):
    assert not _DENIES_REMEDY.search(ordinary)


# ── 2. Chat: an allergen recommended, and the interaction tool blind to the question ──

def test_ghee_offered_to_a_dairy_allergy_gets_a_correction():
    reply = "- **Steamed vegetables** with a small amount of **ghee** if it suits you"
    note = allergen_safety_note(reply, ["dairy"])
    assert note and "dairy" in note and "ghee" in note


@pytest.mark.parametrize("reply", [
    "Best to avoid tonight: ghee, curd and fried food.",
    "Try cool soy milk with cardamom.",
    "Moong dal khichdi with cumin.",
])
def test_correct_advice_gets_no_correction(reply):
    assert allergen_safety_note(reply, ["dairy"]) is None


CHAT_REPLY = """For your acidity, keep dinner **light, warm, and non-spicy**.

Good dinner options tonight:
- **Moong dal khichdi** with a little **cumin and coriander**
- **Steamed vegetables** with a small amount of **ghee** if it suits you

Best to avoid tonight:
- Sour foods/drinks
- Fried, oily, or very spicy curd-based food
- Paneer and cheese dishes

If you want, I can also suggest a menu."""


def test_the_sweeps_real_reply_is_corrected_for_the_ghee_only():
    note = allergen_safety_note(CHAT_REPLY, ["dairy"])
    assert note and "ghee" in note
    assert "paneer" not in note and "curd" not in note   # those were under "avoid"


def test_a_recommendation_after_an_avoid_list_is_still_caught():
    reply = "Avoid:\n- curd\n- paneer\n\nInstead, have warm milk with turmeric."
    assert "milk" in (allergen_safety_note(reply, ["dairy"]) or "")


def test_an_allergy_stored_as_a_string_is_not_read_letter_by_letter():
    assert allergen_safety_note("Moong dal khichdi with a dash of ghee", "dairy")
    assert allergen_safety_note("A cup of rice", "dairy") is None


def test_the_profile_tells_the_agent_which_foods_an_allergy_covers():
    user = SimpleNamespace(allergies=["dairy"], dominant_dosha=None, secondary_dosha=None,
                           medical_history=[], current_medications=[], current_symptoms=[])
    profile = summarize_user_health(user)
    assert "ghee" in profile and "dairy" in profile


class _DB:
    reminders = None


@pytest.mark.asyncio
async def test_the_interaction_tool_checks_the_herb_asked_about():
    user = SimpleNamespace(id="u1", name="T", current_medications=["levothyroxine"], vikriti_history=[],
                           allergies=[], medical_history=[])
    tools = {t.name: t for t in build_tools(_DB(), user, {}, {})}
    out = await tools["check_my_medicine_interactions"].ainvoke({"herbs": ["ashwagandha"]})
    assert "ashwagandha" in out.lower() and "found" in out.lower()
    assert "no known" not in out.lower()


def test_the_agent_is_told_to_pass_the_herb():
    user = SimpleNamespace(id="u1", name="T", allergies=[], medical_history=[], current_medications=[],
                           current_symptoms=[], dominant_dosha=None, secondary_dosha=None)
    assert "passing that herb" in build_system_prompt(user, {})


# ── Multiple chats: the list's title, and deleting one conversation ───────────

def test_a_chat_is_named_by_its_opening_question():
    from routes.chat import _session_title
    assert _session_title({"content": "What should I eat\n tonight?"}) == "What should I eat tonight?"
    assert _session_title(None) == "New chat"
    long = _session_title({"content": "x " * 80})
    assert len(long) <= 58 and long.endswith("…")


class _Deleted:
    def __init__(self, n):
        self.deleted_count = n


class _Coll:
    def __init__(self, docs):
        self.docs = docs

    def _match(self, d, q):
        return all(d.get(k) == v for k, v in q.items())

    async def delete_one(self, q):
        for d in self.docs:
            if self._match(d, q):
                self.docs.remove(d)
                return _Deleted(1)
        return _Deleted(0)

    async def delete_many(self, q):
        keep = [d for d in self.docs if not self._match(d, q)]
        n = len(self.docs) - len(keep)
        self.docs[:] = keep
        return _Deleted(n)


def _chat_db():
    return SimpleNamespace(
        chat_sessions=_Coll([{"session_id": "s1", "user_id": "me"}, {"session_id": "s2", "user_id": "me"},
                             {"session_id": "s3", "user_id": "someone"}]),
        chat_messages=_Coll([{"session_id": "s1", "user_id": "me"}, {"session_id": "s1", "user_id": "me"},
                             {"session_id": "s2", "user_id": "me"}, {"session_id": "s3", "user_id": "someone"}]),
    )


@pytest.mark.asyncio
async def test_deleting_a_chat_removes_only_that_chat(monkeypatch):
    import routes.chat as chat
    db = _chat_db()
    monkeypatch.setattr(chat, "get_mongodb", lambda: db)
    await chat.delete_chat_session("s1", user=SimpleNamespace(id="me"))
    assert [d["session_id"] for d in db.chat_sessions.docs] == ["s2", "s3"]
    assert [d["session_id"] for d in db.chat_messages.docs] == ["s2", "s3"]


@pytest.mark.asyncio
async def test_another_users_chat_cannot_be_deleted(monkeypatch):
    from fastapi import HTTPException
    import routes.chat as chat
    db = _chat_db()
    monkeypatch.setattr(chat, "get_mongodb", lambda: db)
    with pytest.raises(HTTPException) as e:
        await chat.delete_chat_session("s3", user=SimpleNamespace(id="me"))
    assert e.value.status_code == 404
    assert any(d["session_id"] == "s3" for d in db.chat_messages.docs)
