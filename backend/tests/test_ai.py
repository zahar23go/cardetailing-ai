"""Тесты AI-эндпоинтов (консультант, финансист)."""

from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient


class TestAIConsultant:
    """Тесты AI-консультанта для клиентов (промпт из prompts/detailer.yaml)."""

    # ------------------------------------------------------------------
    # 1. Эндпоинт существует и возвращает 200 (LLM замокан)
    # ------------------------------------------------------------------
    async def test_consultant_endpoint_exists(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """✅ POST /api/ai/consultant возвращает 200 с ответом (DeepSeek замокан)."""
        fake = "Рекомендуем комплексную мойку и покрытие керамикой."
        with patch(
            "app.modules.ai.router.run_consultant_chat",
            new_callable=AsyncMock,
            return_value={"response": fake},
        ) as mocked:
            resp = await client.post("/api/ai/consultant", json={
                "messages": [{"role": "user", "content": "Какие услуги вы предлагаете?"}],
                "tz_offset": 180,
            }, headers=auth_headers)
        assert resp.status_code == 200
        data = resp.json()
        assert data["response"] == fake
        # История и tz_offset доехали до оркестратора
        args, kwargs = mocked.call_args
        assert args[3] == [{"role": "user", "content": "Какие услуги вы предлагаете?"}]
        assert kwargs["tz_offset"] == 180

    # ------------------------------------------------------------------
    # 2. Обратная совместимость: одиночный question превращается в сообщение
    # ------------------------------------------------------------------
    async def test_consultant_accepts_legacy_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        with patch(
            "app.modules.ai.router.run_consultant_chat",
            new_callable=AsyncMock,
            return_value={"response": "ок"},
        ) as mocked:
            resp = await client.post("/api/ai/consultant", json={
                "question": "Сколько стоит полировка?",
            }, headers=auth_headers)
        assert resp.status_code == 200
        args, _ = mocked.call_args
        assert args[3] == [{"role": "user", "content": "Сколько стоит полировка?"}]

    # ------------------------------------------------------------------
    # 3. Вопрос без авторизации
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
    # 4. Пустой запрос
    # ------------------------------------------------------------------
    async def test_consultant_empty_question(
        self,
        client: AsyncClient,
        auth_headers: dict,
    ):
        """❌ Пустой вопрос/история отклоняется валидацией."""
        resp = await client.post("/api/ai/consultant", json={
            "question": "",
        }, headers=auth_headers)
        assert resp.status_code == 422

        resp = await client.post("/api/ai/consultant", json={
            "messages": [],
        }, headers=auth_headers)
        assert resp.status_code == 422
