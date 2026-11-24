import json
import logging

import redis.asyncio as redis
from redis.exceptions import RedisError

from config import settings

logger = logging.getLogger(__name__)

GEO_CACHE_TTL_SECONDS = 86_400  # 24 hours
WEATHER_CACHE_TTL_SECONDS = 1_200  # 20 minutes
_SOCKET_TIMEOUT_SECONDS = 1.5


def _create_redis_client() -> redis.Redis | None:
    """Create a short-lived async Redis client when REDIS_URL is configured."""
    if not settings.REDIS_URL:
        return None

    return redis.from_url(
        settings.REDIS_URL,
        encoding="utf-8",
        decode_responses=True,
        socket_connect_timeout=_SOCKET_TIMEOUT_SECONDS,
        socket_timeout=_SOCKET_TIMEOUT_SECONDS,
        retry_on_timeout=False,
    )


async def cache_get_json(key: str) -> dict | None:
    """Fetch and decode a JSON dict from Redis, failing open on errors."""
    client = _create_redis_client()
    if client is None:
        return None

    try:
        raw = await client.get(key)
        if not raw:
            return None
        data = json.loads(raw)
        return data if isinstance(data, dict) else None
    except (RedisError, OSError, json.JSONDecodeError) as e:
        logger.warning("Redis cache get failed for %s: %s", key, e)
        return None
    finally:
        await client.aclose()


async def cache_set_json(key: str, value: dict, ttl_seconds: int) -> None:
    """Serialize and store a JSON dict in Redis with TTL, failing open on errors."""
    client = _create_redis_client()
    if client is None:
        return

    try:
        await client.set(key, json.dumps(value), ex=ttl_seconds)
    except (RedisError, OSError, TypeError, ValueError) as e:
        logger.warning("Redis cache set failed for %s: %s", key, e)
    finally:
        await client.aclose()


async def check_rate_limit(key: str, limit: int, window_seconds: int) -> tuple[bool, int]:
    """Enforce a fixed-window rate limit using atomic INCR + EXPIRE NX, failing open on errors."""
    client = _create_redis_client()
    if client is None:
        return True, 0

    try:
        async with client.pipeline(transaction=True) as pipe:
            pipe.incr(key)
            pipe.expire(key, window_seconds, nx=True)
            pipe.ttl(key)
            count, _expire_applied, ttl = await pipe.execute()

        if int(count) > limit:
            retry_after = int(ttl) if isinstance(ttl, int) and ttl > 0 else window_seconds
            return False, retry_after

        return True, 0
    except (RedisError, OSError) as e:
        logger.warning("Redis rate limit check failed for %s: %s", key, e)
        return True, 0
    finally:
        await client.aclose()
