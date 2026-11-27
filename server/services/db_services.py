import asyncio
from datetime import datetime, timezone
import logging
from typing import Optional
import uuid

from fastapi import HTTPException
from firebase_admin import auth
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from config import s3_client, settings
from database import diary_entry_helper, photo_helper, user_helper
from db_models import DiaryEntryModel, PhotoModel, UserModel

logger = logging.getLogger(__name__)


# === User Services ===
async def create_user_services(db: AsyncSession, user_data: dict) -> dict:
    """Create a user in Firebase Auth and persist their profile in Postgres."""
    try:
        new_firebase_user = await asyncio.to_thread(
            auth.create_user,
            email=user_data["email"],
            password=user_data["password"],
            display_name=user_data.get("displayName"),
        )

        user_profile = UserModel(
            user_id=new_firebase_user.uid,
            email=user_data["email"],
            display_name=user_data.get("displayName"),
            role="user",  # Enforce lowest-privilege role regardless of caller payload
            created_at=datetime.now(timezone.utc),
        )

        db.add(user_profile)
        await db.commit()
        return user_helper(user_profile)

    except auth.EmailAlreadyExistsError:
        raise HTTPException(
            status_code=400,
            detail=f"User with email {user_data['email']} already exists.",
        )
    except Exception:
        await db.rollback()
        logger.exception("Error occurred during user creation")
        raise HTTPException(
            status_code=500,
            detail="Failed to create user",
        )


async def get_user_by_id(db: AsyncSession, user_id: str) -> Optional[UserModel]:
    """Fetch a user ORM record by Firebase user_id."""
    return await db.get(UserModel, user_id)


async def get_user_by_email(db: AsyncSession, email: str) -> Optional[UserModel]:
    """Fetch a user ORM record by email address."""
    result = await db.execute(select(UserModel).where(UserModel.email == email))
    return result.scalar_one_or_none()


async def list_users_service(db: AsyncSession, role: Optional[str] = None) -> list[dict]:
    """List users ordered newest-first, optionally filtered by role."""
    stmt = select(UserModel).order_by(UserModel.created_at.desc())
    if role is not None:
        stmt = stmt.where(UserModel.role == role)
    result = await db.execute(stmt)
    return [user_helper(user) for user in result.scalars().all()]


async def update_user_service(db: AsyncSession, userId: str, user_data: dict) -> dict:
    """Update allowed profile fields for a user in Postgres."""
    user = await db.get(UserModel, userId)
    if not user:
        raise HTTPException(status_code=404, detail=f"User {userId} not found")

    if "displayName" in user_data:
        user.display_name = user_data["displayName"]

    if user_data:
        await db.commit()

    return user_helper(user)


async def delete_user_service(db: AsyncSession, userId: str) -> bool:
    """Delete a user in Firebase Auth first, then S3 photos, then Postgres (CASCADE)."""
    try:
        logger.info("Starting deletion for user %s", userId)

        try:
            await asyncio.to_thread(auth.delete_user, userId)
            logger.info("Successfully deleted user %s from Firebase Auth", userId)
        except Exception as e:
            # If Firebase fails, ABORT entirely. Do not touch the DB.
            logger.error("Failed to delete Firebase identity for %s. Aborting deletion: %s", userId, e)
            return False

        photo_paths_result = await db.execute(
            select(PhotoModel.file_path).where(PhotoModel.user_id == userId)
        )
        objects_to_delete = [{"Key": path} for path in photo_paths_result.scalars().all() if path]

        if objects_to_delete:
            try:
                await asyncio.to_thread(
                    s3_client.delete_objects,
                    Bucket=settings.S3_BUCKET_NAME,
                    Delete={"Objects": objects_to_delete},
                )
                logger.info("Batch deleted %d photos from S3", len(objects_to_delete))
            except Exception as e:
                logger.error("Failed batch S3 deletion for %s: %s", userId, e)
                # Log and continue so user/DB cleanup still finishes.

        user = await db.get(UserModel, userId)
        if not user:
            return False

        await db.delete(user)
        await db.commit()
        return True

    except Exception as e:
        await db.rollback()
        logger.error("Critical error in delete_user_service for %s: %s", userId, e)
        return False


# === Photo Services ===
async def get_photo_by_id(db: AsyncSession, photo_id: str, user_id: str) -> PhotoModel:
    """Retrieve a user-owned photo ORM record or raise HTTP 404."""
    result = await db.execute(
        select(PhotoModel).where(
            PhotoModel.photo_id == photo_id,
            PhotoModel.user_id == user_id,
        )
    )
    photo_doc = result.scalar_one_or_none()
    if not photo_doc:
        raise HTTPException(status_code=404, detail=f"Photo {photo_id} not found")
    return photo_doc


async def list_photos_service(db: AsyncSession, user_id: Optional[str] = None) -> list[dict]:
    """List photo metadata ordered newest-first, optionally scoped to one user."""
    stmt = select(PhotoModel).order_by(PhotoModel.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(PhotoModel.user_id == user_id)
    result = await db.execute(stmt)
    return [photo_helper(photo) for photo in result.scalars().all()]


async def save_photo_metadata_service(db: AsyncSession, userId: str, file_path: str) -> dict:
    """Persist photo metadata for an uploaded S3 key and return serialized photo dict."""
    photo_doc = PhotoModel(
        photo_id=str(uuid.uuid4()),
        user_id=userId,
        file_path=file_path,
        created_at=datetime.now(timezone.utc),
    )
    db.add(photo_doc)
    await db.commit()
    return photo_helper(photo_doc)


async def delete_photo_service(db: AsyncSession, userId: str, photoId: str) -> bool:
    """Delete a photo from S3 and Postgres."""
    photo_doc = await get_photo_by_id(db, photoId, userId)

    if photo_doc.file_path:
        try:
            await asyncio.to_thread(
                s3_client.delete_objects,
                Bucket=settings.S3_BUCKET_NAME,
                Delete={"Objects": [{"Key": photo_doc.file_path}]},
            )
            logger.info("Batch deleted 1 photos from S3")
        except Exception as e:
            logger.error("Failed batch S3 deletion for %s: %s", userId, e)

    await db.delete(photo_doc)
    await db.commit()
    return True


# === Diary Entry Services ===
async def list_diary_entries_service(db: AsyncSession, user_id: Optional[str] = None) -> list[dict]:
    """List diary entries ordered newest-first, optionally scoped to one user."""
    stmt = select(DiaryEntryModel).order_by(DiaryEntryModel.created_at.desc())
    if user_id is not None:
        stmt = stmt.where(DiaryEntryModel.user_id == user_id)
    result = await db.execute(stmt)
    return [diary_entry_helper(entry) for entry in result.scalars().all()]


async def count_diary_entries_service(db: AsyncSession, user_id: str) -> int:
    """Count diary entries belonging to a user."""
    result = await db.execute(
        select(func.count()).select_from(DiaryEntryModel).where(DiaryEntryModel.user_id == user_id)
    )
    return result.scalar_one()


async def get_diary_entry_by_id(db: AsyncSession, entry_id: str, user_id: str) -> Optional[dict]:
    """Fetch a single serialized diary entry owned by user_id, or None."""
    result = await db.execute(
        select(DiaryEntryModel).where(
            DiaryEntryModel.entry_id == entry_id,
            DiaryEntryModel.user_id == user_id,
        )
    )
    entry = result.scalar_one_or_none()
    return diary_entry_helper(entry) if entry else None


async def create_diary_entry_service(db: AsyncSession, userId: str, entry_data: dict) -> dict:
    """Create and return a new diary entry in Postgres."""
    try:
        if not userId:
            raise HTTPException(status_code=400, detail="User ID is required")
        if not entry_data.get("content"):
            raise HTTPException(status_code=400, detail="Entry content is required")

        entry = DiaryEntryModel(
            entry_id=str(uuid.uuid4()),
            user_id=userId,
            file_path=entry_data["filePath"],
            content=entry_data["content"],
            location=entry_data.get("location"),
            weather=entry_data.get("weather"),
            mode=entry_data.get("mode", "auto"),
            created_at=datetime.now(timezone.utc),
        )

        db.add(entry)
        await db.commit()
        return diary_entry_helper(entry)

    except HTTPException:
        raise
    except Exception:
        await db.rollback()
        logger.exception("Unexpected error creating diary entry for user %s", userId)
        raise HTTPException(status_code=500, detail="Failed to create diary entry")


async def update_diary_entry_service(
    db: AsyncSession, entryId: str, userId: str, entry_data: dict
) -> dict:
    """Update a diary entry owned by userId."""
    result = await db.execute(
        select(DiaryEntryModel).where(
            DiaryEntryModel.entry_id == entryId,
            DiaryEntryModel.user_id == userId,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entryId} not found")

    if "content" in entry_data:
        entry.content = entry_data["content"]
    if "location" in entry_data:
        entry.location = entry_data["location"]
    if "weather" in entry_data:
        entry.weather = entry_data["weather"]
    if "mode" in entry_data:
        entry.mode = entry_data["mode"]
    if "editedAt" in entry_data:
        entry.edited_at = entry_data["editedAt"]

    if entry_data:
        await db.commit()

    return diary_entry_helper(entry)


async def delete_diary_entry_service(db: AsyncSession, entryId: str, userId: str) -> bool:
    """Delete a single diary entry owned by userId."""
    result = await db.execute(
        select(DiaryEntryModel).where(
            DiaryEntryModel.entry_id == entryId,
            DiaryEntryModel.user_id == userId,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        return False

    await db.delete(entry)
    await db.commit()
    return True


async def delete_all_diary_entries_service(db: AsyncSession, userId: str) -> int:
    """Delete all diary entries belonging to userId and return deleted row count."""
    result = await db.execute(delete(DiaryEntryModel).where(DiaryEntryModel.user_id == userId))
    await db.commit()
    return result.rowcount or 0
