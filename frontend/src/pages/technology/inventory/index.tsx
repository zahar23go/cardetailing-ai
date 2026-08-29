/**
 * Учёт — /technology/inventory
 * История движений, график остатка, ABC-анализ, критические позиции.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Typography,
  Row,
  Col,
  Table,
  Space,
  Spin,
  Empty,
  Select,
  message,
} from 'antd';
import {
  ReloadOutlined, WarningOutlined, HistoryOutlined,
  BarChartOutlined, AlertOutlined,
} from '@ant-design/icons';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer,
} from 'recharts';
import { Button, Card, Badge } from '../../../components/ui';

const { Text } = Typography;

const API_BASE = '';

interface InventorySummary {
  materials_count: number;
  stock_value: number;
  critical_count: number;
  movements_period: number;
  period_days: number;
}

interface Movement {
  id: number;
  material_id: number;
  material_name: string;
  material_unit: string;
  movement_type: string;
  movement_type_label: string;
  delta: number;
  quantity_before: number;
  quantity_after: number;
  reason?: string | null;
  created_at?: string;
}

interface StockPoint {
  date: string;
  quantity: number;
  value: number;
}

interface AbcRow {
  material_id: number;
  material_name: string;
  category: string;
  unit: string;
  consumption_qty: number;
  consumption_value: number;
  stock_value: number;
  share_percent: number;
  cumulative_percent: number;
  abc_class: string;
  is_low_stock: boolean;
}

interface CriticalRow {
  material_id: number;
  material_name: string;
  sku?: string | null;
  category: string;
  unit: string;
  quantity: number;
  min_quantity: number;
  deficit: number;
  restock_cost: number;
  supplier?: string | null;
}

interface MaterialOption {
  id: number;
  name: string;
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

function formatCurrency(val: number) {
  return `${Number(val || 0).toLocaleString('ru-RU')} ₽`;
}

function formatDate(iso?: string) {
  if (!iso) return '—';
  const d = new Date(iso);
  return d.toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function abcBadge(cls: string) {
  if (cls === 'A') return <Badge variant="danger" size="sm">A</Badge>;
  if (cls === 'B') return <Badge variant="warning" size="sm">B</Badge>;
  return <Badge variant="info" size="sm">C</Badge>;
}

function moveBadge(type: string, label: string) {
  if (type === 'in' || type === 'initial') return <Badge variant="success" size="sm">{label}</Badge>;
  if (type === 'out') return <Badge variant="warning" size="sm">{label}</Badge>;
  return <Badge variant="neutral" size="sm">{label}</Badge>;
}

export default function InventoryPage() {
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);
  const [materialId, setMaterialId] = useState<number | undefined>();
  const [materials, setMaterials] = useState<MaterialOption[]>([]);

  const [summary, setSummary] = useState<InventorySummary | null>(null);
  const [movements, setMovements] = useState<Movement[]>([]);
  const [history, setHistory] = useState<StockPoint[]>([]);
  const [abc, setAbc] = useState<AbcRow[]>([]);
  const [critical, setCritical] = useState<CriticalRow[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const matParam = materialId ? `&material_id=${materialId}` : '';
      const [sum, moves, hist, abcRows, crit, mats] = await Promise.all([
        apiFetch<InventorySummary>(`/api/inventory/summary?days=${days}`),
        apiFetch<{ items: Movement[] }>(`/api/inventory/movements?days=${days}&limit=50${matParam}`),
        apiFetch<StockPoint[]>(`/api/inventory/stock-history?days=${days}${matParam}`),
        apiFetch<AbcRow[]>(`/api/inventory/abc?days=${Math.max(days, 90)}`),
        apiFetch<CriticalRow[]>('/api/inventory/critical'),
        apiFetch<{ items: MaterialOption[] }>('/api/materials?skip=0&limit=500&is_active=true'),
      ]);
      setSummary(sum);
      setMovements(moves.items || []);
      setHistory(hist || []);
      setAbc(abcRows || []);
      setCritical(crit || []);
      setMaterials(mats.items || []);
    } catch {
      message.error('Ошибка загрузки учёта');
    }
    setLoading(false);
  }, [days, materialId]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const chartData = useMemo(
    () => history.map((p) => ({
      ...p,
      label: p.date.slice(5),
    })),
    [history],
  );

  return (
    <>
      <div className="admin-section-head">
        <div>
          <h3>Технология / Учёт</h3>
        </div>
        <Space wrap>
          <Select
            value={days}
            style={{ width: 140 }}
            className="input-luxury"
            onChange={setDays}
            options={[
              { value: 14, label: '14 дней' },
              { value: 30, label: '30 дней' },
              { value: 90, label: '90 дней' },
            ]}
          />
          <Select
            allowClear
            placeholder="Все материалы"
            style={{ minWidth: 220 }}
            className="input-luxury"
            value={materialId}
            onChange={(v) => setMaterialId(v)}
            options={materials.map((m) => ({ value: m.id, label: m.name }))}
            showSearch
            optionFilterProp="label"
          />
          <Button icon={<ReloadOutlined />} look="ghost" onClick={refresh}>
            Обновить
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card variant="kpi">
              <div className="admin-kpi-label">Позиций</div>
              <div className="admin-kpi-value">{summary?.materials_count ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="stats">
              <div className="admin-kpi-label">Стоимость склада</div>
              <div className="admin-kpi-value text-gold-bold">{formatCurrency(summary?.stock_value || 0)}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><WarningOutlined /></div>
              <div className="admin-kpi-label">Критические</div>
              <div className="admin-kpi-value">{summary?.critical_count ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><HistoryOutlined /></div>
              <div className="admin-kpi-label">Движений</div>
              <div className="admin-kpi-value">{summary?.movements_period ?? 0}</div>
            </Card>
          </Col>
        </Row>

        <Card variant="admin" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <BarChartOutlined className="text-gold" />
            <Text className="text-gold-bold">График остатка</Text>
          </div>
          {chartData.length === 0 ? (
            <Empty description={<Text className="text-titanium">Нет данных за период</Text>} />
          ) : (
            <div style={{ width: '100%', height: 260 }}>
              <ResponsiveContainer>
                <AreaChart data={chartData}>
                  <defs>
                    <linearGradient id="invGold" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="5%" stopColor="#C9A227" stopOpacity={0.45} />
                      <stop offset="95%" stopColor="#C9A227" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.08)" />
                  <XAxis dataKey="label" stroke="#9aa0a6" />
                  <YAxis stroke="#9aa0a6" />
                  <RechartsTooltip
                    contentStyle={{ background: '#1a1a1a', border: '1px solid #333' }}
                    formatter={(val: number, name: string) => (
                      name === 'value'
                        ? [formatCurrency(val), 'Стоимость']
                        : [Number(val).toLocaleString('ru-RU'), 'Остаток']
                    )}
                  />
                  <Area
                    type="monotone"
                    dataKey={materialId ? 'quantity' : 'value'}
                    stroke="#C9A227"
                    fill="url(#invGold)"
                    strokeWidth={2}
                  />
                </AreaChart>
              </ResponsiveContainer>
            </div>
          )}
        </Card>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={12}>
            <Card variant="admin">
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
                <AlertOutlined className="text-gold" />
                <Text className="text-gold-bold">Критические позиции</Text>
              </div>
              {critical.length === 0 ? (
                <Empty description={<Text className="text-titanium">Критических позиций нет</Text>} />
              ) : (
                <Table
                  size="small"
                  pagination={false}
                  rowKey="material_id"
                  dataSource={critical.slice(0, 8)}
                  columns={[
                    {
                      title: <Text className="text-gold">Материал</Text>,
                      render: (_, r) => (
                        <div>
                          <Text className="text-white">{r.material_name}</Text>
                          <div><Badge variant="warning" size="sm">дефицит {r.deficit} {r.unit}</Badge></div>
                        </div>
                      ),
                    },
                    {
                      title: <Text className="text-gold">Остаток</Text>,
                      render: (_, r) => (
                        <Text className="text-white">{r.quantity} / {r.min_quantity}</Text>
                      ),
                    },
                    {
                      title: <Text className="text-gold">Докупка</Text>,
                      render: (_, r) => (
                        <Text className="text-gold-bold">{formatCurrency(r.restock_cost)}</Text>
                      ),
                    },
                  ]}
                />
              )}
            </Card>
          </Col>

          <Col xs={24} lg={12}>
            <Card variant="admin">
              <div style={{ marginBottom: 12 }}>
                <Text className="text-gold-bold">ABC-анализ</Text>
                <div><Text className="text-titanium text-13">По стоимости расхода (A≈80%, B≈15%, C≈5%)</Text></div>
              </div>
              {abc.length === 0 ? (
                <Empty description={<Text className="text-titanium">Нет данных</Text>} />
              ) : (
                <Table
                  size="small"
                  pagination={false}
                  rowKey="material_id"
                  dataSource={abc.slice(0, 10)}
                  columns={[
                    {
                      title: <Text className="text-gold">Класс</Text>,
                      dataIndex: 'abc_class',
                      width: 64,
                      render: (v: string) => abcBadge(v),
                    },
                    {
                      title: <Text className="text-gold">Материал</Text>,
                      dataIndex: 'material_name',
                      render: (v: string) => <Text className="text-white">{v}</Text>,
                    },
                    {
                      title: <Text className="text-gold">Доля</Text>,
                      dataIndex: 'share_percent',
                      render: (v: number) => <Text className="text-titanium">{v}%</Text>,
                    },
                    {
                      title: <Text className="text-gold">Сумма</Text>,
                      dataIndex: 'consumption_value',
                      render: (v: number, r) => (
                        <Text className="text-gold-bold">
                          {formatCurrency(v > 0 ? v : r.stock_value)}
                        </Text>
                      ),
                    },
                  ]}
                />
              )}
            </Card>
          </Col>
        </Row>

        <Card variant="admin">
          <div style={{ marginBottom: 12 }}>
            <Text className="text-gold-bold">История движений</Text>
          </div>
          {movements.length === 0 ? (
            <Empty description={<Text className="text-titanium">Движений пока нет — сделайте приход/расход на складе</Text>} />
          ) : (
            <Table
              dataSource={movements}
              rowKey="id"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              columns={[
                {
                  title: <Text className="text-gold">Дата</Text>,
                  dataIndex: 'created_at',
                  render: (v: string) => <Text className="text-titanium">{formatDate(v)}</Text>,
                },
                {
                  title: <Text className="text-gold">Материал</Text>,
                  dataIndex: 'material_name',
                  render: (v: string) => <Text className="text-white">{v}</Text>,
                },
                {
                  title: <Text className="text-gold">Тип</Text>,
                  render: (_, r) => moveBadge(r.movement_type, r.movement_type_label),
                },
                {
                  title: <Text className="text-gold">Δ</Text>,
                  dataIndex: 'delta',
                  render: (v: number, r) => (
                    <Text className={v >= 0 ? 'text-gold-bold' : 'text-white'}>
                      {v >= 0 ? '+' : ''}{Number(v).toLocaleString('ru-RU')} {r.material_unit}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Остаток</Text>,
                  render: (_, r) => (
                    <Text className="text-titanium">
                      {r.quantity_before} → {r.quantity_after}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Комментарий</Text>,
                  dataIndex: 'reason',
                  render: (v?: string) => <Text className="text-titanium">{v || '—'}</Text>,
                },
              ]}
              components={{
                header: {
                  cell: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => (
                    <th {...props} className="table-header-cell" />
                  ),
                },
                body: {
                  row: (props: React.HTMLAttributes<HTMLTableRowElement>) => (
                    <tr {...props} className="table-body-row" />
                  ),
                  cell: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => (
                    <td {...props} className="table-body-cell" />
                  ),
                },
              }}
            />
          )}
        </Card>
      </Spin>
    </>
  );
}
