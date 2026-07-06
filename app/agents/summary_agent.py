from app.graph.state import VoxaraState
from app.services import groq_service
from app.utils.logger import logger


async def extract_data_node(state: VoxaraState) -> dict:
    if not state.get("transcript"):
        return {"errors": state["errors"] + ["NO_TRANSCRIPT"], "status": "failed"}
    try:
        extracted = await groq_service.extract_call_data(state["transcript"])
        summary = await groq_service.generate_agent_summary(extracted)
        return {"extracted_data": extracted, "formatted_summary": summary, "status": "extracted"}
    except RuntimeError as e:
        return {"errors": state["errors"] + [str(e)], "status": "failed"}


def should_schedule_meeting(state: VoxaraState) -> str:
    if state["status"] == "failed":
        return "failed"
    if state.get("extracted_data", {}).get("meeting_requested") is True:
        return "notify_with_meeting"
    return "notify_without_meeting"
