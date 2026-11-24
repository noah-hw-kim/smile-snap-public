from collections.abc import AsyncGenerator
import logging
from urllib.parse import parse_qsl, urlencode, urlparse, urlunparse

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.pool import NullPool

from config import s3_client, settings
from db_models import DiaryEntryModel, PhotoModel, UserModel

logger = logging.getLogger(__name__)


def normalize_database_url(raw_url: str) -> tuple[str, dict]:
    """Convert a Postgres/Neon URI into an asyncpg URL and connect_args."""
    url = raw_url.strip()
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql+asyncpg://", 1)
    elif url.startswith("postgresql://"):
        url = url.replace("postgresql://", "postgresql+asyncpg://", 1)

    parsed = urlparse(url)
    params = dict(parse_qsl(parsed.query, keep_blank_values=True))

    # asyncpg rejects libpq query parameters like sslmode and channel_binding
    sslmode = params.pop("sslmode", None)
    params.pop("channel_binding", None)

    clean_url = urlunparse(parsed._replace(query=urlencode(params)))

    # Disable client-side statement caching for Neon's PgBouncer pooler
    connect_args: dict = {"statement_cache_size": 0}
    if sslmode != "disable":
        connect_args["ssl"] = True

    return clean_url, connect_args


_async_db_url, _db_connect_args = normalize_database_url(settings.DATABASE_URL)

engine = create_async_engine(
    _async_db_url,
    poolclass=NullPool,
    connect_args=_db_connect_args,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
)


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a per-request async SQLAlchemy session."""
    async with AsyncSessionLocal() as session:
        yield session


def _generate_presigned_get_url(file_path: str | None) -> str | None:
    """Create a 15-minute presigned S3 GET URL for a stored object key."""
    if not file_path:
        return None
    try:
        # generate_presigned_url is a local HMAC computation — no network call, safe sync.
        return s3_client.generate_presigned_url(
            "get_object",
            Params={"Bucket": settings.S3_BUCKET_NAME, "Key": file_path},
            ExpiresIn=900,
        )
    except Exception as e:
        logger.error(f"FAILED to generate presigned URL ({type(e).__name__}): {e}")
        return None


def diary_entry_helper(entry: DiaryEntryModel) -> dict:
    """Serialize a DiaryEntryModel ORM row into the camelCase API dict."""
    return {
        "entryId": entry.entry_id,
        "userId": entry.user_id,
        "content": entry.content,
        "imageUrl": _generate_presigned_get_url(entry.file_path),
        "location": entry.location,
        "weather": entry.weather,
        "mode": entry.mode or "auto",
        "createdAt": entry.created_at.isoformat() if entry.created_at else None,
        "editedAt": entry.edited_at.isoformat() if entry.edited_at else None,
    }


def user_helper(user: UserModel) -> dict:
    """Serialize a UserModel ORM row into the camelCase API dict."""
    return {
        "userId": user.user_id,
        "email": user.email,
        "displayName": user.display_name,
        "createdAt": user.created_at.isoformat() if user.created_at else None,
        "role": user.role,
    }


def photo_helper(photo: PhotoModel) -> dict:
    """Serialize a PhotoModel ORM row into the camelCase API dict."""
    return {
        "userId": photo.user_id,
        "photoId": photo.photo_id,
        "filePath": photo.file_path,
        "photoUrl": _generate_presigned_get_url(photo.file_path),
        "createdAt": photo.created_at.isoformat() if photo.created_at else None,
    }
