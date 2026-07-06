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
