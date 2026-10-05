"""Тесты разбора текстовых вызовов функций (DSML-разметка) и их обработки в chat_service."""

from app.modules.ai.tool_text import contains_tool_markup, extract_tool_calls, strip_tool_markup

# Служебный токен модели; в тексте от него остаётся имя "DSML".
MARK = "<|DSML|"


def _raw_call(name: str, params: str = "") -> str:
    return (
        MARK + "function_calls> "
        + MARK + f'invoke name="{name}"> '
        + params
        + MARK + "invoke> "
        + MARK + "function_calls>"
    )


SAMPLE = (
    MARK + "function_calls> "
    + MARK + 'invoke name="create_appointment"> '
    + MARK + 'parameter name="date" string="true">2025-06-15' + MARK + "parameter> "
    + MARK + 'parameter name="services" string="false">["Полировка кузова", "Керамическое покрытие 9H"]' + MARK + "parameter> "
    + MARK + "invoke> "
    + MARK + "function_calls>"
)


# --------------------------------------------------------------- parser
class TestToolText:
    def test_detects_markup(self):
        assert contains_tool_markup(SAMPLE) is True
        assert contains_tool_markup("Просто обычный ответ клиенту.") is False
        assert contains_tool_markup("") is False
        assert contains_tool_markup(None) is False

    def test_extract_name_and_arguments(self):
        calls = extract_tool_calls(SAMPLE)
        assert len(calls) == 1
        call = calls[0]
        assert call["name"] == "create_appointment"
        assert call["arguments"]["date"] == "2025-06-15"
        # string="false" → значение парсится как JSON
        assert call["arguments"]["services"] == ["Полировка кузова", "Керамическое покрытие 9H"]

    def test_extract_without_params(self):
        calls = extract_tool_calls(_raw_call("get_client_profile"))
        assert calls == [{"name": "get_client_profile", "arguments": {}}]

    def test_strip_removes_markup_only(self):
        assert strip_tool_markup(SAMPLE) == ""
        assert strip_tool_markup("Готово, Иван!\n" + SAMPLE) == "Готово, Иван!"
        assert strip_tool_markup("Обычный текст") == "Обычный текст"


# --------------------------------------------------------------- orchestrator
class TestChatServiceTextToolCalls:
    async def test_text_tool_call_is_executed_and_hidden(
        self, db_session, default_tenant, test_user, monkeypatch,
    ):
        """Модель написала вызов текстом → он выполняется, клиент видит только чистый ответ."""
        from app.modules.ai import chat_service

        section = {
            "system": "Ты консультант.",
            "functions": [
                {"name": "get_client_profile", "description": "", "parameters": {"type": "object", "properties": {}}},
            ],
        }
        monkeypatch.setattr(chat_service, "load_prompt", lambda name: section)

        client = {
            "id": test_user.id,
            "full_name": test_user.full_name,
            "role": "client",
            "tenant_id": str(default_tenant.id),
        }

        class _Message:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        scripted = [
            _Message(_raw_call("get_client_profile"), None),  # «сырой» текстовый вызов
            _Message("Готово, Иван! Всё проверил. Чем ещё помочь?", None),  # чистый финал
        ]
        seen: list[list[dict]] = []

        async def fake_chat(messages, tools=None, **kwargs):
            seen.append(messages)
            return scripted.pop(0)

        monkeypatch.setattr(chat_service, "chat_with_tools", fake_chat)

        result = await chat_service.run_consultant_chat(
            db_session,
            default_tenant.id,
            client,
            [{"role": "user", "content": "Запиши меня"}],
        )

        # Клиенту уходит только чистый текст
        assert result["response"] == "Готово, Иван! Всё проверил. Чем ещё помочь?"
        assert "DSML" not in result["response"]
        assert "invoke" not in result["response"].lower()
        # Текстовый вызов был выполнен: во втором запросе к модели есть результат функции
        assert any(m["role"] == "tool" for m in seen[1])

    async def test_malformed_call_does_not_crash(
        self, db_session, default_tenant, test_user, monkeypatch,
    ):
        """Вызов с неверными аргументами не роняет чат: модель получает ошибку и отвечает текстом."""
        from app.modules.ai import chat_service

        section = {
            "system": "Ты консультант.",
            "functions": [
                {"name": "create_appointment", "description": "", "parameters": {"type": "object", "properties": {}}},
            ],
        }
        monkeypatch.setattr(chat_service, "load_prompt", lambda name: section)

        client = {
            "id": test_user.id,
            "full_name": test_user.full_name,
            "role": "client",
            "tenant_id": str(default_tenant.id),
        }

        class _Message:
            def __init__(self, content, tool_calls=None):
                self.content = content
                self.tool_calls = tool_calls

        bad_call = _raw_call(
            "create_appointment",
            MARK + 'parameter name="services" string="false">["Полировка кузова"]' + MARK + "parameter> ",
        )
        scripted = [
            _Message(bad_call, None),
            _Message("Уточни, пожалуйста, дату и время — и я запишу.", None),
        ]
        seen: list[list[dict]] = []

        async def fake_chat(messages, tools=None, **kwargs):
            seen.append(messages)
            return scripted.pop(0)

        monkeypatch.setattr(chat_service, "chat_with_tools", fake_chat)

        result = await chat_service.run_consultant_chat(
            db_session,
            default_tenant.id,
            client,
            [{"role": "user", "content": "Запиши меня на полировку"}],
        )

        assert result["response"] == "Уточни, пожалуйста, дату и время — и я запишу."
        tool_messages = [m for m in seen[1] if m["role"] == "tool"]
        assert tool_messages and '"error"' in tool_messages[0]["content"]
