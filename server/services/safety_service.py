"""
Medical safety helpers for red-flag symptoms.
"""

from __future__ import annotations


RED_FLAG_RULES = {
    "chest pain": "Chest pain can be urgent, especially with breathlessness, sweating, nausea, or pain spreading to the arm/jaw.",
    "severe breathlessness": "Severe trouble breathing needs urgent medical evaluation.",
    "shortness of breath": "Shortness of breath can be serious if sudden, severe, or associated with chest pain.",
    "fainting": "Fainting or loss of consciousness can indicate a serious medical issue.",
    "suicidal": "Thoughts of self-harm or suicide require immediate support from emergency services or a crisis line.",
    "self harm": "Thoughts of self-harm require immediate support from emergency services or a crisis line.",
    "stroke": "Stroke-like symptoms require emergency care immediately.",
    "face drooping": "Face drooping can be a stroke warning sign and needs emergency care.",
    "severe bleeding": "Severe or uncontrolled bleeding requires urgent medical care.",
    "pregnancy bleeding": "Bleeding during pregnancy should be assessed urgently by a clinician.",
    "worst headache": "The worst headache of your life can be a medical emergency.",
}

_TRIAGE_SYSTEM = "You are a medical safety classifier. Reply with ONLY valid JSON."

_TRIAGE_PROMPT = """Classify this health-related message for safety.

Message: "{message}"

Reply ONLY with this JSON:
{{"requires_emergency": true/false, "reason": "brief reason or null"}}

Classify as requires_emergency=true ONLY if the message describes:
- Suicidal ideation or self-harm
- Symptoms of heart attack, stroke, or severe allergic reaction
- Intent to stop critical medications (insulin, blood thinners, seizure meds)
- Unconsciousness or inability to breathe
- Severe trauma or poisoning"""


async def _llm_triage(message: str) -> bool:
    """Returns True if LLM considers this message a medical emergency. Fails open on error."""
    try:
        import json
        from ai.llm_client import llm_client
        resp = await llm_client.generate(
            prompt=_TRIAGE_PROMPT.format(message=message[:500]),
            system_prompt=_TRIAGE_SYSTEM,
            temperature=0.0,
            max_tokens=100,
            json_mode=True,
        )
        data = json.loads(resp)
        return bool(data.get("requires_emergency"))
    except Exception:
        return False


async def detect_red_flags(text: str, symptoms: list[str] | None = None) -> dict:
    """
    Detect medical emergency signals in user input.

    Two-stage: keyword matching (fast) then LLM classification for borderline cases.
    Fails open — LLM errors do not block the user.
    """
    haystack = " ".join([text or "", " ".join(symptoms or [])]).lower()
    matches = [
        {"trigger": trigger, "reason": reason}
        for trigger, reason in RED_FLAG_RULES.items()
        if trigger in haystack
    ]

    if matches:
        return {
            "has_red_flags": True,
            "matches": matches,
            "message": (
                "Your message includes possible urgent warning signs. Ayura AI cannot assess emergencies. "
                "Please contact local emergency services or a qualified clinician immediately."
            ),
        }

    # LLM secondary triage for borderline cases not caught by keywords
    llm_flagged = await _llm_triage(text or "")
    if llm_flagged:
        return {
            "has_red_flags": True,
            "matches": [{"trigger": "llm_triage", "reason": "LLM safety classifier flagged this as a potential emergency."}],
            "message": (
                "Your message includes possible urgent warning signs. Ayura AI cannot assess emergencies. "
                "Please contact local emergency services or a qualified clinician immediately."
            ),
        }

    return {"has_red_flags": False, "matches": [], "message": None}
