"""Тесты модуля отзывов: импорт, список, ИИ-вердикт."""

from unittest.mock import AsyncMock, patch

import pytest


IMPORT_PAYLOAD = {
    "reviews": [
        {"source": "yandex", "external_id": "r1", "author": "Иван", "rating": 5, "text": "Отлично помыли, быстро и чисто"},
        {"source": "yandex", "external_id": "r2", "author": "Пётр", "rating": 2, "text": "Долго ждал, дорого"},
    ]
}


class TestReviewImport:
    async def test_import_and_dedup(self, client, admin_headers):
        """✅ Импорт отзывов и пропуск дубликатов по external_id."""
        r = await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=admin_headers)
        assert r.status_code == 200
        assert r.json() == {"imported": 2, "skipped": 0, "total": 2}

        again = await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=admin_headers)
        assert again.json() == {"imported": 0, "skipped": 2, "total": 2}

    async def test_list(self, client, admin_headers):
        """✅ Список отзывов возвращает импортированные записи."""
        await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=admin_headers)
        r = await client.get("/api/reviews", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["total"] == 2
        assert {i["external_id"] for i in data["items"]} == {"r1", "r2"}

    async def test_create_and_delete(self, client, admin_headers):
        """✅ Добавление одного отзыва вручную и удаление."""
        r = await client.post(
            "/api/reviews",
            json={"source": "manual", "author": "Анна", "rating": 4, "text": "Хорошая химчистка"},
            headers=admin_headers,
        )
        assert r.status_code == 201
        review_id = r.json()["id"]

        d = await client.delete(f"/api/reviews/{review_id}", headers=admin_headers)
        assert d.status_code == 200
        assert (await client.get("/api/reviews", headers=admin_headers)).json()["total"] == 0


class TestReviewVerdict:
    async def test_analyze_with_llm(self, client, admin_headers):
        """✅ Вердикт берётся у ИИ (LLM замокан) и кэшируется."""
        await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=admin_headers)

        fake = {
            "score": 4.1,
            "sentiment": "positive",
            "summary": "В целом качественно, но есть жалобы на цену.",
            "strengths": ["Быстро и чисто"],
            "weaknesses": ["Дорого"],
            "themes": [{"name": "качество", "count": 1, "sentiment": "positive"}],
            "recommendations": ["Пересмотреть цены на мойку"],
        }
        with patch(
            "app.modules.reviews.service.llm_verdict",
            new_callable=AsyncMock,
            return_value=fake,
        ):
            r = await client.post("/api/reviews/analyze", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "ai"
        assert data["score"] == 4.1
        assert data["reviews_count"] == 2
        assert data["strengths"] == ["Быстро и чисто"]

        # Кэш: GET возвращает тот же вердикт без пересчёта
        cached = await client.get("/api/reviews/verdict", headers=admin_headers)
        assert cached.json()["source"] == "ai"
        assert cached.json()["score"] == 4.1

    async def test_analyze_heuristic_fallback(self, client, admin_headers):
        """✅ Без ИИ работает эвристический вердикт по оценкам."""
        await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=admin_headers)
        with patch(
            "app.modules.reviews.service.llm_verdict",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await client.post("/api/reviews/analyze", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert data["source"] == "heuristic"
        assert data["average_rating"] == 3.5
        assert data["reviews_count"] == 2

    async def test_analyze_empty(self, client, admin_headers):
        """✅ Без отзывов вердикт пустой, но эндпоинт отвечает 200."""
        with patch(
            "app.modules.reviews.service.llm_verdict",
            new_callable=AsyncMock,
            return_value=None,
        ):
            r = await client.post("/api/reviews/analyze", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["reviews_count"] == 0

    async def test_verdict_without_analysis(self, client, admin_headers):
        """✅ GET вердикта до анализа не падает."""
        r = await client.get("/api/reviews/verdict", headers=admin_headers)
        assert r.status_code == 200
        assert r.json()["reviews_count"] == 0


class TestReviewAccess:
    async def test_client_forbidden(self, client, auth_headers):
        """❌ Клиент не имеет доступа к отзывам салона."""
        r = await client.get("/api/reviews", headers=auth_headers)
        assert r.status_code in (401, 403)

    async def test_import_requires_admin(self, client, master_headers):
        """❌ Мастер не может импортировать отзывы."""
        r = await client.post("/api/reviews/import", json=IMPORT_PAYLOAD, headers=master_headers)
        assert r.status_code in (401, 403)
