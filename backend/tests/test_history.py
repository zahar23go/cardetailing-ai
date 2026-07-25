"""Тесты истории изменений записей."""

import pytest
from datetime import datetime, timezone, timedelta
from httpx import AsyncClient


class TestHistory:
    """Тесты для AppointmentHistory."""

    async def test_log_create(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Логирование создания записи."""
        from app.services.history_service import log_create
        from app.models import Appointment

        appt = Appointment(
            client_id=test_user.id, tenant_id=default_tenant.id,
            car_id=test_car.id, service_id=test_service.id,
            start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc),
            total_price=5000, status="pending",
        )
        db_session.add(appt)
        await db_session.commit()

        await log_create(db_session, appt, test_user.id)

        from app.models import AppointmentHistory
        result = await db_session.execute(
            AppointmentHistory.__table__.select().where(
                AppointmentHistory.appointment_id == appt.id
            )
        )
        entries = result.fetchall()
        assert len(entries) == 1
        assert entries[0].change_type == "create"

    async def test_log_status_change(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Логирование смены статуса."""
        from app.services.history_service import log_status_change

        await log_status_change(db_session, 1, "pending", "completed", test_user.id)

        from app.models import AppointmentHistory
        result = await db_session.execute(
            AppointmentHistory.__table__.select().where(
                AppointmentHistory.appointment_id == 1,
                AppointmentHistory.change_type == "status_change",
            )
        )
        entries = result.fetchall()
        assert len(entries) >= 1

    async def test_log_cancel(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Логирование отмены."""
        from app.services.history_service import log_cancel
        from app.models import Appointment

        appt = Appointment(
            client_id=test_user.id, tenant_id=default_tenant.id,
            car_id=test_car.id, service_id=test_service.id,
            start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc),
            total_price=5000, status="pending",
        )
        db_session.add(appt)
        await db_session.commit()

        await log_cancel(db_session, appt, test_user.id)

        from app.models import AppointmentHistory
        result = await db_session.execute(
            AppointmentHistory.__table__.select().where(
                AppointmentHistory.appointment_id == appt.id
            )
        )
        entries = result.fetchall()
        assert len(entries) >= 1

    async def test_log_move(self, db_session, default_tenant, test_user):
        """✅ Логирование переноса."""
        from app.services.history_service import log_move

        await log_move(db_session, 1, "2026-01-01T10:00", "2026-01-01T14:00", test_user.id)

        from app.models import AppointmentHistory
        result = await db_session.execute(
            AppointmentHistory.__table__.select().where(
                AppointmentHistory.appointment_id == 1,
                AppointmentHistory.change_type == "move",
            )
        )
        entries = result.fetchall()
        assert len(entries) >= 1

    async def test_get_history(self, db_session, default_tenant, test_user, test_service, test_car):
        """✅ Получение истории с пагинацией."""
        from app.services.history_service import log_create, get_history
        from app.models import Appointment

        appt = Appointment(
            client_id=test_user.id, tenant_id=default_tenant.id,
            car_id=test_car.id, service_id=test_service.id,
            start_time=datetime.now(timezone.utc), end_time=datetime.now(timezone.utc),
            total_price=5000, status="pending",
        )
        db_session.add(appt)
        await db_session.commit()
        await log_create(db_session, appt, test_user.id)

        items, total = await get_history(db_session, appt.id, skip=0, limit=50)
        assert total >= 1
        assert len(items) >= 1

    async def test_history_endpoint(
        self, client, auth_headers, test_service, test_car,
    ):
        """✅ Эндпоинт истории возвращает корректный ответ."""
        # Создаём запись
        start = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        create_resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        appt_id = create_resp.json()["id"]

        # Получаем историю
        resp = await client.get(
            f"/api/appointments/{appt_id}/history",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert "items" in data
        assert "total" in data

    async def test_history_filter_by_type(
        self, client, auth_headers, test_service, test_car,
    ):
        """✅ Фильтрация истории по типу изменения."""
        start = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        create_resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        appt_id = create_resp.json()["id"]

        resp = await client.get(
            f"/api/appointments/{appt_id}/history?change_type=create",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1

    async def test_history_detail_endpoint(
        self,
        client,
        auth_headers,
        test_service,
        test_car,
    ):
        """✅ Эндпоинт деталей истории возвращает корректные данные."""
        # Создаём запись (автоматически логируется create)
        start = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        create_resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200
        appt_id = create_resp.json()["id"]

        # Получаем список истории, чтобы найти ID записи истории
        history_resp = await client.get(
            f"/api/appointments/{appt_id}/history",
            headers=auth_headers,
        )
        assert history_resp.status_code == 200
        history_data = history_resp.json()
        assert history_data["total"] >= 1
        history_id = history_data["items"][0]["id"]

        # Детали истории
        resp = await client.get(
            f"/api/appointments/{appt_id}/history/{history_id}",
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["id"] == history_id
        assert data["appointment_id"] == appt_id
        assert data["change_type"] == "create"
        assert data["changed_by"] is not None
        assert "full_name" in data["changed_by"]

    async def test_history_detail_not_found(
        self,
        client,
        auth_headers,
    ):
        """❌ Несуществующая запись истории возвращает 404."""
        resp = await client.get(
            "/api/appointments/99999/history/99999",
            headers=auth_headers,
        )
        assert resp.status_code == 404
