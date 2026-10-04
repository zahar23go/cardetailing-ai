"""Тесты финансового ассистента: загрузка промпта, mock-функции, chat_service, эндпоинт.

prompts/financier.yaml ещё не написан — файл подменяется через tmp PROMPTS_DIR,
а эндпоинт проверяется и на legacy-ветке, и на prompt-driven ветке.
"""

from unittest.mock import AsyncMock

from app.core import prompt_loader
from app.modules.ai.chat_service import run_consultant_chat
from app.modules.ai.financier_tools import FinancierTools, dispatch

FINANCIER_YAML = """\
financier:
  system: |
    Ты — финансовый ассистент детейлинг-центра.
  functions:
    - name: get_kpi
      description: Ключевые показатели
      parameters: {type: object, properties: {}}
    - name: forecast
      description: Прогноз
      parameters: {type: object, properties: {}}
"""


def _client(test_user, default_tenant) -> dict:
    return {
        "id": test_user.id,
        "full_name": test_user.full_name,
        "role": "admin",
        "tenant_id": str(default_tenant.id),
    }


class _FakePath:
    """Заглушка пути промпта для эндпоинта (файла пока нет)."""

    def __init__(self, exists: bool):
        self._exists = exists

    def is_file(self) -> bool:
        return self._exists


# --------------------------------------------------------------- loader
class TestFinancierPromptLoader:
    def test_reads_financier_prompt(self, tmp_path, monkeypatch):
        """prompt_loader читает любую секцию YAML — проверяем на financier (mock-файл)."""
        monkeypatch.setenv("PROMPTS_DIR", str(tmp_path))
        prompt_loader.clear_cache()
        (tmp_path / "financier.yaml").write_text(FINANCIER_YAML, encoding="utf-8")

        section = prompt_loader.load_prompt("financier")
        assert "финансовый ассистент" in section["system"]
        assert {fn["name"] for fn in section["functions"]} == {"get_kpi", "forecast"}
        assert "financier" in prompt_loader.list_prompts()

    def test_prompts_dir_falls_back_to_repo(self, monkeypatch):
        """/app/prompts нет → fallback на repo/prompts (там лежит detailer.yaml)."""
        monkeypatch.delenv("PROMPTS_DIR", raising=False)
        prompt_loader.clear_cache()
        assert (prompt_loader.prompts_dir() / "detailer.yaml").is_file()


# --------------------------------------------------------------- functions
class TestFinancierMockFunctions:
    async def test_mock_shapes(self, db_session, default_tenant, test_user):
        tools = FinancierTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        assert await tools.get_kpi() == {"revenue": 0, "occupancy": 0, "retention": 0}
        assert await tools.get_revenue_breakdown() == {"services": [], "masters": [], "days": []}
        assert await tools.get_occupancy() == {"salon": 0, "masters": []}
        assert await tools.get_customer_retention() == {"cohorts": []}
        assert await tools.forecast() == {"revenue": 0, "occupancy": 0}

    async def test_dispatch_routes_and_tolerates_args(self, db_session, default_tenant, test_user):
        tools = FinancierTools(db_session, default_tenant.id, _client(test_user, default_tenant))
        # Лишние аргументы от модели не ломают заглушку.
        assert await dispatch(tools, "get_kpi", {"period": "month"}) == {
            "revenue": 0,
            "occupancy": 0,
            "retention": 0,
        }
        assert (await dispatch(tools, "launch_rocket", {}))["ok"] is False


# --------------------------------------------------------------- chat_service
class TestFinancierChatService:
    async def test_prompt_name_financier_uses_financier_tools(
        self, db_session, default_tenant, test_user, monkeypatch,
    ):
        """prompt_name="financier" маршрутизирует вызов функции в FinancierTools."""
        from app.modules.ai import chat_service

        section = {
            "system": "Ты финансовый ассистент.",
            "functions": [
                {"name": "get_kpi", "description": "KPI", "parameters": {"type": "object", "properties": {}}},
            ],
        }
        monkeypatch.setattr(chat_service, "load_prompt", lambda name: section)

        class _Function:
            name = "get_kpi"
            arguments = "{}"

        class _ToolCall:
            id = "call_1"
            function = _Function()

        class _Message:
            def __init__(self, content, tool_calls):
                self.content = content
                self.tool_calls = tool_calls

        scripted = [_Message(None, [_ToolCall()]), _Message("KPI: выручка 0.", None)]
        seen: list[list[dict]] = []

        async def fake_chat(messages, tools=None, **kwargs):
            seen.append(messages)
            return scripted.pop(0)

        monkeypatch.setattr(chat_service, "chat_with_tools", fake_chat)

        result = await run_consultant_chat(
            db_session,
            default_tenant.id,
            _client(test_user, default_tenant),
            [{"role": "user", "content": "Покажи KPI"}],
            prompt_name="financier",
        )
        assert result["response"] == "KPI: выручка 0."
        tool_messages = [m for m in seen[1] if m["role"] == "tool"]
        assert tool_messages
        assert '"revenue": 0' in tool_messages[0]["content"]


# --------------------------------------------------------------- endpoint
class TestFinancierEndpoint:
    async def test_responds_legacy_when_no_prompt(
        self, client, admin_headers, monkeypatch,
    ):
        """Без financier.yaml эндпоинт отвечает старой логикой get_financier_response."""
        monkeypatch.setattr("app.modules.ai.router.prompt_path", lambda name: _FakePath(False))
        monkeypatch.setattr(
            "app.modules.ai.router.get_financier_response",
            AsyncMock(return_value="legacy-ответ"),
        )
        resp = await client.post(
            "/api/ai/financier",
            json={"question": "Какая выручка?"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "legacy-ответ"

    async def test_responds_via_prompt_when_yaml_present(
        self, client, admin_headers, monkeypatch,
    ):
        """При наличии financier.yaml эндпоинт идёт через run_consultant_chat."""
        monkeypatch.setattr("app.modules.ai.router.prompt_path", lambda name: _FakePath(True))
        mocked = AsyncMock(return_value={"response": "prompt-ответ"})
        monkeypatch.setattr("app.modules.ai.router.run_consultant_chat", mocked)

        resp = await client.post(
            "/api/ai/financier",
            json={"question": "Какая выручка?"},
            headers=admin_headers,
        )
        assert resp.status_code == 200
        assert resp.json()["response"] == "prompt-ответ"
        assert mocked.await_args.kwargs["prompt_name"] == "financier"

    async def test_unauthorized(self, client):
        resp = await client.post("/api/ai/financier", json={"question": "Какая выручка?"})
        assert resp.status_code in (401, 403)
