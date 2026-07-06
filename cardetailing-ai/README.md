# CarDetailing AI

AI-платформа для автосервисов с искусственным интеллектом.

## Стек

- **Backend:** FastAPI, PostgreSQL 15, Redis, Celery
- **Frontend:** React, TypeScript, Vite, Ant Design
- **Deployment:** Docker Compose

## Быстрый старт

```bash
# 1. Скопируйте файл окружения
cp .env.example .env

# 2. Запустите проект
docker-compose up -d

# 3. Откройте браузер
# Frontend: http://localhost:5173
# Backend API: http://localhost:8000
# Swagger: http://localhost:8000/docs
```

## Структура

```
cardetailing-ai/
├── backend/          # FastAPI приложение
├── frontend/         # React + TypeScript фронтенд
├── docker-compose.yml
└── .env.example
```
