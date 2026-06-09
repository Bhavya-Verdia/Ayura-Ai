"""
Plan comparison helpers for adapted plan versions.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any


PLAN_SECTIONS = [
    "gym_plan",
    "yoga_plan",
    "diet_plan",
    "panchakarma_plan",
    "home_remedies",
    "seasonal_guidance",
    "daily_tip",
    "safety_checks",
]


def _stable_hash(value: Any) -> str:
    encoded = json.dumps(value, sort_keys=True, default=str, ensure_ascii=True)
    return hashlib.sha256(encoded.encode("utf-8")).hexdigest()


def _count_items(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, dict):
        return sum(_count_items(nested) for nested in value.values()) or len(value)
    if isinstance(value, list):
        return sum(_count_items(item) for item in value) or len(value)
    return 1


def build_plan_diff(previous_plan: dict | None, current_plan: dict) -> dict:
    """Return section-level change metadata between two plan payloads."""
    if not previous_plan:
        return {
            "changed_sections": [],
            "summary": "Initial plan version.",
            "sections": {},
        }

    sections = {}
    changed_sections = []
    for section in PLAN_SECTIONS:
        before = previous_plan.get(section)
        after = current_plan.get(section)
        changed = _stable_hash(before) != _stable_hash(after)
        if changed:
            changed_sections.append(section)
        sections[section] = {
            "changed": changed,
            "before_items": _count_items(before),
            "after_items": _count_items(after),
        }

    readable = ", ".join(section.replace("_", " ") for section in changed_sections)
    summary = f"Updated {readable}." if changed_sections else "No section-level changes detected."
    return {
        "changed_sections": changed_sections,
        "summary": summary,
        "sections": sections,
    }
