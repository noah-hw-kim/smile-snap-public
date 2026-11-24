from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
import pytest

import database
from db_models import DiaryEntryModel, UserModel
from services import db_services


def _make_mock_db() -> MagicMock:
    """Create a lightweight mocked AsyncSession for service unit tests."""
    mock_db = MagicMock()
    mock_db.add = MagicMock()
    mock_db.commit = AsyncMock()
    mock_db.rollback = AsyncMock()
    mock_db.delete = AsyncMock()
    mock_db.get = AsyncMock()
    mock_db.execute = AsyncMock()
    return mock_db


async def test_delete_user_aborts_before_s3_and_db_when_firebase_fails(monkeypatch):
    """H3: If Firebase Auth deletion fails, abort before touching S3 or Postgres."""
    mock_db = _make_mock_db()
    mock_s3_delete = MagicMock()

    monkeypatch.setattr(
        db_services.auth,
        "delete_user",
        MagicMock(side_effect=RuntimeError("firebase unavailable")),
    )
    monkeypatch.setattr(db_services.s3_client, "delete_objects", mock_s3_delete)

    deleted = await db_services.delete_user_service(mock_db, "uid-1")

    assert deleted is False
    mock_s3_delete.assert_not_called()
    mock_db.execute.assert_not_awaited()
    mock_db.delete.assert_not_awaited()
    mock_db.commit.assert_not_awaited()


async def test_delete_user_follows_firebase_s3_postgres_order(monkeypatch):
    """H3: User deletion must run Firebase Auth -> S3 batch delete -> Postgres delete."""
    calls: list[str] = []
    s3_kwargs: dict = {}

    def fake_firebase_delete(uid: str):
        calls.append("firebase")

    def fake_s3_delete(**kwargs):
        calls.append("s3")
        s3_kwargs.update(kwargs)

    async def fake_db_delete(obj):
        calls.append("db_delete")

    mock_photo_result = MagicMock()
    mock_photo_result.scalars.return_value.all.return_value = [
        "screenshots/uid-1/a.png",
        "screenshots/uid-1/b.png",
    ]

    mock_db = _make_mock_db()
    mock_db.execute = AsyncMock(return_value=mock_photo_result)
    mock_db.get = AsyncMock(return_value=UserModel(user_id="uid-1", email="u@example.com"))
    mock_db.delete = AsyncMock(side_effect=fake_db_delete)

    monkeypatch.setattr(db_services.settings, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(db_services.auth, "delete_user", fake_firebase_delete)
    monkeypatch.setattr(db_services.s3_client, "delete_objects", fake_s3_delete)

    deleted = await db_services.delete_user_service(mock_db, "uid-1")

    assert deleted is True
    assert calls == ["firebase", "s3", "db_delete"]
    assert s3_kwargs == {
        "Bucket": "test-bucket",
        "Delete": {
            "Objects": [
                {"Key": "screenshots/uid-1/a.png"},
                {"Key": "screenshots/uid-1/b.png"},
            ]
        },
    }
    mock_db.commit.assert_awaited_once()


async def test_create_diary_entry_persists_model_and_validates_content(monkeypatch):
    """Valid diary creation commits a DiaryEntryModel and returns camelCase fields; empty content fails 400."""
    monkeypatch.setattr(
        database.s3_client,
        "generate_presigned_url",
        MagicMock(return_value="https://s3.example/presigned"),
    )

    mock_db = _make_mock_db()
    result = await db_services.create_diary_entry_service(
        mock_db,
        "uid-1",
        {
            "filePath": "screenshots/uid-1/snap.png",
            "content": "Sunny day in Seoul!",
            "location": {"city": "Seoul"},
            "weather": {"weather": "clear sky", "temperature": 21},
        },
    )

    mock_db.add.assert_called_once()
    mock_db.commit.assert_awaited_once()
    added_entry = mock_db.add.call_args.args[0]
    assert isinstance(added_entry, DiaryEntryModel)
    assert added_entry.user_id == "uid-1"
    assert added_entry.mode == "auto"

    assert set(result.keys()) == {
        "entryId",
        "userId",
        "content",
        "imageUrl",
        "location",
        "weather",
        "mode",
        "createdAt",
        "editedAt",
    }
    assert result["userId"] == "uid-1"
    assert result["imageUrl"] == "https://s3.example/presigned"
    assert result["mode"] == "auto"
    assert result["editedAt"] is None

    empty_db = _make_mock_db()
    with pytest.raises(HTTPException) as exc_info:
        await db_services.create_diary_entry_service(
            empty_db,
            "uid-1",
            {"filePath": "screenshots/uid-1/snap.png", "content": ""},
        )

    assert exc_info.value.status_code == 400
    empty_db.add.assert_not_called()
    empty_db.commit.assert_not_awaited()


async def test_update_diary_entry_not_found_returns_404():
    """Updating a missing or non-owned diary entry must raise HTTP 404 without committing."""
    mock_result = MagicMock()
    mock_result.scalar_one_or_none.return_value = None

    mock_db = _make_mock_db()
    mock_db.execute = AsyncMock(return_value=mock_result)

    with pytest.raises(HTTPException) as exc_info:
        await db_services.update_diary_entry_service(
            mock_db,
            "entry-999",
            "uid-1",
            {"content": "edited"},
        )

    assert exc_info.value.status_code == 404
    mock_db.commit.assert_not_awaited()
