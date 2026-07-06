import asyncio
from datetime import datetime, timedelta

import pytz
from dateutil import parser as dateutil_parser
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build

from app.config import settings
from app.utils.logger import logger

IST = pytz.timezone("Asia/Kolkata")

creds = Credentials(
    token=None,
    refresh_token=settings.GOOGLE_REFRESH_TOKEN,
    client_id=settings.GOOGLE_CLIENT_ID,
    client_secret=settings.GOOGLE_CLIENT_SECRET,
    token_uri="https://oauth2.googleapis.com/token",
)


def _parse_meeting_datetime(extracted_data: dict) -> datetime:
    combined = f"{extracted_data.get('preferred_date') or ''} {extracted_data.get('preferred_time') or ''}".strip()
    try:
        if not combined:
            raise ValueError("no preferred date/time provided")
        parsed = dateutil_parser.parse(combined)
    except (ValueError, OverflowError) as e:
        logger.warning(f"Could not parse meeting datetime from '{combined}' ({e}), defaulting to tomorrow 10:00 AM IST")
        parsed = (datetime.now(IST) + timedelta(days=1)).replace(hour=10, minute=0, second=0, microsecond=0)

    if parsed.tzinfo is None:
        parsed = IST.localize(parsed)
    else:
        parsed = parsed.astimezone(IST)
    return parsed


def _sync_create_event(event_body: dict) -> dict:
    service = build("calendar", "v3", credentials=creds)
    return service.events().insert(calendarId="primary", body=event_body).execute()


async def create_meeting_event(extracted_data: dict) -> dict:
    if extracted_data.get("meeting_requested") is not True:
        return {"success": False, "reason": "meeting_not_requested"}

    start_dt = _parse_meeting_datetime(extracted_data)
    event_body = {
        "summary": f"Property Meeting — {extracted_data.get('caller_name', 'Prospect')}",
        "description": (extracted_data.get("summary") or "") + "\n\nAuto-created by Voxara",
        "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
        "end": {"dateTime": (start_dt + timedelta(hours=1)).isoformat(), "timeZone": "Asia/Kolkata"},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 30}],
        },
    }

    try:
        loop = asyncio.get_event_loop()
        event = await loop.run_in_executor(None, _sync_create_event, event_body)
        logger.info(f"Calendar event created: {event.get('id')}")
        return {"success": True, "event_id": event["id"], "event_link": event.get("htmlLink", "")}
    except Exception as e:
        logger.error(f"Calendar event creation failed: {e}")
        return {"success": False, "error": str(e)}


async def get_auth_url() -> str:
    client_config = {
        "web": {
            "client_id": settings.GOOGLE_CLIENT_ID,
            "client_secret": settings.GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
            "redirect_uris": [settings.GOOGLE_REDIRECT_URI],
        }
    }
    flow = Flow.from_client_config(
        client_config,
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=settings.GOOGLE_REDIRECT_URI,
    )
    auth_url, _ = flow.authorization_url(access_type="offline", prompt="consent")
    return auth_url
