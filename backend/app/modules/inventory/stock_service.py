"""Приёмка и ревизия склада с подписью."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import Material
from app.modules.inventory.models import StockDocument, StockDocumentLine
from app.modules.materials.service import apply_stock_delta, get_material


def assert_signature(user: dict, signed_name: str) -> str:
    expected = (user.get("full_name") or "").strip()
    got = (signed_name or "").strip()
    if not expected:
        raise HTTPException(status_code=400, detail="В профиле нет имени — нельзя подписать документ")
    if got.casefold() != expected.casefold():
        raise HTTPException(
            status_code=400,
            detail=f"Подпись: введите своё имя как в профиле («{expected}»)",
        )
    return expected


def _round3(value: float) -> float:
    return round(float(value or 0), 3)


async def _unique_lines(lines: list[dict]) -> list[dict]:
    seen: set[int] = set()
    out = []
    for row in lines:
        mid = int(row["material_id"])
        if mid in seen:
            raise HTTPException(status_code=400, detail="Одна позиция не должна повторяться в документе")
        seen.add(mid)
        out.append(row)
    return out


def serialize_document(doc: StockDocument) -> dict:
    return {
        "id": doc.id,
        "doc_type": doc.doc_type,
        "document_no": doc.document_no,
        "note": doc.note,
        "signed_name": doc.signed_name,
        "signed_at": doc.signed_at,
        "created_at": doc.created_at,
        "lines": [
            {
                "material_id": ln.material_id,
                "name": ln.name,
                "unit": ln.unit,
                "system_qty": _round3(ln.system_qty),
                "qty": _round3(ln.qty),
                "delta": _round3(ln.delta),
            }
            for ln in (doc.lines or [])
        ],
    }


async def list_documents(
    db: AsyncSession,
    tenant_id: UUID,
    *,
    skip: int = 0,
    limit: int = 30,
    doc_type: str | None = None,
) -> tuple[list[StockDocument], int]:
    filters = [StockDocument.tenant_id == tenant_id]
    if doc_type:
        filters.append(StockDocument.doc_type == doc_type)
    from sqlalchemy import func

    total = int(
        (await db.execute(select(func.count(StockDocument.id)).where(*filters))).scalar() or 0
    )
    result = await db.execute(
        select(StockDocument)
        .options(selectinload(StockDocument.lines))
        .where(*filters)
        .order_by(StockDocument.created_at.desc())
        .offset(skip)
        .limit(limit)
    )
    return list(result.scalars().unique().all()), total


async def post_intake(
    db: AsyncSession,
    tenant_id: UUID,
    user: dict,
    *,
    lines: list[dict],
    signed_name: str,
    document_no: str | None = None,
    note: str | None = None,
) -> StockDocument:
    signed = assert_signature(user, signed_name)
    rows = await _unique_lines(lines)
    if not rows:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одну позицию")

    now = datetime.now(timezone.utc)
    doc = StockDocument(
        tenant_id=tenant_id,
        doc_type="intake",
        document_no=(document_no or "").strip() or None,
        note=(note or "").strip() or None,
        signed_name=signed,
        signed_by_id=user["id"],
        signed_at=now,
        created_by_id=user["id"],
    )
    db.add(doc)
    await db.flush()

    reason = f"Приёмка{(' ' + doc.document_no) if doc.document_no else ''}"
    for row in rows:
        qty = _round3(row.get("qty") or 0)
        if qty <= 0:
            raise HTTPException(status_code=400, detail="Количество приёмки должно быть больше 0")
        mat = await get_material(db, tenant_id, int(row["material_id"]))
        if not mat:
            raise HTTPException(status_code=404, detail=f"Материал #{row['material_id']} не найден")
        before = float(mat.quantity or 0)
        _m, applied = await apply_stock_delta(
            db,
            tenant_id,
            mat.id,
            qty,
            reason=reason,
            created_by_id=user["id"],
            document_id=doc.id,
            movement_type="in",
        )
        db.add(
            StockDocumentLine(
                document_id=doc.id,
                material_id=mat.id,
                name=mat.name,
                unit=mat.unit or "pcs",
                system_qty=before,
                qty=qty,
                delta=applied,
            )
        )

    await db.commit()
    result = await db.execute(
        select(StockDocument)
        .options(selectinload(StockDocument.lines))
        .where(StockDocument.id == doc.id)
    )
    return result.scalar_one()


async def post_revision(
    db: AsyncSession,
    tenant_id: UUID,
    user: dict,
    *,
    lines: list[dict],
    signed_name: str,
    note: str | None = None,
) -> StockDocument:
    signed = assert_signature(user, signed_name)
    rows = await _unique_lines(lines)
    if not rows:
        raise HTTPException(status_code=400, detail="Добавьте хотя бы одну позицию")

    now = datetime.now(timezone.utc)
    doc = StockDocument(
        tenant_id=tenant_id,
        doc_type="revision",
        note=(note or "").strip() or None,
        signed_name=signed,
        signed_by_id=user["id"],
        signed_at=now,
        created_by_id=user["id"],
    )
    db.add(doc)
    await db.flush()

    for row in rows:
        counted = _round3(row.get("qty") if row.get("qty") is not None else row.get("counted_qty") or 0)
        if counted < 0:
            raise HTTPException(status_code=400, detail="Факт не может быть отрицательным")
        mat = await get_material(db, tenant_id, int(row["material_id"]))
        if not mat:
            raise HTTPException(status_code=404, detail=f"Материал #{row['material_id']} не найден")
        before = float(mat.quantity or 0)
        delta = counted - before
        applied = 0.0
        if abs(delta) > 1e-9:
            _m, applied = await apply_stock_delta(
                db,
                tenant_id,
                mat.id,
                delta,
                reason=f"Ревизия: факт {counted:g}",
                created_by_id=user["id"],
                document_id=doc.id,
                movement_type="revision",
            )
        db.add(
            StockDocumentLine(
                document_id=doc.id,
                material_id=mat.id,
                name=mat.name,
                unit=mat.unit or "pcs",
                system_qty=before,
                qty=counted,
                delta=applied if abs(delta) > 1e-9 else 0,
            )
        )

    await db.commit()
    result = await db.execute(
        select(StockDocument)
        .options(selectinload(StockDocument.lines))
        .where(StockDocument.id == doc.id)
    )
    return result.scalar_one()
