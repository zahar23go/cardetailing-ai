"""
Тесты аутентификации.

Проверяют регистрацию, логин и доступ к защищённым маршрутам.
"""

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

    # ------------------------------------------------------------------
    # 2. Регистрация с существующим телефоном → 409
    # ------------------------------------------------------------------
    async def test_register_duplicate_phone(self, client: AsyncClient, test_user):
        """❌ Регистрация с уже существующим телефоном возвращает 409."""
        payload = {
            "phone": test_user.phone,  # телефон уже занят
            "password": "anotherpass",
            "full_name": "Дубликат",
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

    # ------------------------------------------------------------------
    # 6. Доступ к /api/me без токена → 403
    # ------------------------------------------------------------------
    async def test_me_without_token(self, client: AsyncClient):
        """❌ Запрос /api/me без токена возвращает 403."""
        response = await client.get("/api/me")
        assert response.status_code == 403, f"Expected 403, got {response.status_code}: {response.text}"
