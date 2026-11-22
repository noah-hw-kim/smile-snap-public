import os

# Inject dummy test env vars before any app module imports server/config.py.
# Setting os.environ directly also prevents pydantic-settings from loading
# real credentials out of server/.env during unit tests.
TEST_ENV = {
    "S3_BUCKET_NAME": "test-bucket",
    "GEMINI_API_KEY": "test-gemini-key",
    "IPINFO_API_TOKEN": "test-ipinfo-token",
    "WEATHER_API_KEY": "test-weather-key",
    "FIREBASE_WEB_API_KEY": "test-firebase-web-key",
    "GCP_SERVICE_ACCOUNT_JSON": "{}",
    "AWS_DEFAULT_REGION": "us-east-1",
    "ENVIRONMENT": "test",
}

for key, value in TEST_ENV.items():
    os.environ[key] = value
