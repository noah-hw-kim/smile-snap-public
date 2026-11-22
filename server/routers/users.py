from typing import List
from fastapi import APIRouter, Body, HTTPException, Depends
from models import User, UserCreate, UserUpdate
from database import user_collection, user_helper
from dependencies import verify_ownership_or_admin, get_current_admin_user
from services.db_services import create_user_services, get_user_by_id, update_user_service, delete_user_service
import logging

router = APIRouter(
    prefix="/users",
    tags=["Users"] # This creates a nice grouping in the API docs
)

logger = logging.getLogger(__name__)

# === User CRUD operations ===
# CREATE User - This is a public endpoint, so no dependency is needed.
@router.post("/", response_description="Create new user", response_model=User)
async def create_user(
    user: UserCreate = Body(...)
):
    user_dict = user.model_dump()
    created_user = await create_user_services(user_dict)

    return created_user

# GET ALL Users - This should be ADMIN ONLY
@router.get("/", response_description="Get all users (Admin Only)", response_model=List[User])
async def get_all_users(
    admin_user: dict = Depends(get_current_admin_user)
):
    users = []
    async for user in user_collection.find():
        users.append(user_helper(user))
    return users

# GET, UPDATE, DELETE a specific user - Requires ownership OR admin access.
@router.get("/{userId}", response_description="Get user by userId", response_model=User)
async def get_user(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    user = await get_user_by_id(userId) 
    if user:
        return user_helper(user)
    raise HTTPException(status_code=404, detail=f"User {userId} not found")

# UPDATE User - user(self), admin
@router.put("/{userId}", response_description="Update a user", response_model=User)
async def update_user(
    userId: str,
    user: UserUpdate = Body(...),
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    # First, get the target user's current data
    target_user = await user_collection.find_one({"userId": userId})
    if not target_user:
        raise HTTPException(status_code=404, detail=f"User {userId} not found")
    
    # Check email uniqueness only if email is being changed to a different value
    if user.email and user.email != target_user["email"]:
        email_exists = await user_collection.find_one({"email": user.email})
        if email_exists:
            raise HTTPException(status_code=400, detail="User with this email already exists")
    
    # Only update fields that are provided (not None)
    user_dict = user.model_dump(exclude_unset=True)
    updated_user = await update_user_service(userId, user_dict)

    return updated_user

# DELETE User - user(self), admin
@router.delete("/{userId}", response_description="Delete a user")
async def delete_user(
    userId: str,
    authorized_user: dict = Depends(verify_ownership_or_admin)
):
    success = await delete_user_service(userId)
    if success:
        return {"message": "User and all associated data deleted successfully", "deletedUserId": userId}
    raise HTTPException(
        status_code=404, 
        detail=f"User {userId} not found or deletion failed"
    )