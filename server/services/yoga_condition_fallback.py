"""
Dynamic LLM fallback for yoga conditions not in the 30-protocol database.
Generates mini-protocols on-the-fly and caches them in memory.
"""
import json
from core.logger import logger
from ai.llm_client import llm_client

# In-memory cache — persists for the lifetime of the process (shared across requests)
_CACHE: dict[str, dict] = {}

_SYSTEM_PROMPT = """You are an Ayurvedic yoga therapist specialised in therapeutic yoga protocols for rare and unlisted medical conditions.

Generate a minimal evidence-based yoga protocol for the given condition, selecting ONLY from the provided pose and pranayama ID lists.

Respond ONLY with a valid JSON object — no markdown, no explanation:
{
  "condition": "condition_name_lowercase_underscore",
  "name": "Condition Name Therapeutic Yoga Protocol",
  "priority_pose_ids": ["id1", "id2"],
  "priority_pranayama_ids": ["id1", "id2"],
  "avoid_pranayama_ids": ["id1"],
  "avoid_pose_ids": ["id1"],
  "category_emphasis": ["restorative", "seated"],
  "sequence_note": "One actionable sentence about sequencing approach.",
  "lifestyle_note": "One Ayurvedic lifestyle sentence relevant to this condition."
}

Selection rules:
- priority_pose_ids: 6-10 poses most beneficial for this condition
- priority_pranayama_ids: 2-4 pranayama techniques; prefer balancing/calming unless condition requires energy
- avoid_pranayama_ids: 0-3 pranayama techniques dangerous for this condition
- avoid_pose_ids: poses that are UNSAFE or contraindicated for this condition (be thorough — this is a
  safety gate). E.g. avoid deep backbends/inversions for uncontrolled hypertension, retina/glaucoma,
  or cervical instability; avoid deep forward folds/twists for acute disc herniation; avoid strong
  abdominal compression for pregnancy or abdominal surgery. Return [] only if genuinely none apply.
- For serious conditions (cardiac, neurological): avoid breath_retention, bellows_breath, skull_shining
- For inflammatory/autoimmune: prefer restorative, seated, prone categories
- Always include at least 2 restorative poses unless condition clearly benefits from dynamic movement"""


async def _generate_single_protocol(
    condition: str,
    available_pose_ids: list[str],
    available_pranayama_ids: list[str],
) -> dict | None:
    condition_key = condition.lower().replace(" ", "_")
    if condition_key in _CACHE:
        return _CACHE[condition_key]

    pose_list = ", ".join(available_pose_ids[:60])
    prana_list = ", ".join(available_pranayama_ids)

    user_prompt = (
        f"Generate a therapeutic yoga protocol for this medical condition: {condition}\n\n"
        f"Available pose IDs (choose 6-10): {pose_list}\n"
        f"Available pranayama IDs (choose 2-4): {prana_list}\n\n"
        "Select only IDs from the lists above. Prioritise safety and therapeutic benefit."
    )

    try:
        response = await llm_client.generate(
            prompt=user_prompt,
            system_prompt=_SYSTEM_PROMPT,
            json_mode=True,
        )
        protocol = json.loads(response)

        # Validate response has the required structure
        if "error" in protocol or "condition" not in protocol:
            logger.warning(f"Dynamic protocol for '{condition}' had invalid structure")
            return None

        # Ensure IDs are actually available (guard against hallucinated IDs)
        valid_pose_ids = set(available_pose_ids)
        valid_prana_ids = set(available_pranayama_ids)
        protocol["priority_pose_ids"] = [
            pid for pid in protocol.get("priority_pose_ids", []) if pid in valid_pose_ids
        ]
        protocol["priority_pranayama_ids"] = [
            pid for pid in protocol.get("priority_pranayama_ids", []) if pid in valid_prana_ids
        ]
        protocol["avoid_pranayama_ids"] = [
            pid for pid in protocol.get("avoid_pranayama_ids", []) if pid in valid_prana_ids
        ]
        # Pose-level contraindications for this (rare) condition — validated to real
        # pose IDs so the LLM can't invent one. A pose can't be both prioritised and
        # avoided; the avoid list wins (safety).
        _avoid_poses = {pid for pid in protocol.get("avoid_pose_ids", []) if pid in valid_pose_ids}
        protocol["avoid_pose_ids"] = sorted(_avoid_poses)
        protocol["priority_pose_ids"] = [
            pid for pid in protocol["priority_pose_ids"] if pid not in _avoid_poses
        ]

        # Mark as dynamically generated
        protocol["_dynamic"] = True
        _CACHE[condition_key] = protocol
        logger.info(f"Generated dynamic yoga protocol for '{condition}' ({len(protocol['priority_pose_ids'])} poses)")
        return protocol

    except Exception as e:
        logger.warning(f"Dynamic protocol generation failed for '{condition}': {e}")
        return None


async def generate_dynamic_protocols(
    unknown_conditions: list[str],
    available_pose_ids: list[str],
    available_pranayama_ids: list[str],
) -> dict[str, dict]:
    """
    Generate LLM-based protocols for conditions not in the static protocol database.
    Returns a dict keyed by condition name (lowercase) suitable for merging into _PROTOCOL_MAP.
    """
    result: dict[str, dict] = {}
    for condition in unknown_conditions:
        protocol = await _generate_single_protocol(condition, available_pose_ids, available_pranayama_ids)
        if protocol:
            key = condition.lower().replace(" ", "_")
            result[key] = protocol
            # Also index by exact condition string (lowercase) for matching
            result[condition.lower()] = protocol
    return result
