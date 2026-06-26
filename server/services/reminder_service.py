"""
Ayura AI - Reminder scheduling helpers.

Reminders are scheduled in the user's own timezone (stored per reminder). The ARQ
cron runs every minute in UTC; these helpers convert "now" into each reminder's
local time so an "08:00" reminder fires at the user's 08:00 — not 08:00 UTC.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

DEFAULT_TZ = "UTC"


def _local_now(now_utc: datetime, tz_name: str | None) -> datetime:
    try:
        return now_utc.astimezone(ZoneInfo(tz_name or DEFAULT_TZ))
    except Exception:
        return now_utc.astimezone(ZoneInfo(DEFAULT_TZ))


def reminder_due(reminder: dict, now_utc: datetime) -> bool:
    """True if an active reminder's local time + day matches `now_utc` to the minute."""
    if not reminder.get("is_active", True):
        return False
    local = _local_now(now_utc, reminder.get("timezone"))
    if local.strftime("%H:%M") != reminder.get("time"):
        return False
    days = reminder.get("days") or []
    if days and local.strftime("%A").lower() not in [d.lower() for d in days]:
        return False
    return True


def fired_token(reminder: dict, now_utc: datetime) -> str:
    """A per-minute idempotency token (local date + time) so a reminder is delivered
    at most once for a given scheduled minute, even if the cron double-fires."""
    return _local_now(now_utc, reminder.get("timezone")).strftime("%Y-%m-%d %H:%M")
