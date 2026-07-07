import httpx

from app.config import settings


def main():
    response = httpx.patch(
        f"https://api.vapi.ai/phone-number/{settings.VAPI_PHONE_NUMBER_ID}",
        headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        json={"assistantId": settings.VAPI_ASSISTANT_ID},
        timeout=30.0,
    )
    response.raise_for_status()
    print(f"Phone number {settings.VAPI_PHONE_NUMBER_ID} assigned to assistant {settings.VAPI_ASSISTANT_ID}")


if __name__ == "__main__":
    main()
