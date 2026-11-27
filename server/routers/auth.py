import logging

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordRequestForm
import httpx
from sqlalchemy.ext.asyncio import AsyncSession

from config import FIREBASE_SIGN_IN_URL, settings
from database import get_db
from models import TokenResponse
from services.api_services import get_client_ip
from services.cache_services import check_rate_limit
from services.db_services import get_user_by_id

logger = logging.getLogger(__name__)

router = APIRouter(
    tags=["Authentication"]
)

@router.post("/token", response_model=TokenResponse)
async def login_for_access_token(
    request: Request,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: AsyncSession = Depends(get_db),
):
    """
    Takes email (as username) and password, sends them to Firebase,
    and returns the Firebase ID Token.
    """
    client_ip = get_client_ip(request)
    allowed, retry_after = await check_rate_limit(
        f"smilesnap:rl:login:{client_ip}",
        limit=settings.LOGIN_RATE_LIMIT,
        window_seconds=settings.LOGIN_RATE_WINDOW_SECONDS,
    )
    if not allowed:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many login attempts. Please try again later.",
            headers={"Retry-After": str(retry_after)},
        )

    payload = {
        "email": form_data.username,
        "password": form_data.password,
        "returnSecureToken": True
    }

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
        # Log only the status code so str(e) never leaks the request URL (?key=...)
        logger.warning("Firebase sign-in rejected with status %s", e.response.status_code)

        # Don't expose internal errors to client
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication failed",
        )
    except httpx.RequestError as e:
        logger.error("Firebase sign-in request failed: %s", type(e).__name__)
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail="Authentication service unavailable",
        )