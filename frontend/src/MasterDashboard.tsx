import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Row, Col, Button, Tag, Space, Tabs,
  message, Modal, Input, Layout, List, Empty, Spin, Tooltip,
  Statistic,
} from 'antd';
import {
  ToolOutlined, CalendarOutlined, ClockCircleOutlined,
  CheckCircleOutlined, PlayCircleOutlined, EditOutlined,
  LogoutOutlined, ReloadOutlined, CarOutlined,
  UserOutlined, PhoneOutlined, FileTextOutlined,
  BellOutlined, HomeOutlined, BulbOutlined,
  CrownOutlined, CameraOutlined, GiftOutlined,
  SettingOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import PortfolioSection from './components/PortfolioSection';
import NotificationBell from './components/NotificationBell';
import NotificationList from './components/NotificationList';
import NotificationSettings from './components/NotificationSettings';

const { Text } = Typography;
const { TabPane } = Tabs;
const { Header, Content, Sider } = Layout;
const { TextArea } = Input;

/* ============================================================
   TYPES
   ============================================================ */
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

/* ============================================================
   API
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

/* ---------- sidebar items ---------- */
const sidebarItems = [
  { key: 'overview', icon: <HomeOutlined />, label: 'Обзор' },
  { key: 'tasks', icon: <ToolOutlined />, label: 'Задания' },
  { key: 'profile', icon: <UserOutlined />, label: 'Профиль' },
  { key: 'notifications', icon: <BellOutlined />, label: 'Уведомления' },
];

/* ---------- bottom nav items ---------- */
const bottomNavItems = [
  { key: 'overview', icon: <HomeOutlined />, label: 'Главная' },
  { key: 'tasks', icon: <ToolOutlined />, label: 'Задания' },
  { key: 'profile', icon: <UserOutlined />, label: 'Профиль' },
  { key: 'notifications', icon: <BellOutlined />, label: 'Уведом.' },
];

/* ============================================================
   COMPONENT: MasterDashboard
   ============================================================ */
interface MasterDashboardProps {
  user: { id: number; phone: string; full_name: string; role: string };
  onLogout: () => void;
}

export default function MasterDashboard({ user, onLogout }: MasterDashboardProps) {
  const [activeSection, setActiveSection] = useState('overview');

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);

  const [notesModal, setNotesModal] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [notesText, setNotesText] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);

  const [actionLoading, setActionLoading] = useState<number | null>(null);

  // Services for portfolio upload
  const [masterServices, setMasterServices] = useState<{ id: number; name: string }[]>([]);

  const fetchMasterServices = async () => {
    try {
      const data = await apiFetch<{items: { id: number; name: string }[]; total: number}>('/api/services?skip=0&limit=100');
      setMasterServices(data.items);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchAppointments();
  }, []);

  // Load services when Profile tab opens
  useEffect(() => {
    if (activeSection === 'profile') {
      fetchMasterServices();
    }
  }, [activeSection]);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const data = await apiFetch<{items: Appointment[]; total: number}>('/api/masters/me/appointments?skip=0&limit=200');
      setAppointments(data.items);
    } catch (e: any) {
      message.error(e.message || 'Ошибка загрузки записей');
    }
    setLoading(false);
  };

  const handleChangeStatus = async (appt: Appointment, newStatus: string) => {
    setActionLoading(appt.id);
    try {
      await apiFetch(`/api/masters/me/appointments/${appt.id}/status`, {
        method: 'PUT',
        body: JSON.stringify({ status: newStatus }),
      });
      message.success('✅ Статус обновлён');
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления статуса');
    }
    setActionLoading(null);
  };

  const openNotesModal = (appt: Appointment) => {
    setSelectedAppt(appt);
    setNotesText(appt.master_brief || '');
    setNotesModal(true);
  };

  const handleSaveNotes = async () => {
    if (!selectedAppt) return;
    setNotesSaving(true);
    try {
      await apiFetch(`/api/masters/me/appointments/${selectedAppt.id}/notes`, {
        method: 'PUT',
        body: JSON.stringify({ master_brief: notesText }),
      });
      message.success('✅ Заметка сохранена');
      setNotesModal(false);
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения заметки');
    }
    setNotesSaving(false);
  };

  /* ---------- Grouping ---------- */
  const activeAppointments = appointments.filter(
    a => a.status === 'pending' || a.status === 'confirmed' || a.status === 'in_progress'
  );
  const completedAppointments = appointments.filter(
    a => a.status === 'completed'
  );

  const formatCurrency = (val: number) => `${val.toLocaleString()} ₽`;

  /* ============================================================
     RENDER: Overview
     ============================================================ */
  const renderOverview = () => {
    const firstCar = appointments.length > 0 && appointments[0].car
      ? appointments[0].car
      : null;

    const quickActions = [
      { icon: <ToolOutlined />, label: 'Мои задания', key: 'tasks' },
      { icon: <UserOutlined />, label: 'Профиль', key: 'profile' },
      { icon: <CameraOutlined />, label: 'Портфолио', key: 'profile' },
      { icon: <CrownOutlined />, label: 'Достижения', key: 'profile' },
    ];

    const aiServiceChips = ['Мойка', 'Полировка', 'Керамика', 'Химчистка'];

    return (
      <Row gutter={[16, 16]}>
        <Col xs={24} md={16}>
          {/* Карточка авто клиента */}
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <Card className="card-luxury client-car-card">
              {firstCar ? (
                <>
                  <Row justify="space-between" align="top">
                    <Col>
                      <Text className="text-white car-title">
                        {firstCar.make} {firstCar.model}
                      </Text>
                      <div style={{ marginTop: 2 }}>
                        <Text className="text-titanium car-subtitle">
                          {firstCar.license_plate ? ` · ${firstCar.license_plate}` : ''}
                        </Text>
                      </div>
                      <div style={{ marginTop: 8 }}>
                        <Text className="car-status">✔ Автомобиль клиента</Text>
                      </div>
                    </Col>
                    <Col>
                      <Button
                        size="small"
                        className="btn-gold-secondary"
                        onClick={() => setActiveSection('tasks')}
                        style={{ width: 'auto', height: 32, fontSize: 12 }}
                      >К заданию</Button>
                    </Col>
                  </Row>
                  {/* Следующее задание */}
                  {activeAppointments.length > 0 && (
                    <>
                      <Divider className="divider-dim" />
                      <div>
                        <Text className="text-titanium car-service-label">ТЕКУЩЕЕ ЗАДАНИЕ</Text>
                        <div className="flex-space-between" style={{ marginTop: 6 }}>
                          <div>
                            <Text className="text-white car-service-date">
                              {activeAppointments[0].service_name || `Услуга #${activeAppointments[0].service_id}`}
                            </Text>
                            <Text className="text-titanium d-block car-service-name">
                              <ClockCircleOutlined /> {dayjs(activeAppointments[0].start_time).format('DD.MM HH:mm')}
                            </Text>
                          </div>
                          <Tag color={STATUS_COLORS[activeAppointments[0].status]} className="tag-status">
                            {STATUS_LABELS[activeAppointments[0].status]}
                          </Tag>
                        </div>
                      </div>
                    </>
                  )}
                </>
              ) : (
                <div className="text-center">
                  <ToolOutlined className="text-gold" style={{ fontSize: 40 }} />
                  <Text className="text-titanium d-block text-13" style={{ marginTop: 8 }}>
                    Нет активных заданий
                  </Text>
                </div>
              )}
            </Card>
          </motion.div>

          {/* Кнопка быстрого действия (только моб) */}
          <div className="d-mobile-only" style={{ marginTop: 12 }}>
            <Button
              type="primary"
              size="large"
              className="btn-gold"
              onClick={() => setActiveSection('tasks')}
            >Мои задания</Button>
          </div>

          {/* AI Детейлер */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.15 }}
            style={{ marginTop: 20 }}
          >
            <Card className="card-luxury">
              <Row align="middle" style={{ marginBottom: 12 }}>
                <Col flex="auto">
                  <Text className="title-gold text-16">🤖 AI ДЕТЕЙЛЕР</Text>
                  <Text className="text-titanium d-block text-13">
                    Что хотите сделать с автомобилем?
                  </Text>
                </Col>
                <Col>
                  <BulbOutlined className="text-gold" style={{ fontSize: 28 }} />
                </Col>
              </Row>
              <div className="ai-chips">
                {aiServiceChips.map((chip) => (
                  <Button
                    key={chip}
                    className="btn-gold-secondary"
                    onClick={() => {}}
                  >{chip}</Button>
                ))}
              </div>
            </Card>
          </motion.div>

          {/* Быстрые действия */}
          <motion.div
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ duration: 0.3, delay: 0.2 }}
            style={{ marginTop: 16 }}
          >
            <Row gutter={[12, 12]}>
              {quickActions.map((action) => (
                <Col xs={12} key={action.key}>
                  <Card
                    className="card-luxury quick-action-card"
                    hoverable
                    onClick={() => setActiveSection(action.key)}
                    styles={{ body: { padding: '16px 8px' } }}
                  >
                    <span className="quick-action-icon text-gold">{action.icon}</span>
                    <span className="quick-action-label text-white d-block">{action.label}</span>
                  </Card>
                </Col>
              ))}
            </Row>
          </motion.div>
        </Col>

        {/* Боковая панель (десктоп) */}
        <Col xs={0} md={8}>
          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.25 }}
          >
            <div className="analytics-section">
              <Row align="middle" style={{ marginBottom: 16 }}>
                <Col flex="auto">
                  <Text className="text-white analytics-title">📊 Статистика</Text>
                </Col>
              </Row>
              <div className="mb-12">
                <Text className="text-titanium text-13">Активные задания</Text>
                <div style={{ marginTop: 4 }}>
                  <Text className="stat-value-gold">{activeAppointments.length}</Text>
                </div>
              </div>
              <div className="mb-12">
                <Text className="text-titanium text-13">Выполнено сегодня</Text>
                <div style={{ marginTop: 4 }}>
                  <Text className="stat-value-green">
                    {completedAppointments.filter(a => dayjs(a.start_time).isSame(dayjs(), 'day')).length}
                  </Text>
                </div>
              </div>
              <div>
                <Text className="text-titanium text-13">Всего работ</Text>
                <div style={{ marginTop: 4 }}>
                  <Text className="stat-value-white">{appointments.length}</Text>
                </div>
              </div>
            </div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, x: 10 }}
            animate={{ opacity: 1, x: 0 }}
            transition={{ duration: 0.3, delay: 0.3 }}
          >
            <Button
              type="primary"
              size="large"
              className="btn-gold"
              onClick={() => setActiveSection('tasks')}
              style={{ height: 52, fontSize: 16 }}
            >Мои задания</Button>
          </motion.div>
        </Col>
      </Row>
    );
  };

  /* ============================================================
     RENDER: Tasks tab
     ============================================================ */
  const renderTasks = () => (
    <Spin spinning={loading}>
      {/* Stats bar */}
      <Row gutter={[16, 16]} style={{ marginBottom: 24 }}>
        <Col xs={12} sm={6}>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
            <Card className="card-luxury text-center" styles={{ body: { textAlign: 'center' } }}>
              <Statistic
                title={<Text className="text-titanium text-12">Активные</Text>}
                value={activeAppointments.length}
                valueStyle={{ color: '#C8A977', fontSize: 28, fontWeight: 700 }}
              />
            </Card>
          </motion.div>
        </Col>
        <Col xs={12} sm={6}>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 }}>
            <Card className="card-luxury text-center" styles={{ body: { textAlign: 'center' } }}>
              <Statistic
                title={<Text className="text-titanium text-12">Выполнено сегодня</Text>}
                value={completedAppointments.filter(a => dayjs(a.start_time).isSame(dayjs(), 'day')).length}
                valueStyle={{ color: '#4ECB71', fontSize: 28, fontWeight: 700 }}
              />
            </Card>
          </motion.div>
        </Col>
        <Col xs={12} sm={6}>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}>
            <Card className="card-luxury text-center" styles={{ body: { textAlign: 'center' } }}>
              <Statistic
                title={<Text className="text-titanium text-12">Всего заданий</Text>}
                value={appointments.length}
                valueStyle={{ color: '#FFFFFF', fontSize: 28, fontWeight: 700 }}
              />
            </Card>
          </motion.div>
        </Col>
        <Col xs={12} sm={6}>
          <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.15 }}>
            <Card className="card-luxury text-center" styles={{ body: { textAlign: 'center' } }}>
              <Button
                icon={<ReloadOutlined />}
                onClick={fetchAppointments}
                type="text"
                className="btn-logout"
                style={{ marginTop: 12 }}
              >Обновить</Button>
            </Card>
          </motion.div>
        </Col>
      </Row>

      {appointments.length === 0 && !loading ? (
        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
          <Card className="card-luxury text-center">
            <Empty
              description={
                <Space direction="vertical" size="small">
                  <Text className="text-titanium text-16">Нет назначенных заданий</Text>
                  <Text className="text-titanium text-13">
                    Когда администратор назначит вам запись, она появится здесь
                  </Text>
                </Space>
              }
            />
          </Card>
        </motion.div>
      ) : (
        <>
          {activeAppointments.length > 0 && (
            <>
              <Text className="title-gold text-15 d-block mb-12">
                <PlayCircleOutlined /> Активные
              </Text>
              <List
                dataSource={activeAppointments}
                renderItem={(item, index) => (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.05 }}
                  >
                    <Card
                      size="small"
                      className="card-luxury"
                      style={{
                        marginBottom: 12,
                        border: item.status === 'in_progress'
                          ? '1px solid rgba(200,169,119,0.3)'
                          : undefined,
                      }}
                    >
                      <Row justify="space-between" align="middle" gutter={[12, 8]}>
                        <Col xs={24} md={14}>
                          <Space direction="vertical" size={4}>
                            <Space>
                              <Text className="text-white-bold text-15">
                                {item.service_name || `Услуга #${item.service_id}`}
                              </Text>
                              <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                                {STATUS_LABELS[item.status]}
                              </Tag>
                            </Space>
                            <Text className="text-titanium text-13">
                              <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                              {' — '}{dayjs(item.end_time).format('HH:mm')}
                            </Text>
                            {item.client && (
                              <Text className="text-titanium text-13">
                                <UserOutlined /> {item.client.full_name}
                                {' '}<PhoneOutlined /> {item.client.phone}
                              </Text>
                            )}
                            {item.car && (
                              <Text className="text-titanium text-13">
                                <CarOutlined /> {item.car.make} {item.car.model}
                                {item.car.license_plate ? ` (${item.car.license_plate})` : ''}
                              </Text>
                            )}
                            {item.client_notes && (
                              <Text className="text-titanium text-12 opacity-70">
                                <FileTextOutlined /> Клиент: {item.client_notes}
                              </Text>
                            )}
                            {item.master_brief && (
                              <Text className="text-gold text-12">
                                📋 Заметка: {item.master_brief}
                              </Text>
                            )}
                          </Space>
                        </Col>
                        <Col xs={24} md={10}>
                          <Space direction="vertical" size="small" className="w-full">
                            <Text className="text-gold-bold text-16 d-block text-right">
                              {formatCurrency(item.total_price)}
                            </Text>
                            <Space className="w-full" style={{ justifyContent: 'flex-end' }} wrap>
                              {item.status === 'confirmed' && (
                                <Button
                                  size="small"
                                  icon={<PlayCircleOutlined />}
                                  loading={actionLoading === item.id}
                                  onClick={() => handleChangeStatus(item, 'in_progress')}
                                  className="btn-gold-secondary"
                                  style={{ width: 'auto', height: 32, fontSize: 12 }}
                                >Взять в работу</Button>
                              )}
                              {item.status === 'in_progress' && (
                                <Button
                                  size="small"
                                  icon={<CheckCircleOutlined />}
                                  loading={actionLoading === item.id}
                                  onClick={() => handleChangeStatus(item, 'completed')}
                                  style={{
                                    width: 'auto', height: 32, fontSize: 12,
                                    backgroundColor: '#0F5D46', border: 'none',
                                    color: '#FFFFFF', borderRadius: 10,
                                  }}
                                >Завершить</Button>
                              )}
                              <Tooltip title="Заметка мастера">
                                <Button
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={() => openNotesModal(item)}
                                  className="btn-gold-secondary"
                                  style={{ width: 'auto', height: 32, fontSize: 12 }}
                                >Заметка</Button>
                              </Tooltip>
                            </Space>
                          </Space>
                        </Col>
                      </Row>
                    </Card>
                  </motion.div>
                )}
              />
            </>
          )}

          {completedAppointments.length > 0 && (
            <>
              <Text className="text-titanium text-14 d-block mb-12" style={{ marginTop: 24 }}>
                <CheckCircleOutlined style={{ color: '#4ECB71' }} /> Выполненные
              </Text>
              <List
                dataSource={completedAppointments}
                renderItem={(item, index) => (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    transition={{ duration: 0.3, delay: index * 0.03 }}
                  >
                    <Card
                      size="small"
                      className="card-luxury"
                      style={{ marginBottom: 8, opacity: 0.7 }}
                    >
                      <Row justify="space-between" align="middle" gutter={[12, 8]}>
                        <Col xs={24} md={16}>
                          <Space direction="vertical" size={2}>
                            <Space>
                              <Text className="text-white-bold text-14">
                                {item.service_name || `Услуга #${item.service_id}`}
                              </Text>
                              <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                                {STATUS_LABELS[item.status]}
                              </Tag>
                            </Space>
                            <Text className="text-titanium text-12">
                              <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                              {item.client && <> · {item.client.full_name}</>}
                              {item.car && <> · {item.car.make} {item.car.model}</>}
                            </Text>
                          </Space>
                        </Col>
                        <Col xs={24} md={8} className="text-right">
                          <Text className="text-gold-bold text-14">
                            {formatCurrency(item.total_price)}
                          </Text>
                        </Col>
                      </Row>
                    </Card>
                  </motion.div>
                )}
              />
            </>
          )}
        </>
      )}
    </Spin>
  );

  /* ============================================================
     RENDER: Profile
     ============================================================ */
  const renderProfile = () => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
      <Card className="card-luxury" style={{ maxWidth: 480, margin: '0 auto' }}>
        <div style={{
          width: 72, height: 72, borderRadius: '50%', backgroundColor: '#232A33',
          margin: '0 auto 16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
          border: '2px solid #C8A977', fontSize: 32,
        }}>🔧</div>
        <Text className="text-white text-22 d-block text-center" style={{ fontSize: 22, fontWeight: 700 }}>
          {user.full_name}
        </Text>
        <Text className="title-gold text-15 d-block text-center" style={{ marginBottom: 4 }}>
          Мастер-детейлер
        </Text>
        <Text className="text-titanium text-13 d-block text-center mb-20">
          <PhoneOutlined /> {user.phone}
        </Text>

        <div style={{ backgroundColor: '#1A1E23', borderRadius: 14, padding: 16, textAlign: 'center' }}>
          <Text className="text-titanium text-13 d-block mb-4">
            Выполнено работ
          </Text>
          <Text className="stat-value-green">
            {completedAppointments.length}
          </Text>
        </div>
      </Card>

      <div className="mt-4">
        <PortfolioSection masterId={user.id} allServices={masterServices} />
      </div>
    </motion.div>
  );

  /* ============================================================
     RENDER: Notifications
     ============================================================ */
  const renderNotifications = () => (
    <Tabs size="small" tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: 16 }}>
      <TabPane tab="📋 Список" key="list">
        <NotificationList title="Мои уведомления" />
      </TabPane>
      <TabPane tab="⚙️ Настройки" key="settings">
        <NotificationSettings />
      </TabPane>
    </Tabs>
  );

  /* ============================================================
     RENDER: Content router
     ============================================================ */
  const renderContent = () => {
    switch (activeSection) {
      case 'overview': return renderOverview();
      case 'tasks': return renderTasks();
      case 'profile': return renderProfile();
      case 'notifications': return renderNotifications();
      default: return renderOverview();
    }
  };

  /* ============================================================
     Divider component (inline to avoid import)
     ============================================================ */
  const Divider = ({ className }: { className?: string }) => (
    <div className={className} style={{ height: 1, backgroundColor: 'rgba(255,255,255,0.06)', margin: '12px 0' }} />
  );

  /* ============================================================
     MAIN RENDER
     ============================================================ */
  return (
    <Layout className="client-layout">
      {/* Мобильный хедер */}
      <Header className="header-mobile">
        <Text className="title-gold">CAR DETAİLİNG AI</Text>
        <Text className="text-titanium">ВАШ ДЕТЕЙЛИНГ</Text>
      </Header>

      {/* Десктоп хедер */}
      <Header className="header-desktop">
        <Space>
          <ToolOutlined className="text-gold icon-command" />
          <Text className="title-gold title-command">CarDetailing AI</Text>
          <Tag color="gold" className="tag-category">Мастер</Tag>
        </Space>
        <Space size="middle">
          <Text className="text-titanium">🔧 {user.full_name}</Text>
          <NotificationBell />
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} className="btn-logout">
            Выйти
          </Button>
        </Space>
      </Header>

      <Layout>
        {/* Сайдбар (десктоп) */}
        <Sider
          className="sidebar"
          breakpoint="md"
          collapsedWidth={0}
          width={220}
          trigger={null}
        >
          {sidebarItems.map(item => (
            <button
              key={item.key}
              className={`sidebar-item${activeSection === item.key ? ' active' : ''}`}
              onClick={() => setActiveSection(item.key)}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </Sider>

        {/* Контент */}
        <Content className="client-content">
          {renderContent()}
        </Content>
      </Layout>

      {/* Нижняя навигация (моб) */}
      <div className="bottom-nav">
        {bottomNavItems.map(item => (
          <button
            key={item.key}
            className={`bottom-nav-item${activeSection === item.key ? ' active' : ''}`}
            onClick={() => setActiveSection(item.key)}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        ))}
      </div>

      {/* ===== NOTES MODAL ===== */}
      <Modal
        title={<span className="text-white">📋 Заметка мастера</span>}
        open={notesModal}
        onCancel={() => setNotesModal(false)}
        footer={null}
        className="modal-command"
      >
        {selectedAppt && (
          <Space direction="vertical" size="middle" className="w-full">
            <div>
              <Text className="text-titanium text-13 d-block mb-4">
                Услуга: <Text className="text-white">{selectedAppt.service_name}</Text>
              </Text>
              {selectedAppt.client && (
                <Text className="text-titanium text-13 d-block mb-4">
                  Клиент: <Text className="text-white">{selectedAppt.client.full_name}</Text>
                </Text>
              )}
              {selectedAppt.car && (
                <Text className="text-titanium text-13 d-block mb-12">
                  Авто: <Text className="text-white">{selectedAppt.car.make} {selectedAppt.car.model}</Text>
                </Text>
              )}
            </div>
            <div>
              <Text className="text-titanium d-block mb-6">Что сделано / примечания</Text>
              <TextArea
                rows={4}
                className="input-luxury"
                placeholder="Опишите выполненную работу, особенности, расходники..."
                value={notesText}
                onChange={(e) => setNotesText(e.target.value)}
              />
            </div>
            <Button
              type="primary"
              size="large"
              className="btn-gold"
              onClick={handleSaveNotes}
              loading={notesSaving}
            >Сохранить заметку</Button>
          </Space>
        )}
      </Modal>
    </Layout>
  );
}
