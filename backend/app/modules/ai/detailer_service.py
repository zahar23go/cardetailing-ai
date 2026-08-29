"""AI-детейлер: оценка по меткам/фото, допродажи из каталога, слот по боксам.

Vision-модель не требуется: клиент отмечает состояние, фото — доказательство
для мастера. Подбор услуг — по каталогу салона, слоты — по живой занятости боксов.
"""
from __future__ import annotations

from datetime import datetime, timedelta, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Appointment, Box, BoxService, Service
from app.modules.appointments.live_service import FLOOR_STATUSES, PREP_MINUTES

SLOT_START_HOUR = 9
SLOT_END_HOUR = 19
SLOT_STEP_MIN = 30
DEFAULT_DURATION = 60

TAG_CATALOG: list[dict] = [
    {
        "id": "chips",
        "label": "Сколы / риски",
        "area": "paint",
        "finding": "На ЛКП сколы или риски — нужна коррекция лака, затем защита.",
        "needles": ["полир", "керамик", "коррекц", "абразив"],
    },
    {
        "id": "dull",
        "label": "Тусклый лак",
        "area": "paint",
        "finding": "Лак выглядит тусклым — полировка и покрытие вернут глубину цвета.",
        "needles": ["полир", "керамик", "покрыт"],
    },
    {
        "id": "lights",
        "label": "Мутные фары",
        "area": "lights",
        "finding": "Рассеиватели фар мутные — полировка или броня фар.",
        "needles": ["фар"],
    },
    {
        "id": "interior",
        "label": "Салон / кожа",
        "area": "interior",
        "finding": "Салон требует химчистки или ухода за кожей.",
        "needles": ["химчист", "салон", "кожа"],
    },
    {
        "id": "bitumen",
        "label": "Битум / металлик",
        "area": "paint",
        "finding": "Битум и металлические вкрапления — мойка с деконтаминацией.",
        "needles": ["мойк", "двухфаз", "деконтам", "антибит"],
    },
    {
        "id": "wash",
        "label": "Грязный кузов",
        "area": "paint",
        "finding": "Кузов загрязнён — начинаем с профессиональной мойки.",
        "needles": ["мойк", "wash"],
    },
]

_TAG_BY_ID = {t["id"]: t for t in TAG_CATALOG}

NOTE_HINTS: list[tuple[str, list[str]]] = [
    ("chips", ["скол", "риск", "царапин"]),
    ("dull", ["тускл", "выгорел", "матовы"]),
    ("lights", ["фар", "оптик"]),
    ("interior", ["салон", "химчист", "кожа", "сиден"]),
    ("bitumen", ["битум", "металл", "смол"]),
    ("wash", ["грязн", "мойк", "пыль"]),
]


def _norm(value: str | None) -> str:
    return (value or "").lower().replace("ё", "е")


def infer_tags(tags: list[str] | None, notes: str | None) -> list[str]:
    known = [t for t in (tags or []) if t in _TAG_BY_ID]
    hay = _norm(notes)
    if hay:
        for tag_id, needles in NOTE_HINTS:
            if tag_id not in known and any(n in hay for n in needles):
                known.append(tag_id)
    if not known:
        known = ["wash"]
    return known


def _service_blob(service: Service) -> str:
    return _norm(f"{service.name} {service.category or ''} {service.description or ''}")


def _score_service(service: Service, needles: list[str]) -> int:
    blob = _service_blob(service)
    return sum(1 for n in needles if n in blob)


def match_services_for_tags(services: list[Service], tag_ids: list[str]) -> tuple[Service | None, list[dict]]:
    """Первичная услуга + допродажи из каталога по иглам меток."""
    if not services:
        return None, []
    combined: list[str] = []
    for tag_id in tag_ids:
        spec = _TAG_BY_ID.get(tag_id)
        if spec:
            for n in spec["needles"]:
                if n not in combined:
                    combined.append(n)

    ranked: list[tuple[int, float, Service]] = []
    for svc in services:
        score = _score_service(svc, combined)
        if score <= 0:
            continue
        ranked.append((score, float(svc.price or 0), svc))
    ranked.sort(key=lambda x: (x[0], x[1]), reverse=True)

    if not ranked:
        # нет прямого попадания — берём первую активную как «осмотр + мойка»
        fallback = services[0]
        return fallback, []

    primary = ranked[0][2]
    upsells: list[dict] = []
    for _score, _price, svc in ranked[1:]:
        if svc.id == primary.id:
            continue
        upsells.append(_service_offer(svc, reason="Допродажа по состоянию авто"))
        if len(upsells) >= 3:
            break
    return primary, upsells


def _service_offer(service: Service, reason: str) -> dict:
    return {
        "service_id": service.id,
        "name": service.name,
        "price": float(service.price or 0),
        "duration": int(service.duration or DEFAULT_DURATION),
        "category": service.category,
        "reason": reason,
    }


def build_findings(tag_ids: list[str], photo_count: int) -> list[dict]:
    findings = []
    for tag_id in tag_ids:
        spec = _TAG_BY_ID.get(tag_id)
        if not spec:
            continue
        findings.append({
            "tag": tag_id,
            "area": spec["area"],
            "title": spec["label"],
            "detail": spec["finding"],
        })
    if photo_count:
        findings.append({
            "tag": "photos",
            "area": "photo",
            "title": "Фото осмотра",
            "detail": (
                f"Приложено {photo_count} фото. Оценка по меткам клиента; "
                "мастер сверит ЛКП и салон на месте."
            ),
        })
    return findings


def build_master_brief(
    *,
    tag_ids: list[str],
    findings: list[dict],
    primary: Service | None,
    upsells: list[dict],
    slot: dict | None,
    notes: str | None,
    photo_count: int,
) -> str:
    labels = [_TAG_BY_ID[t]["label"] for t in tag_ids if t in _TAG_BY_ID]
    lines = ["Детейлер — сводка до заезда"]
    if labels:
        lines.append(f"Состояние: {', '.join(labels)}.")
    if photo_count:
        lines.append(f"Фото: {photo_count} шт.")
    for item in findings:
        if item.get("tag") == "photos":
            continue
        lines.append(f"• {item['title']}: {item['detail']}")
    if primary:
        lines.append(
            f"Рекомендация: {primary.name} ({float(primary.price or 0):.0f} ₽, {primary.duration} мин)."
        )
    if upsells:
        names = ", ".join(u["name"] for u in upsells)
        lines.append(f"Допродажи: {names}.")
    if slot:
        start = slot.get("start_time")
        when = start
        if isinstance(start, datetime):
            when = start.strftime("%d.%m %H:%M")
        elif isinstance(start, str) and len(start) >= 16:
            when = f"{start[8:10]}.{start[5:7]} {start[11:16]}"
        box = slot.get("box_name") or (f"Бокс {slot['box_id']}" if slot.get("box_id") else "бокс по услуге")
        lines.append(f"Слот: {box}, {when}.")
    if notes and notes.strip():
        lines.append(f"Комментарий клиента: {notes.strip()}")
    return "\n".join(lines)


def _aware(dt: datetime | None) -> datetime | None:
    if dt is None:
        return None
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)


def _overlaps(start: datetime, end: datetime, other_start: datetime, other_end: datetime) -> bool:
    return start < other_end and end > other_start


def client_tz(offset_minutes: int) -> timezone:
    clamped = max(-14 * 60, min(14 * 60, int(offset_minutes or 0)))
    return timezone(timedelta(minutes=clamped))


async def suggest_slots(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    duration_min: int,
    service_id: int | None = None,
    date_from: datetime | None = None,
    days: int = 3,
    tz_offset_minutes: int = 0,
    limit: int = 8,
) -> list[dict]:
    """Свободные слоты с учётом занятости боксов (pending/confirmed/in_progress)."""
    duration = max(SLOT_STEP_MIN, int(duration_min or DEFAULT_DURATION))
    tz = client_tz(tz_offset_minutes)
    now = datetime.now(timezone.utc)
    local_now = now.astimezone(tz)
    start_day = date_from.astimezone(tz).date() if date_from else local_now.date()

    boxes_result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id, Box.is_active == True).order_by(Box.sort_order, Box.id)
    )
    boxes = list(boxes_result.scalars().all())
    if not boxes:
        return []

    preferred_box_ids: set[int] = set()
    if service_id:
        bs_result = await db.execute(
            select(BoxService.box_id).where(
                BoxService.tenant_id == tenant_id,
                BoxService.service_id == service_id,
            )
        )
        preferred_box_ids = {row[0] for row in bs_result.all()}

    window_start = datetime.combine(start_day, datetime.min.time(), tzinfo=tz).astimezone(timezone.utc)
    window_end = window_start + timedelta(days=max(1, days), hours=SLOT_END_HOUR)
    appts_result = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status.in_(FLOOR_STATUSES),
            Appointment.start_time < window_end,
            Appointment.end_time > window_start - timedelta(minutes=PREP_MINUTES),
        )
    )
    appointments = list(appts_result.scalars().all())

    candidates: list[dict] = []
    for day_offset in range(max(1, days)):
        day = start_day + timedelta(days=day_offset)
        minute = SLOT_START_HOUR * 60
        end_minute = SLOT_END_HOUR * 60 + 30
        while minute <= end_minute:
            hour, mins = divmod(minute, 60)
            if hour > SLOT_END_HOUR or (hour == SLOT_END_HOUR and mins > 30):
                break
            local_start = datetime(day.year, day.month, day.day, hour, mins, tzinfo=tz)
            slot_start = local_start.astimezone(timezone.utc)
            slot_end = slot_start + timedelta(minutes=duration)
            minute += SLOT_STEP_MIN
            if slot_end <= now + timedelta(minutes=PREP_MINUTES):
                continue

            free: list[Box] = []
            for box in boxes:
                busy = False
                for appt in appointments:
                    if appt.box_id is not None and appt.box_id != box.id:
                        continue
                    if appt.box_id is None:
                        continue
                    a_start, a_end = _aware(appt.start_time), _aware(appt.end_time)
                    if not a_start or not a_end:
                        continue
                    if _overlaps(slot_start, slot_end, a_start, a_end):
                        busy = True
                        break
                if not busy:
                    free.append(box)
            if not free:
                continue

            preferred = [b for b in free if b.id in preferred_box_ids] if preferred_box_ids else free
            pick = preferred[0] if preferred else free[0]
            candidates.append({
                "start_time": slot_start.isoformat(),
                "end_time": slot_end.isoformat(),
                "label": local_start.strftime("%d.%m %H:%M"),
                "time": local_start.strftime("%H:%M"),
                "date": day.isoformat(),
                "box_id": pick.id,
                "box_name": pick.name,
                "free_boxes": len(free),
                "duration": duration,
            })

    candidates.sort(key=lambda s: (-int(s["free_boxes"]), s["start_time"]))
    # keep chronological among the roomiest, then trim
    top = candidates[: max(limit * 3, limit)]
    top.sort(key=lambda s: s["start_time"])
    return top[:limit]


async def day_slot_grid(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    date_str: str,
    duration_min: int,
    service_id: int | None,
    tz_offset_minutes: int = 0,
) -> list[dict]:
    """Все получасовые слоты выбранного дня с числом свободных боксов (0 = занято)."""
    tz = client_tz(tz_offset_minutes)
    day = datetime.strptime(date_str, "%Y-%m-%d").date()
    start_local = datetime(day.year, day.month, day.day, 0, 0, tzinfo=tz)
    boxes_result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id, Box.is_active == True)
    )
    has_boxes = boxes_result.scalars().first() is not None
    slots = []
    if has_boxes:
        slots = await suggest_slots(
            db,
            tenant_id,
            duration_min=duration_min,
            service_id=service_id,
            date_from=start_local,
            days=1,
            tz_offset_minutes=tz_offset_minutes,
            limit=48,
        )
    by_time = {s["time"]: s for s in slots}
    grid: list[dict] = []
    minute = SLOT_START_HOUR * 60
    while minute <= SLOT_END_HOUR * 60 + 30:
        hour, mins = divmod(minute, 60)
        if hour > SLOT_END_HOUR:
            break
        label = f"{hour:02d}:{mins:02d}"
        found = by_time.get(label)
        if found:
            grid.append({**found, "available": True})
        elif not has_boxes:
            local_start = datetime(day.year, day.month, day.day, hour, mins, tzinfo=tz)
            start_utc = local_start.astimezone(timezone.utc)
            grid.append({
                "time": label,
                "date": date_str,
                "available": True,
                "free_boxes": 0,
                "box_id": None,
                "box_name": None,
                "start_time": start_utc.isoformat(),
                "end_time": (start_utc + timedelta(minutes=duration_min)).isoformat(),
                "duration": duration_min,
            })
        else:
            grid.append({
                "time": label,
                "date": date_str,
                "available": False,
                "free_boxes": 0,
                "box_id": None,
                "box_name": None,
                "start_time": None,
                "end_time": None,
                "duration": duration_min,
            })
        minute += SLOT_STEP_MIN
    return grid


async def load_catalog(db: AsyncSession, tenant_id: UUID) -> list[Service]:
    result = await db.execute(
        select(Service).where(
            Service.tenant_id == tenant_id,
            Service.is_active == True,
        ).order_by(Service.name)
    )
    return list(result.scalars().all())


async def inspect_car(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    tags: list[str] | None,
    notes: str | None,
    photo_count: int = 0,
    service_id: int | None = None,
    tz_offset_minutes: int = 0,
) -> dict:
    tag_ids = infer_tags(tags, notes)
    services = await load_catalog(db, tenant_id)
    if service_id:
        pinned = next((s for s in services if s.id == service_id), None)
        primary, upsells = match_services_for_tags(services, tag_ids)
        if pinned:
            upsells = [u for u in upsells if u["service_id"] != pinned.id]
            if primary and primary.id != pinned.id:
                upsells = [_service_offer(primary, "Связанная услуга по состоянию")] + upsells
                upsells = upsells[:3]
            primary = pinned
    else:
        primary, upsells = match_services_for_tags(services, tag_ids)

    findings = build_findings(tag_ids, photo_count)
    duration = int(primary.duration) if primary and primary.duration else DEFAULT_DURATION
    slots = await suggest_slots(
        db,
        tenant_id,
        duration_min=duration,
        service_id=primary.id if primary else service_id,
        tz_offset_minutes=tz_offset_minutes,
    )
    slot0 = slots[0] if slots else None
    brief = build_master_brief(
        tag_ids=tag_ids,
        findings=findings,
        primary=primary,
        upsells=upsells,
        slot=slot0,
        notes=notes,
        photo_count=photo_count,
    )
    return {
        "tags": tag_ids,
        "findings": findings,
        "primary": _service_offer(primary, "Рекомендация детейлера") if primary else None,
        "upsells": upsells,
        "slots": slots,
        "master_brief": brief,
        "photo_count": photo_count,
    }
