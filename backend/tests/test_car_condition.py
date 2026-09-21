"""Тесты состояния авто для мастера: профиль авто + снимок на визит."""

from datetime import datetime, timedelta, timezone

import pytest


async def _make_appt(db_session, tenant, client_user, master_user, car, service):
    from app.models import Appointment

    appt = Appointment(
        client_id=client_user.id,
        master_id=master_user.id,
        tenant_id=tenant.id,
        car_id=car.id,
        service_id=service.id,
        start_time=datetime.now(timezone.utc) + timedelta(hours=2),
        end_time=datetime.now(timezone.utc) + timedelta(hours=4),
        total_price=5000,
        status="confirmed",
    )
    db_session.add(appt)
    await db_session.commit()
    await db_session.refresh(appt)
    return appt


async def _foreign_headers(db_session, tenant, phone="+79990000001"):
    from app.core.auth import create_token, hash_password
    from app.models import User

    other = User(
        phone=phone,
        password=hash_password("x"),
        full_name="Чужой Клиент",
        role="client",
        tenant_id=tenant.id,
    )
    db_session.add(other)
    await db_session.commit()
    await db_session.refresh(other)
    return {"Authorization": f"Bearer {create_token(other.id, str(other.tenant_id))}"}


class TestConditionCatalog:
    async def test_catalog(self, client, auth_headers):
        """✅ Справочники состояния авто доступны."""
        r = await client.get("/api/cars/condition-catalog", headers=auth_headers)
        assert r.status_code == 200
        data = r.json()
        assert {i["id"] for i in data["paint_types"]} >= {"lacquer", "ceramic", "film"}
        assert {i["id"] for i in data["glass_defects"]} == {"chips", "cracks"}
        assert any(i["id"] == "soft_wash" for i in data["care_requirements"])


class TestCarCondition:
    async def test_owner_sets_condition(self, client, auth_headers, test_car):
        """✅ Владелец задаёт состояние; неизвестные id отбрасываются."""
        r = await client.put(
            f"/api/cars/{test_car.id}/condition",
            json={
                "paint_type": "ceramic",
                "glass_defects": ["chips", "bogus"],
                "care_requirements": ["soft_wash", "zzz"],
                "notes": "скол на лобовом слева",
            },
            headers=auth_headers,
        )
        assert r.status_code == 200
        data = r.json()
        assert data["paint_type"] == "ceramic"
        assert data["glass_defects"] == ["chips"]
        assert data["care_requirements"] == ["soft_wash"]
        assert data["condition_notes"] == "скол на лобовом слева"

        card = await client.get(f"/api/cars/{test_car.id}", headers=auth_headers)
        assert card.status_code == 200
        assert card.json()["paint_type"] == "ceramic"
        assert card.json()["glass_defects"] == ["chips"]

    async def test_master_sets_condition(self, client, master_headers, test_car):
        """✅ Мастер тоже может дополнить состояние авто."""
        r = await client.put(
            f"/api/cars/{test_car.id}/condition",
            json={"paint_type": "film", "glass_defects": ["cracks"]},
            headers=master_headers,
        )
        assert r.status_code == 200
        assert r.json()["glass_defects"] == ["cracks"]

    async def test_foreign_client_forbidden(
        self, client, db_session, default_tenant, test_car
    ):
        """✅ Чужой клиент не может править состояние авто."""
        headers = await _foreign_headers(db_session, default_tenant)
        r = await client.put(
            f"/api/cars/{test_car.id}/condition",
            json={"paint_type": "lacquer"},
            headers=headers,
        )
        assert r.status_code == 404


class TestAppointmentCarCondition:
    async def test_snapshot_overrides_profile(
        self, client, db_session, default_tenant, test_user, test_master,
        test_car, test_service, auth_headers, master_headers,
    ):
        """✅ Снимок на визит перекрывает профиль авто и виден мастеру в brief."""
        await client.put(
            f"/api/cars/{test_car.id}/condition",
            json={"paint_type": "lacquer", "glass_defects": ["chips"]},
            headers=auth_headers,
        )
        appt = await _make_appt(
            db_session, default_tenant, test_user, test_master, test_car, test_service
        )

        # до снимка показывается профиль авто
        r = await client.get(f"/api/appointments/{appt.id}", headers=auth_headers)
        assert r.json()["car"]["paint_type"] == "lacquer"
        assert r.json()["car"]["glass_defects"] == ["chips"]

        # снимок на визит перекрывает профиль
        r = await client.put(
            f"/api/appointments/{appt.id}/car-condition",
            json={"paint_type": "ceramic", "glass_defects": ["cracks"], "notes": "новый скол"},
            headers=auth_headers,
        )
        assert r.status_code == 200
        assert r.json()["car"]["paint_type"] == "ceramic"
        assert r.json()["car"]["glass_defects"] == ["cracks"]

        # мастер видит снимок в сводке
        r = await client.get(
            f"/api/masters/me/appointments/{appt.id}/detailer-brief", headers=master_headers
        )
        assert r.status_code == 200
        assert r.json()["car_condition"]["paint_type"] == "ceramic"
        assert r.json()["car_condition"]["glass_defects"] == ["cracks"]

    async def test_foreign_client_forbidden(
        self, client, db_session, default_tenant, test_user, test_master,
        test_car, test_service, auth_headers,
    ):
        """✅ Чужой клиент не может задать снимок на чужой визит."""
        appt = await _make_appt(
            db_session, default_tenant, test_user, test_master, test_car, test_service
        )
        headers = await _foreign_headers(db_session, default_tenant, phone="+79990000002")
        r = await client.put(
            f"/api/appointments/{appt.id}/car-condition",
            json={"paint_type": "film"},
            headers=headers,
        )
        assert r.status_code == 403
