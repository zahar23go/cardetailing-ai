"""
Seed script for CarDetailing AI.

Generates test data:
  - 7 clients (with 2-3 cars each)
  - 2 masters (plus reuses existing master ID=3)
  - 40 appointments over the last 3 months
  - 12 expenses

Run: python seed.py
      (from the backend/ directory with venv activated)

Uses existing models, tenant (00000000-0000-0000-0000-000000000001),
and existing services (IDs 4-13).
"""

import asyncio
import random
from datetime import datetime, timedelta, timezone
from decimal import Decimal
from uuid import UUID

import bcrypt

# Import all models so they register on Base.metadata
import app.models  # noqa: F401
from app.core.database import async_session_maker
from app.models import Tenant, User, Car, Service, Appointment, AppointmentStatus, Expense

# ---------------------------------------------------------------------------
# Constants
# ---------------------------------------------------------------------------
TENANT_ID = UUID("00000000-0000-0000-0000-000000000001")
TODAY = datetime.now(timezone.utc)
PASSWORD_HASH = bcrypt.hashpw(
    b"password123",
    bcrypt.gensalt(),
).decode("utf-8")

# Service IDs from existing data (IDs 4-13)
SERVICE_IDS = [4, 5, 6, 7, 8, 9, 10, 11, 12, 13]

# Statuses with realistic distribution weights
STATUS_WEIGHTS: dict[str, float] = {
    "completed": 0.45,
    "confirmed": 0.10,
    "in_progress": 0.08,
    "pending": 0.12,
    "cancelled": 0.20,
    "no_show": 0.05,
}

# ---------------------------------------------------------------------------
# Test data
# ---------------------------------------------------------------------------

CLIENTS = [
    {"full_name": "Иван Петров",        "phone": "79501234501", "cars": [("Toyota", "Camry", 2021, "А123ВВ777", "белый"),
                                                                          ("Hyundai", "Sonata", 2020, "А456ВВ777", "чёрный")]},
    {"full_name": "Мария Соколова",     "phone": "79501234502", "cars": [("Kia", "Rio", 2022, "В789ВВ777", "красный"),
                                                                          ("Volkswagen", "Polo", 2019, "В012ВВ777", "синий")]},
    {"full_name": "Алексей Кузнецов",   "phone": "79501234503", "cars": [("BMW", "X5", 2023, "Е345ВВ777", "чёрный"),
                                                                          ("Audi", "Q7", 2021, "Е678ВВ777", "серый"),
                                                                          ("Mercedes", "E200", 2020, "Е901ВВ777", "белый")]},
    {"full_name": "Елена Новикова",     "phone": "79501234504", "cars": [("Nissan", "Qashqai", 2022, "К123ВВ777", "синий"),
                                                                          ("Renault", "Duster", 2020, "К456ВВ777", "зелёный")]},
    {"full_name": "Дмитрий Волков",     "phone": "79501234505", "cars": [("Toyota", "Land Cruiser", 2023, "М789ВВ777", "белый"),
                                                                          ("Lexus", "RX350", 2021, "М012ВВ777", "серебро")]},
    {"full_name": "Ольга Белова",       "phone": "79501234506", "cars": [("Hyundai", "Creta", 2023, "Н345ВВ777", "белый"),
                                                                          ("Kia", "Sportage", 2021, "Н678ВВ777", "красный"),
                                                                          ("Mazda", "CX-5", 2020, "Н901ВВ777", "серый")]},
    {"full_name": "Сергей Морозов",     "phone": "79501234507", "cars": [("Lada", "Vesta", 2022, "О123ВВ777", "чёрный"),
                                                                          ("Skoda", "Octavia", 2021, "О456ВВ777", "синий")]},
]

MASTERS = [
    {"full_name": "Андрей Смирнов",   "phone": "79501234550"},
    {"full_name": "Максим Орлов",     "phone": "79501234551"},
]

EXPENSES = [
    {"name": "Аренда помещения",          "amount": 80000,  "category": "rent",      "notes": "Июль 2026"},
    {"name": "Аренда помещения",          "amount": 80000,  "category": "rent",      "notes": "Июнь 2026"},
    {"name": "Аренда помещения",          "amount": 80000,  "category": "rent",      "notes": "Май 2026"},
    {"name": "Зарплата мастерам",         "amount": 150000, "category": "salary",    "notes": "Июль 2026"},
    {"name": "Зарплата мастерам",         "amount": 140000, "category": "salary",    "notes": "Июнь 2026"},
    {"name": "Зарплата мастерам",         "amount": 145000, "category": "salary",    "notes": "Май 2026"},
    {"name": "Коммунальные услуги",       "amount": 15000,  "category": "utilities", "notes": "Электричество, вода"},
    {"name": "Интернет и связь",          "amount": 5000,   "category": "utilities", "notes": ""},
    {"name": "Яндекс.Директ",             "amount": 25000,  "category": "marketing", "notes": "Реклама в поиске"},
    {"name": "Таргет в Instagram",        "amount": 15000,  "category": "marketing", "notes": "Продвижение постов"},
    {"name": "Закуп автохимии",           "amount": 30000,  "category": "supplies",  "notes": "Шампуни, полироли"},
    {"name": "Расходники (салфетки и пр.)", "amount": 10000, "category": "supplies", "notes": "Микрофибра, скотч"},
]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _pick_status() -> str:
    """Pick a status respecting distribution weights."""
    values, weights = zip(*STATUS_WEIGHTS.items())
    return random.choices(values, weights=weights, k=1)[0]


def _random_datetime_3months() -> datetime:
    """Return a random datetime within the last 3 months (9:00-18:00 on weekdays)."""
    days_ago = random.randint(0, 90)
    date = TODAY - timedelta(days=days_ago)
    # Skip weekends occasionally? Keep it simple — allow any day but working hours
    hour = random.randint(9, 17)
    minute = random.choice([0, 15, 30, 45])
    return date.replace(hour=hour, minute=minute, second=0, microsecond=0)


# ---------------------------------------------------------------------------
# Main seed logic
# ---------------------------------------------------------------------------

async def seed() -> None:
    print("=" * 60)
    print("  CarDetailing AI — Seed Script")
    print("=" * 60)

    async with async_session_maker() as session:
        # ---- Verify tenant exists ----
        tenant = await session.get(Tenant, TENANT_ID)
        if not tenant:
            print("[SKIP] Default tenant not found. Have you run init_db / migrations?")
            return

        # ---- Load existing services ----
        from sqlalchemy import select as sa_select
        result = await session.execute(sa_select(Service).where(Service.tenant_id == TENANT_ID))
        services = result.scalars().all()
        if not services:
            print("[SKIP] No services found. Seed services first.")
            return
        print(f"[OK] Found {len(services)} existing services")

        # ---- 1. Create masters ----
        master_ids = []
        # Reuse existing master ID=3
        existing_master = await session.get(User, 3)
        if existing_master and existing_master.role == "master":
            master_ids.append(existing_master.id)
            print(f"[OK] Reusing existing master: {existing_master.full_name} (id={existing_master.id})")
        else:
            # Create first master if ID=3 doesn't exist/is not master
            m1 = User(
                phone=MASTERS[0]["phone"],
                password=PASSWORD_HASH,
                full_name=MASTERS[0]["full_name"],
                role="master",
                tenant_id=TENANT_ID,
            )
            session.add(m1)
            await session.flush()
            master_ids.append(m1.id)
            print(f"[OK] Created master: {m1.full_name} (id={m1.id})")

        for m_data in MASTERS:
            # Check if phone already exists
            dup = await session.execute(
                sa_select(User).where(User.phone == m_data["phone"])
            )
            if dup.scalar_one_or_none():
                print(f"[SKIP] Master {m_data['full_name']} already exists (phone={m_data['phone']})")
                continue
            m = User(
                phone=m_data["phone"],
                password=PASSWORD_HASH,
                full_name=m_data["full_name"],
                role="master",
                tenant_id=TENANT_ID,
            )
            session.add(m)
            await session.flush()
            master_ids.append(m.id)
            print(f"[OK] Created master: {m.full_name} (id={m.id})")

        print(f"[OK] Total masters available: {len(master_ids)} — IDs: {master_ids}")

        # ---- 2. Create clients with cars ----
        client_ids = []
        # Reuse existing client ID=2 if role=client
        existing_client = await session.get(User, 2)
        if existing_client and existing_client.role == "client":
            client_ids.append(existing_client.id)
            print(f"[OK] Reusing existing client: {existing_client.full_name} (id={existing_client.id})")
            # Check their existing cars
            car_result = await session.execute(
                sa_select(Car).where(Car.client_id == existing_client.id)
            )
            existing_client_cars = car_result.scalars().all()
            if not existing_client_cars:
                # Give them at least one car
                c = Car(
                    client_id=existing_client.id,
                    make="Toyota",
                    model="Corolla",
                    year=2022,
                    license_plate="Х789ХХ777",
                    color="серый",
                    tenant_id=TENANT_ID,
                )
                session.add(c)
                await session.flush()
                print(f"[OK] Added car for {existing_client.full_name}: {c.make} {c.model} ({c.license_plate})")

        for cl_data in CLIENTS:
            # Check duplicate phone
            dup = await session.execute(
                sa_select(User).where(User.phone == cl_data["phone"])
            )
            if dup.scalar_one_or_none():
                print(f"[SKIP] Client {cl_data['full_name']} already exists (phone={cl_data['phone']})")
                # Still collect their ID
                result = await session.execute(
                    sa_select(User).where(User.phone == cl_data["phone"])
                )
                existing = result.scalar_one()
                client_ids.append(existing.id)
                continue

            user = User(
                phone=cl_data["phone"],
                password=PASSWORD_HASH,
                full_name=cl_data["full_name"],
                role="client",
                tenant_id=TENANT_ID,
            )
            session.add(user)
            await session.flush()
            client_ids.append(user.id)

            # Create cars
            for make, model, year, plate, color in cl_data["cars"]:
                car = Car(
                    client_id=user.id,
                    make=make,
                    model=model,
                    year=year,
                    license_plate=plate,
                    color=color,
                    tenant_id=TENANT_ID,
                )
                session.add(car)
                await session.flush()

            print(f"[OK] Created client: {user.full_name} (id={user.id}) "
                  f"with {len(cl_data['cars'])} car(s)")

        print(f"[OK] Total clients available: {len(client_ids)} — IDs: {client_ids}")

        # ---- 3. Load all cars for clients ----
        car_result = await session.execute(
            sa_select(Car).where(
                Car.client_id.in_(client_ids),
                Car.tenant_id == TENANT_ID,
            )
        )
        all_cars: list[Car] = list(car_result.scalars().all())
        car_ids_by_client: dict[int, list[int]] = {}
        for car in all_cars:
            car_ids_by_client.setdefault(car.client_id, []).append(car.id)
        print(f"[OK] Total cars loaded: {len(all_cars)}")

        # ---- 4. Create appointments (30-50 over last 3 months) ----
        appointment_count = random.randint(35, 45)
        created_appts = 0

        for _ in range(appointment_count * 2):  # safety multiplier for collisions
            if created_appts >= appointment_count:
                break

            client_id = random.choice(client_ids)
            # Pick one of client's cars
            client_cars = car_ids_by_client.get(client_id, [])
            if not client_cars:
                continue
            car_id = random.choice(client_cars)
            service_id = random.choice(SERVICE_IDS)
            # Get service duration for end_time calculation
            service_obj = next((s for s in services if s.id == service_id), None)
            if not service_obj:
                continue

            start_time = _random_datetime_3months()
            end_time = start_time + timedelta(minutes=service_obj.duration)
            status = _pick_status()
            price = float(service_obj.price)

            # Skip if master is not assigned for certain statuses
            master_id = random.choice(master_ids) if status in ("confirmed", "in_progress", "completed") else None

            # Add some master_brief for completed/in_progress appts
            master_brief = None
            if status in ("completed", "in_progress"):
                master_brief = random.choice([
                    "Всё выполнено, клиент доволен",
                    "Были сложности с загрязнениями, но справились",
                    "Дополнительно обработали колёсные диски",
                    "Клиент попросил нанести защитное покрытие",
                    "Стандартная процедура, без особенностей",
                    "Машина приехала очень грязная, потратили больше времени",
                    "Дополнительно продублировали полировку фар",
                ])

            # Add client notes for some
            client_notes = None
            if random.random() < 0.25:
                client_notes = random.choice([
                    "Просьба помыть тщательнее колёса",
                    "Есть небольшие сколы на капоте, аккуратнее",
                    "Хочу записаться на следующую неделю ещё раз",
                    "Приеду после обеда",
                    "Нужен чек",
                    "",
                ])

            appointment = Appointment(
                client_id=client_id,
                master_id=master_id,
                car_id=car_id,
                service_id=service_id,
                start_time=start_time,
                end_time=end_time,
                status=status,
                total_price=Decimal(str(price)),
                discount_applied=Decimal("0"),
                client_notes=client_notes if client_notes else None,
                master_brief=master_brief,
                tenant_id=TENANT_ID,
            )
            session.add(appointment)
            created_appts += 1

        await session.flush()
        print(f"[OK] Created {created_appts} appointments")

        # ---- 5. Create expenses ----
        from sqlalchemy import func as sa_func

        expense_count = 0
        for exp_data in EXPENSES:
            # Spread expense dates across the last 3 months
            if "Май" in exp_data.get("notes", ""):
                expense_date = TODAY.replace(day=random.randint(1, 5), month=TODAY.month - 2 if TODAY.month > 2 else 12)
            elif "Июнь" in exp_data.get("notes", ""):
                expense_date = TODAY.replace(day=random.randint(1, 5), month=TODAY.month - 1 if TODAY.month > 1 else 12)
            elif "Июль" in exp_data.get("notes", ""):
                expense_date = TODAY.replace(day=random.randint(1, min(12, TODAY.day)))
            else:
                expense_date = TODAY - timedelta(days=random.randint(0, 90))

            # Fix year if month wrapped
            if expense_date.month > TODAY.month + 1:
                expense_date = expense_date.replace(year=expense_date.year - 1)

            expense = Expense(
                name=exp_data["name"],
                amount=Decimal(str(exp_data["amount"])),
                category=exp_data["category"],
                expense_date=expense_date,
                notes=exp_data["notes"],
                tenant_id=TENANT_ID,
            )
            session.add(expense)
            expense_count += 1

        await session.flush()
        print(f"[OK] Created {expense_count} expenses")

        # ---- Commit everything ----
        await session.commit()
        print()
        print("=" * 60)
        print("  Seed completed successfully!")
        print(f"  • Masters:         {len(master_ids)}")
        print(f"  • Clients:         {len(client_ids)}")
        print(f"  • Cars:            {len(all_cars)}")
        print(f"  • Appointments:    {created_appts}")
        print(f"  • Expenses:        {expense_count}")
        print("=" * 60)


async def main() -> None:
    await seed()


if __name__ == "__main__":
    asyncio.run(main())
