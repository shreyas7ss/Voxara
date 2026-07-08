from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    GROQ_API_KEY: str = ""
    VAPI_API_KEY: str = ""
    VAPI_PHONE_NUMBER_ID: str = ""
    VAPI_ASSISTANT_ID: str = ""
    VAPI_WEBHOOK_SECRET: str = ""
    TWILIO_ACCOUNT_SID: str = ""
    TWILIO_AUTH_TOKEN: str = ""
    WHATSAPP_FROM_NUMBER: str = "whatsapp:+14155238886"
    AGENT_WHATSAPP_NUMBER: str = ""
    GOOGLE_CLIENT_ID: str = ""
    GOOGLE_CLIENT_SECRET: str = ""
    GOOGLE_REDIRECT_URI: str = "http://localhost:8000/auth/google/callback"
    GOOGLE_REFRESH_TOKEN: str = ""
    PORT: int = 8000
    ENV: str = "development"

    # Phase 9 — listings extension
    DATABASE_URL: str = "sqlite:///./voxara.db"
    S3_ENDPOINT_URL: str = ""
    S3_ACCESS_KEY_ID: str = ""
    S3_SECRET_ACCESS_KEY: str = ""
    S3_BUCKET_NAME: str = ""
    S3_REGION: str = "us-east-1"
    S3_PUBLIC_BASE_URL: str = ""
    TWILIO_LISTING_TEMPLATE_SID: str = ""
    MAX_LISTINGS_PER_MATCH: int = 3
    LISTING_MATCH_MIN_SCORE: int = 40


settings = Settings()
