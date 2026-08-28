"""HTTP API — модуль core."""
from __future__ import annotations

from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query, UploadFile, File, status, Body, Request
from fastapi.responses import StreamingResponse, Response
from sqlalchemy import func, or_, select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db
from app.core.auth import (
    get_current_user as _get_current_user,
    require_admin as _require_admin,
    require_master as _require_master,
    hash_password as _hash_password,
    verify_password as _verify_password,
    create_token as _create_token,
)
from app.core.endpoint_helpers import *  # noqa: F401,F403
from app.core.image_service import (
    validate_image,
    save_file_local,
    generate_filename,
    delete_file_local,
    resolve_portfolio_url,
)
from app.core.deepseek_client import get_ai_response, get_financier_response, get_consultant_response
from app.models import *  # noqa: F401,F403
from app.schemas import *  # noqa: F401,F403

router = APIRouter()

@router.get("/api/tenants")
async def get_tenants(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить список всех тенантов (только admin/super_admin)."""
    stmt = select(Tenant).order_by(Tenant.name)
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[TenantOut](
        items=[TenantOut.model_validate(t) for t in items],
        total=total, skip=skip, limit=limit,
    )

@router.post("/api/tenants", response_model=TenantOut)
async def create_tenant(
    request: TenantCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый тенант (только admin/super_admin)."""
    # Проверка уникальности subdomain
    existing = await db.execute(select(Tenant).where(Tenant.subdomain == request.subdomain))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Tenant with this subdomain already exists")

    tenant = Tenant(
        name=request.name,
        subdomain=request.subdomain,
        logo_url=request.logo_url,
        config=request.config or {},
    )
    db.add(tenant)
    await db.commit()
    await db.refresh(tenant)
    return TenantOut.model_validate(tenant)

@router.get("/api/tenants/{tenant_id}", response_model=TenantOut)
async def get_tenant(
    tenant_id: UUID,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить тенант по ID."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")
    return TenantOut.model_validate(tenant)

@router.put("/api/tenants/{tenant_id}", response_model=TenantOut)
async def update_tenant(
    tenant_id: UUID,
    request: TenantUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить тенант."""
    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(tenant, key, value)

    await db.commit()
    await db.refresh(tenant)
    return TenantOut.model_validate(tenant)

@router.delete("/api/tenants/{tenant_id}")
async def delete_tenant(
    tenant_id: UUID,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить тенант (только super_admin)."""
    if current_user["role"] != "super_admin":
        raise HTTPException(status_code=403, detail="Только super_admin может удалять тенанты")

    result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
    tenant = result.scalar_one_or_none()
    if not tenant:
        raise HTTPException(status_code=404, detail="Tenant not found")

    await db.delete(tenant)
    await db.commit()
    return {"message": f"Tenant '{tenant.name}' deleted"}

@router.post("/api/register", response_model=AuthResponse)
async def register(request: RegisterRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == request.phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Пользователь уже существует")

    # Определяем tenant_id
    tenant_id = request.tenant_id
    if tenant_id is None:
        # Для публичной регистрации используем дефолтный тенант
        tenant_result = await db.execute(select(Tenant).limit(1))
        default_tenant = tenant_result.scalar_one_or_none()
        if not default_tenant:
            raise HTTPException(status_code=400, detail="Нет доступного тенанта. Укажите tenant_id.")
        tenant_id = default_tenant.id
    else:
        # Проверяем, что тенант существует
        tenant_result = await db.execute(select(Tenant).where(Tenant.id == tenant_id))
        if not tenant_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Тенант не найден")

    hashed = _hash_password(request.password)
    user = User(
        phone=request.phone,
        password=hashed,
        full_name=request.full_name,
        role="client",
        tenant_id=tenant_id,
    )
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _create_token(user.id, str(tenant_id))
    return AuthResponse(token=token, user=UserOut.model_validate(user))

@router.post("/api/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный телефон или пароль")

    tenant_id = str(user.tenant_id) if user.tenant_id else ""
    token = _create_token(user.id, tenant_id)
    return AuthResponse(token=token, user=UserOut.model_validate(user))

@router.get("/api/me")
async def get_me(current_user: dict = Depends(_get_current_user)):
    return current_user

@router.put("/api/me", response_model=UserOut)
async def update_me(
    request: UserProfileUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == current_user["id"]))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")
    if request.full_name:
        user.full_name = request.full_name.strip()
    if request.phone:
        phone = request.phone.strip()
        taken = await db.execute(
            select(User).where(User.phone == phone, User.id != user.id)
        )
        if taken.scalar_one_or_none():
            raise HTTPException(status_code=400, detail="Этот телефон уже занят")
        user.phone = phone
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)

@router.get("/api/users")
async def get_users(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить список всех пользователей в тенанте (только админ)"""
    stmt = (
        select(User)
        .where(User.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(User.role, User.full_name)
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[UserListOut](
        items=[UserListOut.model_validate(u) for u in items],
        total=total, skip=skip, limit=limit,
    )

@router.put("/api/users/{user_id}/role", response_model=UserOut)
async def update_user_role(
    user_id: int,
    request: UserRoleUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Изменить роль пользователя (только админ)"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    valid_roles = [e.value for e in UserRole]
    if request.role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Недопустимая роль. Доступно: {valid_roles}")

    user.role = request.role
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)

@router.delete("/api/users/{user_id}")
async def delete_user(
    user_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить пользователя (только admin/super_admin).

    - Нельзя удалить самого себя
    - Нельзя удалить супер-администратора
    - Каскадно удаляются автомобили и записи клиента
    - У записей, где пользователь был мастером, master_id = NULL
    """
    if user_id == current_user["id"]:
        raise HTTPException(status_code=400, detail="Нельзя удалить самого себя")

    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if user.role == "super_admin":
        raise HTTPException(status_code=400, detail="Нельзя удалить супер-администратора")

    full_name = user.full_name
    await db.delete(user)
    await db.commit()
    return {"message": f"Пользователь «{full_name}» удалён", "user_id": user_id}

@router.get("/api/users/segments", response_model=RfmResponse)
async def get_rfm_segments(
    segment: str = "",
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """RFM-сегментация клиентов с фильтром по сегменту."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Все клиенты тенанта
    clients_result = await db.execute(
        select(User).where(User.role == "client", User.tenant_id == tenant_id)
    )
    clients = clients_result.scalars().all()

    # Все их завершённые записи
    client_ids = [c.id for c in clients]
    if not client_ids:
        return RfmResponse(clients=[], segments=[], total=0)

    appts_result = await db.execute(
        select(Appointment).where(
            Appointment.client_id.in_(client_ids),
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        ).order_by(Appointment.start_time)
    )
    all_appts = appts_result.scalars().all()

    # Группировка записей по client_id
    client_appts: dict[int, list] = defaultdict(list)
    for a in all_appts:
        client_appts[a.client_id].append(a)

    # Расчёт RFM для каждого клиента
    rfm_clients: list[RfmClient] = []
    for c in clients:
        appts = client_appts.get(c.id, [])
        freq = len(appts)
        monetary = sum(float(a.total_price or 0) for a in appts)

        recency = 999
        last_visit = None
        if appts:
            last = max(a.start_time for a in appts)
            last_visit = last.isoformat() if last else None
            recency = (now - last).days if last else 999

        # Определение сегмента
        if recency <= 30 and freq > 10 and monetary > 100000:
            seg = "vip"
        elif recency <= 60 and freq > 5:
            seg = "loyal"
        elif freq == 1 and recency <= 30:
            seg = "new"
        elif 60 < recency <= 90:
            seg = "sleeping"
        elif recency > 90:
            seg = "lost"
        else:
            seg = "regular"

        rfm_clients.append(RfmClient(
            id=c.id,
            full_name=c.full_name,
            phone=c.phone,
            recency_days=recency,
            frequency=freq,
            monetary=round(monetary, 2),
            segment=seg,
            last_visit=last_visit,
            created_at=c.created_at.isoformat() if c.created_at else None,
        ))

    # Подсчёт по сегментам
    seg_counts: dict[str, dict] = {}
    for rc in rfm_clients:
        s = rc.segment
        if s not in seg_counts:
            seg_counts[s] = {"count": 0, "total_revenue": 0.0}
        seg_counts[s]["count"] += 1
        seg_counts[s]["total_revenue"] += rc.monetary

    total_clients = len(rfm_clients)
    segments_summary = [
        SegmentCount(
            segment=s,
            count=v["count"],
            total_revenue=round(v["total_revenue"], 2),
            percent=round(v["count"] / total_clients * 100, 1) if total_clients else 0,
        )
        for s, v in sorted(seg_counts.items())
    ]

    # Фильтрация по сегменту
    if segment:
        rfm_clients = [rc for rc in rfm_clients if rc.segment == segment]

    return RfmResponse(
        clients=rfm_clients,
        segments=segments_summary,
        total=len(rfm_clients),
    )

@router.get("/api/users/{user_id}", response_model=UserDetailOut)
async def get_user_detail(
    user_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить детальную карточку клиента с историей"""
    result = await db.execute(
        select(User).where(
            User.id == user_id,
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    appts_result = await db.execute(
        select(Appointment)
        .where(
            Appointment.client_id == user_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Appointment.start_time.desc())
    )
    appointments = appts_result.scalars().all()

    return UserDetailOut(
        id=user.id,
        phone=user.phone,
        full_name=user.full_name,
        role=user.role,
        created_at=user.created_at,
        appointments_count=len(appointments),
        total_spent=sum(
            float(a.total_price or 0) for a in appointments if a.status == "completed"
        ),
        last_visit=appointments[0].start_time if appointments else None,
    )

