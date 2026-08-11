/**
 * Аналитика технологии — /technology/analytics
 * Рекомендации по закупкам + аудит расхода (норма vs факт).
 */
import React, { useCallback, useEffect, useState } from 'react';
import {
  Typography, Row, Col, Table, Button, Space, Spin, Empty, Select, message, Tooltip,
} from 'antd';
import {
  ReloadOutlined, ShoppingCartOutlined, AuditOutlined, WarningOutlined,
} from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';

const { Text } = Typography;

const API_BASE = '';

interface Summary {
  period_days: number;
  cover_days: number;
  purchase_items: number;
  purchase_estimate_cost: number;
  purchase_critical: number;
  audit_items: number;
  audit_overspend: number;
  audit_underspend: number;
  audit_variance_cost: number;
}

interface PurchaseRow {
  material_id: number;
  material_name: string;
  sku?: string | null;
  category: string;
  unit: string;
  quantity: number;
  min_quantity: number;
  avg_daily_consumption: number;
  days_of_stock?: number | null;
  target_quantity: number;
  recommend_qty: number;
  purchase_price: number;
  estimate_cost: number;
  supplier?: string | null;
  priority: string;
  reason: string;
}

interface AuditService {
  service_id: number;
  service_name: string;
  completed_count: number;
  norm_per_service: number;
  norm_total: number;
}

interface AuditRow {
  material_id: number;
  material_name: string;
  unit: string;
  norm_qty: number;
  fact_qty: number;
  variance_qty: number;
  variance_percent?: number | null;
  norm_cost: number;
  fact_cost: number;
  variance_cost: number;
  status: string;
  status_label: string;
  services: AuditService[];
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

function priorityBadge(p: string) {
  if (p === 'critical') return <Badge variant="danger" size="sm">Критично</Badge>;
  if (p === 'warn') return <Badge variant="warning" size="sm">Скоро</Badge>;
  return <Badge variant="info" size="sm">План</Badge>;
}

function auditBadge(status: string, label: string) {
  if (status === 'over') return <Badge variant="danger" size="sm">{label}</Badge>;
  if (status === 'under') return <Badge variant="warning" size="sm">{label}</Badge>;
  if (status === 'ok') return <Badge variant="success" size="sm">{label}</Badge>;
  return <Badge variant="neutral" size="sm">{label}</Badge>;
}

export default function TechAnalyticsPage() {
  const [loading, setLoading] = useState(false);
  const [days, setDays] = useState(30);
  const [coverDays, setCoverDays] = useState(30);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [purchases, setPurchases] = useState<PurchaseRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [sum, buy, aud] = await Promise.all([
        apiFetch<Summary>(`/api/tech-analytics/summary?days=${days}&cover_days=${coverDays}`),
        apiFetch<PurchaseRow[]>(
          `/api/tech-analytics/purchase-recommendations?days=${days}&cover_days=${coverDays}`,
        ),
        apiFetch<AuditRow[]>(`/api/tech-analytics/consumption-audit?days=${days}`),
      ]);
      setSummary(sum);
      setPurchases(buy || []);
      setAudit(aud || []);
    } catch {
      message.error('Ошибка загрузки аналитики');
    }
    setLoading(false);
  }, [days, coverDays]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Технология</div>
          <h3>Аналитика</h3>
        </div>
        <Space wrap>
          <Select
            value={days}
            style={{ width: 150 }}
            className="input-luxury"
            onChange={setDays}
            options={[
              { value: 14, label: 'Период 14 дн.' },
              { value: 30, label: 'Период 30 дн.' },
              { value: 90, label: 'Период 90 дн.' },
            ]}
          />
          <Select
            value={coverDays}
            style={{ width: 180 }}
            className="input-luxury"
            onChange={setCoverDays}
            options={[
              { value: 14, label: 'Покрытие 14 дн.' },
              { value: 30, label: 'Покрытие 30 дн.' },
              { value: 60, label: 'Покрытие 60 дн.' },
            ]}
          />
          <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={refresh}>
            Обновить
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><ShoppingCartOutlined /></div>
              <div className="admin-kpi-label">К закупке</div>
              <div className="admin-kpi-value">{summary?.purchase_items ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="stats">
              <div className="admin-kpi-label">Сумма закупки</div>
              <div className="admin-kpi-value text-gold-bold">
                {formatCurrency(summary?.purchase_estimate_cost || 0)}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><WarningOutlined /></div>
              <div className="admin-kpi-label">Перерасход</div>
              <div className="admin-kpi-value">{summary?.audit_overspend ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card variant="stats">
              <div className="admin-kpi-label">Δ факт − норма</div>
              <div className="admin-kpi-value text-gold-bold">
                {formatCurrency(summary?.audit_variance_cost || 0)}
              </div>
            </Card>
          </Col>
        </Row>

        <Card variant="admin" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <ShoppingCartOutlined className="text-gold" />
            <Text className="text-gold-bold">Рекомендации по закупкам</Text>
          </div>
          {purchases.length === 0 ? (
            <Empty description={<Text className="text-titanium">Закупка не требуется</Text>} />
          ) : (
            <Table
              dataSource={purchases}
              rowKey="material_id"
              pagination={{ pageSize: 8, showSizeChanger: false }}
              columns={[
                {
                  title: <Text className="text-gold">Приоритет</Text>,
                  dataIndex: 'priority',
                  width: 110,
                  render: (v: string) => priorityBadge(v),
                },
                {
                  title: <Text className="text-gold">Материал</Text>,
                  render: (_, r) => (
                    <div>
                      <Text className="text-white">{r.material_name}</Text>
                      <div><Text className="text-titanium text-13">{r.reason}</Text></div>
                    </div>
                  ),
                },
                {
                  title: <Text className="text-gold">Остаток</Text>,
                  render: (_, r) => (
                    <Text className="text-white">
                      {r.quantity} / мин {r.min_quantity} {r.unit}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Расход/день</Text>,
                  dataIndex: 'avg_daily_consumption',
                  render: (v: number, r) => (
                    <Text className="text-titanium">{v} {r.unit}</Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Купить</Text>,
                  dataIndex: 'recommend_qty',
                  render: (v: number, r) => (
                    <Text className="text-gold-bold">{v} {r.unit}</Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Сумма</Text>,
                  dataIndex: 'estimate_cost',
                  render: (v: number) => (
                    <Text className="text-gold-bold">{formatCurrency(v)}</Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Поставщик</Text>,
                  dataIndex: 'supplier',
                  render: (v?: string) => (
                    <Text className="text-titanium">{v || '—'}</Text>
                  ),
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

        <Card variant="admin">
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <AuditOutlined className="text-gold" />
            <Text className="text-gold-bold">Аудит расхода: норма vs факт</Text>
          </div>
          <div style={{ marginBottom: 12 }}>
            <Text className="text-titanium text-13">
              Норма = расход по техкарте × число завершённых услуг. Факт = списания со склада.
            </Text>
          </div>
          {audit.length === 0 ? (
            <Empty description={<Text className="text-titanium">Нет данных для аудита за период</Text>} />
          ) : (
            <Table
              dataSource={audit}
              rowKey="material_id"
              pagination={{ pageSize: 10, showSizeChanger: false }}
              expandable={{
                expandedRowRender: (r) => (
                  r.services.length === 0 ? (
                    <Text className="text-titanium">Нет привязки к техкарте</Text>
                  ) : (
                    <Space direction="vertical" size={4}>
                      {r.services.map((s) => (
                        <Text key={`${r.material_id}-${s.service_id}`} className="text-titanium">
                          {s.service_name}: {s.completed_count} усл. × {s.norm_per_service} {r.unit}
                          {' = '}
                          <span className="text-white">{s.norm_total} {r.unit}</span>
                        </Text>
                      ))}
                    </Space>
                  )
                ),
                rowExpandable: (r) => r.services.length > 0 || r.status === 'no_norm',
              }}
              columns={[
                {
                  title: <Text className="text-gold">Статус</Text>,
                  width: 120,
                  render: (_, r) => auditBadge(r.status, r.status_label),
                },
                {
                  title: <Text className="text-gold">Материал</Text>,
                  dataIndex: 'material_name',
                  render: (v: string) => <Text className="text-white">{v}</Text>,
                },
                {
                  title: <Text className="text-gold">Норма</Text>,
                  dataIndex: 'norm_qty',
                  render: (v: number, r) => (
                    <Tooltip title={formatCurrency(r.norm_cost)}>
                      <Text className="text-titanium">{v} {r.unit}</Text>
                    </Tooltip>
                  ),
                },
                {
                  title: <Text className="text-gold">Факт</Text>,
                  dataIndex: 'fact_qty',
                  render: (v: number, r) => (
                    <Tooltip title={formatCurrency(r.fact_cost)}>
                      <Text className="text-white">{v} {r.unit}</Text>
                    </Tooltip>
                  ),
                },
                {
                  title: <Text className="text-gold">Δ</Text>,
                  dataIndex: 'variance_qty',
                  render: (v: number, r) => (
                    <Text className={v > 0 ? 'text-gold-bold' : 'text-titanium'}>
                      {v > 0 ? '+' : ''}{v} {r.unit}
                      {r.variance_percent != null ? ` (${r.variance_percent > 0 ? '+' : ''}${r.variance_percent}%)` : ''}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-gold">Δ ₽</Text>,
                  dataIndex: 'variance_cost',
                  render: (v: number) => (
                    <Text className={v > 0 ? 'text-gold-bold' : 'text-titanium'}>
                      {formatCurrency(v)}
                    </Text>
                  ),
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
