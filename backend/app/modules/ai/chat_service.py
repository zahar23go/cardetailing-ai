"""Оркестратор чата ИИ-консультанта.

Читает промпт из файла (prompts/<name>.yaml) на каждом запросе — правки видны
без пересборки. Собирает системное сообщение (промпт + каталог студии), прогоняет
цикл функциональных вызовов из секции ``functions`` и возвращает финальный текст.

Сервер не хранит состояние: историю диалога присылает клиент.
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.deepseek_client import chat_with_tools
from app.core.prompt_loader import load_prompt
from app.models import MasterSkill, User
from app.modules.ai.detailer_service import load_catalog
from app.modules.ai.detailer_tools import DetailerTools, dispatch

MAX_TOOL_ITERATIONS = 5


def build_tools(functions: list[dict] | None) -> list[dict]:
    """Секция ``functions`` из YAML → схема tools для OpenAI-совместимого API."""
    tools: list[dict] = []
    for fn in functions or []:
        name = fn.get("name")
        if not name:
            continue
        tools.append(
            {
                "type": "function",
                "function": {
                    "name": name,
                    "description": fn.get("description", ""),
                    "parameters": fn.get("parameters") or {"type": "object", "properties": {}},
                },
            }
        )
    return tools


async def build_catalog_context(db: AsyncSession, tenant_id: UUID) -> str:
    """Актуальный каталог услуг и мастеров для системного сообщения."""
    services = await load_catalog(db, tenant_id)
    lines = ["КАТАЛОГ СТУДИИ (используй только эти данные, не выдумывай):", "Услуги:"]
    if services:
        for service in services:
            desc = f" — {service.description}" if service.description else ""
            lines.append(
                f"• {service.name} (категория: {service.category or 'без категории'}), "
                f"{float(service.price or 0):.0f} руб., ~{int(service.duration or 0)} мин.{desc}"
            )
    else:
        lines.append("• Каталог услуг пуст.")

    masters_result = await db.execute(
        select(User).where(User.tenant_id == tenant_id, User.role == "master")
    )
    masters = list(masters_result.scalars().all())
    if masters:
        skills_result = await db.execute(
            select(MasterSkill)
            .options(selectinload(MasterSkill.service))
            .where(MasterSkill.tenant_id == tenant_id)
        )
        by_master: dict[int, list[str]] = {}
        for skill in skills_result.scalars().all():
            if skill.service is not None:
                by_master.setdefault(skill.master_id, []).append(skill.service.name)
        lines.append("Мастера:")
        for master in masters:
            skills = ", ".join(by_master.get(master.id, [])) or "универсал"
            lines.append(f"• {master.full_name} — {skills}")

    return "\n".join(lines)


def _assistant_tool_message(message) -> dict:
    return {
        "role": "assistant",
        "content": message.content or None,
        "tool_calls": [
            {
                "id": call.id,
                "type": "function",
                "function": {"name": call.function.name, "arguments": call.function.arguments or "{}"},
            }
            for call in message.tool_calls
        ],
    }


def _parse_arguments(call) -> dict:
    try:
        return json.loads(call.function.arguments or "{}")
    except (json.JSONDecodeError, TypeError):
        return {}


async def run_consultant_chat(
    db: AsyncSession,
    tenant_id: UUID,
    client: dict,
    messages: list[dict],
    *,
    tz_offset: int = 0,
    prompt_name: str = "detailer",
) -> dict:
    """Прогнать ход диалога через промпт из файла и вернуть ответ консультанта."""
    try:
        section = load_prompt(prompt_name)
    except (FileNotFoundError, ValueError) as exc:
        return {"response": f"Промпт «{prompt_name}» недоступен: {exc}"}

    catalog = await build_catalog_context(db, tenant_id)
    system_content = f"{section.get('system', '').strip()}\n\n{catalog}"

    greeting = (section.get("greeting") or "").strip()
    chat_messages: list[dict] = [{"role": "system", "content": system_content}]
    # Приветствие задаёт голос Максима, если клиент ещё не видел ответов.
    if greeting and not any(m.get("role") == "assistant" for m in messages):
        chat_messages.append({"role": "assistant", "content": greeting})
    for message in messages:
        role, content = message.get("role"), message.get("content", "")
        if role in ("user", "assistant") and content:
            chat_messages.append({"role": role, "content": content})

    tools = build_tools(section.get("functions"))
    runner = DetailerTools(db, tenant_id, client, tz_offset)
    last_text = ""

    for _ in range(MAX_TOOL_ITERATIONS):
        try:
            message = await chat_with_tools(chat_messages, tools)
        except Exception as exc:  # сеть/ключ/лимиты — не роняем чат
            return {"response": last_text or f"Ошибка при обращении к AI: {exc}"}

        tool_calls = getattr(message, "tool_calls", None)
        if not tool_calls:
            return {"response": message.content or last_text or greeting}

        chat_messages.append(_assistant_tool_message(message))
        for call in tool_calls:
            result = await dispatch(runner, call.function.name, _parse_arguments(call))
            chat_messages.append(
                {
                    "role": "tool",
                    "tool_call_id": call.id,
                    "content": json.dumps(result, ensure_ascii=False, default=str),
                }
            )
        last_text = message.content or last_text

    try:
        message = await chat_with_tools(chat_messages, None)
        return {"response": message.content or last_text}
    except Exception as exc:
        return {"response": last_text or f"Ошибка при обращении к AI: {exc}"}
