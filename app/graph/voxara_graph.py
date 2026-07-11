from langgraph.graph import StateGraph, END

from app.graph.state import VoxaraState
from app.agents.call_agent import transcribe_call_node
from app.agents.summary_agent import extract_data_node, should_schedule_meeting
from app.agents.notify_agent import send_whatsapp_node, schedule_calendar_node, finalize_node
from app.agents.listing_agent import match_listings_node, should_send_listings, send_listings_node


def build_graph():
    graph = StateGraph(VoxaraState)

    graph.add_node("transcribe", transcribe_call_node)
    graph.add_node("extract", extract_data_node)
    graph.add_node("send_whatsapp", send_whatsapp_node)
    graph.add_node("schedule_meeting", schedule_calendar_node)
    graph.add_node("match_listings", match_listings_node)
    graph.add_node("send_listings", send_listings_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("transcribe")
    graph.add_edge("transcribe", "extract")
    graph.add_conditional_edges(
        "extract",
        should_schedule_meeting,
        {
            "notify_with_meeting": "schedule_meeting",
            "notify_without_meeting": "match_listings",
            "failed": END,
        }
    )
    graph.add_edge("schedule_meeting", "match_listings")
    graph.add_conditional_edges(
        "match_listings",
        should_send_listings,
        {
            "send": "send_listings",
            "skip": "send_whatsapp",
        }
    )
    graph.add_edge("send_listings", "send_whatsapp")
    graph.add_edge("send_whatsapp", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()


voxara_graph = build_graph()


async def process_call(
    call_id: str,
    audio_bytes: bytes = None,
    transcript: str = None,
    caller_whatsapp_number: str = None,
) -> VoxaraState:
    initial_state: VoxaraState = {
        "call_id": call_id,
        "audio_bytes": audio_bytes,
        "transcript": transcript,
        "extracted_data": None,
        "formatted_summary": None,
        "whatsapp_result": None,
        "calendar_result": None,
        "errors": [],
        "status": "received",
        "caller_whatsapp_number": caller_whatsapp_number,
        "matched_listings": None,
        "listings_send_result": None,
    }
    return await voxara_graph.ainvoke(initial_state)
