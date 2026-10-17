# CarDetailing AI

AI-платформа для управления автомойкой и детейлинг-центром: запись, склад, техкарты,
аналитика и четыре ИИ-ассистента для клиента, мастера, управляющего и владельца.

## Стек

- **Backend:** FastAPI, PostgreSQL 15 (asyncpg), SQLAlchemy 2.0 (async), Alembic
- **Frontend:** React 18, TypeScript, Vite, Ant Design 5, React Router, Recharts, PWA
- **AI:** DeepSeek API, промпты в `prompts/*.yaml`, tool-calling по функциям доменов
- **Аутентификация:** JWT + bcrypt, мультитенантность по `tenant_id`
- **Инфраструктура:** Docker Compose (PostgreSQL + FastAPI + nginx), GitHub Actions

## Возможности

| Роль | Что доступно |
|------|--------------|
| **Клиент** | каталог услуг, запись, история визитов, портфолио авто, скидки и лояльность, отзывы, чат с ИИ |
| **Мастер** | календарь и записи, закрытие заезда (факт/норма времени), KPI, состояние авто, портфолио, навыки |
| **Администратор** | расписание, боксы, CRM услуг и пользователей, скидки, техкарты, склад, уведомления, брендинг, тарифы |
| **Владелец (`super_admin`)** | всё выше + P&L, маржа, break-even, аналитика, отчёты, ИИ-финансист |

### Домены backend (16 модулей)

| Модуль | Назначение |
|--------|------------|
| `core` | аутентификация, тенанты, онбординг, брендинг, тарифы |
| `services` | каталог услуг и себестоимость |
| `appointments` | запись, календарь, закрытие заезда, KPI мастеров, напоминания |
| `cars` | карточка авто, состояние (снимок визита vs профиль), портфолио |
| `photos` | загрузка и выдача фото |
| `materials` | материалы и нормы расхода |
| `tech_cards` | техкарты: версии, блоки, метки, фото шагов |
| `inventory` | склад: остатки, движения, приходные/расходные документы |
| `tech_analytics` | аналитика техпроцессов |
| `expenses` | расходы с бухгалтерскими полями |
| `analytics` | KPI, воронка, загрузка, когорты, теплокарта |
| `ai` | чаты и функции ИИ-ассистентов |
| `reviews` | отзывы, рейтинг студии, ИИ-анализ |
| `discounts` | скидки, акции, уровни лояльности, умные рекомендации |
| `notifications` | уведомления, настройки, SMS/Telegram-напоминания |
| `payments` | платежи и чеки |

## ИИ-ассистенты

| Ассистент | Промпт | API | Что делает |
|-----------|--------|-----|------------|
| **ИИ Макс** (клиент) | `prompts/detailer.yaml` | `POST /api/ai/consultant`, `/api/ai/detailer/*` | подбор услуг, слоты, запись, осмотр авто |
| **ИИ-финансист** (владелец) | `prompts/financier.yaml` | `POST /api/ai/financier`, `GET /api/ai/financier/brief` | KPI, P&L, загрузка, удержание, прогноз |
| **ИИ-управляющий** (админ) | `prompts/manager.yaml` | `POST /api/ai/manager` | расписание смены, загрузка боксов, «что требует внимания» |
| **ИИ-администратор** (владелец) | `prompts/admin.yaml` | `POST /api/ai/admin` | услуги, цены, боксы, скидки, мастера — с подтверждением изменений |

## Тарифы

Тариф хранится в `tenants.plan` и ограничивает модули (`backend/app/modules/plans.py`):

| План | Цена, ₽/мес | Модули |
|------|-------------|--------|
| Базовый | 2990 | услуги, запись (до 150/мес), авто, фото, склад материалов, скидки, уведомления |
| Про | 5990 | безлимит + ИИ-консультант, отзывы, аналитика, расходы, техкарты, платежи |
| Бизнес | 14990 | всё + финансист, White Label, склад и тех-аналитика |

## Структура проекта

```
cardetailing-ai/
├── backend/
│   ├── app/
│   │   ├── main.py                 # FastAPI entry: lifespan, CORS, монтаж модулей
│   │   ├── modules/                # домены: router.py, models.py, schemas.py, service.py
│   │   │   ├── registry.py         # порядок и включение модулей (ENABLED_MODULES)
│   │   │   └── plans.py            # тарифы и их модули
│   │   ├── core/                   # auth, config, БД, DeepSeek, SMS, Telegram, напоминания
│   │   ├── models.py               # общие ORM-модели и enum'ы
│   │   └── finance_formulas.py     # формулы выручки, маржи, break-even
│   ├── alembic/versions/           # миграции
│   ├── tests/                      # pytest (SQLite in-memory)
│   ├── Dockerfile.prod
│   └── requirements.txt
├── frontend/
│   ├── src/
│   │   ├── routes/index.tsx        # роутинг, экраны грузятся через React.lazy
│   │   ├── pages/                  # админка: dashboard, analytics, upload, crm, technology, settings
│   │   │   └── client/             # кабинет клиента
│   │   ├── components/             # общие компоненты и ui-кит
│   │   ├── design/                 # дизайн-система и темы (goldGlow, goldMetal, silver)
│   │   ├── api/                    # клиенты API
│   │   └── pwa.ts                  # service worker и установка PWA
│   ├── vite.config.ts              # прокси /api, manualChunks
│   └── Dockerfile.prod             # сборка + nginx
├── prompts/                        # YAML-промпты ИИ-ассистентов
├── tests/                          # vitest для формул и рекомендаций
├── docker-compose.yml              # локальный стек
├── docker-compose.prod.yml         # prod-стек (db + backend + frontend/nginx)
└── .github/workflows/deploy.yml    # тесты, сборка образов
```

## Быстрый старт

### Backend

```bash
cd backend
python -m venv venv
source venv/Scripts/activate        # Windows
# source venv/bin/activate          # Linux/Mac
pip install -r requirements.txt

# backend/.env: DATABASE_URL, JWT_SECRET, DEEPSEEK_API_KEY, SMS_*
python init_db.py
uvicorn app.main:app --reload --port 8000
```

Swagger: http://localhost:8000/docs

### Frontend

```bash
cd frontend
npm install
npm run dev       # http://localhost:3000, /api проксируется на :8000
npm run build     # tsc + vite build
```

### Тесты

```bash
cd backend
pytest tests/ -q                     # SQLite in-memory, внешняя БД не нужна
```

### Учётная запись по умолчанию

Создаётся при первом старте, если пользователей нет:

- телефон `+79999999999`, пароль `admin123`, роль `super_admin`

## Docker (prod)

```bash
cp .env.example .env                 # заполнить JWT_SECRET, DEEPSEEK_API_KEY, SMS_*
docker compose -f docker-compose.prod.yml up -d --build
```

- `backend` собирается из корня репозитория (`backend/` + `prompts/`) и работает как
  non-root `appuser`; каталог `/app/uploads` принадлежит ему, поэтому новый том
  `uploads_data` сразу доступен на запись.
- `frontend` собирается в nginx-образ, проксирует `/api` на backend и раздаёт `/uploads`.
- Если том `uploads_data` остался от старого деплоя, один раз поправьте владельца:
  `docker compose -f docker-compose.prod.yml run --rm --user root backend chown -R appuser:appuser /app/uploads`.

## Переменные окружения

| Переменная | Назначение |
|------------|------------|
| `DATABASE_URL` | PostgreSQL DSN (в compose собирается из `POSTGRES_*`) |
| `JWT_SECRET`, `JWT_EXPIRE_MINUTES` | подпись и срок жизни токена |
| `DEEPSEEK_API_KEY` | ключ DeepSeek для ассистентов |
| `SMS_PROVIDER`, `SMS_API_KEY`, `SMS_SENDER` | SMS.ru: провайдер `smsru`, ключ и имя отправителя; без ключа — заглушка |
| `TELEGRAM_BOT_TOKEN`, `TELEGRAM_WEBHOOK_URL` | Telegram-уведомления |
| `ENABLED_MODULES` | `all` или список доменов через запятую |
| `PROMPTS_DIR` | каталог с YAML-промптами (в образе `/app/prompts`) |
| `REMINDERS_ENABLED`, `REMINDER_INTERVAL_MINUTES` | фоновый планировщик напоминаний |
| `VITE_API_URL` | адрес backend для dev-прокси Vite |

## Документация

- `BACKLOG.md` — незакрытые работы по приоритетам
- `tests/checklist-salon-financier.md` — чек-лист приёмки ИИ-финансиста
- `frontend/src/design/DESIGN_SYSTEM.md` — дизайн-система
