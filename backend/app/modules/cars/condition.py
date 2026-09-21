"""Состояние и особенности авто, важные мастеру.

Тип краски, дефекты стекла и особые требования к уходу — фиксированные
списки (стабильные id) плюс свободный комментарий. Одни и те же данные
хранятся в профиле авто и снимком на конкретный визит.
"""
from __future__ import annotations

PAINT_TYPES: list[dict] = [
    {"id": "lacquer", "label": "Лак"},
    {"id": "ceramic", "label": "Керамика"},
    {"id": "film", "label": "Плёнка"},
    {"id": "unknown", "label": "Не знаю"},
]

GLASS_DEFECTS: list[dict] = [
    {"id": "chips", "label": "Сколы на лобовом"},
    {"id": "cracks", "label": "Трещины на лобовом"},
]

CARE_REQUIREMENTS: list[dict] = [
    {"id": "acid_free_shampoo", "label": "Бескислотный шампунь"},
    {"id": "soft_wash", "label": "Мягкая мойка"},
    {"id": "no_wax", "label": "Без воска и полироли"},
    {"id": "hand_dry", "label": "Только ручная сушка"},
]

_PAINT_IDS = {item["id"] for item in PAINT_TYPES}
_GLASS_IDS = [item["id"] for item in GLASS_DEFECTS]
_CARE_IDS = [item["id"] for item in CARE_REQUIREMENTS]


def catalog() -> dict:
    """Справочники опций для интерфейса."""
    return {
        "paint_types": PAINT_TYPES,
        "glass_defects": GLASS_DEFECTS,
        "care_requirements": CARE_REQUIREMENTS,
    }


def _clean_ids(values, allowed_order: list[str]) -> list[str]:
    """Оставить только известные id, без дублей, в порядке справочника."""
    if not values:
        return []
    chosen = {str(v) for v in values}
    return [i for i in allowed_order if i in chosen]


def clean_condition(
    paint_type: str | None,
    glass_defects,
    care_requirements,
    notes: str | None,
) -> dict:
    """Нормализовать состояние: валидные id и обрезанный комментарий."""
    return {
        "paint_type": paint_type if paint_type in _PAINT_IDS else None,
        "glass_defects": _clean_ids(glass_defects, _GLASS_IDS),
        "care_requirements": _clean_ids(care_requirements, _CARE_IDS),
        "notes": (notes or "").strip() or None,
    }


def condition_from_car(car) -> dict:
    """Состояние из профиля авто."""
    if car is None:
        return {"paint_type": None, "glass_defects": [], "care_requirements": [], "notes": None}
    return clean_condition(
        getattr(car, "paint_type", None),
        getattr(car, "glass_defects", None),
        getattr(car, "care_requirements", None),
        getattr(car, "condition_notes", None),
    )


def effective_condition(car, snapshot) -> dict:
    """Снимок на визит, если он есть, иначе профиль авто."""
    if snapshot:
        return clean_condition(
            snapshot.get("paint_type"),
            snapshot.get("glass_defects"),
            snapshot.get("care_requirements"),
            snapshot.get("notes"),
        )
    return condition_from_car(car)
