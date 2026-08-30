"""Карточка авто: VIN, фото, таймлайн. Не ломает CRUD и запись."""

from datetime import datetime, timezone, timedelta

from app.models import Appointment


class TestCarCard:
    async def test_list_still_works(self, client, auth_headers, test_car):
        resp = await client.get("/api/cars?skip=0&limit=50", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        items = resp.json()["items"]
        assert any(c["id"] == test_car.id for c in items)
        row = next(c for c in items if c["id"] == test_car.id)
        assert "vin" in row
        assert row["make"] == "BMW"

    async def test_card_empty_timeline(self, client, auth_headers, test_car):
        resp = await client.get(f"/api/cars/{test_car.id}", headers=auth_headers)
        assert resp.status_code == 200, resp.text
        data = resp.json()
        assert data["id"] == test_car.id
        assert data["photos"] == []
        assert data["timeline"] == []
        assert data["vin"] is None

    async def test_put_vin_and_specs(self, client, auth_headers, test_car):
        resp = await client.put(
            f"/api/cars/{test_car.id}",
            json={
                "vin": "wba 3a5c57ef12345",
                "body_type": "Кроссовер",
                "mileage": 42000,
            },
            headers=auth_headers,
        )
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["vin"] == "WBA3A5C57EF12345"
        assert body["body_type"] == "Кроссовер"
        assert body["mileage"] == 42000
        assert body["make"] == "BMW"

    async def test_bad_vin(self, client, auth_headers, test_car):
        resp = await client.put(
            f"/api/cars/{test_car.id}",
            json={"vin": "IOQ123"},
            headers=auth_headers,
        )
        assert resp.status_code == 422

    async def test_other_client_hidden(
        self, client, auth_headers, admin_headers, test_car,
    ):
        resp = await client.get(f"/api/cars/{test_car.id}", headers=admin_headers)
        assert resp.status_code == 200

    async def test_timeline_after_visit(
        self, client, admin_headers, auth_headers, test_service, test_car,
    ):
        start = (datetime.now(timezone.utc) - timedelta(hours=2)).isoformat()
        created = await client.post(
            "/api/appointments",
            json={
                "service_id": test_service.id,
                "car_id": test_car.id,
                "start_time": start,
            },
            headers=auth_headers,
        )
        assert created.status_code == 200, created.text
        appt_id = created.json()["id"]
        done = await client.put(
            f"/api/appointments/{appt_id}",
            json={"status": "completed"},
            headers=admin_headers,
        )
        assert done.status_code == 200, done.text

        card = await client.get(f"/api/cars/{test_car.id}", headers=auth_headers)
        assert card.status_code == 200
        timeline = card.json()["timeline"]
        assert len(timeline) >= 1
        assert timeline[0]["appointment_id"] == appt_id
        assert timeline[0]["status"] == "completed"
        assert timeline[0]["price"] == 5000.0

        booking = await client.get("/api/appointments/me?skip=0&limit=10", headers=auth_headers)
        assert booking.status_code == 200
        assert any(a["id"] == appt_id for a in booking.json()["items"])
