import asyncio
import logging

from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from firebase_admin import auth
from sqlalchemy.ext.asyncio import AsyncSession

from database import get_db, user_helper
from db_models import PhotoModel, UserModel

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")


async def get_current_user(
    token: str = Depends(oauth2_scheme),
    db: AsyncSession = Depends(get_db),
):
    """
    Verifies the Firebase ID token and returns the user's data.
    Raises an HTTPException if the token is invalid.
    """
    try:
        decoded_token = await asyncio.to_thread(auth.verify_id_token, token)

        user = await db.get(UserModel, decoded_token.get("uid"))
        if not user:
            raise HTTPException(status_code=404, detail="User not found in database")

        return user_helper(user)
    except HTTPException:
        raise
    except Exception as e:
        logger.warning("Token verification failed: %s", e)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication credentials",
            headers={"WWW-Authenticate": "Bearer"},
        )


async def get_current_admin_user(current_user: dict = Depends(get_current_user)):
    """A dependency that checks if the current user has the 'admin' role."""
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Admin access required for this resource.",
        )
    return current_user


async def verify_ownership_or_admin(userId: str, current_user: dict = Depends(get_current_user)):
    """
    A dependency that verifies the current user is either the owner of the
    resource (based on the userId in the URL) or is an admin.
    """
    is_owner = current_user["userId"] == userId
    is_admin = current_user.get("role") == "admin"

    if not is_owner and not is_admin:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not authorized to perform this action on this resource.",
        )
    return current_user


async def get_accessible_photo(
    photoId: str,
    current_user: dict = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Dependency that returns a photo if user has access to it.
    """
    try:
        photo_doc = await db.get(PhotoModel, photoId)
        if not photo_doc:
            raise HTTPException(status_code=404, detail=f"Photo {photoId} not found")

        is_owner = current_user["userId"] == photo_doc.user_id
        is_admin = current_user.get("role") == "admin"

        if not is_owner and not is_admin:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Not authorized to access this photo.",
            )

        return photo_doc

    except HTTPException:
        raise
    except Exception:
        logger.exception("Error accessing photo %s", photoId)
        raise HTTPException(status_code=500, detail="Error accessing photo")
