import asyncio
import requests
from fastapi import Request, UploadFile, HTTPException
import uuid
from config import OPENWEATHER_API_URL, ipinfo_handler, WEATHER_API_KEY, EXTERNAL_IP_SERVICE, gemini_client, BUCKET_NAME, bucket
from PIL import Image
from io import BytesIO

def get_client_ip(request: Request) -> str:
    """
    Get the most reliable client IP address from request
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: Client IP address
    """
    forwarded_for = request.headers.get("x-forwarded-for")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    
    real_ip = request.headers.get("x-real-ip") 
    if real_ip:
        return real_ip
        
    return request.client.host

def get_api_ready_ip(request: Request) -> str:
    """
    Get IP address suitable for external API calls
    Falls back to public IP for local testing
    
    Args:
        request: FastAPI Request object
        
    Returns:
        str: IP address suitable for external APIs
    """
    actual_ip = get_client_ip(request)
    
    # For local testing, get your public IP
    if actual_ip in ["127.0.0.1", "::1"] or actual_ip.startswith(("192.168.", "10.", "172.")):
        try:
            # Fallback to your public IP for testing external APIs
            response = requests.get(EXTERNAL_IP_SERVICE, timeout=5)
            public_ip = response.json().get("origin")
            return public_ip
        except:
            # If that fails, return the local IP anyway
            return actual_ip
    
    return actual_ip

def get_weather_from_coordinates(lat, lon):
    # Parameters for the API request
    params = {
        "lat": lat,
        "lon": lon,
        "appid": WEATHER_API_KEY,
        "units": "metric"  # Use Celsius, change to "imperial" for Fahrenheit
    }
    try:
        # Make the API request
        response = requests.get(OPENWEATHER_API_URL, params=params, timeout=10)
        response.raise_for_status()  # Raise an exception for bad status codes
        
        weather_data = response.json()
        
        # Extract useful information
        return {
            "weather": weather_data["weather"][0]["description"],
            "temperature": weather_data["main"]["temp"],
            "city": weather_data.get("name", "Unknown"),
            "country": weather_data["sys"]["country"]
            # "raw_data": weather_data  # Include full response for debugging
        }
        
    except Exception as e:
        print(f"Weather API error: {e}")
        return {}

async def generate_diary_entry(file_path: str, location_data: dict = None, weather_data: dict = None) -> str:
    """
    Generate a diary entry based on a screenshot image URL and context data.
    """
    # The full prompt with a persona, rules, and examples

    new_prompt = """
    You are my personal diary scribe, with a talent for witty, observational humor. Your job is to look at a screenshot of a moment I was happy, consider the context of where I was, and write a diary entry.

    **CONTEXT:**
    - Location: {location_str}
    - Weather: {weather_str}

    **TASK:**
    Write a short, clever, one-paragraph diary entry about the moment captured in the attached screenshot.

    **STRICT RULES:**
    1.  **DO NOT mention the city, state, or country by name.** Instead, subtly hint at the location by referencing a local stereotype, landmark, food, or general vibe.
    2.  The tone should be warm, personal, and genuinely funny, like an inside joke. Avoid cheesy or generic humor.
    3.  Directly reference what you see in the screenshot.
    4.  Keep it concise (2-3 sentences).
    5.  End with a fitting emoji.
    6.  Please ignore the smiling capturing program. Focus on the other parts to create the contents.
    ---
    **EXAMPLES:**

    **Example 1:**
    - CONTEXT: San Francisco, foggy. Screenshot shows code on a laptop.
    - DIARY ENTRY: Finally cracked that impossible bug, feeling like a genius. For a moment there, the fog outside had nothing on the fog in my brain. Guess that's what a billion-dollar idea feels like, right before you forget to save. 💻

    **Example 2:**
    - CONTEXT: A beach town in San Diego, sunny. Screenshot shows a video of someone surfing.
    - DIARY ENTRY: Smiled so hard watching that perfect wave. Pretty sure my only job today is to decide which taco shop to hit up later, and I'm totally okay with that. 🤙
    ---

    **YOUR TURN:**
    Based on the provided context and the attached screenshot, write your diary entry.
    """
    try:
        blob = bucket.blob(file_path)
        img_bytes = await asyncio.to_thread(blob.download_as_bytes)
        
        img = Image.open(BytesIO(img_bytes))

        # 2. Build cleaner context strings
        location_str = "Not available"
        if location_data and location_data.get('city'):
            location_str = f"{location_data['city']}, {location_data.get('region', '')}"

        weather_str = "Not available"
        if weather_data and weather_data.get('description'):
            weather_str = f"{weather_data['description']}, {weather_data.get('temperature')}°F"
        
        # 3. Format the new, smarter prompt
        full_prompt = new_prompt.format(location_str=location_str, weather_str=weather_str)
        
        # 4. Initialize the model and generate content
        response = gemini_client.models.generate_content(
            model='gemini-2.5-flash',
            contents=[
                # types.Part.from_bytes(
                #     data=img_bytes,
                #     mime_type='image/png',
                # ),
                img,
                full_prompt
            ]
        )
        
        return response.text.strip()
        
    except Exception as e:
        print(f"Error generating diary entry: {e}")
        return "Captured a beautiful smile today! 😊"

def get_location_from_ip(ip_address):
    try:
        if not ip_address:
            return None
        details = ipinfo_handler.getDetails(ip_address)
        return details.all
    
    except Exception as e:
        print(f"Error getting location for IP {ip_address}: {e}")
        return None

# 1. Get IP and location information
async def get_contextual_data(request: Request) -> dict:
    ip_info = get_api_ready_ip(request)
    # print("ip: ", ip_info)
    location_raw = get_location_from_ip(ip_info)
    # Only keep city, region, country, lat, lon
    location_data = {
        "city": location_raw.get("city") if location_raw else None,
        "region": location_raw.get("region") if location_raw else None,
        "country": location_raw.get("country") if location_raw else None,
        "lat": location_raw.get("latitude") if location_raw else None,
        "lon": location_raw.get("longitude") if location_raw else None
    }

    # 2. Get weather data if lat/lon available
    weather_data = {"weather": None, "temperature": None}
    if location_data["lat"] and location_data["lon"]:
        raw_weather = get_weather_from_coordinates(location_data["lat"], location_data["lon"])
        # Only keep weather and temperature
        if raw_weather:
            weather_data = {
                "weather": raw_weather.get("weather"),
                "temperature": raw_weather.get("temperature")
            }

    return {"location": location_data, "weather": weather_data}

# 3. Upload image to Google Cloud Storage
async def upload_image_to_gcs(userId: str, image: UploadFile) -> str:
    if not BUCKET_NAME:
        raise HTTPException(status_code=500, detail="BUCKET_NAME environment variable not set")

    # Generate unique filename
    # --- Your existing GCS upload logic ---
    unique_filename = f"screenshots/{userId}/{uuid.uuid4()}.png"
    
    try:
        # storage_client = storage.Client(project=PROJECT_ID)
        # bucket = storage_client.bucket(BUCKET_NAME)
        blob = bucket.blob(unique_filename)
        
        content = await image.read()
        blob.upload_from_string(content, content_type=image.content_type)
        
        # Return the full GCS URL for consistency
        return unique_filename
    
    except Exception as e:
        print(f"Error uploading to GCS: {e}")
        raise HTTPException(status_code=500, detail="Failed to upload image")
