"""
Ayura AI — WhatsApp delivery (Meta WhatsApp Cloud API).

Three uses, each an approved **template** (a business may not message first with free
text; templates are what Meta allows outside a 24-hour customer window). Their exact
text is in `docs/whatsapp_templates.md`:

  * the verification code that proves the number is the user's (authentication);
  * reminders — the same ones web push and email already carry (utility);
  * the morning message: today's meals and the streak (utility).

Who gets a message: only a user who typed their number, ticked consent, and entered
the code sent to it (`routes/whatsapp.py`). Without the code step anyone could point
the app's reminders at someone else's phone. Each kind can be turned off separately,
and removing the number stops everything.

Meta charges per message, so WhatsApp is **opt-in per caller**: a notification goes to
WhatsApp only when its sender passes `whatsapp=True` (reminders, the morning message),
never by default — a badge or a community reply is not worth a paid message.

Outside production with no access token, messages are logged rather than sent, as the
SMS OTP service does, so the flow can be built and tested without a Meta account.
"""
from __future__ import annotations

import re
from datetime import date, datetime, timezone
from typing import Optional

import httpx

from config import settings
from core.logger import logger

_E164 = re.compile(r"^\+[1-9]\d{7,14}$")


def mock_mode() -> bool:
    return not settings.WHATSAPP_ACCESS_TOKEN and settings.APP_ENV != "production"


def available() -> bool:
    """Whether the opt-in should be offered at all."""
    if not settings.WHATSAPP_ENABLED:
        return False
    return mock_mode() or bool(settings.WHATSAPP_ACCESS_TOKEN and settings.WHATSAPP_PHONE_NUMBER_ID)


def normalise_phone(raw: str, default_country: str = "91") -> Optional[str]:
    """E.164, or None. A bare 10-digit number is read as Indian, which is who the app
    is for; anything else must carry its country code."""
    digits = re.sub(r"[^\d+]", "", raw or "")
    if digits.startswith("00"):
        digits = "+" + digits[2:]
    if not digits.startswith("+"):
        digits = digits.lstrip("0")
        if len(digits) == 10:
            digits = f"+{default_country}{digits}"
        else:
            digits = "+" + digits
    return digits if _E164.match(digits) else None


def mask(phone: Optional[str]) -> Optional[str]:
    if not phone:
        return None
    return phone[:3] + " " + "•" * max(0, len(phone) - 7) + phone[-4:]


def clean_param(text: str, limit: int = 900) -> str:
    """Template parameters may not contain newlines, tabs or more than four spaces in
    a row (Meta rejects the whole message), and are capped in length."""
    text = re.sub(r"[\r\n\t]+", " · ", str(text or ""))
    text = re.sub(r" {2,}", " ", text).strip(" ·")
    return text if len(text) <= limit else text[: limit - 1].rstrip() + "…"


async def send_template(to: str, template: str, params: list[str],
                        code_button: Optional[str] = None) -> bool:
    """Send one template message. Returns False on any failure; never raises."""
    params = [clean_param(p) for p in params]
    if mock_mode():
        logger.info("[WHATSAPP MOCK] to=%s template=%s params=%s", mask(to), template, params)
        return True
    if not available():
        return False
    components: list[dict] = [{"type": "body", "parameters": [{"type": "text", "text": p} for p in params]}]
    if code_button is not None:
        # Authentication templates carry the code again in their copy-code button.
        components.append({"type": "button", "sub_type": "url", "index": "0",
                           "parameters": [{"type": "text", "text": code_button}]})
    payload = {
        "messaging_product": "whatsapp", "to": to.lstrip("+"), "type": "template",
        "template": {"name": template, "language": {"code": settings.WHATSAPP_TEMPLATE_LANG},
                     "components": components},
    }
    url = (f"https://graph.facebook.com/{settings.WHATSAPP_API_VERSION}/"
           f"{settings.WHATSAPP_PHONE_NUMBER_ID}/messages")
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.post(url, json=payload,
                                  headers={"Authorization": f"Bearer {settings.WHATSAPP_ACCESS_TOKEN}"})
        if r.status_code >= 400:
            logger.warning("WhatsApp send failed (%s) for %s: %s", r.status_code, mask(to), r.text[:300])
            return False
        return True
    except Exception as exc:
        logger.warning("WhatsApp send error for %s: %s", mask(to), exc)
        return False


def opted_in(user: dict, kind: str) -> Optional[str]:
    """The verified number if this user takes `kind` ("reminders" | "daily"), else None."""
    wa = (user or {}).get("whatsapp") or {}
    if not wa.get("verified_at") or not wa.get("phone"):
        return None
    return wa["phone"] if wa.get(kind) else None


async def send_reminder(db, user_id: str, title: str, body: str) -> bool:
    if not available():
        return False
    user = await db.users.find_one({"_id": user_id}, {"whatsapp": 1, "name": 1})
    phone = opted_in(user, "reminders")
    if not phone:
        return False
    return await send_template(phone, settings.WHATSAPP_TEMPLATE_REMINDER, [title, body])


# ── The morning message ─────────────────────────────────────────────────────

_DAY_FULL = ("Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday")
_SLOTS = (("breakfast", "Breakfast"), ("lunch", "Lunch"), ("dinner", "Dinner"))


def todays_meals(diet_doc: Optional[dict], today: date) -> Optional[str]:
    """Today's meals from the latest diet plan, counted the way DietView counts them:
    week from the days since the plan was made, day by the real weekday. None when
    there is no plan, it has not started, or its four weeks are over."""
    if not diet_doc:
        return None
    plan = ((diet_doc.get("plan_data") or {}).get("diet_plan")) or {}
    weeks = plan.get("diet_weeks") or []
    started = diet_doc.get("generated_at") or plan.get("generated_at")
    if isinstance(started, str):
        try:
            started = datetime.fromisoformat(started.replace("Z", "+00:00"))
        except ValueError:
            return None
    if not isinstance(started, datetime) or not weeks:
        return None
    days = (today - started.date()).days
    if days < 0 or days >= 28:
        return None
    week_no = min(4, days // 7 + 1)
    week = next((w for w in weeks if w.get("week_number") == week_no), None)
    day = ((week or {}).get("daily_plan") or {}).get(_DAY_FULL[today.weekday()]) or {}
    parts = []
    for slot, label in _SLOTS:
        meal = day.get(slot)
        name = (meal.get("meal_name") or meal.get("name")) if isinstance(meal, dict) else None
        if name:
            parts.append(f"{label}: {name}")
    return "; ".join(parts) or None


def daily_text(name: str, meals: Optional[str], streak: int) -> list[str]:
    first = (name or "").split(" ")[0] or "there"
    meals_line = meals or "your plan is in the app"
    if streak >= 2:
        streak_line = f"You are on a {streak}-day streak."
    elif streak == 1:
        streak_line = "You logged yesterday — keep it going."
    else:
        streak_line = "Log one thing today to start a streak."
    return [first, meals_line, streak_line]


async def send_daily_messages(db, now: Optional[datetime] = None) -> int:
    """Called every minute. Sends the morning message to each opted-in user whose local
    time is their chosen time, at most once per local day."""
    from services.rewards import activity, streaks
    from services.reminder_service import _local_now

    if not available():
        return 0
    now = now or datetime.now(timezone.utc)
    sent = 0
    async for user in db.users.find({"whatsapp.daily": True, "whatsapp.verified_at": {"$ne": None}},
                                    {"whatsapp": 1, "name": 1, "timezone": 1}):
        wa = user.get("whatsapp") or {}
        local = _local_now(now, user.get("timezone"))
        if local.strftime("%H:%M") != (wa.get("daily_time") or "07:00"):
            continue
        today = local.date()
        if wa.get("daily_sent_on") == today.isoformat():
            continue
        diet = await db.plan_history.find_one({"user_id": user["_id"], "plan_type": "diet"},
                                              sort=[("generated_at", -1)])
        act = await activity(db, user["_id"], user.get("timezone"), today)
        streak = streaks(act["dates"], today)["current"]
        meals = todays_meals(diet, today)
        if not meals and not diet:
            continue  # nothing to tell someone with no plan yet
        # Mark first: a cron double-fire must not send twice, and a failed send is
        # not retried every minute for the rest of the hour.
        await db.users.update_one({"_id": user["_id"]},
                                  {"$set": {"whatsapp.daily_sent_on": today.isoformat()}})
        if await send_template(opted_in(user, "daily"), settings.WHATSAPP_TEMPLATE_DAILY,
                               daily_text(user.get("name"), meals, streak)):
            sent += 1
    return sent

