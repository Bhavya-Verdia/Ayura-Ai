from core.logger import logger
"""
Ayura AI - Email Service
Handles sending verification and password reset emails via SMTP.
"""

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import asyncio
from config import settings

def _send_email_sync(to_email: str, subject: str, html_body: str):
    """Synchronous function to send email via SMTP."""
    if not settings.SMTP_USER or not settings.SMTP_PASSWORD:
        logger.warning(f" Email not sent because SMTP credentials are not configured.")
        logger.info(f"       To: {to_email} | Subject: {subject}")
        logger.info(f"       Body: {html_body}")
        return

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = settings.FROM_EMAIL
    msg["To"] = to_email

    part = MIMEText(html_body, "html")
    msg.attach(part)

    try:
        with smtplib.SMTP(settings.SMTP_SERVER, settings.SMTP_PORT) as server:
            server.starttls()
            server.login(settings.SMTP_USER, settings.SMTP_PASSWORD)
            server.sendmail(settings.FROM_EMAIL, to_email, msg.as_string())
            logger.info(f"[OK] Email sent to {to_email}")
    except Exception as e:
        logger.error(f" Failed to send email to {to_email}: {e}")

async def send_email(to_email: str, subject: str, html_body: str):
    """Asynchronous wrapper for sending email."""
    await asyncio.to_thread(_send_email_sync, to_email, subject, html_body)

async def send_verification_email(to_email: str, token: str):
    """Send an email verification link."""
    verify_url = f"{settings.FRONTEND_URL}/verify-email?token={token}"
    subject = "Verify your Ayura AI Account"
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0b1426; color: #e2e8f0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f1c32; padding: 30px; border-radius: 12px; border: 1px solid #1e293b;">
          <h2 style="color: #6ee7b7; text-align: center;">Welcome to Ayura AI!</h2>
          <p>Please click the button below to verify your email address and activate your account.</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{verify_url}" style="background-color: #10b981; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Verify Email</a>
          </div>
          <p style="font-size: 12px; color: #94a3b8; text-align: center;">If you didn't create an account, you can safely ignore this email.</p>
        </div>
      </body>
    </html>
    """
    await send_email(to_email, subject, html)

async def send_password_reset_email(to_email: str, token: str):
    """Send a password reset link."""
    reset_url = f"{settings.FRONTEND_URL}/reset-password?token={token}"
    subject = "Reset Your Ayura AI Password"
    
    html = f"""
    <html>
      <body style="font-family: Arial, sans-serif; background-color: #0b1426; color: #e2e8f0; padding: 20px;">
        <div style="max-width: 600px; margin: 0 auto; background-color: #0f1c32; padding: 30px; border-radius: 12px; border: 1px solid #1e293b;">
          <h2 style="color: #f43f5e; text-align: center;">Password Reset Request</h2>
          <p>We received a request to reset your password. Click the button below to set a new one. This link will expire in 1 hour.</p>
          <div style="text-align: center; margin: 30px 0;">
            <a href="{reset_url}" style="background-color: #f43f5e; color: #ffffff; padding: 12px 24px; text-decoration: none; border-radius: 6px; font-weight: bold; display: inline-block;">Reset Password</a>
          </div>
          <p style="font-size: 12px; color: #94a3b8; text-align: center;">If you didn't request a password reset, you can safely ignore this email.</p>
        </div>
      </body>
    </html>
    """
    await send_email(to_email, subject, html)
