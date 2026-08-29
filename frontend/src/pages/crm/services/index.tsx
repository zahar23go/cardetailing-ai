/**
 * Услуги — /crm/services
 * Каталог услуг + CRUD. Локальный state.
 */
import React, { useEffect, useState } from 'react';
import {
  Typography,
  Row,
  Col,
  Table,
  Tag,
  Space,
  message,
  Popconfirm,
  Empty,
  Spin,
  Tooltip,
} from 'antd';
import { Button, Modal, Input } from '../../../components/ui';
import { DeleteOutlined, EditOutlined, PlusOutlined } from '@ant-design/icons';

const { Text } = Typography;
const { TextArea } = Input;

const API_BASE = '';
const PAGE_SIZE = 20;

interface Service {
  id: number;
  name: string;
  description: string;
  category?: string;
  price: number;
  duration: number;
  material_cost?: number;
  cost_price?: number;
  margin_percent?: number;
  is_active?: boolean;
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

function formatCurrency(val: number) {
  return `${val.toLocaleString()} ₽`;
}

export default function ServicesPage() {
  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [servicesTotal, setServicesTotal] = useState(0);
  const [servicesPage, setServicesPage] = useState(1);

  const [serviceModal, setServiceModal] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [serviceForm, setServiceForm] = useState({
    name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0, cost_price: 0,
  });
  const [serviceSaving, setServiceSaving] = useState(false);

  const fetchServices = async (page = servicesPage) => {
    setServicesLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data = await apiFetch<{ items: Service[]; total: number }>(
        `/api/services?skip=${skip}&limit=${PAGE_SIZE}`,
      );
      setServices(data.items);
      setServicesTotal(data.total);
      setServicesPage(page);
    } catch {
      message.error('Ошибка загрузки услуг');
    }
    setServicesLoading(false);
  };

  useEffect(() => {
    fetchServices(1);
  }, []);

  const openServiceModal = (service?: Service) => {
    if (service) {
      setEditingService(service);
      setServiceForm({
        name: service.name,
        description: service.description || '',
        category: service.category || '',
        price: service.price,
        duration: service.duration,
        material_cost: service.material_cost || 0,
        cost_price: service.cost_price ?? service.material_cost ?? 0,
      });
    } else {
      setEditingService(null);
      setServiceForm({
        name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0, cost_price: 0,
      });
    }
    setServiceModal(true);
  };

  const handleSaveService = async () => {
    if (!serviceForm.name.trim()) {
      message.warning('Укажите название услуги');
      return;
    }
    setServiceSaving(true);
    try {
      if (editingService) {
        await apiFetch(`/api/services/${editingService.id}`, {
          method: 'PUT',
          body: JSON.stringify(serviceForm),
        });
        message.success('✅ Услуга обновлена');
      } else {
        await apiFetch('/api/services', {
          method: 'POST',
          body: JSON.stringify(serviceForm),
        });
        message.success('✅ Услуга создана');
      }
      setServiceModal(false);
      fetchServices();
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setServiceSaving(false);
  };

  const handleDeleteService = async (id: number) => {
    try {
      await apiFetch(`/api/services/${id}`, { method: 'DELETE' });
      message.success('✅ Услуга удалена');
      fetchServices();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления');
    }
  };

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Каталог</div>
          <h3>Услуги детейлинга</h3>
        </div>
      </div>

      <Spin spinning={servicesLoading}>
        <div className="toolbar-right">
          <Button type="primary" icon={<PlusOutlined />} look="gold" onClick={() => openServiceModal()}>
            Добавить услугу
          </Button>
        </div>
        {services.length === 0 && !servicesLoading ? (
          <Empty description={<Text className="text-titanium">Нет услуг</Text>} />
        ) : (
          <Table
            dataSource={services}
            rowKey="id"
            pagination={{
              current: servicesPage,
              pageSize: PAGE_SIZE,
              total: servicesTotal,
              onChange: (page) => fetchServices(page),
              showSizeChanger: false,
            }}
            columns={[
              {
                title: <Text className="text-gold">Название</Text>,
                dataIndex: 'name',
                key: 'name',
                render: (val, record) => (
                  <div>
                    <Text className="text-white text-medium">{val}</Text>
                    {record.category && (
                      <Tag className="tag-category tag-category-table">{record.category}</Tag>
                    )}
                  </div>
                ),
              },
              {
                title: <Text className="text-gold">Цена</Text>,
                dataIndex: 'price',
                key: 'price',
                render: (val) => <Text className="text-gold-bold">{formatCurrency(val)}</Text>,
              },
              {
                title: <Text className="text-gold">Длит.</Text>,
                dataIndex: 'duration',
                key: 'duration',
                render: (val) => <Text className="text-titanium">~{val} мин</Text>,
              },
              {
                title: <Text className="text-gold">Материалы</Text>,
                dataIndex: 'material_cost',
                key: 'material_cost',
                render: (val) => (
                  <Text className="text-titanium">{val ? formatCurrency(val) : '—'}</Text>
                ),
              },
              {
                title: <Text className="text-gold">Себестоимость</Text>,
                dataIndex: 'cost_price',
                key: 'cost_price',
                render: (val, record) => (
                  <Text className="text-titanium">
                    {formatCurrency(val ?? record.material_cost ?? 0)}
                  </Text>
                ),
              },
              {
                title: <Text className="text-gold">Маржа</Text>,
                key: 'margin',
                render: (_, record) => {
                  const price = Number(record.price) || 0;
                  const cost = Number(record.cost_price ?? record.material_cost) || 0;
                  const m = price > 0 ? ((price - cost) / price) * 100 : 0;
                  return (
                    <Text className="text-gold-bold">
                      {(record.margin_percent ?? m).toFixed(0)}%
                    </Text>
                  );
                },
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
                        onClick={(e) => {
                          e.stopPropagation();
                          openServiceModal(record);
                        }}
                        className="btn-action-gold"
                      />
                    </Tooltip>
                    <Popconfirm
                      title="Удалить услугу?"
                      onConfirm={() => handleDeleteService(record.id)}
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
                cell: (props: any) => <th {...props} className="table-header-cell" />,
              },
              body: {
                row: (props: any) => <tr {...props} className="table-body-row" />,
                cell: (props: any) => <td {...props} className="table-body-cell" />,
              },
            }}
          />
        )}
      </Spin>

      <Modal
        title={(
          <Text className="text-gold-bold">
            {editingService ? '✏️ Редактировать услугу' : '➕ Новая услуга'}
          </Text>
        )}
        open={serviceModal}
        onCancel={() => setServiceModal(false)}
        footer={null}
        className="modal-command"
      >
        <Space direction="vertical" size="middle">
          <div>
            <span className="label-field">Название *</span>
            <Input
              size="large"
              className="input-luxury"
              placeholder="Например: Полный детейлинг"
              value={serviceForm.name}
              onChange={(e) => setServiceForm((prev) => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <div>
            <span className="label-field">Описание</span>
            <TextArea
              rows={2}
              className="input-luxury"
              placeholder="Описание услуги"
              value={serviceForm.description}
              onChange={(e) => setServiceForm((prev) => ({ ...prev, description: e.target.value }))}
            />
          </div>
          <Row gutter={16}>
            <Col span={12}>
              <span className="label-field">Категория</span>
              <Input
                size="large"
                className="input-luxury"
                placeholder="Например: Мойка"
                value={serviceForm.category}
                onChange={(e) => setServiceForm((prev) => ({ ...prev, category: e.target.value }))}
              />
            </Col>
            <Col span={6}>
              <span className="label-field">Цена (₽)</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                value={serviceForm.price}
                onChange={(e) => setServiceForm((prev) => ({ ...prev, price: Number(e.target.value) }))}
              />
            </Col>
            <Col span={6}>
              <span className="label-field">Длит. (мин)</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                value={serviceForm.duration}
                onChange={(e) => setServiceForm((prev) => ({ ...prev, duration: Number(e.target.value) }))}
              />
            </Col>
          </Row>
          <div>
            <span className="label-field">Стоимость материалов (₽)</span>
            <Input
              size="large"
              type="number"
              className="input-luxury"
              value={serviceForm.material_cost}
              onChange={(e) => setServiceForm((prev) => ({ ...prev, material_cost: Number(e.target.value) }))}
            />
          </div>
          <div>
            <span className="label-field">Себестоимость (₽)</span>
            <Input
              size="large"
              type="number"
              className="input-luxury"
              value={serviceForm.cost_price}
              onChange={(e) => setServiceForm((prev) => ({ ...prev, cost_price: Number(e.target.value) }))}
            />
            {serviceForm.price > 0 && (
              <Text className="text-gold text-13 d-block" style={{ marginTop: 6 }}>
                Маржа:{' '}
                {(
                  ((serviceForm.price - (serviceForm.cost_price || 0)) / serviceForm.price) * 100
                ).toFixed(1)}
                %
              </Text>
            )}
          </div>
          <Button
            type="primary"
            size="large"
            onClick={handleSaveService}
            loading={serviceSaving}
            look="gold"
          >
            {editingService ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>
    </>
  );
}
