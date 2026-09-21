/**
 * Отзывы — /reviews
 * Импорт отзывов, список и ИИ-вердикт по качеству услуг.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Typography, Spin, List, Empty, Popconfirm, message, Tag } from 'antd';
import { DeleteOutlined, RobotOutlined, ImportOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../components/Card';
import Badge from '../../components/Badge';
import { Button, Modal, Input } from '../../components/ui';
import { ReviewsVerdictBlock } from '../../components/ReviewsVerdict';
import {
  analyzeReviews,
  deleteReview,
  getReviews,
  getVerdict,
  importReviews,
  type ReviewIn,
  type ReviewItem,
  type ReviewVerdict,
} from '../../api/reviews';

dayjs.locale('ru');
const { Text } = Typography;
const { TextArea } = Input;

function hashId(value: string): string {
  let h = 0;
  for (let i = 0; i < value.length; i += 1) {
    h = (h * 31 + value.charCodeAt(i)) | 0;
  }
  return `manual-${Math.abs(h).toString(36)}`;
}

function clampRating(value: unknown): number | null {
  const n = Number(value);
  if (!Number.isFinite(n)) return null;
  return Math.min(5, Math.max(1, Math.round(n)));
}

/** Разобрать вставленный текст: JSON или строки «Автор | Оценка | Текст». */
function parseInput(raw: string): ReviewIn[] {
  const text = raw.trim();
  if (!text) return [];

  if (text.startsWith('[') || text.startsWith('{')) {
    try {
      const parsed = JSON.parse(text);
      const arr: Record<string, unknown>[] = Array.isArray(parsed)
        ? parsed
        : (Array.isArray(parsed.reviews) ? parsed.reviews : []);
      const items: ReviewIn[] = arr.map((o) => ({
        source: (o.source as string) || 'manual',
        external_id: (o.external_id as string) ?? null,
        author: (o.author as string) ?? null,
        rating: clampRating(o.rating),
        text: (o.text as string) ?? null,
      }));
      return items.filter((r) => r.text || r.rating != null);
    } catch {
      /* не JSON — разберём построчно ниже */
    }
  }

  const items: ReviewIn[] = [];
  for (const line of text.split('\n')) {
    const raw = line.trim();
    if (!raw) continue;
    const parts = raw.split('|').map((p) => p.trim());
    let author: string | null = null;
    let rating: number | null = null;
    let body = '';

    if (parts.length >= 3) {
      author = parts[0] || null;
      rating = clampRating(parts[1]);
      body = parts.slice(2).join(' | ');
    } else if (parts.length === 2) {
      const asRating = clampRating(parts[0]);
      if (asRating != null && parts[0] !== '') {
        rating = asRating;
      } else {
        author = parts[0] || null;
      }
      body = parts[1];
    } else {
      body = parts[0];
    }

    if (!body && rating == null) continue;
    items.push({
      source: 'manual',
      external_id: hashId(`${author}|${rating}|${body}`),
      author,
      rating,
      text: body || null,
    });
  }
  return items;
}

const SOURCE_LABEL: Record<string, string> = {
  yandex: 'Яндекс.Карты',
  manual: 'Вручную',
  other: 'Другое',
};

export default function ReviewsPage() {
  const [reviews, setReviews] = useState<ReviewItem[]>([]);
  const [total, setTotal] = useState(0);
  const [loading, setLoading] = useState(true);
  const [verdict, setVerdict] = useState<ReviewVerdict | null>(null);
  const [analyzing, setAnalyzing] = useState(false);
  const [importOpen, setImportOpen] = useState(false);
  const [importText, setImportText] = useState('');
  const [importing, setImporting] = useState(false);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const [list, v] = await Promise.all([
        getReviews(0, 100),
        getVerdict().catch(() => null),
      ]);
      setReviews(list.items);
      setTotal(list.total);
      if (v) setVerdict(v);
    } catch (e) {
      message.error((e as Error).message || 'Не удалось загрузить отзывы');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => { load(); }, [load]);

  const runAnalyze = async () => {
    setAnalyzing(true);
    try {
      const v = await analyzeReviews();
      setVerdict(v);
      message.success('Вердикт обновлён');
    } catch (e) {
      message.error((e as Error).message || 'Не удалось проанализировать');
    } finally {
      setAnalyzing(false);
    }
  };

  const doImport = async () => {
    const items = parseInput(importText);
    if (items.length === 0) {
      message.warning('Не удалось распознать отзывы');
      return;
    }
    setImporting(true);
    try {
      const res = await importReviews(items);
      message.success(`Импортировано: ${res.imported}, пропущено дубликатов: ${res.skipped}`);
      setImportOpen(false);
      setImportText('');
      await load();
    } catch (e) {
      message.error((e as Error).message || 'Ошибка импорта');
    } finally {
      setImporting(false);
    }
  };

  const remove = async (id: number) => {
    try {
      await deleteReview(id);
      await load();
    } catch (e) {
      message.error((e as Error).message || 'Не удалось удалить');
    }
  };

  return (
    <div className="reviews-page">
      <div className="flex-space-between reviews-header">
        <Text className="text-white-bold text-18">Отзывы о студии</Text>
        <div className="reviews-header-actions">
          <Button icon={<ImportOutlined />} look="ghost" onClick={() => setImportOpen(true)}>
            Импортировать
          </Button>
          <Button
            icon={<RobotOutlined />}
            look="gold"
            loading={analyzing}
            onClick={runAnalyze}
          >
            Проанализировать ИИ
          </Button>
        </div>
      </div>

      <Card className="card-luxury" style={{ marginBottom: 16 }}>
        <Text className="text-titanium text-12">Вердикт по качеству услуг</Text>
        <div className="mt-8">
          {verdict && verdict.reviews_count > 0 ? (
            <ReviewsVerdictBlock verdict={verdict} />
          ) : (
            <Text className="text-titanium text-13">
              Вердикта пока нет. Добавьте отзывы и нажмите «Проанализировать ИИ».
            </Text>
          )}
        </div>
      </Card>

      <Card className="card-luxury">
        <Text className="text-white-bold text-16">Список отзывов ({total})</Text>
        <Spin spinning={loading}>
          {reviews.length === 0 && !loading ? (
            <Empty description="Отзывов пока нет" className="mt-12" />
          ) : (
            <List
              className="reviews-list"
              itemLayout="vertical"
              dataSource={reviews}
              renderItem={(item) => (
                <List.Item
                  key={item.id}
                  actions={[
                    <Popconfirm
                      key="del"
                      title="Удалить отзыв?"
                      onConfirm={() => remove(item.id)}
                      okText="Удалить"
                      cancelText="Отмена"
                    >
                      <Button size="small" look="ghost" icon={<DeleteOutlined />}>Удалить</Button>
                    </Popconfirm>,
                  ]}
                >
                  <div className="reviews-item-head">
                    <Text className="text-white-bold">{item.author || 'Аноним'}</Text>
                    {item.rating != null && (
                      <Badge variant={item.rating >= 4 ? 'success' : item.rating >= 3 ? 'warning' : 'danger'} size="sm">
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

      <Modal
        title="Импорт отзывов"
        open={importOpen}
        onCancel={() => setImportOpen(false)}
        onOk={doImport}
        confirmLoading={importing}
        okText="Импортировать"
        cancelText="Отмена"
        width={640}
      >
        <Text className="text-titanium text-13">
          По одному отзыву в строке: «Автор | Оценка | Текст». Можно вставить JSON-массив
          (поля source, external_id, author, rating, text) — этот же формат принимает внешний сборщик.
        </Text>
        <TextArea
          rows={9}
          className="mt-12"
          value={importText}
          onChange={(e) => setImportText(e.target.value)}
          placeholder={'Иван | 5 | Отлично помыли, быстро\nПётр | 2 | Долго ждал, дорого'}
        />
      </Modal>
    </div>
  );
}
