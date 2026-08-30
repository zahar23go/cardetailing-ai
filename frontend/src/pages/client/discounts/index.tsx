/**
 * Активные скидки мойки для клиента.
 */
import React, { useEffect, useState } from 'react';
import { Empty, Spin, Typography } from 'antd';
import dayjs from 'dayjs';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  DISCOUNT_TYPE_LABELS,
  DiscountRule,
  apiFetch,
} from '../api';

const { Text } = Typography;

function conditionsText(rule: DiscountRule) {
  const parts: string[] = [];
  if (rule.service_name) parts.push(`Услуга: ${rule.service_name}`);
  if (rule.slot_start && rule.slot_end) parts.push(`Часы: ${rule.slot_start}–${rule.slot_end}`);
  if (rule.valid_until) parts.push(`До ${dayjs(rule.valid_until).format('D MMMM YYYY')}`);
  if (rule.client_id) parts.push('Персональное предложение');
  const c = rule.conditions && typeof rule.conditions === 'object' ? rule.conditions : {};
  if (rule.type === 'win_back' && c.max_recency_days) {
    parts.push(`Если не были ${c.max_recency_days} дней и больше`);
  } else if (rule.type === 'weather') {
    const labels: Record<string, string> = {
      rain: 'В дождь',
      freeze: 'В мороз',
      heat: 'В жару',
      dry: 'В сухую тёплую погоду',
    };
    parts.push(labels[String(c.weather || '')] || 'По прогнозу на день записи');
  } else {
    const extra = Object.entries(c)
      .filter(([, v]) => v !== null && v !== '')
      .map(([k, v]) => `${k}: ${String(v)}`);
    parts.push(...extra);
  }
  return parts;
}

export default function ClientDiscountsPage() {
  const [items, setItems] = useState<DiscountRule[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await apiFetch<{ items: DiscountRule[] }>('/api/discounts/active');
        if (!cancelled) setItems(data.items || []);
      } catch {
        if (!cancelled) setItems([]);
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  if (loading) return <Spin />;

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Скидки</h3>
          <Badge variant="gold">Действующие акции и условия</Badge>
        </div>
      </div>

      {items.length === 0 ? (
        <Card variant="admin" className="client-block">
          <Empty description={<Text className="text-titanium">Сейчас нет активных скидок</Text>} />
        </Card>
      ) : (
        items.map((rule) => {
          const cond = conditionsText(rule);
          return (
            <Card key={rule.id} variant="admin" className="client-block">
              <div className="client-appt-row">
                <div>
                  <div className="client-appt-name">{rule.name}</div>
                  <Badge variant="gold" size="sm">
                    {DISCOUNT_TYPE_LABELS[rule.type] || rule.type}
                  </Badge>
                  {cond.length ? (
                    <ul className="client-discount-terms">
                      {cond.map((line) => <li key={line}>{line}</li>)}
                    </ul>
                  ) : (
                    <Text className="text-titanium">Скидка применяется автоматически при записи</Text>
                  )}
                </div>
                <div className="client-appt-meta">
                  <div className="client-kpi-value">−{rule.discount_percent}%</div>
                </div>
              </div>
            </Card>
          );
        })
      )}
    </>
  );
}
