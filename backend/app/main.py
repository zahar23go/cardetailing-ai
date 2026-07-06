"""
CarDetailing AI — Main Application.

FastAPI entry point with database-backed authentication.
"""

from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.core.database import get_db, init_db
from app.core.deepseek_client import get_ai_response
from app.models import User, UserRole, AppointmentStatus, Service, Car, Appointment

app = FastAPI(title="CarDetailing AI", version="1.0.0")

# ========== CORS ==========
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ========== JWT ==========
SECRET_KEY = "supersecretjwtkeychangeit"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1440

security = HTTPBearer()

# ========== HELPERS ==========
def _hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode("utf-8"), salt).decode("utf-8")

def _verify_password(plain: str, hashed: str) -> bool:
    return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

def _create_token(user_id: int) -> str:
    expire = datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    payload = {"sub": str(user_id), "exp": expire}
    return jwt.encode(payload, SECRET_KEY, algorithm=ALGORITHM)

async def _get_current_user(
    credentials: HTTPAuthorizationCredentials = Depends(security),
    db: AsyncSession = Depends(get_db),
) -> dict:
    token = credentials.credentials
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        user_id = int(payload.get("sub"))
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

# ========== STARTUP ==========
@app.on_event("startup")
async def on_startup():
    await init_db()
    # Используем async for для получения сессии
    async for db in get_db():
        result = await db.execute(select(User).where(User.role == "super_admin"))
        if not result.scalar_one_or_none():
            super_admin = User(
                phone="+79999999999",
                password=_hash_password("admin123"),
                full_name="Супер Администратор",
                role="super_admin",
            )
            db.add(super_admin)
            await db.commit()
            print("[OK] Super-admin created (phone: +79999999999, password: admin123)")
        else:
            print("[OK] Super-admin already exists")
        break

# ========== HEALTH ==========
@app.get("/health")
async def health_check():
    return {"status": "healthy", "message": "CarDetailing AI is running!"}

# ========== AUTH ==========
@app.post("/api/register")
async def register(request: dict, db: AsyncSession = Depends(get_db)):
    phone = request.get("phone")
    password = request.get("password")
    full_name = request.get("full_name")

    if not phone or not password or not full_name:
        raise HTTPException(status_code=400, detail="Все поля обязательны")

    result = await db.execute(select(User).where(User.phone == phone))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Пользователь уже существует")

    hashed = _hash_password(password)
    user = User(phone=phone, password=hashed, full_name=full_name, role="client")
    db.add(user)
    await db.commit()
    await db.refresh(user)

    token = _create_token(user.id)
    return {"token": token, "user": {"id": user.id, "phone": user.phone, "full_name": user.full_name, "role": user.role}}

@app.post("/api/login")
async def login(request: dict, db: AsyncSession = Depends(get_db)):
    phone = request.get("phone")
    password = request.get("password")

    if not phone or not password:
        raise HTTPException(status_code=400, detail="Телефон и пароль обязательны")

    result = await db.execute(select(User).where(User.phone == phone))
    user = result.scalar_one_or_none()
    if not user or not _verify_password(password, user.password):
        raise HTTPException(status_code=401, detail="Неверный телефон или пароль")

    token = _create_token(user.id)
    return {"token": token, "user": {"id": user.id, "phone": user.phone, "full_name": user.full_name, "role": user.role}}

@app.get("/api/me")
async def get_me(current_user: dict = Depends(_get_current_user)):
    return current_user

# ========== SERVICES ==========
@app.get("/api/services")
async def get_services(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Service).where(Service.is_active == True))
    return result.scalars().all()

@app.post("/api/services")
async def create_service(
    request: dict,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    name = request.get("name")
    if not name:
        raise HTTPException(status_code=400, detail="name is required")

    service = Service(
        name=name,
        description=request.get("description"),
        category=request.get("category"),
        price=request.get("price", 0),
        duration=request.get("duration", 60),
        material_cost=request.get("material_cost", 0),
    )
    db.add(service)
    await db.commit()
    await db.refresh(service)
    return service

@app.put("/api/services/{service_id}")
async def update_service(
    service_id: int,
    request: dict,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    for key in ["name", "description", "category", "price", "duration", "material_cost", "is_active"]:
        if key in request:
            setattr(service, key, request[key])

    await db.commit()
    await db.refresh(service)
    return service

@app.delete("/api/services/{service_id}")
async def delete_service(
    service_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    await db.delete(service)
    await db.commit()
    return {"message": "Service deleted"}

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
        "status": appointment.status.value if appointment.status else None,
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
):
    result = await db.execute(
        select(Appointment)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.car),
            selectinload(Appointment.master),
        )
        .order_by(Appointment.start_time.desc())
    )
    return [_serialize_appointment(a) for a in result.scalars().all()]

@app.get("/api/appointments/me")
async def get_my_appointments(
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
        .where(Appointment.client_id == current_user["id"])
        .order_by(Appointment.start_time.desc())
    )
    return [_serialize_appointment(a) for a in result.scalars().all()]

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
        .where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")
    if appointment.client_id != current_user["id"] and current_user["role"] not in ["admin", "super_admin"]:
        raise HTTPException(status_code=403, detail="Access denied")
    return _serialize_appointment(appointment)

@app.post("/api/appointments")
async def create_appointment(
    request: dict,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db),
):
    service_id = request.get("service_id")
    car_id = request.get("car_id")
    start_time_str = request.get("start_time")

    if not all([service_id, car_id, start_time_str]):
        raise HTTPException(status_code=400, detail="service_id, car_id, start_time are required")

    # Проверка услуги
    result = await db.execute(select(Service).where(Service.id == service_id))
    service = result.scalar_one_or_none()
    if not service:
        raise HTTPException(status_code=404, detail="Service not found")

    # Проверка машины
    result = await db.execute(select(Car).where(Car.id == car_id, Car.client_id == current_user["id"]))
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Car not found")

    try:
        start_time = datetime.fromisoformat(start_time_str)
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid start_time format. Use ISO 8601")

    # Приводим к timezone-aware (UTC), т.к. колонки DateTime(timezone=True)
    if start_time.tzinfo is None:
        start_time = start_time.replace(tzinfo=timezone.utc)

    end_time = start_time + timedelta(minutes=service.duration)

    appointment = Appointment(
        client_id=current_user["id"],
        service_id=service_id,
        car_id=car_id,
        start_time=start_time,
        end_time=end_time,
        total_price=service.price,
        status=AppointmentStatus.pending,
        client_notes=request.get("notes") or request.get("client_notes"),
    )
    db.add(appointment)
    await db.commit()
    await db.refresh(appointment)

    # Загружаем связи, чтобы _serialize_appointment не упал с MissingGreenlet
    result = await db.execute(
        select(Appointment)
        .where(Appointment.id == appointment.id)
        .options(
            selectinload(Appointment.client),
            selectinload(Appointment.service),
            selectinload(Appointment.car),
            selectinload(Appointment.master),
        )
    )
    loaded = result.scalar_one()
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
    request: dict,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Appointment not found")

    status_value = request.get("status")
    if status_value:
        try:
            appointment.status = AppointmentStatus(status_value)
        except ValueError:
            raise HTTPException(status_code=400, detail="Invalid status")
    if "master_id" in request:
        appointment.master_id = request["master_id"]
    if "master_brief" in request:
        appointment.master_brief = request["master_brief"]

    await db.commit()
    # expire_on_commit=False → связи всё ещё загружены
    return _serialize_appointment(appointment)

# ========== MASTER ENDPOINTS ==========
@app.get("/api/masters/me/appointments")
async def get_my_master_appointments(
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Получить записи, назначенные текущему мастеру."""
    result = await db.execute(
        select(Appointment)
        .options(*_APPT_LOAD)
        .where(Appointment.master_id == current_user["id"])
        .order_by(Appointment.start_time.desc())
    )
    return [_serialize_appointment(a) for a in result.scalars().all()]


@app.put("/api/masters/me/appointments/{appointment_id}/status")
async def update_master_appointment_status(
    appointment_id: int,
    request: dict,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Сменить статус записи (master: in_progress → completed или confirmed → in_progress)."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    new_status = request.get("status")
    if not new_status:
        raise HTTPException(status_code=400, detail="status обязателен")

    # Разрешённые переходы для мастера
    valid_transitions = {
        "confirmed": ["in_progress"],
        "in_progress": ["completed"],
    }
    allowed = valid_transitions.get(appointment.status.value, [])
    if new_status not in allowed:
        raise HTTPException(
            status_code=400,
            detail=f"Нельзя сменить статус с '{appointment.status.value}' на '{new_status}'. "
                   f"Допустимо: {allowed}",
        )

    try:
        appointment.status = AppointmentStatus(new_status)
    except ValueError:
        raise HTTPException(status_code=400, detail="Недопустимый статус")

    await db.commit()
    return _serialize_appointment(appointment)


@app.put("/api/masters/me/appointments/{appointment_id}/notes")
async def update_master_appointment_notes(
    appointment_id: int,
    request: dict,
    current_user: dict = Depends(_require_master),
    db: AsyncSession = Depends(get_db),
):
    """Добавить/обновить заметку мастера по записи."""
    result = await db.execute(
        select(Appointment).options(*_APPT_LOAD).where(Appointment.id == appointment_id)
    )
    appointment = result.scalar_one_or_none()
    if not appointment:
        raise HTTPException(status_code=404, detail="Запись не найдена")

    if appointment.master_id != current_user["id"]:
        raise HTTPException(status_code=403, detail="Это не ваша запись")

    master_brief = request.get("master_brief") or request.get("notes")
    if master_brief is None:
        raise HTTPException(status_code=400, detail="master_brief или notes обязателен")

    appointment.master_brief = master_brief
    await db.commit()
    return _serialize_appointment(appointment)


# ========== USERS MANAGEMENT ==========
@app.get("/api/users")
async def get_users(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить список всех пользователей (только админ)"""
    result = await db.execute(select(User).order_by(User.role, User.full_name))
    users = result.scalars().all()
    return [
        {
            "id": u.id,
            "phone": u.phone,
            "full_name": u.full_name,
            "role": u.role,
            "created_at": u.created_at,
        }
        for u in users
    ]


@app.put("/api/users/{user_id}/role")
async def update_user_role(
    user_id: int,
    request: dict,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Изменить роль пользователя (только админ)"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    new_role = request.get("role")
    valid_roles = [e.value for e in UserRole]
    if new_role not in valid_roles:
        raise HTTPException(status_code=400, detail=f"Недопустимая роль. Доступно: {valid_roles}")

    user.role = UserRole(new_role)
    await db.commit()
    await db.refresh(user)
    return {
        "id": user.id,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role,
    }


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

    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    if user.role == "super_admin":
        raise HTTPException(status_code=400, detail="Нельзя удалить супер-администратора")

    full_name = user.full_name
    await db.delete(user)
    await db.commit()
    return {"message": f"Пользователь «{full_name}» удалён", "user_id": user_id}


@app.get("/api/users/{user_id}")
async def get_user_detail(
    user_id: int,
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Получить детальную карточку клиента с историей"""
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Пользователь не найден")

    appts_result = await db.execute(
        select(Appointment)
        .where(Appointment.client_id == user_id)
        .order_by(Appointment.start_time.desc())
    )
    appointments = appts_result.scalars().all()

    return {
        "id": user.id,
        "phone": user.phone,
        "full_name": user.full_name,
        "role": user.role,
        "created_at": user.created_at,
        "appointments_count": len(appointments),
        "total_spent": sum(
            float(a.total_price or 0) for a in appointments if a.status == "completed"
        ),
        "last_visit": appointments[0].start_time if appointments else None,
    }


# ========== ANALYTICS ==========
@app.get("/api/analytics/kpi")
async def get_kpi(
    current_user: dict = Depends(_require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Ключевые показатели для дашборда владельца"""
    now = datetime.now(timezone.utc)
    today_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    # Клиенты
    clients_result = await db.execute(select(User).where(User.role == "client"))
    total_clients = len(clients_result.scalars().all())

    # Мастера
    masters_result = await db.execute(select(User).where(User.role == "master"))
    total_masters = len(masters_result.scalars().all())

    # Записи сегодня
    today_result = await db.execute(
        select(Appointment).where(Appointment.start_time >= today_start)
    )
    today_appts = today_result.scalars().all()

    # Записи за месяц
    month_result = await db.execute(
        select(Appointment).where(Appointment.start_time >= month_start)
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
        select(Appointment).where(Appointment.status == "pending")
    )
    pending_count = len(pending_result.scalars().all())

    return {
        "total_clients": total_clients,
        "total_masters": total_masters,
        "today_appointments": len(today_appts),
        "today_revenue": today_revenue,
        "month_revenue": month_revenue,
        "pending_appointments": pending_count,
        "completed_month": sum(1 for a in month_appts if a.status == "completed"),
    }


# ========== AI ==========
@app.post("/api/ai/chat")
async def ai_chat(request: dict):
    user_message = request.get("message", "")
    if not user_message:
        raise HTTPException(status_code=400, detail="Сообщение не может быть пустым")
    response = get_ai_response(user_message)
    return {"response": response}

# ========== CARS ==========

@app.get("/api/cars")
async def get_cars(
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Получить все машины текущего пользователя"""
    result = await db.execute(
        select(Car).where(Car.client_id == current_user["id"])
    )
    cars = result.scalars().all()
    return cars

@app.post("/api/cars")
async def create_car(
    car_data: dict,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Создать новую машину для текущего пользователя"""
    new_car = Car(
        client_id=current_user["id"],
        make=car_data.get("make"),
        model=car_data.get("model"),
        year=car_data.get("year"),
        license_plate=car_data.get("license_plate"),
        color=car_data.get("color"),
        notes=car_data.get("notes")
    )
    db.add(new_car)
    await db.commit()
    await db.refresh(new_car)
    return new_car

@app.delete("/api/cars/{car_id}")
async def delete_car(
    car_id: int,
    current_user: dict = Depends(_get_current_user),
    db: AsyncSession = Depends(get_db)
):
    """Удалить машину (только свою)"""
    result = await db.execute(
        select(Car).where(Car.id == car_id, Car.client_id == current_user["id"])
    )
    car = result.scalar_one_or_none()
    if not car:
        raise HTTPException(status_code=404, detail="Машина не найдена")
    
    await db.delete(car)
    await db.commit()
    return {"message": "Машина удалена"}