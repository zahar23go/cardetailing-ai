"""Отзывы: импорт, дедупликация и ИИ-вердикт по качеству услуг.

Вердикт сначала пытается получить у LLM (DeepSeek, строгий JSON).
Если ключа нет или модель недоступна/ответила не-JSON — используется
детерминированный эвристический вердикт (оценки + ключевые слова).
"""
from __future__ import annotations

import json
from uuid import UUID

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.deepseek_client import client
from app.models import Review, ReviewAnalysis

POSITIVE_WORDS = [
    "отлично", "супер", "доволен", "довольна", "рекомендую", "качественно",
    "быстро", "вежлив", "чисто", "аккуратно", "понравилось", "идеально",
]

NEGATIVE_WORDS = [
    "плохо", "ужас", "хамств", "грубо", "дорого", "долго", "грязно",
    "царапин", "развод", "обман", "не рекомендую", "очередь", "брак",
]

THEME_KEYWORDS: dict[str, list[str]] = {
    "качество": ["качество", "полиров", "керамик", "мойк", "химчист", "результат"],
    "персонал": ["персонал", "мастер", "администратор", "сотрудник", "вежлив"],
    "цена": ["цена", "дорого", "дешево", "стоимость", "прайс"],
    "скорость": ["долго", "быстро", "время", "ожидан", "очередь", "задерж"],
    "чистота": ["чисто", "грязн", "пыль", "разводы", "пятн"],
}

REVIEW_SYSTEM_PROMPT = """Ты — аналитик качества детейлинг-центра.
Проанализируй отзывы клиентов и верни СТРОГО JSON без пояснений и без markdown.

Формат:
{
  "score": 4.3,
  "sentiment": "positive",
  "summary": "краткий вывод о качестве услуг",
  "strengths": ["сильная сторона"],
  "weaknesses": ["слабая сторона"],
  "themes": [{"name": "качество", "count": 5, "sentiment": "positive"}],
  "recommendations": ["конкретное действие"]
}

Правила:
• score — от 0 до 5, оценка качества услуг
• sentiment — positive | neutral | negative
• Опирайся только на текст отзывов, не выдумывай факты
• Если данных мало — честно скажи об этом в summary
• Отвечай по-русски"""


async def import_reviews(db: AsyncSession, tenant_id: UUID, items) -> tuple[int, int]:
    """Добавить отзывы. Дубликаты по (source, external_id) пропускаются."""
    imported = 0
    skipped = 0
    for item in items:
        external_id = (item.external_id or "").strip() or None
        source = (item.source or "manual").strip() or "manual"
        if external_id:
            exists = await db.execute(
                select(Review.id)
                .where(
                    Review.tenant_id == tenant_id,
                    Review.source == source,
                    Review.external_id == external_id,
                )
                .limit(1)
            )
            if exists.scalar_one_or_none() is not None:
                skipped += 1
                continue
        db.add(
            Review(
                tenant_id=tenant_id,
                source=source,
                external_id=external_id,
                author=item.author,
                rating=item.rating,
                text=item.text,
                published_at=item.published_at,
            )
        )
        imported += 1
    await db.commit()
    return imported, skipped


def _sentiment_from_score(score: float | None) -> str | None:
    if score is None:
        return None
    if score >= 4:
        return "positive"
    if score >= 3:
        return "neutral"
    return "negative"


def _average_rating(reviews) -> float | None:
    rated = [r.rating for r in reviews if r.rating]
    if not rated:
        return None
    return round(sum(rated) / len(rated), 2)


def _heuristic_verdict(reviews) -> dict:
    """Детерминированный вердикт без LLM: оценки + ключевые слова."""
    avg = _average_rating(reviews)
    text = " ".join((r.text or "").lower() for r in reviews)
    themes = []
    for name, words in THEME_KEYWORDS.items():
        count = sum(text.count(w) for w in words)
        if count:
            themes.append({"name": name, "count": count, "sentiment": "neutral"})
    themes.sort(key=lambda t: t["count"], reverse=True)

    score = avg
    if score is None:
        pos = sum(text.count(w) for w in POSITIVE_WORDS)
        neg = sum(text.count(w) for w in NEGATIVE_WORDS)
        score = round(5 * pos / (pos + neg), 2) if (pos + neg) else None

    theme_names = {t["name"] for t in themes}
    strengths: list[str] = []
    weaknesses: list[str] = []
    if avg is not None and avg >= 4:
        strengths.append(f"Средняя оценка {avg} из 5 — клиенты довольны сервисом.")
    if "качество" in theme_names:
        strengths.append("В отзывах часто отмечают качество работ.")
    if "персонал" in theme_names:
        strengths.append("Отмечают вежливость персонала.")
    if avg is not None and avg < 3.5:
        weaknesses.append(f"Средняя оценка {avg} из 5 — есть системные жалобы.")
    if "цена" in theme_names:
        weaknesses.append("В отзывах упоминается цена.")
    if "скорость" in theme_names:
        weaknesses.append("Есть упоминания о времени ожидания.")
    if "чистота" in theme_names:
        weaknesses.append("Есть замечания к чистоте.")

    recommendations: list[str] = []
    if weaknesses:
        recommendations.append("Разобрать повторяющиеся жалобы с мастерами и администраторами.")
    if score is not None and score < 4:
        recommendations.append("Просить довольных клиентов оставлять отзывы, чтобы поднять рейтинг.")
    if not recommendations:
        recommendations.append("Поддерживать текущий уровень сервиса и отвечать на отзывы.")

    summary = f"Собрано {len(reviews)} отзывов" + (
        f", средняя оценка {avg} из 5." if avg is not None else "."
    )
    return {
        "score": score,
        "sentiment": _sentiment_from_score(score) or "neutral",
        "summary": summary,
        "strengths": strengths,
        "weaknesses": weaknesses,
        "themes": themes,
        "recommendations": recommendations,
    }


def _parse_json(raw: str | None) -> dict | None:
    if not raw:
        return None
    s = raw.strip()
    if s.startswith("```"):
        s = s.strip("`").strip()
        if s.lower().startswith("json"):
            s = s[4:].strip()
    start = s.find("{")
    end = s.rfind("}")
    if start == -1 or end <= start:
        return None
    try:
        parsed = json.loads(s[start:end + 1])
    except json.JSONDecodeError:
        return None
    return parsed if isinstance(parsed, dict) else None


def _verdict_context(reviews, limit: int = 40) -> str:
    lines = []
    for r in reviews[:limit]:
        rating = f"{r.rating}/5" if r.rating else "без оценки"
        text = (r.text or "").strip().replace("\n", " ")
        if len(text) > 400:
            text = text[:400] + "…"
        lines.append(f"- [{rating}] {text}")
    return "\n".join(lines)


async def llm_verdict(reviews) -> dict | None:
    """Вердикт от DeepSeek (строгий JSON). None — если недоступно."""
    if not settings.DEEPSEEK_API_KEY or not reviews:
        return None
    try:
        prompt = f"Отзывы ({len(reviews)}):\n{_verdict_context(reviews)}"
        response = await client.chat.completions.create(
            model="deepseek-v4-flash",
            messages=[
                {"role": "system", "content": REVIEW_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            temperature=0.2,
            max_tokens=900,
        )
        raw = response.choices[0].message.content if response.choices else None
        return _parse_json(raw)
    except Exception:
        return None


def _normalize_verdict(data: dict, reviews, source: str) -> dict:
    """Привести ответ LLM к единой структуре вердикта."""
    def _str_list(key: str) -> list[str]:
        value = data.get(key)
        if isinstance(value, list):
            return [str(x).strip() for x in value if str(x).strip()]
        return []

    themes = []
    for item in data.get("themes") or []:
        if isinstance(item, dict) and item.get("name"):
            try:
                count = int(item.get("count") or 0)
            except (TypeError, ValueError):
                count = 0
            themes.append({
                "name": str(item["name"]),
                "count": count,
                "sentiment": str(item.get("sentiment") or "neutral"),
            })
        elif isinstance(item, str) and item.strip():
            themes.append({"name": item.strip(), "count": 0, "sentiment": "neutral"})

    score = data.get("score")
    try:
        score = float(score) if score is not None else None
    except (TypeError, ValueError):
        score = None

    return {
        "score": score,
        "sentiment": str(data.get("sentiment") or _sentiment_from_score(score) or "neutral"),
        "summary": (str(data.get("summary")).strip() if data.get("summary") else None),
        "strengths": _str_list("strengths"),
        "weaknesses": _str_list("weaknesses"),
        "themes": themes,
        "recommendations": _str_list("recommendations"),
        "reviews_count": len(reviews),
        "average_rating": _average_rating(reviews),
        "source": source,
    }


def _empty_verdict() -> dict:
    return {
        "score": None,
        "sentiment": "neutral",
        "summary": "Отзывов пока нет — добавьте или импортируйте их.",
        "strengths": [],
        "weaknesses": [],
        "themes": [],
        "recommendations": [],
        "reviews_count": 0,
        "average_rating": None,
        "source": "heuristic",
    }


async def analyze_reviews(db: AsyncSession, tenant_id: UUID) -> dict:
    """Проанализировать отзывы и сохранить вердикт (LLM или эвристика)."""
    result = await db.execute(
        select(Review)
        .where(Review.tenant_id == tenant_id)
        .order_by(Review.id.desc())
    )
    reviews = list(result.scalars().all())

    if not reviews:
        verdict = _empty_verdict()
    else:
        data = await llm_verdict(reviews)
        if data:
            verdict = _normalize_verdict(data, reviews, "ai")
        else:
            verdict = _normalize_verdict(_heuristic_verdict(reviews), reviews, "heuristic")

    row = ReviewAnalysis(
        tenant_id=tenant_id,
        reviews_count=verdict["reviews_count"],
        average_rating=verdict["average_rating"],
        source=verdict["source"],
        verdict=verdict,
    )
    db.add(row)
    await db.commit()
    await db.refresh(row)
    return {**verdict, "created_at": row.created_at}


async def latest_verdict(db: AsyncSession, tenant_id: UUID) -> dict | None:
    """Последний сохранённый вердикт или None."""
    result = await db.execute(
        select(ReviewAnalysis)
        .where(ReviewAnalysis.tenant_id == tenant_id)
        .order_by(ReviewAnalysis.id.desc())
        .limit(1)
    )
    row = result.scalar_one_or_none()
    if row is None:
        return None
    return {
        **(row.verdict or {}),
        "reviews_count": row.reviews_count,
        "average_rating": row.average_rating,
        "source": row.source,
        "created_at": row.created_at,
    }
