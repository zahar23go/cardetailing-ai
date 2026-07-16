"""
SMS Service — отправка SMS через SMS.ru или заглушка.
"""

import httpx

from app.core.config import settings


async def send_sms(phone: str, message: str) -> dict:
    """Отправить SMS.

    Поддерживает:
    - smsru — SMS.ru API
    - stub — заглушка для тестов (печатает в консоль)
    """
    if settings.SMS_PROVIDER == "stub" or not settings.SMS_API_KEY:
        print(f"[SMS STUB] To: {phone}, Message: {message}")
        return {"ok": True, "provider": "stub"}

    if settings.SMS_PROVIDER == "smsru":
        return await _send_smsru(phone, message)

    print(f"[SMS UNKNOWN PROVIDER: {settings.SMS_PROVIDER}] To: {phone}")
    return {"ok": False, "error": f"Unknown provider: {settings.SMS_PROVIDER}"}


async def _send_smsru(phone: str, message: str) -> dict:
    """Отправить SMS через SMS.ru."""
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://sms.ru/sms/send",
            data={
                "api_id": settings.SMS_API_KEY,
                "to": phone,
                "msg": message,
                "from": settings.SMS_SENDER,
                "json": 1,
            },
        )
        return response.json()
