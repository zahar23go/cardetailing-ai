"""Защита от print() с символами вне cp1251 (падение на Windows-консоли)."""

import ast
from pathlib import Path

APP_DIR = Path(__file__).resolve().parents[1] / "app"


def _unsupported_chars(text: str) -> list[str]:
    chars: list[str] = []
    for ch in text:
        try:
            ch.encode("cp1251")
        except UnicodeEncodeError:
            if ch not in chars:
                chars.append(ch)
    return chars


def test_print_calls_are_cp1251_safe() -> None:
    """Все print() в приложении должны безопасно писаться в cp1251-консоль."""
    offenders: list[str] = []
    for path in APP_DIR.rglob("*.py"):
        if "__pycache__" in path.parts:
            continue
        tree = ast.parse(path.read_text(encoding="utf-8"))
        for node in ast.walk(tree):
            if not (
                isinstance(node, ast.Call)
                and isinstance(node.func, ast.Name)
                and node.func.id == "print"
            ):
                continue
            for sub in ast.walk(node):
                if isinstance(sub, ast.Constant) and isinstance(sub.value, str):
                    bad = _unsupported_chars(sub.value)
                    if bad:
                        offenders.append(
                            f"{path.relative_to(APP_DIR)}:{sub.lineno} "
                            f"-> {''.join(bad)!a}"
                        )
    assert not offenders, "print() с символами вне cp1251:\n" + "\n".join(offenders)
