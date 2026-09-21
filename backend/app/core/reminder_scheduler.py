"""Фоновый планировщик напоминаний о визитах.

Раз в REMINDER_INTERVAL_MINUTES проверяет ближайшие записи и рассылает
напоминания клиентам (in-app + Telegram/SMS по настройкам).

Запускается из lifespan FastAPI; отдельного воркера/зависимости не требует.
"""
from __future__ import annotations

import asyncio
import contextlib

from app.core.config import settings
from app.core.database import async_session_maker
from app.core.notification_service import send_appointment_reminders

_task: asyncio.Task | None = None


async def _run_loop(interval_minutes: int) -> None:
    interval = max(1, interval_minutes) * 60
    while True:
        await asyncio.sleep(interval)
        try:
            async with async_session_maker() as db:
                sent = await send_appointment_reminders(db)
            if sent:
                print(f"[reminders] sent {sent}")
        except asyncio.CancelledError:
            raise
        except Exception as exc:  # воркер не должен падать от одной ошибки БД
            print(f"[reminders] error: {exc}")


def start_reminder_scheduler() -> None:
    """Запустить фоновую проверку напоминаний (идемпотентно)."""
    global _task
    if not settings.REMINDERS_ENABLED or _task is not None:
        return
    _task = asyncio.create_task(_run_loop(settings.REMINDER_INTERVAL_MINUTES))
    print(f"[reminders] scheduler started, interval {settings.REMINDER_INTERVAL_MINUTES} min")


async def stop_reminder_scheduler() -> None:
    """Остановить фоновую проверку напоминаний."""
    global _task
    if _task is None:
        return
    _task.cancel()
    with contextlib.suppress(asyncio.CancelledError):
        await _task
    _task = None
