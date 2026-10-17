"""
SMS Service — отправка SMS через SMS.ru или заглушка.

Отправка никогда не выбрасывает исключения наружу: сбой провайдера
возвращается как ``{"ok": False, "error": ...}`` и не ломает сценарий записи.
"""

import re

import httpx

from app.core.config import settings

SMSRU_SEND_URL = "https://sms.ru/sms/send"
SMSRU_TIMEOUT_SECONDS = 10.0


def normalize_phone(phone: str | None) -> str:
    """Привести номер к формату SMS.ru: 11 цифр без «+», например 79991112233.

    Понимает «+7 (999) 111-22-33», «8 999 111 22 33», «9991112233».
    Если номер не приводится к 11 цифрам с кодом страны 7 — пустая строка.
    """
    digits = re.sub(r"\D", "", phone or "")
    if len(digits) == 10:
        digits = "7" + digits
    elif len(digits) == 11 and digits.startswith("8"):
        digits = "7" + digits[1:]
    return digits if len(digits) == 11 and digits.startswith("7") else ""


async def send_sms(phone: str, message: str) -> dict:
    """Отправить SMS.

    Поддерживает:
    - smsru — SMS.ru API
    - stub — заглушка для тестов (печатает в консоль)
    """
    to = normalize_phone(phone)
    if not to:
        print(f"[SMS] Некорректный номер: {phone!r}")
        return {"ok": False, "error": f"Некорректный номер телефона: {phone}"}

    if settings.SMS_PROVIDER == "stub" or not settings.SMS_API_KEY:
        print(f"[SMS STUB] To: {to}, Message: {message}")
        return {"ok": True, "provider": "stub"}

    if settings.SMS_PROVIDER == "smsru":
        return await _send_smsru(to, message)

    print(f"[SMS UNKNOWN PROVIDER: {settings.SMS_PROVIDER}] To: {to}")
    return {"ok": False, "error": f"Unknown provider: {settings.SMS_PROVIDER}"}


async def _send_smsru(phone: str, message: str) -> dict:
    """Отправить SMS через SMS.ru. Ошибки сети и ответа API — в результате, без исключений."""
    payload = {
        "api_id": settings.SMS_API_KEY,
        "to": phone,
        "msg": message,
        "from": settings.SMS_SENDER,
        "json": 1,
    }
    try:
        async with httpx.AsyncClient(timeout=SMSRU_TIMEOUT_SECONDS) as client:
            response = await client.post(SMSRU_SEND_URL, data=payload)
    except httpx.TimeoutException:
        print(f"[SMS] SMS.ru timeout: {phone}")
        return {"ok": False, "provider": "smsru", "error": "Таймаут ответа SMS.ru"}
    except httpx.HTTPError as exc:
        print(f"[SMS] SMS.ru HTTP error: {exc}")
        return {"ok": False, "provider": "smsru", "error": f"Ошибка сети: {exc}"}

    if response.status_code != 200:
        print(f"[SMS] SMS.ru HTTP {response.status_code}")
        return {"ok": False, "provider": "smsru", "error": f"HTTP {response.status_code}"}

    try:
        data = response.json()
    except ValueError:
        print("[SMS] SMS.ru вернул не-JSON")
        return {"ok": False, "provider": "smsru", "error": "Некорректный ответ SMS.ru"}

    if not isinstance(data, dict) or data.get("status") != "OK":
        error = data.get("status_text") if isinstance(data, dict) else None
        status_code = data.get("status_code") if isinstance(data, dict) else None
        print(f"[SMS] SMS.ru error: {error or status_code}")
        return {
            "ok": False,
            "provider": "smsru",
            "error": error or f"Код {status_code}",
            "status_code": status_code,
        }

    sms = (data.get("sms") or {}).get(phone) or {}
    if sms.get("status") != "OK":
        print(f"[SMS] SMS.ru error: {sms.get('status_text') or sms.get('status_code')}")
        return {
            "ok": False,
            "provider": "smsru",
            "error": sms.get("status_text") or f"Код {sms.get('status_code')}",
            "status_code": sms.get("status_code"),
        }

    return {
        "ok": True,
        "provider": "smsru",
        "sms_id": sms.get("sms_id"),
        "status_code": data.get("status_code"),
    }
