"""
Regression tests for the Prakriti/Vikriti assessment (engine/dosha_analyzer.py).

Locks in the agni-flow-through fix: the quiz self-reports Agni (Vishama/Tikshna/
Manda/Sama), but the LLM JSON schema never requested `agni_type`, so it arrived
as None and every downstream engine (diet, routine, panchakarma) silently
defaulted to "sama" — disabling the agni-aware adaptations. Agni is now carried
through deterministically in classical form, on both the LLM and fallback paths.
"""
import pytest
from unittest.mock import AsyncMock, patch


@pytest.mark.asyncio
@pytest.mark.parametrize("quiz_value,expected", [
    ("kapha", "manda"),     # Manda Agni
    ("pitta", "tikshna"),   # Tikshna Agni
    ("vata", "vishama"),    # Vishama Agni
    ("sama", "sama"),       # Sama Agni
])
async def test_agni_type_carried_through_on_fallback(quiz_value, expected):
    """Even when the LLM path fails (→ rule-based fallback), the self-reported
    Agni must reach the result in classical form."""
    from engine.dosha_analyzer import assess_dosha_with_llm
    with patch("ai.llm_client.llm_client") as mock_llm:
        mock_llm.generate = AsyncMock(side_effect=RuntimeError("llm down"))
        result = await assess_dosha_with_llm(
            {"body_frame": quiz_value, "agni_type": quiz_value},
            current_symptoms=[],
            user_profile={"age": 40},
        )
    assert result["agni_type"] == expected


@pytest.mark.asyncio
async def test_numbers_are_deterministic_not_from_llm():
    """Authority inversion: even if the LLM returns a wildly different
    constitution, the authoritative Prakriti numbers come from the deterministic
    engine (reproducible + vaidya-auditable). The LLM only writes narrative."""
    from engine.dosha_analyzer import assess_dosha_with_llm, _rule_based_assessment

    # Clearly Vata-dominant answers
    traits = {"body_frame": "vata", "skin": "vata", "digestion": "vata",
              "agni_type": "vata", "stool_pattern": "vata", "energy": "vata"}

    # LLM mocked to insist it's Kapha — must be ignored for the numbers
    llm_json = (
        '{"prakriti":{"vata":5,"pitta":5,"kapha":90},'
        '"vikriti":{"vata":5,"pitta":5,"kapha":90},'
        '"prakriti_dominant":"kapha","prakriti_secondary":"pitta",'
        '"vikriti_dominant":"kapha","constitution_type":"kapha",'
        '"confidence":"high","explanation":"LLM claims Kapha",'
        '"key_signals":["x"],"contradictions":[],"manas_prakriti":"Sattvic Kapha",'
        '"ama_indicator":"none","ojas":{"score":70,"level":"medium"},'
        '"primary_gunas":["Guru"]}'
    )
    with patch("ai.llm_client.llm_client") as mock_llm:
        mock_llm.generate = AsyncMock(return_value=llm_json)
        r = await assess_dosha_with_llm(traits, [], {"age": 30})

    det = _rule_based_assessment(traits, [], age=30)
    assert r["prakriti_dominant"] == det["prakriti_dominant"] == "vata"
    assert r["prakriti"]["kapha"] != 90        # LLM's number rejected
    assert r["prakriti"] == det["prakriti"]    # engine owns the numbers


def test_manasa_prakriti_scores_sum_to_100_and_pick_dominant():
    """Triguna (Satva/Rajas/Tamas) scoring feeds the Manasa Prakriti bars in the
    result UI — it must normalise to 100 and surface the dominant guna + label."""
    from routes.profile import _compute_manasa_prakriti
    out = _compute_manasa_prakriti({
        "motivation_source": "satva", "mind_clarity": "satva",
        "emotional_quality": "satva", "daily_discipline": "rajas",
        "conflict_approach": "tamas",
    })
    assert out["satva"] + out["rajas"] + out["tamas"] == 100
    assert out["dominant_guna"] == "satva"
    assert out["label"] == "Sattvika"
    assert out["description"]


def test_rule_based_confidence_low_on_ambiguous_input():
    """A sparse / evenly-split assessment must report low confidence so the UI's
    clarify follow-up flow triggers (it gates on dosha_confidence < 45)."""
    from engine.dosha_analyzer import _rule_based_assessment, _confidence_score
    # Only two traits, one each — no clear dominance.
    r = _rule_based_assessment({"body_frame": "vata", "skin": "kapha"}, [])
    assert r["confidence"] == "low"
    assert _confidence_score(r["confidence"]) < 45


def test_rule_based_confidence_not_low_on_clear_input():
    """A full, strongly Vata-leaning assessment must NOT report low confidence, so
    the clarify follow-up flow is skipped (the UI gates clarify on score < 45)."""
    from engine.dosha_analyzer import _rule_based_assessment, _confidence_score
    traits = {
        "body_frame": "vata", "digestion": "vata", "agni_type": "vata",
        "sleep": "vata", "temperature": "vata", "stress_response": "vata",
        "memory": "vata", "nadi_rhythm": "vata",
        "decision_making": "pitta", "speech": "pitta", "energy": "kapha",
    }
    r = _rule_based_assessment(traits, [])
    assert r["confidence"] in ("high", "medium")
    assert _confidence_score(r["confidence"]) >= 45


@pytest.mark.asyncio
async def test_assessment_falls_back_to_rule_based_on_llm_error():
    """An LLM failure must never break the assessment — it degrades to the
    deterministic rule-based scorer with a valid Prakriti/Vikriti."""
    from engine.dosha_analyzer import assess_dosha_with_llm
    with patch("ai.llm_client.llm_client") as mock_llm:
        mock_llm.generate = AsyncMock(side_effect=RuntimeError("llm down"))
        r = await assess_dosha_with_llm(
            {"body_frame": "pitta", "agni_type": "pitta", "skin": "pitta"},
            current_symptoms=["heartburn_acidity"],
            user_profile={"age": 35},
        )
    for key in ("prakriti", "vikriti"):
        assert set(r[key]) == {"vata", "pitta", "kapha"}
        assert abs(sum(r[key].values()) - 100) <= 1
    assert r["prakriti_dominant"] in ("vata", "pitta", "kapha")


def test_blended_trait_shares_65_35():
    """A 'vata+pitta' answer must split its weight across both doshas, primary-first."""
    from engine.dosha_analyzer import _trait_dosha_shares
    assert _trait_dosha_shares("vata") == {"vata": 1.0}
    assert _trait_dosha_shares("vata+pitta") == {"vata": 0.65, "pitta": 0.35}
    # Order matters: primary is whichever is listed first.
    assert _trait_dosha_shares("pitta+vata") == {"pitta": 0.65, "vata": 0.35}


def test_blended_trait_moves_score_vs_single():
    """Blending a trait toward a second dosha must raise that dosha's Prakriti share
    (verified on a balanced set that stays under the 55% self-report cap)."""
    from engine.dosha_analyzer import _rule_based_assessment
    # Roughly 40/30/30 — no dosha near the cap, so redistribution artifacts don't
    # mask the effect of the blend.
    base = {
        "body_frame": "vata", "skin": "vata", "hair": "vata", "energy": "vata",
        "digestion": "pitta", "temperature": "pitta", "memory": "pitta",
        "sleep": "kapha", "stress_response": "kapha", "decision_making": "kapha",
    }
    single = _rule_based_assessment(base, [])
    blended = _rule_based_assessment({**base, "skin": "vata+kapha"}, [])
    assert blended["prakriti"]["kapha"] > single["prakriti"]["kapha"]
    assert blended["prakriti"]["vata"] < single["prakriti"]["vata"]


def test_common_lay_conditions_now_map():
    """Previously-silent free-text conditions must resolve to a dosha signal."""
    from engine.dosha_analyzer import disease_signal
    for term in ("thyroid", "cold", "common cold", "cough", "sugar",
                 "cholesterol", "acidity", "bp", "flu"):
        assert disease_signal(term) is not None, f"{term!r} should now map"


def test_unmapped_conditions_are_surfaced_not_silent():
    """A condition outside the dosha map must be reported back, never dropped silently."""
    from engine.dosha_analyzer import _medical_history_vikriti_signal, _rule_based_assessment
    sig, notes, unmapped = _medical_history_vikriti_signal(["diabetes", "sarcoidosis", "hemophilia"])
    assert sig  # the mapped diabetes still produces a signal
    assert "Sarcoidosis" in unmapped and "Hemophilia" in unmapped
    # Surfaced in the assessment result (both a dedicated field and a key signal).
    traits = {"body_frame": "vata", "digestion": "vata", "skin": "vata"}
    r = _rule_based_assessment(traits, [], medical_history=["sarcoidosis"])
    assert "Sarcoidosis" in r["unmapped_conditions"]
    assert any("outside dosha mapping" in s for s in r["key_signals"])


@pytest.mark.asyncio
async def test_rare_disease_classified_by_llm_contributes_to_vikriti():
    """A disease outside the static map is LLM-classified and then actually feeds
    the Vikriti signal (not merely noted), tagged AI-inferred."""
    import json
    import engine.dosha_analyzer as d
    d._DISEASE_CLASSIFY_CACHE.clear()
    fake = json.dumps({"castleman disease": {
        "p": "kapha", "w": 2.2, "s2": "pitta", "w2": 1.0,
        "s": "Rasavaha Srotas", "c": "Kaphaja Granthi", "d": "rasa"}})
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(return_value=fake)
        extra = await d._classify_unmapped_diseases_llm(["castleman disease"])
    assert extra and extra["castleman disease"]["p"] == "kapha"
    sig, notes, unmapped = d._medical_history_vikriti_signal(
        ["castleman disease"], extra_signals=extra
    )
    assert sig["kapha"] > sig["vata"]          # it moved the signal
    assert unmapped == []                        # no longer silently dropped
    assert any("AI-inferred" in n for n in notes)


@pytest.mark.asyncio
async def test_llm_classification_failure_leaves_condition_unmapped_not_crashing():
    """If the LLM can't classify, the condition stays surfaced-but-unmapped; no crash."""
    import engine.dosha_analyzer as d
    d._DISEASE_CLASSIFY_CACHE.clear()
    with patch("ai.llm_client.llm_client") as m:
        m.generate = AsyncMock(side_effect=RuntimeError("llm down"))
        extra = await d._classify_unmapped_diseases_llm(["zzz unknown syndrome"])
    assert extra == {}
    _, _, unmapped = d._medical_history_vikriti_signal(["zzz unknown syndrome"], extra_signals=extra)
    assert "Zzz Unknown Syndrome" in unmapped


def test_contradictions_are_deterministic():
    """Same answers → same contradictions, every time (no LLM in the loop)."""
    from engine.dosha_analyzer import _rule_based_assessment
    # Kapha body but Pitta mind + Pitta-sharp Agni → a genuine Deha–Manas conflict.
    traits = {
        "body_frame": "kapha", "skin": "kapha", "hair": "kapha",
        "temperature": "kapha", "energy": "kapha", "sleep": "kapha",
        "stress_response": "pitta", "memory": "pitta", "decision_making": "pitta",
        "emotional_nature": "pitta", "speech": "pitta",
        "agni_type": "pitta",
    }
    r1 = _rule_based_assessment(traits, [])
    r2 = _rule_based_assessment(traits, [])
    assert r1["contradictions"] == r2["contradictions"]
    assert len(r1["contradictions"]) >= 1
    # A uniform constitution has no contradictions.
    calm = {k: "vata" for k in traits}
    assert _rule_based_assessment(calm, [])["contradictions"] == []
