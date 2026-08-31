/**
 * Главная / Обзор — /dashboard
 * Локальный fetch: KPI, очередь pending, число услуг. Без Context.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Card,
  Row,
  Col,
  Tag,
  Space,
  Badge,
  List,
  Empty,
  Spin,
} from 'antd';
import { Button } from '../../components/ui';
import {
  CalendarOutlined, ClockCircleOutlined,
  CheckCircleOutlined, DollarOutlined, ReloadOutlined, InsertRowAboveOutlined,
} from '@ant-design/icons';
import {
  AreaChart, Area, ResponsiveContainer,
} from 'recharts';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import { useBrand } from '../../design';

dayjs.locale('ru');

const API_BASE = '';

interface SparkPoint {
  date: string;
  value: number;
}

interface KpiData {
  total_clients: number;
  total_masters: number;
  today_appointments: number;
  today_revenue: number;
  month_revenue: number;
  pending_appointments: number;
  completed_month: number;
  occupancy_pct?: number;
  week_revenue?: number;
  week_change_percent?: number;
  sparkline_revenue?: SparkPoint[];
  sparkline_appointments?: SparkPoint[];
  sparkline_completed?: SparkPoint[];
}

interface PendingAppt {
  id: number;
  start_time: string;
  status: string;
  service_name?: string;
  client?: { id: number; full_name: string; phone: string };
}

interface LiveBoxChip {
  box_id: number;
  name: string;
  state: string;
  state_label: string;
  current?: { service_name: string; overrun?: boolean } | null;
}

interface FinancierRec {
  id: string;
  cause: string;
  action: string;
  effect_rub: number;
  kind: string;
}

const STATUS_COLORS: Record<string, string> = {
  pending: 'gold',
  confirmed: 'blue',
  in_progress: 'cyan',
  completed: 'green',
  cancelled: 'red',
  no_show: 'default',
};

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  in_progress: 'В работе',
  completed: 'Выполнена',
  cancelled: 'Отменена',
  no_show: 'Не явился',
};

function boxTone(b: LiveBoxChip): 'free' | 'gold' | 'amber' | 'red' {
  if (b.current?.overrun) return 'red';
  if (b.state === 'free') return 'free';
  if (b.state === 'preparing') return 'amber';
  if (b.state === 'inactive') return 'amber';
  return 'gold';
}

function recPath(kind: string) {
  if (kind === 'box') return '/upload/boxes';
  if (kind === 'pnl') return '/analytics/finances';
  return '/discounts';
}

function KpiSpark({ data, warn }: { data?: SparkPoint[]; warn?: boolean }) {
  if (!data || data.length < 2) return null;
  const stroke = warn ? '#E8A54B' : '#C8A977';
  return (
    <div className="admin-kpi-spark">
      <ResponsiveContainer width="100%" height={36}>
        <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <Area type="monotone" dataKey="value" stroke={stroke} fill={stroke} fillOpacity={0.18} strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
}

async function apiFetch<T>(path: string): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

export default function DashboardPage() {
  const navigate = useNavigate();
  const { brand } = useBrand();

  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);
  const [pendingList, setPendingList] = useState<PendingAppt[]>([]);
  const [liveBoxes, setLiveBoxes] = useState<LiveBoxChip[]>([]);
  const [insight, setInsight] = useState<FinancierRec | null>(null);

  const refresh = useCallback(async () => {
    setKpiLoading(true);
    try {
      const [kpiData, appts, live, brief] = await Promise.all([
        apiFetch<KpiData>('/api/analytics/kpi'),
        apiFetch<{ items: PendingAppt[] }>('/api/appointments?skip=0&limit=100'),
        apiFetch<{ boxes: LiveBoxChip[] }>('/api/boxes/live').catch(() => ({ boxes: [] })),
        apiFetch<{ recommendations?: FinancierRec[] }>('/api/ai/financier/brief').catch(() => ({
          recommendations: [],
        })),
      ]);
      setKpi(kpiData);
      setPendingList(
        appts.items
          .filter((a) => a.status === 'pending' || a.status === 'confirmed')
          .slice(0, 5),
      );
      setLiveBoxes(live.boxes || []);
      setInsight(brief.recommendations?.[0] || null);
    } catch { /* ignore */ }
    setKpiLoading(false);
  }, []);

  const formatRevenue = (val: number) =>
    `${Number(val || 0).toLocaleString('ru-RU')} ₽`;

  useEffect(() => {
    refresh();
  }, [refresh]);

  const goRecords = () => navigate('/upload/records');

  return (
    <div className="admin-overview">
      <div className="admin-overview-hero">
        <div>
          <div className="admin-overview-kicker">Command Center</div>
          <h2>Контроль салона</h2>
          <p className="admin-overview-date">
            {dayjs().format('D MMMM YYYY, dddd')} · загрузка, прибыль и боксы в одном месте
          </p>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} look="ghost" onClick={refresh}>
            Обновить
          </Button>
          <Button type="primary" look="gold" onClick={goRecords}>
            К записям
          </Button>
          <Button look="ghost" icon={<InsertRowAboveOutlined />} onClick={() => navigate('/upload/boxes')}>
            Боксы
          </Button>
          <Button look="ghost" onClick={() => navigate('/onboarding')}>
            Настройка салона
          </Button>
        </Space>
      </div>

      <Spin spinning={kpiLoading}>
        <Row gutter={[14, 14]} className="admin-kpi-row">
          {[
            { label: 'Записи сегодня', value: kpi?.today_appointments || 0, icon: <CalendarOutlined />, tone: 'gold', spark: kpi?.sparkline_appointments },
            { label: 'Загрузка боксов', value: `${Number(kpi?.occupancy_pct || 0).toLocaleString('ru-RU')}%`, icon: <InsertRowAboveOutlined />, tone: 'gold', spark: undefined as SparkPoint[] | undefined },
            { label: 'Выручка недели', value: formatRevenue(kpi?.week_revenue || 0), icon: <DollarOutlined />, tone: (kpi?.week_change_percent || 0) < 0 ? 'warn' : 'gold', spark: kpi?.sparkline_revenue },
            { label: 'К прошлой неделе', value: `${(kpi?.week_change_percent || 0) > 0 ? '+' : ''}${kpi?.week_change_percent || 0}%`, icon: <DollarOutlined />, tone: (kpi?.week_change_percent || 0) < 0 ? 'warn' : 'ok', spark: undefined },
            { label: 'Ожидают', value: kpi?.pending_appointments || 0, icon: <ClockCircleOutlined />, tone: 'warn', spark: undefined },
            { label: 'Закрыто за месяц', value: kpi?.completed_month || 0, icon: <CheckCircleOutlined />, tone: 'gold', spark: kpi?.sparkline_completed },
          ].map((m) => (
            <Col xs={12} sm={8} lg={8} key={m.label}>
              <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                <Card className={`admin-kpi-card tone-${m.tone}`} bordered={false}>
                  <div className="admin-kpi-icon">{m.icon}</div>
                  <div className="admin-kpi-label">{m.label}</div>
                  <div className="admin-kpi-value">{m.value}</div>
                  <KpiSpark data={m.spark} warn={m.tone === 'warn'} />
                </Card>
              </motion.div>
            </Col>
          ))}
        </Row>
      </Spin>

      {liveBoxes.length > 0 && (
        <Card
          className="admin-panel-card"
          bordered={false}
          style={{ marginTop: 16 }}
          title={<span className="admin-panel-title">Боксы сейчас</span>}
          extra={
            <Button size="small" look="ghost" onClick={() => navigate('/upload/boxes')}>
              Сетка
            </Button>
          }
        >
          <Space wrap>
            {liveBoxes.map((b) => (
              <span
                key={b.box_id}
                className={`box-live-chip box-live-chip--${boxTone(b)}`}
                onClick={() => navigate('/upload/boxes')}
                role="button"
                tabIndex={0}
              >
                {b.name}: {b.state_label}
                {b.current?.service_name ? ` · ${b.current.service_name}` : ''}
                {b.current?.overrun ? ' · задержка' : ''}
              </span>
            ))}
          </Space>
        </Card>
      )}

      {insight ? (
        <Card
          className="admin-panel-card admin-insight-card"
          bordered={false}
          style={{ marginTop: 16 }}
          title={<span className="admin-panel-title">Инсайт AI-финансиста</span>}
          extra={
            <Button size="small" look="gold" onClick={() => navigate(recPath(insight.kind))}>
              Применить рекомендацию
            </Button>
          }
        >
          <p className="admin-insight-cause">{insight.cause}</p>
          <p className="admin-insight-action">{insight.action}</p>
          {insight.effect_rub ? (
            <p className="admin-insight-effect">
              Ожидаемый эффект: +{insight.effect_rub.toLocaleString('ru-RU')} ₽
            </p>
          ) : null}
        </Card>
      ) : null}

      <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
        <Col span={24}>
          <Card
            className="admin-panel-card card-important"
            bordered={false}
            title={<span className="admin-panel-title">Требуют внимания</span>}
            extra={
              <Badge
                count={kpi?.pending_appointments || pendingList.length}
                style={{ backgroundColor: brand.colors.accent.solid }}
              />
            }
          >
            {pendingList.length === 0 ? (
              <Empty description={<span className="text-titanium">Очереди нет</span>} />
            ) : (
              <List
                dataSource={pendingList}
                renderItem={(item) => (
                  <List.Item className="admin-attention-item" onClick={goRecords}>
                    <List.Item.Meta
                      title={
                        <span className="text-white">
                          {item.service_name || `Запись #${item.id}`}
                        </span>
                      }
                      description={
                        <span className="text-titanium">
                          {dayjs(item.start_time).format('DD.MM HH:mm')}
                          {item.client ? ` · ${item.client.full_name}` : ''}
                        </span>
                      }
                    />
                    <Tag color={STATUS_COLORS[item.status]}>
                      {STATUS_LABELS[item.status]}
                    </Tag>
                  </List.Item>
                )}
              />
            )}
          </Card>
        </Col>
      </Row>
    </div>
  );
}
