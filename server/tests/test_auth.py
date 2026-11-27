import logging
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import httpx
import pytest
from fastapi import HTTPException

from routers import auth


def _make_request(host: str = "198.51.100.10") -> MagicMock:
    req = MagicMock()
    req.client = SimpleNamespace(host=host)
    req.headers = {}
    return req


def _make_async_client_cm(post_mock: AsyncMock) -> MagicMock:
    mock_http_client = MagicMock()
    mock_http_client.post = post_mock
    mock_cm = MagicMock()
    mock_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_cm.__aexit__ = AsyncMock(return_value=False)
    return mock_cm


async def test_login_returns_429_when_rate_limited(monkeypatch):
    """POST /token must enforce IP rate limiting before calling Firebase."""
    monkeypatch.setattr(auth, "check_rate_limit", AsyncMock(return_value=(False, 600)))
    mock_post = AsyncMock()
    monkeypatch.setattr(auth.httpx, "AsyncClient", MagicMock(return_value=_make_async_client_cm(mock_post)))

    with pytest.raises(HTTPException) as exc_info:
        await auth.login_for_access_token(
            request=_make_request(),
            form_data=SimpleNamespace(username="user@example.com", password="secret"),
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "600"}
    mock_post.assert_not_awaited()


async def test_login_returns_503_on_firebase_network_error(monkeypatch):
    """Upstream Firebase network errors/timeouts must return HTTP 503."""
    monkeypatch.setattr(auth, "check_rate_limit", AsyncMock(return_value=(True, 0)))
    mock_post = AsyncMock(side_effect=httpx.ConnectTimeout("timed out"))
    monkeypatch.setattr(auth.httpx, "AsyncClient", MagicMock(return_value=_make_async_client_cm(mock_post)))

    with pytest.raises(HTTPException) as exc_info:
        await auth.login_for_access_token(
            request=_make_request(),
            form_data=SimpleNamespace(username="user@example.com", password="secret"),
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 503
    assert exc_info.value.detail == "Authentication service unavailable"


async def test_login_401_does_not_log_firebase_api_key(monkeypatch, caplog):
    """HTTPStatusError from Firebase must return 401 and never log the ?key= query string."""
    monkeypatch.setattr(auth, "check_rate_limit", AsyncMock(return_value=(True, 0)))
    fake_request = httpx.Request(
        "POST",
        "https://identitytoolkit.googleapis.com/v1/accounts:signInWithPassword?key=test-firebase-web-key",
    )
    fake_response = httpx.Response(status_code=400, request=fake_request)
    mock_post = AsyncMock(return_value=fake_response)
    monkeypatch.setattr(auth.httpx, "AsyncClient", MagicMock(return_value=_make_async_client_cm(mock_post)))

    with caplog.at_level(logging.WARNING):
        with pytest.raises(HTTPException) as exc_info:
            await auth.login_for_access_token(
                request=_make_request(),
                form_data=SimpleNamespace(username="user@example.com", password="wrong"),
                db=MagicMock(),
            )

    assert exc_info.value.status_code == 401
    assert "test-firebase-web-key" not in caplog.text
    assert "400" in caplog.text
