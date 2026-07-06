import asyncio

from twilio.rest import Client

from app.config import settings
from app.utils.logger import logger

_client = None


def _get_client() -> Client:
    global _client
    if _client is None:
        _client = Client(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)
    return _client


def _sync_send_message(to_number: str, body: str):
    return _get_client().messages.create(
        from_=settings.WHATSAPP_FROM_NUMBER,
        to=to_number,
        body=body,
    )


async def send_summary_to_agent(summary_text: str, to_number: str = None) -> dict:
    to_number = to_number or settings.AGENT_WHATSAPP_NUMBER
    loop = asyncio.get_event_loop()
    try:
        message = await loop.run_in_executor(None, _sync_send_message, to_number, summary_text)
        logger.info(f"WhatsApp summary sent to {to_number}: SID {message.sid}")
        return {"success": True, "message_sid": str(message.sid)}
    except Exception as e:
        logger.error(f"WhatsApp send to {to_number} failed: {e}")
        return {"success": False, "error": str(e)}
