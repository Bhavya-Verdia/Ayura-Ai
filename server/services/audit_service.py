"""
Ayura AI - Audit Log Service
Append-only event log for health data changes (GDPR/HIPAA audit trail).
"""

from datetime import datetime, timezone
from motor.motor_asyncio import AsyncIOMotorDatabase
import logging

logger = logging.getLogger("ayura.audit")


async def log_health_event(
    db: AsyncIOMotorDatabase,
    user_id: str,
    event_type: str,
    details: dict,
    source: str = "api",
) -> None:
    """
    Append a health-related event to the immutable audit log.

    event_type examples:
        symptom_added, symptom_removed,
        medication_added, medication_removed,
        medical_history_updated,
        dosha_quiz_completed,
        plan_generated, plan_adapted, plan_rated,
        weight_logged, checkin_submitted,
        account_deleted, data_exported

    Args:
        db:         MongoDB database handle.
        user_id:    The authenticated user performing the action.
        event_type: Machine-readable event label.
        details:    Arbitrary extra context (old/new values, plan_id, etc.).
        source:     Origin of the event ("api", "chat", "worker", etc.).
    """
    try:
        await db.audit_log.insert_one({
            "user_id": user_id,
            "event_type": event_type,
            "details": details,
            "source": source,
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as exc:
        # Never crash a request because of audit logging
        logger.error("Audit log write failed: %s | event=%s user=%s", exc, event_type, user_id)


async def log_plan_generated(
    db: AsyncIOMotorDatabase,
    user_id: str,
    plan_id: str,
    plan_type: str,
    model_used: str | None,
    is_adaptation: bool = False,
) -> None:
    """Convenience wrapper for plan generation events."""
    await log_health_event(
        db, user_id,
        event_type="plan_adapted" if is_adaptation else "plan_generated",
        details={"plan_id": plan_id, "plan_type": plan_type, "model_used": model_used},
        source="api",
    )

    # Also surface to the user-facing health timeline feed. The frontend uses
    # `adaptation_triggered` for re-generated plans and `plan_generated` for new ones.
    try:
        await db.timeline.insert_one({
            "user_id": user_id,
            "event_type": "adaptation_triggered" if is_adaptation else "plan_generated",
            "details": {"plan_type": plan_type, "model_used": model_used},
            "source": "api",
            "timestamp": datetime.now(timezone.utc),
        })
    except Exception as exc:
        logger.error("Timeline write failed: %s | plan=%s user=%s", exc, plan_id, user_id)


async def log_symptom_change(
    db: AsyncIOMotorDatabase,
    user_id: str,
    action: str,  # "added" | "removed"
    symptoms: list[str],
    source: str = "api",
) -> None:
    """Convenience wrapper for symptom changes."""
    await log_health_event(
        db, user_id,
        event_type=f"symptom_{action}",
        details={"symptoms": symptoms},
        source=source,
    )


async def log_medication_change(
    db: AsyncIOMotorDatabase,
    user_id: str,
    action: str,  # "added" | "removed" | "updated"
    medications: list[str],
    source: str = "api",
) -> None:
    """Convenience wrapper for medication changes."""
    await log_health_event(
        db, user_id,
        event_type=f"medication_{action}",
        details={"medications": medications},
        source=source,
    )
