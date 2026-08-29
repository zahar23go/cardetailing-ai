/**
 * Скидки — /discounts
 * Локальный state (правила, лояльность, аналитика, модалка) — без OwnerDashboard.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography,
  Card,
  Row,
  Col,
  Statistic,
  Table,
  Tag,
  Space,
  message,
  Select,
  InputNumber,
  Popconfirm,
  Spin,
  Tooltip,
  DatePicker,
  TimePicker,
  Switch,
} from 'antd';
import { Button, Modal, Input } from '../../components/ui';
import {
  PlusOutlined, EditOutlined, DeleteOutlined, ReloadOutlined,
  PhoneOutlined, StarOutlined, AreaChartOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import DiscountIntelligence from '../../components/DiscountIntelligence';
import ServiceDiscountRecs from '../../components/ServiceDiscountRecs';

const { Text } = Typography;
const { Option } = Select;

const API_BASE = '';

interface DiscountRule {
  id: number;
  name: string;
  type: string;
  conditions: Record<string, any>;
  discount_percent: number;
  slot_start: string | null;
  slot_end: string | null;
  service_id?: number;
  service_name?: string;
  client_id?: number;
  client_name?: string;
  valid_until?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface DiscountAnalyticsTopRule {
  rule_id: number;
  rule_name: string;
  rule_type: string;
  times_used: number;
  total_discount: number;
  client_count: number;
}

interface DiscountAnalytics {
  total_rules: number;
  active_rules: number;
  total_times_used: number;
  total_discount_amount: number;
  unique_clients_affected: number;
  top_rules: DiscountAnalyticsTopRule[];
}

interface LoyaltyClient {
  client_id: number;
  full_name: string;
  phone: string;
  balance: number;
  total_earned: number;
  total_spent: number;
}

interface ServiceOption {
  id: number;
  name: string;
  price: number;
}

interface UserOption {
  id: number;
  phone: string;
  full_name: string;
  role: string;
}

const DISCOUNT_TYPE_LABELS: Record<string, string> = {
  happy_hours: 'Happy Hours',
  service: 'На услугу',
  client: 'Персональная',
  segment: 'По сегменту',
  frequency: 'За частоту',
  win_back: 'Возврат',
  cashback: 'Кэшбек',
};

const DISCOUNT_TYPE_COLORS: Record<string, string> = {
  happy_hours: 'blue',
  service: 'gold',
  client: 'purple',
  segment: 'cyan',
  frequency: 'green',
  win_back: 'orange',
  cashback: 'purple',
};

const emptyForm = {
  name: '',
  type: 'happy_hours',
  discount_percent: 0,
  slot_start: '',
  slot_end: '',
  service_id: undefined as number | undefined,
  client_id: undefined as number | undefined,
  valid_until: '',
  is_active: true,
  minVisits: 3,
  maxRecencyDays: 60,
  pointsPercent: 5,
  segment: undefined as string | undefined,
};

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

export default function DiscountsPage() {
  const [discountRules, setDiscountRules] = useState<DiscountRule[]>([]);
  const [discountsLoading, setDiscountsLoading] = useState(false);
  const [discountAnalytics, setDiscountAnalytics] = useState<DiscountAnalytics | null>(null);
  const [discountModal, setDiscountModal] = useState(false);
  const [editingDiscount, setEditingDiscount] = useState<DiscountRule | null>(null);
  const [discountForm, setDiscountForm] = useState(emptyForm);
  const [discountSaving, setDiscountSaving] = useState(false);

  const [loyaltyClients, setLoyaltyClients] = useState<LoyaltyClient[]>([]);
  const [loyaltyLoading, setLoyaltyLoading] = useState(false);

  const [allServices, setAllServices] = useState<ServiceOption[]>([]);
  const [clientUsers, setClientUsers] = useState<UserOption[]>([]);

  const fetchDiscounts = async () => {
    setDiscountsLoading(true);
    try {
      const data = await apiFetch<{ items: DiscountRule[]; total: number }>('/api/discounts?skip=0&limit=100');
      setDiscountRules(data.items);
    } catch { /* ignore */ }
    try {
      const analytics = await apiFetch<DiscountAnalytics>('/api/analytics/discounts');
      setDiscountAnalytics(analytics);
    } catch { /* ignore */ }
    setDiscountsLoading(false);
  };

  const fetchLoyalty = async () => {
    setLoyaltyLoading(true);
    try {
      const data = await apiFetch<{ items: LoyaltyClient[]; total: number }>('/api/loyalty/points?skip=0&limit=100');
      setLoyaltyClients(data.items);
    } catch { /* ignore */ }
    setLoyaltyLoading(false);
  };

  const fetchDiscountAnalytics = async () => {
    try {
      const data = await apiFetch<DiscountAnalytics>('/api/analytics/discounts');
      setDiscountAnalytics(data);
    } catch { /* ignore */ }
  };

  const fetchSelectOptions = async () => {
    try {
      const services = await apiFetch<{ items: ServiceOption[] }>('/api/services?skip=0&limit=500');
      setAllServices(services.items);
    } catch { /* ignore */ }
    try {
      const users = await apiFetch<{ items: UserOption[] }>('/api/users?limit=500');
      setClientUsers(users.items.filter((u) => u.role === 'client'));
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchDiscounts();
    fetchLoyalty();
    fetchSelectOptions();
  }, []);

  const openDiscountModal = (rule?: DiscountRule) => {
    if (rule) {
      setEditingDiscount(rule);
      const cond = rule.conditions || {};
      setDiscountForm({
        name: rule.name,
        type: rule.type,
        discount_percent: rule.discount_percent,
        slot_start: rule.slot_start || '',
        slot_end: rule.slot_end || '',
        service_id: rule.service_id || undefined,
        client_id: rule.client_id || undefined,
        valid_until: rule.valid_until || '',
        is_active: rule.is_active,
        minVisits: cond.min_visits || 3,
        maxRecencyDays: cond.max_recency_days || 60,
        pointsPercent: cond.points_percent || 5,
        segment: cond.segment || undefined,
      });
    } else {
      setEditingDiscount(null);
      setDiscountForm({ ...emptyForm });
    }
    setDiscountModal(true);
  };

  const handleSaveDiscount = async () => {
    if (!discountForm.name.trim()) { message.warning('Укажите название правила'); return; }
    if (!discountForm.discount_percent) { message.warning('Укажите процент скидки'); return; }
    setDiscountSaving(true);
    try {
      const conditions: Record<string, any> = {};
      if (discountForm.type === 'happy_hours') {
        conditions.hour_start = discountForm.slot_start;
        conditions.hour_end = discountForm.slot_end;
      } else if (discountForm.type === 'frequency') {
        conditions.min_visits = discountForm.minVisits;
      } else if (discountForm.type === 'win_back') {
        conditions.max_recency_days = discountForm.maxRecencyDays;
      } else if (discountForm.type === 'cashback') {
        conditions.points_percent = discountForm.pointsPercent;
      } else if (discountForm.type === 'segment') {
        conditions.segment = discountForm.segment;
      }

      const body = {
        name: discountForm.name,
        type: discountForm.type,
        conditions,
        discount_percent: discountForm.discount_percent,
        slot_start: discountForm.slot_start || null,
        slot_end: discountForm.slot_end || null,
        service_id: discountForm.service_id || null,
        client_id: discountForm.client_id || null,
        valid_until: discountForm.valid_until || null,
        is_active: discountForm.is_active,
      };

      if (editingDiscount) {
        await apiFetch(`/api/discounts/${editingDiscount.id}`, {
          method: 'PUT',
          body: JSON.stringify(body),
        });
        message.success('Правило скидки обновлено');
      } else {
        await apiFetch('/api/discounts', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        message.success('Правило скидки создано');
      }
      setDiscountModal(false);
      fetchDiscounts();
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setDiscountSaving(false);
  };

  const handleDeleteDiscount = async (id: number, name: string) => {
    try {
      await apiFetch(`/api/discounts/${id}`, { method: 'DELETE' });
      message.success(`Правило «${name}» удалено`);
      fetchDiscounts();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления');
    }
  };

  const createDiscountFromSuggestion = async (s: {
    name: string;
    hour_start: string;
    hour_end: string;
    weekdays: number[];
    discount_percent: number;
  }) => {
    await apiFetch('/api/discounts', {
      method: 'POST',
      body: JSON.stringify({
        name: s.name,
        type: 'happy_hours',
        conditions: {
          hour_start: s.hour_start,
          hour_end: s.hour_end,
          weekdays: s.weekdays,
        },
        discount_percent: s.discount_percent,
        slot_start: s.hour_start,
        slot_end: s.hour_end,
        is_active: true,
      }),
    });
    fetchDiscounts();
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Лояльность</div>
          <h3>Скидки и бонусы</h3>
        </div>
      </div>

      <DiscountIntelligence onCreateSuggestion={createDiscountFromSuggestion} />

      <div style={{ marginTop: 16, marginBottom: 16 }}>
        <ServiceDiscountRecs />
      </div>

      <Spin spinning={discountsLoading || loyaltyLoading}>
        <div className="toolbar-right mb-12" style={{ marginTop: 16 }}>
          <Button
            type="primary"
            icon={<PlusOutlined />}
            look="gold"
            style={{ width: 'auto' }}
            onClick={() => openDiscountModal()}
          >
            Создать правило вручную
          </Button>
        </div>

        <Card className="card-luxury" style={{ marginBottom: '16px' }}>
          <Text className="title-gold text-16 d-block mb-8">Правила скидок</Text>
          {discountRules.length === 0 && !discountsLoading ? (
            <Text className="text-titanium text-13">Нет правил скидок. Создайте первое правило.</Text>
          ) : (
            <Table
              dataSource={discountRules}
              rowKey="id"
              pagination={false}
              size="small"
              columns={[
                {
                  title: <Text className="text-titanium text-12">Название</Text>,
                  dataIndex: 'name',
                  key: 'name',
                  render: (val, record) => (
                    <Space>
                      <Text className="text-white text-13">{val}</Text>
                      <Tag className="tag-status" color={record.is_active ? 'green' : 'default'}>
                        {record.is_active ? 'Активна' : 'Неактивна'}
                      </Tag>
                    </Space>
                  ),
                },
                {
                  title: <Text className="text-titanium text-12">Тип</Text>,
                  dataIndex: 'type',
                  key: 'type',
                  render: (val) => (
                    <Tag className="tag-status" color={DISCOUNT_TYPE_COLORS[val] || 'default'}>
                      {DISCOUNT_TYPE_LABELS[val] || val}
                    </Tag>
                  ),
                },
                {
                  title: <Text className="text-titanium text-12">%</Text>,
                  dataIndex: 'discount_percent',
                  key: 'percent',
                  render: (val) => <Text className="text-gold-bold text-13">{val}%</Text>,
                },
                {
                  title: <Text className="text-titanium text-12">Привязка</Text>,
                  key: 'binding',
                  render: (_, record) => (
                    <Text className="text-titanium text-12">
                      {record.service_name
                        ? `📋 ${record.service_name}`
                        : record.client_name
                          ? `👤 ${record.client_name}`
                          : '—'}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-titanium text-12">Слот</Text>,
                  key: 'slot',
                  render: (_, record) => (
                    <Text className="text-titanium text-12">
                      {record.slot_start || '∞'} — {record.slot_end || '∞'}
                    </Text>
                  ),
                },
                {
                  title: <Text className="text-titanium text-12">До</Text>,
                  dataIndex: 'valid_until',
                  key: 'valid_until',
                  render: (val) => (
                    <Text className="text-titanium text-12">
                      {val ? dayjs(val).format('DD.MM.YYYY') : '∞'}
                    </Text>
                  ),
                },
                {
                  title: '',
                  key: 'actions',
                  width: 100,
                  render: (_, record) => (
                    <Space size="small">
                      <Tooltip title="Редактировать">
                        <Button
                          size="small"
                          icon={<EditOutlined />}
                          className="btn-action-gold"
                          onClick={() => openDiscountModal(record)}
                        />
                      </Tooltip>
                      <Popconfirm
                        title={`Удалить «${record.name}»?`}
                        onConfirm={() => handleDeleteDiscount(record.id, record.name)}
                        okText="Да"
                        cancelText="Нет"
                      >
                        <Tooltip title="Удалить">
                          <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                        </Tooltip>
                      </Popconfirm>
                    </Space>
                  ),
                },
              ]}
              components={{
                header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                body: {
                  row: (p: any) => <tr {...p} className="table-body-row" />,
                  cell: (p: any) => <td {...p} className="table-body-cell" />,
                },
              }}
            />
          )}
        </Card>

        <Card className="card-luxury">
          <div className="flex-space-between mb-12">
            <Text className="title-gold text-16"><StarOutlined /> Баланс баллов клиентов</Text>
            <Button size="small" icon={<ReloadOutlined />} onClick={fetchLoyalty} type="text" className="btn-logout" />
          </div>
          {loyaltyClients.length === 0 && !loyaltyLoading ? (
            <Text className="text-titanium text-13">
              Нет данных о баллах. Баллы начисляются за завершённые записи.
            </Text>
          ) : (
            <Table
              dataSource={loyaltyClients}
              rowKey="client_id"
              pagination={{ pageSize: 20, size: 'small' }}
              size="small"
              columns={[
                {
                  title: <Text className="text-titanium text-12">Клиент</Text>,
                  dataIndex: 'full_name',
                  key: 'full_name',
                  render: (val) => <Text className="text-white text-13">{val}</Text>,
                },
                {
                  title: <Text className="text-titanium text-12">Телефон</Text>,
                  dataIndex: 'phone',
                  key: 'phone',
                  render: (val) => (
                    <Text className="text-titanium text-13"><PhoneOutlined /> {val}</Text>
                  ),
                },
                {
                  title: <Text className="text-titanium text-12">Баллы</Text>,
                  dataIndex: 'balance',
                  key: 'balance',
                  render: (val) => <Text className="text-gold-bold text-13">{val}</Text>,
                },
                {
                  title: <Text className="text-titanium text-12">Всего заработано</Text>,
                  dataIndex: 'total_earned',
                  key: 'earned',
                  render: (val) => <Text className="text-white text-13">{val}</Text>,
                },
                {
                  title: <Text className="text-titanium text-12">Потрачено</Text>,
                  dataIndex: 'total_spent',
                  key: 'spent',
                  render: (val) => <Text className="text-titanium text-13">{val}</Text>,
                },
              ]}
              components={{
                header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                body: {
                  row: (p: any) => <tr {...p} className="table-body-row" />,
                  cell: (p: any) => <td {...p} className="table-body-cell" />,
                },
              }}
            />
          )}
        </Card>

        <Card className="card-luxury" style={{ marginTop: '16px' }}>
          <div className="flex-space-between mb-12">
            <Text className="title-gold text-16"><AreaChartOutlined /> Аналитика скидок</Text>
            <Button
              size="small"
              icon={<ReloadOutlined />}
              onClick={fetchDiscountAnalytics}
              type="text"
              className="btn-logout"
            />
          </div>
          {discountAnalytics ? (
            <>
              <Row gutter={[12, 12]} className="mb-12">
                <Col xs={12} sm={6}>
                  <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                    <Statistic
                      title={<Text className="text-titanium text-11">Всего правил</Text>}
                      value={discountAnalytics.total_rules}
                      valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                    <Statistic
                      title={<Text className="text-titanium text-11">Активных</Text>}
                      value={discountAnalytics.active_rules}
                      valueStyle={{ color: '#4ECB71', fontSize: '18px', fontWeight: 700 }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                    <Statistic
                      title={<Text className="text-titanium text-11">Применено раз</Text>}
                      value={discountAnalytics.total_times_used}
                      valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}
                    />
                  </Card>
                </Col>
                <Col xs={12} sm={6}>
                  <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                    <Statistic
                      title={<Text className="text-titanium text-11">Сумма скидок</Text>}
                      value={discountAnalytics.total_discount_amount}
                      precision={0}
                      suffix={<Text className="text-titanium text-11">₽</Text>}
                      valueStyle={{ color: '#FFFFFF', fontSize: '18px', fontWeight: 700 }}
                    />
                  </Card>
                </Col>
              </Row>
              {discountAnalytics.top_rules.length > 0 && (
                <Table
                  dataSource={discountAnalytics.top_rules}
                  rowKey="rule_id"
                  pagination={false}
                  size="small"
                  columns={[
                    {
                      title: <Text className="text-titanium text-12">Правило</Text>,
                      dataIndex: 'rule_name',
                      render: (v: any, r: any) => (
                        <Space>
                          <Text className="text-white text-13">{v}</Text>
                          <Tag className="tag-status" color={DISCOUNT_TYPE_COLORS[r.rule_type]}>
                            {DISCOUNT_TYPE_LABELS[r.rule_type] || r.rule_type}
                          </Tag>
                        </Space>
                      ),
                    },
                    {
                      title: <Text className="text-titanium text-12">Использований</Text>,
                      dataIndex: 'times_used',
                      render: (v) => <Text className="text-white-bold text-13">{v}</Text>,
                    },
                    {
                      title: <Text className="text-titanium text-12">Скидка</Text>,
                      dataIndex: 'total_discount',
                      render: (v) => (
                        <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text>
                      ),
                    },
                    {
                      title: <Text className="text-titanium text-12">Клиентов</Text>,
                      dataIndex: 'client_count',
                      render: (v) => <Text className="text-titanium text-13">{v}</Text>,
                    },
                  ]}
                  components={{
                    header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                    body: {
                      row: (p: any) => <tr {...p} className="table-body-row" />,
                      cell: (p: any) => <td {...p} className="table-body-cell" />,
                    },
                  }}
                />
              )}
            </>
          ) : (
            <Text className="text-titanium text-13">Нажмите «Обновить» для загрузки аналитики</Text>
          )}
        </Card>
      </Spin>

      <Modal
        title={
          <Text className="text-gold-bold">
            {editingDiscount ? '✏️ Редактировать правило скидки' : '➕ Новое правило скидки'}
          </Text>
        }
        open={discountModal}
        onCancel={() => { setDiscountModal(false); setEditingDiscount(null); }}
        footer={null}
        width={560}
        className="modal-command"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Название *</span>
            <Input
              size="large"
              className="input-luxury"
              placeholder="Happy Hours"
              value={discountForm.name}
              onChange={(e) => setDiscountForm((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <Row gutter={16}>
            <Col span={12}>
              <span className="label-field">Тип скидки *</span>
              <Select
                size="large"
                className="w-full"
                value={discountForm.type}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, type: v }))}
              >
                <Option value="happy_hours">Happy Hours</Option>
                <Option value="service">На услугу</Option>
                <Option value="client">Персональная</Option>
                <Option value="segment">По сегменту (VIP, Лояльные...)</Option>
                <Option value="frequency">За частоту визитов</Option>
                <Option value="win_back">Возврат клиентов</Option>
                <Option value="cashback">Кэшбек</Option>
              </Select>
            </Col>
            <Col span={12}>
              <span className="label-field">Процент скидки *</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                placeholder="10"
                value={discountForm.discount_percent || ''}
                onChange={(e) => setDiscountForm((prev) => ({
                  ...prev,
                  discount_percent: Number(e.target.value),
                }))}
              />
            </Col>
          </Row>

          {discountForm.type === 'happy_hours' && (
            <Row gutter={16}>
              <Col span={12}>
                <span className="label-field">Время начала слота</span>
                <TimePicker
                  size="large"
                  className="w-full input-luxury"
                  format="HH:mm"
                  value={discountForm.slot_start ? dayjs(discountForm.slot_start, 'HH:mm') : null}
                  onChange={(t) => setDiscountForm((prev) => ({
                    ...prev,
                    slot_start: t ? t.format('HH:mm') : '',
                  }))}
                />
              </Col>
              <Col span={12}>
                <span className="label-field">Время конца слота</span>
                <TimePicker
                  size="large"
                  className="w-full input-luxury"
                  format="HH:mm"
                  value={discountForm.slot_end ? dayjs(discountForm.slot_end, 'HH:mm') : null}
                  onChange={(t) => setDiscountForm((prev) => ({
                    ...prev,
                    slot_end: t ? t.format('HH:mm') : '',
                  }))}
                />
              </Col>
            </Row>
          )}

          {discountForm.type === 'service' && (
            <div>
              <span className="label-field">Услуга *</span>
              <Select
                size="large"
                className="w-full"
                placeholder="Выберите услугу"
                value={discountForm.service_id}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, service_id: v }))}
              >
                {allServices.map((s) => (
                  <Option key={s.id} value={s.id}>{s.name} — {s.price} ₽</Option>
                ))}
              </Select>
            </div>
          )}

          {discountForm.type === 'client' && (
            <div>
              <span className="label-field">Клиент *</span>
              <Select
                size="large"
                className="w-full"
                placeholder="Выберите клиента"
                showSearch
                value={discountForm.client_id}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, client_id: v }))}
                filterOption={(input, option) =>
                  ((option?.label as string) || '').toLowerCase().includes(input.toLowerCase())
                }
              >
                {clientUsers.map((u) => (
                  <Option key={u.id} value={u.id} label={`${u.full_name} (${u.phone})`}>
                    👤 {u.full_name} · {u.phone}
                  </Option>
                ))}
              </Select>
            </div>
          )}

          {discountForm.type === 'segment' && (
            <div>
              <span className="label-field">Сегмент клиентов *</span>
              <Select
                size="large"
                className="w-full"
                placeholder="Выберите сегмент"
                value={discountForm.segment}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, segment: v }))}
              >
                <Option value="vip">⭐ VIP</Option>
                <Option value="loyal">💎 Лояльные</Option>
                <Option value="regular">🔄 Постоянные</Option>
                <Option value="new">🆕 Новые</Option>
                <Option value="sleeping">😴 Спящие</Option>
                <Option value="lost">🚫 Ушедшие</Option>
              </Select>
            </div>
          )}

          <div>
            <span className="label-field">Срок действия (до)</span>
            <DatePicker
              size="large"
              className="w-full input-luxury"
              value={discountForm.valid_until ? dayjs(discountForm.valid_until) : null}
              onChange={(d) => setDiscountForm((prev) => ({
                ...prev,
                valid_until: d ? d.format('YYYY-MM-DD') : '',
              }))}
            />
          </div>

          <div className="flex-space-between" style={{ padding: '8px 0' }}>
            <Text className="text-titanium">Статус скидки</Text>
            <Space>
              <Switch
                checked={discountForm.is_active}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, is_active: v }))}
                checkedChildren="Активна"
                unCheckedChildren="Неактивна"
              />
            </Space>
          </div>

          {discountForm.type === 'frequency' && (
            <div>
              <span className="label-field">Минимальное количество визитов</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={100}
                value={discountForm.minVisits}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, minVisits: v || 1 }))}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {discountForm.type === 'win_back' && (
            <div>
              <span className="label-field">Максимум дней без записи</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={365}
                value={discountForm.maxRecencyDays}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, maxRecencyDays: v || 30 }))}
                style={{ width: '100%' }}
              />
              <Text className="text-titanium text-12 d-block" style={{ marginTop: 4 }}>
                Если клиент не был больше указанного количества дней — применяется скидка
              </Text>
            </div>
          )}

          {discountForm.type === 'cashback' && (
            <div>
              <span className="label-field">Процент кэшбэка</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={100}
                value={discountForm.pointsPercent}
                onChange={(v) => setDiscountForm((prev) => ({ ...prev, pointsPercent: v || 1 }))}
                style={{ width: '100%' }}
              />
              <Text className="text-titanium text-12 d-block" style={{ marginTop: 4 }}>
                Сколько процентов от суммы записи начислять баллами
              </Text>
            </div>
          )}

          <Button
            type="primary"
            size="large"
            look="gold"
            onClick={handleSaveDiscount}
            loading={discountSaving}
          >
            {editingDiscount ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>
    </>
  );
}
