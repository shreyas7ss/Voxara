from pydantic import BaseModel
from typing import Optional

from app.utils.logger import logger


class VapiCustomer(BaseModel):
    number: Optional[str] = None


class VapiCall(BaseModel):
    id: str
    phoneNumber: Optional[dict] = None
    customer: Optional[VapiCustomer] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None


class VapiWebhookPayload(BaseModel):
    type: str
    call: VapiCall
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    summary: Optional[str] = None


async def handle_vapi_webhook(payload: VapiWebhookPayload) -> dict:
    if payload.type != "end-of-call-report":
        return {"ignored": True}

    call_id = payload.call.id
    transcript = (payload.transcript or "").strip()

    if not transcript:
        logger.warning(f"Empty transcript for call {call_id}")
        return {"call_id": call_id, "status": "skipped", "reason": "empty_transcript"}

    caller_number = payload.call.customer.number if payload.call.customer else None
    caller_whatsapp_number = f"whatsapp:{caller_number}" if caller_number else None

    from app.graph.voxara_graph import process_call
    final_state = await process_call(
        call_id=call_id,
        transcript=transcript,
        caller_whatsapp_number=caller_whatsapp_number,
    )

    return {
        "call_id": call_id,
        "status": final_state["status"],
        "errors": final_state["errors"]
    }
