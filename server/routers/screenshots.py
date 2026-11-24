import logging
import traceback
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, photo_helper
from dependencies import get_accessible_photo, get_current_user, verify_ownership_or_admin
from models import Photo
from services.api_services import generate_diary_entry, get_contextual_data, upload_image_to_s3
from services.db_services import (
    create_diary_entry_service,
    delete_photo_service,
    get_photo_by_id,
    list_photos_service,
    save_photo_metadata_service,
)

logger = logging.getLogger(__name__)

router = APIRouter(
    prefix="/screenshots",
    tags=["Screenshots"],
)


@router.get("/user/{userId}", response_description="Get all photos for a specific user", response_model=List[Photo])
async def get_user_photos(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """Get all photos for a specific user (requires ownership or admin access)."""
    return await list_photos_service(db, user_id=userId)


@router.post("/upload", description="Uploads a screenshot and saves its metadata.")
async def upload_screenshot(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles only the image upload and creates a 'photo' record in the database.
    Uses the authenticated user's ID automatically.
    """
    try:
        userId = current_user["userId"]
        file_path = await upload_image_to_s3(userId, image)
        photo_metadata = await save_photo_metadata_service(db, userId, file_path)

        return {
            "photoId": photo_metadata["photoId"],
            "photoUrl": photo_metadata["photoUrl"],
        }
    except Exception as e:
        logger.error("=== UPLOAD FAILED ===")
        logger.error(f"Error: {str(e)}")
        logger.error(f"Error type: {type(e)}")
        logger.error(f"Traceback: {traceback.format_exc()}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/{photoId}", response_description="Get a specific photo", response_model=Photo)
async def get_photo(
    photo_doc=Depends(get_accessible_photo),
):
    """Get a specific photo (user can access own photos, admin can access any photo)."""
    return photo_helper(photo_doc)


@router.delete("/{photoId}", description="Deletes a specific uploaded screenshot")
async def delete_photo(
    photoId: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    userId = current_user["userId"]
    try:
        success = await delete_photo_service(db, userId, photoId)
        if success:
            return Response(status_code=status.HTTP_204_NO_CONTENT)
        raise HTTPException(status_code=404, detail=f"Photo {photoId} not found")
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete photo {photoId} for user {current_user['userId']}: {str(e)}")
        raise HTTPException(status_code=500, detail="Failed to delete photo")


@router.post("/{photoId}/generate", description="Generates a diary entry for a previously uploaded screenshot.")
async def generate_from_screenshot(
    photoId: str,
    request: Request,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Takes a photoId, finds the image, gets context, generates the diary,
    and saves the final entry.
    """
    userId = current_user["userId"]
    logger.info(f"Generating diary entry for photo {photoId} by user {userId}")

    try:
        photo_doc = await get_photo_by_id(db, photoId, userId)
        print("photo_doc completed")

        context = await get_contextual_data(request)
        print("context completed")

        diary_content = await generate_diary_entry(photo_doc.file_path, context["location"], context["weather"])
        print("diary_countent completed")

        entry_to_create = {
            "content": diary_content,
            "filePath": photo_doc.file_path,
            "location": context.get("location"),
            "weather": context.get("weather"),
        }
        diary_entry = await create_diary_entry_service(db, userId, entry_to_create)
        print("create_diary_entry_service completed")

        return {
            "status": "success",
            "diary_entry": diary_entry,
            "photo_id": photoId,
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
