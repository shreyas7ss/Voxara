import asyncio
import json

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


def _sync_send_listing_template(to_number: str, content_variables: dict):
    return _get_client().messages.create(
        content_sid=settings.TWILIO_LISTING_TEMPLATE_SID,
        content_variables=json.dumps(content_variables),
        from_=settings.WHATSAPP_FROM_NUMBER,
        to=to_number,
    )


async def send_listing_template_message(to_number: str, listing: dict, caller_name: str = None) -> dict:
    image_urls = listing.get("image_urls") or []
    content_variables = {
        "1": image_urls[0] if image_urls else "",
        "2": caller_name or "there",
        "3": listing.get("property_type") or "a property",
        "4": listing.get("location") or "",
        "5": listing.get("price_text") or "",
        "6": listing.get("bedrooms") or "",
        "7": listing.get("listing_summary") or "",
    }
    loop = asyncio.get_event_loop()
    try:
        message = await loop.run_in_executor(None, _sync_send_listing_template, to_number, content_variables)
        logger.info(f"Listing WhatsApp sent to {to_number}: SID {message.sid}")
        return {"success": True, "message_sid": str(message.sid)}
    except Exception as e:
        logger.error(f"Listing WhatsApp send to {to_number} failed: {e}")
        return {"success": False, "error": str(e)}
