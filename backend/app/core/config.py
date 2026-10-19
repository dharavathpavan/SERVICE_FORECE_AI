from typing import List, Union
from pydantic import AnyHttpUrl, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    PROJECT_NAME: str = "ServiceForce.ai"
    VERSION: str = "1.0.0"
    API_V1_STR: str = "/api/v1"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    DEMO_MODE: bool = True

    # Security
    SECRET_KEY: str = "serviceforce_super_secret_jwt_key_change_in_production_9988776655"
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 60 * 24 * 7  # 7 days

    # Database: SQLite fallback for instant zero-config run, PostgreSQL + pgvector for production
    DATABASE_URL: str = "sqlite:///./serviceforce.db"

    # AI & Speech Providers
    GEMINI_API_KEY: str = ""
    GEMINI_MODEL: str = "gemini-2.5-flash"
    EMBEDDING_MODEL: str = "text-embedding-004"

    # Telephony & Asterisk / SIP
    ASTERISK_HOST: str = "localhost"
    ASTERISK_PORT: int = 5060
    ASTERISK_AMI_PORT: int = 5038
    ASTERISK_AMI_USER: str = "admin"
    ASTERISK_AMI_SECRET: str = "amp111"
    # ARI (Asterisk REST Interface) - used by the live Asterisk adapter
    ASTERISK_ARI_PORT: int = 8088
    ASTERISK_ARI_USER: str = "serviceforce"
    ASTERISK_ARI_SECRET: str = "change_me_ari_secret"
    ASTERISK_APP: str = "serviceforce"
    # External media target for the audio bridge (AudioSocket)
    ASTERISK_MEDIA_HOST: str = "127.0.0.1"
    ASTERISK_MEDIA_PORT: int = 9099
    # Public WebSocket URL the voice session connects to
    VOICE_BRIDGE_URL: str = "ws://localhost:8000/api/v1/voice/stream"
    TELEPHONY_PROVIDER: str = "mock"  # "mock", "asterisk", "sip_gateway"

    # Voice / real-time speech provider
    VOICE_PROVIDER: str = "mock"  # "mock", "gemini_live"
    GEMINI_LIVE_MODEL: str = "gemini-2.0-flash-exp"
    VOICE_INPUT_SAMPLE_RATE: int = 16000
    VOICE_OUTPUT_SAMPLE_RATE: int = 24000
    # Mock provider speech engine: "auto" (Windows system voice when available,
    # else synthetic tones), "system", or "tones".
    VOICE_MOCK_TTS: str = "auto"

    # Object storage (recordings, uploaded documents)
    STORAGE_BACKEND: str = "local"  # "local", "s3"
    STORAGE_LOCAL_PATH: str = "./storage"
    S3_BUCKET: str = ""
    S3_PREFIX: str = "serviceforce"
    S3_REGION: str = "us-east-1"
    S3_ENDPOINT_URL: str = ""

    # Background workers
    WORKER_MODE: str = "inline"  # "inline" or "celery"

    # CORS
    # Explicit dev origins, plus a localhost regex: `flutter run -d chrome` and
    # `python -m http.server` both pick arbitrary ports, so pinning ports alone
    # silently breaks the browser client. In production, list your exact origin
    # in BACKEND_CORS_ORIGINS and clear BACKEND_CORS_ORIGIN_REGEX.
    BACKEND_CORS_ORIGINS: List[str] = [
        "http://localhost:3000",
        "http://localhost:4200",
        "http://localhost:5173",
        "http://localhost:8000",
        "http://localhost:8080",
        "http://127.0.0.1:3000",
        "http://127.0.0.1:4200",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:8000",
        "http://127.0.0.1:8080",
    ]
    BACKEND_CORS_ORIGIN_REGEX: str = r"^http://(localhost|127\.0\.0\.1)(:\d+)?$"

    # Outbound calling constraints
    DEFAULT_CALLING_HOURS_START: str = "09:00"
    DEFAULT_CALLING_HOURS_END: str = "20:00"
    MAX_CAMPAIGN_CONCURRENCY: int = 10

    # Webhook signature secret
    WEBHOOK_SIGNING_SECRET: str = "whsec_serviceforce_default_secret_key_12345"
    WEBHOOK_REQUIRE_SIGNATURE: bool = False  # set true in production

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore",
    )


settings = Settings()
