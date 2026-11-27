import logging
import time
from typing import List

from fastapi import APIRouter, Depends, File, HTTPException, Request, Response, UploadFile, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, photo_helper
from dependencies import get_accessible_photo, get_current_user, verify_ownership_or_admin
from models import GenerateDiaryResponse, Photo, PhotoUploadResponse
from services.api_services import generate_diary_entry, get_contextual_data, upload_image_to_s3
from services.cache_services import check_rate_limit
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


@router.post("/upload", description="Uploads a screenshot and saves its metadata.", response_model=PhotoUploadResponse)
async def upload_screenshot(
    image: UploadFile = File(...),
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Handles only the image upload and creates a 'photo' record in the database.
    Uses the authenticated user's ID automatically.
    """
    userId = current_user["userId"]
    allowed, retry_after = await check_rate_limit(
        f"smilesnap:rl:upload:{userId}",
        limit=settings.UPLOAD_RATE_LIMIT,
        window_seconds=settings.UPLOAD_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for photo uploads. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    try:
        file_path = await upload_image_to_s3(userId, image)
        photo_metadata = await save_photo_metadata_service(db, userId, file_path)

        return {
            "photoId": photo_metadata["photoId"],
            "photoUrl": photo_metadata["photoUrl"],
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Upload failed for user %s", current_user["userId"])
        raise HTTPException(status_code=500, detail="Failed to upload screenshot")


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
        logger.error("Failed to delete photo %s for user %s: %s", photoId, userId, e)
        raise HTTPException(status_code=500, detail="Failed to delete photo")


@router.post(
    "/{photoId}/generate",
    description="Generates a diary entry for a previously uploaded screenshot.",
    response_model=GenerateDiaryResponse,
)
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

    allowed, retry_after = await check_rate_limit(
        f"smilesnap:rl:generate:{userId}",
        limit=settings.GENERATE_RATE_LIMIT,
        window_seconds=settings.GENERATE_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Rate limit exceeded for diary generation. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    logger.info("Generating diary entry for photo %s by user %s", photoId, userId)
    request_start = time.perf_counter()

    try:
        photo_doc = await get_photo_by_id(db, photoId, userId)
        context = await get_contextual_data(request)
        diary_content = await generate_diary_entry(photo_doc.file_path, context["location"], context["weather"])

        entry_to_create = {
            "content": diary_content,
            "filePath": photo_doc.file_path,
            "location": context.get("location"),
            "weather": context.get("weather"),
        }
        diary_entry = await create_diary_entry_service(db, userId, entry_to_create)
        logger.info(
            "Diary generate request completed photo_id=%s duration_ms=%.1f",
            photoId,
            (time.perf_counter() - request_start) * 1000,
        )

        return {
            "status": "success",
            "diary_entry": diary_entry,
            "photo_id": photoId,
        }
    except HTTPException:
        raise
    except Exception:
        logger.exception("Failed to generate diary entry for photo %s", photoId)
        raise HTTPException(status_code=500, detail="Failed to generate diary entry")
