from io import BytesIO
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

from fastapi import HTTPException
from PIL import Image
import pytest

from services import api_services


def _make_png_bytes() -> bytes:
    """Create a valid 1x1 PNG byte buffer in memory for Pillow image loading tests."""
    buf = BytesIO()
    Image.new("RGB", (1, 1), color="white").save(buf, format="PNG")
    return buf.getvalue()


async def test_optional_enrichment_skips_calls_when_keys_blank(monkeypatch):
    """Blank ipinfo/OpenWeather keys must return empty context without making HTTP calls."""
    monkeypatch.setattr(api_services, "ipinfo_handler", None)
    monkeypatch.setattr(api_services.settings, "WEATHER_API_KEY", "")
    monkeypatch.setattr(
        api_services.httpx,
        "AsyncClient",
        MagicMock(side_effect=AssertionError("Unexpected external HTTP call")),
    )

    assert await api_services.get_location_from_ip("8.8.8.8") is None
    assert await api_services.get_weather_from_coordinates(37.56, 126.97) == {}


async def test_generate_diary_entry_happy_path(monkeypatch):
    """generate_diary_entry downloads S3 image, passes context to Gemini, and trims output."""
    png_bytes = _make_png_bytes()
    mock_get_object = MagicMock(return_value={"Body": BytesIO(png_bytes)})
    mock_generate = AsyncMock(return_value=SimpleNamespace(text="  Great sunny coffee moment! ☕  "))

    monkeypatch.setattr(api_services.settings, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(api_services.s3_client, "get_object", mock_get_object)
    monkeypatch.setattr(api_services.gemini_client.aio.models, "generate_content", mock_generate)

    result = await api_services.generate_diary_entry(
        "screenshots/uid-1/snap.png",
        location_data={"city": "Seoul", "region": "Seoul"},
        weather_data={"weather": "clear sky", "temperature": 21},
    )

    assert result == "Great sunny coffee moment! ☕"
    mock_get_object.assert_called_once_with(
        Bucket="test-bucket",
        Key="screenshots/uid-1/snap.png",
    )
    mock_generate.assert_awaited_once()
    contents = mock_generate.call_args.kwargs["contents"]
    prompt_text = contents[1]
    assert "Seoul, Seoul" in prompt_text
    assert "clear sky, 21°C" in prompt_text


@pytest.mark.parametrize(
    ("side_effect", "return_value"),
    [
        (RuntimeError("secret upstream quota error"), None),
        (None, SimpleNamespace(text="   ")),
    ],
)
async def test_generate_diary_entry_raises_502_on_failure(monkeypatch, side_effect, return_value):
    """H1/H4: S3/Gemini errors or blank text must raise sanitized HTTP 502, never fake diary text."""
    mock_get_object = MagicMock(return_value={"Body": BytesIO(_make_png_bytes())})
    mock_generate = AsyncMock(side_effect=side_effect, return_value=return_value)

    monkeypatch.setattr(api_services.settings, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(api_services.s3_client, "get_object", mock_get_object)
    monkeypatch.setattr(api_services.gemini_client.aio.models, "generate_content", mock_generate)

    with pytest.raises(HTTPException) as exc_info:
        await api_services.generate_diary_entry("screenshots/uid-1/snap.png")

    assert exc_info.value.status_code == 502
    assert exc_info.value.detail == "Failed to generate diary entry"
