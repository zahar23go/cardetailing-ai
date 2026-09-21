/* ============================================================
   Вердикт ИИ по качеству услуг на основе отзывов
   ============================================================ */

import React, { useEffect, useState } from 'react';
import { Typography, Space, Spin, Tag } from 'antd';
import { Link } from 'react-router-dom';
import Card from './Card';
import Badge from './Badge';
import { Button } from './ui';
import { getVerdict, type ReviewVerdict } from '../api/reviews';
import { isModuleEnabled } from '../modules';
import { useEnabledModules } from '../ModulesContext';

const { Text } = Typography;

const SENTIMENT: Record<string, { label: string; variant: 'success' | 'warning' | 'danger' | 'neutral' }> = {
  positive: { label: 'Позитив', variant: 'success' },
  neutral: { label: 'Нейтрально', variant: 'warning' },
  negative: { label: 'Негатив', variant: 'danger' },
};

const SOURCE_LABEL: Record<string, string> = {
  ai: 'ИИ-анализ',
  heuristic: 'Оценки и ключевые слова',
  none: 'Нет данных',
};

function ScoreValue({ verdict }: { verdict: ReviewVerdict }) {
  const score = verdict.score ?? verdict.average_rating;
  if (score == null) return <Text className="text-titanium">—</Text>;
  return (
    <>
      <span className="stat-value-gold">{score}</span>
      <Text className="text-titanium"> / 5</Text>
    </>
  );
}

/** Чистый вывод вердикта (без загрузки). */
export function ReviewsVerdictBlock({ verdict }: { verdict: ReviewVerdict }) {
  const sentiment = verdict.sentiment ? SENTIMENT[verdict.sentiment] : null;

  return (
    <div className="reviews-verdict">
      <Space align="center" size="middle" wrap className="reviews-verdict-head">
        <Text className="text-white-bold text-16">
          <ScoreValue verdict={verdict} />
        </Text>
        {sentiment && <Badge variant={sentiment.variant}>{sentiment.label}</Badge>}
        <Text className="text-titanium text-12">
          {verdict.reviews_count} отзыв(ов) · {SOURCE_LABEL[verdict.source] || verdict.source}
        </Text>
      </Space>

      {verdict.summary && <Text className="reviews-verdict-summary">{verdict.summary}</Text>}

      {verdict.themes.length > 0 && (
        <div className="reviews-verdict-themes">
          {verdict.themes.slice(0, 8).map((t) => (
            <Tag key={t.name} className="tag-status">
              {t.name}{t.count ? ` · ${t.count}` : ''}
            </Tag>
          ))}
        </div>
      )}

      <div className="reviews-verdict-columns">
        {verdict.strengths.length > 0 && (
          <div>
            <Text className="text-titanium text-12">Сильные стороны</Text>
            <ul className="reviews-verdict-list">
              {verdict.strengths.map((s) => <li key={s}>{s}</li>)}
            </ul>
          </div>
        )}
        {verdict.weaknesses.length > 0 && (
          <div>
            <Text className="text-titanium text-12">Слабые стороны</Text>
            <ul className="reviews-verdict-list">
              {verdict.weaknesses.map((w) => <li key={w}>{w}</li>)}
            </ul>
          </div>
        )}
      </div>

      {verdict.recommendations.length > 0 && (
        <div className="reviews-verdict-recs">
          <Text className="text-titanium text-12">Рекомендации</Text>
          <ul className="reviews-verdict-list">
            {verdict.recommendations.map((r) => <li key={r}>{r}</li>)}
          </ul>
        </div>
      )}
    </div>
  );
}

/** Само-загружаемый блок для Аналитики. */
export default function ReviewsVerdictCard() {
  const enabled = useEnabledModules();
  const [verdict, setVerdict] = useState<ReviewVerdict | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!isModuleEnabled(enabled, 'reviews')) {
      setLoading(false);
      return;
    }
    let alive = true;
    getVerdict()
      .then((v) => { if (alive) setVerdict(v); })
      .catch(() => undefined)
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, [enabled]);

  if (!isModuleEnabled(enabled, 'reviews')) return null;

  const hasData = !!verdict && verdict.reviews_count > 0;

  return (
    <Card className="card-luxury reviews-verdict-card">
      <div className="flex-space-between" style={{ marginBottom: 12 }}>
        <Text className="text-white-bold text-16">Качество по отзывам</Text>
        <Link to="/reviews">
          <Button size="small" look="ghost">Все отзывы</Button>
        </Link>
      </div>
      <Spin spinning={loading}>
        {hasData ? (
          <ReviewsVerdictBlock verdict={verdict as ReviewVerdict} />
        ) : (
          <Text className="text-titanium text-13">
            Отзывов пока нет. Добавьте их в разделе «Отзывы» и запустите анализ.
          </Text>
        )}
      </Spin>
    </Card>
  );
}
