import sys
from pathlib import Path

import httpx
from dotenv import set_key

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.config import settings

WEBHOOK_URL = settings.VAPI_SERVER_URL or "https://YOUR_NGROK_OR_PRODUCTION_URL/webhook/vapi"


def server_config() -> dict:
    config = {"url": WEBHOOK_URL}
    if settings.VAPI_SERVER_CREDENTIAL_ID:
        config["credentialId"] = settings.VAPI_SERVER_CREDENTIAL_ID
    return config

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "check_agent_availability",
            "description": "Check the real estate agent's Google Calendar and return open site-visit slots.",
            "parameters": {
                "type": "object",
                "properties": {
                    "date": {
                        "type": "string",
                        "description": "Requested date in YYYY-MM-DD format when possible.",
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Caller or business timezone. Default to Asia/Kolkata.",
                    },
                    "durationMinutes": {
                        "type": "integer",
                        "description": "Meeting duration in minutes. Default to 30.",
                    },
                },
                "required": ["date"],
            },
        },
        "server": server_config(),
    },
    {
        "type": "function",
        "function": {
            "name": "book_agent_meeting",
            "description": "Book a confirmed property meeting or site visit on the agent's Google Calendar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "callerName": {"type": "string", "description": "Caller name."},
                    "callerPhone": {"type": "string", "description": "Caller phone number if known."},
                    "startTime": {
                        "type": "string",
                        "description": "Confirmed meeting start time as an ISO 8601 datetime.",
                    },
                    "endTime": {
                        "type": "string",
                        "description": "Confirmed meeting end time as an ISO 8601 datetime.",
                    },
                    "durationMinutes": {
                        "type": "integer",
                        "description": "Meeting duration in minutes if endTime is not known.",
                    },
                    "timezone": {
                        "type": "string",
                        "description": "Timezone for startTime/endTime. Default to Asia/Kolkata.",
                    },
                    "propertyInterest": {
                        "type": "string",
                        "description": "Short description of the property or buyer requirement.",
                    },
                },
                "required": ["callerName", "startTime"],
            },
        },
        "server": server_config(),
    },
]


def create_tool(tool_config: dict) -> str:
    response = httpx.post(
        "https://api.vapi.ai/tool",
        headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        json=tool_config,
        timeout=30.0,
    )
    response.raise_for_status()
    tool = response.json()
    print(f"Tool created: {tool_config['function']['name']} -> {tool['id']}")
    return tool["id"]


def build_assistant_config(tool_ids: list[str]) -> dict:
    config = dict(ASSISTANT_CONFIG)
    config["model"] = dict(ASSISTANT_CONFIG["model"])
    config["model"]["toolIds"] = tool_ids
    return config


ASSISTANT_CONFIG = {
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
                    "5. Use check_agent_availability before offering exact site-visit slots\n"
                    "6. Use book_agent_meeting only after the caller confirms a slot\n"
                    "7. Collect their name and confirm their phone number\n"
                    "8. Thank them and let them know the agent will follow up shortly\n\n"
                    "Rules:\n"
                    "- Keep responses short and conversational (1-2 sentences max)\n"
                    "- Never make up property listings or prices\n"
                    "- Never claim a meeting is booked until book_agent_meeting succeeds\n"
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
    "server": server_config(),
    "serverMessages": ["tool-calls", "end-of-call-report", "status-update", "transcript"],
}


def main():
    tool_ids = [create_tool(tool_config) for tool_config in TOOL_DEFINITIONS]
    assistant_config = build_assistant_config(tool_ids)
    response = httpx.post(
        "https://api.vapi.ai/assistant",
        headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        json=assistant_config,
        timeout=30.0,
    )
    response.raise_for_status()
    assistant = response.json()
    assistant_id = assistant["id"]
    print(f"Assistant created: {assistant_id}")

    set_key(".env", "VAPI_ASSISTANT_ID", assistant_id)
    print("Saved VAPI_ASSISTANT_ID to .env")


if __name__ == "__main__":
    main()
