"""Интеграционные тесты ИИ-Финансиста и rule-based рекомендаций."""

from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest
from httpx import AsyncClient

from app.finance_formulas import (
    build_expense_insights,
    build_financier_context_metrics,
    discount_percent_relative,
    discount_roi,
)
from app.models import Appointment, Expense

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "test-data.json"


@pytest.fixture(scope="module")
def fixture_data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestFinancierEndpoint:
    async def test_unauthorized(self, client: AsyncClient):
        resp = await client.post("/api/ai/financier", json={"question": "Какая прибыль?"})
        assert resp.status_code in (401, 403)

    async def test_empty_question(
        self,
        client: AsyncClient,
        admin_headers: dict,
    ):
        resp = await client.post(
            "/api/ai/financier",
            json={"question": ""},
            headers=admin_headers,
        )
        assert resp.status_code == 422

    async def test_financier_uses_context_and_returns_ai_text(
        self,
        client: AsyncClient,
        admin_headers: dict,
        db_session,
        default_tenant,
        test_admin,
        test_service,
        test_user,
        test_car,
        test_master,
        fixture_data,
    ):
        """Эндпоинт собирает KPI и передаёт их в get_financier_response."""
        now = datetime.now(timezone.utc)
        appt = Appointment(
            client_id=test_user.id,
            car_id=test_car.id,
            service_id=test_service.id,
            master_id=test_master.id,
            tenant_id=default_tenant.id,
            start_time=now.replace(day=min(now.day, 28), hour=10),
            end_time=now.replace(day=min(now.day, 28), hour=12),
            status="completed",
            total_price=5000,
        )
        db_session.add(appt)
        db_session.add(
            Expense(
                tenant_id=default_tenant.id,
                name="Аренда тест",
                category="rent",
                amount=10000,
                expense_date=now.replace(day=1, hour=0, minute=0, second=0, microsecond=0),
            )
        )
        await db_session.commit()

        fake_answer = (
            "📊 АНАЛИЗ\nВыручка в порядке.\n\n"
            "📌 ПРИЧИНА → ДЕЙСТВИЕ → ПРОГНОЗ\n• Тест → Тест → Тест\n\n"
            "💡 РЕКОМЕНДАЦИИ\n• Держать курс"
        )

        with patch(
            "app.main.get_financier_response",
            new_callable=AsyncMock,
            return_value=fake_answer,
        ) as mocked:
            resp = await client.post(
                "/api/ai/financier",
                json={"question": "Какая прибыль за месяц?"},
                headers=admin_headers,
            )
            assert resp.status_code == 200
            data = resp.json()
            assert data["response"] == fake_answer
            mocked.assert_awaited_once()
            question, context = mocked.await_args.args
            assert "Какая прибыль за месяц?" in question
            assert "Выручка за месяц" in context
            assert "5000" in context or "5" in context  # выручка из записи
            assert "Эффективность мастеров" in context or "мастер" in context.lower()


class TestRuleBasedRecommendations:
    def test_happy_hours_from_fixture(self, fixture_data):
        for case in fixture_data["load_cases"]:
            assert (
                discount_percent_relative(case["hour_load"], case["peak_load"])
                == case["expected_discount"]
            )

    def test_roi_verdicts(self, fixture_data):
        for case in fixture_data["discount_roi_cases"]:
            r = discount_roi(case["times_used"], case["discount_cost"], case["avg_check"])
            assert r["verdict"] == case["expected_verdict"]

    def test_expense_insights_pipeline(self, fixture_data):
        e = fixture_data["expected"]
        insights = build_expense_insights(
            revenue_month=e["total_revenue"],
            material_month=e["total_material_cost"],
            fixed_month=e["total_expenses"],
            rent_month=120000,
            marketing_month=25000,
            prev_by_category={"marketing": 15000},
            cur_by_category={"marketing": 25000},
        )
        assert any(i["type"] == "anomaly" for i in insights)
        assert any(i["type"] == "forecast" and i["severity"] == "warn" for i in insights)

    def test_financier_context_matches_expected(self, fixture_data):
        ctx = build_financier_context_metrics(fixture_data["transactions"])
        assert ctx["month_revenue"] == fixture_data["expected"]["total_revenue"]
        assert ctx["avg_check"] == fixture_data["expected"]["avg_check"]
