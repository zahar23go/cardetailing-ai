"""Тесты реальных функций финансиста (financier_tools) на данных БД.

Проверяют KPI, разбивку выручки, загрузку, удержание и прогноз на завершённых визитах.
"""

from datetime import datetime, timedelta, timezone

from app.models import Appointment, Box, Service
from app.modules.ai.financier_tools import FinancierTools


def _client(test_user, default_tenant) -> dict:
    return {
        "id": test_user.id,
        "full_name": test_user.full_name,
        "role": "admin",
        "tenant_id": str(default_tenant.id),
    }


def _tools(db, default_tenant, test_user) -> FinancierTools:
    return FinancierTools(db, default_tenant.id, _client(test_user, default_tenant))


async def _make_box(db, default_tenant, name="Бокс 1") -> Box:
    box = Box(name=name, tenant_id=default_tenant.id, sort_order=0, is_active=True)
    db.add(box)
    await db.commit()
    await db.refresh(box)
    return box


def _appointment(
    default_tenant,
    *,
    client,
    car,
    service,
    master=None,
    box=None,
    start,
    minutes=120,
    price=5000,
    status="completed",
) -> Appointment:
    return Appointment(
        tenant_id=default_tenant.id,
        client_id=client.id,
        car_id=car.id,
        service_id=service.id,
        master_id=master.id if master else None,
        box_id=box.id if box else None,
        start_time=start,
        end_time=start + timedelta(minutes=minutes),
        status=status,
        total_price=price,
    )


class TestKpi:
    async def test_kpi_counts_only_completed(
        self, db_session, default_tenant, test_user, test_master, test_service, test_car,
    ):
        box = await _make_box(db_session, default_tenant)
        now = datetime.now(timezone.utc)

        db_session.add(_appointment(
            default_tenant, client=test_user, car=test_car, service=test_service,
            master=test_master, box=box, start=now - timedelta(hours=1), price=5000,
        ))
        # Отменённый визит не должен попадать ни в выручку, ни в загрузку.
        db_session.add(_appointment(
            default_tenant, client=test_user, car=test_car, service=test_service,
            master=test_master, box=box, start=now - timedelta(hours=3), price=9999,
            status="cancelled",
        ))
        await db_session.commit()

        kpi = await _tools(db_session, default_tenant, test_user).get_kpi(period="month")
        assert kpi["revenue"] == 5000
        assert kpi["completed_appointments"] == 1
        assert kpi["avg_check"] == 5000
        assert kpi["occupancy"] > 0
        assert kpi["retention"] == 0  # один клиент, один визит


class TestRevenueBreakdown:
    async def test_breakdown_by_service_master_days(
        self, db_session, default_tenant, test_user, test_master, test_service, test_car,
    ):
        other_service = Service(
            name="Химчистка салона", description="Химчистка", category="Детейлинг",
            price=2000, duration=90, material_cost=100, is_active=True,
            tenant_id=default_tenant.id,
        )
        db_session.add(other_service)
        await db_session.commit()
        await db_session.refresh(other_service)

        now = datetime.now(timezone.utc)
        db_session.add_all([
            _appointment(default_tenant, client=test_user, car=test_car, service=test_service,
                         master=test_master, start=now - timedelta(hours=1), price=5000),
            _appointment(default_tenant, client=test_user, car=test_car, service=test_service,
                         master=test_master, start=now - timedelta(hours=2), price=3000),
            _appointment(default_tenant, client=test_user, car=test_car, service=other_service,
                         master=test_master, start=now - timedelta(days=1), price=2000),
        ])
        await db_session.commit()

        tools = _tools(db_session, default_tenant, test_user)
        data = await tools.get_revenue_breakdown(
            date_from=(now - timedelta(days=2)).date().isoformat(),
            date_to=now.date().isoformat(),
        )

        assert data["total_revenue"] == 10000

        by_service = {row["name"]: row for row in data["services"]}
        assert by_service[test_service.name]["revenue"] == 8000
        assert by_service[test_service.name]["count"] == 2
        assert by_service["Химчистка салона"]["revenue"] == 2000
        # Сортировка по выручке (убывание)
        assert data["services"][0]["name"] == test_service.name

        by_master = data["masters"]
        assert len(by_master) == 1
        assert by_master[0]["name"] == test_master.full_name
        assert by_master[0]["revenue"] == 10000

        assert data["days"]
        assert round(sum(row["revenue"] for row in data["days"]), 2) == 10000


class TestOccupancy:
    async def test_occupancy_salon_and_masters(
        self, db_session, default_tenant, test_user, test_master, test_service, test_car,
    ):
        box = await _make_box(db_session, default_tenant)
        now = datetime.now(timezone.utc)
        db_session.add(_appointment(
            default_tenant, client=test_user, car=test_car, service=test_service,
            master=test_master, box=box, start=now - timedelta(hours=1), minutes=120,
        ))
        await db_session.commit()

        data = await _tools(db_session, default_tenant, test_user).get_occupancy(period="day")
        assert data["period_days"] == 1
        assert data["salon"] > 0
        assert data["masters"]
        master_row = next(m for m in data["masters"] if m["name"] == test_master.full_name)
        assert master_row["occupancy"] > 0
        assert master_row["busy_minutes"] == 120


class TestRetention:
    async def test_repeat_client_rate(
        self, db_session, default_tenant, test_user, test_master, test_service, test_car,
    ):
        now = datetime.now(timezone.utc)
        # Два визита одного клиента в разных месяцах → удержание 100%.
        db_session.add_all([
            _appointment(default_tenant, client=test_user, car=test_car, service=test_service,
                         master=test_master, start=now - timedelta(hours=1)),
            _appointment(default_tenant, client=test_user, car=test_car, service=test_service,
                         master=test_master, start=now - timedelta(days=40)),
        ])
        await db_session.commit()

        data = await _tools(db_session, default_tenant, test_user).get_customer_retention(period="quarter")
        assert data["total_clients"] == 1
        assert data["returning_clients"] == 1
        assert data["repeat_rate"] == 100.0
        assert isinstance(data["cohorts"], list)


class TestForecast:
    async def test_forecast_scales_daily_revenue(
        self, db_session, default_tenant, test_user, test_master, test_service, test_car,
    ):
        box = await _make_box(db_session, default_tenant)
        now = datetime.now(timezone.utc)
        db_session.add(_appointment(
            default_tenant, client=test_user, car=test_car, service=test_service,
            master=test_master, box=box, start=now - timedelta(hours=1), price=3000,
        ))
        await db_session.commit()

        data = await _tools(db_session, default_tenant, test_user).forecast(horizon="7d")
        assert data["horizon_days"] == 7
        # 3000 ₽ за 30 дней → 100 ₽/день → 700 ₽ за 7 дней.
        assert data["basis"]["daily_revenue"] == 100
        assert data["revenue"] == 700
        assert data["occupancy"] >= 0


class TestDispatch:
    async def test_dispatch_unknown_function(self, db_session, default_tenant, test_user):
        from app.modules.ai.financier_tools import dispatch

        tools = _tools(db_session, default_tenant, test_user)
        result = await dispatch(tools, "nope", {})
        assert result["ok"] is False
