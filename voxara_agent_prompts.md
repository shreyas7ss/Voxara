# Voxara — Phase-wise Agent Execution Prompts
### AI Call Assistant for Real Estate Agents
**Stack:** Python · FastAPI · Vapi · Groq API (Whisper + LLaMA) · LangGraph · Twilio WhatsApp · Google Calendar API

---

## HOW TO USE THESE PROMPTS
- Feed each phase prompt to your AI coding agent (Cursor / Windsurf / Copilot) **one phase at a time**
- Do NOT move to the next phase until the current phase passes all its validation checks
- Each prompt is self-contained — it includes context, exact file structure, code patterns, and done criteria
- Replace all `YOUR_*` placeholders with real credentials before running

---

## PHASE 1 — Project Scaffold & Environment Setup

```
You are building "Voxara", an AI-powered call assistant for real estate agents.
When a prospect calls the agent's number, Voxara answers, has a conversation,
then automatically sends a WhatsApp summary to the agent and creates a Google
Calendar event if a meeting was requested.

TASK: Scaffold the entire project structure and configure the environment.

Create the following directory and file structure exactly:

voxara/
├── app/
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── call_agent.py          # LangGraph call handling node
│   │   ├── summary_agent.py       # LangGraph summary + intent nodes
│   │   └── notify_agent.py        # LangGraph notification nodes
│   ├── graph/
│   │   ├── __init__.py
│   │   └── voxara_graph.py        # Main LangGraph state machine
│   ├── services/
│   │   ├── __init__.py
│   │   ├── groq_service.py        # Groq API — STT + LLM calls
│   │   ├── whatsapp_service.py    # Twilio WhatsApp API
│   │   ├── calendar_service.py    # Google Calendar API
│   │   └── vapi_service.py        # Vapi webhook handler
│   ├── prompts/
│   │   ├── __init__.py
│   │   └── extraction_prompt.py   # Groq LLM system prompt
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── logger.py              # Loguru logger
│   │   └── validators.py          # Pydantic validators
│   └── main.py                    # FastAPI server entry point
├── tests/
│   ├── __init__.py
│   └── test_integration.py
├── scripts/
│   ├── setup_vapi_assistant.py
│   ├── assign_phone_number.py
│   └── test_call.py
├── .env.example
├── .env                           # gitignored
├── .gitignore
├── requirements.txt
├── Dockerfile
├── docker-compose.yml
└── README.md

CREATE requirements.txt with these exact packages:
fastapi==0.115.0
uvicorn[standard]==0.30.0
langgraph==0.2.28
langchain-core==0.3.15
groq==0.11.0
twilio==9.3.0
google-api-python-client==2.149.0
google-auth-httplib2==0.2.0
google-auth-oauthlib==1.2.1
python-dotenv==1.0.1
pydantic==2.9.2
pydantic-settings==2.5.2
loguru==0.7.2
httpx==0.27.2
tenacity==9.0.0
python-dateutil==2.9.0
pytz==2024.2
slowapi==0.1.9
pytest==8.3.3
pytest-asyncio==0.24.0
python-multipart==0.0.12

CREATE .env.example with these keys (empty values):
GROQ_API_KEY=
VAPI_API_KEY=
VAPI_PHONE_NUMBER_ID=
VAPI_ASSISTANT_ID=
VAPI_WEBHOOK_SECRET=
TWILIO_ACCOUNT_SID=
TWILIO_AUTH_TOKEN=
WHATSAPP_FROM_NUMBER=whatsapp:+14155238886
AGENT_WHATSAPP_NUMBER=whatsapp:+91XXXXXXXXXX
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://localhost:8000/auth/google/callback
GOOGLE_REFRESH_TOKEN=
PORT=8000
ENV=development

CREATE .gitignore:
__pycache__/
*.pyc
*.pyo
.env
*.egg-info/
.pytest_cache/
logs/
token.json
credentials.json
.venv/

SETUP virtual environment and install:
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

DONE CRITERIA:
- pip install -r requirements.txt completes with zero errors
- Directory tree matches exactly, all __init__.py files exist
- python -c "import fastapi, langgraph, groq, twilio" runs without error
- .env.example contains all required keys
```

---

## PHASE 2 — Groq Service (STT + LLM)

```
Context: Voxara project. You are implementing the Groq service layer in Python.
Groq provides Whisper-based STT and LLaMA-based LLM at ultra-low latency
(~200ms), which is critical for real-time voice processing.

TASK: Build app/services/groq_service.py and app/prompts/extraction_prompt.py

--- app/prompts/extraction_prompt.py ---

Define a module-level string constant EXTRACTION_SYSTEM_PROMPT with this content
(do not modify the JSON schema):

You are Voxara, an AI assistant for a real estate agent. You have just received
a call transcript. Extract structured information and respond ONLY with a valid
JSON object matching this exact schema — no preamble, no markdown, no explanation:

{
  "caller_name": "string or null",
  "caller_phone": "string or null",
  "intent": "property_inquiry | site_visit_request | pricing_query | general_inquiry | complaint | other",
  "property_type": "string or null",
  "location_preference": "string or null",
  "budget": "string or null",
  "bedrooms": "string or null",
  "meeting_requested": true or false,
  "preferred_date": "string or null (ISO 8601 date if detectable, else natural language)",
  "preferred_time": "string or null",
  "urgency": "high | medium | low",
  "summary": "2-3 sentence plain English summary of the call for the agent",
  "follow_up_action": "string describing what the agent should do next",
  "language_detected": "string (e.g. English, Hindi, Tamil)"
}

If a field cannot be determined from the transcript, use null.
Never hallucinate information not present in the transcript.

Also define WHATSAPP_SUMMARY_PROMPT as a string that instructs the LLM to
format a WhatsApp-friendly message from structured call data. Output must:
- Use emoji for readability
- Follow this exact structure:
  📞 *New Call Summary — Voxara*
  👤 Caller: {name}
  📋 Intent: {intent}
  🏠 Property: {type} in {location} | Budget: {budget}
  📅 Meeting: {date and time OR "Not requested"}
  ✅ Action: {follow_up_action}

--- app/services/groq_service.py ---

Use the groq Python SDK.
Load settings using pydantic-settings from .env.
Initialize: client = Groq(api_key=settings.GROQ_API_KEY)

Create a Settings class (or import from a shared config module) using
pydantic_settings.BaseSettings that reads GROQ_API_KEY from .env.

Define these three async functions:

1. async def transcribe_audio(audio_bytes: bytes, mime_type: str = "audio/wav") -> dict
   - Calls Groq Whisper: model = "whisper-large-v3"
   - Wrap audio_bytes in io.BytesIO, pass as file=("audio.wav", audio_io, mime_type)
   - Groq SDK is synchronous — run in thread executor:
     loop = asyncio.get_event_loop()
     result = await loop.run_in_executor(None, _sync_transcribe, audio_bytes, mime_type)
   - Use @retry from tenacity: stop=stop_after_attempt(3),
     wait=wait_exponential(multiplier=1, min=0.5, max=4)
     (apply to the inner sync helper, not the async wrapper)
   - Returns: {"transcript": str, "language": str}
   - On all retries exhausted: raise RuntimeError("STT_FAILED")

2. async def extract_call_data(transcript: str) -> dict
   - Calls Groq LLM: model = "llama-3.3-70b-versatile"
   - temperature = 0.1, max_tokens = 1000
   - messages = [
       {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
       {"role": "user", "content": f"Transcript:\n{transcript}"}
     ]
   - Run in thread executor (SDK is sync)
   - Parse response content with json.loads()
   - Validate result has: intent, meeting_requested, summary
   - On JSON parse failure retry once, then raise RuntimeError("EXTRACTION_FAILED")
   - Returns the parsed dict

3. async def generate_agent_summary(extracted_data: dict) -> str
   - Calls Groq LLM: model = "llama-3.3-70b-versatile"
   - System: WHATSAPP_SUMMARY_PROMPT
   - User: json.dumps(extracted_data, indent=2)
   - Run in thread executor
   - Returns the raw string content

DONE CRITERIA:
- python -c "from app.services.groq_service import transcribe_audio, extract_call_data, generate_agent_summary" runs without error
- python -c "from app.prompts.extraction_prompt import EXTRACTION_SYSTEM_PROMPT; print(len(EXTRACTION_SYSTEM_PROMPT))" prints > 200
- No syntax errors in either file
```

---

## PHASE 3 — WhatsApp & Google Calendar Services

```
Context: Voxara project. Implement the two notification services in Python.

TASK A: Build app/services/whatsapp_service.py

Use the Twilio Python SDK.
from twilio.rest import Client

Initialize using settings.TWILIO_ACCOUNT_SID and settings.TWILIO_AUTH_TOKEN.

Define:

async def send_summary_to_agent(summary_text: str, to_number: str = None) -> dict:
  - to_number defaults to settings.AGENT_WHATSAPP_NUMBER if None
  - Twilio SDK is synchronous — run in thread executor
  - Call: client.messages.create(
        from_=settings.WHATSAPP_FROM_NUMBER,
        to=to_number,
        body=summary_text
    )
  - Returns: {"success": True, "message_sid": str(message.sid)}
  - On any exception: returns {"success": False, "error": str(e)}
  - NEVER raise — always return the dict
  - Log both outcomes with loguru logger

TASK B: Build app/services/calendar_service.py

Imports needed:
  from google.oauth2.credentials import Credentials
  from googleapiclient.discovery import build
  from google_auth_oauthlib.flow import Flow
  from datetime import datetime, timedelta
  from dateutil import parser as dateutil_parser
  import pytz, asyncio

Build credentials from settings:
  creds = Credentials(
      token=None,
      refresh_token=settings.GOOGLE_REFRESH_TOKEN,
      client_id=settings.GOOGLE_CLIENT_ID,
      client_secret=settings.GOOGLE_CLIENT_SECRET,
      token_uri="https://oauth2.googleapis.com/token"
  )

Define:

async def create_meeting_event(extracted_data: dict) -> dict:
  - Return immediately if extracted_data.get("meeting_requested") is not True
  - Parse date: combine extracted_data["preferred_date"] + extracted_data["preferred_time"]
    Use dateutil_parser.parse() inside a try/except
    On failure: default to tomorrow at 10:00 AM IST
  - Localize to pytz.timezone("Asia/Kolkata")
  - Build event body dict (see below)
  - Run calendar API call in thread executor:
    service = build("calendar", "v3", credentials=creds)
    event = service.events().insert(calendarId="primary", body=event_body).execute()
  - Returns: {"success": True, "event_id": event["id"], "event_link": event.get("htmlLink", "")}
  - On exception: returns {"success": False, "error": str(e)}

  Event body:
  {
    "summary": f"Property Meeting — {extracted_data.get('caller_name', 'Prospect')}",
    "description": extracted_data.get("summary", "") + "\n\nAuto-created by Voxara",
    "start": {"dateTime": start_dt.isoformat(), "timeZone": "Asia/Kolkata"},
    "end": {"dateTime": (start_dt + timedelta(hours=1)).isoformat(), "timeZone": "Asia/Kolkata"},
    "reminders": {
        "useDefault": False,
        "overrides": [{"method": "popup", "minutes": 30}]
    }
  }

async def get_auth_url() -> str:
  - Creates a Flow using client_config dict built from settings
  - scopes = ["https://www.googleapis.com/auth/calendar"]
  - redirect_uri = settings.GOOGLE_REDIRECT_URI
  - Returns the authorization URL string

DONE CRITERIA:
- python -c "from app.services.whatsapp_service import send_summary_to_agent" — no error
- python -c "from app.services.calendar_service import create_meeting_event, get_auth_url" — no error
- Both files have no syntax errors
```

---

## PHASE 4 — LangGraph Agents & State Machine

```
Context: Voxara project. This is the core phase.
Build the agentic pipeline using LangGraph (Python).
Each node is a discrete async function. The StateGraph
manages transitions and conditional branching.

TASK: Build all agent files and the main LangGraph graph.

--- SHARED STATE SCHEMA ---

Define this TypedDict in app/graph/voxara_graph.py and import
it into all agent files:

from typing import TypedDict, Optional, List

class VoxaraState(TypedDict):
    call_id: str
    audio_bytes: Optional[bytes]
    transcript: Optional[str]
    extracted_data: Optional[dict]
    formatted_summary: Optional[str]
    whatsapp_result: Optional[dict]
    calendar_result: Optional[dict]
    errors: List[str]
    status: str

--- app/agents/call_agent.py ---

from app.graph.voxara_graph import VoxaraState
from app.services import groq_service
from app.utils.logger import logger

async def transcribe_call_node(state: VoxaraState) -> dict:
    # If transcript already present, skip STT entirely
    if state.get("transcript"):
        return {"status": "transcribed"}
    if not state.get("audio_bytes"):
        return {"errors": state["errors"] + ["NO_AUDIO"], "status": "failed"}
    try:
        result = await groq_service.transcribe_audio(state["audio_bytes"])
        return {"transcript": result["transcript"], "status": "transcribed"}
    except RuntimeError as e:
        return {"errors": state["errors"] + [str(e)], "status": "failed"}

NOTE: LangGraph nodes return only the keys they want to update — not the full state.

--- app/agents/summary_agent.py ---

from app.graph.voxara_graph import VoxaraState
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
    # Conditional edge — returns string key matching the routing dict
    if state["status"] == "failed":
        return "failed"
    if state.get("extracted_data", {}).get("meeting_requested") is True:
        return "notify_with_meeting"
    return "notify_without_meeting"

--- app/agents/notify_agent.py ---

from app.graph.voxara_graph import VoxaraState
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

--- app/graph/voxara_graph.py ---

from langgraph.graph import StateGraph, END
from typing import TypedDict, Optional, List
from app.agents.call_agent import transcribe_call_node
from app.agents.summary_agent import extract_data_node, should_schedule_meeting
from app.agents.notify_agent import send_whatsapp_node, schedule_calendar_node, finalize_node

class VoxaraState(TypedDict):
    call_id: str
    audio_bytes: Optional[bytes]
    transcript: Optional[str]
    extracted_data: Optional[dict]
    formatted_summary: Optional[str]
    whatsapp_result: Optional[dict]
    calendar_result: Optional[dict]
    errors: List[str]
    status: str

def build_graph():
    graph = StateGraph(VoxaraState)

    graph.add_node("transcribe", transcribe_call_node)
    graph.add_node("extract", extract_data_node)
    graph.add_node("send_whatsapp", send_whatsapp_node)
    graph.add_node("schedule_meeting", schedule_calendar_node)
    graph.add_node("finalize", finalize_node)

    graph.set_entry_point("transcribe")
    graph.add_edge("transcribe", "extract")
    graph.add_conditional_edges(
        "extract",
        should_schedule_meeting,
        {
            "notify_with_meeting": "schedule_meeting",
            "notify_without_meeting": "send_whatsapp",
            "failed": END,
        }
    )
    graph.add_edge("schedule_meeting", "send_whatsapp")
    graph.add_edge("send_whatsapp", "finalize")
    graph.add_edge("finalize", END)

    return graph.compile()

voxara_graph = build_graph()

async def process_call(
    call_id: str,
    audio_bytes: bytes = None,
    transcript: str = None
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
    }
    return await voxara_graph.ainvoke(initial_state)

DONE CRITERIA:
- python -c "from app.graph.voxara_graph import voxara_graph, process_call" runs without error
- The graph has exactly 5 nodes
- should_schedule_meeting returns correct branch for all 3 cases
- All agent files import without error
```

---

## PHASE 5 — Vapi Webhook Handler & FastAPI Server

```
Context: Voxara project. Wire up the FastAPI server that receives
Vapi webhooks when a call ends.

TASK A: Build app/services/vapi_service.py

Define Pydantic models:

from pydantic import BaseModel
from typing import Optional

class VapiCall(BaseModel):
    id: str
    phoneNumber: Optional[dict] = None
    startedAt: Optional[str] = None
    endedAt: Optional[str] = None

class VapiWebhookPayload(BaseModel):
    type: str
    call: VapiCall
    transcript: Optional[str] = None
    recordingUrl: Optional[str] = None
    summary: Optional[str] = None

Define:

async def handle_vapi_webhook(payload: VapiWebhookPayload) -> dict:
    if payload.type != "end-of-call-report":
        return {"ignored": True}

    call_id = payload.call.id
    transcript = (payload.transcript or "").strip()

    if not transcript:
        logger.warning(f"Empty transcript for call {call_id}")
        return {"call_id": call_id, "status": "skipped", "reason": "empty_transcript"}

    from app.graph.voxara_graph import process_call
    final_state = await process_call(call_id=call_id, transcript=transcript)

    return {
        "call_id": call_id,
        "status": final_state["status"],
        "errors": final_state["errors"]
    }

TASK B: Build app/main.py

from fastapi import FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse
from typing import Optional
from datetime import datetime
from app.services.vapi_service import VapiWebhookPayload, handle_vapi_webhook
from app.services import calendar_service
from app.utils.logger import logger
from app.config import settings

app = FastAPI(title="Voxara", version="1.0.0")

@app.post("/webhook/vapi")
async def vapi_webhook(
    payload: VapiWebhookPayload,
    x_vapi_secret: Optional[str] = Header(None)
):
    if x_vapi_secret != settings.VAPI_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = await handle_vapi_webhook(payload)
    return {"received": True, **result}

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "voxara",
        "timestamp": datetime.utcnow().isoformat()
    }

@app.get("/auth/google")
async def google_auth():
    url = await calendar_service.get_auth_url()
    return RedirectResponse(url)

@app.get("/auth/google/callback")
async def google_callback(code: str):
    logger.info(f"Google OAuth code received: {code[:20]}...")
    return {"message": "Auth code received. Exchange it for a refresh_token manually and add to .env"}

@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled error on {request.url}: {exc}")
    return JSONResponse(status_code=500, content={"error": str(exc)})

Also create app/config.py with a pydantic-settings Settings class that
loads all env vars. Import this settings object everywhere instead of
calling os.getenv() directly.

Run with: uvicorn app.main:app --reload --port 8000

DONE CRITERIA:
- uvicorn app.main:app --reload starts on port 8000 without errors
- GET /health returns 200 JSON
- POST /webhook/vapi with wrong x-vapi-secret returns 401
- POST /webhook/vapi with correct secret + sample payload returns 200
- http://localhost:8000/docs loads the FastAPI Swagger UI
```

---

## PHASE 6 — Vapi Assistant Configuration

```
Context: Voxara project. Configure the Vapi AI voice assistant via API.

TASK: Create scripts/setup_vapi_assistant.py

Use httpx to POST to https://api.vapi.ai/assistant.
Set header: Authorization: Bearer {VAPI_API_KEY}

assistant_config = {
    "name": "Voxara",
    "firstMessage": "Hello! You've reached the office. I'm Voxara, the AI assistant. How can I help you today?",
    "model": {
        "provider": "groq",
        "model": "llama-3.3-70b-versatile",
        "messages": [
            {
                "role": "system",
                "content": (
                    "You are Voxara, a professional AI assistant for a real estate agent.\n"
                    "Your job is to:\n"
                    "1. Greet the caller warmly and professionally\n"
                    "2. Understand what property they are looking for (type, location, budget, bedrooms)\n"
                    "3. Find out if they want to schedule a site visit or meeting\n"
                    "4. If they want a meeting, ask for their preferred date and time\n"
                    "5. Collect their name and confirm their phone number\n"
                    "6. Thank them and let them know the agent will follow up shortly\n\n"
                    "Rules:\n"
                    "- Keep responses short and conversational (1-2 sentences max)\n"
                    "- Never make up property listings or prices\n"
                    "- If asked something you cannot answer, say the agent will call them back\n"
                    "- Be warm, professional, and concise\n"
                    "- Support English, Hindi, and Tamil naturally"
                )
            }
        ],
        "temperature": 0.7
    },
    "voice": {
        "provider": "11labs",
        "voiceId": "21m00Tcm4TlvDq8ikWAM"
    },
    "transcriber": {
        "provider": "deepgram",
        "model": "nova-2",
        "language": "en"
    },
    "endCallMessage": "Thank you for calling! The agent will be in touch soon. Have a great day!",
    "endCallPhrases": ["goodbye", "bye", "thank you bye", "that's all"],
    "serverUrl": "YOUR_NGROK_OR_PRODUCTION_URL/webhook/vapi",
    "serverUrlSecret": "YOUR_VAPI_WEBHOOK_SECRET"
}

After a successful POST:
  - Print the returned assistant id
  - Append VAPI_ASSISTANT_ID={id} to .env automatically using python-dotenv set_key()

Also create scripts/assign_phone_number.py:
  - Load VAPI_PHONE_NUMBER_ID and VAPI_ASSISTANT_ID from .env
  - PATCH https://api.vapi.ai/phone-number/{VAPI_PHONE_NUMBER_ID}
  - Body: {"assistantId": VAPI_ASSISTANT_ID}
  - Print confirmation

Both scripts should be runnable as:
  python scripts/setup_vapi_assistant.py
  python scripts/assign_phone_number.py

DONE CRITERIA:
- Both scripts run without syntax errors (python -m py_compile scripts/setup_vapi_assistant.py)
- setup_vapi_assistant.py creates the assistant when VAPI_API_KEY is valid
- assign_phone_number.py patches the phone number assignment
```

---

## PHASE 7 — End-to-End Testing & Validation

```
Context: Voxara project. Write integration tests and a manual test harness.

TASK A: Create tests/test_integration.py

Use pytest and pytest-asyncio.
Add to pytest config (pyproject.toml or pytest.ini):
  asyncio_mode = "auto"

Use unittest.mock.AsyncMock and patch for all external services.

Write these 4 test cases:

1. async def test_full_pipeline_with_meeting():
   Mock targets (use patch as context manager or decorator):
     - "app.services.groq_service.transcribe_audio"  → returns {"transcript": "...", "language": "en"}
     - "app.services.groq_service.extract_call_data" → returns {
           "intent": "site_visit_request", "meeting_requested": True,
           "caller_name": "Priya", "summary": "Priya wants a 3BHK in Anna Nagar",
           "preferred_date": "2025-12-20", "preferred_time": "11:00 AM",
           "follow_up_action": "Confirm site visit", "urgency": "high",
           "property_type": "3BHK", "location_preference": "Anna Nagar",
           "budget": "1 crore", "language_detected": "English"
       }
     - "app.services.groq_service.generate_agent_summary" → returns "WhatsApp summary text"
     - "app.services.whatsapp_service.send_summary_to_agent" → returns {"success": True, "message_sid": "SM123"}
     - "app.services.calendar_service.create_meeting_event" → returns {"success": True, "event_id": "evt_456", "event_link": "https://cal.google.com/..."}
   
   state = await process_call(call_id="test_001", transcript="I'm Priya, want to see a 3BHK")
   assert state["status"] == "done"
   assert state["whatsapp_result"]["success"] is True
   assert state["calendar_result"]["success"] is True

2. async def test_pipeline_without_meeting():
   Mock extract_call_data to return meeting_requested=False
   state = await process_call(call_id="test_002", transcript="Just asking about prices")
   assert state["status"] == "done"
   assert state["calendar_result"] is None

3. async def test_stt_failure_handled_gracefully():
   Mock transcribe_audio to raise RuntimeError("STT_FAILED")
   state = await process_call(call_id="test_003", audio_bytes=b"fake_audio", transcript=None)
   assert state["status"] == "failed"
   assert "STT_FAILED" in state["errors"]

4. async def test_uses_existing_transcript_skips_stt():
   Mock transcribe_audio as AsyncMock (track calls)
   state = await process_call(call_id="test_004", transcript="Hi I want a 2BHK")
   mock_stt.assert_not_called()
   assert state["status"] == "done"

TASK B: Create scripts/test_call.py — manual test harness

import asyncio, json
from app.graph.voxara_graph import process_call

SAMPLE_TRANSCRIPT = """
Hello, my name is Rahul and I am calling to inquire about 2BHK apartments
in Velachery. My budget is around 80 lakhs. Can we schedule a site visit
this Saturday at 11am? My number is 9876543210.
"""

async def main():
    print("Running Voxara test call simulation...\n")
    state = await process_call(
        call_id="manual_test_001",
        transcript=SAMPLE_TRANSCRIPT
    )
    # Print state excluding audio_bytes (not serializable)
    printable = {k: v for k, v in state.items() if k != "audio_bytes"}
    print(json.dumps(printable, indent=2, default=str))

if __name__ == "__main__":
    asyncio.run(main())

Create pytest.ini in the project root:
[pytest]
asyncio_mode = auto
testpaths = tests

DONE CRITERIA:
- pytest runs all 4 tests and they all PASS with no warnings
- python scripts/test_call.py prints a full JSON state ending in "status": "done"
- No unhandled coroutine warnings or RuntimeWarnings
```

---

## PHASE 8 — Production Hardening & Deployment Prep

```
Context: Voxara project. Final phase — harden and containerize.

TASK A: Add rate limiting to app/main.py
  from slowapi import Limiter, _rate_limit_exceeded_handler
  from slowapi.util import get_remote_address
  from slowapi.errors import RateLimitExceeded

  limiter = Limiter(key_func=get_remote_address)
  app.state.limiter = limiter
  app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

  Decorate the webhook route:
  @limiter.limit("100/minute")
  @app.post("/webhook/vapi")
  async def vapi_webhook(request: Request, ...):

TASK B: Verify tenacity retries in groq_service.py
  - transcribe_audio and extract_call_data must have @retry decorators on
    their inner sync helpers
  - Add a 30-second timeout to all Groq client calls:
    client = Groq(api_key=settings.GROQ_API_KEY, timeout=30.0)
  - In vapi_service.py wrap process_call in asyncio.wait_for with timeout=25

TASK C: Build app/utils/logger.py

from loguru import logger
import sys, os

ENV = os.getenv("ENV", "development")
LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO")

logger.remove()

if ENV == "production":
    os.makedirs("logs", exist_ok=True)
    logger.add(
        "logs/voxara.log",
        rotation="10 MB",
        retention="7 days",
        level=LOG_LEVEL,
        serialize=True   # JSON format in production
    )
else:
    logger.add(
        sys.stderr,
        level=LOG_LEVEL,
        colorize=True,
        format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | <cyan>{name}</cyan> - {message}"
    )

# Re-export logger for use across all modules

TASK D: Create Dockerfile

FROM python:3.12-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY app/ ./app/
RUN mkdir -p logs
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--workers", "2"]

TASK E: Create docker-compose.yml

services:
  voxara:
    build: .
    ports:
      - "8000:8000"
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8000/health"]
      interval: 30s
      timeout: 10s
      retries: 3

TASK F: Update README.md with these sections:
  ## Overview
  ## Architecture
  ## Quick Start
  ## Environment Variables (table with description for each key)
  ## Google OAuth Setup (step-by-step)
  ## Vapi Assistant Setup
  ## WhatsApp Setup via Twilio
  ## Running Locally with ngrok
  ## Running with Docker
  ## Running Tests
  ## Troubleshooting

DONE CRITERIA:
- docker build -t voxara . completes with no errors
- docker-compose up starts server, GET /health returns {"status": "ok"}
- pytest still passes all 4 tests
- Rate limiting responds 429 after 100 req/min on /webhook/vapi
- README.md covers all required sections
```

---

## MASTER CHECKLIST

Before going live, verify every item:

- [ ] All 8 phases complete with zero errors
- [ ] `.env` filled with real credentials — never commit this file
- [ ] Groq API key tested — both STT and LLM responding correctly
- [ ] Vapi assistant created: `python scripts/setup_vapi_assistant.py`
- [ ] Phone number assigned: `python scripts/assign_phone_number.py`
- [ ] WhatsApp Twilio Sandbox or Business API tested with a real message
- [ ] Google Calendar OAuth flow completed via `/auth/google`, refresh token saved
- [ ] Webhook URL publicly reachable (ngrok: `ngrok http 8000`)
- [ ] End-to-end: call the Vapi number → WhatsApp summary received by agent
- [ ] Meeting test: say a date/time during call → Google Calendar event created
- [ ] All 4 pytest tests passing cleanly
- [ ] Docker container builds and `/health` returns `ok`

---

## QUICK REFERENCE — KEY API DETAILS

**Groq STT:**
```
POST https://api.groq.com/openai/v1/audio/transcriptions
model: whisper-large-v3
```

**Groq LLM:**
```
POST https://api.groq.com/openai/v1/chat/completions
model: llama-3.3-70b-versatile
```

**Vapi webhook payload (end-of-call):**
```json
{
  "type": "end-of-call-report",
  "transcript": "full conversation...",
  "call": { "id": "call_abc123" }
}
```

**WhatsApp via Twilio Python:**
```python
client.messages.create(
    from_="whatsapp:+14155238886",
    to="whatsapp:+91XXXXXXXXXX",
    body="Summary text here"
)
```

**Google Calendar create event:**
```
POST https://www.googleapis.com/calendar/v3/calendars/primary/events
```

**LangGraph conditional edge pattern (Python):**
```python
graph.add_conditional_edges(
    "extract",
    should_schedule_meeting,      # function returning a string key
    {
        "notify_with_meeting":   "schedule_meeting",
        "notify_without_meeting": "send_whatsapp",
        "failed":                END,
    }
)
```

**Run locally with ngrok:**
```bash
uvicorn app.main:app --reload --port 8000
ngrok http 8000
# Copy the https URL to Vapi assistant serverUrl
```
