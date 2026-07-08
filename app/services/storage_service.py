import asyncio

import boto3
import httpx

from app.config import settings
from app.utils.logger import logger

_s3_client = None


def _get_s3_client():
    global _s3_client
    if _s3_client is None:
        _s3_client = boto3.client(
            "s3",
            endpoint_url=settings.S3_ENDPOINT_URL or None,
            aws_access_key_id=settings.S3_ACCESS_KEY_ID or None,
            aws_secret_access_key=settings.S3_SECRET_ACCESS_KEY or None,
            region_name=settings.S3_REGION,
        )
    return _s3_client


async def download_twilio_media(media_url: str) -> tuple[bytes, str]:
    async with httpx.AsyncClient() as client:
        response = await client.get(
            media_url,
            auth=(settings.TWILIO_ACCOUNT_SID, settings.TWILIO_AUTH_TOKEN),
            timeout=30.0,
        )
        response.raise_for_status()
        content_type = response.headers.get("content-type", "application/octet-stream")
        return response.content, content_type


def _sync_upload_image(image_bytes: bytes, content_type: str, key: str) -> None:
    _get_s3_client().put_object(
        Bucket=settings.S3_BUCKET_NAME,
        Key=key,
        Body=image_bytes,
        ContentType=content_type,
    )


async def upload_image(image_bytes: bytes, content_type: str, key: str) -> str:
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, _sync_upload_image, image_bytes, content_type, key)
    public_url = f"{settings.S3_PUBLIC_BASE_URL.rstrip('/')}/{key}"
    logger.info(f"Uploaded image to S3: {public_url}")
    return public_url
