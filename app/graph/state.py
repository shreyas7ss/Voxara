from typing import TypedDict, Optional, List


class VoxaraState(TypedDict):
    call_id: str
    audio_bytes: Optional[bytes]
    transcript: Optional[str]
    extracted_data: Optional[dict]
    formatted_summary: Optional[str]
    whatsapp_result: Optional[dict]
    calendar_result: Optional[dict]
    errors: List[str]
    status: str

    # Phase 9 — listings extension
    caller_whatsapp_number: Optional[str]
    matched_listings: Optional[List[dict]]
    listings_send_result: Optional[dict]
