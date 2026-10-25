"""152-ФЗ: право на забвение — обезличивание данных клиента."""
from datetime import datetime, timedelta, timezone

from httpx import AsyncClient
from sqlalchemy import func, select

from app.models import (
    AiChatLog,
    Appointment,
    DetailerInspection,
    LoyaltyPoints,
    Notification,
    User,
)


async def _seed_client_data(db_session, tenant_id, user_id, car_id, service_id):
    now = datetime.now(timezone.utc)
    db_session.add(
        Appointment(
            tenant_id=tenant_id,
            client_id=user_id,
            car_id=car_id,
            service_id=service_id,
            start_time=now - timedelta(days=1),
            end_time=now - timedelta(days=1) + timedelta(hours=1),
            status="completed",
            total_price=5000,
            client_notes="Позвонить заранее",
            master_brief="Клиент просил не мыть двигатель",
        )
    )
    db_session.add(
        Notification(
            tenant_id=tenant_id,
            user_id=user_id,
            title="Напоминание",
            message="Завтра в 10:00",
        )
    )
    db_session.add(LoyaltyPoints(tenant_id=tenant_id, client_id=user_id, balance=120))
    db_session.add(
        AiChatLog(
            tenant_id=tenant_id,
            user_id=user_id,
            session_id="s-1",
            assistant="detailer",
            question="Сколько стоит полировка?",
            answer="От 5000 ₽",
            tool_calls=[],
        )
    )
    db_session.add(
        DetailerInspection(
            tenant_id=tenant_id,
            client_id=user_id,
            tags=[],
            findings=[],
            upsells=[],
            slots=[],
            photo_ids=[],
        )
    )
    await db_session.commit()


class TestRightToBeForgotten:
    async def test_client_deletes_own_data(
        self,
        client: AsyncClient,
        auth_headers: dict,
        db_session,
        test_user,
        test_car,
        test_service,
        default_tenant,
    ):
        old_phone = test_user.phone
        await _seed_client_data(
            db_session, default_tenant.id, test_user.id, test_car.id, test_service.id
        )

        resp = await client.delete("/api/me", headers=auth_headers)
        assert resp.status_code == 204, resp.text

        user = (
            await db_session.execute(select(User).where(User.id == test_user.id))
        ).scalar_one()
        await db_session.refresh(user)
        assert user.anonymized_at is not None
        assert user.phone != old_phone
        assert user.phone.startswith("del")
        assert user.full_name == "Удалённый клиент"

        await db_session.refresh(test_car)
        assert test_car.license_plate is None
        assert test_car.vin is None

        for model, column in (
            (Notification, Notification.user_id),
            (LoyaltyPoints, LoyaltyPoints.client_id),
            (AiChatLog, AiChatLog.user_id),
            (DetailerInspection, DetailerInspection.client_id),
        ):
            count = (
                await db_session.execute(
                    select(func.count()).select_from(model).where(column == test_user.id)
                )
            ).scalar()
            assert count == 0, model.__name__

        appt = (
            await db_session.execute(
                select(Appointment).where(Appointment.client_id == test_user.id)
            )
        ).scalar_one()
        assert appt.client_notes is None
        assert appt.master_brief is None

        # Старые учётные данные больше не работают.
        login = await client.post(
            "/api/login", json={"phone": old_phone, "password": "testpass123"}
        )
        assert login.status_code == 401

        # Повторный запрос идемпотентен.
        again = await client.delete("/api/me", headers=auth_headers)
        assert again.status_code == 204

    async def test_admin_cannot_delete_self_via_client_endpoint(
        self, client: AsyncClient, admin_headers: dict
    ):
        resp = await client.delete("/api/me", headers=admin_headers)
        assert resp.status_code == 400
        assert "клиентскому" in resp.json()["detail"]

    async def test_requires_auth(self, client: AsyncClient):
        resp = await client.delete("/api/me")
        assert resp.status_code == 403
