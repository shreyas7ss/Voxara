from unittest.mock import patch, AsyncMock

from app.graph.voxara_graph import process_call

BASE_EXTRACTED = {
    "caller_name": "Rahul",
    "caller_phone": "9876543210",
    "intent": "site_visit_request",
    "property_type": "2BHK",
    "location_preference": "Velachery",
    "budget": "80 lakhs",
    "bedrooms": "2",
    "meeting_requested": False,
    "preferred_date": None,
    "preferred_time": None,
    "urgency": "medium",
    "summary": "Rahul wants a 2BHK in Velachery",
    "follow_up_action": "send listings",
    "language_detected": "English",
}

MATCHED_LISTING = {
    "id": 1, "property_type": "2BHK", "location": "Velachery",
    "price_text": "80 lakhs", "bedrooms": "2", "image_urls": ["https://cdn.example.com/a.jpg"],
    "listing_summary": "Spacious 2BHK", "match_score": 100,
}


async def test_meeting_requested_and_listings_matched_both_happen():
    extracted = {**BASE_EXTRACTED, "meeting_requested": True, "preferred_date": "2025-12-20", "preferred_time": "11:00 AM"}

    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=extracted)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="summary")), \
         patch("app.services.calendar_service.create_meeting_event", new=AsyncMock(return_value={"success": True, "event_id": "evt_1", "event_link": "https://cal/1"})), \
         patch("app.services.listing_service.get_active_listings", new=AsyncMock(return_value=[MATCHED_LISTING])), \
         patch("app.services.listing_service.match_listings", return_value=[MATCHED_LISTING]), \
         patch("app.services.whatsapp_service.send_listing_template_message", new=AsyncMock(return_value={"success": True, "message_sid": "SM_listing"})), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM_agent"})):
        state = await process_call(call_id="c1", transcript="...", caller_whatsapp_number="whatsapp:+919876543210")

    assert state["status"] == "done"
    assert state["calendar_result"]["success"] is True
    assert state["listings_send_result"]["success"] is True
    assert len(state["matched_listings"]) == 1


async def test_no_meeting_but_listings_matched():
    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=BASE_EXTRACTED)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="summary")), \
         patch("app.services.listing_service.get_active_listings", new=AsyncMock(return_value=[MATCHED_LISTING])), \
         patch("app.services.listing_service.match_listings", return_value=[MATCHED_LISTING]), \
         patch("app.services.whatsapp_service.send_listing_template_message", new=AsyncMock(return_value={"success": True, "message_sid": "SM_listing"})), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM_agent"})):
        state = await process_call(call_id="c2", transcript="...", caller_whatsapp_number="whatsapp:+919876543210")

    assert state["status"] == "done"
    assert state["calendar_result"] is None
    assert len(state["matched_listings"]) == 1


async def test_no_matches_found_skips_send_listings():
    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=BASE_EXTRACTED)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="summary")), \
         patch("app.services.listing_service.get_active_listings", new=AsyncMock(return_value=[])), \
         patch("app.services.whatsapp_service.send_listing_template_message", new=AsyncMock()) as mock_send_listing, \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM_agent"})):
        state = await process_call(call_id="c3", transcript="...", caller_whatsapp_number="whatsapp:+919876543210")

    assert state["status"] == "done"
    assert state["matched_listings"] == []
    assert state["listings_send_result"] is None
    mock_send_listing.assert_not_called()


async def test_general_inquiry_skips_listing_lookup_entirely():
    extracted = {**BASE_EXTRACTED, "intent": "general_inquiry"}

    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=extracted)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="summary")), \
         patch("app.services.listing_service.get_active_listings", new=AsyncMock()) as mock_get_listings, \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM_agent"})):
        state = await process_call(call_id="c4", transcript="...", caller_whatsapp_number="whatsapp:+919876543210")

    assert state["status"] == "done"
    assert state["matched_listings"] == []
    mock_get_listings.assert_not_called()


async def test_no_caller_number_degrades_gracefully_instead_of_crashing():
    with patch("app.services.groq_service.extract_call_data", new=AsyncMock(return_value=BASE_EXTRACTED)), \
         patch("app.services.groq_service.generate_agent_summary", new=AsyncMock(return_value="summary")), \
         patch("app.services.listing_service.get_active_listings", new=AsyncMock(return_value=[MATCHED_LISTING])), \
         patch("app.services.listing_service.match_listings", return_value=[MATCHED_LISTING]), \
         patch("app.services.whatsapp_service.send_summary_to_agent", new=AsyncMock(return_value={"success": True, "message_sid": "SM_agent"})):
        state = await process_call(call_id="c5", transcript="...", caller_whatsapp_number=None)

    assert state["status"] == "done"
    assert state["listings_send_result"] == {"success": False, "error": "NO_CALLER_NUMBER"}
