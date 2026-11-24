from unittest.mock import AsyncMock, MagicMock

from redis.exceptions import RedisError

from services import cache_services


class _FakePipeline:
    """Async context-manager mock matching redis.asyncio pipeline(transaction=True)."""

    def __init__(self, execute_result):
        self.incr = MagicMock()
        self.expire = MagicMock()
        self.ttl = MagicMock()
        self.execute = AsyncMock(return_value=execute_result)

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False


def _make_fake_redis(*, get_value=None, get_side_effect=None, set_side_effect=None, pipe=None):
    client = MagicMock()
    client.get = AsyncMock(return_value=get_value, side_effect=get_side_effect)
    client.set = AsyncMock(side_effect=set_side_effect)
    client.aclose = AsyncMock()
    client.pipeline = MagicMock(return_value=pipe)
    return client


async def test_cache_and_rate_limit_disabled_when_redis_url_blank(monkeypatch):
    """Blank REDIS_URL must skip Redis connections and return disabled defaults."""
    monkeypatch.setattr(cache_services.settings, "REDIS_URL", "")
    mock_from_url = MagicMock(side_effect=AssertionError("Redis should not be initialized"))
    monkeypatch.setattr(cache_services.redis, "from_url", mock_from_url)

    assert await cache_services.cache_get_json("smilesnap:geo:1.2.3.4") is None
    await cache_services.cache_set_json("smilesnap:geo:1.2.3.4", {"city": "Seoul"}, 60)
    assert await cache_services.check_rate_limit("smilesnap:rl:generate:u1", 10, 3600) == (True, 0)


async def test_cache_get_and_set_json_roundtrip(monkeypatch):
    """cache_set_json serializes with TTL and cache_get_json parses valid dicts, closing client."""
    fake_client = _make_fake_redis(get_value='{"city": "Seoul", "region": "Seoul"}')
    monkeypatch.setattr(cache_services.settings, "REDIS_URL", "redis://localhost:6379")
    monkeypatch.setattr(cache_services.redis, "from_url", MagicMock(return_value=fake_client))

    await cache_services.cache_set_json("smilesnap:geo:1.2.3.4", {"city": "Seoul"}, 86400)
    fake_client.set.assert_awaited_once_with("smilesnap:geo:1.2.3.4", '{"city": "Seoul"}', ex=86400)

    loaded = await cache_services.cache_get_json("smilesnap:geo:1.2.3.4")
    assert loaded == {"city": "Seoul", "region": "Seoul"}
    assert fake_client.aclose.await_count == 2


async def test_cache_and_rate_limit_fail_open_on_redis_error(monkeypatch):
    """RedisError must degrade gracefully (None / allow) and still close the client."""
    bad_pipe = _FakePipeline(execute_result=None)
    bad_pipe.execute = AsyncMock(side_effect=RedisError("connection refused"))
    fake_client = _make_fake_redis(
        get_side_effect=RedisError("timeout"),
        set_side_effect=RedisError("read-only"),
        pipe=bad_pipe,
    )
    monkeypatch.setattr(cache_services.settings, "REDIS_URL", "redis://localhost:6379")
    monkeypatch.setattr(cache_services.redis, "from_url", MagicMock(return_value=fake_client))

    assert await cache_services.cache_get_json("smilesnap:geo:1.2.3.4") is None
    await cache_services.cache_set_json("smilesnap:geo:1.2.3.4", {"city": "Seoul"}, 60)
    assert await cache_services.check_rate_limit("smilesnap:rl:generate:u1", 10, 3600) == (True, 0)
    assert fake_client.aclose.await_count == 3


async def test_check_rate_limit_allows_and_blocks_with_atomic_pipeline(monkeypatch):
    """check_rate_limit increments with EXPIRE NX and returns (False, ttl) once limit is exceeded."""
    monkeypatch.setattr(cache_services.settings, "REDIS_URL", "redis://localhost:6379")

    allow_pipe = _FakePipeline(execute_result=[10, True, 3590])
    allow_client = _make_fake_redis(pipe=allow_pipe)
    monkeypatch.setattr(cache_services.redis, "from_url", MagicMock(return_value=allow_client))

    assert await cache_services.check_rate_limit("smilesnap:rl:generate:u1", 10, 3600) == (True, 0)
    allow_pipe.incr.assert_called_once_with("smilesnap:rl:generate:u1")
    allow_pipe.expire.assert_called_once_with("smilesnap:rl:generate:u1", 3600, nx=True)
    allow_pipe.ttl.assert_called_once_with("smilesnap:rl:generate:u1")
    allow_client.aclose.assert_awaited_once()

    block_pipe = _FakePipeline(execute_result=[11, False, 1420])
    block_client = _make_fake_redis(pipe=block_pipe)
    monkeypatch.setattr(cache_services.redis, "from_url", MagicMock(return_value=block_client))

    assert await cache_services.check_rate_limit("smilesnap:rl:generate:u1", 10, 3600) == (False, 1420)
    block_client.aclose.assert_awaited_once()
