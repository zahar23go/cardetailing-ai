"""
Тесты аутентификации.

Проверяют регистрацию, логин и доступ к защищённым маршрутам.
"""

from datetime import date

import pytest
from httpx import AsyncClient


class TestAuth:
    """Набор тестов для эндпоинтов аутентификации."""

    # ------------------------------------------------------------------
    # 1. Успешная регистрация нового пользователя
    # ------------------------------------------------------------------
    async def test_register_success(self, client: AsyncClient, default_tenant):
        """✅ Регистрация нового пользователя с уникальным телефоном.
        default_tenant нужен, чтобы в БД был tenant для нового клиента.
        """
        payload = {
            "phone": "+79991111111",
            "password": "mypassword",
            "full_name": "Новый Клиент",
            "consent": True,
        }
        response = await client.post("/api/register", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        # Проверяем структуру ответа
        assert "token" in data, "Ответ должен содержать token"
        assert "user" in data, "Ответ должен содержать user"
        assert data["user"]["phone"] == payload["phone"]
        assert data["user"]["full_name"] == payload["full_name"]
        assert data["user"]["role"] == "client"
        assert data["branding"]["accent_solid"] == "#D4AF37"

    async def test_register_requires_consent(self, client: AsyncClient, default_tenant):
        """❌ Без согласия на обработку ПДн регистрация отклоняется (152-ФЗ)."""
        base = {
            "phone": "+79992223344",
            "password": "mypassword",
            "full_name": "Без согласия",
        }
        missing = await client.post("/api/register", json=base)
        assert missing.status_code == 422, missing.text

        refused = await client.post("/api/register", json={**base, "consent": False})
        assert refused.status_code == 422, refused.text

    # ------------------------------------------------------------------
    # 2. Регистрация с существующим телефоном → 409
    # ------------------------------------------------------------------
    async def test_register_duplicate_phone(self, client: AsyncClient, test_user):
        """❌ Регистрация с уже существующим телефоном возвращает 409."""
        payload = {
            "phone": test_user.phone,  # телефон уже занят
            "password": "anotherpass",
            "full_name": "Дубликат",
            "consent": True,
        }
        response = await client.post("/api/register", json=payload)
        assert response.status_code == 409, f"Expected 409, got {response.status_code}: {response.text}"
        data = response.json()
        assert "detail" in data

    # ------------------------------------------------------------------
    # 3. Успешный логин
    # ------------------------------------------------------------------
    async def test_login_success(self, client: AsyncClient, test_user):
        """✅ Логин с правильным телефоном и паролем."""
        payload = {
            "phone": test_user.phone,
            "password": "testpass123",  # пароль из conftest._hash_password
        }
        response = await client.post("/api/login", json=payload)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert "token" in data
        assert data["user"]["id"] == test_user.id
        assert data["user"]["phone"] == test_user.phone

    # ------------------------------------------------------------------
    # 4. Логин с неправильным паролем → 401
    # ------------------------------------------------------------------
    async def test_login_wrong_password(self, client: AsyncClient, test_user):
        """❌ Логин с неверным паролем возвращает 401."""
        payload = {
            "phone": test_user.phone,
            "password": "wrongpassword",
        }
        response = await client.post("/api/login", json=payload)
        assert response.status_code == 401, f"Expected 401, got {response.status_code}: {response.text}"

    # ------------------------------------------------------------------
    # 5. Доступ к /api/me с валидным токеном
    # ------------------------------------------------------------------
    async def test_me_with_token(self, client: AsyncClient, auth_headers: dict, test_user):
        """✅ Запрос /api/me с валидным токеном возвращает данные пользователя."""
        response = await client.get("/api/me", headers=auth_headers)
        assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
        data = response.json()

        assert data["id"] == test_user.id
        assert data["phone"] == test_user.phone
        assert data["role"] == "client"
        assert "enabled_modules" in data
        assert "core" in data["enabled_modules"]

    async def test_update_me_email_and_birth_date(
        self,
        client: AsyncClient,
        auth_headers: dict,
        test_user,
        db_session,
    ):
        """✅ /api/me сохраняет email и дату рождения и умеет их очищать."""
        response = await client.put(
            "/api/me",
            json={"email": "alex@example.com", "birth_date": "1990-05-15"},
            headers=auth_headers,
        )
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["email"] == "alex@example.com"
        assert data["birth_date"] == "1990-05-15"

        await db_session.refresh(test_user)
        assert test_user.email == "alex@example.com"
        assert test_user.birth_date.isoformat() == "1990-05-15"

        cleared = await client.put(
            "/api/me",
            json={"email": None, "birth_date": None},
            headers=auth_headers,
        )
        assert cleared.status_code == 200, cleared.text
        assert cleared.json()["email"] is None
        assert cleared.json()["birth_date"] is None

    async def test_admin_user_detail_has_email_and_birth_date(
        self,
        client: AsyncClient,
        admin_headers: dict,
        test_user,
        db_session,
    ):
        """✅ Карточка клиента в CRM отдаёт email и дату рождения."""
        test_user.email = "client@example.com"
        test_user.birth_date = date(1990, 5, 15)
        await db_session.commit()

        response = await client.get(f"/api/users/{test_user.id}", headers=admin_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert data["email"] == "client@example.com"
        assert data["birth_date"] == "1990-05-15"

    async def test_modules_endpoint(self, client: AsyncClient, auth_headers: dict):
        """✅ GET /api/modules отдаёт включённые домены тарифа."""
        response = await client.get("/api/modules", headers=auth_headers)
        assert response.status_code == 200, response.text
        data = response.json()
        assert "modules" in data
        assert "core" in data["modules"]
        assert "appointments" in data["modules"]

    # ------------------------------------------------------------------
    # 6. Доступ к /api/me без токена → 403
    # ------------------------------------------------------------------
    async def test_me_without_token(self, client: AsyncClient):
        """❌ Запрос /api/me без токена возвращает 403."""
        response = await client.get("/api/me")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
