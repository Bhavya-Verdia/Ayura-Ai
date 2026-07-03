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

# The contraindication vocabulary the exercise KB actually uses. The LLM must pick
# ONLY from this set — anything else is dropped.
GYM_CONTRA_VOCAB: list[str] = [
    "heart_disease", "hypertension", "osteoporosis", "herniated_disc",
    "lower_back_pain", "cervical_spondylosis", "neck_injury", "shoulder_injury",
    "rotator_cuff", "elbow_injury", "wrist_injury", "bad_knee", "knee_replacement",
    "hip_injury", "bad_ankle", "ankle_injury", "shin_splints",
]

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
        f"Choose only from this list:\n{', '.join(GYM_CONTRA_VOCAB)}\n\n"
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
        valid = [c for c in (str(x).lower() for x in cats) if c in GYM_CONTRA_VOCAB]
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
