from fastapi import APIRouter, Depends, Body, HTTPException, Response, status
from typing import List
from models import DiaryEntry, DiaryEntryUpdate
from database import diary_collection, diary_entry_helper
from services.db_services import delete_diary_entry_service, update_diary_entry_service
from dependencies import verify_ownership_or_admin
from datetime import datetime, timezone
from .websockets import manager

router = APIRouter(
    prefix="/users/{userId}/entries",
    tags=["Entries"]
)

@router.get("", response_description="Get all entries for a user (no slash)", response_model=List[DiaryEntry])
@router.get("/", response_description="Get all entries for a user (with slash)", response_model=List[DiaryEntry])
async def get_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    # Get all entries for this user
    entries = []
    async for entry in diary_collection.find({"userId": userId}):
        entries.append(diary_entry_helper(entry))
    return entries

# @router.get("", response_description="Get all entries for a user", response_model=List[DiaryEntry])
# async def get_user_entries_no_slash(
#     userId: str,
#     authorized_user: dict = Depends(verify_ownership_or_admin)
# ):
#     # Get all entries for this user
#     entries = []
#     async for entry in diary_collection.find({"userId": userId}):
#         entries.append(diary_entry_helper(entry))
#     return entries

@router.get("/count", response_description="Count entries for user")
async def count_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    count = await diary_collection.count_documents({"userId": userId})
    return {"userId": userId, "entryCount": count}

# GET specific entry
@router.get("/{entryId}", response_description="Get specific entry", response_model=DiaryEntry)
async def get_user_entry(
    userId: str, 
    entryId: str, 
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    entry = await diary_collection.find_one({"entryId": entryId, "userId": userId})
    if not entry:
        raise HTTPException(status_code=404, detail=f"Entry {entryId} not found")
    return diary_entry_helper(entry)

# UPDATE specific entry (allows content changes with mode tracking)
@router.put("/{entryId}", response_description="Update entry (can modify content and switches to manual mode)", response_model=DiaryEntry)
async def update_user_entry(
    userId: str, 
    entryId: str, 
    entry: DiaryEntryUpdate = Body(...),
    authorized_user: dict = Depends(verify_ownership_or_admin)
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
    
    updated_entry = await update_diary_entry_service(entryId, userId, entry_dict)

    message = {"type": "entry_updated", "data": updated_entry}
    await manager.broadcast_to_admins(message)
    await manager.send_to_user(message, userId)

    return updated_entry

@router.delete("/{entryId}")
async def delete_user_entry(
    userId: str,
    entryId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    success = await delete_diary_entry_service(entryId, userId)
    if not success:
        raise HTTPException(status_code=404, detail="Entry not found")
    
    message = {"type": "entry_deleted", "data": {"entryId": entryId, "userId": userId}}
    await manager.broadcast_to_admins(message)
    await manager.send_to_user(message, userId)

    return Response(status_code=status.HTTP_204_NO_CONTENT)

@router.delete("/", response_description="Delete all entries for user")
async def delete_all_user_entries(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    delete_result = await diary_collection.delete_many({"userId": userId})
    return {"userId": userId, "deletedCount": delete_result.deleted_count}



# @router.post("/", response_description="Add new entry for user", response_model=DiaryEntry)
# async def create_user_entry(userId: str, entry: DiaryEntryCreate = Body(...), authorized_user: dict = Depends(verify_ownership_or_admin)):
#     entry_dict = entry.model_dump()
#     created_entry = await create_diary_entry_service(userId, entry_dict)
#     return created_entry

# === ENTRY CRUD operation ===
# READ (all)
# @router.get("/entries/", response_description="List all diary entries", response_model=List[DiaryEntry])
# async def list_diary_entries():
#     entries = []
#     async for entry in diary_collection.find():
#         entries.append(diary_entry_helper(entry))
#     return entries

# # READ (one)
# @router.get("/entries/{id}", response_description="Get a single diary entry", response_model=DiaryEntry)
# async def show_diary_entry(id: str):
#     if not ObjectId.is_valid(id):
#         raise HTTPException(status_code=400, detail=f"{id} is not a valid ObjectId")
        
#     entry = await diary_collection.find_one({"_id": ObjectId(id)})
#     if entry is not None:
#         return diary_entry_helper(entry)
#     raise HTTPException(status_code=404, detail=f"Diary entry {id} not found")