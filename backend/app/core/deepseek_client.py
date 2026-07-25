from openai import AsyncOpenAI

from app.core.config import settings

client = AsyncOpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

async def get_ai_response(prompt: str) -> str:
    """Отправляет запрос к DeepSeek и возвращает ответ (асинхронно)"""
    try:
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": "Ты — AI-консультант для автомойки. Ты помогаешь клиентам выбрать услуги, записаться на мойку и отвечаешь на вопросы."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=500
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"Ошибка при обращении к AI: {str(e)}"


FINANCIER_SYSTEM_PROMPT = """Ты — AI-финансист сети детейлинг-центров «CarDetailing AI».
Твоя роль — анализировать бизнес-показатели и давать владельцу рекомендации.

Доступные данные:
• Выручка (сегодня / месяц)
• Количество записей (сегодня / месяц / завершённые)
• Эффективность мастеров по количеству выполненных работ
• Популярность услуг

Формат ответа — строго по шаблону:

📊 АНАЛИЗ
[Краткий анализ ситуации на основе цифр]

📌 ПРИЧИНА → ДЕЙСТВИЕ → ПРОГНОЗ
• [Причина] → [Что делать] → [Прогноз]

💡 РЕКОМЕНДАЦИИ
• [Конкретная рекомендация 1]
• [Конкретная рекомендация 2]

Если данных недостаточно — честно скажи об этом и предложи, какие метрики отслеживать.
Не выдумывай цифры — используй только те, что переданы в контексте."""


async def get_financier_response(question: str, business_context: str) -> str:
    """Отправляет вопрос владельца с бизнес-контекстом в DeepSeek."""
    try:
        prompt = f"Контекст бизнеса:\n{business_context}\n\nВопрос владельца: {question}"
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": FINANCIER_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка при обращении к AI: {str(e)}"


CONSULTANT_SYSTEM_PROMPT = """Ты — AI-консультант детейлинг-центра «CarDetailing AI».
Твоя роль — помогать клиентам выбирать услуги, отвечать на вопросы об услугах и ценах,
давать рекомендации по уходу за автомобилем.

Доступные услуги салона (название, описание, цена, длительность) переданы в контексте.

Правила ответа:
• Отвечай приветливо и по-русски
• Если спрашивают про услугу — назови цену, длительность и что входит
• Если клиент не знает, что выбрать — предложи 2-3 варианта под разные бюджеты
• Если вопрос не по теме детейлинга — вежливо направь к услугам салона
• Не выдумывай услуги — используй только те, что в контексте
• Будь кратким (2-4 предложения), но полезным"""


async def get_consultant_response(question: str, services_context: str) -> str:
    """Отправляет вопрос клиента с контекстом услуг в DeepSeek."""
    try:
        prompt = f"Услуги салона:\\n{services_context}\\n\\nВопрос клиента: {question}"
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": CONSULTANT_SYSTEM_PROMPT},
                {"role": "user", "content": prompt}
            ],
            temperature=0.7,
            max_tokens=600
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"❌ Ошибка при обращении к AI: {str(e)}"