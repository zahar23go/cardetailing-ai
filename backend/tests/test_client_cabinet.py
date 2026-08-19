"""Клиентский кабинет: мастера, активные скидки, профиль, e2e 6 страниц."""

from unittest.mock import AsyncMock, patch

from httpx import AsyncClient

from app.models import User

CLIENT_PAGES = [
    "/client",
    "/client/booking",
    "/client/portfolio",
    "/client/chat",
    "/client/discounts",
    "/client/settings",
]


class TestClientMasters:
    async def test_list_masters(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_master: User,
    ):
        """✅ GET /api/masters возвращает мастеров салона клиенту."""
        resp = await client.get("/api/masters", headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["total"] >= 1
        names = [m["full_name"] for m in data["items"]]
        assert test_master.full_name in names
        assert all("id" in m and "full_name" in m for m in data["items"])

    async def test_masters_unauthorized(self, client: AsyncClient):
        """❌ Без токена /api/masters недоступен."""
        resp = await client.get("/api/masters")
        assert resp.status_code in (401, 403)


class TestClientDiscountsActive:
    async def test_active_discounts_for_client(
        self,
        client: AsyncClient,
        auth_headers: dict,
        admin_headers: dict,
    ):
        """✅ GET /api/discounts/active отдаёт только активные скидки клиенту."""
        created = await client.post("/api/discounts", json={
            "name": "Клиентская акция",
            "type": "happy_hours",
            "conditions": {},
            "discount_percent": 15,
            "slot_start": "10:00",
            "slot_end": "14:00",
            "is_active": True,
        }, headers=admin_headers)
        assert created.status_code == 200, created.text

        await client.post("/api/discounts", json={
            "name": "Выключенная акция",
            "type": "service",
            "conditions": {},
            "discount_percent": 5,
            "is_active": False,
        }, headers=admin_headers)

        resp = await client.get("/api/discounts/active", headers=auth_headers)
        assert resp.status_code == 200
        names = [r["name"] for r in resp.json()["items"]]
        assert "Клиентская акция" in names
        assert "Выключенная акция" not in names

    async def test_active_discounts_unauthorized(self, client: AsyncClient):
        resp = await client.get("/api/discounts/active")
        assert resp.status_code in (401, 403)


class TestClientProfileCars:
    async def test_update_phone(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user: User,
    ):
        """✅ PUT /api/me меняет телефон."""
        resp = await client.put("/api/me", json={
            "full_name": test_user.full_name,
            "phone": "+79990001122",
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        assert resp.json()["phone"] == "+79990001122"

    async def test_update_car(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_car,
    ):
        """✅ PUT /api/cars/{id} обновляет автомобиль клиента."""
        resp = await client.put(f"/api/cars/{test_car.id}", json={
            "make": "Audi",
            "model": "A6",
            "color": "Белый",
        }, headers=auth_headers)
        assert resp.status_code == 200, resp.text
        body = resp.json()
        assert body["make"] == "Audi"
        assert body["model"] == "A6"
        assert body["color"] == "Белый"


class TestClientCabinetE2E:
    """Логин клиентом → API каждой из 6 страниц кабинета."""

    async def test_login_then_open_six_pages(
        self,
        client: AsyncClient,
        test_user: User,
        test_master: User,
        test_service,
        test_car,
        admin_headers: dict,
    ):
        login = await client.post("/api/login", json={
            "phone": test_user.phone,
            "password": "testpass123",
        })
        assert login.status_code == 200, login.text
        token = login.json()["token"]
        headers = {"Authorization": f"Bearer {token}"}

        # Соответствие URL кабинета → запросы, которые страница делает при открытии
        page_calls = {
            "/client": [
                ("GET", "/api/appointments/me?skip=0&limit=50"),
                ("GET", "/api/services?skip=0&limit=200"),
            ],
            "/client/booking": [
                ("GET", "/api/services?skip=0&limit=200"),
                ("GET", "/api/masters"),
                ("GET", "/api/cars?skip=0&limit=50"),
            ],
            "/client/portfolio": [
                ("GET", "/api/portfolio"),
                ("GET", "/api/portfolio/services"),
            ],
            "/client/chat": [
                ("GET", "/api/services?skip=0&limit=200"),
            ],
            "/client/discounts": [
                ("GET", "/api/discounts/active"),
            ],
            "/client/settings": [
                ("GET", "/api/me"),
                ("GET", "/api/cars?skip=0&limit=50"),
                ("GET", "/api/appointments/me?skip=0&limit=50"),
            ],
        }
        assert list(page_calls.keys()) == CLIENT_PAGES

        fake_ai = f"Рекомендуем {test_service.name}. Можете записаться."
        with patch(
            "app.main.get_consultant_response",
            new_callable=AsyncMock,
            return_value=fake_ai,
        ):
            for path in CLIENT_PAGES:
                for method, url in page_calls[path]:
                    resp = await client.request(method, url, headers=headers)
                    assert resp.status_code == 200, f"{path} → {url}: {resp.status_code} {resp.text}"

            chat = await client.post("/api/ai/consultant", json={
                "question": "Хочу записаться",
            }, headers=headers)
            assert chat.status_code == 200
            assert test_service.name in chat.json()["response"]

        assert test_master.id
        assert test_car.id
