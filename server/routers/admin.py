from typing import List

from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db
from dependencies import get_current_admin_user
from models import DiaryEntry, Photo, User
from services.db_services import (
    list_diary_entries_service,
    list_photos_service,
    list_users_service,
)

router = APIRouter(
    prefix="/admin",
    tags=["Admin"],
)


@router.get("/users", response_model=List[User])
async def get_all_users(
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to list all non-admin users."""
    return await list_users_service(db, role="user")


@router.get("/screenshots", response_model=List[Photo])
async def get_all_screenshots(
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to list all screenshots from all users."""
    return await list_photos_service(db)


@router.get("/entries", response_model=List[DiaryEntry])
async def list_all_entries(
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    """Admin-only endpoint to list all diary entries from all users."""
    return await list_diary_entries_service(db)
