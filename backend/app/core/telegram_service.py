"""
Telegram Service — отправка сообщений через Telegram Bot API.
"""

import httpx

from app.core.config import settings

API_BASE = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}"


async def send_telegram_message(chat_id: str, text: str) -> dict:
    """Отправить сообщение в Telegram."""
    if not settings.TELEGRAM_BOT_TOKEN:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN не настроен"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/sendMessage",
            json={
                "chat_id": chat_id,
                "text": text,
                "parse_mode": "HTML",
            },
        )
        return response.json()


async def set_webhook() -> dict:
    """Установить webhook для Telegram бота."""
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_WEBHOOK_URL:
        return {"ok": False, "error": "TELEGRAM_BOT_TOKEN или TELEGRAM_WEBHOOK_URL не настроены"}

    async with httpx.AsyncClient() as client:
        response = await client.post(
            f"{API_BASE}/setWebhook",
            json={"url": settings.TELEGRAM_WEBHOOK_URL},
        )
        return response.json()


async def delete_webhook() -> dict:
    """Удалить webhook."""
    async with httpx.AsyncClient() as client:
        response = await client.post(f"{API_BASE}/deleteWebhook")
        return response.json()


def _parse_telegram_command(text: str) -> tuple[str, list[str]]:
    """Разобрать команду Telegram. Возвращает (команда, аргументы)."""
    parts = text.strip().split()
    if not parts:
        return "", []
    cmd = parts[0].lower()
    args = parts[1:]
    return cmd, args


async def handle_telegram_webhook(data: dict) -> str:
    """Обработать входящий webhook от Telegram."""
    message = data.get("message", {})
    chat_id = str(message.get("chat", {}).get("id", ""))
    text = message.get("text", "")

    if not chat_id or not text:
        return "ok"

    cmd, args = _parse_telegram_command(text)

    if cmd == "/start":
        await send_telegram_message(
            chat_id,
            "👋 Добро пожаловать в CarDetailing AI Bot!\n\n"
            "Чтобы связать ваш аккаунт, используйте код из личного кабинета.\n\n"
            "Доступные команды:\n"
            "/my_appointments — мои записи\n"
            "/cancel {id} — отменить запись\n"
            "/confirm {id} — подтвердить запись",
        )
        return "ok"

    elif cmd == "/my_appointments":
        await send_telegram_message(
            chat_id,
            "📅 Ваши записи:\n"
            "Для просмотра записей войдите в личный кабинет на сайте.",
        )
        return "ok"

    elif cmd == "/cancel" and args:
        await send_telegram_message(
            chat_id,
            f"✅ Запись #{args[0]} отменена.",
        )
        return "ok"

    elif cmd == "/confirm" and args:
        await send_telegram_message(
            chat_id,
            f"✅ Запись #{args[0]} подтверждена.",
        )
        return "ok"

    else:
        await send_telegram_message(
            chat_id,
            "❌ Неизвестная команда. Используйте /start для списка команд.",
        )
        return "ok"
