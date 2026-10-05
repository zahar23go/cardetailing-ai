"""Разбор текстовых вызовов функций модели (когда API вернул разметку вместо structured tool_calls).

Некоторые модели при включённом tool-calling всё равно отдают вызов функции служебными
токенами прямо в ``content`` (например ``DSML``-разметка с ``invoke``/``parameter``).
Такую разметку нельзя показывать клиенту: её нужно (а) по возможности выполнить и
(б) в любом случае вырезать из текста ответа.

Модуль намеренно толерантен: точные спец-токены могут отличаться, поэтому детект идёт
по подстроке ``DSML`` и по ключевым словам ``invoke``/``parameter``, а значения параметров
обрезаются по ближайшему служебному разделителю.
"""
from __future__ import annotations

import json
import re

# Открывающая часть служебного токена, после которой в тексте остаётся имя "DSML".
_MARKER_CHARS = "<|｜"

_INVOKE_RE = re.compile(r'invoke\s+name\s*=\s*"([^"]+)"', re.IGNORECASE)
_PARAM_RE = re.compile(
    r'parameter\s+name\s*=\s*"([^"]+)"\s+string\s*=\s*"(true|false)"\s*>',
    re.IGNORECASE,
)
# Хвостовая разметка/закрывающий токен в значении параметра.
_TRAILING = re.compile(r"[<｜|].*$", re.DOTALL)


def contains_tool_markup(text: str | None) -> bool:
    """Похоже ли содержимое на текстовый вызов функции (служебная разметка)."""
    if not text:
        return False
    if "DSML" in text:
        return True
    return bool(_INVOKE_RE.search(text) and "parameter" in text.lower())


def _coerce(raw: str, is_string: bool):
    value = _TRAILING.sub("", raw).strip()
    if is_string:
        return value
    try:
        return json.loads(value)
    except (json.JSONDecodeError, TypeError):
        return value


def extract_tool_calls(text: str | None) -> list[dict]:
    """Вытащить вызовы функций из текста: ``[{"name": ..., "arguments": {...}}, ...]``."""
    if not text or not contains_tool_markup(text):
        return []

    calls: list[dict] = []
    invokes = list(_INVOKE_RE.finditer(text))
    for i, invoke in enumerate(invokes):
        block_end = invokes[i + 1].start() if i + 1 < len(invokes) else len(text)
        block = text[invoke.end():block_end]
        params = list(_PARAM_RE.finditer(block))
        arguments: dict = {}
        for j, param in enumerate(params):
            value_end = params[j + 1].start() if j + 1 < len(params) else len(block)
            arguments[param.group(1)] = _coerce(
                block[param.end():value_end],
                param.group(2).lower() == "true",
            )
        calls.append({"name": invoke.group(1), "arguments": arguments})
    return calls


def strip_tool_markup(text: str | None) -> str:
    """Убрать служебную разметку вызова из текста, оставив только чистый ответ."""
    if not text:
        return ""

    starts = []
    if "DSML" in text:
        starts.append(text.find("DSML"))
    invoke = _INVOKE_RE.search(text)
    if invoke:
        starts.append(invoke.start())
    if not starts:
        return text.strip()

    start = min(starts)
    while start > 0 and text[start - 1] in _MARKER_CHARS:
        start -= 1

    last = text.rfind("DSML")
    if last > start:
        close = text.find(">", last)
        end = close + 1 if close != -1 else len(text)
    else:
        end = len(text)

    cleaned = f"{text[:start]}{text[end:]}".strip()
    # Подчищаем осевшие служебные слова, если токены разошлись не идеально.
    cleaned = re.sub(r"\b(?:function_calls|calls)\b", "", cleaned).strip()
    return cleaned
