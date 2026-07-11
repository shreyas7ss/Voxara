import asyncio
import io
import json

from groq import Groq
from tenacity import retry, stop_after_attempt, wait_exponential

from app.config import settings
from app.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT, WHATSAPP_SUMMARY_PROMPT
from app.prompts.listing_prompt import LISTING_EXTRACTION_SYSTEM_PROMPT
from app.utils.logger import logger

client = Groq(api_key=settings.GROQ_API_KEY, timeout=30.0)


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=4))
def _sync_transcribe(audio_bytes: bytes, mime_type: str) -> dict:
    audio_io = io.BytesIO(audio_bytes)
    response = client.audio.transcriptions.create(
        model="whisper-large-v3",
        file=("audio.wav", audio_io, mime_type),
    )
    return {"transcript": response.text, "language": getattr(response, "language", "unknown")}


async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> dict:
    loop = asyncio.get_event_loop()
    try:
        return await loop.run_in_executor(None, _sync_transcribe, audio_bytes, mime_type)
    except Exception as e:
        logger.error(f"STT failed after all retries: {e}")
        raise RuntimeError("STT_FAILED")


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=4))
def _sync_extract(transcript: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": f"Transcript:\n{transcript}"},
        ],
    )
    return response.choices[0].message.content


async def extract_call_data(transcript: str) -> dict:
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _sync_extract, transcript)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Extraction JSON parse failed, retrying once")
        raw = await loop.run_in_executor(None, _sync_extract, transcript)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Extraction JSON parse failed again: {e}")
            raise RuntimeError("EXTRACTION_FAILED")

    if not all(key in parsed for key in ("intent", "meeting_requested", "summary")):
        logger.error(f"Extraction result missing required fields: {parsed}")
        raise RuntimeError("EXTRACTION_FAILED")

    return parsed


@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=0.5, max=4))
def _sync_extract_listing(caption: str) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0.1,
        max_tokens=1000,
        messages=[
            {"role": "system", "content": LISTING_EXTRACTION_SYSTEM_PROMPT},
            {"role": "user", "content": caption},
        ],
    )
    return response.choices[0].message.content


async def extract_listing_data(caption: str) -> dict:
    loop = asyncio.get_event_loop()
    raw = await loop.run_in_executor(None, _sync_extract_listing, caption)

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError:
        logger.warning("Listing extraction JSON parse failed, retrying once")
        raw = await loop.run_in_executor(None, _sync_extract_listing, caption)
        try:
            parsed = json.loads(raw)
        except json.JSONDecodeError as e:
            logger.error(f"Listing extraction JSON parse failed again: {e}")
            raise RuntimeError("LISTING_EXTRACTION_FAILED")

    if not all(key in parsed for key in ("listing_summary", "availability_status")):
        logger.error(f"Listing extraction result missing required fields: {parsed}")
        raise RuntimeError("LISTING_EXTRACTION_FAILED")

    return parsed


def _sync_generate_summary(extracted_data: dict) -> str:
    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": WHATSAPP_SUMMARY_PROMPT},
            {"role": "user", "content": json.dumps(extracted_data, indent=2)},
        ],
    )
    return response.choices[0].message.content


async def generate_agent_summary(extracted_data: dict) -> str:
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, _sync_generate_summary, extracted_data)
