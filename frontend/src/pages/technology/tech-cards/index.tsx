/**
 * Техкарты — /technology/tech-cards
 * Привязка услуг к материалам склада (BOM на услугу).
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Typography, Row, Col, Table, Button, Space, message, Modal, Input,
  Popconfirm, Empty, Spin, Tooltip, Select, InputNumber,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined,
  SearchOutlined, FileTextOutlined, ToolOutlined,
} from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';

const { Text } = Typography;
const { TextArea } = Input;

const API_BASE = '';
const PAGE_SIZE = 20;

interface ServiceOption {
  id: number;
  name: string;
  price: number;
}

interface MaterialOption {
  id: number;
  name: string;
  unit: string;
  sku?: string | null;
  purchase_price: number;
  quantity: number;
}

interface TechCardItem {
  id?: number;
  material_id: number;
  material_name?: string;
  material_unit?: string;
  purchase_price?: number;
  stock_quantity?: number;
  quantity: number;
  line_cost?: number;
  notes?: string | null;
  is_low_stock?: boolean;
}

interface TechCard {
  id: number;
  service_id: number;
  service_name: string;
  service_price: number;
  name?: string | null;
  notes?: string | null;
  is_active: boolean;
  items: TechCardItem[];
  items_count: number;
  estimated_cost: number;
}

type DraftItem = {
  key: string;
  material_id?: number;
  quantity: number;
  notes: string;
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

function newDraftItem(): DraftItem {
  return { key: `${Date.now()}-${Math.random()}`, quantity: 1, notes: '' };
}

export default function TechCardsPage() {
  const [cards, setCards] = useState<TechCard[]>([]);
  const [total, setTotal] = useState(0);
  const [page, setPage] = useState(1);
  const [loading, setLoading] = useState(false);
  const [search, setSearch] = useState('');

  const [services, setServices] = useState<ServiceOption[]>([]);
  const [materials, setMaterials] = useState<MaterialOption[]>([]);

  const [modalOpen, setModalOpen] = useState(false);
  const [editing, setEditing] = useState<TechCard | null>(null);
  const [serviceId, setServiceId] = useState<number | undefined>();
  const [cardName, setCardName] = useState('');
  const [cardNotes, setCardNotes] = useState('');
  const [draftItems, setDraftItems] = useState<DraftItem[]>([newDraftItem()]);
  const [saving, setSaving] = useState(false);

  const materialMap = useMemo(() => {
    const m = new Map<number, MaterialOption>();
    materials.forEach((x) => m.set(x.id, x));
    return m;
  }, [materials]);

  const usedServiceIds = useMemo(
    () => new Set(cards.map((c) => c.service_id)),
    [cards],
  );

  const serviceOptions = useMemo(() => {
    return services
      .filter((s) => editing?.service_id === s.id || !usedServiceIds.has(s.id))
      .map((s) => ({
        value: s.id,
        label: `${s.name} · ${formatCurrency(s.price)}`,
      }));
  }, [services, usedServiceIds, editing]);

  const fetchLookups = useCallback(async () => {
    try {
      const [svc, mat] = await Promise.all([
        apiFetch<{ items: ServiceOption[] }>('/api/services?skip=0&limit=500'),
        apiFetch<{ items: MaterialOption[] }>('/api/materials?skip=0&limit=500&is_active=true'),
      ]);
      setServices(svc.items || []);
      setMaterials(mat.items || []);
    } catch {
      /* ignore */
    }
  }, []);

  const fetchCards = useCallback(async (pageNum = page) => {
    setLoading(true);
    try {
      const params = new URLSearchParams({
        skip: String((pageNum - 1) * PAGE_SIZE),
        limit: String(PAGE_SIZE),
      });
      if (search.trim()) params.set('search', search.trim());
      const data = await apiFetch<{ items: TechCard[]; total: number }>(
        `/api/tech-cards?${params.toString()}`,
      );
      setCards(data.items);
      setTotal(data.total);
      setPage(pageNum);
    } catch {
      message.error('Ошибка загрузки техкарт');
    }
    setLoading(false);
  }, [page, search]);

  useEffect(() => {
    fetchLookups();
  }, [fetchLookups]);

  useEffect(() => {
    fetchCards(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const draftCost = useMemo(() => {
    return draftItems.reduce((sum, row) => {
      if (!row.material_id) return sum;
      const mat = materialMap.get(row.material_id);
      return sum + (Number(row.quantity) || 0) * (Number(mat?.purchase_price) || 0);
    }, 0);
  }, [draftItems, materialMap]);

  const openCreate = () => {
    setEditing(null);
    setServiceId(undefined);
    setCardName('');
    setCardNotes('');
    setDraftItems([newDraftItem()]);
    setModalOpen(true);
  };

  const openEdit = (card: TechCard) => {
    setEditing(card);
    setServiceId(card.service_id);
    setCardName(card.name || card.service_name || '');
    setCardNotes(card.notes || '');
    setDraftItems(
      card.items.length
        ? card.items.map((i) => ({
            key: `e-${i.id || i.material_id}`,
            material_id: i.material_id,
            quantity: Number(i.quantity) || 1,
            notes: i.notes || '',
          }))
        : [newDraftItem()],
    );
    setModalOpen(true);
  };

  const handleSave = async () => {
    if (!serviceId && !editing) {
      message.warning('Выберите услугу');
      return;
    }
    const items = draftItems
      .filter((r) => r.material_id && Number(r.quantity) > 0)
      .map((r) => ({
        material_id: r.material_id as number,
        quantity: Number(r.quantity),
        notes: r.notes.trim() || null,
      }));
    if (items.length === 0) {
      message.warning('Добавьте хотя бы один материал');
      return;
    }
    const ids = items.map((i) => i.material_id);
    if (new Set(ids).size !== ids.length) {
      message.warning('Материал указан дважды');
      return;
    }

    setSaving(true);
    try {
      if (editing) {
        await apiFetch(`/api/tech-cards/${editing.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            name: cardName.trim() || null,
            notes: cardNotes.trim() || null,
            items,
          }),
        });
        message.success('Техкарта обновлена');
      } else {
        await apiFetch('/api/tech-cards', {
          method: 'POST',
          body: JSON.stringify({
            service_id: serviceId,
            name: cardName.trim() || null,
            notes: cardNotes.trim() || null,
            items,
          }),
        });
        message.success('Техкарта создана');
      }
      setModalOpen(false);
      fetchCards(editing ? page : 1);
      fetchLookups();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка сохранения');
    }
    setSaving(false);
  };

  const handleDelete = async (id: number) => {
    try {
      await apiFetch(`/api/tech-cards/${id}`, { method: 'DELETE' });
      message.success('Удалено');
      fetchCards(page);
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка удаления');
    }
  };

  const kpi = useMemo(() => ({
    total,
    withItems: cards.filter((c) => c.items_count > 0).length,
    costSum: cards.reduce((s, c) => s + (Number(c.estimated_cost) || 0), 0),
  }), [cards, total]);

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Технология</div>
          <h3>Техкарты</h3>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={() => fetchCards(page)}>
            Обновить
          </Button>
          <Button type="primary" icon={<PlusOutlined />} className="btn-gold" onClick={openCreate}>
            Новая техкарта
          </Button>
        </Space>
      </div>

      <Row gutter={[14, 14]} style={{ marginBottom: 16 }}>
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><FileTextOutlined /></div>
            <div className="admin-kpi-label">Техкарт</div>
            <div className="admin-kpi-value">{kpi.total}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="kpi">
            <div className="admin-kpi-icon"><ToolOutlined /></div>
            <div className="admin-kpi-label">С материалами</div>
            <div className="admin-kpi-value">{kpi.withItems}</div>
          </Card>
        </Col>
        <Col xs={24} sm={8}>
          <Card variant="stats">
            <div className="admin-kpi-label">Себестоимость материалов (на стр.)</div>
            <div className="admin-kpi-value text-gold-bold">{formatCurrency(kpi.costSum)}</div>
          </Card>
        </Col>
      </Row>

      <Card variant="admin" style={{ marginBottom: 16 }}>
        <Input
          allowClear
          prefix={<SearchOutlined />}
          className="input-luxury"
          placeholder="Поиск по услуге / названию техкарты"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ maxWidth: 420 }}
        />
      </Card>

      <Spin spinning={loading}>
        {cards.length === 0 && !loading ? (
          <Empty description={<Text className="text-titanium">Нет техкарт — привяжите материалы к услугам</Text>} />
        ) : (
          <Table
            dataSource={cards}
            rowKey="id"
            pagination={{
              current: page,
              pageSize: PAGE_SIZE,
              total,
              onChange: (p) => fetchCards(p),
              showSizeChanger: false,
            }}
            expandable={{
              expandedRowRender: (record) => (
                <Table
                  size="small"
                  pagination={false}
                  rowKey={(r) => `${r.material_id}-${r.quantity}`}
                  dataSource={record.items}
                  columns={[
                    {
                      title: <Text className="text-gold">Материал</Text>,
                      render: (_, row) => (
                        <div>
                          <Text className="text-white">{row.material_name}</Text>
                          {row.is_low_stock ? (
                            <div><Badge variant="warning" size="sm">мало на складе</Badge></div>
                          ) : null}
                        </div>
                      ),
                    },
                    {
                      title: <Text className="text-gold">Расход</Text>,
                      render: (_, row) => (
                        <Text className="text-white">
                          {Number(row.quantity).toLocaleString('ru-RU')} {row.material_unit}
                        </Text>
                      ),
                    },
                    {
                      title: <Text className="text-gold">Склад</Text>,
                      render: (_, row) => (
                        <Text className="text-titanium">
                          {Number(row.stock_quantity || 0).toLocaleString('ru-RU')}
                        </Text>
                      ),
                    },
                    {
                      title: <Text className="text-gold">Стоимость</Text>,
                      render: (_, row) => (
                        <Text className="text-gold-bold">{formatCurrency(row.line_cost || 0)}</Text>
                      ),
                    },
                  ]}
                />
              ),
            }}
            columns={[
              {
                title: <Text className="text-gold">Услуга</Text>,
                key: 'service',
                render: (_, record) => (
                  <div>
                    <Text className="text-white text-medium">{record.service_name}</Text>
                    {record.name && record.name !== record.service_name ? (
                      <div><Text className="text-titanium text-13">{record.name}</Text></div>
                    ) : null}
                  </div>
                ),
              },
              {
                title: <Text className="text-gold">Цена услуги</Text>,
                dataIndex: 'service_price',
                render: (val: number) => <Text className="text-gold-bold">{formatCurrency(val)}</Text>,
              },
              {
                title: <Text className="text-gold">Материалов</Text>,
                dataIndex: 'items_count',
                render: (val: number) => <Badge variant="info" size="sm">{val}</Badge>,
              },
              {
                title: <Text className="text-gold">Себест. материалов</Text>,
                dataIndex: 'estimated_cost',
                render: (val: number) => <Text className="text-white">{formatCurrency(val)}</Text>,
              },
              {
                title: <Text className="text-gold">Статус</Text>,
                dataIndex: 'is_active',
                render: (val: boolean) => (
                  val
                    ? <Badge variant="success" size="sm">активна</Badge>
                    : <Badge variant="neutral" size="sm">выкл</Badge>
                ),
              },
              {
                title: '',
                key: 'actions',
                width: 120,
                render: (_, record) => (
                  <Space>
                    <Tooltip title="Редактировать">
                      <Button
                        size="small"
                        icon={<EditOutlined />}
                        className="btn-action-gold"
                        onClick={() => openEdit(record)}
                      />
                    </Tooltip>
                    <Popconfirm
                      title="Удалить техкарту?"
                      onConfirm={() => handleDelete(record.id)}
                      okText="Да"
                      cancelText="Нет"
                    >
                      <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
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
            {editing ? 'Редактировать техкарту' : 'Новая техкарта'}
          </Text>
        )}
        open={modalOpen}
        onCancel={() => setModalOpen(false)}
        footer={null}
        className="modal-command"
        width={720}
        destroyOnClose
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Услуга *</span>
            <Select
              size="large"
              className="input-luxury"
              style={{ width: '100%' }}
              placeholder="Выберите услугу"
              value={serviceId}
              disabled={!!editing}
              onChange={setServiceId}
              options={serviceOptions}
              showSearch
              optionFilterProp="label"
            />
          </div>
          <div>
            <span className="label-field">Название техкарты</span>
            <Input
              size="large"
              className="input-luxury"
              placeholder="По умолчанию — название услуги"
              value={cardName}
              onChange={(e) => setCardName(e.target.value)}
            />
          </div>
          <div>
            <span className="label-field">Заметки</span>
            <TextArea
              rows={2}
              className="input-luxury"
              value={cardNotes}
              onChange={(e) => setCardNotes(e.target.value)}
            />
          </div>

          <div>
            <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
              <span className="label-field">Материалы</span>
              <Button size="small" icon={<PlusOutlined />} onClick={() => setDraftItems((p) => [...p, newDraftItem()])}>
                Строка
              </Button>
            </div>
            <Space direction="vertical" style={{ width: '100%' }} size="small">
              {draftItems.map((row, idx) => {
                const mat = row.material_id ? materialMap.get(row.material_id) : undefined;
                return (
                  <Row key={row.key} gutter={8} align="middle">
                    <Col span={12}>
                      <Select
                        className="input-luxury"
                        style={{ width: '100%' }}
                        placeholder="Материал"
                        value={row.material_id}
                        showSearch
                        optionFilterProp="label"
                        options={materials.map((m) => ({
                          value: m.id,
                          label: `${m.name}${m.sku ? ` (${m.sku})` : ''}`,
                        }))}
                        onChange={(v) => setDraftItems((prev) => prev.map((r, i) => (
                          i === idx ? { ...r, material_id: v } : r
                        )))}
                      />
                    </Col>
                    <Col span={6}>
                      <InputNumber
                        className="input-luxury"
                        style={{ width: '100%' }}
                        min={0.001}
                        step={0.1}
                        value={row.quantity}
                        addonAfter={mat?.unit || ''}
                        onChange={(v) => setDraftItems((prev) => prev.map((r, i) => (
                          i === idx ? { ...r, quantity: Number(v) || 0 } : r
                        )))}
                      />
                    </Col>
                    <Col span={4}>
                      <Text className="text-titanium">
                        {mat ? formatCurrency((Number(row.quantity) || 0) * Number(mat.purchase_price || 0)) : '—'}
                      </Text>
                    </Col>
                    <Col span={2}>
                      <Button
                        danger
                        size="small"
                        icon={<DeleteOutlined />}
                        disabled={draftItems.length <= 1}
                        onClick={() => setDraftItems((prev) => prev.filter((_, i) => i !== idx))}
                      />
                    </Col>
                  </Row>
                );
              })}
            </Space>
            <Text className="text-gold-bold d-block" style={{ marginTop: 10 }}>
              Итого материалов: {formatCurrency(draftCost)}
            </Text>
          </div>

          <Button type="primary" size="large" className="btn-gold" loading={saving} onClick={handleSave}>
            {editing ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>
    </>
  );
}
