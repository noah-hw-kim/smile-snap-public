from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from firebase_admin import auth
from pydantic import ValidationError

from db_models import UserModel
from models import DiaryEntryUpdate, UserCreate, UserUpdate
from services import db_services


def _make_mock_db() -> MagicMock:
    """Create a lightweight mocked AsyncSession for unit tests."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    return mock_db


def test_user_create_schema_drops_role():
    """Public UserCreate schema must not accept or forward a client-supplied role."""
    payload = UserCreate(
        email="attacker@example.com",
        password="secret123",
        displayName="Attacker",
        role="admin",
    )

    assert "role" not in payload.model_dump()


async def test_create_user_services_always_assigns_user_role(monkeypatch):
    """Even if a caller passes role='admin' in user_data, persisted role must be 'user'."""
    fake_firebase_user = SimpleNamespace(uid="firebase-uid-123")
    mock_create_user = MagicMock(return_value=fake_firebase_user)
    mock_db = _make_mock_db()

    monkeypatch.setattr(db_services.auth, "create_user", mock_create_user)

    result = await db_services.create_user_services(
        mock_db,
        {
            "email": "attacker@example.com",
            "password": "secret123",
            "displayName": "Attacker",
            "role": "admin",
        },
    )

    mock_create_user.assert_called_once_with(
        email="attacker@example.com",
        password="secret123",
        display_name="Attacker",
    )
    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()

    added_user = mock_db.add.call_args.args[0]
    assert isinstance(added_user, UserModel)
    assert added_user.user_id == "firebase-uid-123"
    assert added_user.role == "user"
    assert result["role"] == "user"


async def test_create_user_services_duplicate_email_returns_400(monkeypatch):
    """Duplicate Firebase email must raise HTTP 400 and never write to the DB."""
    mock_create_user = MagicMock(
        side_effect=auth.EmailAlreadyExistsError(
            "Email already exists", cause=None, http_response=None
        )
    )
    mock_db = _make_mock_db()

    monkeypatch.setattr(db_services.auth, "create_user", mock_create_user)

    with pytest.raises(HTTPException) as exc_info:
        await db_services.create_user_services(
            mock_db,
            {"email": "dup@example.com", "password": "secret123"},
        )

    assert exc_info.value.status_code == 400
    mock_db.add.assert_not_called()
    mock_db.commit.assert_not_awaited()


async def test_create_user_route_returns_429_when_signup_rate_limited(monkeypatch):
    """Public signup route returns HTTP 429 + Retry-After when IP rate limit is exceeded."""
    from routers import users

    fake_request = MagicMock()
    fake_request.headers = {"x-forwarded-for": "203.0.113.10"}
    fake_request.client = None

    monkeypatch.setattr(users, "check_rate_limit", AsyncMock(return_value=(False, 1800)))
    mock_create = AsyncMock()
    monkeypatch.setattr(users, "create_user_services", mock_create)

    payload = UserCreate(
        email="new@example.com",
        password="secret123",
        displayName="New User",
    )

    with pytest.raises(HTTPException) as exc_info:
        await users.create_user(request=fake_request, user=payload, db=_make_mock_db())

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "1800"}
    mock_create.assert_not_awaited()


def test_user_update_rejects_email_change():
    """UserUpdate must reject email fields so Postgres and Firebase emails cannot drift."""
    with pytest.raises(ValidationError):
        UserUpdate(email="new@example.com")


def test_user_create_rejects_invalid_email():
    """UserCreate must validate email format with EmailStr."""
    with pytest.raises(ValidationError):
        UserCreate(email="not-an-email", password="secret123")


def test_diary_entry_update_enforces_content_max_length():
    """DiaryEntryUpdate enforces the same 5000-char limit as DiaryEntryCreate."""
    assert DiaryEntryUpdate(content="x" * 5000).content == "x" * 5000
    with pytest.raises(ValidationError):
        DiaryEntryUpdate(content="x" * 5001)
