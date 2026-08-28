/**
 * Техкарты — /technology/tech-cards
 * Пошаговые инструкции услуги: блоки, материалы, фото, длительность.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import {
  Typography, Row, Col, Table, Space, message, Popconfirm, Empty, Spin, Tooltip,
} from 'antd';
import {
  DeleteOutlined, EditOutlined, PlusOutlined, ReloadOutlined,
  SearchOutlined, FileTextOutlined, ToolOutlined, EyeOutlined,
  ClockCircleOutlined,
} from '@ant-design/icons';
import { Button, Input, Card, Badge } from '../../../components/ui';
import TechCardForm from './TechCardForm';
import { DurationMark } from './Marks';
import StepPhoto from './StepPhoto';
import {
  DraftBlock,
  MaterialOption,
  ServiceOption,
  TechCard,
  apiFetch,
  cardToDraftBlocks,
  formatCurrency,
  formatDuration,
  formatUnit,
  newDraftBlock,
} from './types';

const { Text } = Typography;
const PAGE_SIZE = 20;

export default function TechCardsPage() {
  const navigate = useNavigate();
  const location = useLocation();
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
  const [draftBlocks, setDraftBlocks] = useState<DraftBlock[]>([newDraftBlock('Блок 1')]);
  const [saving, setSaving] = useState(false);

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
      return data.items;
    } catch {
      message.error('Ошибка загрузки техкарт');
      return [] as TechCard[];
    } finally {
      setLoading(false);
    }
  }, [page, search]);

  useEffect(() => {
    fetchLookups();
  }, [fetchLookups]);

  useEffect(() => {
    fetchCards(1);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [search]);

  const openCreate = () => {
    setEditing(null);
    setServiceId(undefined);
    setCardName('');
    setCardNotes('');
    setDraftBlocks([newDraftBlock('Блок 1')]);
    setModalOpen(true);
  };

  const openEdit = async (card: TechCard) => {
    setEditing(card);
    setServiceId(card.service_id);
    setCardName(card.name || card.service_name || '');
    setCardNotes(card.notes || '');
    setDraftBlocks(cardToDraftBlocks(card));
    setModalOpen(true);
    try {
      const full = await apiFetch<TechCard>(`/api/tech-cards/${card.id}`);
      setEditing(full);
      setServiceId(full.service_id);
      setCardName(full.name || full.service_name || '');
      setCardNotes(full.notes || '');
      setDraftBlocks(cardToDraftBlocks(full));
    } catch {
      /* список уже содержит карту */
    }
  };

  useEffect(() => {
    const editId = (location.state as { editId?: number } | null)?.editId;
    if (!editId || !cards.length) return;
    const found = cards.find((c) => c.id === editId);
    if (found) {
      openEdit(found);
      navigate(location.pathname, { replace: true, state: {} });
    }
  }, [cards, location.state, location.pathname, navigate]);

  const handleSave = async () => {
    if (!serviceId && !editing) {
      message.warning('Выберите услугу');
      return;
    }
    const untitled = draftBlocks.find((b) => !b.title.trim());
    if (untitled) {
      message.warning('У каждого блока должно быть название');
      return;
    }
    const blocks = draftBlocks.map((b) => ({
      title: b.title.trim(),
      description: b.description.trim() || null,
      duration_minutes: Number(b.duration_minutes) || 0,
      photo_url: b.photo_url || null,
      items: b.items
        .filter((r) => r.material_id && Number(r.quantity) > 0)
        .map((r) => ({
          material_id: r.material_id as number,
          quantity: Number(r.quantity),
        })),
    }));
    for (const block of blocks) {
      const ids = block.items.map((i) => i.material_id);
      if (new Set(ids).size !== ids.length) {
        message.warning(`В блоке «${block.title}» материал указан дважды`);
        return;
      }
    }

    setSaving(true);
    try {
      if (editing) {
        await apiFetch(`/api/tech-cards/${editing.id}`, {
          method: 'PUT',
          body: JSON.stringify({
            name: cardName.trim() || null,
            notes: cardNotes.trim() || null,
            blocks,
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
            blocks,
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
          <h3>Технология / Техкарты</h3>
        </div>
        <Space wrap>
          <Button icon={<ReloadOutlined />} look="ghost" onClick={() => fetchCards(page)}>
            Обновить
          </Button>
          <Button type="primary" icon={<PlusOutlined />} look="gold" onClick={openCreate}>
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
            <div className="admin-kpi-label">Стоимость материалов</div>
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
          <Empty description={<Text className="text-titanium">Нет техкарт — соберите инструкцию из шагов</Text>} />
        ) : (
          <Card variant="admin">
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
              expandedRowRender: (record) => {
                const blocks = record.blocks || [];
                const totalMins = Number(record.total_duration_minutes)
                  || blocks.reduce((s, b) => s + (Number(b.duration_minutes) || 0), 0);
                if (blocks.length === 0) {
                  return <Text className="text-titanium">Нет шагов</Text>;
                }
                return (
                  <div className="tech-card-expand">
                    {blocks.map((block, idx) => (
                      <Card key={block.id || idx} variant="admin" className="tech-card-step">
                        <div className="tech-card-step-head">
                          <div className="tech-card-step-title">
                            <span className="tech-card-step-index">{idx + 1}</span>
                            <span className="tech-card-step-name">{block.title || 'Без названия'}</span>
                          </div>
                          <DurationMark minutes={block.duration_minutes || 0} />
                        </div>
                        {block.description ? (
                          <div className="tech-card-step-row">
                            <FileTextOutlined className="tech-card-step-icon" />
                            <span className="tech-card-step-desc">{block.description}</span>
                          </div>
                        ) : null}
                        {block.photo_url ? (
                          <div className="tech-card-step-row">
                            <StepPhoto
                              src={block.photo_url}
                              alt={block.title || `Шаг ${idx + 1}`}
                              size="thumb"
                            />
                          </div>
                        ) : null}
                        {block.items?.length ? (
                          <div className="tech-card-step-row">
                            <ToolOutlined className="tech-card-step-icon" />
                            <Text className="text-gold text-13">
                              {block.items.map((i) => `${i.material_name} (${i.quantity} ${formatUnit(i.material_unit)})`).join(', ')}
                            </Text>
                          </div>
                        ) : null}
                      </Card>
                    ))}
                    <div className="tech-card-expand-total">
                      <ClockCircleOutlined className="tech-card-step-icon" />
                      <Text className="text-gold-bold">
                        Общая длительность: {formatDuration(totalMins)}
                      </Text>
                    </div>
                  </div>
                );
              },
            }}
            columns={[
              {
                title: <Text className="text-gold">Услуга</Text>,
                key: 'service',
                render: (_, record) => (
                  <div>
                    <Text className="text-gold text-medium">{record.service_name}</Text>
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
                title: <Text className="text-gold">Шагов</Text>,
                dataIndex: 'blocks_count',
                render: (val: number) => <Badge variant="gold" size="sm">{val || 0}</Badge>,
              },
              {
                title: <Text className="text-gold">Время</Text>,
                dataIndex: 'total_duration_minutes',
                render: (val: number) => (
                  <Space size={6}>
                    <ClockCircleOutlined className="text-gold" />
                    <Text className="text-gold">{formatDuration(val || 0)}</Text>
                  </Space>
                ),
              },
              {
                title: <Text className="text-gold">Материалов</Text>,
                dataIndex: 'items_count',
                render: (val: number) => <Badge variant="gold" size="sm">{val}</Badge>,
              },
              {
                title: <Text className="text-gold">Себест. материалов</Text>,
                dataIndex: 'estimated_cost',
                render: (val: number) => <Text className="text-gold">{formatCurrency(val)}</Text>,
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
                width: 150,
                render: (_, record) => (
                  <Space>
                    <Tooltip title="Инструкция">
                      <Button
                        size="small"
                        icon={<EyeOutlined />}
                        className="btn-action-gold"
                        onClick={() => navigate(`/technology/tech-cards/${record.id}`)}
                      />
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
          </Card>
        )}
      </Spin>

      <TechCardForm
        open={modalOpen}
        editing={editing}
        materials={materials}
        serviceOptions={serviceOptions}
        draftBlocks={draftBlocks}
        serviceId={serviceId}
        cardName={cardName}
        cardNotes={cardNotes}
        saving={saving}
        onClose={() => setModalOpen(false)}
        onServiceId={setServiceId}
        onCardName={setCardName}
        onCardNotes={setCardNotes}
        onBlocks={setDraftBlocks}
        onSave={handleSave}
      />
    </>
  );
}
