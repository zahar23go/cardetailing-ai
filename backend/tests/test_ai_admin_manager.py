"""Тесты страниц ИИ-ассистентов админки: права и передача истории диалога."""

from app.modules.ai import router as ai_router


def _capture(monkeypatch):
    calls: list[dict] = []

    async def fake(db, tenant_id, user, messages, tz_offset=0, prompt_name="detailer"):
        calls.append(
            {
                "messages": messages,
                "tz_offset": tz_offset,
                "prompt_name": prompt_name,
            }
        )
        return {"response": "ok"}

    monkeypatch.setattr(ai_router, "run_consultant_chat", fake)
    return calls


class TestAccess:
    async def test_manager_forbidden_for_client(self, client, auth_headers):
        res = await client.post(
            "/api/ai/manager",
            json={"question": "Что сегодня в расписании?"},
            headers=auth_headers,
        )
        assert res.status_code == 403

    async def test_manager_forbidden_for_master(self, client, master_headers):
        res = await client.post(
            "/api/ai/manager",
            json={"question": "Что сегодня в расписании?"},
            headers=master_headers,
        )
        assert res.status_code == 403

    async def test_admin_chat_forbidden_for_client(self, client, auth_headers):
        res = await client.post(
            "/api/ai/admin",
            json={"messages": [{"role": "user", "content": "Покажи услуги"}]},
            headers=auth_headers,
        )
        assert res.status_code == 403

    async def test_admin_chat_forbidden_for_master(self, client, master_headers):
        res = await client.post(
            "/api/ai/admin",
            json={"messages": [{"role": "user", "content": "Покажи услуги"}]},
            headers=master_headers,
        )
        assert res.status_code == 403

    async def test_manager_requires_token(self, client):
        res = await client.post("/api/ai/manager", json={"question": "Привет"})
        # HTTPBearer без заголовка отвечает 403, с битым токеном — 401.
        assert res.status_code == 403


class TestManagerChat:
    async def test_messages_history_goes_to_prompt(self, client, admin_headers, monkeypatch):
        calls = _capture(monkeypatch)
        messages = [
            {"role": "user", "content": "Что сегодня в расписании?"},
            {"role": "assistant", "content": "Три заезда утром."},
            {"role": "user", "content": "Что требует внимания?"},
        ]

        res = await client.post(
            "/api/ai/manager",
            json={"messages": messages, "tz_offset": 180},
            headers=admin_headers,
        )

        assert res.status_code == 200
        assert res.json() == {"response": "ok"}
        assert calls[0]["prompt_name"] == "manager"
        assert calls[0]["messages"] == messages
        assert calls[0]["tz_offset"] == 180

    async def test_question_only_still_supported(self, client, admin_headers, monkeypatch):
        calls = _capture(monkeypatch)

        res = await client.post(
            "/api/ai/manager",
            json={"question": "Что сегодня в расписании?"},
            headers=admin_headers,
        )

        assert res.status_code == 200
        assert calls[0]["messages"] == [
            {"role": "user", "content": "Что сегодня в расписании?"},
        ]

    async def test_empty_request_rejected(self, client, admin_headers):
        res = await client.post("/api/ai/manager", json={"tz_offset": 0}, headers=admin_headers)
        assert res.status_code == 422


class TestAdminChat:
    async def test_history_goes_to_admin_prompt(self, client, admin_headers, monkeypatch):
        calls = _capture(monkeypatch)
        messages = [
            {"role": "user", "content": "Покажи услуги и цены"},
            {"role": "assistant", "content": "Вот список услуг."},
            {"role": "user", "content": "Подними цену полировки на 500"},
        ]

        res = await client.post(
            "/api/ai/admin",
            json={"messages": messages, "tz_offset": 180},
            headers=admin_headers,
        )

        assert res.status_code == 200
        assert calls[0]["prompt_name"] == "admin"
        assert calls[0]["messages"] == messages
