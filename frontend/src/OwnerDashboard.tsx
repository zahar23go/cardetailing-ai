import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Row, Col, Statistic, Table, Button, Tag, Space, Tabs,
  message, Modal, Select, Input, Popconfirm, Badge, Layout, List,
  Empty, Spin, Tooltip,
} from 'antd';
import {
  CrownOutlined, ToolOutlined,
  CalendarOutlined, DollarOutlined, ClockCircleOutlined,
  TeamOutlined, DeleteOutlined, EditOutlined,
  PlusOutlined, LogoutOutlined, ReloadOutlined, PhoneOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;
const { TabPane } = Tabs;
const { Header, Content } = Layout;
const { Option } = Select;
const { TextArea } = Input;

/* ============================================================
   TYPES
   ============================================================ */
interface User {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
  created_at?: string;
}

interface Service {
  id: number;
  name: string;
  description: string;
  category?: string;
  price: number;
  duration: number;
  material_cost?: number;
  is_active?: boolean;
}

interface Appointment {
  id: number;
  client_id: number;
  master_id: number | null;
  car_id: number;
  service_id: number;
  start_time: string;
  end_time: string;
  status: string;
  total_price: number;
  discount_applied: number;
  client_notes: string | null;
  master_brief: string | null;
  service_name: string | null;
  client?: { id: number; full_name: string; phone: string };
  master?: { id: number; full_name: string };
  car?: { id: number; make: string; model: string; license_plate: string };
  service?: { id: number; name: string; price: number };
}

interface KpiData {
  total_clients: number;
  total_masters: number;
  today_appointments: number;
  today_revenue: number;
  month_revenue: number;
  pending_appointments: number;
  completed_month: number;
}

/* ============================================================
   API HELPERS
   ============================================================ */
const API_BASE = '';

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

/* ============================================================
   CONSTANTS
   ============================================================ */
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

const ROLE_LABELS: Record<string, string> = {
  client: '👤 Клиент',
  master: '🔧 Мастер',
  admin: '👑 Владелец',
  super_admin: '⭐ Супер-админ',
};

/* ============================================================
   COMPONENT: OwnerDashboard
   ============================================================ */
interface OwnerDashboardProps {
  user: { id: number; phone: string; full_name: string; role: string };
  onLogout: () => void;
}

export default function OwnerDashboard({ user, onLogout }: OwnerDashboardProps) {
  const [activeTab, setActiveTab] = useState('overview');

  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [apptsLoading, setApptsLoading] = useState(false);

  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);

  const [users, setUsers] = useState<User[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);

  // Modals
  const [serviceModal, setServiceModal] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [serviceForm, setServiceForm] = useState({
    name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0,
  });
  const [serviceSaving, setServiceSaving] = useState(false);

  const [apptStatusModal, setApptStatusModal] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [apptNewStatus, setApptNewStatus] = useState<string>('');
  const [apptMasterId, setApptMasterId] = useState<number | undefined>(undefined);
  const [apptBrief, setApptBrief] = useState('');

  const [userRoleModal, setUserRoleModal] = useState(false);
  const [selectedUser, setSelectedUser] = useState<User | null>(null);
  const [userNewRole, setUserNewRole] = useState<string>('');

  // Client detail modal
  const [clientModal, setClientModal] = useState(false);
  const [clientDetail, setClientDetail] = useState<any>(null);
  const [clientLoading, setClientLoading] = useState(false);

  // Fetch all data
  useEffect(() => {
    fetchKpi();
    fetchAppointments();
    fetchServices();
    fetchUsers();
  }, []);

  const fetchKpi = async () => {
    setKpiLoading(true);
    try {
      const data = await apiFetch<KpiData>('/api/analytics/kpi');
      setKpi(data);
    } catch { /* ignore */ }
    setKpiLoading(false);
  };

  const fetchAppointments = async () => {
    setApptsLoading(true);
    try {
      const data = await apiFetch<Appointment[]>('/api/appointments');
      setAppointments(data);
    } catch { message.error('Ошибка загрузки записей'); }
    setApptsLoading(false);
  };

  const fetchServices = async () => {
    setServicesLoading(true);
    try {
      const data = await apiFetch<Service[]>('/api/services');
      setServices(data);
    } catch { message.error('Ошибка загрузки услуг'); }
    setServicesLoading(false);
  };

  const fetchUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await apiFetch<User[]>('/api/users');
      setUsers(data);
    } catch { message.error('Ошибка загрузки пользователей'); }
    setUsersLoading(false);
  };

  /* ---------- Service CRUD ---------- */
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
      });
    } else {
      setEditingService(null);
      setServiceForm({ name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0 });
    }
    setServiceModal(true);
  };

  const handleSaveService = async () => {
    if (!serviceForm.name.trim()) { message.warning('Укажите название услуги'); return; }
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

  /* ---------- User deletion ---------- */
  const handleDeleteUser = async (userId: number, userName: string) => {
    try {
      await apiFetch(`/api/users/${userId}`, { method: 'DELETE' });
      message.success(`✅ Пользователь «${userName}» удалён`);
      fetchUsers();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления пользователя');
    }
  };

  /* ---------- Appointment actions ---------- */
  const openApptStatusModal = (appt: Appointment) => {
    setSelectedAppt(appt);
    setApptNewStatus(appt.status);
    setApptMasterId(appt.master_id || undefined);
    setApptBrief(appt.master_brief || '');
    setApptStatusModal(true);
  };

  const handleUpdateAppointment = async () => {
    if (!selectedAppt) return;
    try {
      const body: any = {};
      if (apptNewStatus !== selectedAppt.status) body.status = apptNewStatus;
      if (apptMasterId !== selectedAppt.master_id) body.master_id = apptMasterId;
      if (apptBrief !== (selectedAppt.master_brief || '')) body.master_brief = apptBrief;
      if (Object.keys(body).length === 0) { setApptStatusModal(false); return; }

      await apiFetch(`/api/appointments/${selectedAppt.id}`, {
        method: 'PUT',
        body: JSON.stringify(body),
      });
      message.success('✅ Статус обновлён');
      setApptStatusModal(false);
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления');
    }
  };

  /* ---------- User role ---------- */
  const openUserRoleModal = (u: User) => {
    setSelectedUser(u);
    setUserNewRole(u.role);
    setUserRoleModal(true);
  };

  const handleUpdateRole = async () => {
    if (!selectedUser || userNewRole === selectedUser.role) {
      setUserRoleModal(false);
      return;
    }
    try {
      await apiFetch(`/api/users/${selectedUser.id}/role`, {
        method: 'PUT',
        body: JSON.stringify({ role: userNewRole }),
      });
      message.success('✅ Роль обновлена');
      setUserRoleModal(false);
      fetchUsers();
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления роли');
    }
  };

  /* ---------- Client detail ---------- */
  const openClientDetail = async (clientId: number) => {
    setClientLoading(true);
    setClientModal(true);
    try {
      const data = await apiFetch(`/api/users/${clientId}`);
      setClientDetail(data);
    } catch {
      message.error('Ошибка загрузки данных клиента');
      setClientModal(false);
    }
    setClientLoading(false);
  };

  /* ============================================================
     RENDER
     ============================================================ */
  const formatCurrency = (val: number) => `${val.toLocaleString()} ₽`;

  return (
    <Layout>
      {/* HEADER */}
      <Header className="header-command">
        <Space>
          <CrownOutlined className="text-gold icon-command" />
          <Text className="title-gold title-command">
            CarDetailing AI
          </Text>
          <Tag color="gold" className="tag-category">
            Command Center
          </Tag>
        </Space>
        <Space size="middle">
          <Text className="text-titanium">👑 {user.full_name}</Text>
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} className="btn-logout">
            Выйти
          </Button>
        </Space>
      </Header>

      {/* CONTENT */}
      <Content className="content-command">
        <Tabs
          activeKey={activeTab}
          onChange={(key) => { setActiveTab(key); }}
          size="large"
        >
          {/* ===== TAB 1: OVERVIEW ===== */}
          <TabPane tab={<span><CrownOutlined /> Обзор</span>} key="overview">
            <Spin spinning={kpiLoading}>
              <Row gutter={[16, 16]}>
                <Col xs={12} sm={6}>
                  <motion.div className="animate-fade-in-up">
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Клиенты</Text>}
                        value={kpi?.total_clients || 0}
                        prefix={<TeamOutlined className="text-gold" />}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div className="animate-fade-in-up" style={{ animationDelay: '0.05s' }}>
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Мастера</Text>}
                        value={kpi?.total_masters || 0}
                        prefix={<ToolOutlined className="text-gold" />}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div className="animate-fade-in-up" style={{ animationDelay: '0.1s' }}>
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Записи сегодня</Text>}
                        value={kpi?.today_appointments || 0}
                        prefix={<CalendarOutlined className="text-gold" />}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div className="animate-fade-in-up" style={{ animationDelay: '0.15s' }}>
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Ожидают</Text>}
                        value={kpi?.pending_appointments || 0}
                        prefix={<Badge status="processing" />}
                        valueStyle={{ color: '#C8A977', fontSize: '28px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
              </Row>
              <Row gutter={[16, 16]} className="mt-4">
                <Col xs={24} sm={12}>
                  <motion.div className="animate-fade-in-up" style={{ animationDelay: '0.2s' }}>
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Выручка сегодня</Text>}
                        value={kpi?.today_revenue || 0}
                        prefix={<DollarOutlined className="icon-revenue-green" />}
                        suffix={<Text className="text-titanium">₽</Text>}
                        valueStyle={{ color: '#4ECB71', fontSize: '32px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={24} sm={12}>
                  <motion.div className="animate-fade-in-up" style={{ animationDelay: '0.25s' }}>
                    <Card className="card-kpi">
                      <Statistic
                        title={<Text className="text-titanium">Выручка за месяц</Text>}
                        value={kpi?.month_revenue || 0}
                        prefix={<DollarOutlined className="text-gold" />}
                        suffix={<Text className="text-titanium">₽</Text>}
                        valueStyle={{ color: '#C8A977', fontSize: '32px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
              </Row>
              <Row className="mt-4">
                <Col span={24}>
                  <Button icon={<ReloadOutlined />} onClick={fetchKpi} type="text" className="btn-logout">
                    Обновить
                  </Button>
                </Col>
              </Row>
            </Spin>
          </TabPane>

          {/* ===== TAB 2: APPOINTMENTS ===== */}
          <TabPane tab={<span><CalendarOutlined /> Записи</span>} key="appointments">
            <Spin spinning={apptsLoading}>
              <div className="toolbar-row">
                <Text className="text-titanium">Всего: {appointments.length}</Text>
                <Button size="small" icon={<ReloadOutlined />} onClick={fetchAppointments} type="text" className="btn-logout" />
              </div>
              {appointments.length === 0 && !apptsLoading ? (
                <Empty description={<Text className="text-titanium">Нет записей</Text>} />
              ) : (
                <List
                  dataSource={appointments}
                  renderItem={(item) => (
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Card
                        size="small"
                        className="card-appointment"
                        onClick={() => openApptStatusModal(item)}
                        hoverable
                      >
                        <Row justify="space-between" align="middle">
                          <Col xs={14}>
                            <Space direction="vertical" size={2}>
                              <Space>
                                <Text className="text-white-bold">
                                  {item.service_name || `Услуга #${item.service_id}`}
                                </Text>
                                <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                                  {STATUS_LABELS[item.status]}
                                </Tag>
                              </Space>
                              <Text className="text-small">
                                <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                                {item.client && <> · 👤 {item.client.full_name}</>}
                              </Text>
                              {item.car && (
                                <Text className="text-small">
                                  🚗 {item.car.make} {item.car.model} {item.car.license_plate ? `(${item.car.license_plate})` : ''}
                                </Text>
                              )}
                            </Space>
                          </Col>
                          <Col xs={10} className="text-right">
                            <Text className="text-gold-bold text-16">
                              {formatCurrency(item.total_price)}
                            </Text>
                            {item.master && (
                              <div>
                                <Text className="text-small">🔧 {item.master.full_name}</Text>
                              </div>
                            )}
                          </Col>
                        </Row>
                      </Card>
                    </motion.div>
                  )}
                />
              )}
            </Spin>
          </TabPane>

          {/* ===== TAB 3: SERVICES ===== */}
          <TabPane tab={<span><ToolOutlined /> Услуги</span>} key="services">
            <Spin spinning={servicesLoading}>
              <div className="toolbar-right">
                <Button
                  type="primary"
                  icon={<PlusOutlined />}
                  onClick={() => openServiceModal()}
                >Добавить услугу</Button>
              </div>
              {services.length === 0 && !servicesLoading ? (
                <Empty description={<Text className="text-titanium">Нет услуг</Text>} />
              ) : (
                <Table
                  dataSource={services}
                  rowKey="id"
                  pagination={false}
                  columns={[
                    {
                      title: <Text className="text-titanium">Название</Text>,
                      dataIndex: 'name',
                      key: 'name',
                      render: (val, record) => (
                        <div>
                          <Text className="text-white text-medium">{val}</Text>
                          {record.category && (
                            <Tag className="tag-category tag-category-table">
                              {record.category}
                            </Tag>
                          )}
                        </div>
                      ),
                    },
                    {
                      title: <Text className="text-titanium">Цена</Text>,
                      dataIndex: 'price',
                      key: 'price',
                      render: (val) => <Text className="text-gold-bold">{formatCurrency(val)}</Text>,
                    },
                    {
                      title: <Text className="text-titanium">Длит.</Text>,
                      dataIndex: 'duration',
                      key: 'duration',
                      render: (val) => <Text className="text-titanium">~{val} мин</Text>,
                    },
                    {
                      title: <Text className="text-titanium">Материалы</Text>,
                      dataIndex: 'material_cost',
                      key: 'material_cost',
                      render: (val) => <Text className="text-titanium">{val ? formatCurrency(val) : '—'}</Text>,
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
                              onClick={(e) => { e.stopPropagation(); openServiceModal(record); }}
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
                              <Button
                                size="small"
                                icon={<DeleteOutlined />}
                                className="btn-action-danger"
                              />
                            </Tooltip>
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                  components={{
                    header: {
                      cell: (props: any) => (
                        <th {...props} className="table-header-cell" />
                      ),
                    },
                    body: {
                      row: (props: any) => (
                        <tr {...props} className="table-body-row" />
                      ),
                      cell: (props: any) => (
                        <td {...props} className="table-body-cell" />
                      ),
                    },
                  }}
                />
              )}
            </Spin>
          </TabPane>

          {/* ===== TAB 4: USERS ===== */}
          <TabPane tab={<span><TeamOutlined /> Пользователи</span>} key="users">
            <Spin spinning={usersLoading}>
              {users.length === 0 && !usersLoading ? (
                <Empty description={<Text className="text-titanium">Нет пользователей</Text>} />
              ) : (
                <Table
                  dataSource={users}
                  rowKey="id"
                  pagination={{ pageSize: 20, size: 'small' }}
                  columns={[
                    {
                      title: <Text className="text-titanium">Имя</Text>,
                      dataIndex: 'full_name',
                      key: 'full_name',
                      render: (val) => <Text className="text-white text-medium">{val}</Text>,
                    },
                    {
                      title: <Text className="text-titanium">Телефон</Text>,
                      dataIndex: 'phone',
                      key: 'phone',
                      render: (val) => <Text className="text-titanium"><PhoneOutlined /> {val}</Text>,
                    },
                    {
                      title: <Text className="text-titanium">Роль</Text>,
                      dataIndex: 'role',
                      key: 'role',
                      render: (val, record) => (
                        <Button
                          size="small"
                          onClick={() => openUserRoleModal(record)}
                          className="btn-role-pill"
                          data-role={val}
                        >
                          {ROLE_LABELS[val] || val}
                        </Button>
                      ),
                    },
                    {
                      title: <Text className="text-titanium">Дата рег.</Text>,
                      dataIndex: 'created_at',
                      key: 'created_at',
                      render: (val) => <Text className="text-titanium">{val ? dayjs(val).format('DD.MM.YYYY') : '—'}</Text>,
                    },
                    {
                      title: '',
                      key: 'actions',
                      width: 140,
                      render: (_, record) => (
                        <Space size="small">
                          {record.role === 'client' && (
                            <Tooltip title="История клиента">
                              <Button
                                size="small"
                                onClick={() => openClientDetail(record.id)}
                                className="btn-action-gold"
                              >📋</Button>
                            </Tooltip>
                          )}
                          <Popconfirm
                            title={`Удалить пользователя «${record.full_name}»?`}
                            description="Будут удалены все автомобили и записи клиента."
                            onConfirm={() => handleDeleteUser(record.id, record.full_name)}
                            okText="Да, удалить"
                            cancelText="Отмена"
                            okButtonProps={{ danger: true }}
                          >
                            <Tooltip title="Удалить пользователя">
                              <Button
                                size="small"
                                icon={<DeleteOutlined />}
                                className="btn-action-danger"
                              />
                            </Tooltip>
                          </Popconfirm>
                        </Space>
                      ),
                    },
                  ]}
                  components={{
                    header: {
                      cell: (props: any) => (
                        <th {...props} className="table-header-cell" />
                      ),
                    },
                    body: {
                      row: (props: any) => (
                        <tr {...props} className="table-body-row" />
                      ),
                      cell: (props: any) => (
                        <td {...props} className="table-body-cell" />
                      ),
                    },
                  }}
                />
              )}
            </Spin>
          </TabPane>
        </Tabs>
      </Content>

      {/* ===== SERVICE MODAL ===== */}
      <Modal
        title={<Text className="text-white">{editingService ? '✏️ Редактировать услугу' : '➕ Новая услуга'}</Text>}
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
              onChange={(e) => setServiceForm(prev => ({ ...prev, name: e.target.value }))}
            />
          </div>
          <div>
            <span className="label-field">Описание</span>
            <TextArea
              rows={2}
              className="input-luxury"
              placeholder="Описание услуги"
              value={serviceForm.description}
              onChange={(e) => setServiceForm(prev => ({ ...prev, description: e.target.value }))}
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
                onChange={(e) => setServiceForm(prev => ({ ...prev, category: e.target.value }))}
              />
            </Col>
            <Col span={6}>
              <span className="label-field">Цена (₽)</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                value={serviceForm.price}
                onChange={(e) => setServiceForm(prev => ({ ...prev, price: Number(e.target.value) }))}
              />
            </Col>
            <Col span={6}>
              <span className="label-field">Длит. (мин)</span>
              <Input
                size="large"
                type="number"
                className="input-luxury"
                value={serviceForm.duration}
                onChange={(e) => setServiceForm(prev => ({ ...prev, duration: Number(e.target.value) }))}
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
              onChange={(e) => setServiceForm(prev => ({ ...prev, material_cost: Number(e.target.value) }))}
            />
          </div>
          <Button
            type="primary"
            size="large"
            onClick={handleSaveService}
            loading={serviceSaving}
            className="btn-gold"
          >{editingService ? 'Сохранить' : 'Создать'}</Button>
        </Space>
      </Modal>

      {/* ===== APPOINTMENT STATUS MODAL ===== */}
      <Modal
        title={<Text className="text-white">📅 Управление записью</Text>}
        open={apptStatusModal}
        onCancel={() => setApptStatusModal(false)}
        footer={null}
        className="modal-command"
      >
        {selectedAppt && (
          <Space direction="vertical" size="middle">
            <Card size="small" className="card-detail">
              <Space direction="vertical" size={4}>
                <Text className="text-white-bold">{selectedAppt.service_name}</Text>
                <Text className="text-small">
                  👤 {selectedAppt.client?.full_name} · 📞 {selectedAppt.client?.phone}
                </Text>
                {selectedAppt.car && (
                  <Text className="text-small">
                    🚗 {selectedAppt.car.make} {selectedAppt.car.model} ({selectedAppt.car.license_plate})
                  </Text>
                )}
                <Text className="text-small">
                  🕐 {dayjs(selectedAppt.start_time).format('DD.MM.YYYY HH:mm')} — {dayjs(selectedAppt.end_time).format('HH:mm')}
                </Text>
                <Text className="text-gold-bold text-16">
                  {formatCurrency(selectedAppt.total_price)}
                </Text>
              </Space>
            </Card>

            <div>
              <span className="label-field">Статус</span>
              <Select
                size="large"
                value={apptNewStatus}
                onChange={setApptNewStatus}
              >
                {Object.entries(STATUS_LABELS).map(([key, label]) => (
                  <Option key={key} value={key}>{label}</Option>
                ))}
              </Select>
            </div>

            <div>
              <span className="label-field">Мастер</span>
              <Select
                size="large"
                placeholder="Назначить мастера"
                value={apptMasterId}
                onChange={setApptMasterId}
                allowClear
              >
                {users.filter(u => u.role === 'master').map(m => (
                  <Option key={m.id} value={m.id}>🔧 {m.full_name}</Option>
                ))}
              </Select>
            </div>

            <div>
              <span className="label-field">Заметка мастеру</span>
              <TextArea
                rows={2}
                className="input-luxury"
                placeholder="Краткое описание задачи..."
                value={apptBrief}
                onChange={(e) => setApptBrief(e.target.value)}
              />
            </div>

            <Button
              type="primary"
              size="large"
              onClick={handleUpdateAppointment}
              className="btn-gold"
            >Сохранить</Button>
          </Space>
        )}
      </Modal>

      {/* ===== USER ROLE MODAL ===== */}
      <Modal
        title={<Text className="text-white">👤 Изменить роль</Text>}
        open={userRoleModal}
        onCancel={() => setUserRoleModal(false)}
        footer={null}
        className="modal-command"
      >
        {selectedUser && (
          <Space direction="vertical" size="middle">
            <div className="text-center">
              <Text className="text-white text-18-bold">{selectedUser.full_name}</Text>
              <Text className="text-titanium d-block">📱 {selectedUser.phone}</Text>
            </div>

            <div>
              <span className="label-field">Новая роль</span>
              <Select
                size="large"
                value={userNewRole}
                onChange={setUserNewRole}
              >
                <Option value="client">👤 Клиент</Option>
                <Option value="master">🔧 Мастер</Option>
                <Option value="admin">👑 Владелец</Option>
                {user.role === 'super_admin' && <Option value="super_admin">⭐ Супер-админ</Option>}
              </Select>
            </div>

            <Button
              type="primary"
              size="large"
              onClick={handleUpdateRole}
              className="btn-gold"
            >Сохранить</Button>
          </Space>
        )}
      </Modal>

      {/* ===== CLIENT DETAIL MODAL ===== */}
      <Modal
        title={<Text className="text-white">📋 Карточка клиента</Text>}
        open={clientModal}
        onCancel={() => { setClientModal(false); setClientDetail(null); }}
        footer={null}
        width={520}
        className="modal-command"
      >
        <Spin spinning={clientLoading}>
          {clientDetail && (
            <Space direction="vertical" size="middle">
              <Card size="small" className="card-detail">
                <Space direction="vertical" size={4}>
                  <Text className="text-white text-18-bold">{clientDetail.full_name}</Text>
                  <Text className="text-titanium">📱 {clientDetail.phone}</Text>
                  <Text className="text-titanium">📅 Регистрация: {dayjs(clientDetail.created_at).format('DD.MM.YYYY')}</Text>
                </Space>
              </Card>

              <Row gutter={16}>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">{clientDetail.appointments_count}</Text>
                    <Text className="text-titanium d-block text-12">Визитов</Text>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">
                      {formatCurrency(clientDetail.total_spent)}
                    </Text>
                    <Text className="text-titanium d-block text-12">Потрачено</Text>
                  </Card>
                </Col>
                <Col span={8}>
                  <Card size="small" className="card-detail">
                    <Text className="text-gold-bold text-24">
                      {clientDetail.last_visit ? dayjs(clientDetail.last_visit).format('DD.MM') : '—'}
                    </Text>
                    <Text className="text-titanium d-block text-12">Последний</Text>
                  </Card>
                </Col>
              </Row>

              {clientDetail.last_visit && (
                <Text className="text-small text-center d-block">
                  🕐 Последний визит: {dayjs(clientDetail.last_visit).format('DD.MM.YYYY HH:mm')}
                </Text>
              )}
            </Space>
          )}
        </Spin>
      </Modal>
    </Layout>
  );
}
