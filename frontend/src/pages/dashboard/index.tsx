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
  TeamOutlined, ToolOutlined, CalendarOutlined, ClockCircleOutlined,
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
  current?: { service_name: string } | null;
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

  const refresh = useCallback(async () => {
    setKpiLoading(true);
    try {
      const [kpiData, appts, live] = await Promise.all([
        apiFetch<KpiData>('/api/analytics/kpi'),
        apiFetch<{ items: PendingAppt[] }>('/api/appointments?skip=0&limit=100'),
        apiFetch<{ boxes: LiveBoxChip[] }>('/api/boxes/live').catch(() => ({ boxes: [] })),
      ]);
      setKpi(kpiData);
      setPendingList(
        appts.items
          .filter((a) => a.status === 'pending' || a.status === 'confirmed')
          .slice(0, 5),
      );
      setLiveBoxes(live.boxes || []);
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
          <div className="admin-overview-kicker">Обзор салона</div>
          <h2>Ключевые показатели</h2>
          <p className="admin-overview-date">
            {dayjs().format('D MMMM YYYY, dddd')} · все ключевые показатели в одном месте
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
        </Space>
      </div>

      <Spin spinning={kpiLoading}>
        <Row gutter={[14, 14]} className="admin-kpi-row">
          {[
            { label: 'Клиенты', value: kpi?.total_clients || 0, icon: <TeamOutlined />, tone: 'gold', spark: undefined as SparkPoint[] | undefined },
            { label: 'Мастера', value: kpi?.total_masters || 0, icon: <ToolOutlined />, tone: 'gold', spark: undefined },
            { label: 'Записи', value: kpi?.today_appointments || 0, icon: <CalendarOutlined />, tone: 'gold', spark: kpi?.sparkline_appointments },
            { label: 'Выручка', value: formatRevenue(kpi?.month_revenue || 0), icon: <DollarOutlined />, tone: 'gold', spark: kpi?.sparkline_revenue },
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
              <Tag
                key={b.box_id}
                style={{ cursor: 'pointer', padding: '4px 10px' }}
                onClick={() => navigate('/upload/boxes')}
              >
                {b.name}: {b.state_label}
                {b.current?.service_name ? ` · ${b.current.service_name}` : ''}
              </Tag>
            ))}
          </Space>
        </Card>
      )}

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
