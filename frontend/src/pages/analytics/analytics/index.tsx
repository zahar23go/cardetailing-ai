/**
 * Аналитика — /analytics/analytics
 * Выручка, воронка, теплокарта + настройка боксов. Локальный state.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography, Card, Row, Col, Statistic, Button, Tag, Space,
  message, Modal, Select, Input, Popconfirm, List,
  Spin, Tooltip, DatePicker, ColorPicker,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, ReloadOutlined,
} from '@ant-design/icons';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';

dayjs.locale('ru');

const { Text } = Typography;
const { Option } = Select;

const API_BASE = '';

interface Service {
  id: number;
  name: string;
}

interface Appointment {
  id: number;
  client_id: number;
  master_id: number | null;
  service_id: number;
  start_time: string;
  end_time: string;
  status: string;
  total_price: number;
  service_name: string | null;
  client?: { id: number; full_name: string; phone: string };
  master?: { id: number; full_name: string };
}

interface RevenuePoint {
  date: string;
  revenue: number;
  appointments: number;
}

interface RevenueData {
  daily: RevenuePoint[];
  total: number;
  avg_per_day: number;
  best_day: string | null;
  worst_day: string | null;
  previous_total: number;
  change_percent: number;
  previous_avg_per_day: number;
}

interface HeatmapCell {
  day: number;
  hour: number;
  count: number;
  revenue: number;
  box_id?: number | null;
}

interface BoxItem {
  id: number;
  name: string;
  color?: string | null;
  sort_order: number;
  is_active: boolean;
  service_ids: number[];
}

interface FunnelStage {
  name: string;
  value: number;
  percent: number;
  color: string;
}

interface FunnelData {
  stages: FunnelStage[];
  total: number;
  conversion_rate: number;
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

const COLOR_MAP: Record<string, string> = {
  'красный': '#FF6B6B',
  'синий': '#4DABF7',
  'зелёный': '#4ECB71',
  'зеленый': '#4ECB71',
  'жёлтый': '#FFD93D',
  'желтый': '#FFD93D',
  'оранжевый': '#FF9F43',
  'фиолетовый': '#A66CFF',
  'розовый': '#FF6B9D',
  'серый': '#95A5A6',
  'чёрный': '#2D3436',
  'черный': '#2D3436',
  'белый': '#FFFFFF',
};

function normalizeColor(color: string | null | undefined): string | null {
  if (!color) return null;
  const trimmed = color.trim();
  if (!trimmed) return null;
  if (/^#[0-9A-Fa-f]{3,8}$/.test(trimmed)) return trimmed;
  return COLOR_MAP[trimmed.toLowerCase()] || trimmed;
}

function hexToRgbArray(hex: string): number[] {
  const clean = hex.replace('#', '');
  if (clean.length === 3) {
    return [
      parseInt(clean[0] + clean[0], 16),
      parseInt(clean[1] + clean[1], 16),
      parseInt(clean[2] + clean[2], 16),
    ];
  }
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ];
}

function hexToRgb(hex: string): string {
  return hexToRgbArray(hex).join(', ');
}

function isLightColor(color: string | null | undefined): boolean {
  if (!color) return false;
  try {
    const [r, g, b] = hexToRgbArray(color);
    return 0.299 * r + 0.587 * g + 0.114 * b > 180;
  } catch {
    return false;
  }
}

function formatCurrency(val: number) {
  return `${val.toLocaleString()} ₽`;
}

async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
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

export default function AnalyticsPage() {
  const [revenueData, setRevenueData] = useState<RevenueData | null>(null);
  const [revenueLoading, setRevenueLoading] = useState(false);
  const [heatmapData, setHeatmapData] = useState<HeatmapCell[]>([]);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [boxes, setBoxes] = useState<BoxItem[]>([]);
  const [selectedBoxId, setSelectedBoxId] = useState<number | undefined>(undefined);
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
  const [funnelLoading, setFunnelLoading] = useState(false);
  const [services, setServices] = useState<Service[]>([]);

  const [boxSettingsModal, setBoxSettingsModal] = useState(false);
  const [boxesFull, setBoxesFull] = useState<any[]>([]);
  const [boxSettingsSaving, setBoxSettingsSaving] = useState(false);
  const [boxEditServices, setBoxEditServices] = useState<Record<number, number[]>>({});
  const [newBoxName, setNewBoxName] = useState('');
  const [newBoxColor, setNewBoxColor] = useState('');
  const [creatingBox, setCreatingBox] = useState(false);
  const [editingBox, setEditingBox] = useState<any>(null);
  const [editBoxModalOpen, setEditBoxModalOpen] = useState(false);

  const [heatmapModalOpen, setHeatmapModalOpen] = useState(false);
  const [heatmapSlotAppts, setHeatmapSlotAppts] = useState<Appointment[]>([]);
  const [heatmapSlotLabel, setHeatmapSlotLabel] = useState('');

  const [periodStart, setPeriodStart] = useState<string | null>(null);
  const [periodEnd, setPeriodEnd] = useState<string | null>(null);

  const fetchRevenueChart = async (start?: string, end?: string) => {
    setRevenueLoading(true);
    try {
      let path = '/api/analytics/revenue';
      const params = new URLSearchParams();
      params.set('_t', String(Date.now()));
      if (start && end) {
        params.set('start_date', start);
        params.set('end_date', end);
      }
      path += `?${params.toString()}`;
      setRevenueData(await apiFetch<RevenueData>(path));
    } catch { /* ignore */ }
    setRevenueLoading(false);
  };

  const fetchHeatmap = async (boxId?: number) => {
    setHeatmapLoading(true);
    try {
      let path = '/api/analytics/heatmap?days=60';
      if (boxId !== undefined) path += `&box_id=${boxId}`;
      const data = await apiFetch<{ cells: HeatmapCell[]; boxes: BoxItem[] }>(path);
      setHeatmapData(data.cells);
      if (data.boxes) setBoxes(data.boxes);
    } catch { /* ignore */ }
    setHeatmapLoading(false);
  };

  const fetchBoxes = async () => {
    try {
      const data = await apiFetch<any[]>('/api/boxes');
      setBoxes(data.map((b: any) => ({
        id: b.id,
        name: b.name,
        color: b.color,
        sort_order: b.sort_order,
        is_active: b.is_active,
        service_ids: b.service_ids || [],
      })));
    } catch { /* ignore */ }
  };

  const fetchBoxesFull = async () => {
    try {
      setBoxesFull(await apiFetch<any[]>('/api/boxes'));
    } catch {
      message.error('Ошибка загрузки боксов');
    }
  };

  const fetchFunnel = async (start?: string, end?: string) => {
    setFunnelLoading(true);
    try {
      let path = '/api/analytics/funnel';
      const params = new URLSearchParams();
      params.set('_t', String(Date.now()));
      if (start && end) {
        params.set('start_date', start);
        params.set('end_date', end);
      }
      path += `?${params.toString()}`;
      setFunnelData(await apiFetch<FunnelData>(path));
    } catch { /* ignore */ }
    setFunnelLoading(false);
  };

  const fetchServices = async () => {
    try {
      const data = await apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=500');
      setServices(data.items);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchRevenueChart();
    fetchBoxes();
    fetchBoxesFull();
    fetchHeatmap();
    fetchFunnel();
    fetchServices();
  }, []);

  const handleSaveBoxSettings = async (boxId: number, serviceIds: number[]) => {
    setBoxSettingsSaving(true);
    try {
      await apiFetch(`/api/boxes/${boxId}`, {
        method: 'PUT',
        body: JSON.stringify({ service_ids: serviceIds }),
      });
      message.success('Настройки бокса сохранены');
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setBoxSettingsSaving(false);
  };

  const handleCreateBox = async () => {
    if (!newBoxName.trim()) { message.warning('Укажите название бокса'); return; }
    setCreatingBox(true);
    try {
      await apiFetch('/api/boxes', {
        method: 'POST',
        body: JSON.stringify({
          name: newBoxName.trim(),
          color: normalizeColor(newBoxColor),
          sort_order: boxesFull.length,
          is_active: true,
        }),
      });
      message.success('✅ Бокс создан');
      setNewBoxName('');
      setNewBoxColor('');
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка создания бокса');
    }
    setCreatingBox(false);
  };

  const handleDeleteBox = async (boxId: number, boxName: string) => {
    try {
      await apiFetch(`/api/boxes/${boxId}`, { method: 'DELETE' });
      message.success(`✅ Бокс «${boxName}» удалён`);
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления бокса');
    }
  };

  const openEditBoxModal = (box: any) => {
    setEditingBox(box);
    setBoxEditServices((prev) => ({ ...prev, [box.id]: box.service_ids || [] }));
    setEditBoxModalOpen(true);
  };

  const handleEditBox = async () => {
    if (!editingBox) return;
    if (!editingBox.name?.trim()) { message.warning('Укажите название бокса'); return; }
    setBoxSettingsSaving(true);
    try {
      await apiFetch(`/api/boxes/${editingBox.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editingBox.name.trim(),
          color: normalizeColor(editingBox.color),
          service_ids: boxEditServices[editingBox.id] || [],
        }),
      });
      message.success('✅ Бокс обновлён');
      setEditBoxModalOpen(false);
      setEditingBox(null);
      fetchBoxes();
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления бокса');
    }
    setBoxSettingsSaving(false);
  };

  const handleHeatmapCellClick = async (day: number, hour: number) => {
    const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const cell = heatmapData.find((c) => c.day === day && c.hour === hour);
    const count = cell?.count || 0;
    setHeatmapSlotLabel(`${dayNames[day]} ${hour}:00 (${count} зап.)`);
    setHeatmapModalOpen(true);
    try {
      const data = await apiFetch<{ items: Appointment[] }>('/api/appointments?skip=0&limit=500');
      const filtered = data.items.filter((a) => {
        const start = new Date(a.start_time);
        return start.getDay() === day && start.getHours() === hour;
      });
      filtered.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
      setHeatmapSlotAppts(filtered);
    } catch {
      setHeatmapSlotAppts([]);
    }
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Метрики</div>
          <h3>Аналитика</h3>
        </div>
      </div>

      <Spin spinning={revenueLoading || heatmapLoading || funnelLoading}>
        <Row gutter={[16, 16]}>
          <Col xs={24} lg={14}>
            <Card className="card-luxury">
              <div className="flex-space-between mb-12" style={{ flexWrap: 'wrap', gap: 8 }}>
                <Text className="title-gold text-16">Выручка</Text>
                <Space size="small" wrap>
                  <Button
                    size="small"
                    className={!periodStart ? 'btn-gold' : 'btn-logout'}
                    onClick={() => {
                      setPeriodStart(null);
                      setPeriodEnd(null);
                      fetchRevenueChart();
                    }}
                  >
                    Месяц
                  </Button>
                  <Button
                    size="small"
                    className={periodStart ? 'btn-gold' : 'btn-logout'}
                    onClick={() => {
                      const end = dayjs();
                      const start = end.subtract(7, 'day');
                      setPeriodStart(start.format('YYYY-MM-DD'));
                      setPeriodEnd(end.format('YYYY-MM-DD'));
                      fetchRevenueChart(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'));
                    }}
                  >
                    Неделя
                  </Button>
                  <DatePicker.RangePicker
                    size="small"
                    className="input-luxury"
                    style={{ width: 200 }}
                    onChange={(dates) => {
                      if (dates && dates[0] && dates[1]) {
                        const s = dates[0].format('YYYY-MM-DD');
                        const e = dates[1].format('YYYY-MM-DD');
                        setPeriodStart(s);
                        setPeriodEnd(e);
                        fetchRevenueChart(s, e);
                      }
                    }}
                  />
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => fetchRevenueChart(periodStart || undefined, periodEnd || undefined)}
                    type="text"
                    className="btn-logout"
                  />
                </Space>
              </div>

              {revenueData && (
                <Row gutter={[12, 12]} className="mb-12">
                  <Col xs={12} sm={6}>
                    <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                      <Statistic
                        title={<Text className="text-titanium text-11">Текущий период</Text>}
                        value={revenueData.total}
                        precision={0}
                        suffix={<Text className="text-titanium text-11">₽</Text>}
                        valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                      <Statistic
                        title={<Text className="text-titanium text-11">Прошлый период</Text>}
                        value={revenueData.previous_total}
                        precision={0}
                        suffix={<Text className="text-titanium text-11">₽</Text>}
                        valueStyle={{ color: '#AAB2BF', fontSize: '18px', fontWeight: 700 }}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                      <Statistic
                        title={<Text className="text-titanium text-11">Изменение</Text>}
                        value={revenueData.change_percent}
                        precision={1}
                        suffix={<Text className="text-titanium text-11">%</Text>}
                        valueStyle={{
                          color: revenueData.change_percent >= 0 ? '#4ECB71' : '#ff4d4f',
                          fontSize: '18px',
                          fontWeight: 700,
                        }}
                        prefix={revenueData.change_percent >= 0 ? '↑' : '↓'}
                      />
                    </Card>
                  </Col>
                  <Col xs={12} sm={6}>
                    <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                      <Statistic
                        title={<Text className="text-titanium text-11">В день (тек./прош.)</Text>}
                        value={revenueData.avg_per_day}
                        precision={0}
                        suffix={(
                          <Text className="text-titanium text-11">
                            / {revenueData.previous_avg_per_day.toLocaleString()} ₽
                          </Text>
                        )}
                        valueStyle={{ color: '#FFFFFF', fontSize: '16px', fontWeight: 600 }}
                      />
                    </Card>
                  </Col>
                </Row>
              )}

              {revenueData && revenueData.daily.length > 0 ? (
                <ResponsiveContainer width="100%" height={260}>
                  <AreaChart data={revenueData.daily}>
                    <defs>
                      <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="5%" stopColor="#C8A977" stopOpacity={0.3} />
                        <stop offset="95%" stopColor="#C8A977" stopOpacity={0} />
                      </linearGradient>
                    </defs>
                    <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                    <XAxis
                      dataKey="date"
                      tick={{ fill: '#AAB2BF', fontSize: 10 }}
                      tickFormatter={(v) => v.slice(8, 10)}
                      axisLine={false}
                      tickLine={false}
                    />
                    <YAxis
                      tick={{ fill: '#AAB2BF', fontSize: 10 }}
                      axisLine={false}
                      tickLine={false}
                      tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`}
                    />
                    <RechartsTooltip
                      contentStyle={{
                        backgroundColor: '#13161A',
                        border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '10px',
                        color: '#AAB2BF',
                      }}
                      formatter={(value: number) => [`${value.toLocaleString()} ₽`, 'Выручка']}
                      labelFormatter={(label) => `📅 ${label}`}
                    />
                    <Area
                      type="monotone"
                      dataKey="revenue"
                      stroke="#C8A977"
                      fill="url(#revenueGradient)"
                      strokeWidth={2}
                    />
                  </AreaChart>
                </ResponsiveContainer>
              ) : (
                <div className="text-center" style={{ padding: '60px 0' }}>
                  <Text className="text-titanium text-13">Нет данных за выбранный период</Text>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24} lg={10}>
            <Card className="card-luxury">
              <div className="flex-space-between mb-12">
                <Text className="title-gold text-16">Воронка продаж</Text>
                <Space size="small">
                  {funnelData && (
                    <Text className="text-titanium text-12">
                      Конверсия:{' '}
                      <Text className="text-gold-bold">{funnelData.conversion_rate}%</Text>
                    </Text>
                  )}
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => fetchFunnel(periodStart || undefined, periodEnd || undefined)}
                    type="text"
                    className="btn-logout"
                  />
                </Space>
              </div>
              {funnelData && funnelData.stages.length > 0 ? (
                <div style={{ height: 260 }}>
                  {funnelData.stages.map((stage, i) => {
                    const maxVal = funnelData.stages[0]?.value || 1;
                    const widthPct = (stage.value / maxVal) * 100;
                    return (
                      <div key={stage.name} className="mb-8">
                        <div className="flex-space-between" style={{ marginBottom: 4 }}>
                          <Text className="text-titanium text-12">{stage.name}</Text>
                          <Space size="small">
                            <Text className="text-white-bold text-13">{stage.value}</Text>
                            <Text className="text-titanium text-11">({stage.percent}%)</Text>
                          </Space>
                        </div>
                        <div
                          style={{
                            height: 22,
                            backgroundColor: 'rgba(255,255,255,0.04)',
                            borderRadius: 6,
                            overflow: 'hidden',
                          }}
                        >
                          <div
                            style={{
                              height: '100%',
                              width: `${widthPct}%`,
                              backgroundColor: stage.color,
                              borderRadius: 6,
                              opacity: 1 - i * 0.15,
                            }}
                          />
                        </div>
                      </div>
                    );
                  })}
                </div>
              ) : (
                <div className="text-center" style={{ padding: '60px 0' }}>
                  <Text className="text-titanium text-13">Нет данных за месяц</Text>
                </div>
              )}
            </Card>
          </Col>

          <Col xs={24}>
            <Card className="card-luxury">
              <div className="flex-space-between mb-12">
                <Text className="title-gold text-16">Тепловая карта загрузки</Text>
                <Space size="small" wrap>
                  <Select
                    size="small"
                    className="input-luxury"
                    placeholder="Все боксы"
                    value={selectedBoxId}
                    onChange={(v) => {
                      setSelectedBoxId(v);
                      fetchHeatmap(v);
                    }}
                    allowClear
                    style={{ minWidth: 160 }}
                    onClear={() => {
                      setSelectedBoxId(undefined);
                      fetchHeatmap(undefined);
                    }}
                  >
                    {boxes
                      .filter((b) => b.is_active !== false)
                      .sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0))
                      .map((b) => {
                        const boxServiceNames = (b.service_ids || [])
                          .map((sid: number) => services.find((s) => s.id === sid)?.name)
                          .filter(Boolean)
                          .join(', ');
                        return (
                          <Option key={b.id} value={b.id}>
                            <Tooltip title={boxServiceNames || 'Нет услуг'} mouseEnterDelay={0.5}>
                              <Space size={4}>
                                <div
                                  style={{
                                    width: 28,
                                    height: 28,
                                    borderRadius: '50%',
                                    backgroundColor: b.color || '#C8A977',
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    color: isLightColor(b.color) ? '#000000' : '#FFFFFF',
                                    fontSize: 12,
                                    fontWeight: 700,
                                    flexShrink: 0,
                                    cursor: 'pointer',
                                    textShadow: '0 1px 3px rgba(0,0,0,0.5)',
                                  }}
                                >
                                  {b.id}
                                </div>
                                <span style={{ color: '#FFFFFF' }}>{b.name}</span>
                              </Space>
                            </Tooltip>
                          </Option>
                        );
                      })}
                  </Select>
                  <Button
                    size="small"
                    icon={<EditOutlined />}
                    onClick={() => setBoxSettingsModal(true)}
                    className="btn-action-gold"
                  >
                    Настройка
                  </Button>
                  <Button
                    size="small"
                    icon={<ReloadOutlined />}
                    onClick={() => fetchHeatmap(selectedBoxId)}
                    type="text"
                    className="btn-logout"
                  />
                </Space>
              </div>

              {heatmapData.length > 0 ? (
                <>
                  <div className="flex-space-between" style={{ marginBottom: 8, paddingLeft: 40 }}>
                    {[8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22].map((h) => (
                      <Text key={h} className="text-titanium text-11" style={{ width: '6.66%', textAlign: 'center' }}>
                        {h}:00
                      </Text>
                    ))}
                  </div>
                  {[0, 1, 2, 3, 4, 5, 6].map((day) => {
                    const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
                    const maxCount = Math.max(...heatmapData.map((c) => c.count), 1);
                    const selectedBoxColor = boxes.find((b) => b.id === selectedBoxId)?.color;
                    const boxRgb = selectedBoxColor ? hexToRgb(selectedBoxColor) : null;
                    return (
                      <div key={day} className="flex-space-between" style={{ marginBottom: 4 }}>
                        <Text className="text-titanium text-11" style={{ width: 36 }}>{dayNames[day]}</Text>
                        {[8, 9, 10, 11, 12, 13, 14, 15, 16, 17, 18, 19, 20, 21, 22].map((hour) => {
                          const cell = heatmapData.find((c) => c.day === day && c.hour === hour);
                          const count = cell?.count || 0;
                          const intensity = count / maxCount;
                          const bgColor = count > 0
                            ? (boxRgb
                              ? `rgba(${boxRgb}, ${0.15 + intensity * 0.7})`
                              : `rgba(200, 169, 119, ${0.1 + intensity * 0.6})`)
                            : 'rgba(255,255,255,0.02)';
                          return (
                            <div
                              key={`${day}-${hour}`}
                              className="text-center"
                              style={{
                                width: '6.66%',
                                height: 32,
                                backgroundColor: bgColor,
                                borderRadius: 4,
                                display: 'flex',
                                alignItems: 'center',
                                justifyContent: 'center',
                                cursor: 'pointer',
                                ...(selectedBoxId && count > 0
                                  ? {
                                    border: `2px solid ${selectedBoxColor || '#C8A977'}`,
                                    boxShadow: `0 0 6px rgba(${boxRgb}, 0.3)`,
                                  }
                                  : {}),
                              }}
                              title={count > 0 ? `${count} записей · ${cell?.revenue.toLocaleString()} ₽` : '✅ Свободно'}
                              onClick={() => handleHeatmapCellClick(day, hour)}
                            >
                              <Text
                                className="text-11"
                                style={{ color: count > maxCount * 0.5 ? '#0B0D10' : '#AAB2BF' }}
                              >
                                {count || '○'}
                              </Text>
                            </div>
                          );
                        })}
                      </div>
                    );
                  })}
                </>
              ) : (
                <div className="text-center" style={{ padding: '40px 0' }}>
                  <Text className="text-titanium text-13">Нет данных за месяц</Text>
                </div>
              )}
            </Card>
          </Col>
        </Row>
      </Spin>

      <Modal
        title={<Text className="text-gold-bold">⚙️ Настройка боксов</Text>}
        open={boxSettingsModal}
        onCancel={() => { setBoxSettingsModal(false); setNewBoxName(''); setNewBoxColor(''); }}
        footer={null}
        width={600}
        className="modal-command"
        afterOpenChange={async (open) => {
          if (open) {
            const data = await apiFetch<any[]>('/api/boxes');
            setBoxesFull(data);
            const init: Record<number, number[]> = {};
            data.forEach((b: any) => { init[b.id] = b.service_ids || []; });
            setBoxEditServices(init);
            setNewBoxName('');
            setNewBoxColor('');
          }
        }}
      >
        <Spin spinning={boxSettingsSaving || creatingBox}>
          <Card size="small" className="card-luxury" style={{ marginBottom: 16 }}>
            <Text className="text-white text-14 d-block mb-8" style={{ textAlign: 'center' }}>
              ➕ Создать новый бокс
            </Text>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <div
                  style={{
                    backgroundColor: normalizeColor(newBoxColor) || '#4DABF7',
                    borderRadius: 30,
                    padding: '6px 16px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    border: '2px solid rgba(255,255,255,0.15)',
                    minWidth: 240,
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                  }}
                >
                  <Input
                    value={newBoxName}
                    onChange={(e) => setNewBoxName(e.target.value)}
                    placeholder="Название бокса"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: isLightColor(normalizeColor(newBoxColor)) ? '#000000' : '#FFFFFF',
                      fontWeight: 600,
                      fontSize: 16,
                      minWidth: 100,
                      flex: 1,
                      outline: 'none',
                      boxShadow: 'none',
                    }}
                  />
                  <Input
                    value={newBoxColor}
                    onChange={(e) => setNewBoxColor(e.target.value)}
                    placeholder="#C8A977"
                    style={{
                      background: 'rgba(255,255,255,0.15)',
                      border: 'none',
                      color: isLightColor(normalizeColor(newBoxColor)) ? '#000000' : '#FFFFFF',
                      fontSize: 12,
                      width: 80,
                      borderRadius: 12,
                      padding: '4px 8px',
                      outline: 'none',
                      boxShadow: 'none',
                    }}
                  />
                  <ColorPicker
                    value={normalizeColor(newBoxColor) || '#4DABF7'}
                    onChange={(color) => setNewBoxColor(color.toHexString())}
                    size="small"
                  />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <Button
                  className="btn-gold"
                  onClick={handleCreateBox}
                  loading={creatingBox}
                  style={{ width: 200 }}
                >
                  Создать
                </Button>
              </div>
            </Space>
          </Card>

          {boxesFull.length === 0 ? (
            <Text className="text-titanium text-13">Нет боксов. Создайте первый бокс выше.</Text>
          ) : (
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {boxesFull.map((box: any) => (
                <Card key={box.id} size="small" className="card-luxury">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div className="flex-space-between">
                      <Space>
                        <Tooltip
                          title={`Услуги: ${(box.service_ids || []).map((sid: number) => services.find((s) => s.id === sid)?.name).filter(Boolean).join(', ') || 'не выбраны'}`}
                          mouseEnterDelay={0.5}
                        >
                          <Text className="text-white text-14">{box.name}</Text>
                        </Tooltip>
                        <Tag color={box.is_active ? 'green' : 'default'}>
                          {box.is_active ? 'Активен' : 'Неактивен'}
                        </Tag>
                      </Space>
                      <Space>
                        <Button
                          icon={<EditOutlined />}
                          onClick={() => openEditBoxModal(box)}
                          style={{
                            backgroundColor: 'transparent',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: '#C8A977',
                            fontSize: 13,
                            height: 32,
                          }}
                        >
                          Редактировать
                        </Button>
                        <Popconfirm
                          title={`Удалить бокс «${box.name}»?`}
                          description="Записи в этом боксе останутся, но бокс будет удалён."
                          onConfirm={() => handleDeleteBox(box.id, box.name)}
                          okText="Да, удалить"
                          cancelText="Отмена"
                          okButtonProps={{ danger: true }}
                        >
                          <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                        </Popconfirm>
                      </Space>
                    </div>
                    <div>
                      <Text className="text-titanium text-12 d-block mb-4">Привязанные услуги</Text>
                      <Select
                        mode="multiple"
                        size="small"
                        className="w-full input-luxury"
                        placeholder="Выберите услуги"
                        value={boxEditServices[box.id] || []}
                        onChange={(vals) => setBoxEditServices((prev) => ({ ...prev, [box.id]: vals }))}
                        style={{ width: '100%' }}
                      >
                        {services.map((s) => (
                          <Option key={s.id} value={s.id}>{s.name}</Option>
                        ))}
                      </Select>
                      {(boxEditServices[box.id] || []).length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {(boxEditServices[box.id] || []).map((sid: number) => {
                            const svc = services.find((s) => s.id === sid);
                            return svc ? (
                              <Tag key={svc.id} color={box.color || '#C8A977'} style={{ borderRadius: 4 }}>
                                {svc.name}
                              </Tag>
                            ) : null;
                          })}
                        </div>
                      )}
                    </div>
                    <Button
                      size="small"
                      className="btn-gold"
                      style={{ alignSelf: 'flex-end' }}
                      onClick={() => handleSaveBoxSettings(box.id, boxEditServices[box.id] || [])}
                      loading={boxSettingsSaving}
                    >
                      Сохранить
                    </Button>
                  </Space>
                </Card>
              ))}
            </Space>
          )}
        </Spin>
      </Modal>

      <Modal
        title={<Text className="text-gold-bold">✏️ Редактировать бокс</Text>}
        open={editBoxModalOpen}
        onCancel={() => { setEditBoxModalOpen(false); setEditingBox(null); }}
        footer={null}
        width={480}
        className="modal-command"
      >
        {editingBox && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <span className="label-field">Название</span>
              <Input
                size="large"
                className="input-luxury"
                placeholder="Название бокса"
                value={editingBox.name}
                onChange={(e) => setEditingBox((prev: any) => ({ ...prev, name: e.target.value }))}
              />
            </div>
            <div>
              <span className="label-field">Цвет</span>
              <Input
                size="large"
                className="input-luxury"
                placeholder="#C8A977"
                value={editingBox.color || ''}
                onChange={(e) => setEditingBox((prev: any) => ({ ...prev, color: e.target.value }))}
              />
            </div>
            <div>
              <Tooltip title="Выберите услуги, которые доступны в этом боксе" mouseEnterDelay={0.5}>
                <span className="label-field">Привязанные услуги</span>
              </Tooltip>
              <Select
                mode="multiple"
                size="large"
                className="w-full input-luxury"
                placeholder="Выберите услуги"
                value={boxEditServices[editingBox.id] || []}
                onChange={(vals) => setBoxEditServices((prev) => ({ ...prev, [editingBox.id]: vals }))}
                style={{ width: '100%' }}
              >
                {services.map((s) => (
                  <Option key={s.id} value={s.id}>{s.name}</Option>
                ))}
              </Select>
              {(boxEditServices[editingBox.id] || []).length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(boxEditServices[editingBox.id] || []).map((sid: number) => {
                    const svc = services.find((s) => s.id === sid);
                    return svc ? (
                      <Tag key={svc.id} color={editingBox.color || '#C8A977'} style={{ borderRadius: 4 }}>
                        {svc.name}
                      </Tag>
                    ) : null;
                  })}
                </div>
              )}
            </div>
            <Button
              type="primary"
              size="large"
              className="btn-gold"
              onClick={handleEditBox}
              loading={boxSettingsSaving}
            >
              Сохранить
            </Button>
          </Space>
        )}
      </Modal>

      <Modal
        title={<Text className="text-gold-bold">📅 {heatmapSlotLabel}</Text>}
        open={heatmapModalOpen}
        onCancel={() => setHeatmapModalOpen(false)}
        footer={null}
        className="modal-command"
        width={520}
      >
        {heatmapSlotAppts.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center' }}>
            <Text className="text-titanium">Нет записей в этот слот</Text>
          </div>
        ) : (
          <List
            dataSource={heatmapSlotAppts}
            renderItem={(item) => (
              <List.Item style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <Space>
                    <Text className="text-white-bold text-13">
                      {item.service_name || `Услуга #${item.service_id}`}
                    </Text>
                    <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                      {STATUS_LABELS[item.status]}
                    </Tag>
                  </Space>
                  <Space size="small">
                    {item.client && <Text className="text-titanium text-12">👤 {item.client.full_name}</Text>}
                    {item.master && <Text className="text-titanium text-12">🔧 {item.master.full_name}</Text>}
                  </Space>
                  <div className="flex-space-between">
                    <Text className="text-titanium text-12">
                      🕐 {dayjs(item.start_time).format('HH:mm')} — {dayjs(item.end_time).format('HH:mm')}
                    </Text>
                    <Text className="text-gold-bold text-13">{formatCurrency(item.total_price)}</Text>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        )}
      </Modal>
    </>
  );
}
