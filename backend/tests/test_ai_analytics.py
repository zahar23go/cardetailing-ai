"""Тесты аналитики диалогов: журнал, метрики, список диалогов, ретеншн, права."""

from datetime import datetime, timedelta, timezone
from types import SimpleNamespace
from uuid import uuid4

from app.core.config import settings
from app.models import AiChatLog
from app.modules.ai import analytics_service, chat_service


async def _log(
    db,
    tenant,
    user,
    *,
    session="s1",
    assistant="detailer",
    question="Вопрос?",
    answer="Ответ",
    tools=None,
    duration=100,
    is_error=False,
    created_at=None,
):
    row = AiChatLog(
        tenant_id=tenant.id,
        user_id=user.id,
        session_id=session,
        assistant=assistant,
        question=question,
        answer=answer,
        tool_calls=tools or [],
        duration_ms=duration,
        is_error=is_error,
    )
    if created_at is not None:
        row.created_at = created_at
    db.add(row)
    await db.commit()
    return row


class TestOverview:
    async def test_counts_dialogs_users_errors_and_avg(
        self, db_session, default_tenant, test_user, test_master,
    ):
        await _log(db_session, default_tenant, test_user, session="a", duration=100)
        await _log(db_session, default_tenant, test_user, session="a", duration=300)
        await _log(
            db_session, default_tenant, test_master, session="b",
            duration=200, is_error=True,
        )

        data = await analytics_service.build_overview(db_session, default_tenant.id, 30)

        assert data["dialogs"] == 2
        assert data["turns"] == 3
        assert data["users"] == 2
        assert data["errors"] == 1
        assert data["error_rate_pct"] == 33.3
        assert data["avg_response_ms"] == 200
        assert len(data["daily"]) == 31  # сегодня + 30 дней периода

    async def test_top_questions_and_tools(
        self, db_session, default_tenant, test_user,
    ):
        await _log(
            db_session, default_tenant, test_user, session="a",
            question="Сколько стоит полировка?",
            tools=["list_services", "create_appointment"],
        )
        await _log(
            db_session, default_tenant, test_user, session="b",
            question="сколько   стоит полировка?",
            tools=["list_services"],
        )

        data = await analytics_service.build_overview(db_session, default_tenant.id, 30)

        assert data["top_questions"][0]["count"] == 2
        assert data["top_tools"][0] == {"name": "list_services", "count": 2}

    async def test_period_filter(self, db_session, default_tenant, test_user):
        old = datetime.now(timezone.utc) - timedelta(days=40)
        await _log(db_session, default_tenant, test_user, session="old", created_at=old)
        await _log(db_session, default_tenant, test_user, session="new")

        recent = await analytics_service.build_overview(db_session, default_tenant.id, 7)
        long = await analytics_service.build_overview(db_session, default_tenant.id, 90)

        assert recent["dialogs"] == 1
        assert long["dialogs"] == 2


class TestDialogs:
    async def test_list_and_detail(self, db_session, default_tenant, test_user):
        await _log(
            db_session, default_tenant, test_user, session="s-1",
            question="Что сегодня в расписании?",
        )
        await _log(
            db_session, default_tenant, test_user, session="s-1",
            question="А завтра?",
        )
        await _log(
            db_session, default_tenant, test_user, session="s-2",
            assistant="manager", question="Где просадка?",
        )

        listing = await analytics_service.list_dialogs(db_session, default_tenant.id)

        assert listing["total"] == 2
        by_session = {item["session_id"]: item for item in listing["items"]}
        assert by_session["s-1"]["turns"] == 2
        assert by_session["s-1"]["first_question"] == "Что сегодня в расписании?"
        assert by_session["s-1"]["user_name"] == test_user.full_name
        assert by_session["s-2"]["assistant"] == "manager"

        detail = await analytics_service.get_dialog(db_session, default_tenant.id, "s-1")
        assert detail is not None
        assert [turn["question"] for turn in detail["turns"]] == [
            "Что сегодня в расписании?",
            "А завтра?",
        ]

    async def test_detail_isolated_by_tenant(self, db_session, default_tenant, test_user):
        await _log(db_session, default_tenant, test_user, session="s-1")

        other_tenant_id = uuid4()

        assert await analytics_service.get_dialog(db_session, other_tenant_id, "s-1") is None


class TestRetention:
    async def test_purge_removes_old_rows(self, monkeypatch, db_session, default_tenant, test_user):
        monkeypatch.setattr(settings, "AI_CHAT_RETENTION_DAYS", 1)
        old = datetime.now(timezone.utc) - timedelta(days=3)
        await _log(db_session, default_tenant, test_user, session="old", created_at=old)
        await _log(db_session, default_tenant, test_user, session="new")

        removed = await analytics_service.purge_expired(db_session, default_tenant.id)

        assert removed == 1
        listing = await analytics_service.list_dialogs(db_session, default_tenant.id)
        assert [item["session_id"] for item in listing["items"]] == ["new"]


class TestChatLogging:
    async def test_turn_is_logged_with_session_and_tools(
        self, monkeypatch, db_session, default_tenant, test_user,
    ):
        async def fake_chat_with_tools(messages, tools=None):
            return SimpleNamespace(content="Возьмите комплексную мойку.", tool_calls=None)

        monkeypatch.setattr(chat_service, "chat_with_tools", fake_chat_with_tools)

        response = await chat_service.run_consultant_chat(
            db_session,
            default_tenant.id,
            {"id": test_user.id, "role": "client"},
            [{"role": "user", "content": "Что посоветуете?"}],
            prompt_name="detailer",
            session_id="sess-42",
        )

        assert response["response"]
        listing = await analytics_service.list_dialogs(db_session, default_tenant.id)
        assert listing["total"] == 1
        item = listing["items"][0]
        assert item["session_id"] == "sess-42"
        assert item["assistant"] == "detailer"
        detail = await analytics_service.get_dialog(db_session, default_tenant.id, "sess-42")
        assert detail["turns"][0]["question"] == "Что посоветуете?"
        assert detail["turns"][0]["answer"] == "Возьмите комплексную мойку."


class TestAnalyticsAccess:
    async def test_forbidden_for_client(self, client, auth_headers):
        res = await client.get("/api/ai/analytics/overview", headers=auth_headers)
        assert res.status_code == 403

    async def test_forbidden_for_master(self, client, master_headers):
        res = await client.get("/api/ai/analytics/dialogs", headers=master_headers)
        assert res.status_code == 403

    async def test_overview_as_admin(self, client, admin_headers, db_session, default_tenant, test_user):
        await _log(db_session, default_tenant, test_user, session="s-1")

        res = await client.get("/api/ai/analytics/overview?period_days=7", headers=admin_headers)

        assert res.status_code == 200
        data = res.json()
        assert data["period_days"] == 7
        assert data["turns"] == 1

    async def test_unknown_dialog_returns_404(self, client, admin_headers):
        res = await client.get("/api/ai/analytics/dialogs/missing", headers=admin_headers)
        assert res.status_code == 404
