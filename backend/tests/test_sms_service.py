"""Тесты SMS-сервиса: нормализация номера и устойчивость к сбоям SMS.ru."""

import httpx
import pytest

from app.core import sms_service
from app.core.config import settings


def test_normalize_phone_variants():
    assert sms_service.normalize_phone("+7 (999) 111-22-33") == "79991112233"
    assert sms_service.normalize_phone("8 999 111 22 33") == "79991112233"
    assert sms_service.normalize_phone("9991112233") == "79991112233"
    assert sms_service.normalize_phone("79991112233") == "79991112233"
    assert sms_service.normalize_phone("") == ""
    assert sms_service.normalize_phone(None) == ""
    assert sms_service.normalize_phone("12345") == ""


class _FakeResponse:
    def __init__(self, payload=None, status_code=200, json_error=False):
        self._payload = payload
        self.status_code = status_code
        self._json_error = json_error

    def json(self):
        if self._json_error:
            raise ValueError("not json")
        return self._payload


class _FakeClient:
    def __init__(self, response=None, exc=None):
        self._response = response
        self._exc = exc
        self.sent_data = None

    async def __aenter__(self):
        return self

    async def __aexit__(self, *exc_info):
        return False

    async def post(self, url, data=None):
        self.sent_data = data
        if self._exc:
            raise self._exc
        return self._response


@pytest.fixture
def smsru_settings(monkeypatch):
    monkeypatch.setattr(settings, "SMS_PROVIDER", "smsru")
    monkeypatch.setattr(settings, "SMS_API_KEY", "test-api-id")
    monkeypatch.setattr(settings, "SMS_SENDER", "CarDetailing")


def _patch_client(monkeypatch, client):
    monkeypatch.setattr(sms_service.httpx, "AsyncClient", lambda **kwargs: client)
    return client


async def test_smsru_success_normalizes_phone(monkeypatch, smsru_settings):
    client = _patch_client(
        monkeypatch,
        _FakeClient(
            _FakeResponse(
                {
                    "status": "OK",
                    "status_code": 100,
                    "sms": {"79991112233": {"status": "OK", "status_code": 100, "sms_id": "abc"}},
                }
            )
        ),
    )

    result = await sms_service.send_sms("+7 (999) 111-22-33", "Тест")

    assert result["ok"] is True
    assert result["sms_id"] == "abc"
    assert client.sent_data["to"] == "79991112233"


async def test_smsru_api_error_does_not_raise(monkeypatch, smsru_settings):
    _patch_client(
        monkeypatch,
        _FakeClient(
            _FakeResponse({"status": "ERROR", "status_code": 201, "status_text": "Недостаточно средств"})
        ),
    )

    result = await sms_service.send_sms("+79991112233", "Тест")

    assert result["ok"] is False
    assert result["error"] == "Недостаточно средств"


async def test_smsru_recipient_error(monkeypatch, smsru_settings):
    _patch_client(
        monkeypatch,
        _FakeClient(
            _FakeResponse(
                {
                    "status": "OK",
                    "status_code": 100,
                    "sms": {"79991112233": {"status": "ERROR", "status_code": 202, "status_text": "Номер в стоп-листе"}},
                }
            )
        ),
    )

    result = await sms_service.send_sms("+79991112233", "Тест")

    assert result["ok"] is False
    assert result["error"] == "Номер в стоп-листе"


async def test_smsru_timeout_does_not_raise(monkeypatch, smsru_settings):
    _patch_client(monkeypatch, _FakeClient(exc=httpx.TimeoutException("timeout")))

    result = await sms_service.send_sms("+79991112233", "Тест")

    assert result["ok"] is False
    assert "Таймаут" in result["error"]


async def test_smsru_http_error_does_not_raise(monkeypatch, smsru_settings):
    _patch_client(monkeypatch, _FakeClient(_FakeResponse(status_code=500)))

    result = await sms_service.send_sms("+79991112233", "Тест")

    assert result["ok"] is False
    assert result["error"] == "HTTP 500"


async def test_smsru_invalid_json_does_not_raise(monkeypatch, smsru_settings):
    _patch_client(monkeypatch, _FakeClient(_FakeResponse(json_error=True)))

    result = await sms_service.send_sms("+79991112233", "Тест")

    assert result["ok"] is False


async def test_invalid_phone_skips_provider(monkeypatch, smsru_settings):
    client = _patch_client(monkeypatch, _FakeClient(_FakeResponse({})))

    result = await sms_service.send_sms("123", "Тест")

    assert result["ok"] is False
    assert client.sent_data is None
