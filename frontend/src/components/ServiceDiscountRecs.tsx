/* ============================================================
   ServiceDiscountRecs — рекомендации скидок по марже/популярности
   ============================================================ */

import React, { useCallback, useEffect, useState } from 'react';
import {
  Button, Card, Col, Empty, InputNumber, Modal, Row, Space, Spin, Table, Tag, Typography, message,
} from 'antd';
import {
  CheckOutlined, CloseOutlined, EditOutlined, ReloadOutlined, RiseOutlined,
} from '@ant-design/icons';
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis,
} from 'recharts';
import dayjs from 'dayjs';

const { Text } = Typography;

interface RecItem {
  id: number;
  service_id: number;
  service_name: string;
  price: number;
  cost_price: number;
  bookings_30d: number;
  bookings_prev_30d: number;
  popularity_index: number;
  margin_raw: number;
  margin_index: number;
  priority: number;
  suggested_percent: number;
  adjusted_percent: number | null;
  scenario: string;
  reason: string;
  status: string;
  discount_rule_id: number | null;
  computed_at?: string;
  decided_at?: string;
}

interface AnalyticsPoint {
  service_id: number;
  service_name: string;
  before_bookings: number;
  after_bookings: number;
  bookings_growth_percent: number;
  before_revenue: number;
  after_revenue: number;
  revenue_delta: number;
}

interface RecsResponse {
  last_computed_at: string | null;
  next_refresh_at: string | null;
  auto_refreshed: boolean;
  items: RecItem[];
  analytics: AnalyticsPoint[];
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  approved: 'Утверждена',
  adjusted: 'Скорректирована',
  rejected: 'Отклонена',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'gold',
  approved: 'green',
  adjusted: 'blue',
  rejected: 'default',
};

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...options?.headers,
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

export default function ServiceDiscountRecs() {
  const [loading, setLoading] = useState(false);
  const [data, setData] = useState<RecsResponse | null>(null);
  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustRec, setAdjustRec] = useState<RecItem | null>(null);
  const [adjustPercent, setAdjustPercent] = useState(15);
  const [decidingId, setDecidingId] = useState<number | null>(null);

  const load = useCallback(async (force = false) => {
    setLoading(true);
    try {
      const path = force
        ? '/api/analytics/service-discount-recs/refresh'
        : '/api/analytics/service-discount-recs';
      const res = await apiFetch<RecsResponse>(path, force ? { method: 'POST' } : undefined);
      setData(res);
      if (res.auto_refreshed) {
        message.info('Рекомендации обновлены (еженедельный пересчёт)');
      }
    } catch (e: any) {
      message.error(e.message || 'Ошибка загрузки рекомендаций');
    } finally {
      setLoading(false);
    }
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  const decide = async (id: number, action: 'approve' | 'reject' | 'adjust', percent?: number) => {
    setDecidingId(id);
    try {
      await apiFetch(`/api/analytics/service-discount-recs/${id}/decide`, {
        method: 'POST',
        body: JSON.stringify({
          action,
          adjusted_percent: percent ?? null,
        }),
      });
      message.success(
        action === 'approve' ? 'Скидка утверждена' :
          action === 'reject' ? 'Отклонено' : 'Скидка скорректирована и создана',
      );
      setAdjustOpen(false);
      await load();
    } catch (e: any) {
      message.error(e.message || 'Ошибка решения');
    } finally {
      setDecidingId(null);
    }
  };

  const pending = (data?.items || []).filter((i) => i.status === 'pending');
  const history = (data?.items || []).filter((i) => i.status !== 'pending');
  const chartData = (data?.analytics || []).map((a) => ({
    name: a.service_name.length > 16 ? `${a.service_name.slice(0, 14)}…` : a.service_name,
    До: a.before_bookings,
    После: a.after_bookings,
  }));

  return (
    <div className="service-recs">
      <div className="discount-intel-toolbar">
        <Space wrap>
          <Text className="text-gold">
            Последний расчёт:{' '}
            {data?.last_computed_at ? dayjs(data.last_computed_at).format('DD.MM.YYYY HH:mm') : '—'}
          </Text>
          <Text className="text-titanium text-13">
            Следующий авто-обновление:{' '}
            {data?.next_refresh_at ? dayjs(data.next_refresh_at).format('DD.MM.YYYY') : '—'}
          </Text>
          <Button
            size="small"
            icon={<ReloadOutlined />}
            className="btn-gold-secondary"
            loading={loading}
            onClick={() => load(true)}
          >
            Пересчитать сейчас
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
          <Text className="admin-panel-title">Рекомендации по услугам</Text>
          <p className="discount-intel-hint">
            Приоритет = (1 − популярность)×0.6 + (1 − маржинальность)×0.4.
            ≥0.7 → 20–30%, 0.5–0.69 → 10–20%. Отдельно: высокомаржинальные просевшие услуги.
          </p>
          {pending.length === 0 ? (
            <Empty description={<span className="text-titanium">Нет активных рекомендаций — заполните себестоимость услуг</span>} />
          ) : (
            <Space direction="vertical" size={12} style={{ width: '100%' }}>
              {pending.map((r) => (
                <div key={r.id} className="service-rec-card">
                  <div className="service-rec-head">
                    <div>
                      <Text className="text-white-bold text-14">{r.service_name}</Text>
                      <div className="service-rec-tags">
                        <Tag color="gold">−{r.suggested_percent}%</Tag>
                        <Tag color={r.scenario === 'high_margin_decline' ? 'purple' : 'blue'}>
                          {r.scenario === 'high_margin_decline' ? 'Просадка маржи' : 'Приоритет'}
                        </Tag>
                        <Tag>приоритет {r.priority.toFixed(2)}</Tag>
                      </div>
                    </div>
                    <div className="service-rec-metrics">
                      <span>Записи 30д: <b>{r.bookings_30d}</b> (было {r.bookings_prev_30d})</span>
                      <span>Маржа: <b>{(r.margin_raw * 100).toFixed(0)}%</b></span>
                      <span>Себест.: <b>{r.cost_price.toLocaleString()} ₽</b> / {r.price.toLocaleString()} ₽</span>
                      <span>Попул.: <b>{(r.popularity_index * 100).toFixed(0)}%</b></span>
                    </div>
                  </div>
                  <p className="service-rec-reason">{r.reason}</p>
                  <Space wrap>
                    <Button
                      className="btn-gold"
                      size="small"
                      icon={<CheckOutlined />}
                      loading={decidingId === r.id}
                      onClick={() => decide(r.id, 'approve')}
                    >
                      Утвердить
                    </Button>
                    <Button
                      className="btn-gold-secondary"
                      size="small"
                      icon={<EditOutlined />}
                      onClick={() => {
                        setAdjustRec(r);
                        setAdjustPercent(r.suggested_percent);
                        setAdjustOpen(true);
                      }}
                    >
                      Скорректировать
                    </Button>
                    <Button
                      danger
                      size="small"
                      icon={<CloseOutlined />}
                      loading={decidingId === r.id}
                      onClick={() => decide(r.id, 'reject')}
                    >
                      Отклонить
                    </Button>
                  </Space>
                </div>
              ))}
            </Space>
          )}
        </Card>

        {history.length > 0 && (
          <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
            <Text className="admin-panel-title">История решений</Text>
            <Table
              style={{ marginTop: 12 }}
              size="small"
              rowKey="id"
              pagination={{ pageSize: 8, size: 'small' }}
              dataSource={history}
              columns={[
                {
                  title: <Text className="text-gold text-12">Услуга</Text>,
                  dataIndex: 'service_name',
                  render: (v) => <Text className="text-white text-13">{v}</Text>,
                },
                {
                  title: <Text className="text-gold text-12">%</Text>,
                  key: 'pct',
                  render: (_, r) => (
                    <Text className="text-gold-bold">
                      −{r.adjusted_percent ?? r.suggested_percent}%
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-gold text-12">Статус</Text>,
                  dataIndex: 'status',
                  render: (v) => <Tag color={STATUS_COLORS[v]}>{STATUS_LABELS[v] || v}</Tag>,
                },
                {
                  title: <Text className="text-gold text-12">Дата</Text>,
                  dataIndex: 'decided_at',
                  render: (v) => (
                    <Text className="text-titanium text-12">
                      {v ? dayjs(v).format('DD.MM.YYYY') : '—'}
                    </Text>
                  ),
                },
              ]}
            />
          </Card>
        )}

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">
                <RiseOutlined /> До / После (записи)
              </Text>
              <p className="discount-intel-hint">Сравнение 30 дней до и после утверждения скидки</p>
              {chartData.length === 0 ? (
                <Empty description={<span className="text-titanium">Утвердите рекомендацию — появится график</span>} />
              ) : (
                <div style={{ width: '100%', height: 260 }}>
                  <ResponsiveContainer>
                    <BarChart data={chartData}>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: '#aab2bf', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#aab2bf', fontSize: 11 }} width={36} />
                      <RechartsTooltip
                        contentStyle={{ background: '#14161a', border: '1px solid rgba(212,168,75,0.3)' }}
                      />
                      <Legend />
                      <Bar dataKey="До" fill="rgba(170,178,191,0.7)" radius={[6, 6, 0, 0]} />
                      <Bar dataKey="После" fill="#D4A84B" radius={[6, 6, 0, 0]} />
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={10}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">Влияние на выручку</Text>
              <Table
                style={{ marginTop: 12 }}
                size="small"
                pagination={false}
                rowKey="service_id"
                dataSource={data?.analytics || []}
                locale={{ emptyText: 'Нет данных' }}
                columns={[
                  {
                    title: <Text className="text-gold text-12">Услуга</Text>,
                    dataIndex: 'service_name',
                    render: (v) => <Text className="text-white text-12">{v}</Text>,
                  },
                  {
                    title: <Text className="text-gold text-12">Δ записи</Text>,
                    dataIndex: 'bookings_growth_percent',
                    render: (v) => (
                      <Tag color={v >= 0 ? 'green' : 'red'}>{v > 0 ? '+' : ''}{v}%</Tag>
                    ),
                  },
                  {
                    title: <Text className="text-gold text-12">Δ выручка</Text>,
                    dataIndex: 'revenue_delta',
                    render: (v) => (
                      <Text className={v >= 0 ? 'text-gold-bold text-12' : 'text-12'}>
                        {v >= 0 ? '+' : ''}{Number(v).toLocaleString()} ₽
                      </Text>
                    ),
                  },
                ]}
              />
            </Card>
          </Col>
        </Row>
      </Spin>

      <Modal
        title={<Text className="text-gold-bold">Скорректировать скидку</Text>}
        open={adjustOpen}
        onCancel={() => setAdjustOpen(false)}
        footer={null}
        className="modal-command"
      >
        {adjustRec && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Text className="text-white">{adjustRec.service_name}</Text>
            <Text className="text-titanium text-13">{adjustRec.reason}</Text>
            <div>
              <span className="label-field">Процент скидки</span>
              <InputNumber
                min={1}
                max={50}
                value={adjustPercent}
                onChange={(v) => setAdjustPercent(Number(v) || 1)}
                className="w-full"
              />
            </div>
            <Button
              className="btn-gold"
              loading={decidingId === adjustRec.id}
              onClick={() => decide(adjustRec.id, 'adjust', adjustPercent)}
            >
              Сохранить и утвердить (−{adjustPercent}%)
            </Button>
          </Space>
        )}
      </Modal>
    </div>
  );
}
