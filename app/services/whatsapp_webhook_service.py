from uuid import uuid4

from app.config import settings
from app.services import groq_service, listing_service, storage_service
from app.utils.logger import logger


async def handle_inbound_whatsapp(form: dict) -> dict:
    if form.get("From") != settings.AGENT_WHATSAPP_NUMBER:
        logger.warning(f"Ignoring inbound WhatsApp from unrecognized sender: {form.get('From')}")
        return {"ignored": True}

    num_media = int(form.get("NumMedia", "0") or "0")
    if num_media == 0:
        return {"ignored": True, "reason": "no_media"}

    media_items = [
        (form[f"MediaUrl{i}"], form.get(f"MediaContentType{i}", "application/octet-stream"))
        for i in range(num_media)
        if f"MediaUrl{i}" in form
    ]

    uploaded_urls = []
    for media_url, content_type in media_items:
        content, _ = await storage_service.download_twilio_media(media_url)
        public_url = await storage_service.upload_image(content, content_type, f"listings/{uuid4().hex}.jpg")
        uploaded_urls.append(public_url)

    caption = form.get("Body", "") or ""
    extracted = await groq_service.extract_listing_data(caption)

    listing = await listing_service.create_listing(
        agent_number=form["From"],
        raw_caption=caption,
        extracted=extracted,
        image_urls=uploaded_urls,
        message_sid=form.get("MessageSid", ""),
    )

    return {"ingested": True, "listing_id": listing.id}
