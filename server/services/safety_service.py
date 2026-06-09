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


def detect_red_flags(text: str, symptoms: list[str] | None = None) -> dict:
    haystack = " ".join([text or "", " ".join(symptoms or [])]).lower()
    matches = [
        {"trigger": trigger, "reason": reason}
        for trigger, reason in RED_FLAG_RULES.items()
        if trigger in haystack
    ]
    return {
        "has_red_flags": bool(matches),
        "matches": matches,
        "message": (
            "Your message includes possible urgent warning signs. Ayura AI cannot assess emergencies. "
            "Please contact local emergency services or a qualified clinician immediately."
            if matches
            else None
        ),
    }
