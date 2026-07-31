"""
CarDetailing AI — Main Application.

FastAPI entry point with database-backed authentication.
"""

import contextlib
from collections import defaultdict
from datetime import datetime, timedelta, timezone, time
from uuid import UUID

import bcrypt
import jwt
from fastapi import FastAPI, Depends, HTTPException, Query, UploadFile, File, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.staticfiles import StaticFiles
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.config import settings
from app.core.database import get_db, init_db
from app.core.deepseek_client import get_ai_response, get_financier_response, get_consultant_response
from app.core.image_service import validate_image, save_file_local, generate_filename, delete_file_local
from app.models import Box, BoxService, Tenant, User, UserRole, AppointmentStatus, Service, Car, Appointment, Expense, DiscountRule, ClientDiscount, LoyaltyPoints, LoyaltyTierConfig, Photo, EntityType, Notification, UserNotificationSettings, WorkingHours, AppointmentHistory, Payment, ServiceDiscountRecommendation
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
    ExpenseCategoryItem, ExpenseCategoryBreakdown, ExpenseMonthPoint,
    ExpenseInsight, ExpenseAnalyticsResponse,
    PLReport, ServiceMargin,
    RevenueResponse, RevenuePoint, HeatmapResponse, HeatmapCell,
    FunnelResponse, FunnelStage,
    RfmResponse, RfmClient, SegmentCount,
    DiscountRuleCreate, DiscountRuleUpdate, DiscountRuleOut,
    ClientDiscountOut, DiscountAnalyticsResponse, DiscountAnalyticsTopRule,
    DiscountIntelligenceResponse, DiscountSuggestion, DiscountRuleAdvice,
    DiscountRoiItem, DiscountBeforeAfterPoint,
    ServiceDiscountRecOut, ServiceDiscountRecDecision, ServiceDiscountRecAnalyticsPoint,
    ServiceDiscountRecsResponse,
    LoyaltyPointsSummary, LoyaltyTierConfigOut, LoyaltyTierConfigUpdate, ClientTierOut,
    PaginatedResponse,
    PhotoOut, PhotoOrderUpdate, PhotoCreateResponse,
    NotificationOut, UnreadCountOut,
    NotificationSettingsOut, NotificationSettingsUpdate,
    TelegramConnectRequest,
    WorkingHoursOut, WorkingHoursUpdate,
    BoxCreate, BoxUpdate, BoxOut,
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

# ========== STATIC FILES ==========
import os
uploads_dir = os.path.join(os.path.dirname(__file__), "..", "uploads")
if os.path.isdir(uploads_dir):
    app.mount("/uploads", StaticFiles(directory=uploads_dir), name="uploads")

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


# ========== SERVICE HELPERS ==========

def _service_to_out(service: Service) -> ServiceOut:
    price = float(service.price or 0)
    cost = float(getattr(service, "cost_price", None) or 0)
    if cost <= 0:
        cost = float(service.material_cost or 0)
    material = float(service.material_cost or 0)
    margin = round(((price - cost) / price) * 100, 1) if price > 0 else 0.0
    return ServiceOut(
        id=service.id,
        name=service.name,
        description=service.description,
        category=service.category,
        price=price,
        duration=service.duration,
        material_cost=material,
        cost_price=cost,
        margin_percent=margin,
        is_active=bool(service.is_active),
        created_at=service.created_at,
    )


# ========== DISCOUNT HELPERS ==========

def _parse_time_str(value: str | None) -> time | None:
    """Convert 'HH:MM' string to datetime.time or None."""
    if not value:
        return None
    try:
        parts = value.strip().split(':')
        return time(int(parts[0]), int(parts[1]))
    except (ValueError, IndexError):
        return None


def _discount_rule_to_out(rule) -> dict:
    """Convert DiscountRule ORM to dict with slot times and related names."""
    return {
        "id": rule.id,
        "name": rule.name,
        "type": rule.type,
        "conditions": rule.conditions,
        "discount_percent": rule.discount_percent,
        "slot_start": rule.slot_start.strftime('%H:%M') if rule.slot_start else None,
        "slot_end": rule.slot_end.strftime('%H:%M') if rule.slot_end else None,
        "service_id": rule.service_id,
        "service_name": rule.service.name if rule.service else None,
        "client_id": rule.client_id,
        "client_name": rule.client.full_name if rule.client else None,
        "valid_until": rule.valid_until.isoformat() if rule.valid_until else None,
        "is_active": rule.is_active,
        "created_at": rule.created_at,
        "updated_at": rule.updated_at,
    }


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
        items=[_service_to_out(s) for s in items],
        total=total, skip=skip, limit=limit,
    )

@app.post("/api/services", response_model=ServiceOut)
async def create_service(
    request: ServiceCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    cost = request.cost_price if request.cost_price is not None else 0
    if cost <= 0:
        cost = request.material_cost or 0
    service = Service(
        name=request.name,
        description=request.description,
        category=request.category,
        price=request.price,
        duration=request.duration,
        material_cost=request.material_cost,
        cost_price=cost,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return _service_to_out(service)


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
    return _service_to_out(service)


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
        "box_id": appointment.box_id,
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

    # Авто-назначение бокса по услуге, если не указан
    box_id = request.box_id
    if box_id is None:
        bs_result = await db.execute(
            select(BoxService).where(
                BoxService.service_id == request.service_id,
                BoxService.tenant_id == UUID(current_user["tenant_id"]),
            ).limit(1)
        )
        bs = bs_result.scalar_one_or_none()
        if bs:
            box_id = bs.box_id

    appointment = Appointment(
        client_id=current_user["id"],
        service_id=request.service_id,
        car_id=request.car_id,
        start_time=start_time,
        end_time=end_time,
        total_price=service.price,
        status="pending",
        client_notes=request.notes or request.client_notes,
        box_id=box_id,
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
            Appointment.status.in_(["pending", "confirmed", "in_progress"]),
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


# ========== AI CONSULTANT (for clients) ==========

@app.post("/api/ai/consultant", response_model=FinancierResponse)
async def ai_consultant(
    request: FinancierRequest,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """AI-консультант для клиентов: помогает выбрать услуги, отвечает на вопросы."""
    tenant_id = UUID(current_user["tenant_id"])

    # Загружаем все услуги салона
    services_result = await db.execute(
        select(Service).where(
            Service.is_active == True,
            Service.tenant_id == tenant_id,
        ).order_by(Service.name)
    )
    services = services_result.scalars().all()

    # Загружаем количество фото в портфолио по каждой услуге
    portfolio_counts: dict[int, int] = {}
    if services:
        sids = [s.id for s in services]
        count_result = await db.execute(
            select(Photo.service_id, func.count(Photo.id))
            .where(
                Photo.tenant_id == tenant_id,
                Photo.entity_type == "portfolio",
                Photo.service_id.in_(sids),
            )
            .group_by(Photo.service_id)
        )
        for row in count_result.all():
            portfolio_counts[row[0]] = row[1]

    # Формируем контекст услуг
    services_lines = []
    for s in services:
        cat = s.category or "Без категории"
        photo_count = portfolio_counts.get(s.id, 0)
        photo_hint = f", фото в портфолио: {photo_count}" if photo_count else ""
        services_lines.append(
            f"• {s.name} (категория: {cat}) — {s.price} руб., ~{s.duration} мин., "
            f"описание: {s.description or '—'}{photo_hint}"
        )

    services_context = "\n".join(services_lines) if services_lines else "Услуги временно не загружены."

    response = await get_consultant_response(request.question, services_context)
    return FinancierResponse(response=response)


# ========== EXPENSES & P&L ==========

EXPENSE_CATALOG: list[dict] = [
    {"key": "rent", "label": "Аренда", "subcategories": ["Помещение", "Парковка", "Склад", "Оборудование в аренду"]},
    {"key": "salary", "label": "Зарплата", "subcategories": ["Оклад", "Премии", "Налоги с ФОТ", "Подрядчики"]},
    {"key": "utilities", "label": "Коммунальные услуги", "subcategories": ["Электричество", "Вода", "Отопление", "Интернет", "Вывоз мусора"]},
    {"key": "marketing", "label": "Реклама", "subcategories": ["Онлайн-реклама", "Офлайн", "Блогеры / партнёры", "Полиграфия"]},
    {"key": "supplies", "label": "Расходники и материалы", "subcategories": ["Химия", "Расходники", "Инвентарь", "Спецодежда"]},
    {"key": "equipment", "label": "Оборудование", "subcategories": ["Покупка", "Ремонт", "Обслуживание", "Амортизация"]},
    {"key": "taxes", "label": "Налоги и сборы", "subcategories": ["УСН / НДС", "Страховые взносы", "Лицензии", "Штрафы"]},
    {"key": "insurance", "label": "Страхование", "subcategories": ["Имущество", "Ответственность", "Сотрудники"]},
    {"key": "software", "label": "ПО и сервисы", "subcategories": ["CRM / SaaS", "Бухгалтерия", "Связь", "Облако"]},
    {"key": "transport", "label": "Транспорт", "subcategories": ["ГСМ", "Такси / доставка", "Ремонт авто"]},
    {"key": "other", "label": "Прочее", "subcategories": ["Канцелярия", "Обучение", "Представительские", "Другое"]},
]

EXPENSE_CAT_LABELS = {c["key"]: c["label"] for c in EXPENSE_CATALOG}


def _parse_optional_dt(value: str | None):
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
        if dt.tzinfo is None:
            dt = dt.replace(tzinfo=timezone.utc)
        return dt
    except ValueError:
        return None


def _expense_to_out(e: Expense) -> ExpenseOut:
    return ExpenseOut(
        id=e.id,
        name=e.name,
        amount=float(e.amount or 0),
        category=e.category or "other",
        subcategory=getattr(e, "subcategory", None),
        payment_status=getattr(e, "payment_status", None) or "paid",
        period_type=getattr(e, "period_type", None) or "monthly",
        period_start=getattr(e, "period_start", None),
        period_end=getattr(e, "period_end", None),
        expense_date=e.expense_date,
        notes=e.notes,
        created_at=e.created_at,
        updated_at=getattr(e, "updated_at", None),
    )


@app.get("/api/expenses/categories", response_model=list[ExpenseCategoryItem])
async def get_expense_categories(current_user: dict = Depends(_require_admin)):
    """Справочник категорий и подкатегорий затрат (RU)."""
    return [ExpenseCategoryItem(**c) for c in EXPENSE_CATALOG]


@app.get("/api/expenses")
async def get_expenses(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    category: str | None = Query(None),
    payment_status: str | None = Query(None),
    date_from: str | None = Query(None, description="YYYY-MM-DD"),
    date_to: str | None = Query(None, description="YYYY-MM-DD"),
):
    """Список расходов с фильтрами."""
    tenant_id = UUID(current_user["tenant_id"])
    filters = [Expense.tenant_id == tenant_id]
    if category:
        filters.append(Expense.category == category)
    if payment_status:
        filters.append(Expense.payment_status == payment_status)
    df = _parse_optional_dt(date_from)
    dt = _parse_optional_dt(date_to)
    if df:
        filters.append(Expense.expense_date >= df)
    if dt:
        # inclusive end of day
        if dt.hour == 0 and dt.minute == 0:
            dt = dt.replace(hour=23, minute=59, second=59)
        filters.append(Expense.expense_date <= dt)

    stmt = select(Expense).where(*filters).order_by(Expense.expense_date.desc())
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_expense_to_out(e) for e in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.post("/api/expenses", response_model=ExpenseOut)
async def create_expense(
    request: ExpenseCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый расход."""
    expense = Expense(
        name=request.name,
        amount=request.amount,
        category=request.category or "other",
        subcategory=request.subcategory,
        payment_status=request.payment_status or "paid",
        period_type=request.period_type or "monthly",
        period_start=_parse_optional_dt(request.period_start),
        period_end=_parse_optional_dt(request.period_end),
        expense_date=_parse_optional_dt(request.expense_date) or datetime.now(timezone.utc),
        notes=request.notes,
        tenant_id=UUID(current_user["tenant_id"]),
    )
    db.add(expense)
    await db.commit()
    await db.refresh(expense)
    return _expense_to_out(expense)


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
    for key in ("expense_date", "period_start", "period_end"):
        if key in update_data:
            update_data[key] = _parse_optional_dt(update_data[key])

    for key, value in update_data.items():
        setattr(expense, key, value)

    await db.commit()
    await db.refresh(expense)
    return _expense_to_out(expense)


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
    return {"message": "Expense deleted"}


@app.get("/api/analytics/expenses", response_model=ExpenseAnalyticsResponse)
async def get_expense_analytics(
    months: int = Query(6, ge=1, le=24),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика затрат: разбивка, графики, ИИ-подсказки."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = (now.replace(day=1) - timedelta(days=months * 31)).replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.tenant_id == tenant_id,
                Expense.expense_date >= date_from,
            )
        )
    ).scalars().all()

    total = sum(float(e.amount or 0) for e in expenses)
    paid_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", "paid") or "paid") == "paid")
    unpaid_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", None) or "") == "unpaid")
    overdue_total = sum(float(e.amount or 0) for e in expenses if (getattr(e, "payment_status", None) or "") == "overdue")

    cat_map: dict[str, dict] = {}
    for e in expenses:
        cat = e.category or "other"
        if cat not in cat_map:
            cat_map[cat] = {"amount": 0.0, "count": 0}
        cat_map[cat]["amount"] += float(e.amount or 0)
        cat_map[cat]["count"] += 1

    by_category = [
        ExpenseCategoryBreakdown(
            category=k,
            label=EXPENSE_CAT_LABELS.get(k, k),
            amount=round(v["amount"], 2),
            share_percent=round((v["amount"] / total * 100) if total else 0, 1),
            count=v["count"],
        )
        for k, v in sorted(cat_map.items(), key=lambda x: x[1]["amount"], reverse=True)
    ]

    # by month
    month_map: dict[str, dict] = {}
    for e in expenses:
        if not e.expense_date:
            continue
        key = e.expense_date.strftime("%Y-%m")
        if key not in month_map:
            month_map[key] = {"total": 0.0, "by_category": {}}
        month_map[key]["total"] += float(e.amount or 0)
        cat = e.category or "other"
        month_map[key]["by_category"][cat] = month_map[key]["by_category"].get(cat, 0) + float(e.amount or 0)

    month_names = {
        1: "Янв", 2: "Фев", 3: "Мар", 4: "Апр", 5: "Май", 6: "Июн",
        7: "Июл", 8: "Авг", 9: "Сен", 10: "Окт", 11: "Ноя", 12: "Дек",
    }
    by_month = []
    for key in sorted(month_map.keys()):
        y, m = key.split("-")
        by_month.append(ExpenseMonthPoint(
            month=key,
            label=f"{month_names[int(m)]} {y}",
            total=round(month_map[key]["total"], 2),
            by_category={k: round(v, 2) for k, v in month_map[key]["by_category"].items()},
        ))

    # Revenue this month for break-even / forecast
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    appts = (
        await db.execute(
            select(Appointment)
            .options(selectinload(Appointment.service))
            .where(
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= month_start,
                Appointment.status == "completed",
            )
        )
    ).scalars().all()
    revenue_month = sum(float(a.total_price or 0) for a in appts)
    material_month = sum(float(a.service.material_cost or 0) if a.service else 0 for a in appts)

    # Fixed costs this month
    month_expenses = [e for e in expenses if e.expense_date and e.expense_date >= month_start]
    fixed_month = sum(float(e.amount or 0) for e in month_expenses)

    # Contribution margin ratio
    contrib = revenue_month - material_month
    contrib_ratio = (contrib / revenue_month) if revenue_month > 0 else 0.4
    break_even = round(fixed_month / contrib_ratio, 2) if contrib_ratio > 0 else 0.0
    forecast_profit = round(revenue_month - material_month - fixed_month, 2)

    insights: list[ExpenseInsight] = []

    # MoM anomalies by category
    if len(by_month) >= 2:
        prev, cur = by_month[-2], by_month[-1]
        for cat_key, label in EXPENSE_CAT_LABELS.items():
            prev_v = prev.by_category.get(cat_key, 0)
            cur_v = cur.by_category.get(cat_key, 0)
            if prev_v > 0 and cur_v > prev_v * 1.3:
                growth = (cur_v - prev_v) / prev_v * 100
                insights.append(ExpenseInsight(
                    type="anomaly",
                    severity="critical" if growth >= 40 else "warn",
                    title=f"Рост: {label}",
                    message=f"{label} выросли на {growth:.0f}% ({prev_v:,.0f} → {cur_v:,.0f} ₽). Проверьте счета и тарифы.",
                ))

    # Rent share tip
    rent = cat_map.get("rent", {}).get("amount", 0)
    if revenue_month > 0 and rent > 0:
        # approximate monthly rent from period share
        rent_month = sum(float(e.amount or 0) for e in month_expenses if e.category == "rent")
        share = rent_month / revenue_month * 100
        if share >= 25:
            insights.append(ExpenseInsight(
                type="tip",
                severity="warn",
                title="Аренда дорогая относительно выручки",
                message=f"Аренда ≈ {share:.0f}% выручки месяца. Ориентир для салона — до 15–20%. Рассмотрите пересмотр договора или рост загрузки.",
            ))

    # Marketing efficiency
    mkt_month = sum(float(e.amount or 0) for e in month_expenses if e.category == "marketing")
    if mkt_month > 0 and revenue_month > 0:
        roi_proxy = revenue_month / mkt_month
        if roi_proxy < 5:
            insights.append(ExpenseInsight(
                type="tip",
                severity="warn",
                title="Реклама может быть неэффективна",
                message=f"На 1 ₽ рекламы приходится ≈ {roi_proxy:.1f} ₽ выручки. Проверьте каналы: отключите слабые, усильте рабочие.",
            ))
        elif roi_proxy >= 10:
            insights.append(ExpenseInsight(
                type="tip",
                severity="info",
                title="Реклама работает",
                message=f"Соотношение выручка/реклама ≈ {roi_proxy:.1f}× — можно аккуратно масштабировать рабочие каналы.",
            ))

    insights.append(ExpenseInsight(
        type="break_even",
        severity="info",
        title="Точка безубыточности",
        message=(
            f"При текущих постоянных затратах ({fixed_month:,.0f} ₽) и марже после материалов "
            f"нужна выручка ≈ {break_even:,.0f} ₽/мес. Сейчас: {revenue_month:,.0f} ₽."
        ),
    ))
    insights.append(ExpenseInsight(
        type="forecast",
        severity="info" if forecast_profit >= 0 else "warn",
        title="Прогноз прибыли (месяц)",
        message=f"Выручка − материалы − постоянные ≈ {forecast_profit:,.0f} ₽.",
    ))

    return ExpenseAnalyticsResponse(
        total=round(total, 2),
        paid_total=round(paid_total, 2),
        unpaid_total=round(unpaid_total, 2),
        overdue_total=round(overdue_total, 2),
        by_category=by_category,
        by_month=by_month,
        insights=insights,
        break_even_revenue=break_even,
        forecast_profit=forecast_profit,
        revenue_month=round(revenue_month, 2),
    )


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
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Дневная выручка за период (Area Chart) + сравнение с предыдущим периодом."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем границы периода
    if start_date and end_date:
        s_date = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        e_date = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        # По умолчанию — текущий месяц
        s_date = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if s_date.month == 12:
            e_date = s_date.replace(year=s_date.year + 1, month=1)
        else:
            e_date = s_date.replace(month=s_date.month + 1)

    period_days = (e_date - s_date).days

    # Предыдущий период (такой же длины)
    prev_end = s_date
    prev_start = prev_end - timedelta(days=period_days)

    async def _fetch_period(start: datetime, end: datetime) -> tuple[list[RevenuePoint], float, float]:
        """Вспомогательная функция: получить данные за период."""
        result = await db.execute(
            select(Appointment).where(
                Appointment.start_time >= start,
                Appointment.start_time < end,
                Appointment.tenant_id == tenant_id,
                Appointment.status == "completed",
            ).order_by(Appointment.start_time)
        )
        appts = result.scalars().all()

        # Если период <= 31 день — группировка по дням, иначе по неделям/месяцам
        daily: dict[str, dict] = {}
        for a in appts:
            if period_days <= 35:
                key = a.start_time.strftime("%Y-%m-%d")
            else:
                key = a.start_time.strftime("%Y-%m-%d")  # пока дни, фронт сам сгруппирует
            if key not in daily:
                daily[key] = {"revenue": 0.0, "appointments": 0}
            daily[key]["revenue"] += float(a.total_price or 0)
            daily[key]["appointments"] += 1

        points = [
            RevenuePoint(date=key, revenue=round(v["revenue"], 2), appointments=v["appointments"])
            for key, v in sorted(daily.items())
        ]
        total = round(sum(p.revenue for p in points), 2)
        days_count = max(len(daily), 1)
        avg = round(total / days_count, 2) if days_count else 0
        return points, total, avg

    # Основной период
    points, total, avg = await _fetch_period(s_date, e_date)

    # Предыдущий период
    prev_points, prev_total, prev_avg = await _fetch_period(prev_start, prev_end)

    # Лучший/худший день
    days_with_data = [p for p in points if p.appointments > 0]
    best = max(days_with_data, key=lambda p: p.revenue) if days_with_data else None
    worst = min(days_with_data, key=lambda p: p.revenue) if days_with_data else None

    # Изменение в %
    change_percent = round(
        ((total - prev_total) / prev_total * 100) if prev_total else 0, 1
    )

    return RevenueResponse(
        daily=points,
        total=total,
        avg_per_day=avg,
        best_day=best.date if best else None,
        worst_day=worst.date if worst else None,
        previous_total=round(prev_total, 2),
        change_percent=change_percent,
        previous_avg_per_day=prev_avg,
    )


@app.get("/api/analytics/heatmap", response_model=HeatmapResponse)
async def get_heatmap(
    box_id: int | None = Query(None, description="Фильтр по боксу"),
    days: int = Query(60, ge=7, le=120, description="Период анализа в днях"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Тепловая карта загрузки: день недели × час за выбранный период."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(days=days)

    # Фильтр по боксу
    filters = [
        Appointment.start_time >= date_from,
        Appointment.start_time <= now,
        Appointment.tenant_id == tenant_id,
        Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
    ]
    if box_id is not None:
        filters.append(Appointment.box_id == box_id)

    result = await db.execute(
        select(Appointment).where(*filters)
    )
    appts = result.scalars().all()

    # Сетка 7×15 (дни недели × часы 8-22)
    cells_map: dict[tuple[int, int], dict] = {}
    for day in range(7):
        for hour in range(8, 23):
            cells_map[(day, hour)] = {"count": 0, "revenue": 0.0}

    for a in appts:
        day = a.start_time.weekday()  # 0=Mon
        hour = a.start_time.hour
        key = (day, hour)
        if key in cells_map:
            cells_map[key]["count"] += 1
            cells_map[key]["revenue"] += float(a.total_price or 0)

    cells = [
        HeatmapCell(
            day=d, hour=h, count=v["count"],
            revenue=round(v["revenue"], 2),
            box_id=box_id,
        )
        for (d, h), v in sorted(cells_map.items())
    ]

    # Загружаем список боксов тенанта
    boxes_result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id).order_by(Box.sort_order, Box.name)
    )
    boxes = boxes_result.scalars().all()

    # Загружаем привязки услуг для всех боксов (как в /api/boxes)
    box_ids = [b.id for b in boxes]
    box_services_map: dict[int, list[int]] = {}
    if box_ids:
        bs_result = await db.execute(
            select(BoxService).where(
                BoxService.box_id.in_(box_ids),
                BoxService.tenant_id == tenant_id,
            )
        )
        for bs in bs_result.scalars().all():
            box_services_map.setdefault(bs.box_id, []).append(bs.service_id)

    out = []
    for b in boxes:
        bo = BoxOut.model_validate(b)
        bo.service_ids = box_services_map.get(b.id, [])
        out.append(bo)

    return HeatmapResponse(cells=cells, boxes=out)


@app.get("/api/analytics/funnel", response_model=FunnelResponse)
async def get_funnel(
    start_date: str | None = Query(None, description="YYYY-MM-DD"),
    end_date: str | None = Query(None, description="YYYY-MM-DD"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Воронка продаж: конверсия по статусам за период (по дате создания записи)."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)

    # Определяем границы периода по created_at
    if start_date and end_date:
        date_from = datetime.fromisoformat(start_date).replace(tzinfo=timezone.utc)
        date_to = datetime.fromisoformat(end_date).replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
    else:
        # По умолчанию — последние 30 дней
        date_to = now
        date_from = date_to - timedelta(days=30)

    result = await db.execute(
        select(Appointment).where(
            Appointment.created_at >= date_from,
            Appointment.created_at <= date_to,
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

    conversion = round(counts["completed"] / total * 100, 1) if total else 0

    return FunnelResponse(
        stages=stages,
        total=total,
        conversion_rate=conversion,
    )


@app.get("/api/analytics/discounts", response_model=DiscountAnalyticsResponse)
async def get_discount_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика эффективности скидок."""
    tenant_id = UUID(current_user["tenant_id"])

    # Все правила
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    all_rules = rules_result.scalars().all()
    total_rules = len(all_rules)
    active_rules = sum(1 for r in all_rules if r.is_active)

    # Все применения скидок
    cd_result = await db.execute(
        select(ClientDiscount)
        .options(selectinload(ClientDiscount.discount_rule))
        .where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    all_cd = cd_result.scalars().all()

    total_times_used = len(all_cd)
    total_discount_amount = sum(float(cd.applied_amount or 0) for cd in all_cd)
    unique_clients = len(set(cd.client_id for cd in all_cd))

    # Топ правил по использованию
    rule_usage: dict[int, dict] = {}
    for cd in all_cd:
        rid = cd.discount_rule_id
        if rid not in rule_usage:
            rule_usage[rid] = {"times_used": 0, "total_discount": 0.0, "clients": set()}
        rule_usage[rid]["times_used"] += 1
        rule_usage[rid]["total_discount"] += float(cd.applied_amount or 0)
        rule_usage[rid]["clients"].add(cd.client_id)

    top_rules = []
    for rid, stats in sorted(rule_usage.items(), key=lambda x: x[1]["times_used"], reverse=True)[:10]:
        rule = next((r for r in all_rules if r.id == rid), None)
        top_rules.append(DiscountAnalyticsTopRule(
            rule_id=rid,
            rule_name=rule.name if rule else f"Правило #{rid}",
            rule_type=rule.type if rule else "unknown",
            times_used=stats["times_used"],
            total_discount=round(stats["total_discount"], 2),
            client_count=len(stats["clients"]),
        ))

    return DiscountAnalyticsResponse(
        total_rules=total_rules,
        active_rules=active_rules,
        total_times_used=total_times_used,
        total_discount_amount=round(total_discount_amount, 2),
        unique_clients_affected=unique_clients,
        top_rules=top_rules,
    )


def _discount_percent_relative(hour_load: float, peak_load: float) -> int:
    """
    Happy Hours только там, где загрузка заметно ниже пика группы (Пн–Пт / Сб / Вс).

    Пиковые часы на теплокарте → 0% (скидка вредна).
    Простой / почти пустые слоты → 20–25%.
    """
    if peak_load <= 0:
        return 25

    ratio = hour_load / peak_load
    if ratio >= 0.55:
        return 0
    if ratio >= 0.35:
        return 10
    if ratio >= 0.20:
        return 15
    if hour_load <= 0 or ratio < 0.12:
        return 25
    return 20


def _merge_hour_suggestions(
    hour_percents: dict[int, tuple[int, float]],
    weekdays: list[int],
    weekday_label: str,
    prefix: str,
) -> list[DiscountSuggestion]:
    """Склеивает соседние часы с одинаковым % (пики с 0% разрывают цепочку)."""
    suggestions: list[DiscountSuggestion] = []
    hours = sorted(h for h, (p, _) in hour_percents.items() if p > 0)
    if not hours:
        return suggestions

    start = hours[0]
    prev = hours[0]
    cur_pct, _ = hour_percents[start]

    def flush(s: int, e: int, pct: int, avg: float):
        if pct <= 0:
            return
        suggestions.append(DiscountSuggestion(
            key=f"{prefix}-{s}-{e}-{pct}",
            name=f"Happy Hours {weekday_label} {s:02d}:00–{e:02d}:00",
            hour_start=f"{s:02d}:00",
            hour_end=f"{e:02d}:00",
            weekdays=weekdays,
            weekday_label=weekday_label,
            discount_percent=pct,
            avg_load=round(avg, 2),
            reason=(
                f"Загрузка {avg:.2f} отн. пика группы → скидка {pct}%. "
                f"Свободный слот на теплокарте — Happy Hours подстегнут спрос."
            ),
        ))

    avgs = [hour_percents[start][1]]
    for h in hours[1:]:
        pct, avg = hour_percents[h]
        if h == prev + 1 and pct == cur_pct:
            prev = h
            avgs.append(avg)
            continue
        flush(start, prev + 1, cur_pct, sum(avgs) / len(avgs))
        start = prev = h
        cur_pct = pct
        avgs = [avg]
    flush(start, prev + 1, cur_pct, sum(avgs) / len(avgs))
    return suggestions


def _build_group_hour_percents(
    weekdays: list[int],
    avg_for,
) -> dict[int, tuple[int, float]]:
    """
    Яркость часа = max по дням группы (как на теплокарте).
    Пик = max по часам. Скидка только ниже пика.
    """
    hour_loads: dict[int, float] = {}
    for hour in range(8, 23):
        day_avgs = [avg_for(d, hour) for d in weekdays]
        hour_loads[hour] = max(day_avgs) if day_avgs else 0.0

    peak = max(hour_loads.values()) if hour_loads else 0.0
    hour_percents: dict[int, tuple[int, float]] = {}
    for hour, load in hour_loads.items():
        mean_load = sum(avg_for(d, hour) for d in weekdays) / max(len(weekdays), 1)
        pct = _discount_percent_relative(load, peak)
        hour_percents[hour] = (pct, mean_load)
    return hour_percents


@app.get("/api/analytics/discount-intelligence", response_model=DiscountIntelligenceResponse)
async def get_discount_intelligence(
    days: int = Query(60, ge=14, le=120, description="Период анализа"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Загрузка → авто-предложения Happy Hours + ROI + рекомендации."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    date_from = now - timedelta(days=days)

    result = await db.execute(
        select(Appointment).where(
            Appointment.tenant_id == tenant_id,
            Appointment.start_time >= date_from,
            Appointment.start_time <= now,
            Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
        )
    )
    appts = result.scalars().all()

    # Сколько раз встречался каждый weekday в периоде
    weekday_occ: dict[int, int] = {d: 0 for d in range(7)}
    cursor = date_from.date()
    end_d = now.date()
    while cursor <= end_d:
        weekday_occ[cursor.weekday()] += 1
        cursor += timedelta(days=1)

    cells_map: dict[tuple[int, int], dict] = {}
    for day in range(7):
        for hour in range(8, 23):
            cells_map[(day, hour)] = {"count": 0, "revenue": 0.0}

    for a in appts:
        key = (a.start_time.weekday(), a.start_time.hour)
        if key in cells_map:
            cells_map[key]["count"] += 1
            cells_map[key]["revenue"] += float(a.total_price or 0)

    cells = [
        HeatmapCell(day=d, hour=h, count=v["count"], revenue=round(v["revenue"], 2))
        for (d, h), v in sorted(cells_map.items())
    ]

    def avg_for(day: int, hour: int) -> float:
        occ = max(weekday_occ.get(day, 1), 1)
        return cells_map[(day, hour)]["count"] / occ

    # Группы: Пн–Пт и Сб / Вс отдельно (Вс тоже)
    groups = [
        ([0, 1, 2, 3, 4], "Пн–Пт", "wd"),
        ([5], "Сб", "sat"),
        ([6], "Вс", "sun"),
    ]

    suggestions: list[DiscountSuggestion] = []
    for weekdays, label, prefix in groups:
        hour_percents = _build_group_hour_percents(weekdays, avg_for)
        suggestions.extend(_merge_hour_suggestions(hour_percents, weekdays, label, prefix))

    # Существующие правила
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    all_rules = rules_result.scalars().all()

    cd_result = await db.execute(
        select(ClientDiscount).where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    all_cd = cd_result.scalars().all()
    usage_by_rule: dict[int, list] = defaultdict(list)
    for cd in all_cd:
        usage_by_rule[cd.discount_rule_id].append(cd)

    avg_check = 0.0
    completed = [a for a in appts if a.status == "completed"]
    if completed:
        avg_check = sum(float(a.total_price or 0) for a in completed) / len(completed)

    roi: list[DiscountRoiItem] = []
    before_after: list[DiscountBeforeAfterPoint] = []
    recommendations: list[DiscountRuleAdvice] = []

    for rule in all_rules:
        used = usage_by_rule.get(rule.id, [])
        cost = sum(float(cd.applied_amount or 0) for cd in used)
        times = len(used)
        # Эвристика: каждая скидка «привела» ~0.6 визита сверх базовой загрузки
        extra_rev = round(times * avg_check * 0.6, 2) if avg_check else 0.0
        roi_pct = round(((extra_rev - cost) / cost) * 100, 1) if cost > 0 else (100.0 if times > 0 else 0.0)
        verdict = "держать" if roi_pct >= 20 else ("пересмотреть" if roi_pct >= 0 else "отключить")
        roi.append(DiscountRoiItem(
            rule_id=rule.id,
            rule_name=rule.name,
            times_used=times,
            discount_cost=round(cost, 2),
            estimated_extra_revenue=extra_rev,
            roi_percent=roi_pct,
            verdict=verdict,
        ))

        if rule.type == "happy_hours" and rule.slot_start and rule.slot_end:
            h0 = rule.slot_start.hour
            h1 = rule.slot_end.hour
            if h1 <= h0:
                h1 = h0 + 1
            cond_days = (rule.conditions or {}).get("weekdays")
            if not isinstance(cond_days, list) or not cond_days:
                cond_days = list(range(5))  # legacy: будни

            created = rule.created_at or date_from
            if created.tzinfo is None:
                created = created.replace(tzinfo=timezone.utc)
            before_from = created - timedelta(days=30)
            after_to = min(now, created + timedelta(days=30))

            def slot_avg(a_from, a_to):
                cnt = 0
                days_n = 0
                d = a_from.date()
                while d <= a_to.date():
                    if d.weekday() in cond_days:
                        days_n += 1
                    d += timedelta(days=1)
                for a in appts:
                    if a_from <= a.start_time <= a_to and a.start_time.weekday() in cond_days:
                        if h0 <= a.start_time.hour < h1:
                            cnt += 1
                return round(cnt / max(days_n, 1), 2)

            # для before/after нужны все записи — подгрузим расширенный диапазон
            before_avg = 0.0
            after_avg = 0.0
            ext = await db.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.start_time >= before_from,
                    Appointment.start_time <= after_to,
                    Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
                )
            )
            ext_appts = ext.scalars().all()

            def slot_avg_ext(a_from, a_to, pool):
                cnt = 0
                days_n = 0
                d = a_from.date()
                while d <= a_to.date():
                    if d.weekday() in cond_days:
                        days_n += 1
                    d += timedelta(days=1)
                for a in pool:
                    if a_from <= a.start_time <= a_to and a.start_time.weekday() in cond_days:
                        if h0 <= a.start_time.hour < h1:
                            cnt += 1
                return round(cnt / max(days_n, 1), 2)

            before_avg = slot_avg_ext(before_from, created, ext_appts)
            after_avg = slot_avg_ext(created, after_to, ext_appts)
            before_after.append(DiscountBeforeAfterPoint(
                rule_id=rule.id,
                rule_name=rule.name,
                label=f"{rule.slot_start.strftime('%H:%M')}–{rule.slot_end.strftime('%H:%M')}",
                before_avg=before_avg,
                after_avg=after_avg,
            ))

            # Рекомендация: относительно пика группы; широкий слот с пиком внутри — отключить
            peak_for_rule = max(
                (avg_for(d, h) for d in cond_days for h in range(8, 23)),
                default=0.0,
            )
            hour_ideals: list[int] = []
            hour_loads: list[float] = []
            for h in range(h0, min(h1, 23)):
                load = max((avg_for(d, h) for d in cond_days), default=0.0)
                hour_loads.append(load)
                hour_ideals.append(_discount_percent_relative(load, peak_for_rule))
            slot_avg_now = sum(hour_loads) / len(hour_loads) if hour_loads else 0.0
            peak_hours_inside = sum(1 for p in hour_ideals if p == 0)
            idle_ideals = [p for p in hour_ideals if p > 0]
            if peak_hours_inside > 0:
                ideal = 0
            elif idle_ideals:
                ideal = min(idle_ideals)
            else:
                ideal = _discount_percent_relative(slot_avg_now, peak_for_rule)

            if not rule.is_active:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="keep",
                    message="Правило выключено",
                ))
            elif peak_hours_inside > 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=(
                        f"Слот {h0:02d}:00–{h1:02d}:00 перекрывает пик загрузки "
                        f"({peak_hours_inside} ч). На пике скидку давать нельзя — "
                        f"сузьте до пустых часов или отключите."
                    ),
                    suggested_percent=0,
                ))
            elif ideal == 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=f"Слот у пика (ср. {slot_avg_now:.2f}) — скидку лучше отключить",
                    suggested_percent=0,
                ))
            elif ideal > rule.discount_percent + 4:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="increase",
                    message=f"Слот пустой (ср. {slot_avg_now:.2f}) — увеличить до {ideal}%",
                    suggested_percent=ideal,
                ))
            elif ideal < rule.discount_percent - 4:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="decrease",
                    message=f"Загрузка выросла (ср. {slot_avg_now:.2f}) — снизить до {ideal}%",
                    suggested_percent=ideal,
                ))
            elif verdict == "отключить" and times > 0:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="disable",
                    message=f"ROI {roi_pct}% отрицательный — отключить или пересобрать слот",
                ))
            else:
                recommendations.append(DiscountRuleAdvice(
                    rule_id=rule.id, rule_name=rule.name, action="keep",
                    message=f"Слот ок (ср. {slot_avg_now:.2f}, ROI {roi_pct}%)",
                    suggested_percent=rule.discount_percent,
                ))

    # Предложения, которых ещё нет как правил
    existing_keys = set()
    for r in all_rules:
        if r.type == "happy_hours" and r.slot_start and r.slot_end:
            existing_keys.add(
                (r.slot_start.strftime("%H:%M"), r.slot_end.strftime("%H:%M"), r.discount_percent)
            )

    for s in suggestions:
        if (s.hour_start, s.hour_end, s.discount_percent) not in existing_keys:
            recommendations.insert(0, DiscountRuleAdvice(
                rule_id=None,
                rule_name=s.name,
                action="create",
                message=s.reason,
                suggested_percent=s.discount_percent,
            ))

    return DiscountIntelligenceResponse(
        period_days=days,
        cells=cells,
        suggestions=suggestions,
        recommendations=recommendations[:20],
        roi=roi,
        before_after=before_after,
    )


@app.post("/api/discounts/broadcast-happy-hours")
async def broadcast_happy_hours(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Рассылка клиентам о текущих Happy Hours."""
    from app.core.notification_service import create_notification

    tenant_id = UUID(current_user["tenant_id"])
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            DiscountRule.type == "happy_hours",
        )
    )
    rules = rules_result.scalars().all()
    if not rules:
        raise HTTPException(status_code=400, detail="Нет активных Happy Hours для рассылки")

    lines = []
    for r in rules:
        slot = f"{r.slot_start.strftime('%H:%M') if r.slot_start else '?'}–{r.slot_end.strftime('%H:%M') if r.slot_end else '?'}"
        days = (r.conditions or {}).get("weekdays")
        if isinstance(days, list) and days:
            names = ["Пн", "Вт", "Ср", "Чт", "Пт", "Сб", "Вс"]
            day_label = "–".join(names[d] for d in sorted(days) if 0 <= d <= 6)
        else:
            day_label = "Пн–Пт"
        lines.append(f"• {day_label} {slot}: −{r.discount_percent}%")

    title = "Счастливые часы в салоне"
    message = "Запишитесь в свободное время и получите скидку:\n" + "\n".join(lines)

    clients = await db.execute(
        select(User).where(
            User.tenant_id == tenant_id,
            User.role == UserRole.client,
        )
    )
    client_list = clients.scalars().all()
    sent = 0
    for c in client_list:
        await create_notification(
            db,
            user_id=c.id,
            tenant_id=tenant_id,
            title=title,
            message=message,
            type="promo",
            channel="in_app",
        )
        sent += 1

    return {"sent": sent, "message": f"Рассылка отправлена {sent} клиентам"}


def _percent_from_priority(priority: float) -> int:
    """≥0.7 → 20–30%, 0.45–0.69 → 10–20%."""
    if priority >= 0.7:
        t = min(1.0, (priority - 0.7) / 0.3)
        return int(round(20 + t * 10))
    if priority >= 0.45:
        t = (priority - 0.45) / 0.25
        return int(round(10 + t * 10))
    return 0


async def _compute_service_discount_recs(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ServiceDiscountRecommendation]:
    """
    Авто-рекомендации скидок по услугам (бухлогика салона).

    Цель:
    - подстегнуть просевшие по количеству записей;
    - подстегнуть низкомаржинальные (объём → списать постоянные на них);
    - высокомаржинальные с нормальным спросом НЕ резать (на них зарабатываем).

    Формула приоритета:
      volume_need = 1 − популярность (0…1)
      margin_need = 1 − маржа (себест./цена)
      priority = volume_need×0.55 + margin_need×0.45
    + давление постоянных расходов усиливает % на низкомаржинальных.
    """
    now = datetime.now(timezone.utc)
    cur_from = now - timedelta(days=30)
    prev_from = now - timedelta(days=60)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    services = (
        await db.execute(
            select(Service).where(Service.tenant_id == tenant_id, Service.is_active == True)
        )
    ).scalars().all()
    if not services:
        return []

    appts = (
        await db.execute(
            select(Appointment).where(
                Appointment.tenant_id == tenant_id,
                Appointment.start_time >= prev_from,
                Appointment.start_time <= now,
                Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
            )
        )
    ).scalars().all()

    stats: dict[int, dict] = {
        s.id: {"cur": 0, "prev": 0, "service": s} for s in services
    }
    revenue_month = 0.0
    for a in appts:
        sid = a.service_id
        if a.start_time >= month_start:
            revenue_month += float(a.total_price or 0)
        if sid not in stats:
            continue
        if a.start_time >= cur_from:
            stats[sid]["cur"] += 1
        elif a.start_time >= prev_from:
            stats[sid]["prev"] += 1

    # Постоянные расходы текущего месяца (давление на маржу)
    expenses = (
        await db.execute(
            select(Expense).where(
                Expense.tenant_id == tenant_id,
                Expense.expense_date >= month_start,
                Expense.expense_date <= now,
            )
        )
    ).scalars().all()
    fixed_month = sum(float(e.amount or 0) for e in expenses)
    overhead_pressure = fixed_month / max(revenue_month, 1.0)

    max_bookings = max((v["cur"] for v in stats.values()), default=0) or 1
    booking_counts = [v["cur"] for v in stats.values()]
    median_bookings = sorted(booking_counts)[len(booking_counts) // 2] if booking_counts else 0

    margins_raw: list[float] = []
    service_margin: dict[int, float] = {}
    for s in services:
        price = float(s.price or 0)
        cost = float(getattr(s, "cost_price", None) or 0) or float(s.material_cost or 0)
        raw = ((price - cost) / price) if price > 0 else 0.0
        raw = max(0.0, min(1.0, raw))
        service_margin[s.id] = raw
        margins_raw.append(raw)
    margin_median = sorted(margins_raw)[len(margins_raw) // 2] if margins_raw else 0.5

    # Порог «высокая маржа — защищаем цену»
    HIGH_MARGIN_PROTECT = 0.70

    old_pending = (
        await db.execute(
            select(ServiceDiscountRecommendation).where(
                ServiceDiscountRecommendation.tenant_id == tenant_id,
                ServiceDiscountRecommendation.status == "pending",
            )
        )
    ).scalars().all()
    for row in old_pending:
        await db.delete(row)

    created: list[ServiceDiscountRecommendation] = []
    for s in services:
        price = float(s.price or 0)
        cost = float(getattr(s, "cost_price", None) or 0) or float(s.material_cost or 0)
        margin_raw = service_margin[s.id]
        bookings = stats[s.id]["cur"]
        prev = stats[s.id]["prev"]
        popularity = bookings / max_bookings

        volume_need = 1.0 - popularity
        if bookings == 0:
            volume_need = 1.0
        elif bookings <= max(median_bookings, 1):
            volume_need = max(volume_need, 0.65)

        margin_need = 1.0 - margin_raw
        # индекс для UI (как раньше): относительно медианы каталога
        if margin_median >= 0.999:
            margin_index = 1.0
        else:
            # выше медианы → ближе к 1, ниже → ближе к 0
            span = max(1.0 - margin_median, margin_median, 0.01)
            margin_index = max(0.0, min(1.0, 0.5 + (margin_raw - margin_median) / (2 * span)))

        is_low_volume = bookings <= max(1, int(max_bookings * 0.45)) or popularity <= 0.45
        is_low_margin = margin_raw <= margin_median or margin_raw < 0.55

        # Высокомаржинальные с нормальным/хорошим спросом — не трогаем
        if margin_raw >= HIGH_MARGIN_PROTECT and not is_low_volume:
            continue

        # Нужна скидка только если просадка по объёму ИЛИ низкая маржа
        if not (is_low_volume or is_low_margin):
            continue

        priority = volume_need * 0.55 + margin_need * 0.45
        if priority < 0.40:
            continue

        suggested = _percent_from_priority(priority)
        if suggested <= 0:
            continue

        # На высокомаржинальных, но просевших — только мягкая скидка (заполнить слот)
        if margin_raw >= HIGH_MARGIN_PROTECT and is_low_volume:
            suggested = min(suggested, 12)
            scenario = "volume_fill"
            reason = (
                f"Просадка по записям: {bookings} за 30д (макс в каталоге {max_bookings}). "
                f"Маржа высокая ({margin_raw * 100:.0f}%) — цену сильно не режем, "
                f"мягкая скидка {suggested}% только чтобы подтянуть спрос. "
                f"Себест. {cost:.0f} ₽ / цена {price:.0f} ₽."
            )
        elif is_low_margin:
            scenario = "low_margin_volume"
            # Постоянные расходы списываем через объём на низкомаржинальных
            if overhead_pressure >= 0.20:
                boost = 5 if overhead_pressure < 0.35 else 8
                suggested = min(30, suggested + boost)
            reason = (
                f"Низкомаржинальная услуга ({margin_raw * 100:.0f}%) — приоритет объёма: "
                f"постоянные затраты ({fixed_month:,.0f} ₽/мес) удобнее закрывать оборотом здесь, "
                f"а высокомаржинальные оставлять без скидки. "
                f"Записей 30д: {bookings} (попул. {popularity:.2f}). "
                f"Себест. {cost:.0f} ₽ / цена {price:.0f} ₽. "
                f"Приоритет {priority:.2f} = объём×0.55 + (1−маржа)×0.45 → скидка {suggested}%."
            )
        else:
            scenario = "volume_fill"
            reason = (
                f"Мало записей ({bookings} за 30д, макс {max_bookings}) — подстегнуть спрос. "
                f"Маржа {margin_raw * 100:.0f}%. Рекомендуемая скидка: {suggested}%."
            )

        # margin_index для хранения: используем «нужность маржи» как 1 - margin для согласованности UI
        rec = ServiceDiscountRecommendation(
            tenant_id=tenant_id,
            service_id=s.id,
            period_days=30,
            bookings_30d=bookings,
            bookings_prev_30d=prev,
            popularity_index=round(popularity, 4),
            margin_raw=round(margin_raw, 4),
            margin_index=round(margin_index, 4),
            priority=round(priority, 4),
            suggested_percent=suggested,
            scenario=scenario,
            reason=reason,
            status="pending",
            computed_at=now,
        )
        db.add(rec)
        created.append(rec)

    await db.commit()
    for r in created:
        await db.refresh(r)
    return created


def _rec_to_out(rec: ServiceDiscountRecommendation) -> ServiceDiscountRecOut:
    svc = rec.service
    price = float(svc.price or 0) if svc else 0
    cost = float(getattr(svc, "cost_price", None) or 0) if svc else 0
    if svc and cost <= 0:
        cost = float(svc.material_cost or 0)
    return ServiceDiscountRecOut(
        id=rec.id,
        service_id=rec.service_id,
        service_name=svc.name if svc else f"Услуга #{rec.service_id}",
        price=price,
        cost_price=cost,
        bookings_30d=rec.bookings_30d,
        bookings_prev_30d=rec.bookings_prev_30d,
        popularity_index=rec.popularity_index,
        margin_raw=rec.margin_raw,
        margin_index=rec.margin_index,
        priority=rec.priority,
        suggested_percent=rec.suggested_percent,
        adjusted_percent=rec.adjusted_percent,
        scenario=rec.scenario,
        reason=rec.reason,
        status=rec.status,
        discount_rule_id=rec.discount_rule_id,
        computed_at=rec.computed_at,
        decided_at=rec.decided_at,
    )


async def _rec_analytics(
    db: AsyncSession,
    tenant_id: UUID,
) -> list[ServiceDiscountRecAnalyticsPoint]:
    now = datetime.now(timezone.utc)
    approved = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .options(selectinload(ServiceDiscountRecommendation.service))
            .where(
                ServiceDiscountRecommendation.tenant_id == tenant_id,
                ServiceDiscountRecommendation.status.in_(["approved", "adjusted"]),
                ServiceDiscountRecommendation.decided_at.isnot(None),
            )
            .order_by(ServiceDiscountRecommendation.decided_at.desc())
            .limit(20)
        )
    ).scalars().all()

    out: list[ServiceDiscountRecAnalyticsPoint] = []
    for rec in approved:
        decided = rec.decided_at
        if decided.tzinfo is None:
            decided = decided.replace(tzinfo=timezone.utc)
        before_from = decided - timedelta(days=30)
        after_to = min(now, decided + timedelta(days=30))
        appts = (
            await db.execute(
                select(Appointment).where(
                    Appointment.tenant_id == tenant_id,
                    Appointment.service_id == rec.service_id,
                    Appointment.start_time >= before_from,
                    Appointment.start_time <= after_to,
                    Appointment.status.in_(["completed", "confirmed", "in_progress", "pending"]),
                )
            )
        ).scalars().all()
        before_b = after_b = 0
        before_r = after_r = 0.0
        for a in appts:
            if a.start_time < decided:
                before_b += 1
                before_r += float(a.total_price or 0)
            else:
                after_b += 1
                after_r += float(a.total_price or 0)
        growth = ((after_b - before_b) / before_b * 100) if before_b > 0 else (100.0 if after_b else 0.0)
        out.append(ServiceDiscountRecAnalyticsPoint(
            service_id=rec.service_id,
            service_name=rec.service.name if rec.service else f"#{rec.service_id}",
            before_bookings=before_b,
            after_bookings=after_b,
            bookings_growth_percent=round(growth, 1),
            before_revenue=round(before_r, 2),
            after_revenue=round(after_r, 2),
            revenue_delta=round(after_r - before_r, 2),
        ))
    return out


@app.get("/api/analytics/service-discount-recs", response_model=ServiceDiscountRecsResponse)
async def get_service_discount_recs(
    force: bool = Query(False, description="Принудительный пересчёт"),
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Рекомендации скидок по услугам. Авто-обновление раз в неделю."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    auto_refreshed = False

    latest = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
            .order_by(ServiceDiscountRecommendation.computed_at.desc())
            .limit(1)
        )
    ).scalar_one_or_none()

    need_refresh = force or latest is None
    if latest and latest.computed_at:
        computed = latest.computed_at
        if computed.tzinfo is None:
            computed = computed.replace(tzinfo=timezone.utc)
        if now - computed >= timedelta(days=7):
            need_refresh = True

    if need_refresh:
        await _compute_service_discount_recs(db, tenant_id)
        auto_refreshed = True
        latest = (
            await db.execute(
                select(ServiceDiscountRecommendation)
                .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
                .order_by(ServiceDiscountRecommendation.computed_at.desc())
                .limit(1)
            )
        ).scalar_one_or_none()

    rows = (
        await db.execute(
            select(ServiceDiscountRecommendation)
            .options(selectinload(ServiceDiscountRecommendation.service))
            .where(ServiceDiscountRecommendation.tenant_id == tenant_id)
            .order_by(
                ServiceDiscountRecommendation.status.asc(),
                ServiceDiscountRecommendation.priority.desc(),
            )
        )
    ).scalars().all()

    last_at = latest.computed_at if latest else None
    next_at = (last_at + timedelta(days=7)) if last_at else now
    analytics = await _rec_analytics(db, tenant_id)

    return ServiceDiscountRecsResponse(
        last_computed_at=last_at,
        next_refresh_at=next_at,
        auto_refreshed=auto_refreshed,
        items=[_rec_to_out(r) for r in rows],
        analytics=analytics,
    )


@app.post("/api/analytics/service-discount-recs/refresh", response_model=ServiceDiscountRecsResponse)
async def refresh_service_discount_recs(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Принудительный пересчёт рекомендаций."""
    return await get_service_discount_recs(force=True, current_user=current_user, db=db)


@app.post("/api/analytics/service-discount-recs/{rec_id}/decide", response_model=ServiceDiscountRecOut)
async def decide_service_discount_rec(
    rec_id: int,
    body: ServiceDiscountRecDecision,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Утвердить / отклонить / скорректировать рекомендацию."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(ServiceDiscountRecommendation)
        .options(selectinload(ServiceDiscountRecommendation.service))
        .where(
            ServiceDiscountRecommendation.id == rec_id,
            ServiceDiscountRecommendation.tenant_id == tenant_id,
        )
    )
    rec = result.scalar_one_or_none()
    if not rec:
        raise HTTPException(status_code=404, detail="Рекомендация не найдена")
    if rec.status not in ("pending",):
        raise HTTPException(status_code=400, detail="Рекомендация уже обработана")

    action = (body.action or "").lower().strip()
    now = datetime.now(timezone.utc)

    if action == "reject":
        rec.status = "rejected"
        rec.decided_at = now
        await db.commit()
        await db.refresh(rec)
        return _rec_to_out(rec)

    if action not in ("approve", "adjust"):
        raise HTTPException(status_code=400, detail="action: approve | reject | adjust")

    percent = body.adjusted_percent if action == "adjust" and body.adjusted_percent else rec.suggested_percent
    if action == "adjust":
        if not body.adjusted_percent:
            raise HTTPException(status_code=400, detail="Укажите adjusted_percent")
        rec.adjusted_percent = percent
        rec.status = "adjusted"
    else:
        rec.status = "approved"

    svc_name = rec.service.name if rec.service else f"Услуга #{rec.service_id}"
    rule_name = f"Скидка на услугу: {svc_name} (−{percent}%)"
    # уникальное имя
    exists = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id, DiscountRule.name == rule_name)
    )
    if exists.scalar_one_or_none():
        rule_name = f"{rule_name} · {now.strftime('%d.%m')}"

    rule = DiscountRule(
        name=rule_name,
        type="service",
        conditions={
            "source": "service_margin_rec",
            "rec_id": rec.id,
            "priority": rec.priority,
            "scenario": rec.scenario,
        },
        discount_percent=percent,
        service_id=rec.service_id,
        is_active=True,
        tenant_id=tenant_id,
    )
    db.add(rule)
    await db.flush()
    rec.discount_rule_id = rule.id
    rec.decided_at = now
    await db.commit()

    result = await db.execute(
        select(ServiceDiscountRecommendation)
        .options(selectinload(ServiceDiscountRecommendation.service))
        .where(ServiceDiscountRecommendation.id == rec.id)
    )
    rec = result.scalar_one()
    return _rec_to_out(rec)


# =============================================================================
# DISCOUNTS & LOYALTY (list CRUD continues below if not already)
# =============================================================================


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
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(DiscountRule.tenant_id == UUID(current_user["tenant_id"]))
        .order_by(DiscountRule.created_at.desc())
    )
    items, total = await _paginate(db, stmt, skip=skip, limit=limit)
    return {
        "items": [_discount_rule_to_out(r) for r in items],
        "total": total,
        "skip": skip,
        "limit": limit,
    }


@app.post("/api/discounts", response_model=DiscountRuleOut)
async def create_discount_rule(
    request: DiscountRuleCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новое правило скидки."""
    tenant_id = UUID(current_user["tenant_id"])

    # Проверка на дубликат по имени
    existing = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.name == request.name,
        )
    )
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=400, detail=f"Скидка с названием «{request.name}» уже существует")

    slot_start = _parse_time_str(request.slot_start)
    slot_end = _parse_time_str(request.slot_end)
    valid_until = _parse_date_str(request.valid_until)

    rule = DiscountRule(
        name=request.name,
        type=request.type,
        conditions=request.conditions or {},
        discount_percent=request.discount_percent,
        slot_start=slot_start,
        slot_end=slot_end,
        service_id=request.service_id,
        client_id=request.client_id,
        valid_until=valid_until,
        is_active=request.is_active if request.is_active is not None else True,
        tenant_id=tenant_id,
    )
    try:
        db.add(rule)
        await db.commit()
        result = await db.execute(
            select(DiscountRule)
            .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
            .where(DiscountRule.id == rule.id)
        )
        rule = result.scalar_one()
        # Уведомление — не должно ломать создание скидки
        try:
            await _notify_discount_created(db, rule, current_user)
        except Exception as notify_err:
            print(f"[WARN] Notification failed: {notify_err}")
        return _discount_rule_to_out(rule)
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        print(f"[ERROR] Create discount failed: {e}")
        raise HTTPException(status_code=400, detail=str(e))


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
    if "slot_start" in update_data:
        update_data["slot_start"] = _parse_time_str(update_data["slot_start"])
    if "slot_end" in update_data:
        update_data["slot_end"] = _parse_time_str(update_data["slot_end"])
    if "valid_until" in update_data:
        update_data["valid_until"] = _parse_date_str(update_data["valid_until"])

    for key, value in update_data.items():
        setattr(rule, key, value)

    await db.commit()
    # Reload with relations
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(DiscountRule.id == rule.id)
    )
    rule = result.scalar_one()
    return _discount_rule_to_out(rule)


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
    try:
        await db.delete(rule)
        await db.commit()
    except Exception as e:
        await db.rollback()
        raise HTTPException(
            status_code=400,
            detail=f"Не удалось удалить правило «{name}»: {str(e)}",
        )
    return {"message": f"Правило скидки «{name}» удалено"}


# ========== LOYALTY POINTS ==========

@app.get("/api/loyalty/points")
async def get_loyalty_points(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
    client_id: int | None = Query(None, description="Фильтр по ID клиента (возвращает одного)"),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
):
    """Получить баланс баллов клиентов."""
    tenant_id = UUID(current_user["tenant_id"])

    if client_id is not None:
        # Один конкретный клиент — ищем его баллы напрямую
        points_result = await db.execute(
            select(LoyaltyPoints).where(
                LoyaltyPoints.client_id == client_id,
                LoyaltyPoints.tenant_id == tenant_id,
            )
        )
        lp = points_result.scalar_one_or_none()
        user_result = await db.execute(
            select(User).where(User.id == client_id, User.tenant_id == tenant_id)
        )
        user = user_result.scalar_one_or_none()
        if not user:
            return {"items": [], "total": 0}

        return {
            "items": [LoyaltyPointsSummary(
                client_id=user.id,
                full_name=user.full_name,
                phone=user.phone,
                balance=lp.balance if lp else 0,
                total_earned=lp.total_earned if lp else 0,
                total_spent=lp.total_spent if lp else 0,
            )],
            "total": 1,
        }

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
        return {"items": [], "total": 0}

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


# ========== SEGMENT HELPER ==========

async def _get_client_segment(client_id: int, tenant_id: UUID, db: AsyncSession) -> str:
    """Определить RFM-сегмент клиента."""
    now = datetime.now(timezone.utc)

    # Все завершённые записи клиента
    appts_result = await db.execute(
        select(Appointment).where(
            Appointment.client_id == client_id,
            Appointment.tenant_id == tenant_id,
            Appointment.status == "completed",
        ).order_by(Appointment.start_time)
    )
    appts = appts_result.scalars().all()

    freq = len(appts)
    monetary = sum(float(a.total_price or 0) for a in appts)

    recency = 999
    if appts:
        last = max(a.start_time for a in appts)
        recency = (now - last).days if last else 999

    if freq == 0:
        # Клиент без завершённых записей — новый
        return "new"
    elif recency <= 30 and freq > 10 and monetary > 100000:
        return "vip"
    elif recency <= 60 and freq > 5:
        return "loyal"
    elif freq == 1 and recency <= 30:
        return "new"
    elif 60 < recency <= 90:
        return "sleeping"
    elif recency > 90:
        return "lost"
    else:
        return "regular"


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
        print(f"[DEBUG][_auto_apply_discount] Appointment #{appointment_id} not found, skipping.")
        return

    now = datetime.now(timezone.utc)
    tenant_id = appointment.tenant_id

    print(f"[DEBUG][_auto_apply_discount] Appointment #{appointment_id}: "
          f"service_id={appointment.service_id}, "
          f"total_price={appointment.total_price}, "
          f"client_id={appointment.client_id}, "
          f"start_time={appointment.start_time}")

    # Загружаем активные правила скидок (непросроченные)
    rules_result = await db.execute(
        select(DiscountRule).where(
            DiscountRule.tenant_id == tenant_id,
            DiscountRule.is_active == True,
            (DiscountRule.valid_until == None) | (DiscountRule.valid_until >= now),
        )
    )
    rules = rules_result.scalars().all()

    print(f"[DEBUG][_auto_apply_discount] Found {len(rules)} active/valid rules for tenant_id={tenant_id}")

    best_discount = 0
    best_rule = None

    for rule in rules:
        conditions = rule.conditions or {}
        print(f"[DEBUG][_auto_apply_discount] Checking rule id={rule.id}, name='{rule.name}', "
              f"type={rule.type}, service_id={rule.service_id}, "
              f"discount={rule.discount_percent}%, "
              f"valid_until={rule.valid_until}")

        if rule.type == "happy_hours":
            # Скидка на часовой слот (например, 14:00–16:00)
            if not rule.slot_start or not rule.slot_end:
                continue

            appt_time = appointment.start_time
            if not appt_time:
                continue

            # Извлекаем время записи (часы:минуты)
            appt_slot = appt_time.time()

            # Проверяем, попадает ли время записи в слот
            # Обработка случая, когда слот переходит через полночь (не типично, но на всякий)
            slot_active = False
            if rule.slot_start <= rule.slot_end:
                slot_active = rule.slot_start <= appt_slot <= rule.slot_end
            else:
                # Слот переходит через полночь (например, 22:00–02:00)
                slot_active = appt_slot >= rule.slot_start or appt_slot <= rule.slot_end

            # Дни недели из conditions.weekdays (0=Пн…6=Вс); по умолчанию будни
            allowed_days = conditions.get("weekdays")
            if not isinstance(allowed_days, list) or not allowed_days:
                allowed_days = [0, 1, 2, 3, 4]

            if slot_active and appt_time.weekday() in allowed_days:
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

        elif rule.type == "service":
            # Скидка на конкретную услугу
            if rule.service_id and rule.service_id == appointment.service_id:
                print(f"[DEBUG][_auto_apply_discount]  → service MATCH! rule.service_id={rule.service_id} == appointment.service_id={appointment.service_id}")
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule
            else:
                print(f"[DEBUG][_auto_apply_discount]  → service MISMATCH: rule.service_id={rule.service_id} vs appointment.service_id={appointment.service_id}")

        elif rule.type == "client":
            # Персональная скидка для клиента
            if rule.client_id and rule.client_id == appointment.client_id:
                if rule.discount_percent > best_discount:
                    best_discount = rule.discount_percent
                    best_rule = rule

        elif rule.type == "segment":
            # Скидка по RFM-сегменту (например, {"segment": "vip"})
            target_segment = conditions.get("segment", "")
            if target_segment:
                client_seg = await _get_client_segment(appointment.client_id, tenant_id, db)
                if client_seg == target_segment:
                    if rule.discount_percent > best_discount:
                        best_discount = rule.discount_percent
                        best_rule = rule
        elif rule.type == "cashback":
            # Кэшбек начисляется при завершении, не при создании — пропускаем
            continue

    if best_rule and best_discount > 0:
        original_price = float(appointment.total_price)
        # Защита минимальной цены (из conditions: {"min_price": 500})
        raw_conditions = best_rule.conditions or {}
        if isinstance(raw_conditions, str):
            import json
            raw_conditions = json.loads(raw_conditions)
        min_price = float(raw_conditions.get("min_price", 0))
        max_discount = max(0, original_price - min_price)
        effective_discount = min(
            round(original_price * best_discount / 100, 2),
            max_discount,
        )
        appointment.discount_applied = effective_discount
        appointment.total_price = original_price - effective_discount
        cd = ClientDiscount(
            tenant_id=tenant_id,
            client_id=appointment.client_id,
            discount_rule_id=best_rule.id,
            appointment_id=appointment.id,
            applied_percent=best_discount,
            applied_amount=effective_discount,
            is_used=True,
        )
        db.add(cd)
        await db.commit()
        print(f"[DEBUG][_auto_apply_discount] ✓ Applied discount rule #{best_rule.id} '{best_rule.name}': "
              f"{best_discount}% → {effective_discount} руб. "
              f"Price: {original_price} → {appointment.total_price}")
    else:
        print(f"[DEBUG][_auto_apply_discount] ✗ No applicable discount found "
              f"(best_rule={best_rule}, best_discount={best_discount})")


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


# ========== BOXES ==========

@app.get("/api/boxes", response_model=list[BoxOut])
async def get_boxes(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Список всех боксов/зон тенанта."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Box).where(Box.tenant_id == tenant_id)
        .order_by(Box.sort_order, Box.name)
    )
    boxes = result.scalars().all()

    # Загружаем привязки услуг для всех боксов
    box_ids = [b.id for b in boxes]
    box_services_map: dict[int, list[int]] = {}
    if box_ids:
        bs_result = await db.execute(
            select(BoxService).where(
                BoxService.box_id.in_(box_ids),
                BoxService.tenant_id == tenant_id,
            )
        )
        for bs in bs_result.scalars().all():
            box_services_map.setdefault(bs.box_id, []).append(bs.service_id)

    out = []
    for b in boxes:
        bo = BoxOut.model_validate(b)
        bo.service_ids = box_services_map.get(b.id, [])
        out.append(bo)
    return out


@app.post("/api/boxes", response_model=BoxOut)
async def create_box(
    request: BoxCreate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Создать новый бокс/зону."""
    tenant_id = UUID(current_user["tenant_id"])
    box = Box(
        name=request.name,
        color=request.color,
        sort_order=request.sort_order,
        is_active=request.is_active,
        tenant_id=tenant_id,
    )
    db.add(box)
    await db.commit()
    await db.refresh(box)

    # Привязываем услуги, если указаны
    if request.service_ids:
        for sid in request.service_ids:
            db.add(BoxService(box_id=box.id, service_id=sid, tenant_id=tenant_id))
        await db.commit()

    bo = BoxOut.model_validate(box)
    bo.service_ids = request.service_ids or []
    return bo


@app.put("/api/boxes/{box_id}", response_model=BoxOut)
async def update_box(
    box_id: int,
    request: BoxUpdate,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Обновить бокс/зону."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Box).where(Box.id == box_id, Box.tenant_id == tenant_id)
    )
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=404, detail="Бокс не найден")

    update_data = request.model_dump(exclude_unset=True)
    # Обрабатываем service_ids отдельно
    service_ids = update_data.pop("service_ids", None)

    for key, value in update_data.items():
        setattr(box, key, value)

    # Обновляем привязку услуг
    if service_ids is not None:
        # Удаляем старые
        await db.execute(
            BoxService.__table__.delete().where(
                BoxService.box_id == box_id,
                BoxService.tenant_id == tenant_id,
            )
        )
        # Добавляем новые
        for sid in service_ids:
            db.add(BoxService(box_id=box_id, service_id=sid, tenant_id=tenant_id))

    await db.commit()
    await db.refresh(box)

    # Загружаем итоговые service_ids
    bs_result = await db.execute(
        select(BoxService).where(
            BoxService.box_id == box_id,
            BoxService.tenant_id == tenant_id,
        )
    )
    bo = BoxOut.model_validate(box)
    bo.service_ids = [bs.service_id for bs in bs_result.scalars().all()]
    return bo


@app.delete("/api/boxes/{box_id}")
async def delete_box(
    box_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Удалить бокс/зону."""
    result = await db.execute(
        select(Box).where(Box.id == box_id, Box.tenant_id == UUID(current_user["tenant_id"]))
    )
    box = result.scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=404, detail="Бокс не найден")

    # Сбросить box_id у связанных записей
    await db.execute(
        update(Appointment).where(Appointment.box_id == box_id).values(box_id=None)
    )
    await db.delete(box)
    await db.commit()
    return {"message": f"Бокс «{box.name}» удалён"}


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
    service_id: int | None = None,
    description: str | None = None,
) -> PhotoCreateResponse:
    """Validate, save and create Photo record."""
    contents = await file.read()
    mime = validate_image(contents, file.filename or "image.jpg")
    filename = generate_filename(file.filename or "image.jpg")
    subdir = f"{entity_type}s/{entity_id or 'unknown'}"
    url, thumb_url = save_file_local(contents, subdir, filename)

    photo_data = {
        "tenant_id": tenant_id,
        "entity_type": entity_type,
        "url": url,
        "thumbnail_url": thumb_url,
        "title": title or file.filename,
        "description": description,
        "service_id": service_id,
        "file_size": len(contents),
        "mime_type": mime,
        "uploaded_by_id": uploaded_by_id,
    }
    # entity_field может совпадать с uploaded_by_id (портфолио) — избегаем дубликата
    if entity_field != "uploaded_by_id":
        photo_data[entity_field] = entity_id
    photo = Photo(**photo_data)
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
    service_id: int | None = Query(None, description="ID услуги, к которой относится фото"),
    description: str | None = Query(None, description="Описание работы (было → стало)"),
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Загрузить фото в портфолио мастера с привязкой к услуге."""
    # Если указан service_id — проверяем, что услуга существует
    if service_id is not None:
        srv_result = await db.execute(
            select(Service).where(
                Service.id == service_id,
                Service.tenant_id == UUID(current_user["tenant_id"]),
            )
        )
        if not srv_result.scalar_one_or_none():
            raise HTTPException(status_code=404, detail="Услуга не найдена")

    return await _save_uploaded_photo(
        db, file, UUID(current_user["tenant_id"]), "portfolio", "uploaded_by_id", current_user["id"],
        current_user["id"], title=title, service_id=service_id, description=description,
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

    # Для портфолио подгружаем связи с услугой и загрузчиком
    query = select(Photo).where(
        filter_col == entity_id,
        Photo.tenant_id == UUID(current_user["tenant_id"]),
        Photo.entity_type == entity_type,
    )
    if entity_type == "portfolio":
        query = query.options(
            selectinload(Photo.service),
            selectinload(Photo.uploader),
        )
    result = await db.execute(query.order_by(Photo.sort_order, Photo.created_at.desc()))
    photos = result.scalars().all()

    # Обогащаем ответ именами для портфолио
    result_list = []
    for p in photos:
        po = PhotoOut.model_validate(p)
        if entity_type == "portfolio":
            po.service_name = p.service.name if p.service else None
            po.uploader_name = p.uploader.full_name if p.uploader else None
        result_list.append(po)
    return result_list


@app.get("/api/portfolio", response_model=list[PhotoOut])
async def get_all_portfolio(
    service_id: int | None = Query(None, description="Фильтр по услуге"),
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить все портфолио-фото салона (с фильтром по услуге)."""
    tenant_id = UUID(current_user["tenant_id"])
    query = (
        select(Photo)
        .options(selectinload(Photo.service), selectinload(Photo.uploader))
        .where(
            Photo.tenant_id == tenant_id,
            Photo.entity_type == "portfolio",
        )
    )
    if service_id is not None:
        query = query.where(Photo.service_id == service_id)

    result = await db.execute(query.order_by(Photo.created_at.desc()))
    photos = result.scalars().all()

    result_list = []
    for p in photos:
        po = PhotoOut.model_validate(p)
        po.service_name = p.service.name if p.service else None
        po.uploader_name = p.uploader.full_name if p.uploader else None
        result_list.append(po)
    return result_list


@app.get("/api/portfolio/services", response_model=list[dict])
async def get_portfolio_services(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """Получить список услуг, по которым есть фото в портфолио."""
    tenant_id = UUID(current_user["tenant_id"])
    result = await db.execute(
        select(Photo.service_id, func.count(Photo.id).label("photo_count"))
        .where(
            Photo.tenant_id == tenant_id,
            Photo.entity_type == "portfolio",
            Photo.service_id.isnot(None),
        )
        .group_by(Photo.service_id)
        .order_by(func.count(Photo.id).desc())
    )
    rows = result.all()
    service_ids = [r.service_id for r in rows if r.service_id]

    services_out = []
    if service_ids:
        srv_result = await db.execute(
            select(Service).where(Service.id.in_(service_ids))
        )
        srv_map = {s.id: s for s in srv_result.scalars().all()}
        for r in rows:
            srv = srv_map.get(r.service_id)
            services_out.append({
                "service_id": r.service_id,
                "service_name": srv.name if srv else f"Услуга #{r.service_id}",
                "photo_count": r.photo_count,
            })
    return services_out


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
    try:
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
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        traceback.print_exc()
        print(f"[ERROR] get_master_calendar({master_id}): {e}")
        raise HTTPException(status_code=500, detail=str(e))


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
    result = await db.execute(
        select(AppointmentHistory)
        .options(selectinload(AppointmentHistory.changed_by))
        .where(
            AppointmentHistory.id == history_id,
            AppointmentHistory.appointment_id == appointment_id,
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

    # --- 4. Прогноз на 3 месяца (скользящее среднее + тренд) ---
    forecast = []
    # Собираем общую выручку по месяцам (сумма по всем услугам)
    monthly_total: dict[str, float] = {}
    for a in appts:
        m = a.start_time.strftime("%Y-%m")
        monthly_total[m] = monthly_total.get(m, 0) + float(a.total_price or 0)

    if len(monthly_total) >= 3:
        sorted_months = sorted(monthly_total.keys())
        last_3 = sorted_months[-3:]

        # Средняя выручка за последние 3 месяца
        recent_revenues = [monthly_total[m] for m in last_3]
        avg_revenue = sum(recent_revenues) / len(recent_revenues)

        # Тренд: изменение между самым старым и самым новым месяцем из last_3
        if recent_revenues[0] > 0:
            trend = (recent_revenues[-1] - recent_revenues[0]) / recent_revenues[0]
        else:
            trend = 0.0

        # Уровень уверенности: чем больше данных, тем выше
        data_points = len(monthly_total)
        if data_points >= 6:
            confidence_width = 0.2  # ±20%
        elif data_points >= 4:
            confidence_width = 0.3  # ±30%
        else:
            confidence_width = 0.4  # ±40%

        # Прогноз на 3 месяца вперёд
        last_month_dt = datetime.strptime(sorted_months[-1] + "-01", "%Y-%m-%d")
        for i in range(1, 4):
            next_m = (last_month_dt + timedelta(days=32 * i)).strftime("%Y-%m")
            # Прогноз: среднее * (1 + тренд)^i (экспоненциальное сглаживание)
            projected = avg_revenue * ((1 + trend) ** i)
            forecast.append(ForecastPoint(
                month=next_m,
                forecast=round(projected, 2),
                lower_bound=round(projected * (1 - confidence_width), 2),
                upper_bound=round(projected * (1 + confidence_width), 2),
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


# =============================================================================
# DISCOUNT HELPERS & EXTENDED ENDPOINTS
# =============================================================================

def _parse_date_str(value: str | None):
    """Convert 'YYYY-MM-DD' string to timezone-aware datetime (end of day UTC) or None.

    Ensures the discount remains valid for the entire specified day regardless
    of the server's local timezone offset.
    """
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
        if dt.tzinfo is None:
            # Treat as a date-only → end of day UTC so the discount lasts the full day
            dt = dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
        return dt
    except (ValueError, TypeError):
        return None


async def _notify_discount_created(db: AsyncSession, rule, admin_user: dict):
    """Send notification about a new discount to relevant clients."""
    from app.core.notification_service import create_notification

    tenant_id = rule.tenant_id
    now = datetime.now(timezone.utc)

    # Собираем получателей
    recipient_ids = []

    if rule.client_id:
        # Персональная скидка — только этому клиенту
        recipient_ids = [rule.client_id]
    elif rule.service_id:
        # Скидка на услугу — всем, кто её заказывал
        appt_result = await db.execute(
            select(Appointment.client_id)
            .where(
                Appointment.service_id == rule.service_id,
                Appointment.tenant_id == tenant_id,
                Appointment.status == "completed",
            )
            .distinct()
        )
        recipient_ids = [r[0] for r in appt_result.all()]
    else:
        # Общая скидка — всем клиентам
        user_result = await db.execute(
            select(User.id).where(
                User.role == "client",
                User.tenant_id == tenant_id,
            )
        )
        recipient_ids = [r[0] for r in user_result.all()]

    # Лимит на число уведомлений (не спамим)
    for uid in recipient_ids[:50]:
        await create_notification(
            db=db,
            user_id=uid,
            tenant_id=tenant_id,
            type="promo",
            channel="in_app",
            title=f"🎉 Новая скидка: {rule.name}",
            message=f"Скидка {rule.discount_percent}% на услуги салона. "
                    f"Действует до {rule.valid_until.strftime('%d.%m.%Y') if rule.valid_until else 'отдельного уведомления'}.",
            related_entity_type="discount",
            related_entity_id=rule.id,
        )


# ===== DISCOUNT BY SERVICE =====

@app.get("/api/discounts/by-service/{service_id}", response_model=list[dict])
async def get_discounts_by_service(
    service_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить скидки для конкретной услуги."""
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
            DiscountRule.service_id == service_id,
            DiscountRule.is_active == True,
        )
        .order_by(DiscountRule.created_at.desc())
    )
    return [_discount_rule_to_out(r) for r in result.scalars().all()]


# ===== DISCOUNT BY CLIENT =====

@app.get("/api/discounts/by-client/{client_id}", response_model=list[dict])
async def get_discounts_by_client(
    client_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить персональные скидки для клиента."""
    result = await db.execute(
        select(DiscountRule)
        .options(selectinload(DiscountRule.service), selectinload(DiscountRule.client))
        .where(
            DiscountRule.tenant_id == UUID(current_user["tenant_id"]),
            DiscountRule.client_id == client_id,
            DiscountRule.is_active == True,
        )
        .order_by(DiscountRule.created_at.desc())
    )
    return [_discount_rule_to_out(r) for r in result.scalars().all()]


# ===== DISCOUNT ANALYTICS =====

@app.get("/api/discounts/analytics")
async def get_discount_analytics(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Аналитика эффективности скидок."""
    tenant_id = UUID(current_user["tenant_id"])
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Все правила скидок
    rules_result = await db.execute(
        select(DiscountRule).where(DiscountRule.tenant_id == tenant_id)
    )
    rules = rules_result.scalars().all()

    # Все применения скидок (ClientDiscount)
    cd_result = await db.execute(
        select(ClientDiscount)
        .options(selectinload(ClientDiscount.discount_rule))
        .where(
            ClientDiscount.tenant_id == tenant_id,
            ClientDiscount.is_used == True,
        )
    )
    client_discounts = cd_result.scalars().all()

    # Статистика по каждому правилу
    rule_stats = {}
    for cd in client_discounts:
        rule_id = cd.discount_rule_id
        if rule_id not in rule_stats:
            rule_stats[rule_id] = {
                "count": 0,
                "total_discount_amount": 0.0,
                "total_original_price": 0.0,
            }
        rule_stats[rule_id]["count"] += 1
        rule_stats[rule_id]["total_discount_amount"] += float(cd.applied_amount or 0)

        # Ищем оригинальную цену в appointment
        if cd.appointment_id:
            appt_result = await db.execute(
                select(Appointment).where(Appointment.id == cd.appointment_id)
            )
            appt = appt_result.scalar_one_or_none()
            if appt:
                original = float(appt.total_price or 0) + float(appt.discount_applied or 0)
                rule_stats[rule_id]["total_original_price"] += original

    # Собираем результат
    analytics = []
    for rule in rules:
        stats = rule_stats.get(rule.id, {"count": 0, "total_discount_amount": 0.0, "total_original_price": 0.0})
        roi = 0
        if stats["total_discount_amount"] > 0:
            roi = round(
                (stats["total_original_price"] - stats["total_discount_amount"]) / stats["total_discount_amount"] * 100,
                1,
            ) if stats["total_discount_amount"] else 0

        analytics.append({
            "rule_id": rule.id,
            "rule_name": rule.name,
            "rule_type": rule.type,
            "discount_percent": rule.discount_percent,
            "is_active": rule.is_active,
            "usage_count": stats["count"],
            "total_discount_amount": round(stats["total_discount_amount"], 2),
            "total_original_price": round(stats["total_original_price"], 2),
            "roi_percent": roi,
        })

    # Общая статистика
    total_used = sum(a["usage_count"] for a in analytics)
    total_discounted = sum(a["total_discount_amount"] for a in analytics)

    return {
        "rules": analytics,
        "summary": {
            "total_rules": len(rules),
            "active_rules": sum(1 for r in rules if r.is_active),
            "total_discount_uses": total_used,
            "total_discount_amount": round(total_discounted, 2),
        },
    }
