/**
 * Отзывы студии — рейтинг и отзывы для клиента.
 */
import React, { useEffect, useState } from 'react';
import { Typography, Spin, List, Empty, message, Tag } from 'antd';
import { StarFilled } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import { getPublicReviews, type ReviewItem, type ReviewSummary } from '../../../api/reviews';

dayjs.locale('ru');
const { Text } = Typography;

const SOURCE_LABEL: Record<string, string> = {
  yandex: 'Яндекс.Карты',
  manual: 'Студия',
  other: 'Другое',
};

export default function ClientReviewsPage() {
  const [summary, setSummary] = useState<ReviewSummary | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let alive = true;
    getPublicReviews()
      .then((data) => { if (alive) setSummary(data); })
      .catch((e) => message.error((e as Error).message || 'Не удалось загрузить отзывы'))
      .finally(() => { if (alive) setLoading(false); });
    return () => { alive = false; };
  }, []);

  const rating = summary?.average_rating ?? null;

  return (
    <div className="client-reviews">
      <Card className="card-luxury reviews-rating-hero">
        <div className="reviews-rating-value">
          <StarFilled className="reviews-rating-star" />
          <span className="stat-value-gold">{rating != null ? rating : '—'}</span>
          <Text className="text-titanium"> / 5</Text>
        </div>
        <Text className="text-titanium text-13">
          Рейтинг студии по {summary?.count ?? 0} отзыв(ам)
        </Text>
      </Card>

      <Card className="card-luxury">
        <Text className="text-white-bold text-16">Отзывы</Text>
        <Spin spinning={loading}>
          {!loading && (summary?.items.length ?? 0) === 0 ? (
            <Empty description="Отзывов пока нет" className="mt-12" />
          ) : (
            <List
              className="reviews-list"
              itemLayout="vertical"
              dataSource={summary?.items ?? []}
              renderItem={(item: ReviewItem) => (
                <List.Item key={item.id}>
                  <div className="reviews-item-head">
                    <Text className="text-white-bold">{item.author || 'Аноним'}</Text>
                    {item.rating != null && (
                      <Badge
                        variant={item.rating >= 4 ? 'success' : item.rating >= 3 ? 'warning' : 'danger'}
                        size="sm"
                      >
                        {item.rating}/5
                      </Badge>
                    )}
                    <Tag className="tag-status">{SOURCE_LABEL[item.source] || item.source}</Tag>
                    {item.created_at && (
                      <Text className="text-titanium text-12">
                        {dayjs(item.created_at).format('D MMM YYYY')}
                      </Text>
                    )}
                  </div>
                  {item.text && <Text className="text-titanium reviews-item-text">{item.text}</Text>}
                </List.Item>
              )}
            />
          )}
        </Spin>
      </Card>
    </div>
  );
}
