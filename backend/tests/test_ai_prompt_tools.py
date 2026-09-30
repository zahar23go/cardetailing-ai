"""Тесты интеграции промпта detailer.yaml: загрузчик, tool-схемы, функции Максима."""

import os
import time
from datetime import datetime, timedelta, timezone

import pytest

from app.core import prompt_loader
from app.models import Appointment, Material, Notification, Photo
from app.modules.ai.chat_service import build_tools
from app.modules.ai.detailer_tools import DetailerTools, dispatch

EXPECTED_FUNCTIONS = {
    "get_client_profile",
    "update_client_profile",
    "search_portfolio",
    "search_products",
    "get_free_slots",
    "create_appointment",
    "send_master_brief",
    "escalate_to_human",
}


def _client(test_user, default_tenant) -> dict:
    return {
        "id": test_user.id,
        "full_name": test_user.full_name,
        "role": "client",
        "tenant_id": str(default_tenant.id),
    }


def _future(days: int = 3) -> str:
    return (datetime.now(timezone.utc) + timedelta(days=days)).date().isoformat()


# --------------------------------------------------------------- loader
class TestPromptLoader:
    def test_reads_detailer_prompt(self):
        section = prompt_loader.load_prompt("detailer")
        assert section["system"].strip()
        names = {fn["name"] for fn in section["functions"]}
        assert names == EXPECTED_FUNCTIONS

    def test_list_prompts_contains_detailer(self):
        assert "detailer" in prompt_loader.list_prompts()

    def test_hot_reload_without_restart(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path))
        prompt_loader.clear_cache()
        path = tmp_path / "demo.yaml"
        path.write_text("demo:\n  system: |\n    Версия 1\n", encoding="utf-8")
        assert prompt_loader.load_prompt("demo")["system"].strip() == "Версия 1"

        path.write_text("demo:\n  system: |\n    Версия 2\n", encoding="utf-8")
        os.utime(path, (time.time() + 5, time.time() + 5))
        assert prompt_loader.load_prompt("demo")["system"].strip() == "Версия 2"

    def test_missing_prompt_raises(self, tmp_path, monkeypatch):
        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path))
        prompt_loader.clear_cache()
        with pytest.raises(FileNotFoundError):
            prompt_loader.load_prompt("nope")

    def test_build_tools_from_yaml(self):
        section = prompt_loader.load_prompt("detailer")
        tools = build_tools(section["functions"])
        assert len(tools) == len(EXPECTED_FUNCTIONS)
        first = tools[0]["function"]
        assert first["name"] == "get_client_profile"
        assert first["parameters"]["type"] == "object"


# --------------------------------------------------------------- functions
class TestDetailerFunctions:
    async def test_get_client_profile(
        self, db_session, default_tenant, test_user, test_car,
    ):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        profile = await tools.get_client_profile()
        assert profile["has_profile"] is True
        assert profile["cars"][0]["make"] == "BMW"
        assert "coating_type" in profile["cars"][0]

    async def test_update_client_profile(
        self, db_session, default_tenant, test_user, test_car,
    ):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await tools.update_client_profile(
            coating_type="Керамика",
            glass_damage="скол на лобовом",
            special_requirements="бескислотный шампунь, только ручная сушка",
        )
        assert result["ok"] is True
        await db_session.refresh(test_car)
        assert test_car.paint_type == "ceramic"
        assert "скол на лобовом" in test_car.glass_defects
        assert "бескислотный шампунь" in test_car.care_requirements

    async def test_search_products_hides_price(
        self, db_session, default_tenant, test_user,
    ):
        db_session.add(Material(
            name="Шампунь бескислотный", category="chemistry", unit="l",
            quantity=10, purchase_price=500, is_active=True, tenant_id=default_tenant.id,
            notes="Для керамики",
        ))
        await db_session.commit()

        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await tools.search_products("шампунь")
        assert result["products"]
        product = result["products"][0]
        assert product["name"] == "Шампунь бескислотный"
        # Закупочную цену клиенту не показываем
        assert "price" not in product
        assert "purchase_price" not in product

    async def test_search_portfolio(
        self, db_session, default_tenant, test_user, test_service,
    ):
        db_session.add(Photo(
            tenant_id=default_tenant.id, entity_type="portfolio",
            service_id=test_service.id, uploaded_by_id=test_user.id,
            url="/images/polish.jpg", title="Полировка",
        ))
        await db_session.commit()

        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await tools.search_portfolio("Полировка")
        assert result["count"] >= 1
        assert result["photos"][0]["image_url"] == "/images/polish.jpg"
        assert result["photos"][0]["master"] == test_user.full_name

    async def test_get_free_slots_returns_available(
        self, db_session, default_tenant, test_user, test_service,
    ):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await tools.get_free_slots([test_service.name], date=_future())
        assert result["services"] == [test_service.name]
        assert result["slots"]
        assert result["slots"][0]["time"]

    async def test_create_appointment_and_master_brief(
        self, db_session, default_tenant, test_user, test_car, test_master, test_service,
    ):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        booking = await tools.create_appointment([{
            "service_name": test_service.name,
            "employee_name": test_master.full_name,
            "date": _future(),
            "time": "10:00",
        }])
        assert booking["ok"] is True
        assert booking["count"] == 1
        appointment_id = booking["bookings"][0]["appointment_id"]

        appointment = await db_session.get(Appointment, appointment_id)
        assert appointment.car_id == test_car.id
        assert appointment.master_id == test_master.id

        brief = await tools.send_master_brief(
            employee_name=test_master.full_name,
            summary="Полируем кузов перед продажей.",
            features="Лак, скол на капоте",
            images=["/images/polish.jpg"],
        )
        assert brief["ok"] is True
        await db_session.refresh(appointment)
        assert "Полируем кузов" in appointment.master_brief
        assert "Лак, скол на капоте" in appointment.master_brief

    async def test_escalate_notifies_admin(
        self, db_session, default_tenant, test_user, test_admin,
    ):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await dispatch(tools, "escalate_to_human", {"reason": "Просит живого администратора"})
        assert result["ok"] is True
        assert result["notified"] >= 1

        from sqlalchemy import select
        rows = (await db_session.execute(
            select(Notification).where(Notification.user_id == test_admin.id)
        )).scalars().all()
        assert rows

    async def test_dispatch_unknown_function(self, db_session, default_tenant, test_user):
        tools = DetailerTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        result = await dispatch(tools, "launch_rocket", {})
        assert result["ok"] is False


# --------------------------------------------------------------- orchestrator
class TestChatService:
    async def test_tool_loop_returns_final_text(
        self, db_session, default_tenant, test_user, monkeypatch,
    ):
        """LLM просит get_client_profile, затем отвечает текстом."""
        from app.modules.ai import chat_service

        class _Function:
            name = "get_client_profile"
            arguments = "{}"

        class _ToolCall:
            id = "call_1"
            function = _Function()

        class _Message:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls

        scripted = [_Message(None, [_ToolCall()]), _Message("Профиль загружен, чем помочь?", None)]
        seen: list[list[dict]] = []

        async def fake_chat(messages, tools=None, **kwargs):
            seen.append(messages)
            return scripted.pop(0)

        monkeypatch.setattr(chat_service, "chat_with_tools", fake_chat)
        result = await chat_service.run_consultant_chat(
            db_session,
            default_tenant.id,
            _client(test_user, default_tenant),
            [{"role": "user", "content": "Привет"}],
        )
        assert result["response"] == "Профиль загружен, чем помочь?"
        # Второй вызов модели получил результат функции (роль tool)
        assert any(message["role"] == "tool" for message in seen[1])
