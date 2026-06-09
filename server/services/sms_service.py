"""
Ayura AI - SMS Service
Handles sending OTPs for mobile login. Currently set to Development Mode.
"""

from core.logger import logger
from config import settings

class SMSService:
    def __init__(self, use_mock: bool | None = None):
        if use_mock is None:
            use_mock = settings.SMS_OTP_MOCK and settings.APP_ENV != "production"
        self.use_mock = use_mock
        # TODO: Add Twilio initialization here when switching to production
        # e.g., self.client = Client(settings.TWILIO_SID, settings.TWILIO_AUTH_TOKEN)

    async def send_otp(self, phone_number: str, otp_code: str) -> bool:
        """Send an OTP code via SMS."""
        if self.use_mock:
            # Development mode: Just log the OTP
            logger.info("=" * 40)
            logger.info(f"📱 MOCK SMS TO: {phone_number}")
            logger.info(f"🔑 OTP CODE:    {otp_code}")
            logger.info("=" * 40)
            return True

        logger.error("SMS OTP requested but no production SMS provider is configured.")
        return False

sms_service = SMSService()

async def send_sms_otp(phone_number: str, otp_code: str) -> bool:
    return await sms_service.send_otp(phone_number, otp_code)
