import httpx
from dotenv import set_key

from app.config import settings

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
    # Replace with your ngrok/production URL before running against a real Vapi account
    "serverUrl": "https://YOUR_NGROK_OR_PRODUCTION_URL/webhook/vapi",
    "serverUrlSecret": settings.VAPI_WEBHOOK_SECRET,
}


def main():
    response = httpx.post(
        "https://api.vapi.ai/assistant",
        headers={"Authorization": f"Bearer {settings.VAPI_API_KEY}"},
        json=ASSISTANT_CONFIG,
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
