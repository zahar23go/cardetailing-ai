# CarDetailing AI

AI-платформа для управления автомойкой и детейлинг-центром.

## Стек

- **Backend:** FastAPI, PostgreSQL 15 (asyncpg), SQLAlchemy 2.0 (async)
- **Frontend:** React 18, TypeScript, Vite, Ant Design 5
- **AI:** DeepSeek API (консультант по услугам)
- **Аутентификация:** JWT + bcrypt

## Быстрый старт (локально)

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate   # Windows
# source venv/bin/activate     # Linux/Mac
pip install -r requirements.txt

# Настройте .env (см. backend/.env.example)
# Запустите PostgreSQL и создайте БД cardetailing

python init_db.py
uvicorn app.main:app --reload --port 8000
```

### Frontend

```bash
cd frontend
npm install
npm run dev
# Откроется на http://localhost:3000
# API проксируется на http://localhost:8000
```

## Роли

| Роль | Возможности |
|------|------------|
| **Клиент** | Просмотр услуг, запись, управление авто |
| **Мастер** | Просмотр заданий, смена статуса, заметки |
| **Владелец (admin)** | KPI-дашборд, управление услугами, пользователями, записями |
| **Супер-админ** | Всё что у admin + смена роли на super_admin |

### Учётные записи по умолчанию

После первого запуска создаётся супер-администратор:
- Телефон: `+79999999999`
- Пароль: `admin123`

## Структура проекта

```
cardetailing-ai/
├── backend/
│   ├── app/
│   │   ├── main.py              # FastAPI приложение (все эндпоинты)
│   │   ├── models.py            # SQLAlchemy ORM модели
│   │   └── core/
│   │       ├── config.py        # Pydantic Settings
│   │       ├── database.py      # Подключение к БД, сессии
│   │       └── deepseek_client.py  # DeepSeek AI клиент
│   ├── requirements.txt
│   └── .env
├── frontend/
│   ├── src/
│   │   ├── App.tsx              # Главный компонент (аутентификация + роутинг)
│   │   ├── ClientDashboard.tsx   # Панель клиента
│   │   ├── OwnerDashboard.tsx    # Панель владельца
│   │   ├── MasterDashboard.tsx   # Панель мастера
│   │   └── styles/              # Дизайн-система (theme, global, components)
│   ├── package.json
│   └── vite.config.ts
└── docker-compose.yml           # Docker-развёртывание
```
