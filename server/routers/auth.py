from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import FIREBASE_SIGN_IN_URL
from database import get_db
import logging
from services.db_services import get_user_by_id

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/token")
async def login_for_access_token(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Takes email (as username) and password, sends them to Firebase,
    and returns the Firebase ID Token.
    """
    payload = {
        "email": form_data.username,
        "password": form_data.password,
        "returnSecureToken": True
    }

    logger = logging.getLogger(__name__)
    
    try:
        async with httpx.AsyncClient() as client:
            response = await client.post(FIREBASE_SIGN_IN_URL, json=payload, timeout=10)
            response.raise_for_status()
            firebase_data = response.json()

            firebase_uid = firebase_data.get("localId")
            id_token = firebase_data.get("idToken")

            if not firebase_uid or not id_token:
                raise HTTPException(status_code=500, detail="Invalid response from auth service")

            user_from_db = await get_user_by_id(db, firebase_uid)
            if not user_from_db:
                raise HTTPException(status_code=404, detail="User not found in application database")

            return {
                "access_token": id_token,
                "token_type": "bearer",
                "user": {
                    "userId": user_from_db.user_id,
                    "email": user_from_db.email,
                    "displayName": user_from_db.display_name,
                    "role": user_from_db.role,
                },
            }
        
    except httpx.HTTPStatusError as e:
        # httpx raises HTTPStatusError on 4xx/5xx responses from raise_for_status()
        logger.error(f"Firebase auth error: {str(e)}")

        # Don't expose internal errors to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED, 
            detail="Authentication failed"
        )