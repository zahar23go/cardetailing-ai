"""Закрытие заезда: чек-лист техкарты, списание склада, снимок чека."""
from __future__ import annotations

from datetime import datetime, timezone
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.models import (
    Appointment,
    AppointmentCloseMaterial,
    AppointmentCloseStep,
    AppointmentInvoice,
    Material,
    Service,
    TechCard,
    TechCardBlock,
    TechCardItem,
)
from app.modules.materials.service import apply_stock_delta


def snapshot_material_cost(appointment: Appointment) -> float:
    """Себестоимость для P&L: чек закрытия, иначе каталог услуги."""
    inv = getattr(appointment, "invoice", None)
    if inv is not None:
        return float(inv.material_cost or 0)
    if appointment.service:
        return float(appointment.service.material_cost or 0)
    return 0.0


def snapshot_revenue(appointment: Appointment) -> float:
    """Выручка: цена из чека закрытия, иначе текущая цена записи."""
    inv = getattr(appointment, "invoice", None)
    if inv is not None:
        return float(inv.price or 0)
    return float(appointment.total_price or 0)


def compute_box_margins(completed: list[Appointment], total_expenses: float) -> list[dict]:
    """Маржа по боксу. Постоянные расходы делим пропорционально выручке."""
    groups: dict[int | None, dict] = {}
    total_revenue = 0.0
    for a in completed:
        inv = getattr(a, "invoice", None)
        bid = inv.box_id if inv is not None else a.box_id
        if inv is not None and getattr(inv, "box", None):
            name = inv.box.name
        elif getattr(a, "box", None):
            name = a.box.name
        else:
            name = "Без бокса"
        if bid not in groups:
            groups[bid] = {
                "box_id": bid,
                "box_name": name,
                "total_revenue": 0.0,
                "total_material_cost": 0.0,
                "appointment_count": 0,
            }
        rev = snapshot_revenue(a)
        groups[bid]["total_revenue"] += rev
        groups[bid]["total_material_cost"] += snapshot_material_cost(a)
        groups[bid]["appointment_count"] += 1
        total_revenue += rev

    rows = []
    for g in groups.values():
        gp = g["total_revenue"] - g["total_material_cost"]
        mp = round(gp / g["total_revenue"] * 100, 1) if g["total_revenue"] else 0.0
        share = (g["total_revenue"] / total_revenue) if total_revenue else 0.0
        allocated = round(float(total_expenses or 0) * share, 2)
        rows.append({
            "box_id": g["box_id"],
            "box_name": g["box_name"],
            "total_revenue": round(g["total_revenue"], 2),
            "total_material_cost": round(g["total_material_cost"], 2),
            "gross_profit": round(gp, 2),
            "margin_percent": mp,
            "appointment_count": g["appointment_count"],
            "allocated_expenses": allocated,
            "net_profit": round(gp - allocated, 2),
        })
    rows.sort(key=lambda x: x["total_revenue"], reverse=True)
    return rows


def _round2(value: float) -> float:
    return round(float(value or 0), 2)


def _round3(value: float) -> float:
    return round(float(value or 0), 3)


def serialize_invoice(inv: AppointmentInvoice) -> dict:
    box_name = None
    if inv.box_id and getattr(inv, "box", None):
        box_name = inv.box.name
    return {
        "id": inv.id,
        "appointment_id": inv.appointment_id,
        "box_id": inv.box_id,
        "box_name": box_name,
        "service_id": inv.service_id,
        "service_name": inv.service_name,
        "price": _round2(inv.price),
        "discount": _round2(inv.discount),
        "material_cost": _round2(inv.material_cost),
        "catalog_material_cost": _round2(inv.catalog_material_cost),
        "shortage_qty_cost": _round2(inv.shortage_qty_cost),
        "gross_profit": _round2(inv.gross_profit),
        "closed_at": inv.closed_at,
        "notes": inv.notes,
        "steps": [
            {
                "block_id": s.block_id,
                "sort_order": s.sort_order,
                "title": s.title,
                "done": s.done,
            }
            for s in (inv.steps or [])
        ],
        "materials": [
            {
                "material_id": m.material_id,
                "name": m.name,
                "unit": m.unit,
                "norm_qty": _round3(m.norm_qty),
                "actual_qty": _round3(m.actual_qty),
                "applied_qty": _round3(m.applied_qty),
                "unit_cost": _round2(m.unit_cost),
                "line_cost": _round2(m.line_cost),
                "shortage": _round3(m.shortage),
                "delta_percent": (
                    round((float(m.actual_qty) - float(m.norm_qty)) / float(m.norm_qty) * 100, 1)
                    if float(m.norm_qty or 0) > 0
                    else 0.0
                ),
            }
            for m in (inv.materials or [])
        ],
    }


async def get_invoice(db: AsyncSession, appointment_id: int, tenant_id: UUID) -> AppointmentInvoice | None:
    result = await db.execute(
        select(AppointmentInvoice)
        .options(
            selectinload(AppointmentInvoice.steps),
            selectinload(AppointmentInvoice.materials),
            selectinload(AppointmentInvoice.box),
        )
        .where(
            AppointmentInvoice.appointment_id == appointment_id,
            AppointmentInvoice.tenant_id == tenant_id,
        )
    )
    return result.scalar_one_or_none()


async def load_tech_card(db: AsyncSession, tenant_id: UUID, service_id: int) -> TechCard | None:
    result = await db.execute(
        select(TechCard)
        .options(
            selectinload(TechCard.blocks).selectinload(TechCardBlock.items).selectinload(TechCardItem.material),
            selectinload(TechCard.items).selectinload(TechCardItem.material),
        )
        .where(
            TechCard.tenant_id == tenant_id,
            TechCard.service_id == service_id,
            TechCard.is_active.is_(True),
        )
    )
    return result.scalar_one_or_none()


def build_preview(appointment: Appointment, card: TechCard | None) -> dict:
    service = appointment.service
    catalog_cost = float(service.material_cost or 0) if service else 0.0
    steps = []
    materials: dict[int, dict] = {}
    if card and card.blocks:
        for block in card.blocks:
            step_mats = []
            for item in block.items or []:
                mid = item.material_id
                mat = item.material
                qty = float(item.quantity or 0)
                if mid not in materials:
                    materials[mid] = {
                        "material_id": mid,
                        "name": mat.name if mat else f"#{mid}",
                        "unit": mat.unit if mat else "pcs",
                        "norm_qty": 0.0,
                        "actual_qty": 0.0,
                        "stock": float(mat.quantity or 0) if mat else 0.0,
                        "unit_cost": float(mat.purchase_price or 0) if mat else 0.0,
                    }
                materials[mid]["norm_qty"] += qty
                materials[mid]["actual_qty"] += qty
                step_mats.append({"material_id": mid, "quantity": _round3(qty)})
            steps.append({
                "block_id": block.id,
                "sort_order": block.sort_order,
                "title": block.title,
                "done": True,
                "materials": step_mats,
            })
    elif card:
        for item in card.items or []:
            mid = item.material_id
            mat = item.material
            if mid not in materials:
                materials[mid] = {
                    "material_id": mid,
                    "name": mat.name if mat else f"#{mid}",
                    "unit": mat.unit if mat else "pcs",
                    "norm_qty": 0.0,
                    "actual_qty": 0.0,
                    "stock": float(mat.quantity or 0) if mat else 0.0,
                    "unit_cost": float(mat.purchase_price or 0) if mat else 0.0,
                }
            qty = float(item.quantity or 0)
            materials[mid]["norm_qty"] += qty
            materials[mid]["actual_qty"] += qty

    mat_list = []
    estimated = 0.0
    for row in materials.values():
        row["norm_qty"] = _round3(row["norm_qty"])
        row["actual_qty"] = _round3(row["actual_qty"])
        estimated += row["actual_qty"] * row["unit_cost"]
        mat_list.append(row)

    estimated_cost = _round2(estimated) if mat_list else _round2(catalog_cost)
    price = float(appointment.total_price or 0)
    return {
        "appointment_id": appointment.id,
        "service_id": appointment.service_id,
        "service_name": service.name if service else "",
        "box_id": appointment.box_id,
        "box_name": appointment.box.name if appointment.box else None,
        "price": _round2(price),
        "discount": _round2(appointment.discount_applied or 0),
        "catalog_material_cost": _round2(catalog_cost),
        "estimated_material_cost": estimated_cost,
        "estimated_gross_profit": _round2(price - estimated_cost),
        "has_tech_card": card is not None,
        "already_closed": False,
        "steps": steps,
        "materials": mat_list,
    }


async def preview_close(db: AsyncSession, appointment: Appointment, tenant_id: UUID) -> dict:
    existing = await get_invoice(db, appointment.id, tenant_id)
    if existing:
        data = serialize_invoice(existing)
        data["already_closed"] = True
        data["has_tech_card"] = bool(data["steps"] or data["materials"])
        data["estimated_material_cost"] = data["material_cost"]
        data["estimated_gross_profit"] = data["gross_profit"]
        return data
    card = await load_tech_card(db, tenant_id, appointment.service_id)
    return build_preview(appointment, card)


async def ensure_invoice(
    db: AsyncSession,
    appointment: Appointment,
    tenant_id: UUID,
    *,
    user_id: int | None,
    steps_in: list[dict] | None = None,
    materials_in: list[dict] | None = None,
    notes: str | None = None,
) -> AppointmentInvoice:
    """Создаёт чек один раз. Повторный вызов возвращает существующий (без второго списания)."""
    existing = await get_invoice(db, appointment.id, tenant_id)
    if existing:
        return existing

    if appointment.service is None and appointment.service_id:
        srv = await db.execute(select(Service).where(Service.id == appointment.service_id))
        appointment.service = srv.scalar_one_or_none()

    card = await load_tech_card(db, tenant_id, appointment.service_id)
    preview = build_preview(appointment, card)

    done_map: dict[int, bool] = {}
    if steps_in:
        for s in steps_in:
            bid = s.get("block_id")
            if bid is not None:
                done_map[int(bid)] = bool(s.get("done", True))

    actual_map: dict[int, float] = {}
    if materials_in:
        for m in materials_in:
            mid = m.get("material_id")
            if mid is not None:
                actual_map[int(mid)] = float(m.get("actual_qty", m.get("norm_qty") or 0))

    # Recalc norms from done steps if tech card has blocks
    norms: dict[int, dict] = {}
    if card and card.blocks:
        for block in card.blocks:
            done = done_map.get(block.id, True)
            for item in block.items or []:
                mid = item.material_id
                mat = item.material
                if mid not in norms:
                    norms[mid] = {
                        "material": mat,
                        "norm": 0.0,
                    }
                if done:
                    norms[mid]["norm"] += float(item.quantity or 0)
    elif card:
        for item in card.items or []:
            mid = item.material_id
            if mid not in norms:
                norms[mid] = {"material": item.material, "norm": 0.0}
            norms[mid]["norm"] += float(item.quantity or 0)

    step_rows = []
    if preview["steps"]:
        for s in preview["steps"]:
            bid = s["block_id"]
            step_rows.append(
                AppointmentCloseStep(
                    block_id=bid,
                    sort_order=s["sort_order"],
                    title=s["title"],
                    done=done_map.get(bid, True),
                )
            )

    material_rows = []
    total_cost = 0.0
    shortage_cost = 0.0
    for mid, info in norms.items():
        mat: Material | None = info["material"]
        norm = _round3(info["norm"])
        actual = _round3(actual_map.get(mid, norm))
        unit_cost = float(mat.purchase_price or 0) if mat else 0.0
        applied = 0.0
        if actual > 0 and mat is not None:
            _mat, applied_delta = await apply_stock_delta(
                db,
                tenant_id,
                mid,
                -actual,
                reason=f"Закрытие заезда #{appointment.id}",
                created_by_id=user_id,
                appointment_id=appointment.id,
            )
            applied = _round3(abs(applied_delta))
        shortage = _round3(max(0.0, actual - applied))
        line = _round2(applied * unit_cost)
        total_cost += line
        shortage_cost += _round2(shortage * unit_cost)
        material_rows.append(
            AppointmentCloseMaterial(
                material_id=mid,
                name=mat.name if mat else f"#{mid}",
                unit=mat.unit if mat else "pcs",
                norm_qty=norm,
                actual_qty=actual,
                applied_qty=applied,
                unit_cost=unit_cost,
                line_cost=line,
                shortage=shortage,
            )
        )

    catalog_cost = float(appointment.service.material_cost or 0) if appointment.service else 0.0
    if not material_rows:
        total_cost = catalog_cost

    price = float(appointment.total_price or 0)
    discount = float(appointment.discount_applied or 0)
    service_name = appointment.service.name if appointment.service else preview["service_name"]

    inv = AppointmentInvoice(
        tenant_id=tenant_id,
        appointment_id=appointment.id,
        box_id=appointment.box_id,
        service_id=appointment.service_id,
        service_name=service_name or "",
        price=price,
        discount=discount,
        material_cost=_round2(total_cost),
        catalog_material_cost=_round2(catalog_cost),
        shortage_qty_cost=_round2(shortage_cost),
        gross_profit=_round2(price - total_cost),
        closed_by_id=user_id,
        closed_at=datetime.now(timezone.utc),
        notes=notes,
        steps=step_rows,
        materials=material_rows,
    )
    db.add(inv)
    await db.flush()
    loaded = await get_invoice(db, appointment.id, tenant_id)
    return loaded or inv
