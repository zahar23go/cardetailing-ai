"""Тесты AI-эндпоинтов (консультант, финансист)."""

from unittest.mock import AsyncMock, patch

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
        """✅ POST /api/ai/consultant возвращает 200 с ответом (DeepSeek замокан)."""
        fake = "Рекомендуем комплексную мойку и покрытие керамикой."
        with patch(
            "app.modules.ai.router.get_consultant_response",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            resp = await client.post("/api/ai/consultant", json={
                "question": "Какие услуги вы предлагаете?",
            }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert "response" in data
        assert len(data["response"]) > 0
        assert data["response"] == fake

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
