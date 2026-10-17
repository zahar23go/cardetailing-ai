"""Аналитика диалогов с ИИ-ассистентами.

Пишет каждый ход чата в ``ai_chat_logs`` (вопрос, ответ, инструменты, время),
считает метрики для админки и чистит текст старше ``AI_CHAT_RETENTION_DAYS``.

Логирование и очистка не должны ломать сам чат: ошибки печатаются и глотаются.
"""
from __future__ import annotations

from collections import Counter, defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import case, delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models import AiChatLog, User

# Больше строк за период не анализируем — защита от гигантских выборок.
MAX_ANALYZED_TURNS = 5000
_PURGE_INTERVAL = timedelta(hours=1)
_purge_seen: dict[str, datetime] = {}


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _iso(value: datetime | str | None) -> str | None:
    if value is None or isinstance(value, str):
        return value
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.isoformat()


def _normalize_question(text: str) -> str:
    return " ".join((text or "").lower().split())


async def log_turn(
    db: AsyncSession,
    *,
    tenant_id: UUID,
    user_id: int | None,
    session_id: str,
    assistant: str,
    question: str,
    answer: str,
    tool_calls: list[str] | None = None,
    duration_ms: int = 0,
    is_error: bool = False,
) -> None:
    """Записать ход диалога. Сбой логирования не должен ломать чат."""
    try:
        db.add(
            AiChatLog(
                tenant_id=tenant_id,
                user_id=user_id,
                session_id=session_id[:64],
                assistant=assistant[:32],
                question=question,
                answer=answer,
                tool_calls=tool_calls or [],
                duration_ms=max(0, duration_ms),
                is_error=is_error,
            )
        )
        await db.commit()
    except Exception as exc:  # noqa: BLE001 — аналитика не важнее ответа клиенту
        await db.rollback()
        print(f"[ai-analytics] log error: {exc}")
        return
    await _maybe_purge(db, tenant_id)


async def _maybe_purge(db: AsyncSession, tenant_id: UUID) -> None:
    """Чистка старых записей не чаще раза в час на тенант."""
    now = _now()
    key = str(tenant_id)
    last = _purge_seen.get(key)
    if last and now - last < _PURGE_INTERVAL:
        return
    _purge_seen[key] = now
    try:
        await purge_expired(db, tenant_id)
    except Exception as exc:  # noqa: BLE001
        print(f"[ai-analytics] purge error: {exc}")


async def purge_expired(db: AsyncSession, tenant_id: UUID | None = None) -> int:
    """Удалить ходы старше срока хранения. ``days <= 0`` — хранение без ограничения."""
    days = settings.AI_CHAT_RETENTION_DAYS
    if days <= 0:
        return 0
    cutoff = _now() - timedelta(days=days)
    stmt = delete(AiChatLog).where(AiChatLog.created_at < cutoff)
    if tenant_id is not None:
        stmt = stmt.where(AiChatLog.tenant_id == tenant_id)
    result = await db.execute(stmt)
    await db.commit()
    return result.rowcount or 0


async def build_overview(db: AsyncSession, tenant_id: UUID, period_days: int = 30) -> dict:
    """KPI, динамика по дням, распределение по ассистентам, топ вопросов и функций."""
    days = max(1, min(period_days, 365))
    now = _now()
    start = now - timedelta(days=days)
    await purge_expired(db, tenant_id)

    rows = list(
        (
            await db.execute(
                select(AiChatLog)
                .where(AiChatLog.tenant_id == tenant_id, AiChatLog.created_at >= start)
                .order_by(AiChatLog.created_at)
                .limit(MAX_ANALYZED_TURNS)
            )
        ).scalars().all()
    )

    turns = len(rows)
    sessions = {row.session_id for row in rows}
    users = {row.user_id for row in rows if row.user_id is not None}
    errors = sum(1 for row in rows if row.is_error)
    durations = [row.duration_ms for row in rows if row.duration_ms]

    by_assistant = Counter(row.assistant for row in rows)
    tools: Counter[str] = Counter()
    for row in rows:
        for name in row.tool_calls or []:
            tools[name] += 1

    questions: Counter[str] = Counter()
    examples: dict[str, str] = {}
    for row in rows:
        key = _normalize_question(row.question)
        if len(key) < 4:
            continue
        questions[key] += 1
        examples.setdefault(key, row.question.strip())

    daily_turns: Counter[str] = Counter()
    daily_sessions: dict[str, set[str]] = defaultdict(set)
    for row in rows:
        day = _iso(row.created_at) or ""
        day = day[:10]
        daily_turns[day] += 1
        daily_sessions[day].add(row.session_id)

    daily: list[dict] = []
    cursor = start.date()
    today = now.date()
    while cursor <= today:
        key = cursor.isoformat()
        daily.append(
            {
                "date": key,
                "turns": daily_turns.get(key, 0),
                "dialogs": len(daily_sessions.get(key, ())),
            }
        )
        cursor += timedelta(days=1)

    return {
        "period_days": days,
        "retention_days": settings.AI_CHAT_RETENTION_DAYS,
        "dialogs": len(sessions),
        "turns": turns,
        "users": len(users),
        "errors": errors,
        "error_rate_pct": round(100.0 * errors / turns, 1) if turns else 0.0,
        "avg_response_ms": int(sum(durations) / len(durations)) if durations else 0,
        "by_assistant": [
            {
                "assistant": name,
                "turns": count,
                "share_pct": round(100.0 * count / turns, 1) if turns else 0.0,
            }
            for name, count in by_assistant.most_common()
        ],
        "daily": daily,
        "top_questions": [
            {"text": examples.get(key, key), "count": count}
            for key, count in questions.most_common(10)
        ],
        "top_tools": [{"name": name, "count": count} for name, count in tools.most_common(10)],
    }


async def list_dialogs(db: AsyncSession, tenant_id: UUID, limit: int = 20, offset: int = 0) -> dict:
    """Последние диалоги: одна строка на сессию + первая реплика пользователя."""
    has_error = func.max(case((AiChatLog.is_error.is_(True), 1), else_=0))

    sessions = (
        await db.execute(
            select(
                AiChatLog.session_id,
                func.min(AiChatLog.created_at).label("first_at"),
                func.max(AiChatLog.created_at).label("last_at"),
                func.count(AiChatLog.id).label("turns"),
                func.max(AiChatLog.user_id).label("user_id"),
                func.max(AiChatLog.assistant).label("assistant"),
                has_error.label("has_error"),
            )
            .where(AiChatLog.tenant_id == tenant_id)
            .group_by(AiChatLog.session_id)
            .order_by(func.max(AiChatLog.created_at).desc())
            .limit(limit)
            .offset(offset)
        )
    ).all()

    total = (
        await db.execute(
            select(func.count(func.distinct(AiChatLog.session_id))).where(
                AiChatLog.tenant_id == tenant_id
            )
        )
    ).scalar_one()

    session_ids = [row.session_id for row in sessions]
    first_question: dict[str, str] = {}
    user_names: dict[int, str] = {}
    if session_ids:
        first_rows = (
            await db.execute(
                select(AiChatLog.session_id, AiChatLog.question, AiChatLog.created_at)
                .where(AiChatLog.tenant_id == tenant_id, AiChatLog.session_id.in_(session_ids))
                .order_by(AiChatLog.created_at)
            )
        ).all()
        for session_id, question, _created in first_rows:
            first_question.setdefault(session_id, question)

        user_ids = {row.user_id for row in sessions if row.user_id is not None}
        if user_ids:
            user_rows = (
                await db.execute(select(User.id, User.full_name).where(User.id.in_(user_ids)))
            ).all()
            user_names = {user_id: full_name for user_id, full_name in user_rows}

    items = [
        {
            "session_id": row.session_id,
            "assistant": row.assistant,
            "turns": row.turns,
            "user_name": user_names.get(row.user_id) if row.user_id is not None else None,
            "first_question": first_question.get(row.session_id),
            "first_at": _iso(row.first_at),
            "last_at": _iso(row.last_at),
            "has_error": bool(row.has_error),
        }
        for row in sessions
    ]
    return {"items": items, "total": total, "limit": limit, "offset": offset}


async def get_dialog(db: AsyncSession, tenant_id: UUID, session_id: str) -> dict | None:
    """Полная переписка одной сессии (в пределах тенанта)."""
    rows = list(
        (
            await db.execute(
                select(AiChatLog)
                .where(AiChatLog.tenant_id == tenant_id, AiChatLog.session_id == session_id)
                .order_by(AiChatLog.created_at)
            )
        ).scalars().all()
    )
    if not rows:
        return None

    user_name = None
    user_id = next((row.user_id for row in rows if row.user_id is not None), None)
    if user_id is not None:
        user_name = (
            await db.execute(select(User.full_name).where(User.id == user_id))
        ).scalar_one_or_none()

    return {
        "session_id": session_id,
        "assistant": rows[0].assistant,
        "user_name": user_name,
        "turns": [
            {
                "question": row.question,
                "answer": row.answer,
                "tool_calls": row.tool_calls or [],
                "duration_ms": row.duration_ms,
                "is_error": row.is_error,
                "created_at": _iso(row.created_at),
            }
            for row in rows
        ],
    }
