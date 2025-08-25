from config import database, bucket
from google.cloud import storage
from datetime import timedelta, datetime
import logging

logger = logging.getLogger(__name__)

# This is our collection
diary_collection = database.get_collection("diary_entries")
user_collection = database.get_collection("users")
photo_collection = database.get_collection("photos")

# Helper to convert MongoDB's ObjectId to a string
def diary_entry_helper(entry) -> dict:
    file_path = entry.get("filePath")
    image_url = None

    if file_path:
        try:
            # logger.info(f"Attempting to generate signed URL for: {file_path}")
            # logger.info(f"Bucket: {bucket.name}")

            blob = bucket.blob(file_path)
            image_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="GET",
            )
        except Exception as e:
            logger.error(f"FAILED to generate signed URL: {str(e)}")
            logger.error(f"Error type: {type(e).__name__}")
            image_url = None
    
    return {
        "entryId": entry["entryId"],
        "userId": entry["userId"],
        "content": entry["content"],
        "imageUrl": image_url,
        "location": entry["location"],
        "weather": entry["weather"],
        "mode": entry.get("mode", "auto"),
        "createdAt": entry.get("createdAt").isoformat() if entry.get("createdAt") else None,
        "editedAt": entry.get("editedAt").isoformat() if entry.get("editedAt") else None
    }

def user_helper(user) -> dict:
    return {
        "userId": user["userId"],
        "email": user["email"],
        "displayName": user.get("displayName"),
        "createdAt": user.get("createdAt").isoformat() if user.get("createdAt") else None,
        "role": user["role"]
    }

def photo_helper(photo) -> dict:
    # Safely get the file path.
    file_path = photo.get("filePath")
    photo_url = None

    if file_path:
        try:
            blob = bucket.blob(file_path)
            photo_url = blob.generate_signed_url(
                version="v4",
                expiration=timedelta(minutes=15),
                method="GET",
            )
            # print(f"Generated signed URL: {photo_url}")  # Add this debug line
        except Exception as e:
            print(f"Error generating signed URL: {e}")  # Add this debug line
            photo_url = None
    
    return {
        "userId": photo.get("userId"),
        "photoId": photo.get("photoId"),
        "filePath": file_path,
        "photoUrl": photo_url,
        "createdAt": photo["createdAt"].isoformat() if photo.get("createdAt") else None
    }