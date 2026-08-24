"""LLM triage for conditions the knowledge base does not recognise.

## Why this exists

`disease_signal` knows 102 diseases and the onboarding checklist offers 71, all of
which map. Onboarding also has a free-text box, and that is where the coverage ends:
of conditions users plausibly type by hand, roughly 30% of common off-list diagnoses
and 5% of rare ones resolve to anything at all.

An unrecognised condition did not merely go un-personalised — it **passed every
safety gate by default**. `_match_contraindications` matches tokens; a token no
entry lists matches nothing; matching nothing is indistinguishable from being
cleared. Measured across fifteen unmapped conditions where being wrong is dangerous
— chemotherapy, radiotherapy, active tuberculosis, DVT, cardiac stent, pacemaker,
gestational diabetes, hepatitis B, Addison's, myasthenia gravis among them — all
fifteen received the **identical full Vamana plan a healthy forty-year-old gets**.

## Why the enricher could not fix it

`panchakarma_enricher` already sends unmapped conditions to the LLM as
`rare_disease_assessment`. It runs *after* the engine and merges narrative keys
only, so the LLM can state that a therapy is contraindicated in one field while the
calendar schedules it on day four. That was demonstrated, not assumed: a mocked LLM
returning "CONTRAINDICATED — Vamana must not be performed during active
chemotherapy" left `pradhana_karma_selected.primary == "vamana"` and Vamana on the
schedule. The narrative and the plan contradicted each other, and the better the
LLM answered the worse the contradiction looked.

So triage runs BEFORE the engine and returns the same shape the KB uses —
`hard`/`soft` token→mechanism maps — which the existing deterministic gate consumes
exactly as if a human had authored it.

## The three rules that make this safe

1. **Restrict only, never unlock.** The triage may add contraindications. It has no
   representation for removing one, so no LLM answer can lift a bar a vaidya wrote.
   The engine merges KB entries *over* triage entries for the same token.
2. **Fail closed.** If the LLM is unreachable, returns unparseable JSON, or answers
   in a shape this module does not accept, the condition's status is not `ok` and
   the caller withholds Shodhana. Today the same failure proceeds to full Vamana.
   A therapy that induces vomiting should not be the default for a diagnosis the
   system could not read.
3. **Never authored, always labelled.** Every entry carries `source: "llm_triage"`
   and `reviewed: false`, and travels to the patient as a Vaidya-review flag. This
   is a floor under an unrecognised diagnosis, not a substitute for a vaidya.
"""
import json
import logging

from ai.llm_client import llm_client
from core.cache import cache_manager

logger = logging.getLogger(__name__)

# The only Karmas the engine can schedule. An answer naming anything else is
# discarded rather than translated — a triage that can invent a therapy name is a
# triage that can put one on a calendar.
_KARMAS = ("vamana", "virechana", "basti", "nasya", "raktamokshana")
_SEVERITIES = ("hard", "soft", "none")
_SHODHANA_VERDICTS = ("permitted", "mridu_only", "contraindicated")

# What the entry in the box actually is. The distinction decides whether failing to
# assess it withholds Shodhana:
#   disease / treatment  assess it. A treatment is not a lesser case — "chemotherapy"
#                        and "dialysis" are among the most dangerous things the box
#                        can contain, and an earlier draft of this prompt told the
#                        model to decline them for not being diseases.
#   symptom              "back pain", "hair fall", "gas problem". Not an eligibility
#                        finding, and withholding purification over one would punish
#                        a patient for describing themselves in ordinary words.
#   unclear              cannot be read. This is the case that fails closed.
_KINDS = ("disease", "treatment", "symptom", "unclear")

CACHE_PREFIX = "condition_triage"
CACHE_TTL_SECONDS = 30 * 24 * 3600  # The assessment of a disease is not user-specific.

_SYSTEM_PROMPT = """You are a senior Vaidya (MD Ayurveda) with clinical training in modern medicine, performing a SAFETY TRIAGE for a Panchakarma engine.

You are given a diagnosis the engine's knowledge base does not recognise. Your only job is to decide whether each of the five Shodhana procedures is safe for a patient with that diagnosis, and to state the mechanism for every restriction you impose.

The five procedures and what they physically do:
- vamana: therapeutic emesis. Repeated forceful vomiting. Valsalva strain, large fluid shifts, aspiration risk, oesophageal and gastric pressure.
- virechana: therapeutic purgation. Fluid and electrolyte loss, sustained stimulation of inflamed or fragile GI mucosa.
- basti: medicated enema. Rectal instillation and retention; pelvic and rectal pressure; absorption via colonic mucosa.
- nasya: nasal instillation of medicated oil. The mildest of the five.
- raktamokshana: bloodletting or leeching. Removes blood volume.

RULES YOU MUST FOLLOW:
- You may only RESTRICT. You are never asked whether to permit something; the engine decides that. Saying "none" means only that you found no reason to restrict.
- "hard" = do not perform this procedure on this patient. "soft" = perform with a stated modification or extra monitoring. "none" = no restriction you can identify.
- Every "hard" and every "soft" MUST have a mechanism: the specific physiological or classical reason this diagnosis and this procedure conflict. One sentence. No mechanism means no restriction — do not pad.
- Classify what you were given in "kind" before anything else:
  - "disease": a named diagnosis.
  - "treatment": an ongoing therapy or device rather than a disease — "chemotherapy", "dialysis", "cardiac stent", "pacemaker", "transplant". ASSESS THESE FULLY. They are among the most dangerous entries this box receives, and what matters is the state the patient is in because of them.
  - "symptom": a complaint rather than a diagnosis — "back pain", "hair fall", "gas", "tiredness". Assess nothing; the engine handles symptoms elsewhere.
  - "unclear": you cannot tell what this is, or cannot assess it. Say so rather than guessing — an unclear entry causes purification to be withheld, which is the safe outcome.
- Never guess. "unclear" is always available and is never the wrong answer when you are unsure.
- Be conservative in proportion to how depleting the procedure is. Vamana and Raktamokshana deplete most.

Respond ONLY with valid JSON matching the schema given. No preamble, no markdown fences."""

_USER_PROMPT = """Diagnosis as the patient entered it: "{condition}"

Return exactly this JSON:

{{
  "kind": "disease" | "treatment" | "symptom" | "unclear",
  "note": "One line: what this is. If unclear, why you could not assess it.",
  "classical_analogue": "Closest classical Ayurvedic disease name, or null",
  "dosha": "vata" | "pitta" | "kapha" | null,
  "srotas": "Primary Srotas involved, or null",
  "shodhana": "permitted" | "mridu_only" | "contraindicated",
  "karma": {{
    "vamana": "hard" | "soft" | "none",
    "virechana": "hard" | "soft" | "none",
    "basti": "hard" | "soft" | "none",
    "nasya": "hard" | "soft" | "none",
    "raktamokshana": "hard" | "soft" | "none"
  }},
  "mechanisms": {{
    "<karma name>": "One sentence naming the mechanism. Required for every karma you marked hard or soft."
  }},
  "monitoring": "What a supervising Vaidya must watch specifically for this diagnosis, or null",
  "confidence": "high" | "medium" | "low"
}}"""


def _validate(raw: dict, condition: str) -> dict | None:
    """Accept only an answer this module can act on. Anything else fails closed.

    Silently repairing a malformed answer is the failure this whole module exists to
    prevent — a triage that guesses at what the LLM meant is a triage whose output
    nobody can trace back to a stated mechanism.
    """
    if not isinstance(raw, dict):
        return None
    if raw.get("kind") not in ("disease", "treatment"):
        return None
    if raw.get("shodhana") not in _SHODHANA_VERDICTS:
        return None

    karma = raw.get("karma")
    if not isinstance(karma, dict):
        return None

    mechanisms = raw.get("mechanisms") if isinstance(raw.get("mechanisms"), dict) else {}

    hard: dict[str, str] = {}
    soft: dict[str, str] = {}
    for k in _KARMAS:
        severity = karma.get(k)
        if severity not in _SEVERITIES:
            return None            # an unusable answer for one Karma taints the set
        if severity == "none":
            continue
        mechanism = mechanisms.get(k)
        if not isinstance(mechanism, str) or len(mechanism.strip()) < 15:
            # A restriction without a mechanism cannot be reviewed, argued with, or
            # shown to the patient. The KB's own rule; it applies to this layer too.
            continue
        (hard if severity == "hard" else soft)[k] = mechanism.strip()

    return {
        "condition": condition,
        "kind": raw["kind"],
        "note": raw.get("note") or "",
        "classical_analogue": raw.get("classical_analogue") or None,
        "dosha": raw.get("dosha") if raw.get("dosha") in ("vata", "pitta", "kapha") else None,
        "srotas": raw.get("srotas") or None,
        "shodhana": raw["shodhana"],
        "hard": hard,
        "soft": soft,
        "monitoring": raw.get("monitoring") or None,
        "confidence": raw.get("confidence") if raw.get("confidence") in ("high", "medium", "low") else "low",
        "source": "llm_triage",
        "reviewed": False,
    }


async def _triage_one(condition: str) -> dict:
    cache_key = {"condition": condition.strip().lower()}
    try:
        if cached := await cache_manager.get_plan(CACHE_PREFIX, cache_key):
            return cached
    except Exception as e:                                   # cache is never load-bearing
        logger.warning(f"condition triage cache read failed for {condition!r}: {e}")

    try:
        text = await llm_client.generate(
            prompt=_USER_PROMPT.format(condition=condition),
            system_prompt=_SYSTEM_PROMPT,
            temperature=0.2,     # a safety assessment is not a place for variety
            json_mode=True,
        )
        parsed = json.loads(text)
    except Exception as e:
        logger.error(f"condition triage LLM call failed for {condition!r}: {e}")
        return {"condition": condition, "status": "unavailable",
                "reason": "the assessment service could not be reached"}

    note = parsed.get("note") if isinstance(parsed, dict) else None

    if isinstance(parsed, dict) and parsed.get("kind") == "symptom":
        # Not an eligibility finding. Withholding purification because somebody
        # wrote "back pain" in a free-text box would make the safe path the useless
        # one for a large number of perfectly ordinary users.
        result = {"condition": condition, "status": "not_a_diagnosis", "kind": "symptom",
                  "reason": note or "read as a symptom rather than a diagnosis"}
        try:
            await cache_manager.set_plan(CACHE_PREFIX, cache_key, result, expire=CACHE_TTL_SECONDS)
        except Exception as e:
            logger.warning(f"condition triage cache write failed for {condition!r}: {e}")
        return result

    validated = _validate(parsed, condition)
    if validated is None:
        logger.info(f"condition triage returned no usable assessment for {condition!r}")
        return {"condition": condition, "status": "unassessable",
                "reason": note or "the assessment could not read this as a diagnosis it can evaluate"}

    result = {**validated, "status": "ok"}
    try:
        await cache_manager.set_plan(CACHE_PREFIX, cache_key, result, expire=CACHE_TTL_SECONDS)
    except Exception as e:
        logger.warning(f"condition triage cache write failed for {condition!r}: {e}")
    return result


async def triage_conditions(conditions: list[str]) -> dict[str, dict]:
    """Assess each unrecognised condition. Never raises — the caller fails closed.

    Sequential rather than gathered: the list is short (a user has one or two
    unmapped diagnoses, not twenty), the cache makes repeats free, and a burst of
    parallel LLM calls per plan request is the kind of thing that takes the quota
    down for everyone.
    """
    out: dict[str, dict] = {}
    for condition in conditions:
        if not condition or not condition.strip():
            continue
        try:
            out[condition] = await _triage_one(condition)
        except Exception as e:                              # belt and braces
            logger.error(f"condition triage crashed for {condition!r}: {e}")
            out[condition] = {"condition": condition, "status": "unavailable",
                              "reason": "the assessment service could not be reached"}
    return out
