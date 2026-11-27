import logging
from typing import List

from fastapi import APIRouter, Body, Depends, HTTPException, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from config import settings
from database import get_db, user_helper
from dependencies import get_current_admin_user, verify_ownership_or_admin
from models import User, UserCreate, UserDeleteResponse, UserUpdate
from services.api_services import get_client_ip
from services.cache_services import check_rate_limit
from services.db_services import (
    create_user_services,
    delete_user_service,
    get_user_by_id,
    list_users_service,
    update_user_service,
)

router = APIRouter(
    prefix="/users",
    tags=["Users"],
)

logger = logging.getLogger(__name__)


# === User CRUD operations ===
# CREATE User - This is a public endpoint, so no dependency is needed.
@router.post("/", response_description="Create new user", response_model=User)
async def create_user(
    request: Request,
    user: UserCreate = Body(...),
    db: AsyncSession = Depends(get_db),
):
    client_ip = get_client_ip(request)
    allowed, retry_after = await check_rate_limit(
        f"smilesnap:rl:signup:{client_ip}",
        limit=settings.SIGNUP_RATE_LIMIT,
        window_seconds=settings.SIGNUP_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many signup attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    user_dict = user.model_dump()
    return await create_user_services(db, user_dict)


# GET ALL Users - This should be ADMIN ONLY
@router.get("/", response_description="Get all users (Admin Only)", response_model=List[User])
async def get_all_users(
    admin_user: dict = Depends(get_current_admin_user),
    db: AsyncSession = Depends(get_db),
):
    return await list_users_service(db)


# GET, UPDATE, DELETE a specific user - Requires ownership OR admin access.
@router.get("/{userId}", response_description="Get user by userId", response_model=User)
async def get_user(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    user = await get_user_by_id(db, userId)
    if user:
        return user_helper(user)
    raise HTTPException(status_code=404, detail=f"User {userId} not found")


# UPDATE User - user(self), admin
@router.put("/{userId}", response_description="Update a user", response_model=User)
async def update_user(
    userId: str,
    user: UserUpdate = Body(...),
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    target_user = await get_user_by_id(db, userId)
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {userId} not found")

    user_dict = user.model_dump(exclude_unset=True)
    return await update_user_service(db, userId, user_dict)


# DELETE User - user(self), admin
@router.delete("/{userId}", response_description="Delete a user", response_model=UserDeleteResponse)
async def delete_user(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin),
    db: AsyncSession = Depends(get_db),
):
    success = await delete_user_service(db, userId)
    if success:
        return {"message": "User and all associated data deleted successfully", "deletedUserId": userId}
    raise HTTPException(
        status_code=404,
        detail=f"User {userId} not found or deletion failed",
    )
