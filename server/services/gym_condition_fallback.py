"""
Dynamic LLM fallback for gym exercise safety on rare / unlisted conditions.

The exercise KB tags exercises with a fixed set of contraindication categories
(heart_disease, hypertension, osteoporosis, herniated_disc, …). For a condition
NOT covered by those tags or the static alias map, we ask the LLM which of the
KNOWN categories apply — a tiny, validated choice — and merge them into the same
deterministic tag gate. The LLM never picks exercises directly and can only return
categories that already exist in the KB, so it cannot invent an unsafe filter.
"""
import json
from core.logger import logger
from ai.llm_client import llm_client

from engine.movement_risk import RISK_VOCAB

# The contraindication vocabulary the exercise KB actually uses, and the movement
# mechanisms beside it. The LLM must pick ONLY from these — anything else is
# dropped. It used to be offered body parts alone, so for epilepsy or glaucoma
# the most it could say was "hypertension", and `ankle_injury` and
# `shin_splints` were on offer while no movement carried either.
GYM_CONTRA_VOCAB: list[str] = [
    "heart_disease", "hypertension", "osteoporosis", "herniated_disc",
    "lower_back_pain", "cervical_spondylosis", "neck_injury", "shoulder_injury",
    "rotator_cuff", "elbow_injury", "wrist_injury", "bad_knee", "knee_replacement",
    "hip_injury", "bad_ankle",
]
GYM_RISK_VOCAB: list[str] = sorted(RISK_VOCAB)
_MECHANISM_GLOSS = {
    "spinal_flexion": "trunk flexion/twisting under load",
    "intracranial_pressure": "head below the heart",
    "abdominal_pressure": "heavy bracing / straining",
    "fall_risk": "loaded single-leg and stepping work",
    "seizure_risk": "a load that lands on the body if control is lost",
    "wrist_weight_bearing": "bodyweight on the wrists",
    "neck_load": "load through the neck",
    "spinal_extension": "loaded lumbar extension",
}

_CACHE: dict[str, list[str]] = {}

_SYSTEM_PROMPT = (
    "You are a clinical exercise physiologist. Given a medical condition, decide which "
    "exercise-risk categories should be avoided for safety. Choose ONLY from the provided "
    "category list. Respond with valid JSON only, no prose."
)


async def _classify_single(condition: str) -> list[str]:
    key = condition.strip().lower()
    if key in _CACHE:
        return _CACHE[key]
    prompt = (
        f"Condition: {condition}\n\n"
        f"Which of these exercise-risk categories should be avoided for this condition? "
        f"Choose only from these lists.\nBody parts: {', '.join(GYM_CONTRA_VOCAB)}\n"
        f"Movement mechanisms: "
        f"{', '.join(f'{k} ({v})' for k, v in _MECHANISM_GLOSS.items())}\n\n"
        'Respond as JSON: {"avoid_categories": ["cat1", "cat2"]}. '
        "Include a category only if exertion of that type is genuinely risky for this "
        "condition (e.g. heart_disease/hypertension for cardiovascular limits, "
        "herniated_disc/lower_back_pain for spinal loading, osteoporosis for high-impact/"
        "axial-load). Empty list if none apply."
    )
    try:
        resp = await llm_client.generate(prompt=prompt, system_prompt=_SYSTEM_PROMPT, json_mode=True)
        data = json.loads(resp) if resp else {}
        cats = data.get("avoid_categories") or data.get("terms") or []
        allowed = set(GYM_CONTRA_VOCAB) | set(GYM_RISK_VOCAB)
        valid = [c for c in (str(x).lower() for x in cats) if c in allowed]
        # de-dupe, preserve order
        seen: list[str] = []
        for c in valid:
            if c not in seen:
                seen.append(c)
        _CACHE[key] = seen
        if seen:
            logger.info(f"Gym fallback: '{condition}' → avoid {seen}")
        return seen
    except Exception as e:
        logger.warning(f"Gym condition fallback failed for '{condition}': {e}")
        return []  # fail-safe: no phantom filter, and don't cache the failure


async def gym_avoid_tags_for_conditions(conditions: list[str]) -> set[str]:
    """Return the union of KB contraindication tags to avoid for the given
    (uncovered) conditions. Safe to call with []; never raises."""
    tags: set[str] = set()
    for c in conditions or []:
        tags.update(await _classify_single(c))
    return tags


def uncovered_conditions(user_profile: dict) -> list[str]:
    """Declared conditions the engine has no rule of any kind for.

    Covered means a body-part tag, a movement mechanism, an impact restriction,
    an intensity ceiling or a before-you-train note — anything the plan would
    act on. Only the rest are worth an LLM call."""
    from services.gym_condition_guidance import guidance_for
    from services.gym_plan_engine import (_condition_contra_tags, _IMPACT_CONDITIONS,
                                          _INTENSITY_CEILING)
    from engine.movement_risk import condition_risk_tags

    contra = set(GYM_CONTRA_VOCAB)
    ceiling = [t for _, terms in _INTENSITY_CEILING for t in terms]
    out = []
    for c in user_profile.get("medical_history") or []:
        low = str(c).lower()
        if (_condition_contra_tags([c]) & contra or condition_risk_tags([c])
                or guidance_for([c]) or any(t in low for t in _IMPACT_CONDITIONS)
                or any(t in low for t in ceiling)):
            continue
        out.append(c)
    return out


async def extra_avoid_tags_for(user_profile: dict) -> set[str]:
    """The single entry both plan paths use. The holistic worker called the
    engine without it, so a rare condition was screened when the gym plan was
    generated on its own and not when it was generated with everything else."""
    uncovered = uncovered_conditions(user_profile)
    return await gym_avoid_tags_for_conditions(uncovered) if uncovered else set()
