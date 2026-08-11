/**
 * Склад — /technology/warehouse
 * CRUD номенклатуры через /api/materials. Card + Badge из дизайн-системы.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Typography, Row, Col, Table, Button, Space, message, Modal, Input,
  Popconfirm, Empty, Spin, Tooltip, Select, InputNumber,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined,
  WarningOutlined, InboxOutlined, SearchOutlined,
} from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';

const { Text } = Typography;
const { TextArea } = Input;

const API_BASE = '';
const PAGE_SIZE = 20;

const UNIT_OPTIONS = [
  { value: 'pcs', label: 'шт' },
  { value: 'ml', label: 'мл' },
  { value: 'l', label: 'л' },
  { value: 'g', label: 'г' },
  { value: 'kg', label: 'кг' },
  { value: 'm', label: 'м' },
  { value: 'pack', label: 'упак.' },
];

interface MaterialCategory {
  key: string;
  label: string;
}

interface Material {
  id: number;
  name: string;
  sku?: string | null;
  category: string;
  unit: string;
  quantity: number;
  min_quantity: number;
  purchase_price: number;
  supplier?: string | null;
  notes?: string | null;
  is_active: boolean;
  is_low_stock: boolean;
  stock_value: number;
  created_at?: string;
  updated_at?: string;
}

type MaterialForm = {
  name: string;
  sku: string;
  category: string;
  unit: string;
  quantity: number;
  min_quantity: number;
  purchase_price: number;
  supplier: string;
  notes: string;
  is_active: boolean;
};

const emptyForm = (): MaterialForm => ({
  name: '',
  sku: '',
  category: 'other',
  unit: 'pcs',
  quantity: 0,
  min_quantity: 0,
  purchase_price: 0,
  supplier: '',
  notes: '',
  is_active: true,
});

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
    const detail = body.detail;
    const msg = Array.isArray(detail)
      ? detail.map((d: { msg?: string }) => d.msg).filter(Boolean).join('; ')
      : (detail || `Ошибка ${res.status}`);
    throw new Error(msg);
  }
  return res.json();
}

function formatCurrency(val: number) {
  return `${Number(val || 0).toLocaleString('ru-RU')} ₽`;
}

function unitLabel(unit: string) {
  return UNIT_OPTIONS.find((u) => u.value === unit)?.label || unit;
}

export default function WarehousePage() {
  const [items, setItems] = useState<Material[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [categories, setCategories] = useState<MaterialCategory[]>([]);

  const [search, setSearch] = useState('');
  const [categoryFilter, setCategoryFilter] = useState<string | undefined>();
  const [lowStockOnly, setLowStockOnly] = useState(false);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<Material | null>(null);
  const [form, setForm] = useState<MaterialForm>(emptyForm);
  const [saving, setSaving] = useState(false);

  const [adjustOpen, setAdjustOpen] = useState(false);
  const [adjustTarget, setAdjustTarget] = useState<Material | null>(null);
  const [adjustDelta, setAdjustDelta] = useState<number>(1);
  const [adjusting, setAdjusting] = useState(false);

  const categoryLabel = useCallback(
    (key: string) => categories.find((c) => c.key === key)?.label || key,
    [categories],
  );

  const fetchCategories = useCallback(async () => {
    try {
      const data = await apiFetch<MaterialCategory[]>('/api/materials/categories');
      setCategories(data);
    } catch {
      /* ignore */
    }
  }, []);

  const fetchMaterials = useCallback(async (pageNum = page) => {
    setLoading(true);
    try {
      const skip = (pageNum - 1) * PAGE_SIZE;
      const params = new URLSearchParams({
        skip: String(skip),
        limit: String(PAGE_SIZE),
      });
      if (search.trim()) params.set('search', search.trim());
      if (categoryFilter) params.set('category', categoryFilter);
      if (lowStockOnly) params.set('low_stock_only', 'true');

      const data = await apiFetch<{ items: Material[]; total: number }>(
        `/api/materials?${params.toString()}`,
      );
      setItems(data.items);
      setTotal(data.total);
      setPage(pageNum);
    } catch {
      message.error('Ошибка загрузки склада');
    }
    setLoading(false);
  }, [page, search, categoryFilter, lowStockOnly]);

  useEffect(() => {
    fetchCategories();
  }, [fetchCategories]);

  useEffect(() => {
    fetchMaterials(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search, categoryFilter, lowStockOnly]);

  const kpi = useMemo(() => {
    const low = items.filter((m) => m.is_low_stock).length;
    const value = items.reduce((s, m) => s + (Number(m.stock_value) || 0), 0);
    return { total, low, value };
  }, [items, total]);

  const openCreate = () => {
    setEditing(null);
    setForm(emptyForm());
    setModalOpen(true);
  };

  const openEdit = (m: Material) => {
    setEditing(m);
    setForm({
      name: m.name,
      sku: m.sku || '',
      category: m.category || 'other',
      unit: m.unit || 'pcs',
      quantity: Number(m.quantity) || 0,
      min_quantity: Number(m.min_quantity) || 0,
      purchase_price: Number(m.purchase_price) || 0,
      supplier: m.supplier || '',
      notes: m.notes || '',
      is_active: m.is_active !== false,
    });
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!form.name.trim()) {
      message.warning('Укажите название');
      return;
    }
    setSaving(true);
    try {
      const payload = {
        name: form.name.trim(),
        sku: form.sku.trim() || null,
        category: form.category,
        unit: form.unit,
        quantity: form.quantity,
        min_quantity: form.min_quantity,
        purchase_price: form.purchase_price,
        supplier: form.supplier.trim() || null,
        notes: form.notes.trim() || null,
        is_active: form.is_active,
      };
      if (editing) {
        await apiFetch(`/api/materials/${editing.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            name: payload.name,
            sku: payload.sku,
            category: payload.category,
            unit: payload.unit,
            min_quantity: payload.min_quantity,
            purchase_price: payload.purchase_price,
            supplier: payload.supplier,
            notes: payload.notes,
            is_active: payload.is_active,
          }),
        });
        message.success('Позиция обновлена');
      } else {
        await apiFetch('/api/materials', {
          method: 'POST',
          body: JSON.stringify(payload),
        });
        message.success('Позиция создана');
      }
      setModalOpen(false);
      fetchMaterials(editing ? page : 1);
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка сохранения');
    }
    setSaving(false);
  };

  const handleDelete = async (id: number) => {
    try {
      await apiFetch(`/api/materials/${id}`, { method: 'DELETE' });
      message.success('Удалено');
      fetchMaterials(page);
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка удаления');
    }
  };

  const openAdjust = (m: Material) => {
    setAdjustTarget(m);
    setAdjustDelta(1);
    setAdjustOpen(true);
  };

  const handleAdjust = async () => {
    if (!adjustTarget || !adjustDelta) {
      message.warning('Укажите изменение остатка');
      return;
    }
    setAdjusting(true);
    try {
      await apiFetch(`/api/materials/${adjustTarget.id}/adjust?delta=${adjustDelta}`, {
        method: 'POST',
      });
      message.success(adjustDelta > 0 ? 'Приход учтён' : 'Расход учтён');
      setAdjustOpen(false);
      fetchMaterials(page);
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка изменения остатка');
    }
    setAdjusting(false);
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Технология</div>
          <h3>Склад</h3>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={() => fetchMaterials(page)}>
            Обновить
          </Button>
          <Button type="primary" icon={<PlusOutlined />} className="btn-gold" onClick={openCreate}>
            Добавить
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><InboxOutlined /></div>
            <div className="admin-kpi-label">Позиций</div>
            <div className="admin-kpi-value">{kpi.total}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><WarningOutlined /></div>
            <div className="admin-kpi-label">Низкий остаток</div>
            <div className="admin-kpi-value">{kpi.low}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="stats">
            <div className="admin-kpi-label">Стоимость на странице</div>
            <div className="admin-kpi-value text-gold-bold">{formatCurrency(kpi.value)}</div>
          </Card>
        </Col>
      </Row>

      <Card variant="admin" style={{ marginBottom: 16 }}>
        <Space wrap style={{ width: '100%' }}>
          <Input
            allowClear
            prefix={<SearchOutlined />}
            className="input-luxury"
            placeholder="Поиск: название, SKU, поставщик"
            value={search}
            onChange={(e) => setSearch(e.target.value)}
            style={{ minWidth: 240 }}
          />
          <Select
            allowClear
            placeholder="Категория"
            className="input-luxury"
            style={{ minWidth: 180 }}
            value={categoryFilter}
            onChange={(v) => setCategoryFilter(v)}
            options={categories.map((c) => ({ value: c.key, label: c.label }))}
          />
          <Button
            className={lowStockOnly ? 'btn-gold' : 'btn-gold-secondary'}
            type={lowStockOnly ? 'primary' : 'default'}
            icon={<WarningOutlined />}
            onClick={() => setLowStockOnly((v) => !v)}
          >
            Только низкий остаток
          </Button>
        </Space>
      </Card>

      <Spin spinning={loading}>
        {items.length === 0 && !loading ? (
          <Empty description={<Text className="text-titanium">Склад пуст</Text>} />
        ) : (
          <Table
            dataSource={items}
            rowKey="id"
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              onChange: (p) => fetchMaterials(p),
              showSizeChanger: false,
            }}
            columns={[
              {
                title: <Text className="text-gold">Название</Text>,
                key: 'name',
                render: (_, record) => (
                  <div>
                    <Text className="text-white text-medium">{record.name}</Text>
                    {record.sku ? (
                      <div><Text className="text-titanium text-13">SKU: {record.sku}</Text></div>
                    ) : null}
                  </div>
                ),
              },
              {
                title: <Text className="text-gold">Категория</Text>,
                dataIndex: 'category',
                key: 'category',
                render: (val: string) => (
                  <Badge variant="gold" size="sm">{categoryLabel(val)}</Badge>
                ),
              },
              {
                title: <Text className="text-gold">Остаток</Text>,
                key: 'quantity',
                render: (_, record) => (
                  <Space>
                    <Text className="text-white">
                      {Number(record.quantity).toLocaleString('ru-RU')} {unitLabel(record.unit)}
                    </Text>
                    {record.is_low_stock ? (
                      <Badge variant="warning" size="sm">мало</Badge>
                    ) : (
                      <Badge variant="success" size="sm">норма</Badge>
                    )}
                  </Space>
                ),
              },
              {
                title: <Text className="text-gold">Мин.</Text>,
                dataIndex: 'min_quantity',
                key: 'min_quantity',
                render: (val: number) => (
                  <Text className="text-titanium">{Number(val).toLocaleString('ru-RU')}</Text>
                ),
              },
              {
                title: <Text className="text-gold">Цена</Text>,
                dataIndex: 'purchase_price',
                key: 'purchase_price',
                render: (val: number) => (
                  <Text className="text-gold-bold">{formatCurrency(val)}</Text>
                ),
              },
              {
                title: <Text className="text-gold">Сумма</Text>,
                dataIndex: 'stock_value',
                key: 'stock_value',
                render: (val: number) => (
                  <Text className="text-white">{formatCurrency(val)}</Text>
                ),
              },
              {
                title: '',
                key: 'actions',
                width: 160,
                render: (_, record) => (
                  <Space>
                    <Tooltip title="Приход / расход">
                      <Button
                        size="small"
                        className="btn-action-gold"
                        onClick={() => openAdjust(record)}
                      >
                        ±
                      </Button>
                    </Tooltip>
                    <Tooltip title="Редактировать">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        className="btn-action-gold"
                        onClick={() => openEdit(record)}
                      />
                    </Tooltip>
                    <Popconfirm
                      title="Удалить позицию?"
                      onConfirm={() => handleDelete(record.id)}
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
      </Spin>

      <Modal
        title={(
          <Text className="text-gold-bold">
            {editing ? 'Редактировать позицию' : 'Новая позиция склада'}
          </Text>
        )}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        className="modal-command"
        destroyOnClose
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Название *</span>
            <Input
              size="large"
              className="input-luxury"
              value={form.name}
              onChange={(e) => setForm((p) => ({ ...p, name: e.target.value }))}
            />
          </div>
          <Row gutter={12}>
            <Col span={12}>
              <span className="label-field">SKU / артикул</span>
              <Input
                size="large"
                className="input-luxury"
                value={form.sku}
                onChange={(e) => setForm((p) => ({ ...p, sku: e.target.value }))}
              />
            </Col>
            <Col span={12}>
              <span className="label-field">Поставщик</span>
              <Input
                size="large"
                className="input-luxury"
                value={form.supplier}
                onChange={(e) => setForm((p) => ({ ...p, supplier: e.target.value }))}
              />
            </Col>
          </Row>
          <Row gutter={12}>
            <Col span={12}>
              <span className="label-field">Категория</span>
              <Select
                size="large"
                className="input-luxury"
                style={{ width: '100%' }}
                value={form.category}
                onChange={(v) => setForm((p) => ({ ...p, category: v }))}
                options={categories.map((c) => ({ value: c.key, label: c.label }))}
              />
            </Col>
            <Col span={12}>
              <span className="label-field">Ед. изм.</span>
              <Select
                size="large"
                className="input-luxury"
                style={{ width: '100%' }}
                value={form.unit}
                onChange={(v) => setForm((p) => ({ ...p, unit: v }))}
                options={UNIT_OPTIONS}
              />
            </Col>
          </Row>
          <Row gutter={12}>
            {!editing && (
              <Col span={8}>
                <span className="label-field">Остаток</span>
                <InputNumber
                  size="large"
                  className="input-luxury"
                  style={{ width: '100%' }}
                  min={0}
                  value={form.quantity}
                  onChange={(v) => setForm((p) => ({ ...p, quantity: Number(v) || 0 }))}
                />
              </Col>
            )}
            <Col span={editing ? 12 : 8}>
              <span className="label-field">Мин. запас</span>
              <InputNumber
                size="large"
                className="input-luxury"
                style={{ width: '100%' }}
                min={0}
                value={form.min_quantity}
                onChange={(v) => setForm((p) => ({ ...p, min_quantity: Number(v) || 0 }))}
              />
            </Col>
            <Col span={editing ? 12 : 8}>
              <span className="label-field">Цена закупки</span>
              <InputNumber
                size="large"
                className="input-luxury"
                style={{ width: '100%' }}
                min={0}
                value={form.purchase_price}
                onChange={(v) => setForm((p) => ({ ...p, purchase_price: Number(v) || 0 }))}
              />
            </Col>
          </Row>
          <div>
            <span className="label-field">Заметки</span>
            <TextArea
              rows={2}
              className="input-luxury"
              value={form.notes}
              onChange={(e) => setForm((p) => ({ ...p, notes: e.target.value }))}
            />
          </div>
          <Button type="primary" size="large" className="btn-gold" loading={saving} onClick={handleSave}>
            {editing ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>

      <Modal
        title={<Text className="text-gold-bold">Приход / расход</Text>}
        open={adjustOpen}
        onCancel={() => setAdjustOpen(false)}
        footer={null}
        className="modal-command"
        destroyOnClose
      >
        {adjustTarget && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <Text className="text-white">{adjustTarget.name}</Text>
            <Text className="text-titanium">
              Текущий остаток: {Number(adjustTarget.quantity).toLocaleString('ru-RU')}{' '}
              {unitLabel(adjustTarget.unit)}
            </Text>
            <div>
              <span className="label-field">Изменение (+ приход, − расход)</span>
              <InputNumber
                size="large"
                className="input-luxury"
                style={{ width: '100%' }}
                value={adjustDelta}
                onChange={(v) => setAdjustDelta(Number(v) || 0)}
              />
            </div>
            <Space>
              <Button onClick={() => setAdjustDelta(Math.abs(adjustDelta) || 1)}>+ Приход</Button>
              <Button onClick={() => setAdjustDelta(-Math.abs(adjustDelta || 1))}>- Расход</Button>
            </Space>
            <Button type="primary" className="btn-gold" loading={adjusting} onClick={handleAdjust}>
              Применить
            </Button>
          </Space>
        )}
      </Modal>
    </>
  );
}
