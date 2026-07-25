"""Тесты AI-эндпоинтов (консультант, финансист)."""

import pytest
from httpx import AsyncClient


class TestAIConsultant:
    """Тесты AI-консультанта для клиентов."""

    # ------------------------------------------------------------------
    # 1. Эндпоинт существует и возвращает 200
    # ------------------------------------------------------------------
    async def test_consultant_endpoint_exists(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """✅ POST /api/ai/consultant возвращает 200 с ответом."""
        resp = await client.post("/api/ai/consultant", json={
            "question": "Какие услуги вы предлагаете?",
        }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        # Ответ не должен быть пустым
        assert len(data["response"]) > 0

    # ------------------------------------------------------------------
    # 2. Вопрос без авторизации
    # ------------------------------------------------------------------
    async def test_consultant_unauthorized(
        self,
        client: AsyncClient,
    ):
        """❌ Без токена — ошибка авторизации."""
        resp = await client.post("/api/ai/consultant", json={
            "question": "Сколько стоит полировка?",
        })
        assert resp.status_code in (401, 403)

    # ------------------------------------------------------------------
    # 3. Пустой вопрос
    # ------------------------------------------------------------------
    async def test_consultant_empty_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """❌ Пустой вопрос отклоняется валидацией."""
        resp = await client.post("/api/ai/consultant", json={
            "question": "",
        }, headers=auth_headers)
        assert resp.status_code == 422
