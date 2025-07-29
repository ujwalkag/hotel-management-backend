# apps/bills/notifications.py

import os
import logging
from twilio.rest import Client

logger = logging.getLogger(__name__)

TWILIO_ACCOUNT_SID = os.getenv("TWILIO_ACCOUNT_SID")
TWILIO_AUTH_TOKEN = os.getenv("TWILIO_AUTH_TOKEN")
TWILIO_WHATSAPP_FROM = os.getenv("TWILIO_WHATSAPP_FROM")  # e.g. whatsapp:+14155238886
DEFAULT_ADMIN_WHATSAPP = os.getenv("ADMIN_WHATSAPP_TO")   # e.g. whatsapp:+91XXXXXXXXXX

client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)


def notify_admin_via_whatsapp(message, to=None, media_url=None):
    """
    Send a WhatsApp message via Twilio.
    If `to` is None, message is sent to ADMIN_WHATSAPP_TO (single or comma-separated).
    `media_url` should be a public URL to the PDF.
    """
    if not all([TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN, TWILIO_WHATSAPP_FROM]):
        logger.warning("Twilio config missing. Skipping WhatsApp notification.")
        return

    recipients = [to] if to else DEFAULT_ADMIN_WHATSAPP.split(",")

    for number in recipients:
        number = number.strip()
        if not number.startswith("whatsapp:"):
            number = f"whatsapp:{number}"
        try:
            message_data = {
                "from_": TWILIO_WHATSAPP_FROM,
                "to": number,
                "body": message,
            }
            if media_url:
                message_data["media_url"] = [media_url]
            client.messages.create(**message_data)
            logger.info(f"WhatsApp sent to {number}")
        except Exception as e:
            logger.error(f"Failed WhatsApp to {number}: {e}")


def send_sms_text(message, to):
    """Future-ready: Twilio SMS API placeholder"""
    logger.info(f"[SMS Placeholder] Would send to {to}: {message}")

