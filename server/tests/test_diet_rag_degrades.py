"""A ChromaDB outage costs the plan its citations, not the plan.

The five `rag_pipeline.query` calls in `generate_diet_plan_llm` sat directly under the
function's outer `except`, which returns None and sends the caller to the rule engine.
So a ChromaDB restart did not degrade the diet plan — it replaced it. Every generation
during the outage silently lost the LLM path entirely: the therapeutic arc, the
per-meal energy budget, the condition coaching, all of it, with nothing on screen to
say why.

Retrieval is supplementary grounding. An outage degrades, it does not withhold — the
same rule `classify_condition_apathya_llm` and the remedies triage follow for the same
layer.
"""

from unittest.mock import AsyncMock, patch

import pytest

from services import diet_llm_generator as g

_PROFILE = {
    "id": "p", "dominant_dosha": "pitta", "agni_type": "tikshna", "age": 41,
    "gender": "female", "height_cm": 158, "weight_kg": 74,
    "activity_level": "sedentary", "bmi_category": "overweight",
    "current_season": "grishma", "medical_history": ["diabetes"],
}
_PREFS = {
    "dietary_type": "vegetarian", "diet_goal": "weight_loss", "food_allergies": [],
    "food_intolerances": [], "gut_health_issue": "healthy",
    "intermittent_fasting": "no", "water_intake": "1-2L", "fasting_days": [],
}


@pytest.mark.asyncio
async def test_a_retrieval_outage_does_not_take_the_brief_down_with_it():
    """The brief is still built, and still carries everything that does not come from
    ChromaDB — which is the arc, the energy prescription and the whole condition
    protocol."""
    async def boom(*_a, **_k):
        raise RuntimeError("ChromaDB not initialized. Call init_chromadb() first.")

    captured = {}

    async def fake_generate(prompt, *_a, **_k):
        captured["prompt"] = prompt
        raise RuntimeError("stop here — the brief is what this test is about")

    with patch.object(g.rag_pipeline, "query", new=AsyncMock(side_effect=boom)), \
         patch.object(g.llm_client, "generate", new=AsyncMock(side_effect=fake_generate)):
        await g.generate_diet_plan_llm(_PROFILE, _PREFS)

    brief = captured.get("prompt", "")
    assert brief, "generation gave up before it ever built a brief"
    assert "ENERGY PRESCRIPTION" in brief
    assert "Prameha" in brief or "Diabetes" in brief
    # And nothing claiming a classical citation it could not retrieve.
    assert "CLASSICAL KNOWLEDGE BASE" not in brief


@pytest.mark.asyncio
async def test_partial_retrieval_keeps_what_it_got():
    """A condition query that succeeded before the failure is still grounding for that
    condition, so the recovery is not all-or-nothing either."""
    calls = {"n": 0}

    async def flaky(*_a, **_k):
        calls["n"] += 1
        if calls["n"] == 1:
            return [{"content": "Yava is Pathya in Prameha.", "metadata": {"source": "charaka"}}]
        raise RuntimeError("ChromaDB went away")

    captured = {}

    async def fake_generate(prompt, *_a, **_k):
        captured["prompt"] = prompt
        raise RuntimeError("stop here")

    with patch.object(g.rag_pipeline, "query", new=AsyncMock(side_effect=flaky)), \
         patch.object(g.llm_client, "generate", new=AsyncMock(side_effect=fake_generate)):
        await g.generate_diet_plan_llm(_PROFILE, _PREFS)

    assert "CLASSICAL KNOWLEDGE BASE" in captured.get("prompt", "")


def test_the_retrieval_block_has_its_own_handler():
    """A structural guard: moving a `rag_pipeline.query` call back outside the inner
    try restores the defect, and no behavioural test would notice until ChromaDB was
    actually down in production."""
    import ast
    import inspect
    import textwrap

    src = textwrap.dedent(inspect.getsource(g.generate_diet_plan_llm))
    tree = ast.parse(src)

    def guarded(node, depth=0):
        """Every rag_pipeline.query call must sit inside a Try nested in the outer one."""
        found = []
        for child in ast.walk(node):
            if (isinstance(child, ast.Attribute) and child.attr == "query"
                    and isinstance(child.value, ast.Name)
                    and child.value.id == "rag_pipeline"):
                found.append(child)
        return found

    inner_tries = [n for n in ast.walk(tree) if isinstance(n, ast.Try)]
    assert inner_tries, "generate_diet_plan_llm has no try block at all"
    # The queries must all live inside a Try that is NOT the outermost one.
    outermost = max(inner_tries, key=lambda t: len(ast.dump(t)))
    nested = [t for t in inner_tries if t is not outermost]
    all_queries = guarded(tree)
    assert all_queries, "no rag_pipeline.query calls found — has retrieval moved?"
    covered = {id(q) for t in nested for q in guarded(t)}
    uncovered = [q for q in all_queries if id(q) not in covered]
    assert not uncovered, (
        f"{len(uncovered)} rag_pipeline.query call(s) sit directly under the outer "
        f"except, which returns None — a retrieval outage would replace the plan "
        f"rather than degrade it"
    )
