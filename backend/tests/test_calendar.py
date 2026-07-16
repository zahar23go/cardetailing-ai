"""Тесты календаря мастера."""

from datetime import datetime, timezone, timedelta
from httpx import AsyncClient
from app.models import WorkingHours


class TestCalendar:
    """Тесты для календаря и рабочего графика."""

    async def test_working_hours_create(self, db_session, default_tenant, test_master):
        """✅ Создание рабочих часов мастера."""
        wh = WorkingHours(
            master_id=test_master.id,
            tenant_id=default_tenant.id,
            day_of_week=0,
            start_time="09:00",
            end_time="18:00",
            is_working_day=True,
        )
        db_session.add(wh)
        await db_session.commit()
        assert wh.id is not None

    async def test_master_calendar(
        self, client, admin_headers, test_master, test_service, test_car,
    ):
        """✅ Получение календаря мастера."""
        from app.models import WorkingHours, Appointment
        from app.core.database import Base
        from sqlalchemy import select

        # Получаем сессию через зависимость
        response = await client.get(
            f"/api/calendar/{test_master.id}?start_date=2026-01-01&end_date=2026-01-07",
            headers=admin_headers,
        )
        # Должен вернуть календарь (даже пустой)
        assert response.status_code == 200
        data = response.json()
        assert "days" in data
        assert "working_hours" in data

    async def test_move_appointment(
        self, client, auth_headers, admin_headers, test_service, test_car,
    ):
        """✅ Перенос записи (Drag & Drop)."""
        import urllib.parse
        # Создаём запись (клиентом, которому принадлежит машина)
        start = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
        create_resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert create_resp.status_code == 200, f"Create failed: {create_resp.text}"
        appt_id = create_resp.json()["id"]

        # Переносим (админом)
        new_time = (datetime.now(timezone.utc) + timedelta(days=5, hours=3)).isoformat()
        encoded_time = urllib.parse.quote(new_time)
        move_resp = await client.put(
            f"/api/appointments/{appt_id}/move?start_time={encoded_time}",
            headers=admin_headers,
        )
        assert move_resp.status_code == 200, f"Move failed: {move_resp.text}"
        assert move_resp.json()["appointment_id"] == appt_id

    async def test_working_hours_endpoint(
        self, client, admin_headers, default_tenant, test_master,
    ):
        """✅ Получение и обновление рабочих часов."""
        from app.models import WorkingHours

        # Сначала получаем (пустой список)
        resp = await client.get(
            f"/api/masters/working-hours?master_id={test_master.id}",
            headers=admin_headers,
        )
        assert resp.status_code == 200

        # Обновляем
        hours_data = [
            {"day_of_week": 0, "start_time": "09:00", "end_time": "18:00", "is_working_day": True},
            {"day_of_week": 1, "start_time": "09:00", "end_time": "18:00", "is_working_day": True},
            {"day_of_week": 2, "start_time": "09:00", "end_time": "18:00", "is_working_day": True},
            {"day_of_week": 3, "start_time": "09:00", "end_time": "18:00", "is_working_day": True},
            {"day_of_week": 4, "start_time": "09:00", "end_time": "18:00", "is_working_day": True},
            {"day_of_week": 5, "start_time": "10:00", "end_time": "16:00", "is_working_day": True},
            {"day_of_week": 6, "start_time": "00:00", "end_time": "00:00", "is_working_day": False},
        ]
        resp = await client.put(
            f"/api/masters/working-hours/{test_master.id}",
            json=hours_data,
            headers=admin_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 7
