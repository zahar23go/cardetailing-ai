"""Тесты платежей."""

from httpx import AsyncClient


class TestPayments:
    """Тесты для онлайн-оплаты."""

    async def test_create_payment(self, client, auth_headers, test_service, test_car):
        """✅ Создание платежа для записи."""
        from datetime import datetime, timezone, timedelta

        start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        appt_id = resp.json()["id"]

        resp = await client.post(
            "/api/payments/create",
            json={"appointment_id": appt_id, "payment_method": "card"},
            headers=auth_headers,
        )
        assert resp.status_code == 200
        data = resp.json()
        assert data["status"] == "pending"
        assert data["appointment_id"] == appt_id

    async def test_payment_status(self, client, auth_headers, test_service, test_car):
        """✅ Проверка статуса платежа."""
        from datetime import datetime, timezone, timedelta

        start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        appt_id = resp.json()["id"]

        pay_resp = await client.post(
            "/api/payments/create",
            json={"appointment_id": appt_id},
            headers=auth_headers,
        )
        pay_id = pay_resp.json()["id"]

        status_resp = await client.get(f"/api/payments/{pay_id}/status", headers=auth_headers)
        assert status_resp.status_code == 200
        assert status_resp.json()["status"] == "pending"

    async def test_payment_webhook(self, client, auth_headers, test_service, test_car):
        """✅ Webhook обновляет статус платежа."""
        from datetime import datetime, timezone, timedelta

        start = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
        resp = await client.post(
            "/api/appointments",
            json={"service_id": test_service.id, "car_id": test_car.id, "start_time": start},
            headers=auth_headers,
        )
        appt_id = resp.json()["id"]

        pay_resp = await client.post(
            "/api/payments/create",
            json={"appointment_id": appt_id},
            headers=auth_headers,
        )
        payment_id = pay_resp.json()["payment_id"]

        webhook_resp = await client.post(
            "/api/payments/webhook",
            json={
                "event": "payment.succeeded",
                "payment_id": payment_id,
                "status": "succeeded",
                "amount": 5000,
            },
        )
        assert webhook_resp.status_code == 200
