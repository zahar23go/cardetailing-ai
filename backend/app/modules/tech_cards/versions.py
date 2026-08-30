"""Версии техкарт и PDF-инструкция."""
from __future__ import annotations

from io import BytesIO
from pathlib import Path
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import TechCard
from app.modules.tech_cards.models import TechCardVersion
from app.modules.tech_cards.service import get_tech_card, tech_card_to_out

UNIT_LABELS = {
    "pcs": "шт",
    "ml": "мл",
    "l": "л",
    "g": "г",
    "kg": "кг",
    "m": "м",
    "pack": "упак.",
}


def _snapshot_body(card: TechCard) -> dict:
    data = tech_card_to_out(card).model_dump(mode="json")
    for key in ("created_at", "updated_at", "current_version"):
        data.pop(key, None)
    return data


def _summary(snapshot: dict) -> dict:
    blocks = snapshot.get("blocks") or []
    return {
        "blocks_count": int(snapshot.get("blocks_count") or len(blocks)),
        "items_count": int(snapshot.get("items_count") or 0),
        "estimated_cost": float(snapshot.get("estimated_cost") or 0),
        "name": snapshot.get("name") or snapshot.get("service_name"),
    }


async def record_version(
    db: AsyncSession,
    card: TechCard,
    *,
    actor_id: int | None = None,
) -> TechCardVersion | None:
    body = _snapshot_body(card)
    last = (
        await db.execute(
            select(TechCardVersion)
            .where(TechCardVersion.tech_card_id == card.id)
            .order_by(TechCardVersion.version_no.desc())
            .limit(1)
        )
    ).scalar_one_or_none()
    prev = last.snapshot if last else None
    if isinstance(prev, str):
        import json
        prev = json.loads(prev)
    if last and prev == body:
        return last
    next_no = int(last.version_no) + 1 if last else 1
    row = TechCardVersion(
        tenant_id=card.tenant_id,
        tech_card_id=card.id,
        version_no=next_no,
        snapshot=body,
        created_by_id=actor_id,
    )
    db.add(row)
    card.current_version = next_no
    await db.flush()
    return row


async def list_versions(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
) -> list[dict]:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        return []
    rows = (
        await db.execute(
            select(TechCardVersion)
            .where(
                TechCardVersion.tech_card_id == card_id,
                TechCardVersion.tenant_id == tenant_id,
            )
            .order_by(TechCardVersion.version_no.desc())
        )
    ).scalars().all()
    out = []
    for row in rows:
        snap = row.snapshot or {}
        meta = _summary(snap)
        out.append({
            "id": row.id,
            "version_no": row.version_no,
            "created_at": row.created_at,
            **meta,
        })
    return out


async def get_version(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    version_no: int,
) -> dict | None:
    row = (
        await db.execute(
            select(TechCardVersion).where(
                TechCardVersion.tech_card_id == card_id,
                TechCardVersion.tenant_id == tenant_id,
                TechCardVersion.version_no == version_no,
            )
        )
    ).scalar_one_or_none()
    if not row:
        return None
    snap = row.snapshot or {}
    return {
        "id": row.id,
        "version_no": row.version_no,
        "created_at": row.created_at,
        "snapshot": snap,
        **_summary(snap),
    }


def _font_path() -> str | None:
    candidates = [
        Path(r"C:\Windows\Fonts\arial.ttf"),
        Path(r"C:\Windows\Fonts\calibri.ttf"),
        Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
        Path("/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf"),
        Path("/usr/share/fonts/truetype/freefont/FreeSans.ttf"),
    ]
    for path in candidates:
        if path.exists():
            return str(path)
    return None


def _safe(text: str) -> str:
    return (text or "").replace("\x00", " ").strip()


def build_pdf_bytes(snapshot: dict, *, version_no: int | None = None) -> bytes:
    from reportlab.lib.pagesizes import A4
    from reportlab.lib.units import mm
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.pdfgen import canvas

    font_name = "Helvetica"
    font_path = _font_path()
    if font_path:
        pdfmetrics.registerFont(TTFont("CardFont", font_path))
        font_name = "CardFont"

    buf = BytesIO()
    c = canvas.Canvas(buf, pagesize=A4)
    width, height = A4
    y = height - 18 * mm
    left = 18 * mm

    def line(text: str, size: int = 11, gap: int = 16, bold: bool = False):
        nonlocal y
        if y < 22 * mm:
            c.showPage()
            y = height - 18 * mm
        c.setFont(font_name, size)
        c.drawString(left, y, _safe(text)[:110])
        y -= gap

    title = snapshot.get("name") or snapshot.get("service_name") or "Техкарта"
    ver = version_no or snapshot.get("current_version") or ""
    line(f"CAR DETAILING AI — техкарта{f'  v{ver}' if ver else ''}", 9, 14)
    line(str(title), 16, 20)
    svc = snapshot.get("service_name")
    if svc and svc != title:
        line(f"Услуга: {svc}", 11, 14)
    mins = int(snapshot.get("total_duration_minutes") or 0)
    cost = float(snapshot.get("estimated_cost") or 0)
    line(f"Длительность: {mins} мин   ·   Норма материалов: {cost:.2f} ₽", 11, 18)
    notes = snapshot.get("notes")
    if notes:
        line(f"Заметки: {notes}", 10, 16)

    blocks = snapshot.get("blocks") or []
    for idx, block in enumerate(blocks, start=1):
        y -= 4
        line(f"{idx}. {block.get('title') or 'Шаг'}", 13, 18)
        dur = int(block.get("duration_minutes") or 0)
        if dur:
            line(f"   Время: {dur} мин", 10, 14)
        desc = block.get("description")
        if desc:
            line(f"   {desc}", 10, 14)
        for item in block.get("items") or []:
            unit = UNIT_LABELS.get(item.get("material_unit") or "", item.get("material_unit") or "")
            qty = item.get("quantity") or 0
            name = item.get("material_name") or f"#{item.get('material_id')}"
            line(f"   • {name}: {qty:g} {unit}", 10, 13)

    c.save()
    return buf.getvalue()


async def render_pdf(
    db: AsyncSession,
    tenant_id: UUID,
    card_id: int,
    *,
    version_no: int | None = None,
) -> tuple[bytes, str]:
    card = await get_tech_card(db, tenant_id, card_id)
    if not card:
        raise HTTPException(status_code=404, detail="Tech card not found")
    if version_no:
        ver = await get_version(db, tenant_id, card_id, version_no)
        if not ver:
            raise HTTPException(status_code=404, detail="Версия не найдена")
        snapshot = ver["snapshot"]
        no = ver["version_no"]
    else:
        snapshot = tech_card_to_out(card).model_dump(mode="json")
        no = int(card.current_version or 0) or None
    pdf = build_pdf_bytes(snapshot, version_no=no)
    slug = no or "current"
    return pdf, f"tech-card-{card_id}-v{slug}.pdf"
