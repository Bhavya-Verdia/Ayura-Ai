"""The Ritucharya card is cached on the server.

Every dashboard load ran a weather lookup, a RAG query and a billed LLM call (4.6 s
measured on production), with no server cache and no quota. These tests hold the
three rules of the cache: a second request with the same inputs makes no LLM call,
a different profile is a different card, and a fallback card is never cached.
"""

import asyncio
import json
import types

import pytest

import services.seasonal_service as svc


class _Cache:
    def __init__(self):
        self.store = {}

    async def get_plan(self, prefix, params):
        return self.store.get((prefix, json.dumps(params, sort_keys=True)))

    async def set_plan(self, prefix, params, result, expire=0):
        self.store[(prefix, json.dumps(params, sort_keys=True))] = result


class _LLM:
    provider = "azure"

    def __init__(self, fail=False):
        self.calls = 0
        self.fail = fail

    async def generate(self, **_k):
        self.calls += 1
        if self.fail:
            raise RuntimeError("model down")
        return json.dumps({
            "focus": "Cool and steady routines this season.",
            "diet_adjustments": ["Favour cucumber and coriander"],
            "lifestyle_changes": ["Walk in the evening"],
            "avoid": ["Very spicy food"],
            "dosha_impact": "Pitta rises.",
        })


async def _no_weather(*_a, **_k):
    return None


@pytest.fixture
def cache(monkeypatch):
    import core.cache

    fake = _Cache()
    monkeypatch.setattr(core.cache, "cache_manager", fake)
    monkeypatch.setattr(svc, "fetch_weather", _no_weather)
    monkeypatch.setattr(svc, "is_chromadb_available", lambda: False)
    return fake


def _run(dosha="pitta", profile=None):
    return asyncio.run(svc.build_seasonal_guidance(dosha, profile or {}))


def test_the_second_request_makes_no_llm_call(cache, monkeypatch):
    llm = _LLM()
    monkeypatch.setattr(svc, "llm_client", llm)
    first = _run()
    second = _run()
    assert llm.calls == 1
    assert first == second


def test_a_different_profile_is_a_different_card(cache, monkeypatch):
    llm = _LLM()
    monkeypatch.setattr(svc, "llm_client", llm)
    _run(profile={"medical_history": ["diabetes"]})
    _run(profile={"medical_history": ["acidity"]})
    _run(profile={"medical_history": ["diabetes"], "allergies": ["dairy"]})
    _run(dosha="vata", profile={"medical_history": ["diabetes"]})
    assert llm.calls == 4


def test_a_fallback_card_is_not_cached(cache, monkeypatch):
    monkeypatch.setattr(svc, "llm_client", _LLM(fail=True))
    _run()
    assert not cache.store
    recovered = _LLM()
    monkeypatch.setattr(svc, "llm_client", recovered)
    _run()
    assert recovered.calls == 1, "the generic card must not outlive the outage"


def test_the_prompt_never_asks_to_support_a_condition():
    """The live card read "prevent heat-related flare-ups and support anxiety"."""
    import inspect

    assert 'Never write "support <condition>"' in inspect.getsource(svc.build_seasonal_guidance)


def test_no_cache_still_returns_a_card(monkeypatch):
    """Redis down is a slower card, never a missing one."""
    import core.cache

    class _Broken:
        async def get_plan(self, *_a, **_k):
            raise ConnectionError

        async def set_plan(self, *_a, **_k):
            raise ConnectionError

    monkeypatch.setattr(core.cache, "cache_manager", _Broken())
    monkeypatch.setattr(svc, "fetch_weather", _no_weather)
    monkeypatch.setattr(svc, "is_chromadb_available", lambda: False)
    monkeypatch.setattr(svc, "llm_client", _LLM())
    assert _run()["recommendations"]["diet_adjustments"]
