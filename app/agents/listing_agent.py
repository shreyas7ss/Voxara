from app.graph.state import VoxaraState
from app.services import listing_service, whatsapp_service
from app.utils.logger import logger

_MATCHABLE_INTENTS = ("property_inquiry", "site_visit_request")


async def match_listings_node(state: VoxaraState) -> dict:
    data = state.get("extracted_data") or {}
    if data.get("intent") not in _MATCHABLE_INTENTS:
        return {"matched_listings": []}
    if not (data.get("property_type") or data.get("location_preference")):
        return {"matched_listings": []}

    listings = await listing_service.get_active_listings()
    matches = listing_service.match_listings(data, listings)
    return {"matched_listings": matches}


def should_send_listings(state: VoxaraState) -> str:
    if state["status"] == "failed":
        return "skip"
    return "send" if state.get("matched_listings") else "skip"


async def send_listings_node(state: VoxaraState) -> dict:
    caller = state.get("caller_whatsapp_number")
    if not caller:
        logger.warning(f"[Voxara] Call {state['call_id']}: matched listings but no caller WhatsApp number")
        return {"listings_send_result": {"success": False, "error": "NO_CALLER_NUMBER"}}

    caller_name = (state.get("extracted_data") or {}).get("caller_name")
    results = []
    for listing in state["matched_listings"]:
        result = await whatsapp_service.send_listing_template_message(caller, listing, caller_name=caller_name)
        results.append(result)

    return {"listings_send_result": {"success": any(r["success"] for r in results), "results": results}}
