from unittest.mock import AsyncMock, patch

from app.services.vapi_service import handle_vapi_webhook


async def test_vapi_tool_calls_return_results_with_matching_ids():
    payload = {
        "message": {
            "type": "tool-calls",
            "call": {
                "id": "call_123",
                "phoneNumber": {"id": "pn_123"},
                "customer": {"number": "+919876543210"},
            },
            "toolCallList": [
                {
                    "id": "tool_avail_1",
                    "name": "check_agent_availability",
                    "arguments": {"date": "2026-07-13", "timezone": "Asia/Kolkata"},
                },
                {
                    "id": "tool_book_1",
                    "name": "book_agent_meeting",
                    "parameters": {
                        "callerName": "Priya",
                        "startTime": "2026-07-13T15:00:00+05:30",
                        "endTime": "2026-07-13T15:30:00+05:30",
                    },
                },
            ],
        }
    }

    availability = {
        "availableSlots": [
            {
                "startTime": "2026-07-13T15:00:00+05:30",
                "endTime": "2026-07-13T15:30:00+05:30",
            }
        ],
        "calendarId": "primary",
    }
    booking = {
        "success": True,
        "eventId": "evt_123",
        "htmlLink": "https://calendar.google.com/event",
        "startTime": "2026-07-13T15:00:00+05:30",
        "endTime": "2026-07-13T15:30:00+05:30",
    }

    with patch("app.services.calendar_service.check_agent_availability", new=AsyncMock(return_value=availability)), \
         patch("app.services.calendar_service.book_agent_meeting", new=AsyncMock(return_value=booking)) as mock_book:
        result = await handle_vapi_webhook(payload)

    assert result == {
        "results": [
            {"name": "check_agent_availability", "toolCallId": "tool_avail_1", "result": availability},
            {"name": "book_agent_meeting", "toolCallId": "tool_book_1", "result": booking},
        ]
    }
    mock_book.assert_awaited_once()
    assert mock_book.await_args.kwargs["parameters"]["callerPhone"] == "+919876543210"


async def test_wrapped_end_of_call_report_uses_artifact_transcript():
    payload = {
        "message": {
            "type": "end-of-call-report",
            "call": {"id": "call_456", "customer": {"number": "+919111111111"}},
            "artifact": {"transcript": "User asked about a 2BHK. Assistant helped."},
        }
    }
    final_state = {"status": "done", "errors": []}

    with patch("app.graph.voxara_graph.process_call", new=AsyncMock(return_value=final_state)) as mock_process:
        result = await handle_vapi_webhook(payload)

    assert result == {"call_id": "call_456", "status": "done", "errors": []}
    mock_process.assert_awaited_once_with(
        call_id="call_456",
        transcript="User asked about a 2BHK. Assistant helped.",
        caller_whatsapp_number="whatsapp:+919111111111",
    )
