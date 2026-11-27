from io import BytesIO
import logging
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


async def test_get_location_from_ip_returns_cached_value_without_calling_ipinfo(monkeypatch):
    """Cache hit in get_location_from_ip must return cached dict without calling ipinfo."""
    cached_geo = {"city": "Seoul", "region": "Seoul", "country": "KR"}
    mock_handler = MagicMock()
    mock_handler.getDetails = MagicMock(side_effect=AssertionError("ipinfo should not be called on cache hit"))

    monkeypatch.setattr(api_services, "ipinfo_handler", mock_handler)
    monkeypatch.setattr(api_services, "cache_get_json", AsyncMock(return_value=cached_geo))
    mock_cache_set = AsyncMock()
    monkeypatch.setattr(api_services, "cache_set_json", mock_cache_set)

    result = await api_services.get_location_from_ip("8.8.8.8")

    assert result == cached_geo
    mock_cache_set.assert_not_awaited()


async def test_get_weather_from_coordinates_caches_rounded_key_on_miss(monkeypatch):
    """Cache miss in get_weather_from_coordinates fetches OpenWeather and stores rounded cache key."""
    fake_response = MagicMock()
    fake_response.raise_for_status = MagicMock()
    fake_response.json.return_value = {
        "weather": [{"description": "clear sky"}],
        "main": {"temp": 21.5},
        "name": "Seoul",
        "sys": {"country": "KR"},
    }
    mock_http_client = MagicMock()
    mock_http_client.get = AsyncMock(return_value=fake_response)
    mock_client_cm = MagicMock()
    mock_client_cm.__aenter__ = AsyncMock(return_value=mock_http_client)
    mock_client_cm.__aexit__ = AsyncMock(return_value=False)

    monkeypatch.setattr(api_services.settings, "WEATHER_API_KEY", "test-weather-key")
    monkeypatch.setattr(api_services.httpx, "AsyncClient", MagicMock(return_value=mock_client_cm))
    monkeypatch.setattr(api_services, "cache_get_json", AsyncMock(return_value=None))
    mock_cache_set = AsyncMock()
    monkeypatch.setattr(api_services, "cache_set_json", mock_cache_set)

    result = await api_services.get_weather_from_coordinates(37.5665, 126.978)

    expected = {"weather": "clear sky", "temperature": 21.5, "city": "Seoul", "country": "KR"}
    assert result == expected
    mock_cache_set.assert_awaited_once_with(
        "smilesnap:weather:37.57:126.98",
        expected,
        api_services.WEATHER_CACHE_TTL_SECONDS,
    )


def _make_upload_file(content: bytes, content_type: str | None) -> MagicMock:
    upload = MagicMock()
    upload.content_type = content_type
    upload.read = AsyncMock(return_value=content)
    return upload


@pytest.mark.parametrize("bad_type", ["text/plain", "image/svg+xml", None])
async def test_upload_image_to_s3_rejects_disallowed_content_types(monkeypatch, bad_type):
    """Non-image MIME types and SVGs must fail with HTTP 400 before touching S3."""
    mock_put = MagicMock()
    monkeypatch.setattr(api_services.s3_client, "put_object", mock_put)

    with pytest.raises(HTTPException) as exc_info:
        await api_services.upload_image_to_s3("uid-1", _make_upload_file(b"data", bad_type))

    assert exc_info.value.status_code == 400
    mock_put.assert_not_called()


async def test_upload_image_to_s3_rejects_empty_and_oversized_files(monkeypatch):
    """Empty uploads fail 400 and uploads exceeding MAX_UPLOAD_BYTES fail 413 without touching S3."""
    mock_put = MagicMock()
    monkeypatch.setattr(api_services.s3_client, "put_object", mock_put)
    monkeypatch.setattr(api_services.settings, "MAX_UPLOAD_BYTES", 100)

    with pytest.raises(HTTPException) as empty_exc:
        await api_services.upload_image_to_s3("uid-1", _make_upload_file(b"", "image/png"))
    assert empty_exc.value.status_code == 400

    with pytest.raises(HTTPException) as big_exc:
        await api_services.upload_image_to_s3("uid-1", _make_upload_file(b"x" * 101, "image/png"))
    assert big_exc.value.status_code == 413
    mock_put.assert_not_called()


async def test_upload_image_to_s3_rejects_corrupted_image_bytes(monkeypatch):
    """Spoofed image/png header with invalid image bytes must fail HTTP 400 before touching S3."""
    mock_put = MagicMock()
    monkeypatch.setattr(api_services.s3_client, "put_object", mock_put)

    with pytest.raises(HTTPException) as exc_info:
        await api_services.upload_image_to_s3("uid-1", _make_upload_file(b"not-a-real-png", "image/png"))

    assert exc_info.value.status_code == 400
    mock_put.assert_not_called()


async def test_upload_image_to_s3_uploads_valid_png(monkeypatch):
    """Valid PNG bytes pass validation and upload to S3 with .png key."""
    png_bytes = _make_png_bytes()
    mock_put = MagicMock()
    monkeypatch.setattr(api_services.settings, "S3_BUCKET_NAME", "test-bucket")
    monkeypatch.setattr(api_services.s3_client, "put_object", mock_put)

    key = await api_services.upload_image_to_s3("uid-1", _make_upload_file(png_bytes, "image/png"))

    assert key.startswith("screenshots/uid-1/")
    assert key.endswith(".png")
    mock_put.assert_called_once_with(
        Bucket="test-bucket",
        Key=key,
        Body=png_bytes,
        ContentType="image/png",
    )


async def test_upload_screenshot_route_returns_429_when_upload_rate_limited(monkeypatch):
    """upload_screenshot route returns HTTP 429 + Retry-After when upload rate limit is exceeded."""
    from routers import screenshots

    monkeypatch.setattr(screenshots, "check_rate_limit", AsyncMock(return_value=(False, 900)))
    mock_upload = AsyncMock()
    monkeypatch.setattr(screenshots, "upload_image_to_s3", mock_upload)

    with pytest.raises(HTTPException) as exc_info:
        await screenshots.upload_screenshot(
            image=_make_upload_file(b"png", "image/png"),
            current_user={"userId": "uid-1"},
            db=MagicMock(),
        )

    assert exc_info.value.status_code == 429
    assert exc_info.value.headers == {"Retry-After": "900"}
    mock_upload.assert_not_awaited()


def test_get_client_ip_ignores_forwarded_headers_and_uses_client_host():
    """get_client_ip must trust request.client.host and ignore spoofable forwarded headers."""
    fake_request = MagicMock()
    fake_request.headers = {"x-forwarded-for": "1.2.3.4", "x-real-ip": "5.6.7.8"}
    fake_request.client = SimpleNamespace(host="198.51.100.42")

    assert api_services.get_client_ip(fake_request) == "198.51.100.42"

    no_client_request = MagicMock()
    no_client_request.headers = {"x-forwarded-for": "1.2.3.4"}
    no_client_request.client = None

    assert api_services.get_client_ip(no_client_request) == "unknown"


async def test_enrichment_logs_cache_hit_and_miss_durations(monkeypatch, caplog):
    """Geo and weather lookups log cache=hit/miss with duration_ms for CloudWatch queries."""
    mock_handler = MagicMock()
    mock_handler.getDetails = MagicMock(return_value=SimpleNamespace(all={"city": "Seoul"}))
    monkeypatch.setattr(api_services, "ipinfo_handler", mock_handler)
    monkeypatch.setattr(api_services.settings, "WEATHER_API_KEY", "test-weather-key")
    monkeypatch.setattr(api_services, "cache_set_json", AsyncMock())

    with caplog.at_level(logging.INFO, logger=api_services.__name__):
        monkeypatch.setattr(api_services, "cache_get_json", AsyncMock(return_value=None))
        await api_services.get_location_from_ip("8.8.8.8")

        monkeypatch.setattr(api_services, "cache_get_json", AsyncMock(return_value={"city": "Seoul"}))
        await api_services.get_location_from_ip("8.8.8.8")

        monkeypatch.setattr(
            api_services,
            "cache_get_json",
            AsyncMock(return_value={"weather": "clear sky", "temperature": 21.0}),
        )
        await api_services.get_weather_from_coordinates(37.56, 126.97)

    assert "Geo lookup cache=miss duration_ms=" in caplog.text
    assert "Geo lookup cache=hit duration_ms=" in caplog.text
    assert "Weather lookup cache=hit duration_ms=" in caplog.text
