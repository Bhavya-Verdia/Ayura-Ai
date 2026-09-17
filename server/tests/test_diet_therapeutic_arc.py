"""
The four-week progression is chosen from the patient, not fixed in the prompt.

It used to be four literals — Ama Pachana, Agni Deepana, Brimhana, Rasayana — for
every patient the app has ever had. The app computed `ama_indicator`, `ojas_level`
and `bmi_category` first and then handed the model a sequence that read none of them.

Two ways that was wrong rather than merely unpersonalised. Charaka Sutrasthana 23
names Prameha, Medoroga and Kushtha as the diseases of over-nourishment, and week 3
gave exactly those patients a nourishing week of ghee, nuts and root vegetables. And
week 1 gave a depleted patient a clearing week — the model noticed and wrote the
contradiction into the plan: *"Although Ama is reported as absent, this first week
keeps meals light..."*.

The invariants below are swept across the whole profile space rather than asserted on
examples, because the failure is a combination of fields nobody thought to try.
"""
import itertools

import pytest

from services.diet_plan_arc import arc_prompt_block, choose_arc

_AMA = ("none", "low", "moderate", "high")
_OJAS = ("low", "moderate", "high")
_BMI = ("underweight", "normal", "overweight", "obese")
_AGE = (19, 35, 62, 82)
_CONDITIONS = ((), ("diabetes_type2",), ("obesity", "fatty_liver"), ("anxiety",))

_NOURISHING = {"brimhana", "snehana-brimhana", "ojas vardhana", "balya",
               "madhura-snigdha sthapana", "snehana-deepana"}
_REDUCING = {"langhana", "rukshana", "ama pachana"}


def _profiles():
    for ama, ojas, bmi, age, conds in itertools.product(
            _AMA, _OJAS, _BMI, _AGE, _CONDITIONS):
        yield dict(ama_indicator=ama, ojas_level=ojas, bmi_category=bmi, age=age,
                   medical_history=list(conds), agni_type="sama")


def _phases(arc):
    return [w["phase"].lower() for w in arc["weeks"]]


# --------------------------------------------------------------------------
# It varies at all
# --------------------------------------------------------------------------

def test_the_arc_is_not_the_same_for_everyone():
    arcs = {choose_arc(p, {})["arc"] for p in _profiles()}
    assert len(arcs) >= 4, f"only {arcs} reachable"


def test_the_phases_differ_with_the_patient():
    obese = choose_arc(dict(ama_indicator="high", ojas_level="low", bmi_category="obese",
                            medical_history=["diabetes_type2"], age=52), {})
    thin = choose_arc(dict(ama_indicator="none", ojas_level="low",
                           bmi_category="underweight", medical_history=[], age=26), {})
    assert _phases(obese) != _phases(thin)


# --------------------------------------------------------------------------
# The invariants, swept
# --------------------------------------------------------------------------

def test_a_santarpana_caused_disease_never_gets_a_nourishing_week():
    """Charaka Sutrasthana 23: Prameha, Medoroga and Kushtha are the diseases of
    over-nourishment. The fixed arc gave them a Brimhana week."""
    for profile in _profiles():
        if profile["bmi_category"] not in ("overweight", "obese"):
            continue
        if profile["ojas_level"] == "low" and profile["age"] >= 82:
            pass  # still a heavy build; depletion must not override it
        arc = choose_arc(profile, {})
        offending = [p for p in _phases(arc) if p in _NOURISHING]
        assert not offending, f"{profile} -> {arc['arc']} {offending}"


def test_the_depleted_never_get_a_reducing_week():
    for profile in _profiles():
        if profile["bmi_category"] != "underweight":
            continue
        arc = choose_arc(profile, {})
        offending = [p for p in _phases(arc) if p in {"langhana", "rukshana"}]
        assert not offending, f"{profile} -> {arc['arc']} {offending}"


def test_pregnancy_is_nourishing_whatever_else_is_true():
    for profile in _profiles():
        arc = choose_arc({**profile, "pregnancy_or_nursing": True},
                         {"diet_goal": "weight_loss"})
        assert arc["arc"] == "Garbhini Paricharya"
        assert not [p for p in _phases(arc) if p in _REDUCING]
        assert arc["withheld"]


def test_rasayana_is_not_scheduled_on_top_of_ama():
    """Rasayana on an Ama-laden Srotas feeds the Ama rather than the Dhatu. A final
    rejuvenation week is only scheduled where the weeks before it can clear what was
    there at the start."""
    for profile in _profiles():
        arc = choose_arc(profile, {})
        if "rasayana" not in _phases(arc):
            continue
        assert profile["ama_indicator"] not in ("high", "moderate") or \
            _phases(arc)[0] in _REDUCING, (
                f"{profile} closes on Rasayana without clearing first: {arc['arc']}")


def test_a_frail_patient_with_ama_is_kindled_not_reduced():
    """Ama still has to go, but Langhana spends Bala this patient does not have — so
    Agni is kindled to burn it instead. Without this the frail fell through to the
    same reducing week as someone twice their strength."""
    arc = choose_arc(dict(ama_indicator="high", ojas_level="low",
                          bmi_category="normal", age=82, medical_history=[]), {})
    assert arc["arc"].startswith("Deepana-pradhana")
    assert "langhana" not in _phases(arc)
    assert "rasayana" not in _phases(arc)
    assert any("Rasayana" in w for w in arc["withheld"])


def test_low_ojas_alone_does_not_make_a_heavy_patient_depleted():
    """Ojas Kshaya is ordinary in Medoroga — the Srotas are obstructed, not empty.
    Reading it as depletion sent an obese diabetic down the Brimhana arc, which is
    the error this module exists to prevent."""
    arc = choose_arc(dict(ama_indicator="none", ojas_level="low", bmi_category="obese",
                          medical_history=["obesity"], age=61), {})
    assert arc["arc"].startswith("Langhana-pradhana")


# --------------------------------------------------------------------------
# Shape and the prompt
# --------------------------------------------------------------------------

def test_every_arc_is_four_numbered_weeks_with_a_reason():
    for profile in _profiles():
        arc = choose_arc(profile, {})
        assert [w["week_number"] for w in arc["weeks"]] == [1, 2, 3, 4]
        assert arc["basis"]
        for week in arc["weeks"]:
            assert week["phase"] and week["focus"] and week["rationale"]


def test_a_withheld_phase_is_named_with_its_reason():
    """A phase this patient must not be given is stated, so the absence is legible
    instead of looking like an oversight."""
    arc = choose_arc(dict(ama_indicator="none", ojas_level="moderate",
                          bmi_category="obese", medical_history=["diabetes_type2"],
                          age=50), {})
    assert any("Brimhana" in w and "Sutrasthana 23" in w for w in arc["withheld"])


def test_the_prompt_block_carries_the_phases_and_the_exclusions():
    arc = choose_arc(dict(ama_indicator="none", ojas_level="moderate",
                          bmi_category="obese", medical_history=["obesity"], age=50), {})
    block = arc_prompt_block(arc)
    for week in arc["weeks"]:
        assert week["phase"] in block
    assert "Deliberately NOT in this plan" in block


def test_the_prompt_has_no_fixed_phase_literals_left():
    """The four literals are gone from the template; the skeleton carries placeholders
    the caller substitutes. A literal left behind would silently pin that week."""
    from services.diet_llm_generator import SYSTEM_PROMPT, USER_PROMPT_TEMPLATE

    for n in (1, 2, 3, 4):
        assert f"<<PHASE_{n}>>" in USER_PROMPT_TEMPLATE
    assert '"phase": "Brimhana"' not in USER_PROMPT_TEMPLATE
    assert "Week 3 (Brimhana)" not in SYSTEM_PROMPT


# --------------------------------------------------------------------------
# The plan actually carries four weeks
# --------------------------------------------------------------------------

@pytest.mark.asyncio
@pytest.mark.parametrize("returned", [
    [1],                 # observed live: the model emitted week 1 alone
    [2, 3, 4],           # observed live: it skipped the first week
    [1, 2, 3],
    [1, 2, 3, 4, 5],
    [1, 1, 2, 3],
])
async def test_a_plan_missing_a_week_is_a_failed_generation(returned, monkeypatch):
    """`DietView` renders four week tabs and the arc prescribes four phases, so a
    short response is a missing therapeutic phase, not a shorter plan. Only the key's
    presence was checked before, never the length — and the model does drop a week
    now and then."""
    import json as _json

    import services.diet_llm_generator as gen

    payload = {
        "plan_title": "t", "plan_description": "d", "pathya_apathya": {},
        "weeks": [{"week_number": n, "phase": "x", "daily_plan": {}} for n in returned],
    }

    async def _fake_generate(**kwargs):
        return _json.dumps(payload)

    async def _no_rag(*a, **k):
        return []

    monkeypatch.setattr(gen.llm_client, "generate", _fake_generate)
    monkeypatch.setattr(gen.rag_pipeline, "query", _no_rag)

    result = await gen.generate_diet_plan_llm(
        {"id": "u", "ama_indicator": "none", "bmi_category": "normal"},
        {"diet_goal": "general_wellness"})
    assert result is None, f"a plan with weeks {returned} was accepted"


@pytest.mark.asyncio
async def test_four_weeks_out_of_order_are_accepted_and_sorted(monkeypatch):
    """Order is the model's presentation, not a clinical error — but the plan has to
    come out in the prescribed sequence, because week 3 of a reduction-led arc is not
    interchangeable with week 1."""
    import json as _json

    import services.diet_llm_generator as gen

    payload = {
        "plan_title": "t", "plan_description": "d", "pathya_apathya": {},
        "weeks": [{"week_number": n, "phase": "whatever the model said",
                   "daily_plan": {}} for n in (3, 1, 4, 2)],
    }

    async def _fake_generate(**kwargs):
        return _json.dumps(payload)

    async def _no_rag(*a, **k):
        return []

    monkeypatch.setattr(gen.llm_client, "generate", _fake_generate)
    monkeypatch.setattr(gen.rag_pipeline, "query", _no_rag)

    profile = {"id": "u", "ama_indicator": "none", "ojas_level": "low",
               "bmi_category": "underweight", "age": 26}
    result = await gen.generate_diet_plan_llm(profile, {"diet_goal": "muscle_support"})
    assert result is not None
    assert [w["week_number"] for w in result["diet_weeks"]] == [1, 2, 3, 4]
    # And the labels are the prescription, not the model's echo.
    prescribed = [w["phase"] for w in choose_arc(profile, {})["weeks"]]
    assert [w["phase"] for w in result["diet_weeks"]] == prescribed
