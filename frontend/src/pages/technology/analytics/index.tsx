/**
 * Аналитика технологии — /technology/analytics
 * Рекомендации, аудит норма vs факт (ручной + период), аномалии, AuditLog.
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
  Tooltip,
  InputNumber,
  Alert,
} from 'antd';
import { Button } from '../../../components/ui';
import {
  ReloadOutlined, ShoppingCartOutlined, AuditOutlined, WarningOutlined,
  ThunderboltOutlined, CheckOutlined, CalculatorOutlined,
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
  anomaly_count: number;
  open_audit_logs: number;
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

interface AnomalyRow {
  code: string;
  severity: string;
  material_id: number;
  material_name: string;
  unit: string;
  title: string;
  message: string;
  metric_value: number;
  cost_impact: number;
  fingerprint: string;
}

interface AuditLogRow {
  id: number;
  kind: string;
  severity: string;
  material_id?: number | null;
  material_name?: string | null;
  title: string;
  message?: string | null;
  status: string;
  created_at?: string;
}

interface TechCardItem {
  material_id: number;
  material_name: string;
  material_unit: string;
  quantity: number;
  purchase_price?: number;
}

interface TechCardOption {
  id: number;
  service_id: number;
  service_name: string;
  name?: string | null;
  items: TechCardItem[];
}

async function apiFetch<T>(path: string, init?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    ...init,
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
      ...(init?.headers || {}),
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
  return new Date(iso).toLocaleString('ru-RU', {
    day: '2-digit', month: '2-digit', year: 'numeric',
    hour: '2-digit', minute: '2-digit',
  });
}

function priorityBadge(p: string) {
  if (p === 'critical') return <Badge variant="danger" size="sm">Срочно заказать</Badge>;
  if (p === 'warn') return <Badge variant="warning" size="sm">Заказать</Badge>;
  return <Badge variant="info" size="sm">Заказать</Badge>;
}

function auditBadge(status: string, label: string) {
  if (status === 'over') return <Badge variant="danger" size="sm">{label}</Badge>;
  if (status === 'under') return <Badge variant="warning" size="sm">{label}</Badge>;
  if (status === 'ok') return <Badge variant="success" size="sm">{label}</Badge>;
  return <Badge variant="neutral" size="sm">{label}</Badge>;
}

function severityBadge(s: string) {
  if (s === 'critical') return <Badge variant="danger" size="sm">critical</Badge>;
  if (s === 'warn') return <Badge variant="warning" size="sm">warn</Badge>;
  return <Badge variant="info" size="sm">info</Badge>;
}

function kindBadge(k: string) {
  if (k === 'anomaly') return <Badge variant="danger" size="sm">Аномалия</Badge>;
  if (k === 'audit') return <Badge variant="warning" size="sm">Аудит</Badge>;
  return <Badge variant="info" size="sm">Закупка</Badge>;
}

export default function TechAnalyticsPage() {
  const [loading, setLoading] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [days, setDays] = useState(30);
  const [coverDays, setCoverDays] = useState(30);
  const [summary, setSummary] = useState<Summary | null>(null);
  const [purchases, setPurchases] = useState<PurchaseRow[]>([]);
  const [audit, setAudit] = useState<AuditRow[]>([]);
  const [anomalies, setAnomalies] = useState<AnomalyRow[]>([]);
  const [logs, setLogs] = useState<AuditLogRow[]>([]);

  const [techCards, setTechCards] = useState<TechCardOption[]>([]);
  const [manualCardId, setManualCardId] = useState<number | undefined>();
  const [manualServices, setManualServices] = useState<number>(1);
  const [manualFacts, setManualFacts] = useState<Record<number, number>>({});

  const refresh = useCallback(async () => {
    setLoading(true);
    try {
      const [sum, buy, aud, anom, journal, cards] = await Promise.all([
        apiFetch<Summary>(`/api/tech-analytics/summary?days=${days}&cover_days=${coverDays}`),
        apiFetch<PurchaseRow[]>(
          `/api/tech-analytics/purchase-recommendations?days=${days}&cover_days=${coverDays}`,
        ),
        apiFetch<AuditRow[]>(`/api/tech-analytics/consumption-audit?days=${days}`),
        apiFetch<AnomalyRow[]>(`/api/tech-analytics/anomalies?days=${days}`),
        apiFetch<{ items: AuditLogRow[] }>('/api/tech-analytics/audit-logs?status=open&limit=50'),
        apiFetch<{ items: TechCardOption[] }>('/api/tech-cards?skip=0&limit=200&is_active=true'),
      ]);
      setSummary(sum);
      setPurchases(buy || []);
      setAudit(aud || []);
      setAnomalies(anom || []);
      setLogs(journal.items || []);
      setTechCards(cards.items || []);
    } catch {
      message.error('Ошибка загрузки аналитики');
    }
    setLoading(false);
  }, [days, coverDays]);

  useEffect(() => {
    refresh();
  }, [refresh]);

  const selectedCard = useMemo(
    () => techCards.find((c) => c.id === manualCardId),
    [techCards, manualCardId],
  );

  const manualRows = useMemo(() => {
    if (!selectedCard) return [];
    const n = Math.max(0, Number(manualServices) || 0);
    return (selectedCard.items || []).map((item) => {
      const expected = Number(item.quantity || 0) * n;
      const fact = Number(manualFacts[item.material_id] ?? 0);
      const variance = fact - expected;
      const pct = expected > 0 ? ((fact / expected) - 1) * 100 : (fact > 0 ? null : 0);
      const warn = pct != null && Math.abs(pct) > 10;
      return {
        material_id: item.material_id,
        material_name: item.material_name,
        unit: item.material_unit,
        expected,
        fact,
        variance,
        pct: pct == null ? null : Math.round(pct * 10) / 10,
        warn,
      };
    });
  }, [selectedCard, manualServices, manualFacts]);

  const hasManualWarn = manualRows.some((r) => r.warn);

  const runSync = async () => {
    setSyncing(true);
    try {
      const res = await apiFetch<{ created: number; updated: number; resolved: number; anomalies: number }>(
        `/api/tech-analytics/sync?days=${days}&cover_days=${coverDays}`,
        { method: 'POST' },
      );
      message.success(
        `Синхронизация: +${res.created} / ≈${res.updated} / закрыто ${res.resolved} (аномалий ${res.anomalies})`,
      );
      await refresh();
    } catch {
      message.error('Не удалось синхронизировать AuditLog');
    }
    setSyncing(false);
  };

  const resolveLog = async (id: number) => {
    try {
      await apiFetch(`/api/tech-analytics/audit-logs/${id}/resolve`, { method: 'POST' });
      message.success('Запись закрыта');
      await refresh();
    } catch {
      message.error('Не удалось закрыть запись');
    }
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <h3>Технология / Аналитика</h3>
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
          <Button
            icon={<ThunderboltOutlined />}
            look="gold"
            loading={syncing}
            onClick={runSync}
          >
            Синхронизировать
          </Button>
          <Button icon={<ReloadOutlined />} look="ghost" onClick={refresh}>
            Обновить
          </Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6} md={4}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><ShoppingCartOutlined /></div>
              <div className="admin-kpi-label">К закупке</div>
              <div className="admin-kpi-value">{summary?.purchase_items ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6} md={5}>
            <Card variant="stats">
              <div className="admin-kpi-label">Сумма закупки</div>
              <div className="admin-kpi-value text-gold-bold">
                {formatCurrency(summary?.purchase_estimate_cost || 0)}
              </div>
            </Card>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><WarningOutlined /></div>
              <div className="admin-kpi-label">Перерасход</div>
              <div className="admin-kpi-value">{summary?.audit_overspend ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6} md={4}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><ThunderboltOutlined /></div>
              <div className="admin-kpi-label">Аномалии</div>
              <div className="admin-kpi-value">{summary?.anomaly_count ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6} md={3}>
            <Card variant="kpi">
              <div className="admin-kpi-icon"><AuditOutlined /></div>
              <div className="admin-kpi-label">Журнал</div>
              <div className="admin-kpi-value">{summary?.open_audit_logs ?? 0}</div>
            </Card>
          </Col>
          <Col xs={12} sm={6} md={4}>
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
            <ThunderboltOutlined className="text-gold" />
            <Text className="text-gold-bold">Аномалии</Text>
          </div>
          {anomalies.length === 0 ? (
            <Empty description={<Text className="text-titanium">Аномалий не найдено</Text>} />
          ) : (
            <Table
              dataSource={anomalies}
              rowKey="fingerprint"
              pagination={{ pageSize: 6, showSizeChanger: false }}
              columns={[
                {
                  title: <Text className="text-gold">Уровень</Text>,
                  dataIndex: 'severity',
                  width: 100,
                  render: (v: string) => severityBadge(v),
                },
                {
                  title: <Text className="text-gold">Событие</Text>,
                  render: (_, r) => (
                    <div>
                      <Text className="text-white">{r.title}</Text>
                      <div><Text className="text-titanium text-13">{r.message}</Text></div>
                    </div>
                  ),
                },
                {
                  title: <Text className="text-gold">Код</Text>,
                  dataIndex: 'code',
                  render: (v: string) => <Badge variant="neutral" size="sm">{v}</Badge>,
                },
                {
                  title: <Text className="text-gold">Влияние</Text>,
                  dataIndex: 'cost_impact',
                  render: (v: number) => (
                    <Text className="text-gold-bold">{formatCurrency(v)}</Text>
                  ),
                },
              ]}
            />
          )}
        </Card>

        <Card variant="admin" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 12 }}>
            <ShoppingCartOutlined className="text-gold" />
            <Text className="text-gold-bold">Рекомендации по закупкам</Text>
          </div>
          {purchases.length === 0 ? (
            <Empty description={<Text className="text-titanium">Запас в норме</Text>} />
          ) : (
            <Table
              dataSource={purchases}
              rowKey="material_id"
              pagination={{ pageSize: 8, showSizeChanger: false }}
              columns={[
                {
                  title: <Text className="text-gold">Приоритет</Text>,
                  dataIndex: 'priority',
                  width: 150,
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
            />
          )}
        </Card>

        <Card variant="admin" style={{ marginBottom: 16 }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
            <CalculatorOutlined className="text-gold" />
            <Text className="text-gold-bold">Аудит расхода: норма vs факт</Text>
          </div>
          <div style={{ marginBottom: 12 }}>
            <Text className="text-titanium text-13">
              Выберите техкарту, укажите число услуг и фактический расход — система посчитает отклонение.
            </Text>
          </div>
          <Space wrap style={{ marginBottom: 14 }}>
            <Select
              allowClear
              placeholder="Техкарта / услуга"
              className="input-luxury"
              style={{ minWidth: 280 }}
              value={manualCardId}
              onChange={(v) => {
                setManualCardId(v);
                setManualFacts({});
              }}
              options={techCards.map((c) => ({
                value: c.id,
                label: c.name || c.service_name,
              }))}
              showSearch
              optionFilterProp="label"
            />
            <InputNumber
              className="input-luxury"
              min={0}
              step={1}
              value={manualServices}
              onChange={(v) => setManualServices(Number(v || 0))}
              addonBefore="Услуг"
              style={{ width: 160 }}
            />
          </Space>

          {!selectedCard ? (
            <Empty description={<Text className="text-titanium">Выберите техкарту для расчёта</Text>} />
          ) : (
            <>
              {hasManualWarn && (
                <Alert
                  type="warning"
                  showIcon
                  style={{ marginBottom: 12 }}
                  message="Отклонение больше 10%"
                  description="Фактический расход заметно отличается от нормы по техкарте."
                />
              )}
              <Table
                dataSource={manualRows}
                rowKey="material_id"
                pagination={false}
                size="small"
                columns={[
                  {
                    title: <Text className="text-gold">Материал</Text>,
                    dataIndex: 'material_name',
                    render: (v: string) => <Text className="text-white">{v}</Text>,
                  },
                  {
                    title: <Text className="text-gold">Норма</Text>,
                    render: (_, r) => (
                      <Text className="text-titanium">
                        {Number(r.expected).toLocaleString('ru-RU')} {r.unit}
                      </Text>
                    ),
                  },
                  {
                    title: <Text className="text-gold">Факт</Text>,
                    render: (_, r) => (
                      <InputNumber
                        className="input-luxury"
                        min={0}
                        step={0.1}
                        value={manualFacts[r.material_id] ?? 0}
                        onChange={(v) => setManualFacts((prev) => ({
                          ...prev,
                          [r.material_id]: Number(v || 0),
                        }))}
                        addonAfter={r.unit}
                        style={{ width: 160 }}
                      />
                    ),
                  },
                  {
                    title: <Text className="text-gold">Δ %</Text>,
                    render: (_, r) => (
                      <Space>
                        <Text className={r.warn ? 'text-gold-bold' : 'text-titanium'}>
                          {r.pct == null ? '—' : `${r.pct > 0 ? '+' : ''}${r.pct}%`}
                        </Text>
                        {r.warn ? <Badge variant="danger" size="sm">&gt;10%</Badge> : null}
                      </Space>
                    ),
                  },
                ]}
              />
            </>
          )}

          <div style={{ marginTop: 20, marginBottom: 8 }}>
            <Text className="text-gold-bold">Автоаудит за период</Text>
            <div>
              <Text className="text-titanium text-13">
                Норма по завершённым услугам × техкарта; факт — списания со склада.
              </Text>
            </div>
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
                      {r.variance_percent != null && Math.abs(r.variance_percent) > 10
                        ? ' ⚠'
                        : ''}
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
            />
          )}
        </Card>

        <Card variant="admin">
          <div style={{ marginBottom: 12 }}>
            <Text className="text-gold-bold">Журнал AuditLog</Text>
            <div>
              <Text className="text-titanium text-13">
                Открытые записи после синхронизации (рекомендации, аудит, аномалии).
              </Text>
            </div>
          </div>
          {logs.length === 0 ? (
            <Empty description={<Text className="text-titanium">Журнал пуст — нажмите «Синхронизировать»</Text>} />
          ) : (
            <Table
              dataSource={logs}
              rowKey="id"
              pagination={{ pageSize: 8, showSizeChanger: false }}
              columns={[
                {
                  title: <Text className="text-gold">Тип</Text>,
                  dataIndex: 'kind',
                  width: 110,
                  render: (v: string) => kindBadge(v),
                },
                {
                  title: <Text className="text-gold">Уровень</Text>,
                  dataIndex: 'severity',
                  width: 100,
                  render: (v: string) => severityBadge(v),
                },
                {
                  title: <Text className="text-gold">Запись</Text>,
                  render: (_, r) => (
                    <div>
                      <Text className="text-white">{r.title}</Text>
                      <div><Text className="text-titanium text-13">{r.message || ''}</Text></div>
                    </div>
                  ),
                },
                {
                  title: <Text className="text-gold">Дата</Text>,
                  dataIndex: 'created_at',
                  width: 140,
                  render: (v: string) => <Text className="text-titanium">{formatDate(v)}</Text>,
                },
                {
                  title: '',
                  width: 90,
                  render: (_, r) => (
                    <Button
                      size="small"
                      icon={<CheckOutlined />}
                      look="ghost"
                      onClick={() => resolveLog(r.id)}
                    >
                      OK
                    </Button>
                  ),
                },
              ]}
            />
          )}
        </Card>
      </Spin>
    </>
  );
}
