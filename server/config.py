import os
from dotenv import load_dotenv
import ipinfo
from google import genai
import motor.motor_asyncio
from google.cloud import storage

# Load environment variables from .env file once
load_dotenv()

# --- Cloud & API Keys ---
MONGO_DETAILS = os.getenv("MONGO_DETAILS", "mongodb://localhost:27017")
BUCKET_NAME = os.getenv("BUCKET_NAME")
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")
IPINFO_API_TOKEN = os.getenv("IPINFO_API_TOKEN")
WEATHER_API_KEY = os.getenv("WEATHER_API_KEY")
PROJECT_ID = os.getenv("GCP_PROJECT_ID")
FIREBASE_WEB_API_KEY = os.getenv("FIREBASE_WEB_API_KEY")

# --- Derived Variables ---
BASE_GCS_URL = f"https://storage.googleapis.com/{BUCKET_NAME}"
EXTERNAL_IP_SERVICE = "https://httpbin.org/ip"
FIREBASE_SIGN_IN_URL = f"https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key={FIREBASE_WEB_API_KEY}"
OPENWEATHER_API_URL = "https://api.openweathermap.org/data/2.5/weather"

# --- API Client Initializations ---

# MongoDB Client
mongo_client = motor.motor_asyncio.AsyncIOMotorClient(MONGO_DETAILS)
database = mongo_client.smile_snap

# Google GenAI Client
if not GEMINI_API_KEY:
    raise ValueError("GEMINI_API_KEY not found. Make sure to set it in your .env file.")
gemini_client = genai.Client(api_key=GEMINI_API_KEY)

# Google Cloud Storage Client
storage_client = storage.Client(project=PROJECT_ID)
bucket = storage_client.bucket(BUCKET_NAME)

# Initialize IPinfo
ipinfo_handler = ipinfo.getHandler(access_token=IPINFO_API_TOKEN)

"""Simple validation for required environment variables"""
required_vars = {
    'MONGO_DETAILS': MONGO_DETAILS,
    'BUCKET_NAME': BUCKET_NAME,
    'GEMINI_API_KEY': GEMINI_API_KEY,
    'FIREBASE_WEB_API_KEY': FIREBASE_WEB_API_KEY,
    'PROJECT_ID': PROJECT_ID
}

missing_vars = [name for name, value in required_vars.items() if not value]

if missing_vars:
    raise ValueError(f"Missing required environment variables: {', '.join(missing_vars)}")

print("✅ All required environment variables are set")

