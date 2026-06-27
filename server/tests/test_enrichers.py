"""
Tests for plan enricher LLM-fallback behaviour.

Each enricher must return the rule-engine output (enriched=False) when:
  - the LLM is unavailable (returns an error JSON)
  - the LLM returns malformed / non-JSON text
  - the LLM call raises an exception

These tests mock llm_client.generate so no real API calls are made.
"""

import json
import pytest
from unittest.mock import AsyncMock, patch


# ── Helpers ───────────────────────────────────────────────────────────────────

def _llm_error_response():
    return json.dumps({"error": "No LLM provider available. Configure AZURE_OPENAI_API_KEY or GEMINI_API_KEY."})


def _llm_bad_json():
    return "I'm sorry, I can't generate a JSON response right now."


# ── Yoga enricher ─────────────────────────────────────────────────────────────

def _mock_rag(module: str):
    """Return a context-manager that mocks rag_pipeline for the given enricher module."""
    return patch(f"{module}.rag_pipeline", **{
        "query": AsyncMock(return_value=[]),
        "format_context.return_value": "",
    })


@pytest.mark.asyncio
async def test_yoga_enricher_falls_back_on_llm_error():
    from services.yoga_plan_enricher import enrich_yoga_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "test-yoga"}
    user_profile = {"dominant_dosha": "vata"}
    yoga_prefs = {}

    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_error_response())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_yoga_plan(raw_plan, user_profile, yoga_prefs)

    assert result["enriched"] is False
    assert result["plan_id"] == "test-yoga"


@pytest.mark.asyncio
async def test_yoga_enricher_falls_back_on_bad_json():
    from services.yoga_plan_enricher import enrich_yoga_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "test-yoga-2"}
    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_bad_json())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_yoga_plan(raw_plan, {}, {})

    assert result["enriched"] is False


@pytest.mark.asyncio
async def test_yoga_enricher_falls_back_on_exception():
    from services.yoga_plan_enricher import enrich_yoga_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "test-yoga-3"}
    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(side_effect=RuntimeError("Azure timeout"))
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_yoga_plan(raw_plan, {}, {})

    assert result["enriched"] is False


# ── Gym enricher ──────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_gym_enricher_falls_back_on_llm_error():
    from services.gym_plan_enricher import enrich_gym_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "test-gym"}
    with patch("services.gym_plan_enricher.llm_client") as mock_llm, \
         patch("services.gym_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_error_response())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_gym_plan(raw_plan, {}, {})

    assert result["enriched"] is False
    assert result["plan_id"] == "test-gym"


# ── Diet enricher ─────────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_diet_enricher_falls_back_on_llm_error():
    from services.diet_plan_enricher import enrich_diet_plan

    raw_plan = {"weekly_schedule": [], "plan_id": "test-diet"}
    with patch("services.diet_plan_enricher.llm_client") as mock_llm, \
         patch("services.diet_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_error_response())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_diet_plan(raw_plan, {}, {})

    assert result["enriched"] is False


# ── Panchakarma enricher ──────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_panchakarma_enricher_falls_back_on_llm_error():
    from services.panchakarma_enricher import enrich_panchakarma_plan

    raw_plan = {"daily_schedule": [], "plan_id": "test-pk"}
    with patch("services.panchakarma_enricher.llm_client") as mock_llm, \
         patch("services.panchakarma_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_error_response())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_panchakarma_plan(raw_plan, {}, {})

    assert result["enriched"] is False
    assert result["plan_id"] == "test-pk"


# ── Remedy enricher ───────────────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_remedy_enricher_falls_back_on_llm_error():
    from services.remedy_enricher import enrich_remedies_plan

    raw_plan = {
        "symptoms_addressed": [{"symptom_id": "cold", "symptom_display": "Cold", "severity": "mild", "remedy": {"name": "Ginger tea"}}],
        "plan_id": "test-remedy",
    }
    with patch("services.remedy_enricher.llm_client") as mock_llm, \
         patch("services.remedy_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=_llm_error_response())
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_remedies_plan(raw_plan, {})

    assert result["enriched"] is False
    assert result["plan_id"] == "test-remedy"


@pytest.mark.asyncio
async def test_remedy_enricher_returns_raw_when_no_symptoms():
    from services.remedy_enricher import enrich_remedies_plan

    raw_plan = {"symptoms_addressed": [], "plan_id": "test-remedy-empty"}
    result = await enrich_remedies_plan(raw_plan, {})

    assert result["enriched"] is False
    assert result["plan_id"] == "test-remedy-empty"


# ── Successful enrichment path ────────────────────────────────────────────────

@pytest.mark.asyncio
async def test_yoga_enricher_merges_valid_llm_response():
    from services.yoga_plan_enricher import enrich_yoga_plan

    valid_response = json.dumps({
        "plan_title": "Vata Calming Yoga Plan",
        "plan_description": "A gentle flow to ground your energy.",
        "daily_intention": {"Monday": "Breathe and be present"},
        "breathing_guidance": "Inhale deeply for 4 counts.",
        "lifestyle_sync": "Align your practice with sunrise.",
        "progression_plan": {"week_1": "Foundational poses"},
        "motivational_note": "You are doing great.",
    })

    raw_plan = {"weekly_schedule": [], "plan_id": "test-yoga-ok"}
    with patch("services.yoga_plan_enricher.llm_client") as mock_llm, \
         patch("services.yoga_plan_enricher.rag_pipeline") as mock_rag:
        mock_llm.generate = AsyncMock(return_value=valid_response)
        mock_llm.provider = "azure_openai"
        mock_rag.query = AsyncMock(return_value=[])
        mock_rag.format_context = lambda docs, max_chars=None: ""
        result = await enrich_yoga_plan(raw_plan, {"dominant_dosha": "vata"}, {})

    assert result["enriched"] is True
    assert result["plan_title"] == "Vata Calming Yoga Plan"
    assert result["enrichment_model"] == "azure_openai"
