import asyncio
import json

from pydantic import BaseModel
from typing import Any, Optional

from app.config import settings
from app.services import calendar_service
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


def _payload_to_message(payload: VapiWebhookPayload | dict[str, Any]) -> dict[str, Any]:
    if isinstance(payload, VapiWebhookPayload):
        return payload.model_dump()
    if isinstance(payload, dict) and isinstance(payload.get("message"), dict):
        return payload["message"]
    if isinstance(payload, dict):
        return payload
    return {}


def _get_nested(data: dict[str, Any], *keys: str) -> Any:
    current: Any = data
    for key in keys:
        if not isinstance(current, dict):
            return None
        current = current.get(key)
    return current


def _extract_tool_calls(message: dict[str, Any]) -> list[dict[str, Any]]:
    def normalize_parameters(raw: Any) -> dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        if isinstance(raw, str):
            try:
                parsed = json.loads(raw)
                return parsed if isinstance(parsed, dict) else {}
            except json.JSONDecodeError:
                return {}
        return {}

    if isinstance(message.get("toolCallList"), list):
        return [
            {
                "id": tool_call.get("id"),
                "name": tool_call.get("name"),
                "parameters": normalize_parameters(tool_call.get("parameters") or tool_call.get("arguments")),
            }
            for tool_call in message["toolCallList"]
            if isinstance(tool_call, dict)
        ]

    if isinstance(message.get("toolWithToolCallList"), list):
        calls = []
        for item in message["toolWithToolCallList"]:
            if not isinstance(item, dict):
                continue
            tool_call = item.get("toolCall") or {}
            function = tool_call.get("function") or {}
            calls.append(
                {
                    "id": tool_call.get("id"),
                    "name": item.get("name") or function.get("name") or tool_call.get("name"),
                    "parameters": normalize_parameters(
                        tool_call.get("parameters") or function.get("parameters") or tool_call.get("arguments")
                    ),
                }
            )
        return calls

    if isinstance(message.get("toolCalls"), list):
        return [
            {
                "id": tool_call.get("id"),
                "name": tool_call.get("function", {}).get("name") or tool_call.get("name"),
                "parameters": normalize_parameters(
                    tool_call.get("function", {}).get("arguments") or tool_call.get("parameters")
                ),
            }
            for tool_call in message["toolCalls"]
            if isinstance(tool_call, dict)
        ]

    return []


def _agent_context_for_call(message: dict[str, Any]) -> dict[str, str]:
    phone_number_id = (
        _get_nested(message, "call", "phoneNumberId")
        or _get_nested(message, "call", "phoneNumber", "id")
        or _get_nested(message, "phoneNumber", "id")
        or settings.VAPI_PHONE_NUMBER_ID
    )
    return {
        "phone_number_id": phone_number_id or "",
        "calendar_id": settings.AGENT_CALENDAR_ID or "primary",
        "agent_whatsapp_number": settings.AGENT_WHATSAPP_NUMBER,
    }


def _caller_number_from_message(message: dict[str, Any]) -> Optional[str]:
    return (
        _get_nested(message, "call", "customer", "number")
        or _get_nested(message, "customer", "number")
    )


async def _handle_single_tool_call(tool_call: dict[str, Any], message: dict[str, Any]) -> dict[str, Any]:
    tool_call_id = tool_call.get("id") or ""
    tool_name = tool_call.get("name") or ""
    parameters = tool_call.get("parameters") or {}
    agent = _agent_context_for_call(message)

    try:
        if tool_name == "check_agent_availability":
            result = await calendar_service.check_agent_availability(
                parameters=parameters,
                calendar_id=agent["calendar_id"],
            )
            return {"name": tool_name, "toolCallId": tool_call_id, "result": result}

        if tool_name == "book_agent_meeting":
            if not parameters.get("callerPhone"):
                caller_number = _caller_number_from_message(message)
                if caller_number:
                    parameters = {**parameters, "callerPhone": caller_number}
            result = await calendar_service.book_agent_meeting(
                parameters=parameters,
                calendar_id=agent["calendar_id"],
            )
            return {"name": tool_name, "toolCallId": tool_call_id, "result": result}

        return {
            "name": tool_name,
            "toolCallId": tool_call_id,
            "error": f"Unsupported tool: {tool_name}",
        }
    except Exception as e:
        logger.error(f"Vapi tool call failed ({tool_name}/{tool_call_id}): {e}")
        return {"name": tool_name, "toolCallId": tool_call_id, "error": str(e)}


async def handle_tool_calls(message: dict[str, Any]) -> dict:
    tool_calls = _extract_tool_calls(message)
    results = []
    for tool_call in tool_calls:
        results.append(await _handle_single_tool_call(tool_call, message))
    return {"results": results}


async def handle_vapi_webhook(payload: VapiWebhookPayload | dict[str, Any]) -> dict:
    message = _payload_to_message(payload)
    message_type = message.get("type")

    if message_type == "tool-calls":
        return await handle_tool_calls(message)

    if message_type != "end-of-call-report":
        logger.info(f"Ignoring Vapi message type: {message_type}")
        return {"ignored": True, "type": message_type}

    call = message.get("call") or {}
    call_id = call.get("id") or "unknown_call"
    artifact = message.get("artifact") or {}
    transcript = (artifact.get("transcript") or message.get("transcript") or "").strip()

    if not transcript:
        logger.warning(f"Empty transcript for call {call_id}")
        return {"call_id": call_id, "status": "skipped", "reason": "empty_transcript"}

    caller_number = _caller_number_from_message(message)
    caller_whatsapp_number = f"whatsapp:{caller_number}" if caller_number else None

    from app.graph.voxara_graph import process_call
    try:
        final_state = await asyncio.wait_for(
            process_call(
                call_id=call_id,
                transcript=transcript,
                caller_whatsapp_number=caller_whatsapp_number,
            ),
            timeout=25,
        )
    except asyncio.TimeoutError:
        logger.error(f"process_call timed out for call {call_id}")
        return {"call_id": call_id, "status": "timeout", "errors": ["PROCESS_CALL_TIMEOUT"]}

    return {
        "call_id": call_id,
        "status": final_state["status"],
        "errors": final_state["errors"]
    }
