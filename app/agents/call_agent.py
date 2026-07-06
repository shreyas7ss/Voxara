from app.graph.state import VoxaraState
from app.services import groq_service
from app.utils.logger import logger


async def transcribe_call_node(state: VoxaraState) -> dict:
    if state.get("transcript"):
        return {"status": "transcribed"}
    if not state.get("audio_bytes"):
        return {"errors": state["errors"] + ["NO_AUDIO"], "status": "failed"}
    try:
        result = await groq_service.transcribe_audio(state["audio_bytes"])
        return {"transcript": result["transcript"], "status": "transcribed"}
    except RuntimeError as e:
        return {"errors": state["errors"] + [str(e)], "status": "failed"}
