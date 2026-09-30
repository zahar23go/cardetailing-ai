"""Загрузчик промптов из YAML с hot-reload.

Промпты лежат в каталоге ``prompts/`` (см. ``PROMPTS_DIR``). Файл кэшируется
по mtime: после правки YAML следующий вызов подхватит изменения без пересборки
и перезапуска приложения.

Формат файла (пример ``prompts/detailer.yaml``)::

    detailer:
      system: |
        ...
      greeting: |
        ...
      functions:
        - name: get_client_profile
          description: ...
          parameters: {type: object, properties: {}}

``load_prompt("detailer")`` вернёт словарь секции ``detailer``.
"""
from __future__ import annotations

import os
from pathlib import Path

import yaml

# backend/app/core/prompt_loader.py -> parents: core, app, backend, <repo root>
_REPO_ROOT = Path(__file__).resolve().parents[3]
_BACKEND_ROOT = Path(__file__).resolve().parents[2]

_cache: dict[str, tuple[float, dict]] = {}


def prompts_dir() -> Path:
    """Каталог с промптами: env ``PROMPTS_DIR`` → известные пути → repo/prompts."""
    candidates: list[Path] = []
    env_dir = os.getenv("PROMPTS_DIR")
    if env_dir:
        candidates.append(Path(env_dir))
    # Типовые места: docker-образ и локальная разработка
    candidates.append(Path("/app/prompts"))
    candidates.append(_REPO_ROOT / "prompts")
    candidates.append(_BACKEND_ROOT / "prompts")
    candidates.append(Path.cwd() / "prompts")
    for candidate in candidates:
        if candidate.is_dir():
            return candidate
    # Ничего не нашли — вернём первый кандидат, чтобы ошибка указала ожидаемый путь
    return candidates[0]


def prompt_path(name: str) -> Path:
    """Путь к файлу промпта ``name`` (без расширения)."""
    base = prompts_dir()
    for suffix in (".yaml", ".yml"):
        path = base / f"{name}{suffix}"
        if path.is_file():
            return path
    return base / f"{name}.yaml"


def list_prompts() -> list[str]:
    """Имена доступных промптов (файлы ``*.yaml``/``*.yml`` без расширения)."""
    base = prompts_dir()
    if not base.is_dir():
        return []
    return sorted(p.stem for p in base.iterdir() if p.suffix in (".yaml", ".yml"))


def load_prompt(name: str) -> dict:
    """Прочитать секцию промпта ``name`` из YAML.

    Кэш инвалидируется по mtime файла, поэтому правки видны на лету.
    """
    path = prompt_path(name)
    if not path.is_file():
        raise FileNotFoundError(f"Промпт '{name}' не найден: {path}")

    mtime = path.stat().st_mtime
    cache_key = str(path)
    cached = _cache.get(cache_key)
    if cached and cached[0] == mtime:
        return cached[1]

    with path.open("r", encoding="utf-8") as fh:
        data = yaml.safe_load(fh)

    if not isinstance(data, dict):
        raise ValueError(f"Промпт '{name}' должен быть словарём (YAML-маппингом)")
    # detailer.yaml хранит данные под собственным ключом; иначе берём весь документ.
    section = data.get(name, data)
    if not isinstance(section, dict):
        raise ValueError(f"Секция '{name}' в {path} должна быть словарём")

    _cache[cache_key] = (mtime, section)
    return section


def clear_cache() -> None:
    """Сбросить кэш промптов (для тестов)."""
    _cache.clear()
