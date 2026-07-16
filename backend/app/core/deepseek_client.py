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