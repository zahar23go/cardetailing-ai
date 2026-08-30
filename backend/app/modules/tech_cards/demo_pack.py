"""Демо-контент: 6 техкарт заказчика + номенклатура склада.

Оборудование не заводим отдельным справочником — только в тексте шагов и notes.
Повторный запуск идемпотентен: карты с маркером demo-pack-6 обновляются,
чужие техкарты не трогаем.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Material, Service, TechCard
from app.modules.tech_cards.service import create_tech_card, update_tech_card
from app.schemas import TechCardBlockIn, TechCardCreate, TechCardItemIn, TechCardUpdate

MARKER = "demo-pack-6"

# key → склад
MATERIALS: dict[str, dict] = {
    "foam": {"name": "Шампунь активная пена", "unit": "ml", "price": 0.50, "qty": 8000, "min": 500, "cat": "chemistry"},
    "water": {"name": "Вода техническая", "unit": "l", "price": 0.05, "qty": 2000, "min": 200, "cat": "other"},
    "antirain": {"name": "Антидождь", "unit": "ml", "price": 1.20, "qty": 800, "min": 80, "cat": "chemistry"},
    "wheel": {"name": "Шампунь для дисков (кислотный)", "unit": "ml", "price": 0.80, "qty": 2000, "min": 200, "cat": "chemistry"},
    "salon_wet": {"name": "Средство для химчистки салона", "unit": "ml", "price": 1.50, "qty": 3000, "min": 300, "cat": "chemistry"},
    "microfiber": {"name": "Салфетки микрофибра", "unit": "pcs", "price": 15, "qty": 250, "min": 30, "cat": "consumables"},
    "degreaser": {"name": "Обезжириватель", "unit": "ml", "price": 0.50, "qty": 4000, "min": 400, "cat": "chemistry"},
    "abrasive": {"name": "Паста абразивная (грубая)", "unit": "ml", "price": 1.80, "qty": 2500, "min": 200, "cat": "chemistry"},
    "finish": {"name": "Паста финишная (полировальная)", "unit": "ml", "price": 2.50, "qty": 1500, "min": 150, "cat": "chemistry"},
    "wax": {"name": "Воск / герметик для защиты", "unit": "ml", "price": 1.20, "qty": 1500, "min": 150, "cat": "chemistry"},
    "pad_coarse": {"name": "Полировальный круг (грубый)", "unit": "pcs", "price": 300, "qty": 20, "min": 4, "cat": "consumables"},
    "pad_soft": {"name": "Полировальный круг (мягкий)", "unit": "pcs", "price": 350, "qty": 20, "min": 4, "cat": "consumables"},
    "tape": {"name": "Малярный скотч", "unit": "m", "price": 4, "qty": 200, "min": 20, "cat": "consumables"},
    "ceramic": {"name": "Керамическое покрытие 9H", "unit": "ml", "price": 100, "qty": 240, "min": 30, "cat": "chemistry"},
    "applicator": {"name": "Аппликатор (губка)", "unit": "pcs", "price": 50, "qty": 40, "min": 6, "cat": "consumables"},
    "polish_cloth": {"name": "Салфетка для полировки", "unit": "pcs", "price": 15, "qty": 80, "min": 10, "cat": "consumables"},
    "sandpaper": {"name": "Шлифовальная бумага P1500–P3000", "unit": "pcs", "price": 50, "qty": 60, "min": 9, "cat": "consumables"},
    "paint": {"name": "Набор для подбора краски", "unit": "ml", "price": 20, "qty": 80, "min": 10, "cat": "chemistry"},
    "lacquer": {"name": "Лак для фиксации", "unit": "ml", "price": 5, "qty": 200, "min": 20, "cat": "chemistry"},
    "chip_paste": {"name": "Полировальная паста", "unit": "ml", "price": 2.50, "qty": 800, "min": 80, "cat": "chemistry"},
    "extract_shampoo": {"name": "Шампунь для химчистки салона", "unit": "ml", "price": 2.00, "qty": 2500, "min": 200, "cat": "chemistry"},
    "stain": {"name": "Пятновыводитель для ткани", "unit": "ml", "price": 3.00, "qty": 800, "min": 80, "cat": "chemistry"},
    "leather": {"name": "Средство для кожи (кондиционер)", "unit": "ml", "price": 2.50, "qty": 1000, "min": 100, "cat": "chemistry"},
    "brush": {"name": "Щётка мягкая", "unit": "pcs", "price": 100, "qty": 12, "min": 2, "cat": "inventory"},
}

# canonical name, aliases to reuse existing catalog, price, duration min, category
SERVICES: list[dict] = [
    {
        "key": "wash",
        "name": "Бесконтактная мойка кузова",
        "aliases": ["Мойка кузова", "Бесконтактная мойка"],
        "price": 1800,
        "duration": 15,
        "category": "Мойка",
        "description": "Снятие грязи пеной и водой высокого давления без касания кузова.",
    },
    {
        "key": "complex",
        "name": "Комплексная мойка",
        "aliases": ["Комплексная мойка (кузов + салон + диски)"],
        "price": 4500,
        "duration": 40,
        "category": "Мойка",
        "description": "Кузов, диски и влажная уборка салона.",
    },
    {
        "key": "polish",
        "name": "Полировка кузова",
        "aliases": ["Полировка кузова (стандартная)"],
        "price": 12000,
        "duration": 120,
        "category": "Полировка",
        "description": "Абразив + финиш + защита. Возврат блеска ЛКП.",
    },
    {
        "key": "ceramic",
        "name": "Керамическое покрытие 9H",
        "aliases": ["Нанесение керамического покрытия 9H", "Керамика"],
        "price": 28000,
        "duration": 120,
        "category": "Защита",
        "description": "Жидкая керамика, гидрофоб и защита до 3 лет.",
    },
    {
        "key": "chips",
        "name": "Локальный ремонт сколов",
        "aliases": ["Локальный ремонт сколов и царапин"],
        "price": 5500,
        "duration": 70,
        "category": "Кузов",
        "description": "Скол до металла: шлифовка, подбор краски, лак.",
    },
    {
        "key": "interior",
        "name": "Химчистка салона",
        "aliases": ["Химчистка салона (глубокая)", "Химчистка сидений"],
        "price": 8000,
        "duration": 70,
        "category": "Салон",
        "description": "Экстрактор, пятна, кожа, проветривание.",
    },
]


def _notes(equipment: str, extra: str = "") -> str:
    parts = [
        f"Маркер загрузки: {MARKER}.",
        f"Оборудование (не склад, не списываем): {equipment}",
    ]
    if extra:
        parts.append(extra)
    return " ".join(parts)


def _item(ids: dict[str, int], key: str, qty: float) -> TechCardItemIn:
    return TechCardItemIn(material_id=ids[key], quantity=qty)


def _cards(ids: dict[str, int]) -> dict[str, dict]:
    """key услуги → payload техкарты."""
    return {
        "wash": {
            "name": "Бесконтактная мойка кузова",
            "notes": _notes(
                "пеногенератор, аппарат высокого давления (Кёрхер), фильтр-осушитель воздуха.",
                "Цель: смыть грязь без касания кузова, без царапин.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Подготовка",
                    duration_minutes=2,
                    description=(
                        "Проверить давление воды — 100–120 бар. "
                        "В пеногенератор налить 50 мл шампуня активной пены. "
                        "Долить воду до 1 литра (вода : шампунь ≈ 20:1). "
                        "Закрыть, встряхнуть, подключить к пистолету."
                    ),
                    items=[_item(ids, "foam", 50), _item(ids, "water", 5)],
                ),
                TechCardBlockIn(
                    title="Смачивание кузова",
                    duration_minutes=1,
                    description=(
                        "Включить аппарат. С 30–40 см пройти весь кузов водой сверху вниз. "
                        "Сбить песок и крупные комки грязи."
                    ),
                    items=[_item(ids, "water", 5)],
                ),
                TechCardBlockIn(
                    title="Нанесение пены",
                    duration_minutes=4,
                    description=(
                        "Режим «пена». Слой 5–7 мм: крыша → пороги. "
                        "Не лить на горячий выхлоп и мотор. Держать 3–5 минут. "
                        "Пена не должна высохнуть — при подсыхании слегка сбрызнуть водой."
                    ),
                    items=[],
                ),
                TechCardBlockIn(
                    title="Смыв",
                    duration_minutes=4,
                    description=(
                        "Режим вода высокого давления. Смывать сверху вниз, быстро, без паузы в точке. "
                        "Дистанция 30 см, угол 30–45°. Арки, пороги, решётка — отдельно."
                    ),
                    items=[_item(ids, "water", 10)],
                ),
                TechCardBlockIn(
                    title="Сушка",
                    duration_minutes=4,
                    description=(
                        "Пройти кузов сверху вниз, убрать капли с крыши, капота, багажника. "
                        "Фильтр-осушитель на воздухе — меньше разводов. "
                        "Антидождь — по желанию клиента: 10 мл на стёкла."
                    ),
                    items=[_item(ids, "antirain", 10)],
                ),
            ],
        },
        "complex": {
            "name": "Комплексная мойка",
            "notes": _notes(
                "пеногенератор, Кёрхер, пылесос влажной/сухой уборки, щётки для дисков.",
                "Цель: снаружи и внутри чисто за один заезд.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Мойка кузова",
                    duration_minutes=12,
                    description=(
                        "Как бесконтактная мойка: пена 20:1, давление 100–120 бар, смыв сверху вниз. "
                        "Дополнительно продуть стыки дверей, капота, багажника. "
                        "Решётку радиатора — осторожно, не мять соты."
                    ),
                    items=[_item(ids, "foam", 60), _item(ids, "water", 20)],
                ),
                TechCardBlockIn(
                    title="Диски и арки",
                    duration_minutes=6,
                    description=(
                        "Кислотный шампунь на диск и шину, 1–2 минуты. "
                        "Щёткой между спицами. Смыть 80–100 бар. Все 4 колеса. Арки — струёй."
                    ),
                    items=[_item(ids, "wheel", 30), _item(ids, "water", 10)],
                ),
                TechCardBlockIn(
                    title="Салон: пылесос и влажная уборка",
                    duration_minutes=18,
                    description=(
                        "Пылесос: коврики, сиденья, подголовники, багажник, щелевая насадка. "
                        "Химию наносить на салфетку, не на панель. Протереть торпедо, консоль, руль, карты дверей. "
                        "Кожа — только если стоит кондиционер для кожи. "
                        "Двери открыть 5–10 минут, стёкла изнутри — чистой салфеткой."
                    ),
                    items=[_item(ids, "salon_wet", 50), _item(ids, "microfiber", 3)],
                ),
            ],
        },
        "polish": {
            "name": "Полировка кузова (стандартная)",
            "notes": _notes(
                "роторная машинка 1500–2000 и 1000–1200 об/мин, по желанию орбиталь, LED-лампы.",
                "Не греть ЛКП выше 40 °C. Очки. Цель: блеск и мелкие риски.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Подготовка и оклейка",
                    duration_minutes=10,
                    description=(
                        "Сначала бесконтактная мойка. Обезжирить весь кузов, подождать 2–3 минуты. "
                        "Скотчем закрыть резину стёкол, пластик, хром, фары, стыки панелей."
                    ),
                    items=[
                        _item(ids, "foam", 50),
                        _item(ids, "water", 20),
                        _item(ids, "degreaser", 50),
                        _item(ids, "tape", 5),
                    ],
                ),
                TechCardBlockIn(
                    title="Абразивная полировка",
                    duration_minutes=45,
                    description=(
                        "10–15 капель грубой пасты на грубый круг, не на кузов. "
                        "1500–2000 об/мин, круг под 15–20°, участок 50×50 см, 8–10 проходов, 1–2 минуты. "
                        "Рукой проверять нагрев. Снять пасту микрофиброй, смотреть под лампой."
                    ),
                    items=[_item(ids, "abrasive", 100), _item(ids, "pad_coarse", 1), _item(ids, "microfiber", 1)],
                ),
                TechCardBlockIn(
                    title="Финишная полировка",
                    duration_minutes=30,
                    description=(
                        "5–7 капель финиша на мягкий круг. 1000–1200 об/мин, круговые движения, "
                        "около минуты на участок 50×50 см. Снять чистой салфеткой."
                    ),
                    items=[_item(ids, "finish", 50), _item(ids, "pad_soft", 1), _item(ids, "microfiber", 1)],
                ),
                TechCardBlockIn(
                    title="Защита воском",
                    duration_minutes=15,
                    description=(
                        "Воск на мягкую салфетку, равномерно, выдержка 5–7 минут. "
                        "Располировать до блеска без нажима. Проверка при свете: нет разводов и пропусков."
                    ),
                    items=[_item(ids, "wax", 50)],
                ),
            ],
        },
        "ceramic": {
            "name": "Нанесение керамического покрытия 9H",
            "notes": _notes(
                "LED-лампы, инфракрасный термометр кузова.",
                "Кузов 15–25 °C, ниже 10 °C не наносить. Первичное отверждение 2–4 ч, полное 24–48 ч без воды.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Мойка и обезжиривание IPA",
                    duration_minutes=30,
                    description=(
                        "Бесконтактная мойка. Обезжирить весь кузов, испарение 3–5 минут. "
                        "Кузов холодный, не с солнца. Замерить температуру."
                    ),
                    items=[_item(ids, "foam", 50), _item(ids, "water", 20), _item(ids, "degreaser", 100)],
                ),
                TechCardBlockIn(
                    title="Нанесение керамики",
                    duration_minutes=75,
                    description=(
                        "3–5 капель на аппликатор. Участок 40×40 см крест-накрест, тонкий слой. "
                        "Выдержка 30–60 с (при 20 °C ≈ 45 с). Радужные разводы — сразу полировать. "
                        "Круговые лёгкие движения салфеткой. Следующий участок с нахлёстом 5–10 см."
                    ),
                    items=[
                        _item(ids, "ceramic", 30),
                        _item(ids, "applicator", 2),
                        _item(ids, "polish_cloth", 5),
                    ],
                ),
                TechCardBlockIn(
                    title="Контроль и отверждение",
                    duration_minutes=10,
                    description=(
                        "Осмотреть под лампой: нет пропусков и пятен. "
                        "Сухое помещение 2–4 часа. Воду и касания — только после полного отверждения."
                    ),
                    items=[_item(ids, "microfiber", 3)],
                ),
            ],
        },
        "chips": {
            "name": "Локальный ремонт сколов и царапин",
            "notes": _notes(
                "орбитальная шлифмашинка, кисть или краскопульт, ИК-лампа сушки.",
                "Цель: закрыть скол до металла без перекраса всей детали.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Локальная мойка и маскировка",
                    duration_minutes=10,
                    description=(
                        "Помыть только зону ремонта. Обезжирить, 1–2 минуты на испарение. "
                        "Скотч вокруг скола, чтобы краска не ушла на соседнюю ЛКП."
                    ),
                    items=[_item(ids, "degreaser", 30), _item(ids, "tape", 1), _item(ids, "microfiber", 1)],
                ),
                TechCardBlockIn(
                    title="Шлифовка P1500 → P3000",
                    duration_minutes=18,
                    description=(
                        "P1500 — до металла, ржавчину снять. P2000 — сгладить край. "
                        "P3000 — матовая гладкая поверхность. Круговые лёгкие движения."
                    ),
                    items=[_item(ids, "sandpaper", 3)],
                ),
                TechCardBlockIn(
                    title="Подбор и нанесение эмали",
                    duration_minutes=12,
                    description=(
                        "Смешать цвет с родным, проба на клочке. Тонкий слой кистью или пультом. "
                        "Сушка 5–10 минут (лампа). При необходимости второй слой, ещё 10–15 минут."
                    ),
                    items=[_item(ids, "paint", 5)],
                ),
                TechCardBlockIn(
                    title="Лак",
                    duration_minutes=5,
                    description="Тонкий слой лака поверх краски. Сушка ИК 15–20 минут.",
                    items=[_item(ids, "lacquer", 10)],
                ),
                TechCardBlockIn(
                    title="Переход и полировка",
                    duration_minutes=15,
                    description=(
                        "P3000 по стыку лака и родного покрытия. "
                        "Паста на салфетку, до блеска, остатки снять."
                    ),
                    items=[_item(ids, "chip_paste", 20), _item(ids, "microfiber", 1)],
                ),
            ],
        },
        "interior": {
            "name": "Химчистка салона (глубокая)",
            "notes": _notes(
                "экстрактор, пароочиститель, пылесос влажной/сухой уборки.",
                "Цель: пятна, запах, ткань и кожа.",
            ),
            "blocks": [
                TechCardBlockIn(
                    title="Разгрузка и пылесос",
                    duration_minutes=10,
                    description=(
                        "Вынуть вещи и крупный мусор. Коврики отдельно. "
                        "Сиденья, складки, под сиденьями, багажник, щелевая насадка."
                    ),
                    items=[],
                ),
                TechCardBlockIn(
                    title="Пятна",
                    duration_minutes=12,
                    description=(
                        "Пятновыводитель на ткань и ковры, 3–5 минут. "
                        "Мягкая щётка кругами, затем влажная салфетка."
                    ),
                    items=[_item(ids, "stain", 30), _item(ids, "brush", 1), _item(ids, "microfiber", 2)],
                ),
                TechCardBlockIn(
                    title="Экстрактор",
                    duration_minutes=25,
                    description=(
                        "Шампунь с водой 1:5 в бак. Участки 30×30 см: нанести, 1–2 минуты, вытянуть. "
                        "Пар для сушки. Двери открыты."
                    ),
                    items=[_item(ids, "extract_shampoo", 100), _item(ids, "water", 10)],
                ),
                TechCardBlockIn(
                    title="Кожа",
                    duration_minutes=10,
                    description="Кондиционер на салфетку: сиденья и руль. Чистой салфеткой располировать.",
                    items=[_item(ids, "leather", 50), _item(ids, "microfiber", 2)],
                ),
                TechCardBlockIn(
                    title="Стёкла и проветривание",
                    duration_minutes=5,
                    description="Стёкла изнутри. Проветрить 5–10 минут, запаха химии быть не должно.",
                    items=[_item(ids, "microfiber", 1)],
                ),
            ],
        },
    }


async def _ensure_material(db: AsyncSession, tenant_id: UUID, spec: dict) -> Material:
    result = await db.execute(
        select(Material).where(
            Material.tenant_id == tenant_id,
            Material.name == spec["name"],
        )
    )
    mat = result.scalar_one_or_none()
    if mat:
        mat.unit = spec["unit"]
        mat.purchase_price = Decimal(str(spec["price"]))
        mat.category = spec["cat"]
        mat.min_quantity = Decimal(str(spec["min"]))
        mat.is_active = True
        if float(mat.quantity or 0) < float(spec["min"]):
            mat.quantity = Decimal(str(spec["qty"]))
        return mat
    mat = Material(
        tenant_id=tenant_id,
        name=spec["name"],
        category=spec["cat"],
        unit=spec["unit"],
        quantity=Decimal(str(spec["qty"])),
        min_quantity=Decimal(str(spec["min"])),
        purchase_price=Decimal(str(spec["price"])),
        notes=f"{MARKER}: демо-номенклатура для техкарт",
        is_active=True,
    )
    db.add(mat)
    await db.flush()
    return mat


async def _ensure_service(db: AsyncSession, tenant_id: UUID, spec: dict) -> Service:
    names = [spec["name"], *spec.get("aliases", [])]
    result = await db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.name.in_(names),
        )
    )
    found = list(result.scalars().all())
    svc = None
    for n in names:
        svc = next((s for s in found if s.name == n), None)
        if svc:
            break
    if not svc and found:
        svc = found[0]
    if svc:
        return svc
    svc = Service(
        tenant_id=tenant_id,
        name=spec["name"],
        description=spec.get("description") or "",
        category=spec.get("category") or "",
        price=Decimal(str(spec["price"])),
        duration=int(spec["duration"]),
        material_cost=0,
        cost_price=0,
        is_active=True,
    )
    db.add(svc)
    await db.flush()
    return svc


def _bom_cost(blocks: list[TechCardBlockIn], price_by_id: dict[int, float]) -> float:
    total = 0.0
    for b in blocks:
        for it in b.items:
            total += float(it.quantity) * float(price_by_id.get(it.material_id, 0))
    return round(total, 2)


async def apply_demo_pack(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    force: bool = False,
) -> dict:
    """Создаёт/обновляет демо-материалы, услуги и 6 техкарт. Возвращает счётчики.

    force=True — перезаписать карту услуги даже без маркера (демо-тенант / CLI).
    """
    mat_ids: dict[str, int] = {}
    for key, spec in MATERIALS.items():
        mat = await _ensure_material(db, tenant_id, spec)
        mat_ids[key] = mat.id
    price_by_id = {mat_ids[k]: float(v["price"]) for k, v in MATERIALS.items()}

    created = 0
    updated = 0
    skipped = 0
    cards_payload = _cards(mat_ids)

    for spec in SERVICES:
        svc = await _ensure_service(db, tenant_id, spec)
        payload = cards_payload[spec["key"]]
        cost = _bom_cost(payload["blocks"], price_by_id)
        if float(svc.material_cost or 0) == 0:
            svc.material_cost = Decimal(str(cost))
            svc.cost_price = Decimal(str(cost))

        existing = await db.execute(
            select(TechCard)
            .options(selectinload(TechCard.blocks), selectinload(TechCard.items))
            .where(
                TechCard.tenant_id == tenant_id,
                TechCard.service_id == svc.id,
            )
        )
        card = existing.scalar_one_or_none()
        data_create = TechCardCreate(
            service_id=svc.id,
            name=payload["name"],
            notes=payload["notes"],
            is_active=True,
            blocks=payload["blocks"],
        )
        if card is None:
            await create_tech_card(db, tenant_id, data_create)
            created += 1
            continue
        notes = card.notes or ""
        has_content = bool(card.blocks or card.items)
        if not force and MARKER not in notes and has_content:
            skipped += 1
            continue
        await update_tech_card(
            db,
            tenant_id,
            card.id,
            TechCardUpdate(
                name=payload["name"],
                notes=payload["notes"],
                is_active=True,
                blocks=payload["blocks"],
            ),
        )
        updated += 1

    return {
        "materials": len(mat_ids),
        "created": created,
        "updated": updated,
        "skipped": skipped,
    }


async def seed_demo_pack_for_default_tenant() -> dict:
    from app.core.database import async_session_maker
    from app.models import Tenant

    tenant_id = UUID("00000000-0000-0000-0000-000000000001")
    async with async_session_maker() as session:
        tenant = await session.get(Tenant, tenant_id)
        if not tenant:
            raise RuntimeError("Нет демо-тенанта. Сначала init_db / seed.")
        stats = await apply_demo_pack(session, tenant_id, force=True)
        await session.commit()
        return stats


if __name__ == "__main__":
    import asyncio

    stats = asyncio.run(seed_demo_pack_for_default_tenant())
    print("demo-pack-6:", stats)
