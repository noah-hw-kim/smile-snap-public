from fastapi import APIRouter, File, UploadFile, Form, Request, HTTPException, Depends, Response, status
from services.api_services import upload_image_to_gcs, get_contextual_data, generate_diary_entry
from services.db_services import create_diary_entry_service, save_photo_metadata_service, delete_photo_service, get_photo_by_id
from dependencies import get_accessible_photo, verify_ownership_or_admin, get_current_user
from database import photo_collection, photo_helper
from models import Photo
from typing import List
import logging
from .websockets import manager

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/screenshots",
    tags=["Screenshots"]
)
    
@router.get("/user/{userId}", response_description="Get all photos for a specific user (Admin only)", response_model=List[Photo])
async def get_user_photos(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    """Get all photos for a specific user (requires ownership or admin access)"""
    # print("passed authorization part")
    
    photos = []
    async for photo in photo_collection.find({"userId": userId}):
        photos.append(photo_helper(photo))
    
    # print("photos: ", photos)

    return photos

@router.post("/upload", description="Uploads a screenshot and saves its metadata.")
async def upload_screenshot(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """
    Handles only the image upload and creates a 'photo' record in the database.
    Uses the authenticated user's ID automatically.
    """
    try:
        # logger.info(f"=== UPLOAD START ===")
        # logger.info(f"User ID: {current_user['userId']}")
        # logger.info(f"Image filename: {image.filename}")
        # logger.info(f"BUCKET_NAME: {os.getenv('BUCKET_NAME')}")
        # logger.info(f"PROJECT_ID from env: {os.getenv('GCP_PROJECT_ID')}")
        # logger.info(f"BASE_GCS_URL: {BASE_GCS_URL}")
        
        userId = current_user["userId"]
        
        # logger.info("Calling upload_image_to_gcs...")
        file_path = await upload_image_to_gcs(userId, image)
        # logger.info(f"upload_image_to_gcs returned: {file_path}")
        
        # logger.info("Calling save_photo_metadata_service...")
        photo_metadata = await save_photo_metadata_service(userId, file_path)
        # logger.info(f"save_photo_metadata_service returned: {photo_metadata}")
        
        # logger.info(f"Final photoUrl: {photo_metadata.get('photoUrl', 'NOT_SET')}")
        # logger.info(f"=== UPLOAD SUCCESS ===")
        
        message = {"type": "photo_created", "data": photo_metadata}
        await manager.send_to_user(message, userId)
        await manager.broadcast_to_admins(message)
        
        return {
            "photoId": photo_metadata["photoId"],
            "photoUrl": photo_metadata["photoUrl"]
        }
    except Exception as e:
        logger.error(f"=== UPLOAD FAILED ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))

# Get specific photo by ID
@router.get("/{photoId}", response_description="Get a specific photo", response_model=Photo)
async def get_photo(
    photo_doc: dict = Depends(get_accessible_photo)
):
    """Get a specific photo (user can access own photos, admin can access any photo)"""
    return photo_helper(photo_doc)

# ADD THIS ENDPOINT to delete a specific photo
@router.delete("/{photoId}", description="Deletes a specific uploaded screenshot")
async def delete_photo(
    photoId: str,
    current_user: dict = Depends(get_current_user)
):
    userId = current_user["userId"]
    success = await delete_photo_service(userId, photoId)
    try:
        if success:
            message = {"type": "photo_deleted", "data": {"photoId": photoId, "userId": userId}}
            await manager.send_to_user(message, userId)
            await manager.broadcast_to_admins(message)
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        raise HTTPException(status_code=404, detail=f"Photo {photoId} not found")
    except Exception as e:
        logger.error(f"Failed to delete photo {photoId} for user {current_user['userId']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete photo")

@router.post("/{photoId}/generate", description="Generates a diary entry for a previously uploaded screenshot.")
async def generate_from_screenshot(
    photoId: str,
    request: Request,
    current_user: dict = Depends(get_current_user)
):
    """
    Takes a photoId, finds the image, gets context, generates the diary,
    and saves the final entry.
    """
    userId = current_user["userId"]
    logger.info(f"Generating diary entry for photo {photoId} by user {userId}")

    try:
        photo_doc = await get_photo_by_id(photoId, userId)
        print("photo_doc completed")

        context = await get_contextual_data(request)
        print("context completed")

        diary_content = await generate_diary_entry(photo_doc["filePath"], context["location"], context["weather"])
        print("diary_countent completed")

        
        entry_to_create = {
            "content": diary_content,
            "filePath": photo_doc["filePath"],
            "location": context.get('location'),
            "weather": context.get('weather')
        }
        diary_entry = await create_diary_entry_service(userId, entry_to_create)
        print("create_diary_entry_service completed")

        message = {"type": "entry_created", "data": diary_entry}
        await manager.send_to_user(message, userId)
        await manager.broadcast_to_admins(message)
        
        return {
            "status": "success",
            "diary_entry": diary_entry,
            "photo_id": photoId
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
