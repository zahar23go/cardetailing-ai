"""
Тесты уведомлений.

Проверяют создание, прочтение, настройки, отправку, webhook.
"""

import pytest
from httpx import AsyncClient
from datetime import datetime, timezone, timedelta


class TestNotifications:
    """Набор тестов для эндпоинтов уведомлений."""

    # ------------------------------------------------------------------
    # 1. Создание уведомления (через сервис)
    # ------------------------------------------------------------------
    async def test_create_notification(self, db_session, default_tenant, test_user):
        """✅ Создание уведомления через сервис."""
        from app.core.notification_service import create_notification

        notif = await create_notification(
            db_session, test_user.id, default_tenant.id,
            title="Тест", message="Тестовое уведомление",
            type="info",
        )
        assert notif.id is not None
        assert notif.title == "Тест"
        assert notif.is_read is False

    # ------------------------------------------------------------------
    # 2. Отметить уведомление как прочитанное
    # ------------------------------------------------------------------
    async def test_mark_as_read(self, db_session, default_tenant, test_user):
        """✅ Отметка уведомления как прочитанного."""
        from app.core.notification_service import create_notification, mark_as_read

        notif = await create_notification(
            db_session, test_user.id, default_tenant.id,
            title="Тест", message="Тест",
        )
        ok = await mark_as_read(db_session, notif.id, test_user.id)
        assert ok is True

        # Проверяем
        assert notif.is_read is True

    # ------------------------------------------------------------------
    # 3. Получение непрочитанных
    # ------------------------------------------------------------------
    async def test_unread_count(self, client: AsyncClient, auth_headers: dict):
        """✅ Получение количества непрочитанных уведомлений."""
        response = await client.get("/api/notifications/unread-count", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "count" in data

    # ------------------------------------------------------------------
    # 4. Настройки уведомлений (получение + обновление)
    # ------------------------------------------------------------------
    async def test_notification_settings(self, client: AsyncClient, auth_headers: dict):
        """✅ Получение и обновление настроек уведомлений."""
        # Получение
        response = await client.get("/api/notifications/settings", headers=auth_headers)
        assert response.status_code == 200
        data = response.json()
        assert "telegram_enabled" in data

        # Обновление
        response = await client.put(
            "/api/notifications/settings",
            json={"sms_enabled": True, "sms_phone": "+79991112233"},
            headers=auth_headers,
        )
        assert response.status_code == 200
        data = response.json()
        assert data["sms_enabled"] is True

    # ------------------------------------------------------------------
    # 5. Отправка SMS (stub)
    # ------------------------------------------------------------------
    async def test_send_sms_stub(self):
        """✅ Отправка SMS через заглушку."""
        from app.core.sms_service import send_sms

        result = await send_sms("+79991112233", "Тестовое SMS")
        assert result["ok"] is True
        assert result["provider"] == "stub"

    # ------------------------------------------------------------------
    # 6. Telegram webhook (команда /start)
    # ------------------------------------------------------------------
    async def test_telegram_webhook_start(self, client: AsyncClient):
        """✅ Обработка команды /start от Telegram."""
        response = await client.post(
            "/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 12345},
                    "text": "/start",
                }
            },
        )
        assert response.status_code == 200

    # ------------------------------------------------------------------
    # 7. Telegram webhook (неизвестная команда)
    # ------------------------------------------------------------------
    async def test_telegram_webhook_unknown(self, client: AsyncClient):
        """✅ Обработка неизвестной команды."""
        response = await client.post(
            "/api/telegram/webhook",
            json={
                "message": {
                    "chat": {"id": 12345},
                    "text": "/unknown_command",
                }
            },
        )
        assert response.status_code == 200

    # ------------------------------------------------------------------
    # 8. Напоминания о записях
    # ------------------------------------------------------------------
    @staticmethod
    def _appt(tenant, user, car, service, hours_ahead, status="confirmed"):
        from app.models import Appointment

        return Appointment(
            client_id=user.id,
            tenant_id=tenant.id,
            car_id=car.id,
            service_id=service.id,
            start_time=datetime.now(timezone.utc) + timedelta(hours=hours_ahead),
            end_time=datetime.now(timezone.utc) + timedelta(hours=hours_ahead + 2),
            total_price=5000,
            status=status,
        )

    async def test_send_reminder_due(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ За час до визита напоминание отправляется (дефолт — 1 час)."""
        from app.core.notification_service import send_appointment_reminders

        db_session.add(self._appt(default_tenant, test_user, test_car, test_service, 0.5))
        await db_session.commit()

        assert await send_appointment_reminders(db_session) == 1

    async def test_send_reminder_not_due(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ За 3 часа при дефолте 1 час напоминание ещё не отправляется."""
        from app.core.notification_service import send_appointment_reminders

        db_session.add(self._appt(default_tenant, test_user, test_car, test_service, 3))
        await db_session.commit()

        assert await send_appointment_reminders(db_session) == 0

    async def test_send_reminder_not_duplicated(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Повторный прогон не дублирует напоминание по той же записи."""
        from app.core.notification_service import send_appointment_reminders

        db_session.add(self._appt(default_tenant, test_user, test_car, test_service, 0.5))
        await db_session.commit()

        assert await send_appointment_reminders(db_session) == 1
        assert await send_appointment_reminders(db_session) == 0

    async def test_send_reminder_respects_user_lead_time(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Личная настройка remind_hours_before меняет момент отправки."""
        from app.core.notification_service import send_appointment_reminders, upsert_settings

        await upsert_settings(db_session, test_user.id, remind_hours_before=4)
        db_session.add(self._appt(default_tenant, test_user, test_car, test_service, 3))
        await db_session.commit()

        assert await send_appointment_reminders(db_session) == 1

    async def test_send_reminder_opt_out(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Клиент отключил напоминания — уведомление не создаётся."""
        from app.core.notification_service import send_appointment_reminders, upsert_settings

        await upsert_settings(db_session, test_user.id, notify_appointment_reminder=False)
        db_session.add(self._appt(default_tenant, test_user, test_car, test_service, 0.5))
        await db_session.commit()

        assert await send_appointment_reminders(db_session) == 0
