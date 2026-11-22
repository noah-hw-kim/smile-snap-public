from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastapi import HTTPException
from firebase_admin import auth

from models import UserCreate
from services import db_services


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
    mock_insert_one = AsyncMock()

    monkeypatch.setattr(db_services.auth, "create_user", mock_create_user)
    monkeypatch.setattr(db_services.user_collection, "insert_one", mock_insert_one)

    result = await db_services.create_user_services(
        {
            "email": "attacker@example.com",
            "password": "secret123",
            "displayName": "Attacker",
            "role": "admin",
        }
    )

    mock_create_user.assert_called_once_with(
        email="attacker@example.com",
        password="secret123",
        display_name="Attacker",
    )
    mock_insert_one.assert_awaited_once()

    inserted_doc = mock_insert_one.call_args.args[0]
    assert inserted_doc["userId"] == "firebase-uid-123"
    assert inserted_doc["role"] == "user"
    assert result["role"] == "user"


async def test_create_user_services_duplicate_email_returns_400(monkeypatch):
    """Duplicate Firebase email must raise HTTP 400 and never write to the DB."""
    mock_create_user = MagicMock(
        side_effect=auth.EmailAlreadyExistsError(
            "Email already exists", cause=None, http_response=None
        )
    )
    mock_insert_one = AsyncMock()

    monkeypatch.setattr(db_services.auth, "create_user", mock_create_user)
    monkeypatch.setattr(db_services.user_collection, "insert_one", mock_insert_one)

    with pytest.raises(HTTPException) as exc_info:
        await db_services.create_user_services(
            {"email": "dup@example.com", "password": "secret123"}
        )

    assert exc_info.value.status_code == 400
    mock_insert_one.assert_not_awaited()
