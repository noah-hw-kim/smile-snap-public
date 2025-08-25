import os
from fastapi import FastAPI, HTTPException
import requests
from google.cloud import storage
from services.location_service import get_location_from_ip
from services.weather_service import get_weather_from_coordinates

PROJECT_ID = os.getenv("GCP_PROJECT_ID")
BUCKET_NAME = os.getenv("BUCKET_NAME")
EXTERNAL_IP_SERVICE = "https://httpbin.org/ip"

app = FastAPI()
@app.get("/test-location")
def test_location(ip: str = None):
    """Test location service with optional IP parameter"""
    try:
        if ip:
            # Test with provided IP (simulates production user)
            test_ip = ip
            location = get_location_from_ip(test_ip)
            scenario = "Custom IP provided"
        else:
            # Test with server's public IP (simulates local development fallback)
            response = requests.get(EXTERNAL_IP_SERVICE, timeout=5)
            test_ip = response.json().get("origin")
            location = get_location_from_ip(test_ip)
            scenario = "Server's public IP (local development simulation)"
        
        return {
            "test_ip": test_ip,
            "scenario": scenario,
            "location_data": location,
            "status": "success",
            "note": "Use ?ip=X.X.X.X to test production user scenarios"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
        
@app.get("/test-weather")
def test_weather(lat: float, lon: float):
    """Test weather service with lat and lon"""
    # Validate coordinate ranges
    if not (-90 <= lat <= 90):
        raise HTTPException(status_code=400, detail="Latitude must be between -90 and 90")
    if not (-180 <= lon <= 180):
        raise HTTPException(status_code=400, detail="Longitude must be between -180 and 180")
    
    try:
        response = get_weather_from_coordinates(lat, lon)
        return {
            "coordinates": {"lat": lat, "lon": lon},
            "weather_data": response,
            "status": "success"
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/test-upload")
def upload_test_file():
    """Uploads a simple test file to Google Cloud Storage."""
    if not BUCKET_NAME:
        raise HTTPException(status_code=500, detail="BUCKET_NAME environment variable not set")

    try:
        storage_client = storage.Client(project = PROJECT_ID)
        bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob("test-upload.txt") # The name of the file in the bucket

        blob.upload_from_string("This is a test file from FastAPI!")

        return {"message": "File uploaded successfully.", "file_url": blob.public_url}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))