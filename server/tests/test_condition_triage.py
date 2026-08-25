"""The LLM triage for diagnoses the knowledge base does not recognise.

Before this layer, an unrecognised diagnosis passed every safety gate by default.
`_match_contraindications` matches tokens; a token no entry lists matches nothing;
matching nothing is indistinguishable from being cleared. Measured across fifteen
unmapped conditions where being wrong is dangerous — chemotherapy, active
tuberculosis, DVT, cardiac stent, pacemaker, gestational diabetes, Addison's,
myasthenia gravis — all fifteen received the byte-identical plan a healthy
forty-year-old gets, ending in therapeutic emesis.
"""
import json
from unittest.mock import AsyncMock, patch

import pytest

from services import condition_triage as ct
from services.panchakarma_engine import generate_panchakarma_plan


def _profile(**over):
    base = dict(id="t", age=40, gender="male", dominant_dosha="kapha",
                vikriti_dominant="kapha", fitness_level="advanced",
                ama_indicator="none", ojas_level="high", digestion_quality="good",
                medical_history=[])
    base.update(over)
    return base


def _prefs(**over):
    base = dict(setting="clinic", available_time_days=21, detox_experience="experienced",
                access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
                self_care_time_per_day="1 hour", panchakarma_goal="detox")
    base.update(over)
    return base


def _finding(**over):
    base = dict(status="ok", condition="chemotherapy", shodhana="permitted",
                hard={}, soft={}, note="", confidence="high")
    base.update(over)
    return {"chemotherapy": base}


GOOD_LLM = {
    "kind": "treatment",
    "note": "Cytotoxic chemotherapy for malignancy.",
    "classical_analogue": "Arbuda with Dhatu Kshaya",
    "dosha": "vata",
    "srotas": "Rasavaha Srotas",
    "shodhana": "contraindicated",
    "karma": {"vamana": "hard", "virechana": "hard", "basti": "soft",
              "nasya": "none", "raktamokshana": "hard"},
    "mechanisms": {
        "vamana": "Emesis in a thrombocytopenic patient risks uncontrolled mucosal bleeding.",
        "virechana": "Purgation compounds the fluid loss and mucositis of cytotoxic therapy.",
        "basti": "Neutropenia makes any rectal instrumentation a bacteraemia risk.",
        "raktamokshana": "Removing blood from a myelosuppressed patient deepens the cytopenia.",
    },
    "monitoring": "Platelet and neutrophil counts before any procedure.",
    "confidence": "high",
}


# ── Validation: only an answer the engine can act on is accepted ──────────────

def test_a_well_formed_assessment_becomes_hard_and_soft_maps():
    out = ct._validate(GOOD_LLM, "chemotherapy")
    assert out is not None
    assert set(out["hard"]) == {"vamana", "virechana", "raktamokshana"}
    assert set(out["soft"]) == {"basti"}
    assert out["reviewed"] is False and out["source"] == "llm_triage"


@pytest.mark.parametrize("mutation,why", [
    ({"kind": "unclear"}, "the model said it could not read the entry"),
    ({"kind": "symptom"}, "a symptom is handled elsewhere, not assessed here"),
    ({"shodhana": "probably fine"}, "verdict outside the accepted set"),
    ({"karma": {"vamana": "maybe"}}, "severity outside the accepted set"),
    ({"karma": "all of them"}, "karma is not a mapping"),
])
def test_an_unusable_assessment_is_rejected_rather_than_repaired(mutation, why):
    """Guessing at what a malformed safety answer meant is the failure this
    module exists to prevent — the output must trace back to a stated mechanism."""
    assert ct._validate({**GOOD_LLM, **mutation}, "chemotherapy") is None, why


def test_a_restriction_without_a_mechanism_is_dropped():
    """A bar nobody can review, argue with, or show the patient is not a bar."""
    out = ct._validate({**GOOD_LLM, "mechanisms": {"vamana": "bad"}}, "chemotherapy")
    assert out is not None
    assert "vamana" not in out["hard"], "kept a restriction with no stated mechanism"


# ── The service fails closed, never open ──────────────────────────────────────

@pytest.mark.asyncio
async def test_an_unreachable_model_reports_unavailable_rather_than_clear():
    with patch.object(ct.cache_manager, "get_plan", AsyncMock(return_value=None)), \
         patch.object(ct.llm_client, "generate", AsyncMock(side_effect=RuntimeError("boom"))):
        out = await ct.triage_conditions(["chemotherapy"])
    assert out["chemotherapy"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_unparseable_output_reports_unavailable():
    with patch.object(ct.cache_manager, "get_plan", AsyncMock(return_value=None)), \
         patch.object(ct.llm_client, "generate", AsyncMock(return_value="not json at all")):
        out = await ct.triage_conditions(["chemotherapy"])
    assert out["chemotherapy"]["status"] == "unavailable"


@pytest.mark.asyncio
async def test_a_good_assessment_is_cached_by_condition_not_by_user():
    """The assessment of a disease does not depend on who has it."""
    setter = AsyncMock()
    with patch.object(ct.cache_manager, "get_plan", AsyncMock(return_value=None)), \
         patch.object(ct.cache_manager, "set_plan", setter), \
         patch.object(ct.llm_client, "generate", AsyncMock(return_value=json.dumps(GOOD_LLM))):
        out = await ct.triage_conditions(["chemotherapy"])

    assert out["chemotherapy"]["status"] == "ok"
    key = setter.await_args.args[1]
    assert key == {"condition": "chemotherapy"}, "cache key must be the condition alone"


# ── The engine acts on it ─────────────────────────────────────────────────────

def test_an_unassessed_diagnosis_withholds_shodhana():
    """Fail closed. This case used to produce full Vamana."""
    plan = generate_panchakarma_plan(_profile(medical_history=["chemotherapy"]), _prefs())
    cd = plan["clinical_decisions"]

    assert cd["shodhana_or_shamana"]["type"] == "shamana"
    assert cd["pradhana_karma_selected"]["primary"] is None
    assert cd["shodhana_or_shamana"]["unassessed_condition"] is True
    # Not a clinical bar: nobody found this patient unfit to purify.
    assert cd["shodhana_or_shamana"]["clinically_ineligible"] is False


def test_an_unavailable_triage_withholds_shodhana():
    triage = {"chemotherapy": {"condition": "chemotherapy", "status": "unavailable",
                               "reason": "the assessment service could not be reached"}}
    plan = generate_panchakarma_plan(_profile(medical_history=["chemotherapy"]),
                                     _prefs(), condition_triage=triage)
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == "shamana"


@pytest.mark.parametrize("verdict,expected", [
    ("contraindicated", "shamana"),
    ("mridu_only", "mridu_shodhana"),
    ("permitted", "shodhana"),
])
def test_each_triage_verdict_reaches_the_plan(verdict, expected):
    plan = generate_panchakarma_plan(
        _profile(medical_history=["chemotherapy"]), _prefs(),
        condition_triage=_finding(shodhana=verdict,
                                  hard={"vamana": "Emesis risks uncontrolled mucosal bleeding."}
                                  if verdict == "contraindicated" else {}))
    assert plan["clinical_decisions"]["shodhana_or_shamana"]["type"] == expected


def test_a_per_karma_restriction_substitutes_the_therapy():
    plan = generate_panchakarma_plan(
        _profile(medical_history=["chemotherapy"]), _prefs(),
        condition_triage=_finding(
            shodhana="permitted",
            hard={"vamana": "Emesis in a thrombocytopenic patient risks mucosal bleeding."}))
    pk = plan["clinical_decisions"]["pradhana_karma_selected"]

    assert pk["primary"] != "vamana"
    assert any("chemotherapy" in w for w in plan["clinical_decisions"]["safety_warnings"])


def test_triage_can_restrict_but_never_unlock():
    """Epilepsy is a HARD KB bar on Vamana. No model answer may lift it."""
    hostile = {"epilepsy": {"status": "ok", "condition": "epilepsy", "shodhana": "permitted",
                            "hard": {}, "soft": {"vamana": "Perfectly safe, proceed at full strength."},
                            "confidence": "high"}}
    plan = generate_panchakarma_plan(_profile(medical_history=["epilepsy"]), _prefs(),
                                     condition_triage=hostile)
    assert plan["clinical_decisions"]["pradhana_karma_selected"]["primary"] != "vamana"


def test_a_recognised_diagnosis_never_reaches_the_triage_at_all():
    """All 71 conditions the onboarding checklist offers are mapped, so the ordinary
    path must not pay for an LLM call."""
    from engine.dosha_analyzer import disease_signal
    plan = generate_panchakarma_plan(_profile(medical_history=["hypertension"]), _prefs())

    assert disease_signal("hypertension") is not None
    assert plan["clinical_decisions"]["condition_triage"] == []
    assert plan["clinical_decisions"]["unmapped_conditions"] == []


# ── A treatment is not a lesser case; a symptom is not an eligibility finding ──

def test_a_treatment_is_assessed_rather_than_declined():
    """"chemotherapy" and "dialysis" are not diseases, and they are the most
    dangerous things the free-text box receives. An earlier draft of the prompt told
    the model to decline them for exactly that reason."""
    out = ct._validate(GOOD_LLM, "chemotherapy")
    assert out is not None and out["kind"] == "treatment"
    assert out["hard"], "a treatment must be able to carry restrictions"


@pytest.mark.asyncio
async def test_a_symptom_is_recorded_without_withholding_anything():
    symptom = {**GOOD_LLM, "kind": "symptom", "note": "A complaint, not a diagnosis."}
    with patch.object(ct.cache_manager, "get_plan", AsyncMock(return_value=None)), \
         patch.object(ct.cache_manager, "set_plan", AsyncMock()), \
         patch.object(ct.llm_client, "generate", AsyncMock(return_value=json.dumps(symptom))):
        out = await ct.triage_conditions(["back_pain"])
    assert out["back_pain"]["status"] == "not_a_diagnosis"


def test_a_symptom_does_not_withhold_shodhana():
    """Otherwise writing "back pain" in a free-text box costs a patient the cleanse,
    which makes the safe path the useless one for a large, ordinary set of users."""
    triage = {"back_pain": {"condition": "back_pain", "status": "not_a_diagnosis",
                            "kind": "symptom", "reason": "a complaint, not a diagnosis"}}
    plan = generate_panchakarma_plan(_profile(medical_history=["back_pain"]), _prefs(),
                                     condition_triage=triage)
    cd = plan["clinical_decisions"]

    assert cd["shodhana_or_shamana"]["type"] == "shodhana"
    assert cd["pradhana_karma_selected"]["primary"] is not None
    assert cd["condition_triage"][0]["outcome"] == "not_a_diagnosis", "still recorded"


def test_common_phrasings_of_a_known_disease_never_reach_the_triage():
    """Fail-closed makes recognition load-bearing: a typing variant of one of the
    commonest diseases in the product must not become a withheld plan.

    `diabetes_type_2` and `diabetes_type2` differ by one underscore, and the first
    resolved to nothing.
    """
    from engine.dosha_analyzer import disease_signal
    for phrasing in ("diabetes_type_2", "diabetes type 2", "type 2 diabetes",
                     "diabetes_type2", "low bp", "ckd", "high bp"):
        assert disease_signal(phrasing) is not None, f"{phrasing!r} fell through to triage"


# ── The assessed Dosha steers the pool, and only the pool ────────────────────
#
# A disease the KB knows contributes its Dosha through `disease_signal`. A disease
# it does not know contributed nothing: two patients with two different unmapped
# diagnoses got byte-identical schedules, because the only thing their diagnosis
# changed was the sentence naming it. The triage has always returned a Dosha for
# the conditions it can place; the engine only ever printed it.

def _tri(condition, dosha, verdict="permitted", hard=None):
    return {condition: {"condition": condition, "status": "ok", "kind": "disease",
                        "shodhana": verdict, "dosha": dosha,
                        "hard": hard or {}, "soft": {},
                        "source": "llm_triage", "reviewed": False}}


def _pk_profile(**over):
    base = dict(id="t", age=40, gender="male", dominant_dosha="vata", vikriti_dominant="vata",
                fitness_level="advanced", ama_indicator="none", ojas_level="high",
                digestion_quality="good", medical_history=["some rare disease"])
    base.update(over)
    return base


def _pk_prefs(**over):
    base = dict(setting="home", available_time_days=14, detox_experience="experienced",
                access_to_ayurvedic_herbs="yes", diet_adherence_ability="strict",
                self_care_time_per_day="2 hours", panchakarma_goal="detox")
    base.update(over)
    return base


def test_assessed_dosha_changes_the_schedule():
    """Otherwise the field is decoration — which is what it was."""
    import json
    from services.panchakarma_engine import generate_panchakarma_plan
    plans = {
        d: json.dumps(generate_panchakarma_plan(
            _pk_profile(), _pk_prefs(), None,
            condition_triage=_tri("some rare disease", d))["daily_schedule"],
            sort_keys=True, default=str)
        for d in ("vata", "pitta", "kapha")
    }
    assert len(set(plans.values())) > 1, \
        "every assessed Dosha produced the same schedule — the signal is inert"


def test_assessed_dosha_never_outranks_the_vitiated_dosha():
    """It is a preference-strength signal. A therapy that aggravates the Dosha the
    patient is actually vitiated in must not be promoted over one that pacifies it,
    however the triage reads the disease."""
    from services.panchakarma_engine import filter_and_score_therapies, pk_therapies
    for vikriti in ("vata", "pitta", "kapha"):
        for triage_dosha in ("vata", "pitta", "kapha"):
            pool = filter_and_score_therapies(
                _pk_profile(dominant_dosha=vikriti, vikriti_dominant=vikriti),
                _pk_prefs(), "purvakarma", pk_therapies, vikriti,
                [("some rare disease", triage_dosha)])
            aggravating = [i for i, t in enumerate(pool)
                           if t.get("dosha_effect", {}).get(vikriti, 0) > 0]
            pacifying = [i for i, t in enumerate(pool)
                         if t.get("dosha_effect", {}).get(vikriti, 0) < 0]
            if aggravating and pacifying:
                assert min(aggravating) > max(pacifying), (
                    f"vikriti={vikriti} triage={triage_dosha}: a therapy that aggravates "
                    "the vitiated Dosha was ranked above one that pacifies it")


def test_assessed_dosha_does_not_choose_the_karma():
    """Karma follows Vikriti or Ritu — never an AI reading of a diagnosis."""
    from services.panchakarma_engine import generate_panchakarma_plan
    karmas = {
        d: generate_panchakarma_plan(
            _pk_profile(), _pk_prefs(setting="clinic"), None,
            condition_triage=_tri("some rare disease", d)
        )["clinical_decisions"]["pradhana_karma_selected"]["primary"]
        for d in ("vata", "pitta", "kapha")
    }
    assert len(set(karmas.values())) == 1, f"the triage Dosha moved the Karma: {karmas}"


def test_assessed_dosha_cannot_lift_a_contraindication():
    """Restrict-only holds for this field too: an answer that places the disease in
    a convenient Dosha must not soften a bar the same answer declares."""
    from services.panchakarma_engine import generate_panchakarma_plan
    plan = generate_panchakarma_plan(
        _pk_profile(dominant_dosha="kapha", vikriti_dominant="kapha"),
        _pk_prefs(setting="clinic"), None,
        condition_triage=_tri("some rare disease", "kapha", verdict="contraindicated",
                              hard={"vamana": "a stated mechanism long enough to count"}))
    cd = plan["clinical_decisions"]
    assert cd["shodhana_or_shamana"]["type"] == "shamana"
    assert cd["pradhana_karma_selected"]["primary"] is None


def test_the_influence_is_stated_and_labelled():
    """A signal that changes the plan and is not stated is one nobody can argue
    with — and this one is AI-derived."""
    from services.panchakarma_engine import generate_panchakarma_plan
    plan = generate_panchakarma_plan(
        _pk_profile(), _pk_prefs(), None,
        condition_triage=_tri("some rare disease", "pitta"))
    influence = plan["clinical_decisions"]["triage_dosha_influence"]
    assert influence and influence[0]["dosha"] == "pitta"
    assert influence[0]["source"] == "llm_triage"
    assert influence[0]["reviewed"] is False


def test_no_triage_leaves_scoring_untouched():
    import json
    from services.panchakarma_engine import generate_panchakarma_plan
    a = generate_panchakarma_plan(_pk_profile(medical_history=[]), _pk_prefs(), None)
    b = generate_panchakarma_plan(_pk_profile(medical_history=[]), _pk_prefs(), None,
                                  condition_triage={})
    assert (json.dumps(a["daily_schedule"], sort_keys=True, default=str)
            == json.dumps(b["daily_schedule"], sort_keys=True, default=str))
    assert a["clinical_decisions"]["triage_dosha_influence"] == []


def test_an_unplaceable_dosha_is_ignored_not_guessed():
    from services.panchakarma_engine import _triage_dosha_signals
    assert _triage_dosha_signals({"x": {"status": "ok", "dosha": "tridosha"}}) == []
    assert _triage_dosha_signals({"x": {"status": "unavailable", "dosha": "vata"}}) == []
    assert _triage_dosha_signals({"x": {"status": "ok", "dosha": "vata"}}) == [("x", "vata")]


# ── Grounding ────────────────────────────────────────────────────────────────
#
# This was the only LLM call in the plan path with no retrieval. Every other one is
# grounded — `panchakarma_enricher` pulls six documents from ChromaDB before writing
# a sentence of narrative. This call decides whether a patient is barred from
# therapeutic emesis, and it answered from model priors. The ordering was backwards.

_ANSWER = json.dumps({
    "kind": "disease", "note": "n", "classical_analogue": "Mamsagata Vata",
    "dosha": "vata", "srotas": "Mamsavaha", "shodhana": "contraindicated",
    "karma": {"vamana": "hard", "virechana": "none", "basti": "none",
              "nasya": "none", "raktamokshana": "none"},
    "mechanisms": {"vamana": "Neuromuscular weakness makes airway reflexes unreliable"},
    "monitoring": None, "confidence": "medium",
})


def _no_cache():
    return (patch.object(ct.cache_manager, "get_plan", AsyncMock(return_value=None)),
            patch.object(ct.cache_manager, "set_plan", AsyncMock()))


async def _run_triage(condition, rag_side_effect=None, rag_return=None, capture=None):
    import ai.rag_pipeline as rp

    async def fake_gen(prompt, system_prompt, temperature, json_mode):
        if capture is not None:
            capture["prompt"] = prompt
        return _ANSWER

    get_p, set_p = _no_cache()
    rag_kw = {"side_effect": rag_side_effect} if rag_side_effect else {"return_value": rag_return or []}
    with patch.object(ct.llm_client, "generate", side_effect=fake_gen), get_p, set_p, \
            patch.object(rp.rag_pipeline, "query", AsyncMock(**rag_kw)):
        return await ct._triage_one(condition)


@pytest.mark.asyncio
async def test_the_assessment_is_grounded_in_the_corpus():
    capture = {}
    result = await _run_triage(
        "myasthenia gravis",
        rag_return=[{"content": "Vamana expels Kapha; withheld in depleted Bala.",
                     "metadata": {"source": "panchakarma_protocols"}}],
        capture=capture)
    assert result["grounded"] is True
    assert result["context_sources"] == ["panchakarma_protocols"]
    assert "CLASSICAL CONTEXT" in capture["prompt"]


@pytest.mark.asyncio
async def test_retrieved_context_is_framed_as_background_not_evidence():
    """The corpus cannot contain the disease — that is what makes it unrecognised.
    A retrieval that looks relevant and is not is worse than none, so the prompt has
    to say what the context is and is not."""
    capture = {}
    await _run_triage("myasthenia gravis",
                      rag_return=[{"content": "x", "metadata": {"source": "s"}}],
                      capture=capture)
    assert "NOT necessarily about the diagnosis" in capture["prompt"]


@pytest.mark.asyncio
async def test_a_missing_corpus_degrades_but_does_not_withhold():
    """Retrieval failure is not assessment failure. Failing closed on an unreachable
    ChromaDB would cost the cleanse to everyone with an off-list diagnosis whenever
    the vector store hiccups — the LLM is still reachable and still answering."""
    capture = {}
    result = await _run_triage("myasthenia gravis",
                               rag_side_effect=RuntimeError("chroma down"),
                               capture=capture)
    assert result["status"] == "ok"
    assert result["grounded"] is False
    assert result["hard"] == {"vamana": "Neuromuscular weakness makes airway reflexes unreliable"}
    assert "no higher" in capture["prompt"], "an ungrounded answer must cap its own confidence"


@pytest.mark.asyncio
async def test_grounding_does_not_loosen_restrict_only():
    """Context is background, not permission. The bars the answer declares survive
    whether or not anything was retrieved."""
    grounded = await _run_triage("myasthenia gravis",
                                 rag_return=[{"content": "Vamana is the Kapha cleanse.",
                                              "metadata": {"source": "s"}}])
    ungrounded = await _run_triage("myasthenia gravis", rag_side_effect=RuntimeError("down"))
    assert grounded["hard"] == ungrounded["hard"]
    assert grounded["shodhana"] == ungrounded["shodhana"] == "contraindicated"
