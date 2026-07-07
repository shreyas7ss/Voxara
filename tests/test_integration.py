from unittest.mock import patch, AsyncMock

from app.graph.voxara_graph import process_call

SAMPLE_EXTRACTED = {
    "caller_name": "Priya",
    "caller_phone": None,
    "intent": "site_visit_request",
    "property_type": "3BHK",
    "location_preference": "Anna Nagar",
    "budget": "1 crore",
    "bedrooms": "3",
    "meeting_requested": True,
    "preferred_date": "2025-12-20",
    "preferred_time": "11:00 AM",
    "urgency": "high",
    "summary": "Priya wants a 3BHK in Anna Nagar",
    "follow_up_action": "Confirm site visit",
    "language_detected": "English",
}


async def test_full_pipeline_with_meeting():
    with patch("app.services.groq_service.transcribe_audio", new=AsyncMock(return_value={"transcript": "...", "language": "en"})), \
         patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=SAMPLE_EXTRACTED)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="WhatsApp summary text")), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM123"})), \
         patch("app.services.calendar_service.create_meeting_event", new=AsyncMock(return_value={"success": True, "event_id": "evt_456", "event_link": "https://cal.google.com/..."})):
        state = await process_call(call_id="test_001", transcript="I'm Priya, want to see a 3BHK")

    assert state["status"] == "done"
    assert state["whatsapp_result"]["success"] is True
    assert state["calendar_result"]["success"] is True


async def test_pipeline_without_meeting():
    extracted_no_meeting = {**SAMPLE_EXTRACTED, "meeting_requested": False}
    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=extracted_no_meeting)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="WhatsApp summary text")), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM124"})):
        state = await process_call(call_id="test_002", transcript="Just asking about prices")

    assert state["status"] == "done"
    assert state["calendar_result"] is None


async def test_stt_failure_handled_gracefully():
    with patch("app.services.groq_service.transcribe_audio", new=AsyncMock(side_effect=RuntimeError("STT_FAILED"))):
        state = await process_call(call_id="test_003", audio_bytes=b"fake_audio", transcript=None)

    assert state["status"] == "failed"
    assert "STT_FAILED" in state["errors"]


async def test_uses_existing_transcript_skips_stt():
    mock_stt = AsyncMock()
    extracted_no_meeting = {**SAMPLE_EXTRACTED, "meeting_requested": False}
    with patch("app.services.groq_service.transcribe_audio", new=mock_stt), \
         patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=extracted_no_meeting)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="WhatsApp summary text")), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM125"})):
        state = await process_call(call_id="test_004", transcript="Hi I want a 2BHK")

    mock_stt.assert_not_called()
    assert state["status"] == "done"
