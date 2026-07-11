from twilio.request_validator import RequestValidator

from app.config import settings


def validate_twilio_signature(url: str, form: dict, signature: str) -> bool:
    validator = RequestValidator(settings.TWILIO_AUTH_TOKEN)
    return validator.validate(url, form, signature or "")
