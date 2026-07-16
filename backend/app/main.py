"""
CarDetailing AI — Main Application.

FastAPI entry point with database-backed authentication.
"""

import contextlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from uuid import UUID

import bcrypt
import jwt
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.deepseek_client import get_ai_response, get_financier_response
from app.core.image_service import validate_image, save_file_local, generate_filename, delete_file_local
from app.models import Tenant, User, UserRole, AppointmentStatus, Service, Car, Appointment, Expense, DiscountRule, ClientDiscount, LoyaltyPoints, LoyaltyTierConfig, Photo, EntityType, Notification, UserNotificationSettings, WorkingHours, AppointmentHistory, Payment
from app.schemas import (
    RegisterRequest, LoginRequest, AuthResponse, UserOut,
    ServiceCreate, ServiceUpdate, ServiceOut,
    CarCreate, CarOut,
    AppointmentCreate, AppointmentStatusUpdate, AppointmentOut,
    MasterStatusUpdate, MasterNotesUpdate, ClientAppointmentEdit,
    UserListOut, UserRoleUpdate, UserDetailOut,
    KpiOut, ChatRequest, ChatResponse,
    FinancierRequest, FinancierResponse,
    TenantCreate, TenantUpdate, TenantOut,
    ExpenseCreate, ExpenseUpdate, ExpenseOut,
    PLReport, ServiceMargin,
    RevenueResponse, RevenuePoint, HeatmapResponse, HeatmapCell,
    FunnelResponse, FunnelStage,
    RfmResponse, RfmClient, SegmentCount,
    DiscountRuleCreate, DiscountRuleUpdate, DiscountRuleOut,
    ClientDiscountOut, LoyaltyPointsSummary, LoyaltyTierConfigOut, LoyaltyTierConfigUpdate, ClientTierOut,
    PaginatedResponse,
    PhotoOut, PhotoOrderUpdate, PhotoCreateResponse,
    NotificationOut, UnreadCountOut,
    NotificationSettingsOut, NotificationSettingsUpdate,
    TelegramConnectRequest,
    WorkingHoursOut, WorkingHoursUpdate,
    CalendarResponse, CalendarDay, CalendarAppointment, HistoryEntryOut, HistoryResponse, ServiceTrendPoint, ServiceTrend, ServiceComparison, TopService, ForecastPoint, ServiceAnalyticsResponse, PaymentCreateRequest, PaymentOut, PaymentWebhookRequest, RevenueDetail, PeriodComparison, MasterRevenueSummary, ServiceRevenueSummary, RevenueReportResponse,
)

@contextlib.asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup and shutdown events."""
    await init_db()
    async for db in get_db():
        tenant_result = await db.execute(select(Tenant).limit(1))
        default_tenant = tenant_result.scalar_one_or_none()
        if not default_tenant:
            default_tenant = Tenant(
                name="Default Workshop",
                subdomain="default",
            )
            db.add(default_tenant)
            await db.commit()
            await db.refresh(default_tenant)
            print(f"[OK] Default tenant created (id={default_tenant.id}, name='{default_tenant.name}')")
        else:
            print(f"[OK] Tenant already exists (id={default_tenant.id}, name='{default_tenant.name}')")
        result = await db.execute(select(User).where(User.role == "super_admin"))
        if not result.scalar_one_or_none():
            super_admin = User(
                phone="+79999999999",
                password=_hash_password("admin123"),
                full_name="Супер Администратор",
                role="super_admin",
                tenant_id=default_tenant.id,
            )
            db.add(super_admin)
            await db.commit()
            print("[OK] Super-admin created (phone: +79999999999, password: admin123)")
        else:
            print("[OK] Super-admin already exists")
        break
    yield

app = FastAPI(title="CarDetailing AI", version="1.0.0", lifespan=lifespan)

# ========== CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== JWT ==========
SECRET_KEY = settings.JWT_SECRET
ALGORITHM = settings.JWT_ALGORITHM
ACCESS_TOKEN_EXPIRE_MINUTES = settings.JWT_EXPIRE_MINUTES

security = HTTPBearer()

# ========== HELPERS ==========
def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def _create_token(user_id: int, tenant_id: str) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "tenant_id": tenant_id, "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
        tenant_id = payload.get("tenant_id")
    except jwt.PyJWTError:
        raise HTTPException(status_code=401, detail="Недействительный токен")

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=401, detail="Пользователь не найден")

    return {
        "id": user.id,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role,
        "tenant_id": tenant_id,
    }

def _require_admin(current_user: dict = Depends(_get_current_user)):
    if current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён. Только для администраторов.")
    return current_user


def _require_master(current_user: dict = Depends(_get_current_user)):
    """Проверка: текущий пользователь — мастер (или админ)."""
    if current_user["role"] not in ["master", "admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён. Только для мастеров.")
    return current_user


# ========== PAGINATION HELPER ==========

async def _paginate(db: AsyncSession, stmt, skip: int = 0, limit: int = 20):
    """Execute a SELECT statement with pagination.

    Returns (items_list, total_count).
    Uses a separate COUNT query for the total.
    """
    # Count total rows
    count_stmt = select(func.count()).select_from(stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    # Apply pagination
    result = await db.execute(stmt.offset(skip).limit(limit))
    items = result.scalars().all()

    return items, total


# ========== HEALTH ==========
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "CarDetailing AI is running!"}

# ========== TENANTS ==========
@app.get("/api/tenants")
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


@app.post("/api/tenants", response_model=TenantOut)
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


@app.get("/api/tenants/{tenant_id}", response_model=TenantOut)
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


@app.put("/api/tenants/{tenant_id}", response_model=TenantOut)
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


@app.delete("/api/tenants/{tenant_id}")
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

# ========== AUTH ==========
@app.post("/api/register", response_model=AuthResponse)
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

@app.post("/api/login", response_model=AuthResponse)
async def login(request: LoginRequest, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.phone == request.phone))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(request.password, user.password):
        raise HTTPException(status_code=401, detail="Неверный телефон или пароль")

    tenant_id = str(user.tenant_id) if user.tenant_id else ""
    token = _create_token(user.id, tenant_id)
    return AuthResponse(token=token, user=UserOut.model_validate(user))

@app.get("/api/me")
async def get_me(current_user: dict = Depends(_get_current_user)):
    return current_user

# ========== SERVICES ==========
@app.get("/api/services")
async def get_services(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Service)
        .where(
            Service.is_active == True,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Service.name)
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[ServiceOut](
        items=[ServiceOut.model_validate(s) for s in items],
        total=total, skip=skip, limit=limit,
    )

@app.post("/api/services", response_model=ServiceOut)
async def create_service(
    request: ServiceCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    service = Service(
        name=request.name,
        description=request.description,
        category=request.category,
        price=request.price,
        duration=request.duration,
        material_cost=request.material_cost,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)


@app.put("/api/services/{service_id}", response_model=ServiceOut)
async def update_service(
    service_id: int,
    request: ServiceUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    update_data = request.model_dump(exclude_unset=True)
    for key, value in update_data.items():
        setattr(service, key, value)

    await db.commit()
    await db.refresh(service)
    return ServiceOut.model_validate(service)


@app.delete("/api/services/{service_id}")
async def delete_service(
    service_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Service).where(
            Service.id == service_id,
            Service.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Услуга не найдена")

    # Проверяем, есть ли связанные записи
    appt_result = await db.execute(
        select(Appointment).where(Appointment.service_id == service_id)
    )
    related_appts = appt_result.scalars().all()
    if related_appts:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя удалить услугу «{service.name}»: есть {len(related_appts)} связанн{'ая' if len(related_appts) == 1 else 'ые'} запис{'ь' if len(related_appts) == 1 else 'и'}. "
                   f"Сначала удалите или переназначьте записи.",
        )

    await db.delete(service)
    await db.commit()
    return {"message": f"Услуга «{service.name}» удалена"}

# ========== APPOINTMENTS ==========
def _serialize_appointment(appointment):
    return {
        "id": appointment.id,
        "client_id": appointment.client_id,
        "master_id": appointment.master_id,
        "car_id": appointment.car_id,
        "service_id": appointment.service_id,
        "start_time": appointment.start_time,
        "end_time": appointment.end_time,
        "status": appointment.status if appointment.status else None,
        "total_price": float(appointment.total_price) if appointment.total_price is not None else 0,
        "discount_applied": float(appointment.discount_applied) if appointment.discount_applied is not None else 0,
        "client_notes": appointment.client_notes,
        "master_brief": appointment.master_brief,
        "created_at": appointment.created_at,
        "updated_at": appointment.updated_at,
        "service_name": appointment.service.name if appointment.service else None,
        "client": {
            "id": appointment.client.id,
            "full_name": appointment.client.full_name,
            "phone": appointment.client.phone,
        } if appointment.client else None,
        "master": {
            "id": appointment.master.id,
            "full_name": appointment.master.full_name,
        } if appointment.master else None,
        "car": {
            "id": appointment.car.id,
            "make": appointment.car.make,
            "model": appointment.car.model,
            "license_plate": appointment.car.license_plate,
        } if appointment.car else None,
        "service": {
            "id": appointment.service.id,
            "name": appointment.service.name,
            "price": float(appointment.service.price),
        } if appointment.service else None,
    }

@app.get("/api/appointments")
async def get_all_appointments(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(Appointment.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@app.get("/api/appointments/me")
async def get_my_appointments(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(
            Appointment.client_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }

@app.get("/api/appointments/{appointment_id}")
async def get_appointment(
    appointment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.car),
            selectinload(Appointment.master),
        )
        .where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.client_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return _serialize_appointment(appointment)

@app.post("/api/appointments", response_model=AppointmentOut)
async def create_appointment(
    request: AppointmentCreate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Проверка услуги
    result = await db.execute(select(Service).where(Service.id == request.service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Проверка машины
    result = await db.execute(select(Car).where(Car.id == request.car_id, Car.client_id == current_user["id"]))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    start_time = datetime.fromisoformat(request.start_time)
    # Приводим к timezone-aware (UTC), т.к. колонки DateTime(timezone=True)
    if start_time.tzinfo is None:
        # Если часовой пояс не указан — считаем, что время уже в UTC
        start_time = start_time.replace(tzinfo=timezone.utc)
    else:
        # Если часовой пояс указан — конвертируем в UTC
        start_time = start_time.astimezone(timezone.utc)

    end_time = start_time + timedelta(minutes=service.duration)

    appointment = Appointment(
        client_id=current_user["id"],
        service_id=request.service_id,
        car_id=request.car_id,
        start_time=start_time,
        end_time=end_time,
        total_price=service.price,
        status="pending",
        client_notes=request.notes or request.client_notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # Автоматическое применение скидок
    await _auto_apply_discount(appointment.id, db)

    # Перезагружаем запись после применения скидки
    await db.refresh(appointment)

    # Загружаем связи, чтобы не упасть с MissingGreenlet
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment.id)
        .options(selectinload(Appointment.client), selectinload(Appointment.service), selectinload(Appointment.car), selectinload(Appointment.master))
    )
    
    loaded = result.scalar_one()
    # History: log creation
    from app.services.history_service import log_create as _log_create
    await _log_create(db, loaded, current_user["id"])

    return _serialize_appointment(loaded)

# Общие опции загрузки связей Appointment — предотвращает MissingGreenlet
_APPT_LOAD = (
    selectinload(Appointment.client),
    selectinload(Appointment.service),
    selectinload(Appointment.car),
    selectinload(Appointment.master),
)


@app.put("/api/appointments/{appointment_id}")
async def update_appointment_status(
    appointment_id: int,
    request: AppointmentStatusUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    # Capture old data for history
    old_data = {
        "status": appointment.status,
        "master_id": appointment.master_id,
        "master_brief": appointment.master_brief,
    }
    if request.status is not None:
        appointment.status = request.status
    if request.master_id is not None:
        appointment.master_id = request.master_id
    if request.master_brief is not None:
        appointment.master_brief = request.master_brief

    await db.commit()

    # Начисляем баллы, если статус стал completed
    if request.status == "completed":
        await _award_loyalty_points(appointment.id, db)

    return _serialize_appointment(appointment)

# ========== CANCEL APPOINTMENT (CLIENT) ==========
@app.put("/api/appointments/{appointment_id}/cancel")
async def cancel_appointment(
    appointment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отменить запись (только свою, только в статусах pending/confirmed)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.client_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    if appointment.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя отменить запись в статусе «{appointment.status}». "
                   f"Допустимо только для «Ожидает» или «Подтверждена».",
        )

    appointment.status = "cancelled"
    await db.commit()

    # Перезагружаем со связями, чтобы избежать MissingGreenlet
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
        )
    )
    appointment = result.scalar_one()

    # History: log cancel
    from app.services.history_service import log_cancel as _log_cancel
    await _log_cancel(db, appointment, current_user["id"])
    return _serialize_appointment(appointment)


# ========== EDIT APPOINTMENT (CLIENT) ==========
@app.put("/api/appointments/{appointment_id}/edit")
async def edit_appointment(
    appointment_id: int,
    request: ClientAppointmentEdit,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Редактировать запись (только свою, только в статусах pending/confirmed)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.client_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    if appointment.status not in ["pending", "confirmed"]:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя редактировать запись в статусе «{appointment.status}».",
        )

    # Update fields if provided
    if request.start_time is not None:
        start_time = datetime.fromisoformat(request.start_time)
        if start_time.tzinfo is None:
            start_time = start_time.replace(tzinfo=timezone.utc)
        appointment.start_time = start_time
        # Recalculate end_time based on service duration
        appointment.end_time = start_time + timedelta(minutes=appointment.service.duration)

    if request.car_id is not None:
        # Verify car belongs to user
        car_result = await db.execute(
            select(Car).where(Car.id == request.car_id, Car.client_id == current_user["id"])
        )
        car = car_result.scalar_one_or_none()
        if not car:
            raise HTTPException(status_code=404, detail="Автомобиль не найден")
        appointment.car_id = request.car_id

    if request.client_notes is not None:
        appointment.client_notes = request.client_notes

    await db.commit()
    # Reload with relationships for serialization
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment_id)
        .options(*_APPT_LOAD)
    )
    return _serialize_appointment(result.scalar_one())


# ========== MASTER ENDPOINTS ==========
@app.get("/api/masters/me/appointments")
async def get_my_master_appointments(
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить записи, назначенные текущему мастеру."""
    stmt = (
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(
            Appointment.master_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Appointment.start_time.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_serialize_appointment(a) for a in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.put("/api/masters/me/appointments/{appointment_id}/status")
async def update_master_appointment_status(
    appointment_id: int,
    request: MasterStatusUpdate,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Сменить статус записи (master: in_progress → completed или confirmed → in_progress)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    new_status = request.status
    # Разрешённые переходы для мастера
    valid_transitions = {
        "confirmed": ["in_progress"],
        "in_progress": ["completed"],
    }
    allowed = valid_transitions.get(appointment.status, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя сменить статус с '{appointment.status}' на '{new_status}'. "
                   f"Допустимо: {allowed}",
        )

    appointment.status = new_status

    await db.commit()

    # History: log status change
    from app.services.history_service import log_status_change as _log_sc
    await _log_sc(db, appointment.id, appointment.status, new_status, current_user["id"])

    # Начисляем баллы, если мастер завершил запись
    if new_status == "completed":
        await _award_loyalty_points(appointment.id, db)

    return _serialize_appointment(appointment)


@app.put("/api/masters/me/appointments/{appointment_id}/notes")
async def update_master_appointment_notes(
    appointment_id: int,
    request: MasterNotesUpdate,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Добавить/обновить заметку мастера по записи."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    appointment.master_brief = request.master_brief
    await db.commit()
    return _serialize_appointment(appointment)


# ========== USERS MANAGEMENT ==========
@app.get("/api/users")
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


@app.put("/api/users/{user_id}/role", response_model=UserOut)
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


@app.delete("/api/users/{user_id}")
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

# ========== RFM SEGMENTATION ==========

@app.get("/api/users/segments", response_model=RfmResponse)
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





@app.get("/api/users/{user_id}", response_model=UserDetailOut)
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


# ========== ANALYTICS ==========
@app.get("/api/analytics/kpi", response_model=KpiOut)
async def get_kpi(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ключевые показатели для дашборда владельца"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Клиенты
    clients_result = await db.execute(
        select(User).where(
            User.role == "client",
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    total_clients = len(clients_result.scalars().all())

    # Мастера
    masters_result = await db.execute(
        select(User).where(
            User.role == "master",
            User.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    total_masters = len(masters_result.scalars().all())

    # Записи сегодня
    today_result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= today_start,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    today_appts = today_result.scalars().all()

    # Записи за месяц
    month_result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    month_appts = month_result.scalars().all()

    # Выручка
    today_revenue = sum(
        float(a.total_price or 0) for a in today_appts if a.status == "completed"
    )
    month_revenue = sum(
        float(a.total_price or 0) for a in month_appts if a.status == "completed"
    )

    # Ожидающие
    pending_result = await db.execute(
        select(Appointment).where(
            Appointment.status == "pending",
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    pending_count = len(pending_result.scalars().all())

    return KpiOut(
        total_clients=total_clients,
        total_masters=total_masters,
        today_appointments=len(today_appts),
        today_revenue=today_revenue,
        month_revenue=month_revenue,
        pending_appointments=pending_count,
        completed_month=sum(1 for a in month_appts if a.status == "completed"),
    )


# ========== AI ==========
@app.post("/api/ai/chat", response_model=ChatResponse)
async def ai_chat(request: ChatRequest):
    response = await get_ai_response(request.message)
    return ChatResponse(response=response)


@app.post("/api/ai/financier", response_model=FinancierResponse)
async def ai_financier(
    request: FinancierRequest,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """AI-финансист: аналитика бизнеса + рекомендации."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Сбор контекста ---

    # Всего клиентов / мастеров
    clients_result = await db.execute(
        select(User).where(User.role == "client", User.tenant_id == tenant_id)
    )
    total_clients = len(clients_result.scalars().all())

    masters_result = await db.execute(
        select(User).where(User.role == "master", User.tenant_id == tenant_id)
    )
    total_masters = len(masters_result.scalars().all())

    # Выручка сегодня / месяц
    month_appts = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    month_list = month_appts.scalars().all()
    month_revenue = sum(float(a.total_price or 0) for a in month_list if a.status == "completed")

    today_appts = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= today_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    today_list = today_appts.scalars().all()
    today_revenue = sum(float(a.total_price or 0) for a in today_list if a.status == "completed")

    # Записи
    total_appts = len(month_list)
    completed_appts = sum(1 for a in month_list if a.status == "completed")
    pending_appts = sum(1 for a in month_list if a.status == "pending")

    # Эффективность мастеров
    master_stats = {}
    for a in month_list:
        if a.master_id and a.status == "completed":
            master_name = f"мастер #{a.master_id}"
            if a.master_id not in master_stats:
                result = await db.execute(select(User).where(User.id == a.master_id))
                master = result.scalar_one_or_none()
                master_name = master.full_name if master else master_name
                master_stats[a.master_id] = {"name": master_name, "completed": 0, "revenue": 0.0}
            master_stats[a.master_id]["completed"] += 1
            master_stats[a.master_id]["revenue"] += float(a.total_price or 0)

    # Популярность услуг
    service_popularity = {}
    for a in month_list:
        if a.service_id:
            if a.service_id not in service_popularity:
                srv_result = await db.execute(select(Service).where(Service.id == a.service_id))
                srv = srv_result.scalar_one_or_none()
                service_popularity[a.service_id] = {
                    "name": srv.name if srv else f"услуга #{a.service_id}",
                    "count": 0,
                }
            service_popularity[a.service_id]["count"] += 1

    # Формируем текст контекста
    ctx_lines = [
        f"• Всего клиентов: {total_clients}",
        f"• Всего мастеров: {total_masters}",
        f"• Записей за месяц: {total_appts} (завершено: {completed_appts}, ожидают: {pending_appts})",
        f"• Записей сегодня: {len(today_list)}",
        f"• Выручка за месяц: {month_revenue:.0f} руб.",
        f"• Выручка сегодня: {today_revenue:.0f} руб.",
    ]

    if master_stats:
        ctx_lines.append("\nЭффективность мастеров (за месяц):")
        for m in sorted(master_stats.values(), key=lambda x: x["completed"], reverse=True):
            ctx_lines.append(f"  • {m['name']}: {m['completed']} работ(ы), {m['revenue']:.0f} руб.")

    if service_popularity:
        ctx_lines.append("\nПопулярность услуг (за месяц):")
        for s in sorted(service_popularity.values(), key=lambda x: x["count"], reverse=True):
            ctx_lines.append(f"  • {s['name']}: {s['count']} записей")

    business_context = "\n".join(ctx_lines)
    response = await get_financier_response(request.question, business_context)
    return FinancierResponse(response=response)


# ========== EXPENSES & P&L ==========

@app.get("/api/expenses")
async def get_expenses(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Список всех расходов тенанта."""
    stmt = (
        select(Expense)
        .where(Expense.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(Expense.expense_date.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[ExpenseOut](
        items=[ExpenseOut.model_validate(e) for e in items],
        total=total, skip=skip, limit=limit,
    )


@app.post("/api/expenses", response_model=ExpenseOut)
async def create_expense(
    request: ExpenseCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый расход."""
    expense_date = None
    if request.expense_date:
        try:
            expense_date = datetime.fromisoformat(request.expense_date)
        except ValueError:
            pass

    expense = Expense(
        name=request.name,
        amount=request.amount,
        category=request.category,
        expense_date=expense_date,
        notes=request.notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return ExpenseOut.model_validate(expense)


@app.put("/api/expenses/{expense_id}", response_model=ExpenseOut)
async def update_expense(
    expense_id: int,
    request: ExpenseUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить расход."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    update_data = request.model_dump(exclude_unset=True)
    if "expense_date" in update_data and update_data["expense_date"]:
        try:
            update_data["expense_date"] = datetime.fromisoformat(update_data["expense_date"])
        except ValueError:
            del update_data["expense_date"]

    for key, value in update_data.items():
        setattr(expense, key, value)

    await db.commit()
    await db.refresh(expense)
    return ExpenseOut.model_validate(expense)


@app.delete("/api/expenses/{expense_id}")
async def delete_expense(
    expense_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить расход."""
    result = await db.execute(
        select(Expense).where(
            Expense.id == expense_id,
            Expense.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    expense = result.scalar_one_or_none()
    if not expense:
        raise HTTPException(status_code=404, detail="Expense not found")

    await db.delete(expense)
    await db.commit()
    return {"message": f"Расход «{expense.name}» удалён"}


@app.get("/api/analytics/pl", response_model=PLReport)
async def get_pl_report(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """P&L отчёт: прибыли и убытки + маржинальность услуг."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # --- Выручка ---
    month_appts = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service))
        .where(
            Appointment.start_time >= month_start,
            Appointment.tenant_id == tenant_id,
        )
    )
    appts = month_appts.scalars().all()
    completed = [a for a in appts if a.status == "completed"]

    total_revenue = sum(float(a.total_price or 0) for a in completed)
    completed_count = len(completed)
    avg_check = round(total_revenue / completed_count, 2) if completed_count else 0

    # --- Материальные затраты ---
    total_material_cost = sum(float(a.service.material_cost or 0) for a in completed if a.service)

    # --- Маржинальность по услугам ---
    service_map: dict[int, dict] = {}
    for a in completed:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_map:
            srv = a.service
            service_map[sid] = {
                "service_id": sid,
                "service_name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "total_revenue": 0.0,
                "total_material_cost": 0.0,
                "appointment_count": 0,
            }
        service_map[sid]["total_revenue"] += float(a.total_price or 0)
        service_map[sid]["total_material_cost"] += float(a.service.material_cost or 0) if a.service else 0
        service_map[sid]["appointment_count"] += 1

    service_margins = []
    for s in service_map.values():
        gp = s["total_revenue"] - s["total_material_cost"]
        mp = round(gp / s["total_revenue"] * 100, 1) if s["total_revenue"] else 0
        service_margins.append(ServiceMargin(
            service_id=s["service_id"],
            service_name=s["service_name"],
            category=s["category"],
            total_revenue=round(s["total_revenue"], 2),
            total_material_cost=round(s["total_material_cost"], 2),
            gross_profit=round(gp, 2),
            margin_percent=mp,
            appointment_count=s["appointment_count"],
        ))
    service_margins.sort(key=lambda x: x.appointment_count, reverse=True)

    # --- Постоянные расходы ---
    expenses_result = await db.execute(
        select(Expense).where(
            Expense.tenant_id == tenant_id,
            Expense.expense_date >= month_start,
        )
    )
    expenses = expenses_result.scalars().all()
    total_expenses = sum(float(e.amount or 0) for e in expenses)

    expenses_by_category: dict[str, float] = {}
    for e in expenses:
        cat = e.category or "other"
        expenses_by_category[cat] = expenses_by_category.get(cat, 0) + float(e.amount or 0)

    # --- Итоговые расчёты ---
    gross_profit = round(total_revenue - total_material_cost, 2)
    gross_margin = round(gross_profit / total_revenue * 100, 1) if total_revenue else 0
    net_profit = round(gross_profit - total_expenses, 2)
    net_margin = round(net_profit / total_revenue * 100, 1) if total_revenue else 0

    return PLReport(
        total_revenue=round(total_revenue, 2),
        completed_appointments=completed_count,
        avg_check=avg_check,
        total_material_cost=round(total_material_cost, 2),
        total_expenses=round(total_expenses, 2),
        expenses_by_category=expenses_by_category,
        gross_profit=gross_profit,
        gross_margin_percent=gross_margin,
        net_profit=net_profit,
        net_margin_percent=net_margin,
        service_margins=service_margins,
        period="month",
    )


# ========== ANALYTICS CHARTS ==========

@app.get("/api/analytics/revenue", response_model=RevenueResponse)
async def get_revenue_chart(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Дневная выручка за текущий месяц (Area Chart)."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Берём следующий месяц для верхней границы
    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.start_time < next_month,
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        ).order_by(Appointment.start_time)
    )
    appts = result.scalars().all()

    # Группировка по дням
    daily: dict[str, dict] = {}
    days_in_month = (next_month - month_start).days
    for i in range(days_in_month):
        day = month_start + timedelta(days=i)
        key = day.strftime("%Y-%m-%d")
        daily[key] = {"revenue": 0.0, "appointments": 0}

    for a in appts:
        key = a.start_time.strftime("%Y-%m-%d")
        if key in daily:
            daily[key]["revenue"] += float(a.total_price or 0)
            daily[key]["appointments"] += 1

    points = [
        RevenuePoint(date=key, revenue=round(v["revenue"], 2), appointments=v["appointments"])
        for key, v in sorted(daily.items())
    ]

    total = round(sum(p.revenue for p in points), 2)
    days_with_data = [p for p in points if p.appointments > 0]
    avg = round(total / days_in_month, 2) if days_in_month else 0
    best = max(days_with_data, key=lambda p: p.revenue) if days_with_data else None
    worst = min(days_with_data, key=lambda p: p.revenue) if days_with_data else None

    return RevenueResponse(
        daily=points,
        total=total,
        avg_per_day=avg,
        best_day=best.date if best else None,
        worst_day=worst.date if worst else None,
    )


@app.get("/api/analytics/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Тепловая карта загрузки: день недели × час."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.start_time < next_month,
            Appointment.tenant_id == tenant_id,
            Appointment.status.in_(["completed", "confirmed", "in_progress"]),
        )
    )
    appts = result.scalars().all()

    # Сетка 7×12 (дни недели × часы 9-20)
    cells_map: dict[tuple[int, int], dict] = {}
    for day in range(7):
        for hour in range(9, 21):
            cells_map[(day, hour)] = {"count": 0, "revenue": 0.0}

    for a in appts:
        day = a.start_time.weekday()  # 0=Mon
        hour = a.start_time.hour
        key = (day, hour)
        if key in cells_map:
            cells_map[key]["count"] += 1
            cells_map[key]["revenue"] += float(a.total_price or 0)

    cells = [
        HeatmapCell(day=d, hour=h, count=v["count"], revenue=round(v["revenue"], 2))
        for (d, h), v in sorted(cells_map.items())
    ]

    return HeatmapResponse(cells=cells)


@app.get("/api/analytics/funnel", response_model=FunnelResponse)
async def get_funnel(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Воронка продаж: конверсия по статусам."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if month_start.month == 12:
        next_month = month_start.replace(year=month_start.year + 1, month=1)
    else:
        next_month = month_start.replace(month=month_start.month + 1)

    result = await db.execute(
        select(Appointment).where(
            Appointment.start_time >= month_start,
            Appointment.start_time < next_month,
            Appointment.tenant_id == tenant_id,
        )
    )
    appts = result.scalars().all()

    total = len(appts)
    status_order = ["pending", "confirmed", "in_progress", "completed", "cancelled", "no_show"]
    counts = {s: 0 for s in status_order}
    for a in appts:
        s = a.status or "pending"
        if s in counts:
            counts[s] += 1

    funnel_stages = ["pending", "confirmed", "in_progress", "completed"]
    stage_labels = {
        "pending": "Создано",
        "confirmed": "Подтверждено",
        "in_progress": "В работе",
        "completed": "Выполнено",
    }
    stage_colors = {
        "pending": "#C8A977",
        "confirmed": "#4ECB71",
        "in_progress": "#AAB2BF",
        "completed": "#C8A977",
    }

    stages = []
    for i, s in enumerate(funnel_stages):
        val = counts[s]
        pct = round(val / total * 100, 1) if total else 0
        stages.append(FunnelStage(
            name=stage_labels[s],
            value=val,
            percent=pct,
            color=stage_colors[s],
        ))

    conversion = round(counts["completed"] / counts["pending"] * 100, 1) if counts["pending"] else 0

    return FunnelResponse(
        stages=stages,
        total=total,
        conversion_rate=conversion,
    )


# =============================================================================
# DISCOUNTS & LOYALTY
# =============================================================================

@app.get("/api/discounts")
async def get_discount_rules(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить все правила скидок тенанта."""
    stmt = (
        select(DiscountRule)
        .where(DiscountRule.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(DiscountRule.created_at.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[DiscountRuleOut](
        items=[DiscountRuleOut.model_validate(r) for r in items],
        total=total, skip=skip, limit=limit,
    )


@app.post("/api/discounts", response_model=DiscountRuleOut)
async def create_discount_rule(
    request: DiscountRuleCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новое правило скидки."""
    start_date = None
    if request.start_date:
        try:
            start_date = datetime.fromisoformat(request.start_date)
        except ValueError:
            pass
    end_date = None
    if request.end_date:
        try:
            end_date = datetime.fromisoformat(request.end_date)
        except ValueError:
            pass

    rule = DiscountRule(
        name=request.name,
        type=request.type,
        conditions=request.conditions or {},
        discount_percent=request.discount_percent,
        start_date=start_date,
        end_date=end_date,
        is_active=request.is_active if request.is_active is not None else True,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return DiscountRuleOut.model_validate(rule)


@app.put("/api/discounts/{rule_id}", response_model=DiscountRuleOut)
async def update_discount_rule(
    rule_id: int,
    request: DiscountRuleUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить правило скидки."""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id,
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило скидки не найдено")

    update_data = request.model_dump(exclude_unset=True)
    if "start_date" in update_data:
        if update_data["start_date"]:
            try:
                update_data["start_date"] = datetime.fromisoformat(update_data["start_date"])
            except ValueError:
                del update_data["start_date"]
    if "end_date" in update_data:
        if update_data["end_date"]:
            try:
                update_data["end_date"] = datetime.fromisoformat(update_data["end_date"])
            except ValueError:
                del update_data["end_date"]

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    await db.refresh(rule)
    return DiscountRuleOut.model_validate(rule)


@app.delete("/api/discounts/{rule_id}")
async def delete_discount_rule(
    rule_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить правило скидки."""
    result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.id == rule_id,
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    rule = result.scalar_one_or_none()
    if not rule:
        raise HTTPException(status_code=404, detail="Правило скидки не найдено")

    name = rule.name
    await db.delete(rule)
    await db.commit()
    return {"message": f"Правило скидки «{name}» удалено"}


# ========== LOYALTY POINTS ==========

@app.get("/api/loyalty/points")
async def get_loyalty_points(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить баланс баллов всех клиентов."""
    tenant_id = UUID(current_user["tenant_id"])

    # Все клиенты тенанта (с пагинацией)
    clients_stmt = (
        select(User)
        .where(User.role == "client", User.tenant_id == tenant_id)
        .order_by(User.full_name)
    )
    # Count total clients first
    count_stmt = select(func.count()).select_from(clients_stmt.subquery())
    total = (await db.execute(count_stmt)).scalar() or 0

    clients_result = await db.execute(clients_stmt.offset(skip).limit(limit))
    clients = clients_result.scalars().all()

    # Их баллы
    client_ids = [c.id for c in clients]
    if not client_ids:
        return []

    points_result = await db.execute(
        select(LoyaltyPoints).where(LoyaltyPoints.client_id.in_(client_ids))
    )
    points_map: dict[int, LoyaltyPoints] = {}
    for p in points_result.scalars().all():
        points_map[p.client_id] = p

    result = []
    for c in clients:
        lp = points_map.get(c.id)
        result.append(LoyaltyPointsSummary(
            client_id=c.id,
            full_name=c.full_name,
            phone=c.phone,
            balance=lp.balance if lp else 0,
            total_earned=lp.total_earned if lp else 0,
            total_spent=lp.total_spent if lp else 0,
        ))

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


# ========== AUTO-APPLY DISCOUNT ON APPOINTMENT CREATE ==========

async def _auto_apply_discount(appointment_id: int, db: AsyncSession):
    """Автоматически применить скидку к записи (вызывается после создания)."""
    # Загружаем запись со связями
    result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service))
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return

    now = datetime.now(timezone.utc)
    tenant_id = appointment.tenant_id

    # Загружаем активные правила скидок
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
        )
    )
    rules = rules_result.scalars().all()

    best_discount = 0
    best_rule = None

    for rule in rules:
        conditions = rule.conditions or {}

        # Проверка дат — сравниваем с временем ЗАПИСИ, а не с now
        # (иначе запись на будущую дату не получит скидку, если правило начнётся позже today)
        appt_time = appointment.start_time or now
        if rule.start_date and rule.start_date > appt_time:
            continue
        if rule.end_date and rule.end_date < appt_time:
            continue

        if rule.type == "happy_hours":
            # Скидка в часы низкой загрузки
            utc_offset = conditions.get("utc_offset", 0)
            raw_hour = appointment.start_time.hour if appointment.start_time else now.hour
            hour = (raw_hour + utc_offset) % 24
            happy_start = conditions.get("hour_start", 10)
            happy_end = conditions.get("hour_end", 14)
            min_discount = conditions.get("min_discount", 0)

            # Отладка
            weekday = appointment.start_time.weekday() if appointment.start_time else -1
            print(f"[DEBUG] happy_hours: start_time={appointment.start_time}, hour={hour}, weekday={weekday}")
            print(f"[DEBUG] rule: {happy_start} <= {hour} <= {happy_end} = {happy_start <= hour <= happy_end}")
            print(f"[DEBUG] rule.start_date={rule.start_date}, appt_time={appt_time}, date_ok={not (rule.start_date and rule.start_date > appt_time)}")
            print(f"[DEBUG] min_discount={min_discount}, discount_percent={rule.discount_percent}")

            if min_discount and rule.discount_percent < min_discount:
                continue
            # Проверка: happy hours
            if happy_start <= hour <= happy_end and appointment.start_time and appointment.start_time.weekday() < 5:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "frequency":
            # Скидка за частоту визитов
            min_visits = conditions.get("min_visits", 3)
            # Считаем завершённые записи клиента
            count_result = await db.execute(
                select(func.count(Appointment.id)).where(
                    Appointment.client_id == appointment.client_id,
                    Appointment.tenant_id == tenant_id,
                    Appointment.status == "completed",
                )
            )
            completed_count = count_result.scalar() or 0
            if completed_count >= min_visits:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "win_back":
            # Скидка для возврата ушедших клиентов
            max_recency_days = conditions.get("max_recency_days", 60)
            # Ищем последнюю запись клиента
            last_result = await db.execute(
                select(Appointment.start_time)
                .where(
                    Appointment.client_id == appointment.client_id,
                    Appointment.tenant_id == tenant_id,
                    Appointment.status == "completed",
                )
                .order_by(Appointment.start_time.desc())
                .limit(1)
            )
            last_visit = last_result.scalar()
            if last_visit:
                days_since = (now - last_visit).days
                if days_since >= max_recency_days:
                    if rule.discount_percent > best_discount:
                        best_discount = rule.discount_percent
                        best_rule = rule

        elif rule.type == "cashback":
            # Кэшбек начисляется при завершении, не при создании — пропускаем
            continue

    if best_rule and best_discount > 0:
        original_price = float(appointment.total_price)
        discount_amount = round(original_price * best_discount / 100, 2)
        appointment.discount_applied = discount_amount
        appointment.total_price = original_price - discount_amount

        cd = ClientDiscount(
            tenant_id=tenant_id,
            client_id=appointment.client_id,
            discount_rule_id=best_rule.id,
            appointment_id=appointment.id,
            applied_percent=best_discount,
            applied_amount=discount_amount,
            is_used=True,
        )
        db.add(cd)
        await db.commit()


# ========== AWARD LOYALTY POINTS ON COMPLETION ==========

async def _award_loyalty_points(appointment_id: int, db: AsyncSession):
    """Начислить баллы лояльности за завершённую запись."""
    result = await db.execute(
        select(Appointment).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        return

    # Начисляем 1 балл за каждые 100 рублей
    points_to_award = max(1, int(float(appointment.total_price) / 100))

    # Получаем или создаём запись баллов
    points_result = await db.execute(
        select(LoyaltyPoints).where(
            LoyaltyPoints.client_id == appointment.client_id,
            LoyaltyPoints.tenant_id == appointment.tenant_id,
        )
    )
    lp = points_result.scalar_one_or_none()

    if lp:
        lp.balance += points_to_award
        lp.total_earned += points_to_award
    else:
        lp = LoyaltyPoints(
            client_id=appointment.client_id,
            tenant_id=appointment.tenant_id,
            balance=points_to_award,
            total_earned=points_to_award,
            total_spent=0,
        )
        db.add(lp)

    await db.commit()


# ========== CARS ==========

@app.get("/api/cars")
async def get_cars(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить все машины текущего пользователя"""
    stmt = (
        select(Car)
        .where(
            Car.client_id == current_user["id"],
            Car.tenant_id == UUID(current_user["tenant_id"]),
        )
        .order_by(Car.created_at.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return PaginatedResponse[CarOut](
        items=[CarOut.model_validate(c) for c in items],
        total=total, skip=skip, limit=limit,
    )

@app.post("/api/cars", response_model=CarOut)
async def create_car(
    car_data: CarCreate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую машину для текущего пользователя"""
    new_car = Car(
        client_id=current_user["id"],
        make=car_data.make,
        model=car_data.model,
        year=car_data.year,
        license_plate=car_data.license_plate,
        color=car_data.color,
        notes=car_data.notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(new_car)
    await db.commit()
    await db.refresh(new_car)
    return CarOut.model_validate(new_car)

@app.delete("/api/cars/{car_id}")
async def delete_car(
    car_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить машину (только свою)"""
    result = await db.execute(
        select(Car).where(
            Car.id == car_id,
            Car.client_id == current_user["id"],
            Car.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    
    await db.delete(car)
    await db.commit()
    return {"message": "Машина удалена"}


# =============================================================================
# PHOTO UPLOADS
# =============================================================================

MAX_PHOTOS_PER_ENTITY = 20


async def _get_photo_or_404(photo_id: int, db: AsyncSession, tenant_id: UUID) -> Photo:
    result = await db.execute(
        select(Photo).where(Photo.id == photo_id, Photo.tenant_id == tenant_id)
    )
    photo = result.scalar_one_or_none()
    if not photo:
        raise HTTPException(status_code=404, detail="Фото не найдено")
    return photo


async def _save_uploaded_photo(
    db: AsyncSession,
    file: UploadFile,
    tenant_id: UUID,
    entity_type: str,
    entity_field: str,
    entity_id: int | None,
    uploaded_by_id: int,
    title: str | None = None,
) -> PhotoCreateResponse:
    """Validate, save and create Photo record."""
    contents = await file.read()
    mime = validate_image(contents, file.filename or "image.jpg")
    filename = generate_filename(file.filename or "image.jpg")
    subdir = f"{entity_type}s/{entity_id or 'unknown'}"
    url, thumb_url = save_file_local(contents, subdir, filename)

    photo = Photo(
        tenant_id=tenant_id,
        entity_type=entity_type,
        url=url,
        thumbnail_url=thumb_url,
        title=title or file.filename,
        file_size=len(contents),
        mime_type=mime,
        uploaded_by_id=uploaded_by_id,
        **{entity_field: entity_id},
    )
    db.add(photo)
    await db.commit()
    await db.refresh(photo)

    return PhotoCreateResponse(
        id=photo.id,
        url=photo.url,
        thumbnail_url=photo.thumbnail_url,
        title=photo.title,
    )


@app.post("/api/upload/car/{car_id}", response_model=PhotoCreateResponse)
async def upload_car_photo(
    car_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото автомобиля."""
    result = await db.execute(
        select(Car).where(Car.id == car_id, Car.client_id == current_user["id"],
                          Car.tenant_id == UUID(current_user["tenant_id"]))
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Автомобиль не найден")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "car", "car_id", car_id,
        current_user["id"],
    )


@app.post("/api/upload/appointment/{appointment_id}", response_model=PhotoCreateResponse)
async def upload_appointment_photo(
    appointment_id: int,
    file: UploadFile = File(...),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото выполненной работы (до/после)."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appt.client_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "appointment", "appointment_id", appointment_id,
        current_user["id"],
    )


@app.post("/api/upload/portfolio", response_model=PhotoCreateResponse)
async def upload_portfolio_photo(
    file: UploadFile = File(...),
    title: str | None = Query(None),
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото в портфолио мастера."""
    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "portfolio", "uploaded_by_id", current_user["id"],
        current_user["id"], title=title,
    )


@app.get("/api/photos/{entity_type}/{entity_id}", response_model=list[PhotoOut])
async def get_photos(
    entity_type: str,
    entity_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список фото для сущности."""
    entity_field = {
        "car": "car_id",
        "appointment": "appointment_id",
        "portfolio": "uploaded_by_id",
    }.get(entity_type, "car_id")

    filter_col = getattr(Photo, entity_field, None)
    if filter_col is None:
        raise HTTPException(status_code=400, detail="Некорректный тип сущности")

    result = await db.execute(
        select(Photo)
        .where(
            filter_col == entity_id,
            Photo.tenant_id == UUID(current_user["tenant_id"]),
            Photo.entity_type == entity_type,
        )
        .order_by(Photo.sort_order, Photo.created_at.desc())
    )
    return [PhotoOut.model_validate(p) for p in result.scalars().all()]


@app.delete("/api/photos/{photo_id}")
async def delete_photo(
    photo_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Удалить фото."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    delete_file_local(photo.url)
    if photo.thumbnail_url:
        delete_file_local(photo.thumbnail_url)

    await db.delete(photo)
    await db.commit()
    return {"message": "Фото удалено", "photo_id": photo_id}


@app.put("/api/photos/{photo_id}/primary")
async def set_primary_photo(
    photo_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Сделать фото основным."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    photo.is_primary = True
    await db.commit()
    return {"message": "Фото отмечено как основное", "photo_id": photo_id}


@app.put("/api/photos/{photo_id}/order")
async def update_photo_order(
    photo_id: int,
    request: PhotoOrderUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Изменить порядок фото."""
    photo = await _get_photo_or_404(photo_id, db, UUID(current_user["tenant_id"]))

    if photo.uploaded_by_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Доступ запрещён")

    photo.sort_order = request.sort_order
    await db.commit()
    return {"message": "Порядок фото обновлён", "photo_id": photo_id}

@app.get("/api/notifications", response_model=PaginatedResponse[NotificationOut])
async def get_notifications(
    unread_only: bool = Query(False),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список уведомлений."""
    from app.core.notification_service import get_notifications as _get_notifs
    items, total = await _get_notifs(
        db, current_user["id"], UUID(current_user["tenant_id"]),
        skip=skip, limit=limit, unread_only=unread_only,
    )
    return PaginatedResponse[NotificationOut](
        items=[NotificationOut.model_validate(n) for n in items],
        total=total, skip=skip, limit=limit,
    )


@app.get("/api/notifications/unread-count", response_model=UnreadCountOut)
async def get_unread_count(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить количество непрочитанных уведомлений."""
    from app.core.notification_service import get_unread_count as _count
    count = await _count(db, current_user["id"], UUID(current_user["tenant_id"]))
    return UnreadCountOut(count=count)


@app.put("/api/notifications/{notification_id}/read")
async def mark_notification_read(
    notification_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить уведомление как прочитанное."""
    from app.core.notification_service import mark_as_read
    ok = await mark_as_read(db, notification_id, current_user["id"])
    if not ok:
        raise HTTPException(status_code=404, detail="Уведомление не найдено")
    return {"message": "Уведомление отмечено как прочитанное"}


@app.put("/api/notifications/read-all")
async def mark_all_notifications_read(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отметить все уведомления как прочитанные."""
    from app.core.notification_service import mark_all_as_read
    count = await mark_all_as_read(db, current_user["id"], UUID(current_user["tenant_id"]))
    return {"message": f"Отмечено {count} уведомлений как прочитанные", "count": count}


@app.get("/api/notifications/settings", response_model=NotificationSettingsOut)
async def get_notification_settings(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить настройки уведомлений."""
    from app.core.notification_service import get_settings
    settings = await get_settings(db, current_user["id"])
    if not settings:
        return NotificationSettingsOut()
    return NotificationSettingsOut.model_validate(settings)


@app.put("/api/notifications/settings", response_model=NotificationSettingsOut)
async def update_notification_settings(
    request: NotificationSettingsUpdate,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Обновить настройки уведомлений."""
    from app.core.notification_service import upsert_settings
    data = request.model_dump(exclude_unset=True)
    settings = await upsert_settings(db, current_user["id"], **data)
    return NotificationSettingsOut.model_validate(settings)


@app.post("/api/telegram/connect")
async def connect_telegram(
    request: TelegramConnectRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Подключить Telegram по коду."""
    from app.core.notification_service import upsert_settings
    # В реальном приложении здесь проверка кода из Telegram Bot
    settings = await upsert_settings(
        db, current_user["id"],
        telegram_enabled=True,
        telegram_chat_id=f"user_{current_user['id']}",
        telegram_code=request.code,
    )
    return {"message": "Telegram подключён", "chat_id": settings.telegram_chat_id}


@app.post("/api/telegram/disconnect")
async def disconnect_telegram(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Отключить Telegram."""
    from app.core.notification_service import upsert_settings
    await upsert_settings(
        db, current_user["id"],
        telegram_enabled=False,
        telegram_chat_id=None,
    )
    return {"message": "Telegram отключён"}


@app.post("/api/telegram/webhook")
async def telegram_webhook(
    data: dict,
):
    """Webhook для Telegram бота."""
    from app.core.telegram_service import handle_telegram_webhook
    return await handle_telegram_webhook(data)


# =============================================================================
# CALENDAR
# =============================================================================

@app.get("/api/calendar/{master_id}", response_model=CalendarResponse)
async def get_master_calendar(
    master_id: int,
    start_date: str = Query(..., description="YYYY-MM-DD"),
    end_date: str = Query(..., description="YYYY-MM-DD"),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить календарь мастера на диапазон дат."""
    tenant_id = UUID(current_user["tenant_id"])

    # Получаем мастера
    result = await db.execute(select(User).where(User.id == master_id, User.tenant_id == tenant_id))
    master = result.scalar_one_or_none()
    if not master:
        raise HTTPException(status_code=404, detail="Мастер не найден")

    # Рабочие часы
    wh_result = await db.execute(
        select(WorkingHours).where(
            WorkingHours.master_id == master_id,
            WorkingHours.tenant_id == tenant_id,
        ).order_by(WorkingHours.day_of_week)
    )
    working_hours = wh_result.scalars().all()

    # Записи мастера на диапазон
    from datetime import date as date_type
    s_date = date_type.fromisoformat(start_date)
    e_date = date_type.fromisoformat(end_date)
    from datetime import datetime, time
    s_dt = datetime.combine(s_date, time.min, tzinfo=timezone.utc)
    e_dt = datetime.combine(e_date, time.max, tzinfo=timezone.utc)

    appt_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.client), selectinload(Appointment.service), selectinload(Appointment.car))
        .where(
            Appointment.master_id == master_id,
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= s_dt,
            Appointment.start_time <= e_dt,
        )
        .order_by(Appointment.start_time)
    )
    appts = appt_result.scalars().all()

    # Группировка по дням
    from collections import defaultdict
    days_map: dict[str, list] = defaultdict(list)
    for a in appts:
        day_key = a.start_time.strftime("%Y-%m-%d")
        days_map[day_key].append(CalendarAppointment(
            id=a.id,
            client_id=a.client_id,
            master_id=a.master_id,
            car_id=a.car_id,
            service_id=a.service_id,
            start_time=a.start_time.isoformat(),
            end_time=a.end_time.isoformat(),
            status=a.status,
            total_price=float(a.total_price or 0),
            service_name=a.service.name if a.service else None,
            client_name=a.client.full_name if a.client else None,
            car_info=f"{a.car.make} {a.car.model}" if a.car else None,
        ))

    days = []
    current = s_date
    while current <= e_date:
        key = current.isoformat()
        days.append(CalendarDay(
            date=key,
            day_of_week=current.weekday(),
            appointments=days_map.get(key, []),
        ))
        from datetime import timedelta
        current += timedelta(days=1)

    return CalendarResponse(
        master_id=master_id,
        master_name=master.full_name,
        days=days,
        working_hours=[WorkingHoursOut.model_validate(w) for w in working_hours],
    )


@app.put("/api/appointments/{appointment_id}/move")
async def move_appointment(
    appointment_id: int,
    start_time: str = Query(..., description="Новое время ISO 8601"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Перенести запись (Drag & Drop)."""
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == appointment_id,
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    new_start = datetime.fromisoformat(start_time.replace("Z", "+00:00"))
    if new_start.tzinfo is None:
        new_start = new_start.replace(tzinfo=timezone.utc)

    old_start_str = appt.start_time.isoformat() if appt.start_time else ""
    duration = (appt.end_time - appt.start_time).total_seconds() / 60
    appt.start_time = new_start
    appt.end_time = new_start + timedelta(minutes=duration)
    await db.commit()


    # History: log move
    from app.services.history_service import log_move as _log_move
    from datetime import datetime as _dt
    await _log_move(db, appointment_id, old_start_str, new_start.isoformat(), current_user["id"])

    return {"message": "Запись перенесена", "appointment_id": appointment_id}



@app.get("/api/masters/working-hours", response_model=list[WorkingHoursOut])
async def get_working_hours(
    master_id: int | None = Query(None),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить рабочие часы мастеров."""
    tenant_id = UUID(current_user["tenant_id"])
    stmt = select(WorkingHours).where(WorkingHours.tenant_id == tenant_id)
    if master_id:
        stmt = stmt.where(WorkingHours.master_id == master_id)
    stmt = stmt.order_by(WorkingHours.master_id, WorkingHours.day_of_week)

    result = await db.execute(stmt)
    return [WorkingHoursOut.model_validate(w) for w in result.scalars().all()]


@app.put("/api/masters/working-hours/{master_id}", response_model=list[WorkingHoursOut])
async def update_working_hours(
    master_id: int,
    hours: list[WorkingHoursUpdate],
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить рабочие часы мастера."""
    tenant_id = UUID(current_user["tenant_id"])

    # Удаляем старые
    await db.execute(
        WorkingHours.__table__.delete().where(
            WorkingHours.master_id == master_id,
            WorkingHours.tenant_id == tenant_id,
        )
    )

    # Создаём новые
    for h in hours:
        wh = WorkingHours(
            master_id=master_id,
            tenant_id=tenant_id,
            day_of_week=h.day_of_week,
            start_time=h.start_time,
            end_time=h.end_time,
            is_working_day=h.is_working_day,
        )
        db.add(wh)

    await db.commit()

    result = await db.execute(
        select(WorkingHours).where(
            WorkingHours.master_id == master_id,
            WorkingHours.tenant_id == tenant_id,
        ).order_by(WorkingHours.day_of_week)
    )
    return [WorkingHoursOut.model_validate(w) for w in result.scalars().all()]


# =============================================================================
# APPOINTMENT HISTORY
# =============================================================================

@app.get("/api/appointments/{appointment_id}/history")
async def get_appointment_history(
    appointment_id: int,
    change_type: str | None = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить историю изменений записи."""
    from app.services.history_service import get_history

    items, total = await get_history(db, appointment_id, skip=skip, limit=limit, change_type=change_type)

    # Serialize with user name
    result = []
    for item in items:
        entry = HistoryEntryOut(
            id=item.id,
            appointment_id=item.appointment_id,
            change_type=item.change_type,
            field_name=item.field_name,
            old_value=item.old_value,
            new_value=item.new_value,
            created_at=item.created_at,
        )
        if item.changed_by:
            entry.changed_by = {
                "id": item.changed_by.id,
                "full_name": item.changed_by.full_name,
            }
        result.append(entry)

    return {
        "items": result,
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.get("/api/appointments/{appointment_id}/history/{history_id}")
async def get_history_detail(
    appointment_id: int,
    history_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить детали конкретного изменения."""
    from sqlalchemy.orm import selectinload
    result = await db.execute(
        select(AppointmentHistory, Payment)
        .options(selectinload(AppointmentHistory, Payment.changed_by))
        .where(
            AppointmentHistory, Payment.id == history_id,
            AppointmentHistory, Payment.appointment_id == appointment_id,
        )
    )
    entry = result.scalar_one_or_none()
    if not entry:
        raise HTTPException(status_code=404, detail="Запись истории не найдена")

    out = HistoryEntryOut(
        id=entry.id,
        appointment_id=entry.appointment_id,
        change_type=entry.change_type,
        field_name=entry.field_name,
        old_value=entry.old_value,
        new_value=entry.new_value,
        created_at=entry.created_at,
    )
    if entry.changed_by:
        out.changed_by = {"id": entry.changed_by.id, "full_name": entry.changed_by.full_name}
    return out


# =============================================================================
# LOYALTY TIERS
# =============================================================================

@app.get("/api/loyalty/tiers", response_model=list[LoyaltyTierConfigOut])
async def get_loyalty_tiers(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить конфигурацию уровней лояльности."""
    result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(LoyaltyTierConfig.min_total_spent.asc())
    )
    return [LoyaltyTierConfigOut.model_validate(t) for t in result.scalars().all()]


@app.put("/api/loyalty/tiers", response_model=list[LoyaltyTierConfigOut])
async def update_loyalty_tiers(
    tiers: list[LoyaltyTierConfigUpdate],
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить конфигурацию уровней лояльности."""
    tenant_id = UUID(current_user["tenant_id"])

    # Delete old config
    await db.execute(
        LoyaltyTierConfig.__table__.delete().where(
            LoyaltyTierConfig.tenant_id == tenant_id
        )
    )

    # Insert new
    for t in tiers:
        config = LoyaltyTierConfig(
            tenant_id=tenant_id,
            tier=t.tier,
            min_total_spent=t.min_total_spent,
            min_visits=t.min_visits,
            discount_percent=t.discount_percent,
            bonus_multiplier=t.bonus_multiplier,
            color=t.color,
        )
        db.add(config)

    await db.commit()

    result = await db.execute(
        select(LoyaltyTierConfig)
        .where(LoyaltyTierConfig.tenant_id == tenant_id)
        .order_by(LoyaltyTierConfig.min_total_spent.asc())
    )
    return [LoyaltyTierConfigOut.model_validate(t) for t in result.scalars().all()]


@app.get("/api/loyalty/my-tier", response_model=ClientTierOut)
async def get_my_tier(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить свой уровень лояльности."""
    from app.services.loyalty_service import get_client_tier_info
    from app.models import User

    await recalculate_tier_if_needed(db, current_user["id"], UUID(current_user["tenant_id"]))

    info = await get_client_tier_info(db, current_user["id"], UUID(current_user["tenant_id"]))

    user_result = await db.execute(
        select(User).where(User.id == current_user["id"])
    )
    user = user_result.scalar_one()

    return ClientTierOut(
        client_id=current_user["id"],
        full_name=user.full_name,
        phone=user.phone,
        **info,
    )


async def recalculate_tier_if_needed(db: AsyncSession, client_id: int, tenant_id: UUID):
    """Пересчитать уровень клиента."""
    from app.services.loyalty_service import recalculate_tier
    await recalculate_tier(db, client_id, tenant_id)


# =============================================================================
# SERVICE ANALYTICS
# =============================================================================

@app.get("/api/analytics/services", response_model=ServiceAnalyticsResponse)
async def get_service_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    months: int = Query(6, ge=1, le=24),
):
    """Аналитика по услугам: тренды, сравнение, топ-5, прогноз."""
    from collections import defaultdict
    from datetime import datetime, timezone, timedelta
    import math

    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем периоды
    current_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    previous_start = (current_start - timedelta(days=1)).replace(day=1)
    prev_prev_start = (previous_start - timedelta(days=1)).replace(day=1)

    # Все услуги тенанта
    services_result = await db.execute(
        select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
    )
    services = {s.id: s for s in services_result.scalars().all()}

    # Все завершённые записи за период
    start_date = now - timedelta(days=months * 31)
    appts_result = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service))
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= start_date,
        )
        .order_by(Appointment.start_time)
    )
    appts = appts_result.scalars().all()

    # --- 1. Тренды по месяцам ---
    monthly_data: dict[int, dict[str, dict]] = {}
    for a in appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in monthly_data:
            monthly_data[sid] = {}
        month_key = a.start_time.strftime("%Y-%m")
        if month_key not in monthly_data[sid]:
            monthly_data[sid][month_key] = {"revenue": 0.0, "count": 0}
        monthly_data[sid][month_key]["revenue"] += float(a.total_price or 0)
        monthly_data[sid][month_key]["count"] += 1

    trends = []
    for sid, months_data in monthly_data.items():
        srv = services.get(sid)
        monthly = [
            ServiceTrendPoint(month=m, revenue=round(d["revenue"], 2), count=d["count"])
            for m, d in sorted(months_data.items())
        ]
        trends.append(ServiceTrend(
            service_id=sid,
            service_name=srv.name if srv else f"Услуга #{sid}",
            category=srv.category if srv else None,
            monthly=monthly,
        ))

    # --- 2. Сравнение периодов ---
    comparison = []
    for sid in monthly_data:
        srv = services.get(sid)
        prev_month = previous_start.strftime("%Y-%m")
        prev_prev = prev_prev_start.strftime("%Y-%m")

        cur = monthly_data[sid].get(prev_month, {"revenue": 0.0, "count": 0})
        prev = monthly_data[sid].get(prev_prev, {"revenue": 0.0, "count": 0})

        change = 0.0
        if prev["revenue"] > 0:
            change = round((cur["revenue"] - prev["revenue"]) / prev["revenue"] * 100, 1)

        comparison.append(ServiceComparison(
            service_id=sid,
            service_name=srv.name if srv else f"Услуга #{sid}",
            current_revenue=round(cur["revenue"], 2),
            previous_revenue=round(prev["revenue"], 2),
            change_percent=change,
            current_count=cur["count"],
            previous_count=prev["count"],
        ))

    # --- 3. Топ-5 услуг ---
    service_totals: dict[int, dict] = {}
    for a in appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_totals:
            srv = services.get(sid)
            service_totals[sid] = {
                "name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "revenue": 0.0, "count": 0,
            }
        service_totals[sid]["revenue"] += float(a.total_price or 0)
        service_totals[sid]["count"] += 1

    sorted_services = sorted(service_totals.values(), key=lambda x: x["revenue"], reverse=True)
    top_services = [
        TopService(
            service_id=list(service_totals.keys())[list(service_totals.values()).index(s)],
            service_name=s["name"],
            category=s["category"],
            total_revenue=round(s["revenue"], 2),
            total_count=s["count"],
            avg_price=round(s["revenue"] / s["count"], 2) if s["count"] else 0,
        )
        for s in sorted_services[:5]
    ]

    # --- 4. Прогноз (простое скользящее среднее) ---
    forecast = []
    if appts:
        # Собираем последние 3 месяца
        last_months = sorted(set(
            a.start_time.strftime("%Y-%m") for a in appts
        ))[-3:]
        if last_months:
            total_rev = sum(
                monthly_data[a.service_id].get(m, {"revenue": 0})["revenue"]
                for sid in monthly_data for m in [last_months[-1]]
                if m in monthly_data[sid]
                for a in appts if a.service_id == sid
            )

            avg_revenue = total_rev / len(last_months) if last_months else 0

            pass

            # Простой прогноз на 3 месяца вперёд
            last_month = datetime.strptime(last_months[-1] + "-01", "%Y-%m-%d")
            for i in range(1, 4):
                next_m = (last_month + timedelta(days=32 * i)).strftime("%Y-%m")
                forecast.append(ForecastPoint(
                    month=next_m,
                    forecast=round(avg_revenue, 2),
                    lower_bound=round(avg_revenue * 0.8, 2),
                    upper_bound=round(avg_revenue * 1.2, 2),
                ))

    return ServiceAnalyticsResponse(
        trends=trends,
        comparison=comparison,
        top_services=top_services,
        forecast=forecast,
    )


# =============================================================================
# REPORTS & EXPORT
# =============================================================================

@app.get("/api/reports/revenue", response_model=RevenueReportResponse)
async def get_revenue_report(
    period: str = Query("month", pattern="^(day|week|month|year)$"),
    start_date: str = Query(None, description="YYYY-MM-DD"),
    end_date: str = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Отчёт по выручке: сводка, сравнение, детализация."""
    from datetime import datetime, date, time, timedelta

    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Период
    if start_date and end_date:
        s_date = datetime.strptime(start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
        e_date = datetime.strptime(end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc) + timedelta(days=1)
    else:
        if period == "day":
            s_date = now.replace(hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date + timedelta(days=1)
        elif period == "week":
            s_date = (now - timedelta(days=now.weekday())).replace(hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date + timedelta(days=7)
        elif period == "month":
            s_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
            e_date = (s_date + timedelta(days=32)).replace(day=1)
        else:  # year
            s_date = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
            e_date = s_date.replace(year=s_date.year + 1)

    # Предыдущий период
    prev_duration = (e_date - s_date).total_seconds()
    p_start = s_date - timedelta(seconds=prev_duration)
    p_end = s_date

    # Записи за текущий период
    appts_current = await db.execute(
        select(Appointment)
        .options(selectinload(Appointment.service), selectinload(Appointment.master), selectinload(Appointment.client))
        .where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= s_date,
            Appointment.start_time < e_date,
        )
        .order_by(Appointment.start_time)
    )
    current_appts = appts_current.scalars().all()

    # Записи за предыдущий период
    appts_previous = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
            Appointment.start_time >= p_start,
            Appointment.start_time < p_end,
        )
    )
    prev_appts = appts_previous.scalars().all()

    current_revenue = sum(float(a.total_price or 0) for a in current_appts)
    prev_revenue = sum(float(a.total_price or 0) for a in prev_appts)
    current_count = len(current_appts)
    prev_count = len(prev_appts)

    change_percent = 0.0
    if prev_revenue > 0:
        change_percent = round((current_revenue - prev_revenue) / prev_revenue * 100, 1)

    # --- По услугам ---
    service_map: dict[int, dict] = {}
    for a in current_appts:
        if not a.service_id:
            continue
        sid = a.service_id
        if sid not in service_map:
            srv = a.service
            service_map[sid] = {
                "name": srv.name if srv else f"Услуга #{sid}",
                "category": srv.category if srv else None,
                "revenue": 0.0, "count": 0,
            }
        service_map[sid]["revenue"] += float(a.total_price or 0)
        service_map[sid]["count"] += 1

    by_service = [
        ServiceRevenueSummary(
            service_id=sid,
            service_name=d["name"],
            category=d["category"],
            total_revenue=round(d["revenue"], 2),
            total_count=d["count"],
            avg_price=round(d["revenue"] / d["count"], 2) if d["count"] else 0,
        )
        for sid, d in sorted(service_map.items(), key=lambda x: x[1]["revenue"], reverse=True)
    ]

    # --- По мастерам ---
    master_map: dict[int, dict] = {}
    for a in current_appts:
        mid = a.master_id or 0
        if mid not in master_map:
            name = "Без мастера"
            if a.master:
                name = a.master.full_name
            master_map[mid] = {"name": name, "revenue": 0.0, "count": 0}
        master_map[mid]["revenue"] += float(a.total_price or 0)
        master_map[mid]["count"] += 1

    by_master = [
        MasterRevenueSummary(
            master_id=mid, master_name=d["name"],
            total_revenue=round(d["revenue"], 2),
            completed_count=d["count"],
            avg_revenue=round(d["revenue"] / d["count"], 2) if d["count"] else 0,
        )
        for mid, d in sorted(master_map.items(), key=lambda x: x[1]["revenue"], reverse=True)
    ]

    # --- Детализация ---
    details = []
    for a in current_appts:
        material = float(a.service.material_cost or 0) if a.service else 0
        details.append(RevenueDetail(
            date=a.start_time.strftime("%Y-%m-%d %H:%M"),
            service_name=a.service.name if a.service else "—",
            master_name=a.master.full_name if a.master else "—",
            client_name=a.client.full_name if a.client else "—",
            total_price=float(a.total_price or 0),
            material_cost=material,
            profit=float(a.total_price or 0) - material,
        ))

    total_profit = sum(d.profit for d in details)

    return RevenueReportResponse(
        total_revenue=round(current_revenue, 2),
        total_profit=round(total_profit, 2),
        period_comparison=[PeriodComparison(
            period=period,
            current_revenue=round(current_revenue, 2),
            previous_revenue=round(prev_revenue, 2),
            current_count=current_count,
            previous_count=prev_count,
            change_percent=change_percent,
        )],
        by_service=by_service,
        by_master=by_master,
        details=details,
    )


@app.get("/api/reports/revenue/csv")
async def export_revenue_csv(
    period: str = Query("month"),
    start_date: str = Query(None),
    end_date: str = Query(None),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Экспорт отчёта по выручке в CSV."""
    from fastapi.responses import StreamingResponse
    import io

    # Получаем данные через тот же эндпоинт
    report = await get_revenue_report(
        period=period, start_date=start_date, end_date=end_date,
        current_user=current_user, db=db,
    )

    output = io.StringIO()
    output.write("sep=,\n")
    output.write("Дата,Услуга,Мастер,Клиент,Сумма,Материалы,Прибыль\n")

    for d in report.details:
        output.write(
            f"{d.date},{d.service_name},{d.master_name},{d.client_name},"
            f"{d.total_price},{d.material_cost},{d.profit}\n"
        )

    output.seek(0)
    return StreamingResponse(
        iter([output.getvalue()]),
        media_type="text/csv",
        headers={"Content-Disposition": f"attachment; filename=revenue_report_{period}.csv"},
    )


# =============================================================================
# PAYMENTS
# =============================================================================

@app.post("/api/payments/create", response_model=PaymentOut)
async def create_payment(
    request: PaymentCreateRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Создать платёж для записи."""
    # Проверяем запись
    result = await db.execute(
        select(Appointment).where(
            Appointment.id == request.appointment_id,
            Appointment.client_id == current_user["id"],
            Appointment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    appt = result.scalar_one_or_none()
    if not appt:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    # Проверяем, нет ли уже оплаты
    existing = await db.execute(
        select(Payment).where(
            Payment.appointment_id == request.appointment_id,
            Payment.status.in_(["pending", "succeeded"]),
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail="Платёж уже создан")

    payment = Payment(
        tenant_id=UUID(current_user["tenant_id"]),
        appointment_id=request.appointment_id,
        amount=appt.total_price,
        payment_method=request.payment_method or "card",
        status="pending",
        payment_id=f"pay_{appt.id}_{int(datetime.now().timestamp())}",
    )
    db.add(payment)
    await db.commit()
    await db.refresh(payment)
    return PaymentOut.model_validate(payment)


@app.post("/api/payments/webhook")
async def payment_webhook(
    data: PaymentWebhookRequest,
    db: AsyncSession = Depends(get_db),
):
    """Webhook от платёжной системы."""
    result = await db.execute(
        select(Payment).where(Payment.payment_id == data.payment_id)
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    payment.status = data.status
    await db.commit()
    return {"message": "Статус платежа обновлён"}


@app.get("/api/payments/{payment_id}/status", response_model=PaymentOut)
async def get_payment_status(
    payment_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Проверить статус платежа."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")
    return PaymentOut.model_validate(payment)


@app.post("/api/payments/{payment_id}/refund")
async def refund_payment(
    payment_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Возврат платежа."""
    result = await db.execute(
        select(Payment).where(
            Payment.id == payment_id,
            Payment.tenant_id == UUID(current_user["tenant_id"]),
        )
    )
    payment = result.scalar_one_or_none()
    if not payment:
        raise HTTPException(status_code=404, detail="Платёж не найден")

    if payment.status != "succeeded":
        raise HTTPException(status_code=400, detail="Только успешные платежи можно вернуть")

    payment.status = "refunded"
    await db.commit()
    return {"message": "Платёж возвращён", "payment_id": payment_id}
