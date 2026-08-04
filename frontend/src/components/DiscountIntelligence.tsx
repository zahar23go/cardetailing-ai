/* ============================================================
   DiscountIntelligence — тепловая карта + авто-скидки по загрузке
   ============================================================ */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button, Card, Col, Empty, message, Row, Space, Spin, Table, Tag, Tooltip, Typography,
} from 'antd';
import {
  GiftOutlined, ReloadOutlined, ThunderboltOutlined, SendOutlined, BulbOutlined,
} from '@ant-design/icons';
import {
  Bar, BarChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis,
} from 'recharts';

const { Text } = Typography;

interface HeatmapCell {
  day: number;
  hour: number;
  count: number;
  revenue: number;
}

interface DiscountSuggestion {
  key: string;
  name: string;
  hour_start: string;
  hour_end: string;
  weekdays: number[];
  weekday_label: string;
  discount_percent: number;
  avg_load: number;
  reason: string;
}

interface DiscountRuleAdvice {
  rule_id: number | null;
  rule_name: string;
  action: string;
  message: string;
  suggested_percent: number | null;
}

interface DiscountRoiItem {
  rule_id: number;
  rule_name: string;
  times_used: number;
  discount_cost: number;
  estimated_extra_revenue: number;
  roi_percent: number;
  verdict: string;
}

interface DiscountBeforeAfterPoint {
  rule_id: number;
  rule_name: string;
  label: string;
  before_avg: number;
  after_avg: number;
}

interface IntelligenceData {
  period_days: number;
  cells: HeatmapCell[];
  suggestions: DiscountSuggestion[];
  recommendations: DiscountRuleAdvice[];
  roi: DiscountRoiItem[];
  before_after: DiscountBeforeAfterPoint[];
}

const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
const HOURS = Array.from({ length: 15 }, (_, i) => i + 8); // 8..22

const ACTION_COLORS: Record<string, string> = {
  create: 'gold',
  increase: 'blue',
  decrease: 'orange',
  disable: 'red',
  keep: 'green',
};

const ACTION_LABELS: Record<string, string> = {
  create: 'Создать',
  increase: 'Увеличить',
  decrease: 'Снизить',
  disable: 'Отключить',
  keep: 'Оставить',
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

function cellColor(count: number, max: number) {
  if (max <= 0 || count <= 0) return 'rgba(212,168,75,0.06)';
  const t = Math.min(1, count / max);
  const alpha = 0.12 + t * 0.75;
  return `rgba(212, 168, 75, ${alpha})`;
}

interface Props {
  onCreateSuggestion: (s: DiscountSuggestion) => Promise<void> | void;
  onApplyAdvice?: (advice: DiscountRuleAdvice) => Promise<void> | void;
}

export default function DiscountIntelligence({ onCreateSuggestion, onApplyAdvice }: Props) {
  const [loading, setLoading] = useState(false);
  const [broadcasting, setBroadcasting] = useState(false);
  const [creatingKey, setCreatingKey] = useState<string | null>(null);
  const [data, setData] = useState<IntelligenceData | null>(null);
  const [periodDays, setPeriodDays] = useState(60);

  const load = useCallback(async (days = periodDays) => {
    setLoading(true);
    try {
      const res = await apiFetch<IntelligenceData>(`/api/analytics/discount-intelligence?days=${days}`);
      setData(res);
    } catch (e: any) {
      message.error(e.message || 'Ошибка загрузки аналитики скидок');
    } finally {
      setLoading(false);
    }
  }, [periodDays]);

  useEffect(() => {
    load();
  }, [load]);

  const maxCount = useMemo(
    () => Math.max(1, ...(data?.cells.map((c) => c.count) || [1])),
    [data],
  );

  const getCount = (day: number, hour: number) =>
    data?.cells.find((c) => c.day === day && c.hour === hour)?.count || 0;

  const handleCreate = async (s: DiscountSuggestion) => {
    setCreatingKey(s.key);
    try {
      await onCreateSuggestion(s);
      message.success(`Создано: ${s.name}`);
      await load();
    } catch (e: any) {
      message.error(e.message || 'Не удалось создать правило');
    } finally {
      setCreatingKey(null);
    }
  };

  const handleBroadcast = async () => {
    setBroadcasting(true);
    try {
      const res = await apiFetch<{ sent: number; message: string }>(
        '/api/discounts/broadcast-happy-hours',
        { method: 'POST' },
      );
      message.success(res.message || `Отправлено: ${res.sent}`);
    } catch (e: any) {
      message.error(e.message || 'Ошибка рассылки');
    } finally {
      setBroadcasting(false);
    }
  };

  const chartData = (data?.before_after || []).map((p) => ({
    name: p.rule_name.length > 18 ? `${p.rule_name.slice(0, 16)}…` : p.rule_name,
    До: p.before_avg,
    После: p.after_avg,
  }));

  return (
    <div className="discount-intel">
      <div className="discount-intel-toolbar">
        <Space wrap>
          <span className="badge badge--gold badge--lead">Период анализа</span>
          {[30, 60, 90].map((d) => (
            <Button
              key={d}
              size="small"
              className={periodDays === d ? 'btn-gold' : 'btn-gold-secondary'}
              onClick={() => { setPeriodDays(d); }}
            >
              {d} дн.
            </Button>
          ))}
          <Button
            size="small"
            icon={<ReloadOutlined />}
            className="btn-gold-secondary"
            onClick={() => load(periodDays)}
          >
            Обновить
          </Button>
          <Button
            size="small"
            icon={<SendOutlined />}
            className="btn-gold"
            loading={broadcasting}
            onClick={handleBroadcast}
          >
            Рассылка Happy Hours
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
          <Text className="admin-panel-title">Тепловая карта загрузки</Text>
          <p className="discount-intel-hint">
            Дни × часы за последние {data?.period_days || periodDays} дней. Чем ярче золото — тем выше загрузка
            (пик, без скидок). Тёмные ячейки = простой → сюда Happy Hours.
          </p>
          {!data?.cells?.length ? (
            <Empty description={<span className="text-titanium">Нет данных за период</span>} />
          ) : (
            <div className="discount-heatmap-wrap">
              <table className="discount-heatmap">
                <thead>
                  <tr>
                    <th />
                    {DAY_NAMES.map((d) => (
                      <th key={d}>{d}</th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {HOURS.map((hour) => (
                    <tr key={hour}>
                      <td className="hour">{String(hour).padStart(2, '0')}:00</td>
                      {DAY_NAMES.map((_, day) => {
                        const count = getCount(day, hour);
                        return (
                          <Tooltip key={`${day}-${hour}`} title={`${DAY_NAMES[day]} ${hour}:00 — ${count} записей`}>
                            <td style={{ background: cellColor(count, maxCount) }}>
                              <span>{count || ''}</span>
                            </td>
                          </Tooltip>
                        );
                      })}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </Card>

        <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
          <div className="flex-space-between mb-12">
            <Text className="admin-panel-title">
              <ThunderboltOutlined /> Авто-предложения по данным
            </Text>
          </div>
          <p className="discount-intel-hint">
            Скидка считается относительно пика на теплокарте: яркие часы (11–12, пик) — без Happy Hours;
            тёмные (простой: обед, вечер 18–20) — скидка 15–25%. Пн–Пт, Сб и Вс считаются отдельно.
          </p>
          {!data?.suggestions?.length ? (
            <Empty description={<span className="text-titanium">Нет слотов для скидок — загрузка равномерная</span>} />
          ) : (
            <div className="discount-suggest-grid">
              {data.suggestions.map((s) => (
                <div key={s.key} className="discount-suggest-card">
                  <div className="top">
                    <Tag color="gold">{s.weekday_label}</Tag>
                    <span className="pct">−{s.discount_percent}%</span>
                  </div>
                  <div className="slot">{s.hour_start}–{s.hour_end}</div>
                  <div className="meta">ср. загрузка {s.avg_load}</div>
                  <div className="reason">{s.reason}</div>
                  <Button
                    className="btn-gold"
                    size="small"
                    icon={<GiftOutlined />}
                    loading={creatingKey === s.key}
                    onClick={() => handleCreate(s)}
                  >
                    Создать
                  </Button>
                </div>
              ))}
            </div>
          )}
        </Card>

        <Row gutter={[16, 16]}>
          <Col xs={24} lg={12}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title"><BulbOutlined /> Рекомендации</Text>
              <div style={{ marginTop: 12 }}>
                {(data?.recommendations || []).length === 0 ? (
                  <Text className="text-titanium text-13">Пока нет рекомендаций</Text>
                ) : (
                  <Space direction="vertical" size={8} style={{ width: '100%' }}>
                    {data!.recommendations.map((r, idx) => (
                      <div key={`${r.rule_name}-${idx}`} className="discount-advice-row">
                        <Tag color={ACTION_COLORS[r.action] || 'default'}>{ACTION_LABELS[r.action] || r.action}</Tag>
                        <div>
                          <div className="name">{r.rule_name}</div>
                          <div className="msg">{r.message}</div>
                        </div>
                        {r.action === 'create' && onApplyAdvice && (
                          <Button size="small" className="btn-gold-secondary" onClick={() => onApplyAdvice(r)}>
                            К созданию
                          </Button>
                        )}
                      </div>
                    ))}
                  </Space>
                )}
              </div>
            </Card>
          </Col>
          <Col xs={24} lg={12}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">ROI по скидкам</Text>
              <Table
                style={{ marginTop: 12 }}
                size="small"
                pagination={false}
                rowKey="rule_id"
                dataSource={data?.roi || []}
                locale={{ emptyText: 'Нет применений скидок' }}
                columns={[
                  {
                    title: <Text className="text-gold text-12">Правило</Text>,
                    dataIndex: 'rule_name',
                    render: (v) => <Text className="text-white text-13">{v}</Text>,
                  },
                  {
                    title: <Text className="text-gold text-12">Потеря</Text>,
                    dataIndex: 'discount_cost',
                    render: (v) => <Text className="text-13">{Number(v).toLocaleString()} ₽</Text>,
                  },
                  {
                    title: <Text className="text-gold text-12">Оценка выручки</Text>,
                    dataIndex: 'estimated_extra_revenue',
                    render: (v) => <Text className="text-gold-bold text-13">{Number(v).toLocaleString()} ₽</Text>,
                  },
                  {
                    title: <Text className="text-gold text-12">ROI</Text>,
                    dataIndex: 'roi_percent',
                    render: (v, r) => (
                      <Tag color={v >= 20 ? 'green' : v >= 0 ? 'orange' : 'red'}>
                        {v}% · {r.verdict}
                      </Tag>
                    ),
                  },
                ]}
              />
            </Card>
          </Col>
        </Row>

        {chartData.length > 0 && (
          <Card className="admin-panel-card" bordered={false} style={{ marginTop: 16 }}>
            <Text className="admin-panel-title">До / После введения скидки</Text>
            <p className="discount-intel-hint">Средняя загрузка слота за 30 дней до и после создания правила</p>
            <div style={{ width: '100%', height: 260, marginTop: 8 }}>
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
          </Card>
        )}
      </Spin>
    </div>
  );
}
