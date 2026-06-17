"""
Ayura AI - SMS Service
Handles sending OTPs for mobile login.
"""

import asyncio
from core.logger import logger
from config import settings


class SMSService:
    def __init__(self, use_mock: bool | None = None):
        if use_mock is None:
            use_mock = settings.SMS_OTP_MOCK and settings.APP_ENV != "production"
        self.use_mock = use_mock

    async def send_otp(self, phone_number: str, otp_code: str) -> bool:
        """Send an OTP code via SMS."""
        if self.use_mock:
            logger.info("=" * 40)
            logger.info(f"[SMS MOCK] OTP for {phone_number}: {otp_code}")
            logger.info("=" * 40)
            return True

        sid = getattr(settings, "TWILIO_ACCOUNT_SID", None)
        auth = getattr(settings, "TWILIO_AUTH_TOKEN", None)
        from_number = getattr(settings, "TWILIO_PHONE_NUMBER", None)

        if not sid or not auth or not from_number:
            logger.error(
                "Twilio credentials not configured. "
                "Set TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_PHONE_NUMBER."
            )
            return False

        try:
            from twilio.rest import Client

            def _send():
                client = Client(sid, auth)
                client.messages.create(
                    body=f"Your Ayura AI verification code is: {otp_code}. Valid for 5 minutes.",
                    from_=from_number,
                    to=phone_number,
                )

            await asyncio.to_thread(_send)
            logger.info(f"Twilio SMS sent to {phone_number}")
            return True
        except Exception as e:
            logger.error(f"Twilio SMS delivery failed: {e}")
            return False


sms_service = SMSService()


async def send_sms_otp(phone_number: str, otp_code: str) -> bool:
    return await sms_service.send_otp(phone_number, otp_code)
