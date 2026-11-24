from datetime import datetime, timezone
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Response, status
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import verify_ownership_or_admin
from models import DiaryEntry, DiaryEntryUpdate
from services.db_services import (
    count_diary_entries_service,
    delete_all_diary_entries_service,
    delete_diary_entry_service,
    get_diary_entry_by_id,
    list_diary_entries_service,
    update_diary_entry_service,
)

router = APIRouter(
    prefix="/users/{userId}/entries",
    tags=["Entries"],
)


@router.get("", response_description="Get all entries for a user (no slash)", response_model=List[DiaryEntry])
@router.get("/", response_description="Get all entries for a user (with slash)", response_model=List[DiaryEntry])
async def get_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    return await list_diary_entries_service(db, user_id=userId)


@router.get("/count", response_description="Count entries for user")
async def count_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    count = await count_diary_entries_service(db, userId)
    return {"userId": userId, "entryCount": count}


# GET specific entry
@router.get("/{entryId}", response_description="Get specific entry", response_model=DiaryEntry)
async def get_user_entry(
    userId: str,
    entryId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    entry = await get_diary_entry_by_id(db, entryId, userId)
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entryId} not found")
    return entry


# UPDATE specific entry (allows content changes with mode tracking)
@router.put("/{entryId}", response_description="Update entry (can modify content and switches to manual mode)", response_model=DiaryEntry)
async def update_user_entry(
    userId: str,
    entryId: str,
    entry: DiaryEntryUpdate = Body(...),
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    """
    Update entry. If content is modified, automatically switches to manual mode.
    This preserves the distinction between AI-generated and user-edited content.
    """
    entry_dict = entry.model_dump(exclude_unset=True)

    # If content is being updated, mark as manual mode
    if "content" in entry_dict:
        entry_dict["mode"] = "manual"
        entry_dict["editedAt"] = datetime.now(timezone.utc)

    return await update_diary_entry_service(db, entryId, userId, entry_dict)


@router.delete("/{entryId}")
async def delete_user_entry(
    userId: str,
    entryId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    success = await delete_diary_entry_service(db, entryId, userId)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")

    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/", response_description="Delete all entries for user")
async def delete_all_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    deleted_count = await delete_all_diary_entries_service(db, userId)
    return {"userId": userId, "deletedCount": deleted_count}
