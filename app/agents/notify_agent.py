from app.graph.state import VoxaraState
from app.services import whatsapp_service, calendar_service
from app.utils.logger import logger


async def send_whatsapp_node(state: VoxaraState) -> dict:
    result = await whatsapp_service.send_summary_to_agent(state["formatted_summary"])
    return {"whatsapp_result": result}


async def schedule_calendar_node(state: VoxaraState) -> dict:
    result = await calendar_service.create_meeting_event(state["extracted_data"])
    return {"calendar_result": result}


async def finalize_node(state: VoxaraState) -> dict:
    wa = state.get("whatsapp_result", {})
    cal = state.get("calendar_result")
    logger.info(
        f"[Voxara] Call {state['call_id']} complete | "
        f"WA: {wa.get('success')} | "
        f"Cal: {cal.get('success') if cal else 'skipped'}"
    )
    return {"status": "done"}
