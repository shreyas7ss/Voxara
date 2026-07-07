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
