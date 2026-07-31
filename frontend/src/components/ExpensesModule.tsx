/* ============================================================
   ExpensesModule — учёт постоянных затрат
   ============================================================ */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Button, Card, Col, DatePicker, Empty, Input, Modal, Popconfirm, Row, Select,
  Space, Spin, Statistic, Table, Tag, Typography, message,
} from 'antd';
import {
  PlusOutlined, ReloadOutlined, DeleteOutlined, EditOutlined,
  WarningOutlined, BulbOutlined, RiseOutlined,
} from '@ant-design/icons';
import {
  Bar, BarChart, CartesianGrid, Cell, Legend, Pie, PieChart,
  ResponsiveContainer, Tooltip as RechartsTooltip, XAxis, YAxis,
} from 'recharts';
import dayjs, { Dayjs } from 'dayjs';

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;
const { RangePicker } = DatePicker;

interface ExpenseCat {
  key: string;
  label: string;
  subcategories: string[];
}

interface Expense {
  id: number;
  name: string;
  amount: number;
  category: string;
  subcategory?: string | null;
  payment_status: string;
  period_type: string;
  period_start?: string | null;
  period_end?: string | null;
  expense_date?: string | null;
  notes?: string | null;
}

interface Analytics {
  total: number;
  paid_total: number;
  unpaid_total: number;
  overdue_total: number;
  by_category: { category: string; label: string; amount: number; share_percent: number; count: number }[];
  by_month: { month: string; label: string; total: number; by_category: Record<string, number> }[];
  insights: { type: string; severity: string; title: string; message: string }[];
  break_even_revenue: number;
  forecast_profit: number;
  revenue_month: number;
}

const STATUS_LABELS: Record<string, string> = {
  paid: 'Оплачено',
  unpaid: 'Не оплачено',
  overdue: 'Просрочено',
  partial: 'Частично',
};
const STATUS_COLORS: Record<string, string> = {
  paid: 'green',
  unpaid: 'orange',
  overdue: 'red',
  partial: 'gold',
};
const PERIOD_LABELS: Record<string, string> = {
  monthly: 'Месяц',
  quarterly: 'Квартал',
  yearly: 'Год',
  one_time: 'Разовый',
};

const PIE_COLORS = ['#D4A84B', '#E0BC5A', '#A67C2D', '#F0D9A0', '#8B6914', '#C8A977', '#5B8DEF', '#4ECB71', '#E85D75', '#2EC4B6', '#A78BFA'];

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

const emptyForm = {
  name: '',
  amount: 0,
  category: 'rent',
  subcategory: '',
  payment_status: 'paid',
  period_type: 'monthly',
  expense_date: dayjs().format('YYYY-MM-DD'),
  period_start: '',
  period_end: '',
  notes: '',
};

export default function ExpensesModule() {
  const [loading, setLoading] = useState(false);
  const [items, setItems] = useState<Expense[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [catalog, setCatalog] = useState<ExpenseCat[]>([]);
  const [analytics, setAnalytics] = useState<Analytics | null>(null);

  const [filterCategory, setFilterCategory] = useState<string>('all');
  const [filterStatus, setFilterStatus] = useState<string>('all');
  const [filterRange, setFilterRange] = useState<[Dayjs, Dayjs] | null>(null);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Expense | null>(null);
  const [form, setForm] = useState({ ...emptyForm });
  const [saving, setSaving] = useState(false);

  const catLabel = useMemo(() => {
    const m: Record<string, string> = {};
    catalog.forEach((c) => { m[c.key] = c.label; });
    return m;
  }, [catalog]);

  const subOptions = useMemo(() => {
    const cat = catalog.find((c) => c.key === form.category);
    return cat?.subcategories || [];
  }, [catalog, form.category]);

  const loadCatalog = useCallback(async () => {
    try {
      const data = await apiFetch<ExpenseCat[]>('/api/expenses/categories');
      setCatalog(data);
    } catch { /* ignore */ }
  }, []);

  const loadList = useCallback(async (p = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((p - 1) * 20),
        limit: '20',
      });
      if (filterCategory !== 'all') params.set('category', filterCategory);
      if (filterStatus !== 'all') params.set('payment_status', filterStatus);
      if (filterRange) {
        params.set('date_from', filterRange[0].format('YYYY-MM-DD'));
        params.set('date_to', filterRange[1].format('YYYY-MM-DD'));
      }
      const data = await apiFetch<{ items: Expense[]; total: number }>(`/api/expenses?${params}`);
      setItems(data.items);
      setTotal(data.total);
      setPage(p);
    } catch (e: any) {
      message.error(e.message || 'Ошибка загрузки расходов');
    } finally {
      setLoading(false);
    }
  }, [page, filterCategory, filterStatus, filterRange]);

  const loadAnalytics = useCallback(async () => {
    try {
      const data = await apiFetch<Analytics>('/api/analytics/expenses?months=6');
      setAnalytics(data);
    } catch { /* ignore */ }
  }, []);

  const refreshAll = useCallback(async () => {
    await Promise.all([loadList(1), loadAnalytics()]);
  }, [loadList, loadAnalytics]);

  useEffect(() => {
    loadCatalog();
    refreshAll();
  }, []);

  useEffect(() => {
    loadList(1);
  }, [filterCategory, filterStatus, filterRange]);

  const openCreate = () => {
    setEditing(null);
    setForm({ ...emptyForm, subcategory: catalog[0]?.subcategories[0] || '' });
    setModalOpen(true);
  };

  const openEdit = (e: Expense) => {
    setEditing(e);
    setForm({
      name: e.name,
      amount: e.amount,
      category: e.category || 'other',
      subcategory: e.subcategory || '',
      payment_status: e.payment_status || 'paid',
      period_type: e.period_type || 'monthly',
      expense_date: e.expense_date ? dayjs(e.expense_date).format('YYYY-MM-DD') : dayjs().format('YYYY-MM-DD'),
      period_start: e.period_start ? dayjs(e.period_start).format('YYYY-MM-DD') : '',
      period_end: e.period_end ? dayjs(e.period_end).format('YYYY-MM-DD') : '',
      notes: e.notes || '',
    });
    setModalOpen(true);
  };

  const save = async () => {
    if (!form.name.trim()) { message.warning('Укажите описание'); return; }
    if (!form.amount) { message.warning('Укажите сумму'); return; }
    setSaving(true);
    try {
      const body = {
        ...form,
        period_start: form.period_start || null,
        period_end: form.period_end || null,
        subcategory: form.subcategory || null,
      };
      if (editing) {
        await apiFetch(`/api/expenses/${editing.id}`, { method: 'PUT', body: JSON.stringify(body) });
        message.success('Расход обновлён');
      } else {
        await apiFetch('/api/expenses', { method: 'POST', body: JSON.stringify(body) });
        message.success('Расход добавлен');
      }
      setModalOpen(false);
      await refreshAll();
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    } finally {
      setSaving(false);
    }
  };

  const remove = async (id: number, name: string) => {
    try {
      await apiFetch(`/api/expenses/${id}`, { method: 'DELETE' });
      message.success(`«${name}» удалён`);
      await refreshAll();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления');
    }
  };

  const pieData = (analytics?.by_category || []).map((c) => ({
    name: c.label,
    value: c.amount,
  }));

  const monthChart = (analytics?.by_month || []).map((m) => ({
    name: m.label,
    total: m.total,
    ...Object.fromEntries(
      Object.entries(m.by_category).map(([k, v]) => [catLabel[k] || k, v]),
    ),
  }));

  const categoryKeysForStack = useMemo(() => {
    const keys = new Set<string>();
    (analytics?.by_month || []).forEach((m) => {
      Object.keys(m.by_category).forEach((k) => keys.add(catLabel[k] || k));
    });
    return Array.from(keys).slice(0, 6);
  }, [analytics, catLabel]);

  return (
    <div className="expenses-module">
      <div className="flex-space-between mb-12" style={{ flexWrap: 'wrap', gap: 10 }}>
        <Text className="admin-panel-title">Учёт постоянных затрат</Text>
        <Space wrap>
          <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={refreshAll}>Обновить</Button>
          <Button icon={<PlusOutlined />} className="btn-gold" onClick={openCreate}>Добавить затрату</Button>
        </Space>
      </div>

      <Spin spinning={loading}>
        <Row gutter={[12, 12]} style={{ marginBottom: 16 }}>
          <Col xs={12} sm={6}>
            <Card className="admin-kpi-card" bordered={false}>
              <div className="admin-kpi-label">Всего за период</div>
              <div className="admin-kpi-value">{(analytics?.total || 0).toLocaleString()} ₽</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="admin-kpi-card tone-ok" bordered={false}>
              <div className="admin-kpi-label">Оплачено</div>
              <div className="admin-kpi-value">{(analytics?.paid_total || 0).toLocaleString()} ₽</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="admin-kpi-card tone-warn" bordered={false}>
              <div className="admin-kpi-label">Не оплачено</div>
              <div className="admin-kpi-value">{(analytics?.unpaid_total || 0).toLocaleString()} ₽</div>
            </Card>
          </Col>
          <Col xs={12} sm={6}>
            <Card className="admin-kpi-card tone-danger" bordered={false}>
              <div className="admin-kpi-label">Просрочено</div>
              <div className="admin-kpi-value">{(analytics?.overdue_total || 0).toLocaleString()} ₽</div>
            </Card>
          </Col>
        </Row>

        <Row gutter={[16, 16]} style={{ marginBottom: 16 }}>
          <Col xs={24} lg={10}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">Разбивка по категориям</Text>
              {pieData.length === 0 ? (
                <Empty description={<span className="text-titanium">Нет данных</span>} />
              ) : (
                <>
                  <div style={{ width: '100%', height: 220 }}>
                    <ResponsiveContainer>
                      <PieChart>
                        <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={50} outerRadius={80} paddingAngle={2}>
                          {pieData.map((_, i) => (
                            <Cell key={i} fill={PIE_COLORS[i % PIE_COLORS.length]} />
                          ))}
                        </Pie>
                        <RechartsTooltip
                          contentStyle={{ background: '#14161a', border: '1px solid rgba(212,168,75,0.3)' }}
                          formatter={(v: number) => [`${Number(v).toLocaleString()} ₽`, 'Сумма']}
                        />
                      </PieChart>
                    </ResponsiveContainer>
                  </div>
                  <div className="expense-cat-list">
                    {(analytics?.by_category || []).map((c) => (
                      <div key={c.category} className="expense-cat-row">
                        <span>{c.label}</span>
                        <b>{c.amount.toLocaleString()} ₽ · {c.share_percent}%</b>
                      </div>
                    ))}
                  </div>
                </>
              )}
            </Card>
          </Col>
          <Col xs={24} lg={14}>
            <Card className="admin-panel-card" bordered={false}>
              <Text className="admin-panel-title">Динамика по месяцам</Text>
              {monthChart.length === 0 ? (
                <Empty description={<span className="text-titanium">Нет данных</span>} />
              ) : (
                <div style={{ width: '100%', height: 280, marginTop: 8 }}>
                  <ResponsiveContainer>
                    <BarChart data={monthChart}>
                      <CartesianGrid stroke="rgba(255,255,255,0.06)" vertical={false} />
                      <XAxis dataKey="name" tick={{ fill: '#aab2bf', fontSize: 11 }} />
                      <YAxis tick={{ fill: '#aab2bf', fontSize: 11 }} width={48} />
                      <RechartsTooltip
                        contentStyle={{ background: '#14161a', border: '1px solid rgba(212,168,75,0.3)' }}
                      />
                      <Legend />
                      {categoryKeysForStack.length === 0 ? (
                        <Bar dataKey="total" name="Итого" fill="#D4A84B" radius={[6, 6, 0, 0]} />
                      ) : (
                        categoryKeysForStack.map((k, i) => (
                          <Bar key={k} dataKey={k} stackId="a" fill={PIE_COLORS[i % PIE_COLORS.length]} />
                        ))
                      )}
                    </BarChart>
                  </ResponsiveContainer>
                </div>
              )}
            </Card>
          </Col>
        </Row>

        <Card className="admin-panel-card" bordered={false} style={{ marginBottom: 16 }}>
          <Text className="admin-panel-title"><BulbOutlined /> ИИ-аналитика затрат</Text>
          <Row gutter={[12, 12]} style={{ marginTop: 12 }}>
            <Col xs={24} sm={12}>
              <Statistic
                title={<Text className="text-titanium text-12">Точка безубыточности</Text>}
                value={analytics?.break_even_revenue || 0}
                precision={0}
                suffix="₽/мес"
                valueStyle={{ color: '#D4A84B', fontSize: 20, fontWeight: 700 }}
              />
            </Col>
            <Col xs={24} sm={12}>
              <Statistic
                title={<Text className="text-titanium text-12">Прогноз прибыли</Text>}
                value={analytics?.forecast_profit || 0}
                precision={0}
                suffix="₽"
                prefix={<RiseOutlined />}
                valueStyle={{
                  color: (analytics?.forecast_profit || 0) >= 0 ? '#4ECB71' : '#ff4d4f',
                  fontSize: 20,
                  fontWeight: 700,
                }}
              />
            </Col>
          </Row>
          <div className="expense-insights" style={{ marginTop: 12 }}>
            {(analytics?.insights || []).length === 0 ? (
              <Text className="text-titanium text-13">Подсказки появятся после накопления данных</Text>
            ) : (
              (analytics?.insights || []).map((ins, idx) => (
                <div key={idx} className={`expense-insight severity-${ins.severity}`}>
                  <WarningOutlined />
                  <div>
                    <div className="title">{ins.title}</div>
                    <div className="msg">{ins.message}</div>
                  </div>
                </div>
              ))
            )}
          </div>
        </Card>

        <Card className="admin-panel-card" bordered={false}>
          <div className="appt-filters" style={{ marginBottom: 12 }}>
            <div className="appt-filters-controls">
              <Select
                value={filterCategory}
                onChange={setFilterCategory}
                className="appt-filter-select"
                style={{ minWidth: 180 }}
              >
                <Option value="all">Все категории</Option>
                {catalog.map((c) => (
                  <Option key={c.key} value={c.key}>{c.label}</Option>
                ))}
              </Select>
              <Select
                value={filterStatus}
                onChange={setFilterStatus}
                className="appt-filter-select"
                style={{ minWidth: 160 }}
              >
                <Option value="all">Все статусы</Option>
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <Option key={k} value={k}>{v}</Option>
                ))}
              </Select>
              <RangePicker
                value={filterRange}
                onChange={(v) => setFilterRange(v as [Dayjs, Dayjs] | null)}
                format="DD.MM.YYYY"
                className="appt-range-picker"
              />
            </div>
          </div>

          <Table
            dataSource={items}
            rowKey="id"
            size="small"
            pagination={{
              current: page,
              pageSize: 20,
              total,
              onChange: (p) => loadList(p),
              showSizeChanger: false,
            }}
            columns={[
              {
                title: <Text className="text-gold text-12">Описание</Text>,
                dataIndex: 'name',
                render: (v, r) => (
                  <div>
                    <Text className="text-white text-13">{v}</Text>
                    {r.notes && <div className="text-titanium text-11">{r.notes}</div>}
                  </div>
                ),
              },
              {
                title: <Text className="text-gold text-12">Категория</Text>,
                key: 'cat',
                render: (_, r) => (
                  <div>
                    <Tag className="tag-category">{catLabel[r.category] || r.category}</Tag>
                    {r.subcategory && <div className="text-titanium text-11">{r.subcategory}</div>}
                  </div>
                ),
              },
              {
                title: <Text className="text-gold text-12">Сумма</Text>,
                dataIndex: 'amount',
                width: 110,
                render: (v) => <Text className="text-gold-bold text-13">{Number(v).toLocaleString()} ₽</Text>,
              },
              {
                title: <Text className="text-gold text-12">Дата</Text>,
                dataIndex: 'expense_date',
                width: 100,
                render: (v) => <Text className="text-titanium text-12">{v ? dayjs(v).format('DD.MM.YYYY') : '—'}</Text>,
              },
              {
                title: <Text className="text-gold text-12">Период</Text>,
                dataIndex: 'period_type',
                width: 90,
                render: (v) => <Text className="text-titanium text-12">{PERIOD_LABELS[v] || v}</Text>,
              },
              {
                title: <Text className="text-gold text-12">Статус</Text>,
                dataIndex: 'payment_status',
                width: 120,
                render: (v) => <Tag color={STATUS_COLORS[v] || 'default'}>{STATUS_LABELS[v] || v}</Tag>,
              },
              {
                title: '',
                key: 'actions',
                width: 90,
                render: (_, r) => (
                  <Space size="small">
                    <Button size="small" icon={<EditOutlined />} className="btn-action-gold" onClick={() => openEdit(r)} />
                    <Popconfirm title={`Удалить «${r.name}»?`} onConfirm={() => remove(r.id, r.name)} okText="Да" cancelText="Нет">
                      <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                    </Popconfirm>
                  </Space>
                ),
              },
            ]}
          />
        </Card>
      </Spin>

      <Modal
        title={<Text className="text-gold-bold">{editing ? 'Редактировать затрату' : 'Новая затрата'}</Text>}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        className="modal-command"
        width={560}
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Описание *</span>
            <Input
              size="large"
              className="input-luxury"
              placeholder="Аренда бокса за март"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>
          <Row gutter={12}>
            <Col span={12}>
              <span className="label-field">Категория</span>
              <Select
                size="large"
                className="w-full"
                value={form.category}
                onChange={(v) => {
                  const cat = catalog.find((c) => c.key === v);
                  setForm((p) => ({
                    ...p,
                    category: v,
                    subcategory: cat?.subcategories[0] || '',
                  }));
                }}
              >
                {catalog.map((c) => (
                  <Option key={c.key} value={c.key}>{c.label}</Option>
                ))}
              </Select>
            </Col>
            <Col span={12}>
              <span className="label-field">Подкатегория</span>
              <Select
                size="large"
                className="w-full"
                value={form.subcategory || undefined}
                onChange={(v) => setForm((p) => ({ ...p, subcategory: v }))}
                allowClear
              >
                {subOptions.map((s) => (
                  <Option key={s} value={s}>{s}</Option>
                ))}
              </Select>
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <span className="label-field">Сумма *</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                value={form.amount || ''}
                onChange={(e) => setForm((p) => ({ ...p, amount: Number(e.target.value) }))}
              />
            </Col>
            <Col span={12}>
              <span className="label-field">Дата</span>
              <DatePicker
                size="large"
                className="w-full"
                value={form.expense_date ? dayjs(form.expense_date) : null}
                onChange={(d) => setForm((p) => ({ ...p, expense_date: d ? d.format('YYYY-MM-DD') : '' }))}
                format="DD.MM.YYYY"
              />
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <span className="label-field">Статус оплаты</span>
              <Select
                size="large"
                className="w-full"
                value={form.payment_status}
                onChange={(v) => setForm((p) => ({ ...p, payment_status: v }))}
              >
                {Object.entries(STATUS_LABELS).map(([k, v]) => (
                  <Option key={k} value={k}>{v}</Option>
                ))}
              </Select>
            </Col>
            <Col span={12}>
              <span className="label-field">Период</span>
              <Select
                size="large"
                className="w-full"
                value={form.period_type}
                onChange={(v) => setForm((p) => ({ ...p, period_type: v }))}
              >
                {Object.entries(PERIOD_LABELS).map(([k, v]) => (
                  <Option key={k} value={k}>{v}</Option>
                ))}
              </Select>
            </Col>
          </Row>
          <div>
            <span className="label-field">Заметка</span>
            <TextArea
              rows={2}
              className="input-luxury"
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
            />
          </div>
          <Button type="primary" size="large" className="btn-gold" loading={saving} onClick={save}>
            {editing ? 'Сохранить' : 'Добавить'}
          </Button>
        </Space>
      </Modal>
    </div>
  );
}
