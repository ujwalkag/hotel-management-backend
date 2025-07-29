from django.conf import settings
from twilio.rest import Client

def notify_customer_via_sms(to_number, message):
    """
    Tries WhatsApp first, falls back to SMS if WhatsApp fails.
    """
    client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    whatsapp_from = getattr(settings, "TWILIO_WHATSAPP_FROM", None)
    sms_from = getattr(settings, "TWILIO_SMS_FROM", None)
    wa_sent = False
    wa_sid = None

    # Try WhatsApp first
    if whatsapp_from:
        wa_to = f"whatsapp:+91{to_number}" if not to_number.startswith("whatsapp:") else to_number
        try:
            wa_msg = client.messages.create(
                body=message,
                from_=whatsapp_from,
                to=wa_to
            )
            wa_sid = wa_msg.sid
            wa_sent = wa_sid is not None
        except Exception as e:
            print(f"Twilio WhatsApp error: {e}")

    # Fallback to SMS if WhatsApp failed
    sms_sid = None
    if not wa_sent and sms_from:
        sms_to = f"+91{to_number}" if not to_number.startswith("+") else to_number
        try:
            sms_msg = client.messages.create(
                body=message,
                from_=sms_from,
                to=sms_to
            )
            sms_sid = sms_msg.sid
        except Exception as e:
            print(f"Twilio SMS error: {e}")

    return wa_sid if wa_sent else sms_sid
