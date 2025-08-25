from fastapi import APIRouter, Depends
from typing import List
from database import user_collection, user_helper, diary_collection, diary_entry_helper, photo_collection, photo_helper
from models import User, DiaryEntry, Photo
from dependencies import get_current_admin_user

router = APIRouter(
    prefix="/admin",
    tags=["Admin"]
)

# ADD THIS ENDPOINT HERE
@router.get("/users", response_model=List[User])
async def get_all_users(
    admin_user: dict = Depends(get_current_admin_user)
):
    """Admin-only endpoint to list all users."""
    users = []
    async for user in user_collection.find({"role": "user"}):
        users.append(user_helper(user))
    
    return users

@router.get("/screenshots", response_model=List[Photo])
async def get_all_screenshots(admin_user: dict = Depends(get_current_admin_user)):
    """Admin-only endpoint to list all screenshots from all users."""
    photos = []
    async for photo in photo_collection.find():
        photos.append(photo_helper(photo))
    return photos

@router.get("/entries", response_model=List[DiaryEntry])
async def list_all_entries(admin_user: dict = Depends(get_current_admin_user)):
    """Admin-only endpoint to list all diary entries from all users."""
    entries = []
    async for entry in diary_collection.find():
        entries.append(diary_entry_helper(entry))
    return entries

