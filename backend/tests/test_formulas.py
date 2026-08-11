"""Юнит-тесты чистых формул финансов / ИИ-Финансиста."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from app.finance_formulas import (
    apply_overhead_boost,
    avg_check,
    avg_load,
    break_even_revenue,
    build_expense_insights,
    build_financier_context_metrics,
    compute_pl,
    contribution_ratio,
    discount_percent_relative,
    discount_roi,
    forecast_profit,
    gross_margin_percent,
    gross_profit,
    heatmap_intensity,
    is_low_margin,
    is_low_volume,
    net_margin_percent,
    net_profit,
    percent_from_priority,
    resolve_service_cost,
    service_discount_priority,
    service_margin_percent,
    service_margin_raw,
    should_protect_high_margin,
    sum_expenses,
    sum_material_cost,
    sum_revenue,
)

FIXTURE = Path(__file__).resolve().parents[2] / "tests" / "test-data.json"


@pytest.fixture(scope="module")
def data():
    return json.loads(FIXTURE.read_text(encoding="utf-8"))


class TestPL:
    def test_revenue(self, data):
        assert sum_revenue(data["transactions"]) == data["expected"]["total_revenue"]

    def test_materials(self, data):
        assert sum_material_cost(data["transactions"]) == data["expected"]["total_material_cost"]

    def test_expenses(self, data):
        assert sum_expenses(data["expenses"]) == data["expected"]["total_expenses"]

    def test_avg_check(self, data):
        e = data["expected"]
        assert avg_check(e["total_revenue"], e["completed_count"]) == e["avg_check"]

    def test_gross(self, data):
        e = data["expected"]
        assert gross_profit(e["total_revenue"], e["total_material_cost"]) == e["gross_profit"]
        assert gross_margin_percent(e["total_revenue"], e["total_material_cost"]) == e["gross_margin_percent"]

    def test_net(self, data):
        e = data["expected"]
        assert net_profit(e["total_revenue"], e["total_material_cost"], e["total_expenses"]) == e["net_profit"]
        assert net_margin_percent(e["total_revenue"], e["total_material_cost"], e["total_expenses"]) == e["net_margin_percent"]

    def test_compute_pl(self, data):
        pl = compute_pl(data["transactions"], data["expenses"])
        e = data["expected"]
        assert pl["total_revenue"] == e["total_revenue"]
        assert pl["completed_appointments"] == e["completed_count"]
        assert pl["avg_check"] == e["avg_check"]
        assert pl["gross_profit"] == e["gross_profit"]
        assert pl["net_profit"] == e["net_profit"]


class TestServiceMargin:
    def test_catalog_margins(self, data):
        for sid, exp in data["expected"]["service_margins"].items():
            assert service_margin_percent(exp["price"], exp["cost"]) == exp["margin_percent"]
            assert resolve_service_cost(exp["cost"], 0) == exp["cost"]

    def test_cost_fallback(self):
        assert resolve_service_cost(0, 500) == 500
        assert service_margin_raw(1000, 400) == pytest.approx(0.6)


class TestBreakEven:
    def test_break_even_and_forecast(self, data):
        e = data["expected"]
        ratio = contribution_ratio(e["total_revenue"], e["total_material_cost"])
        assert break_even_revenue(e["total_expenses"], ratio) == e["break_even_revenue"]
        assert forecast_profit(e["total_revenue"], e["total_material_cost"], e["total_expenses"]) == e["net_profit"]

    def test_default_contrib(self):
        assert contribution_ratio(0, 0) == 0.4


class TestLoad:
    def test_avg_and_intensity(self):
        assert avg_load(10, 4) == 2.5
        assert heatmap_intensity(3, 6) == 0.5

    def test_discount_percent_relative(self, data):
        for case in data["load_cases"]:
            assert discount_percent_relative(case["hour_load"], case["peak_load"]) == case["expected_discount"]


class TestDiscountRoi:
    def test_roi_cases(self, data):
        for case in data["discount_roi_cases"]:
            r = discount_roi(case["times_used"], case["discount_cost"], case["avg_check"])
            assert r["verdict"] == case["expected_verdict"]
            if "expected_roi_min" in case:
                assert r["roi_percent"] >= case["expected_roi_min"]
            if "expected_roi_max" in case:
                assert r["roi_percent"] < case["expected_roi_max"]


class TestServiceDiscountPriority:
    def test_percent_from_priority(self, data):
        for case in data["priority_cases"]:
            pct = percent_from_priority(case["priority"])
            if "expected_percent" in case:
                assert pct == case["expected_percent"]
            if "expected_percent_min" in case:
                assert pct >= case["expected_percent_min"]
            if "expected_percent_max" in case:
                assert pct <= case["expected_percent_max"]

    def test_priority_formula(self):
        assert service_discount_priority(0.2, 0.4) == pytest.approx(0.8 * 0.55 + 0.6 * 0.45)

    def test_overhead_and_protect(self):
        assert apply_overhead_boost(15, 0.25) == 20
        assert apply_overhead_boost(15, 0.4) == 23
        assert should_protect_high_margin(0.75, False) is True
        assert should_protect_high_margin(0.75, True) is False
        assert is_low_volume(2, 10, 0.2) is True
        assert is_low_margin(0.4, 0.6) is True


class TestFinancierContext:
    def test_context_metrics(self, data):
        ctx = build_financier_context_metrics(
            data["transactions"], total_clients=40, total_masters=2
        )
        e = data["expected"]
        assert ctx["month_revenue"] == e["total_revenue"]
        assert ctx["completed_appointments"] == e["completed_count"]
        assert ctx["avg_check"] == e["avg_check"]
        by_name = {m["name"]: m for m in ctx["masters"]}
        assert by_name["Иван"]["completed"] == e["masters"]["Иван"]["completed"]
        assert by_name["Иван"]["revenue"] == e["masters"]["Иван"]["revenue"]
        assert by_name["Пётр"]["completed"] == e["masters"]["Пётр"]["completed"]
        assert by_name["Пётр"]["revenue"] == e["masters"]["Пётр"]["revenue"]


class TestExpenseInsights:
    def test_insights(self, data):
        e = data["expected"]
        insights = build_expense_insights(
            revenue_month=e["total_revenue"],
            material_month=e["total_material_cost"],
            fixed_month=e["total_expenses"],
            rent_month=120000,
            marketing_month=25000,
            prev_by_category={"marketing": 15000},
            cur_by_category={"marketing": 25000},
            category_labels={"marketing": "Маркетинг"},
        )
        types = {i["type"] for i in insights}
        assert "anomaly" in types
        assert "break_even" in types
        assert "forecast" in types
        assert any(i.get("title") == "Аренда дорогая относительно выручки" for i in insights)
        assert any(i.get("title") == "Реклама может быть неэффективна" for i in insights)
