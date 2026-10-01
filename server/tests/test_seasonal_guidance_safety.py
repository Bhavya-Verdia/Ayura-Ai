"""The Ritucharya card names foods, and knew nothing about who was reading it.

`build_seasonal_guidance` took a dosha and nothing else, while `diet_adjustments` is
LLM-written and names specific foods. A real Sharad card read:

    "Favor sweet, bitter, and astringent foods such as pomegranate, white rice,
     and leafy greens"
    "Use cow ghee and cooling, room-temperature meals to soothe aggravated Pitta"

shown identically to every Pitta user. White rice is Apathya in Prameha and cow ghee
is a declared dairy allergen; the endpoint knew about neither and no gate read the
output. It is the second food-recommending surface in this app with that shape — the
plan's own Pathya card was the first.
"""

import asyncio
import inspect

import pytest

from services.ahara_safety import apply_advisory_safety
from services.seasonal_service import build_seasonal_guidance


def test_the_patient_reaches_the_prompt():
    """Prevention before filtering, the order that worked for the diet brief."""
    src = inspect.getsource(build_seasonal_guidance)
    assert "medical_history" in src
    assert "allergies" in src
    assert "pregnancy_or_nursing" in src
    assert "dietary_type" in src


def test_both_callers_pass_the_profile():
    """A card generated on the holistic path must not be blinder than one generated
    from the endpoint — the asymmetry `build_diet_plan` exists to prevent."""
    from pathlib import Path

    root = Path(__file__).resolve().parent.parent
    for rel in ("routes/plans.py", "routes/plan_runner.py"):
        src = (root / rel).read_text(encoding="utf-8")
        for line in src.splitlines():
            if "build_seasonal_guidance(" in line and "import" not in line:
                assert "user_profile" in line or "model_dump" in line, f"{rel}: {line.strip()}"


@pytest.mark.parametrize("item,conditions,allergies", [
    ("Favour white rice and pomegranate this season", ["diabetes"], []),
    ("Use cow ghee and warm milk at night", [], ["dairy"]),
    ("Take curd with your midday meal", ["acidity"], []),
    ("Add rajma and chole for protein", ["bloating"], []),
])
def test_the_gate_withholds_what_the_prompt_let_through(item, conditions, allergies):
    """The backstop, exercised directly on the shape the seasonal payload takes:
    `diet_adjustments` is the recommendation list, so a contradicted entry is
    withheld rather than flagged."""
    out = apply_advisory_safety(
        {"pathya_apathya": {"pathya": [item], "apathya": []}},
        conditions, allergies, [], extra_terms={}, pregnant=False)
    assert out["withheld_recommendations"], item
    assert out["pathya_apathya"]["pathya"] == []


def test_the_avoid_list_is_never_scanned():
    """`avoid` exists to name these foods, exactly as `pathya_apathya.apathya` does.
    Scanning it would withhold the warning."""
    avoid = ["Curd at night and excess sour foods", "White rice and refined flour"]
    out = apply_advisory_safety(
        {"pathya_apathya": {"pathya": [], "apathya": list(avoid)}},
        ["diabetes", "acidity"], [], [], extra_terms={}, pregnant=False)
    assert out["pathya_apathya"]["apathya"] == avoid


def test_a_clean_card_loses_nothing():
    out = apply_advisory_safety(
        {"pathya_apathya": {"pathya": ["Favour bitter greens and coconut water"],
                            "apathya": []}},
        ["diabetes"], [], [], extra_terms={}, pregnant=False)
    assert out["withheld_recommendations"] == []
    assert len(out["pathya_apathya"]["pathya"]) == 1


@pytest.fixture
def offline(monkeypatch):
    """No network in the suite. These two tests are about the plumbing around the
    model — the malformed-profile path and the no-profile path — not about what it
    writes, and a live call makes them slow and dependent on a key being present."""
    import types

    import services.seasonal_service as svc

    # `provider` is a read-only property on the real client, so the client is
    # replaced rather than mutated. `"none"` is the value the service already
    # branches on to return its fallback without calling out.
    monkeypatch.setattr(svc, "llm_client", types.SimpleNamespace(provider="none"))
    monkeypatch.setattr(svc, "fetch_weather", _noop_weather)
    monkeypatch.setattr(svc, "is_chromadb_available", lambda: False)


async def _noop_weather(*_a, **_k):
    return None


def test_the_gate_never_loses_the_card(offline):
    """A safety layer that throws must not cost the user their seasonal guidance —
    the same contract every scan in `ahara_safety` is held to. `allergies` is a string
    here, which is what emptied the card before it was guarded."""
    out = asyncio.run(build_seasonal_guidance("pitta", {"medical_history": None,
                                                        "allergies": "not-a-list"}))
    assert out["recommendations"]["diet_adjustments"]


def test_it_still_works_with_no_profile_at_all(offline):
    """The signature stays backward compatible: a caller with only a dosha gets a
    card, not an exception."""
    out = asyncio.run(build_seasonal_guidance("vata"))
    assert out["recommendations"]["diet_adjustments"]
    assert out["season"]
