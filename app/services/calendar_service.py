import asyncio
from datetime import datetime, time, timedelta

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


def _sync_create_event_for_calendar(calendar_id: str, event_body: dict) -> dict:
    service = build("calendar", "v3", credentials=creds)
    return service.events().insert(calendarId=calendar_id, body=event_body).execute()


def _sync_freebusy(calendar_id: str, time_min: str, time_max: str) -> dict:
    service = build("calendar", "v3", credentials=creds)
    body = {
        "timeMin": time_min,
        "timeMax": time_max,
        "timeZone": "Asia/Kolkata",
        "items": [{"id": calendar_id}],
    }
    return service.freebusy().query(body=body).execute()


def _parse_tool_datetime(value: str, timezone_name: str = "Asia/Kolkata") -> datetime:
    tz = pytz.timezone(timezone_name)
    parsed = dateutil_parser.parse(value)
    if parsed.tzinfo is None:
        return tz.localize(parsed)
    return parsed.astimezone(tz)


def _overlaps(start_a: datetime, end_a: datetime, start_b: datetime, end_b: datetime) -> bool:
    return start_a < end_b and start_b < end_a


def _available_slots_for_busy_blocks(
    day_start: datetime,
    day_end: datetime,
    busy_blocks: list[dict],
    slot_minutes: int,
) -> list[dict]:
    slots = []
    current = day_start
    busy_ranges = []
    for block in busy_blocks:
        try:
            busy_ranges.append(
                (
                    _parse_tool_datetime(block["start"], day_start.tzinfo.zone),
                    _parse_tool_datetime(block["end"], day_start.tzinfo.zone),
                )
            )
        except Exception:
            logger.warning(f"Skipping unparsable busy block: {block}")

    while current + timedelta(minutes=slot_minutes) <= day_end:
        slot_end = current + timedelta(minutes=slot_minutes)
        if not any(_overlaps(current, slot_end, busy_start, busy_end) for busy_start, busy_end in busy_ranges):
            slots.append({"startTime": current.isoformat(), "endTime": slot_end.isoformat()})
        current = slot_end
    return slots


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


async def check_agent_availability(parameters: dict, calendar_id: str = "primary") -> dict:
    timezone_name = parameters.get("timezone") or "Asia/Kolkata"
    tz = pytz.timezone(timezone_name)
    date_text = parameters.get("date") or parameters.get("preferredDate")
    slot_minutes = int(parameters.get("durationMinutes") or 30)

    try:
        target_day = dateutil_parser.parse(date_text).date() if date_text else datetime.now(tz).date()
    except (TypeError, ValueError, OverflowError):
        target_day = datetime.now(tz).date()

    business_start = tz.localize(datetime.combine(target_day, time(hour=10)))
    business_end = tz.localize(datetime.combine(target_day, time(hour=18)))

    try:
        loop = asyncio.get_event_loop()
        freebusy = await loop.run_in_executor(
            None,
            _sync_freebusy,
            calendar_id,
            business_start.isoformat(),
            business_end.isoformat(),
        )
        busy_blocks = freebusy.get("calendars", {}).get(calendar_id, {}).get("busy", [])
        available_slots = _available_slots_for_busy_blocks(
            business_start,
            business_end,
            busy_blocks,
            slot_minutes,
        )
        return {"availableSlots": available_slots[:6], "calendarId": calendar_id}
    except Exception as e:
        logger.error(f"Calendar free/busy lookup failed: {e}")
        return {"availableSlots": [], "error": str(e), "calendarId": calendar_id}


async def book_agent_meeting(parameters: dict, calendar_id: str = "primary") -> dict:
    timezone_name = parameters.get("timezone") or "Asia/Kolkata"
    caller_name = parameters.get("callerName") or "Prospect"
    caller_phone = parameters.get("callerPhone") or ""
    property_interest = parameters.get("propertyInterest") or parameters.get("notes") or ""

    try:
        start_dt = _parse_tool_datetime(parameters["startTime"], timezone_name)
        if parameters.get("endTime"):
            end_dt = _parse_tool_datetime(parameters["endTime"], timezone_name)
        else:
            duration_minutes = int(parameters.get("durationMinutes") or 30)
            end_dt = start_dt + timedelta(minutes=duration_minutes)
    except Exception as e:
        logger.error(f"Invalid booking time from Vapi tool call: {e}")
        return {"success": False, "error": "INVALID_BOOKING_TIME"}

    event_body = {
        "summary": f"Property Meeting - {caller_name}",
        "description": (
            f"Caller: {caller_name}\n"
            f"Phone: {caller_phone}\n"
            f"Interest: {property_interest}\n\n"
            "Booked during a Voxara Vapi call"
        ),
        "start": {"dateTime": start_dt.isoformat(), "timeZone": timezone_name},
        "end": {"dateTime": end_dt.isoformat(), "timeZone": timezone_name},
        "reminders": {
            "useDefault": False,
            "overrides": [{"method": "popup", "minutes": 30}],
        },
    }

    try:
        loop = asyncio.get_event_loop()
        event = await loop.run_in_executor(None, _sync_create_event_for_calendar, calendar_id, event_body)
        return {
            "success": True,
            "eventId": event["id"],
            "htmlLink": event.get("htmlLink", ""),
            "startTime": start_dt.isoformat(),
            "endTime": end_dt.isoformat(),
        }
    except Exception as e:
        logger.error(f"Calendar booking failed: {e}")
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
