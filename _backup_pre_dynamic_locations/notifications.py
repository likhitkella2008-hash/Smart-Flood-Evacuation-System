"""
Smart Flood Evacuation & Rescue System - Notification Service
=============================================================

Handles real SMS dispatch via Twilio REST API (when configured via
environment variables) and manages synchronized in-app notifications.

Features:
- Configurable SMS backend via environment variables.
- Clean terminal/logger fallback when real SMS credentials are absent.
- Graceful error handling (provider timeouts, invalid numbers).
- Privacy protection: phone numbers masked in logs, tokens never logged.
- Accurate delivery status reporting (no false success claims).
"""

import os
import logging
from datetime import datetime
from typing import Dict, Any, Optional
import requests

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("SmartFloodNotifications")


def mask_phone(phone: str) -> str:
    """Masks all but the last 4 digits of a phone number for privacy."""
    clean = "".join(ch for ch in str(phone) if ch.isalnum() or ch == "+")
    if len(clean) <= 4:
        return "****"
    return "*" * (len(clean) - 4) + clean[-4:]


class NotificationService:
    def __init__(self):
        self.provider = os.environ.get("SMS_PROVIDER", "console").strip().lower()
        self.twilio_sid = os.environ.get("TWILIO_ACCOUNT_SID", "").strip()
        self.twilio_token = os.environ.get("TWILIO_AUTH_TOKEN", "").strip()
        self.twilio_from = os.environ.get("TWILIO_PHONE_NUMBER", "").strip()

    def is_real_sms_configured(self) -> bool:
        """Returns True if Twilio credentials are fully supplied."""
        return bool(self.twilio_sid and self.twilio_token and self.twilio_from)

    def send_sms(self, phone: str, message: str) -> Dict[str, Any]:
        """
        Dispatches SMS via Twilio if configured, or logs to console.
        Returns a dict indicating actual delivery state.
        """
        if not phone or not message:
            return {"success": False, "provider": "none", "error": "Missing phone or message text"}

        # Format Indian numbers if 10 digits
        clean_phone = phone.strip()
        if len(clean_phone) == 10 and clean_phone.isdigit():
            clean_phone = "+91" + clean_phone

        # 1. Attempt Twilio REST API if configured
        if self.is_real_sms_configured():
            try:
                url = f"https://api.twilio.com/2010-04-01/Accounts/{self.twilio_sid}/Messages.json"
                resp = requests.post(
                    url,
                    data={
                        "To": clean_phone,
                        "From": self.twilio_from,
                        "Body": message
                    },
                    auth=(self.twilio_sid, self.twilio_token),
                    timeout=8.0
                )
                if resp.status_code in [200, 201]:
                    logger.info("Real SMS sent successfully to %s via Twilio", mask_phone(clean_phone))
                    return {
                        "success": True,
                        "provider": "twilio",
                        "sid": resp.json().get("sid"),
                        "message": "SMS dispatched via Twilio gateway"
                    }
                else:
                    err_msg = resp.json().get("message", f"Twilio HTTP {resp.status_code}")
                    logger.warning("Twilio SMS failed for %s: %s", mask_phone(clean_phone), err_msg)
                    return {
                        "success": False,
                        "provider": "twilio",
                        "error": f"Twilio error: {err_msg}"
                    }
            except Exception as ex:
                logger.error("Exception during Twilio dispatch to %s: %s", mask_phone(clean_phone), str(ex))
                return {
                    "success": False,
                    "provider": "twilio",
                    "error": f"Twilio connection failure: {str(ex)}"
                }

        # 2. Development / Fallback Console Provider
        masked = mask_phone(clean_phone)
        logger.info("[SMS NOTIFICATION SIMULATOR] To: %s | Text: %s", masked, message)
        print()
        print("=" * 60)
        print("SMS NOTIFICATION (Simulator / In-App Mode)")
        print("=" * 60)
        print("RECIPIENT :", masked)
        print("MESSAGE   :", message)
        print("CONFIG    : Real SMS provider not configured (set TWILIO_* vars)")
        print("=" * 60)
        print()

        return {
            "success": True,
            "provider": "console",
            "message": "Recorded to console; real SMS provider not configured"
        }

    def notify(
        self,
        conn,
        citizen_id: int,
        phone: str,
        message: str,
        event_type: str = "general"
    ) -> Dict[str, Any]:
        """
        Creates an in-app notification in the database and attempts SMS dispatch.
        """
        # In-app notification record
        try:
            conn.execute("""
                INSERT INTO notifications (citizen_id, message, is_read, created_at)
                VALUES (?, ?, 0, ?)
            """, (
                citizen_id,
                message,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            ))
            in_app_ok = True
        except Exception as ex:
            logger.error("Failed to record in-app notification: %s", str(ex))
            in_app_ok = False

        # SMS dispatch
        sms_result = self.send_sms(phone, message)

        return {
            "in_app_saved": in_app_ok,
            "sms_result": sms_result,
            "event_type": event_type
        }


# Singleton service instance
notification_service = NotificationService()
