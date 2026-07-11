import sys
from pathlib import Path

import httpx
from dotenv import set_key

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

TEMPLATE_BODY = (
    "Hi {{2}}! Following up on your inquiry — here's a property that matches "
    "what you're looking for:\n"
    "🏠 {{3}} in {{4}}   💰 Budget: {{5}}   🛏️ Bedrooms: {{6}}\n"
    "{{7}}\n"
    "Reply to this message or call us back to schedule a visit!"
)

CONTENT_PAYLOAD = {
    "friendly_name": "voxara_listing_match",
    "language": "en",
    "variables": {
        "1": "image_url", "2": "name", "3": "type",
        "4": "location", "5": "budget", "6": "bedrooms", "7": "summary",
    },
    "types": {
        "twilio/media": {
            "body": TEMPLATE_BODY,
            "media": ["{{1}}"],
        }
    },
}


def main():
    auth = (settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN)

    response = httpx.post(
        "https://content.twilio.com/v1/Content",
        auth=auth,
        json=CONTENT_PAYLOAD,
        timeout=30.0,
    )
    response.raise_for_status()
    content_sid = response.json()["sid"]
    print(f"Content template created: {content_sid}")

    approval_response = httpx.post(
        f"https://content.twilio.com/v1/Content/{content_sid}/ApprovalRequests/whatsapp",
        auth=auth,
        json={"name": "voxara_listing_match", "category": "UTILITY"},
        timeout=30.0,
    )
    approval_response.raise_for_status()
    print("Submitted for WhatsApp approval — this is manual/out-of-band and can take hours to days.")

    set_key(".env", "TWILIO_LISTING_TEMPLATE_SID", content_sid)
    print("Saved TWILIO_LISTING_TEMPLATE_SID to .env")


if __name__ == "__main__":
    main()
