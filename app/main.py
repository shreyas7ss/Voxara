from fastapi import BackgroundTasks, FastAPI, HTTPException, Header, Request
from fastapi.responses import JSONResponse, RedirectResponse, Response
from typing import Optional
from datetime import datetime

from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

from app.services.vapi_service import VapiWebhookPayload, handle_vapi_webhook
from app.services.whatsapp_webhook_service import handle_inbound_whatsapp
from app.services import calendar_service
from app.utils.logger import logger
from app.utils.validators import validate_twilio_signature
from app.config import settings

app = FastAPI(title="Voxara", version="1.0.0")

limiter = Limiter(key_func=get_remote_address)
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)


@app.post("/webhook/vapi")
@limiter.limit("100/minute")
async def vapi_webhook(
    request: Request,
    payload: VapiWebhookPayload,
    x_vapi_secret: Optional[str] = Header(None)
):
    if x_vapi_secret != settings.VAPI_WEBHOOK_SECRET:
        raise HTTPException(status_code=401, detail="Unauthorized")
    result = await handle_vapi_webhook(payload)
    return {"received": True, **result}


@app.post("/webhook/whatsapp/inbound")
@limiter.limit("20/minute")
async def whatsapp_inbound_webhook(request: Request, background_tasks: BackgroundTasks):
    form = dict(await request.form())

    signature = request.headers.get("X-Twilio-Signature", "")
    if not validate_twilio_signature(str(request.url), form, signature):
        raise HTTPException(status_code=403, detail="Invalid Twilio signature")

    background_tasks.add_task(handle_inbound_whatsapp, form)
    return Response(content="<Response></Response>", media_type="application/xml")


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
