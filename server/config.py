import logging

from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict
import ipinfo
from google import genai
import boto3

logger = logging.getLogger(__name__)


# ── Settings ──────────────────────────────────────────────────────────────────
# Pydantic reads from the .env file and validates types automatically.
# Any required field that is missing will raise a clear error at startup
# instead of silently returning None deep inside a request.
class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Database
    DATABASE_URL: str

    S3_BUCKET_NAME: str

    # External APIs
    GEMINI_API_KEY: str
    IPINFO_API_TOKEN: str = Field(default="")
    WEATHER_API_KEY: str = Field(default="")
    FIREBASE_WEB_API_KEY: str

    # Firebase — explicit service account for non-GCP environments (Lambda)
    GCP_SERVICE_ACCOUNT_JSON: str

    # App
    ENVIRONMENT: str = Field(default="production")

    # Redis (optional — leave blank to disable caching and rate limiting)
    REDIS_URL: str = Field(default="")
    GENERATE_RATE_LIMIT: int = Field(default=10, ge=1)
    GENERATE_RATE_WINDOW_SECONDS: int = Field(default=3600, ge=1)
    SIGNUP_RATE_LIMIT: int = Field(default=5, ge=1)
    SIGNUP_RATE_WINDOW_SECONDS: int = Field(default=3600, ge=1)
    LOGIN_RATE_LIMIT: int = Field(default=10, ge=1)
    LOGIN_RATE_WINDOW_SECONDS: int = Field(default=900, ge=1)
    UPLOAD_RATE_LIMIT: int = Field(default=10, ge=1)
    UPLOAD_RATE_WINDOW_SECONDS: int = Field(default=3600, ge=1)
    MAX_UPLOAD_BYTES: int = Field(default=10 * 1024 * 1024, ge=1)


settings = Settings()

# ── Derived constants ──────────────────────────────────────────────────────────
# Keep these as module-level names so no other file needs to change.
S3_BUCKET_NAME = settings.S3_BUCKET_NAME
GEMINI_API_KEY = settings.GEMINI_API_KEY
IPINFO_API_TOKEN = settings.IPINFO_API_TOKEN
WEATHER_API_KEY = settings.WEATHER_API_KEY
FIREBASE_WEB_API_KEY = settings.FIREBASE_WEB_API_KEY

EXTERNAL_IP_SERVICE = "https://httpbin.org/ip"
FIREBASE_SIGN_IN_URL = (
    f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword"
    f"?key={FIREBASE_WEB_API_KEY}"
)
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# ── API client initializations ─────────────────────────────────────────────────
# Clients are created once at startup and shared across the app.

gemini_client = genai.Client(api_key=GEMINI_API_KEY)

ipinfo_handler = ipinfo.getHandler(access_token=IPINFO_API_TOKEN) if IPINFO_API_TOKEN else None

# S3 client — on Lambda, credentials come from the IAM execution role automatically.
# Locally, boto3 reads from ~/.aws/credentials (set by `aws configure`).
# No keys in code — same principle as ADC, but for AWS.
s3_client = boto3.client("s3")

logger.info("All required environment variables loaded and validated")
