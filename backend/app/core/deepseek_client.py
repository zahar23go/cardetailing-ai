from openai import OpenAI

from app.core.config import settings

client = OpenAI(
    api_key=settings.DEEPSEEK_API_KEY,
    base_url="https://api.deepseek.com/v1"
)

def get_ai_response(prompt: str) -> str:
    """Отправляет запрос к DeepSeek и возвращает ответ"""
    try:
        response = client.chat.completions.create(
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