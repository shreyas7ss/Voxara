from unittest.mock import patch, AsyncMock, MagicMock

import pytest

from app.services import whatsapp_webhook_service
from app.utils.validators import validate_twilio_signature

EXTRACTED_LISTING = {
    "property_type": "2BHK",
    "location": "Velachery",
    "price_text": "80 lakhs",
    "bedrooms": "2",
    "furnishing": "semi-furnished",
    "amenities": ["metro nearby"],
    "listing_summary": "Spacious 2BHK near metro",
    "availability_status": "available",
}


async def test_rejects_non_agent_sender():
    form = {"From": "whatsapp:+911111111111", "Body": "hi", "NumMedia": "1", "MediaUrl0": "https://x/y.jpg"}
    with patch("app.services.whatsapp_webhook_service.listing_service.create_listing", new=AsyncMock()) as mock_create:
        result = await whatsapp_webhook_service.handle_inbound_whatsapp(form)

    assert result == {"ignored": True}
    mock_create.assert_not_called()


async def test_no_media_is_ignored():
    from app.config import settings
    form = {"From": settings.AGENT_WHATSAPP_NUMBER, "Body": "just text, no photos", "NumMedia": "0"}
    result = await whatsapp_webhook_service.handle_inbound_whatsapp(form)
    assert result == {"ignored": True, "reason": "no_media"}


async def test_downloads_media_uploads_to_s3_and_creates_listing():
    from app.config import settings
    form = {
        "From": settings.AGENT_WHATSAPP_NUMBER,
        "Body": "Spacious 2BHK in Velachery, 80 lakhs",
        "NumMedia": "2",
        "MediaUrl0": "https://api.twilio.com/media/ME0",
        "MediaContentType0": "image/jpeg",
        "MediaUrl1": "https://api.twilio.com/media/ME1",
        "MediaContentType1": "image/png",
        "MessageSid": "SM_test",
    }

    fake_listing = MagicMock(id=42)

    with patch("app.services.whatsapp_webhook_service.storage_service.download_twilio_media",
               new=AsyncMock(return_value=(b"bytes", "image/jpeg"))) as mock_download, \
         patch("app.services.whatsapp_webhook_service.storage_service.upload_image",
               new=AsyncMock(side_effect=["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"])) as mock_upload, \
         patch("app.services.whatsapp_webhook_service.groq_service.extract_listing_data",
               new=AsyncMock(return_value=EXTRACTED_LISTING)), \
         patch("app.services.whatsapp_webhook_service.listing_service.create_listing",
               new=AsyncMock(return_value=fake_listing)) as mock_create:
        result = await whatsapp_webhook_service.handle_inbound_whatsapp(form)

    assert result == {"ingested": True, "listing_id": 42}
    assert mock_download.call_count == 2
    assert mock_upload.call_count == 2
    create_kwargs = mock_create.call_args.kwargs
    assert create_kwargs["image_urls"] == ["https://cdn.example.com/a.jpg", "https://cdn.example.com/b.jpg"]
    assert create_kwargs["extracted"] == EXTRACTED_LISTING


async def test_extract_listing_data_retries_once_then_raises_on_bad_json():
    from app.services import groq_service

    bad_response = MagicMock(choices=[MagicMock(message=MagicMock(content="not json"))])
    with patch.object(groq_service.client.chat.completions, "create", return_value=bad_response):
        with pytest.raises(RuntimeError, match="LISTING_EXTRACTION_FAILED"):
            await groq_service.extract_listing_data("some caption")


def test_validate_twilio_signature_uses_request_validator():
    with patch("app.utils.validators.RequestValidator") as MockValidator:
        MockValidator.return_value.validate.return_value = True
        result = validate_twilio_signature("https://example.com/webhook", {"From": "x"}, "sig123")

    assert result is True
    MockValidator.return_value.validate.assert_called_once_with(
        "https://example.com/webhook", {"From": "x"}, "sig123"
    )
