import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography,
  Card,
  Row,
  Col,
  Tag,
  Space,
  Tabs,
  message,
  Layout,
  List,
  Empty,
  Spin,
  Tooltip,
  Statistic,
} from 'antd';
import { Button, Modal, Input } from './components/ui';
import {
  ToolOutlined, CalendarOutlined, ClockCircleOutlined,
  CheckCircleOutlined, PlayCircleOutlined, EditOutlined,
  LogoutOutlined, ReloadOutlined, CarOutlined,
  UserOutlined, PhoneOutlined, FileTextOutlined,
  BellOutlined, HomeOutlined, BulbOutlined,
  CrownOutlined, CameraOutlined, GiftOutlined,
  SettingOutlined, DollarOutlined, TeamOutlined,
  StarOutlined, FileProtectOutlined, WarningOutlined,
} from '@ant-design/icons';
import { useNavigate } from 'react-router-dom';
import { AreaChart, Area, ResponsiveContainer } from 'recharts';
import { isModuleEnabled, type AppModuleName } from './modules';
import { useEnabledModules } from './ModulesContext';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import PortfolioSection from './components/PortfolioSection';
import NotificationBell from './components/NotificationBell';
import NotificationList from './components/NotificationList';
import NotificationSettings from './components/NotificationSettings';
import CloseVisitModal from './components/CloseVisitModal';

dayjs.locale('ru');

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

interface KpiSparkPoint {
  date: string;
  value: number;
}

interface MasterKpi {
  period_start: string;
  revenue: number;
  avg_check: number;
  completed_month: number;
  completed_today: number;
  unique_clients: number;
  repeat_clients: number;
  repeat_rate: number;
  tech_steps_done: number;
  tech_steps_total: number;
  tech_compliance_pct: number;
  overspend_qty: number;
  overspend_cost: number;
  overspend_pct: number;
  score: number;
  score_hint: string;
  sparkline_revenue: KpiSparkPoint[];
}

const EMPTY_KPI: MasterKpi = {
  period_start: '',
  revenue: 0,
  avg_check: 0,
  completed_month: 0,
  completed_today: 0,
  unique_clients: 0,
  repeat_clients: 0,
  repeat_rate: 0,
  tech_steps_done: 0,
  tech_steps_total: 0,
  tech_compliance_pct: 0,
  overspend_qty: 0,
  overspend_cost: 0,
  overspend_pct: 0,
  score: 0,
  score_hint: 'техкарта · расход · повтор',
  sparkline_revenue: [],
};

function MasterKpiSpark({ data }: { data?: KpiSparkPoint[] }) {
  if (!data || data.length < 2) return null;
  return (
    <div className="admin-kpi-spark">
      <ResponsiveContainer width="100%" height={36}>
        <AreaChart data={data} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
          <Area type="monotone" dataKey="value" stroke="#C8A977" fill="#C8A977" fillOpacity={0.18} strokeWidth={1.5} dot={false} />
        </AreaChart>
      </ResponsiveContainer>
    </div>
  );
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
  confirmed: 'gold',
  in_progress: 'gold',
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

/* ---------- sidebar / bottom nav ---------- */
const MASTER_NAV: { key: string; icon: React.ReactNode; label: string; short?: string; module?: AppModuleName }[] = [
  { key: 'overview', icon: <HomeOutlined />, label: 'Обзор', short: 'Главная' },
  { key: 'tasks', icon: <ToolOutlined />, label: 'Задания', module: 'appointments' },
  { key: 'portfolio', icon: <CameraOutlined />, label: 'Портфолио', module: 'photos' },
  { key: 'profile', icon: <UserOutlined />, label: 'Профиль' },
  { key: 'notifications', icon: <BellOutlined />, label: 'Уведомления', short: 'Уведом.', module: 'notifications' },
];

/* ============================================================
   COMPONENT: MasterDashboard
   ============================================================ */
interface MasterDashboardProps {
  user: { id: number; phone: string; full_name: string; role: string };
  onLogout: () => void;
  initialSection?: string;
}

export default function MasterDashboard({ user, onLogout, initialSection = 'overview' }: MasterDashboardProps) {
  const navigate = useNavigate();
  const enabled = useEnabledModules();
  const nav = MASTER_NAV.filter((item) => isModuleEnabled(enabled, item.module || 'core'));
  const [activeSection, setActiveSection] = useState(initialSection);

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [kpi, setKpi] = useState<MasterKpi>(EMPTY_KPI);
  const [loading, setLoading] = useState(false);

  const [notesModal, setNotesModal] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [notesText, setNotesText] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);

  const [actionLoading, setActionLoading] = useState<number | null>(null);
  const [closeAppt, setCloseAppt] = useState<Appointment | null>(null);

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

  useEffect(() => {
    setActiveSection(initialSection);
  }, [initialSection]);

  useEffect(() => {
    if (activeSection === 'profile' || activeSection === 'portfolio') {
      fetchMasterServices();
    }
  }, [activeSection]);

  const fetchAppointments = async () => {
    setLoading(true);
    try {
      const [data, kpiData] = await Promise.all([
        apiFetch<{ items: Appointment[]; total: number }>('/api/masters/me/appointments?skip=0&limit=200'),
        apiFetch<MasterKpi>('/api/masters/me/kpi').catch(() => null),
      ]);
      setAppointments(data.items);
      if (kpiData) setKpi(kpiData);
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

  const goSection = (key: string) => {
    setActiveSection(key);
    if (key === 'portfolio') navigate('/master/portfolio');
    else if (window.location.pathname.startsWith('/master')) navigate('/');
  };

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
      ...(isModuleEnabled(enabled, 'photos')
        ? [{ icon: <CameraOutlined />, label: 'Портфолио', key: 'portfolio' }]
        : []),
      { icon: <CrownOutlined />, label: 'Достижения', key: 'profile' },
    ];

    const aiServiceChips = ['Мойка', 'Полировка', 'Керамика', 'Химчистка'];

    return (
      <div className="master-overview">
        <Row gutter={[16, 16]} align="stretch" className="master-overview-top">
          <Col xs={24} md={16}>
            <motion.div
              className="master-overview-cell"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3 }}
            >
              <Card className="card-luxury client-car-card">
                {firstCar ? (
                  <>
                    <Row justify="space-between" align="top">
                      <Col>
                        <Text className="text-white car-title">
                          {firstCar.make} {firstCar.model}
                        </Text>
                        <div className="mt-4">
                          <Text className="text-titanium car-subtitle">
                            {firstCar.license_plate ? ` · ${firstCar.license_plate}` : ''}
                          </Text>
                        </div>
                        <div className="mt-8">
                          <Text className="car-status">✔ Автомобиль клиента</Text>
                        </div>
                      </Col>
                      <Col>
                        <Button
                          size="small"
                          look="ghost"
                          onClick={() => goSection('tasks')}
                        >
                          К заданию
                        </Button>
                      </Col>
                    </Row>
                    {activeAppointments.length > 0 && (
                      <>
                        <Divider className="divider-dim" />
                        <div>
                          <Text className="text-titanium car-service-label">ТЕКУЩЕЕ ЗАДАНИЕ</Text>
                          <div className="flex-space-between mt-8">
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
                    <Text className="text-titanium d-block text-13 mt-8">
                      Нет активных заданий
                    </Text>
                  </div>
                )}
              </Card>
            </motion.div>
          </Col>

          <Col xs={24} md={8}>
            <motion.div
              className="master-overview-cell"
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ duration: 0.3, delay: 0.1 }}
            >
              <div className="analytics-section master-overview-stats">
                <Text className="text-white analytics-title">Статистика</Text>
                <div className="mt-12">
                  <Text className="text-titanium text-13">Активные задания</Text>
                  <div>
                    <Text className="stat-value-gold">{activeAppointments.length}</Text>
                  </div>
                </div>
                <div className="mt-12">
                  <Text className="text-titanium text-13">Выполнено сегодня</Text>
                  <div>
                    <Text className="stat-value-green">{kpi.completed_today}</Text>
                  </div>
                </div>
                <div className="mt-12">
                  <Text className="text-titanium text-13">Закрыто за месяц</Text>
                  <div>
                    <Text className="stat-value-white">{kpi.completed_month}</Text>
                  </div>
                </div>
                <Button
                  type="primary"
                  size="large"
                  look="gold" className="master-overview-tasks-btn"
                  onClick={() => goSection('tasks')}
                >
                  Мои задания
                </Button>
              </div>
            </motion.div>
          </Col>
        </Row>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.12 }}
        >
          <div className="admin-section-head master-kpi-title">
            <div>
              <h3>Мои показатели</h3>
              <p className="text-titanium" style={{ marginTop: 4 }}>
                За месяц{kpi.period_start ? ` · с ${dayjs(kpi.period_start).format('D MMMM')}` : ''}
                {' · '}оценка по техкартам, расходу и повторным
              </p>
            </div>
          </div>
          <Row gutter={[12, 12]} className="master-kpi-row">
            {[
              {
                key: 'rev',
                label: 'Выручка',
                value: formatCurrency(kpi.revenue),
                icon: <DollarOutlined />,
                tone: 'gold' as const,
                hint: null as string | null,
                spark: kpi.sparkline_revenue,
              },
              {
                key: 'avg',
                label: 'Средний чек',
                value: formatCurrency(kpi.avg_check),
                icon: <CheckCircleOutlined />,
                tone: 'gold' as const,
                hint: kpi.completed_month ? `${kpi.completed_month} закрытий` : 'пока нет закрытий',
                spark: undefined,
              },
              {
                key: 'rep',
                label: 'Повторные',
                value: String(kpi.repeat_clients),
                icon: <TeamOutlined />,
                tone: kpi.repeat_clients > 0 ? ('ok' as const) : ('gold' as const),
                hint: kpi.unique_clients
                  ? `${kpi.repeat_rate}% · ${kpi.unique_clients} клиентов`
                  : 'клиенты с 2+ визитами',
                spark: undefined,
              },
              {
                key: 'score',
                label: 'Оценка',
                value: `${kpi.score.toFixed(1)} / 5`,
                icon: <StarOutlined />,
                tone: kpi.score >= 4 ? ('ok' as const) : kpi.score >= 2.5 ? ('gold' as const) : ('warn' as const),
                hint: kpi.score_hint,
                spark: undefined,
              },
              {
                key: 'tech',
                label: 'Техкарта',
                value: `${kpi.tech_compliance_pct}%`,
                icon: <FileProtectOutlined />,
                tone: kpi.tech_compliance_pct >= 90 ? ('ok' as const) : kpi.tech_compliance_pct >= 70 ? ('gold' as const) : ('warn' as const),
                hint: kpi.tech_steps_total
                  ? `${kpi.tech_steps_done} из ${kpi.tech_steps_total} шагов`
                  : 'нет отметок на закрытии',
                spark: undefined,
              },
              {
                key: 'over',
                label: 'Перерасход',
                value: kpi.overspend_cost > 0 ? `+${formatCurrency(kpi.overspend_cost)}` : formatCurrency(0),
                icon: <WarningOutlined />,
                tone: kpi.overspend_cost > 0 ? ('warn' as const) : ('ok' as const),
                hint: kpi.overspend_qty > 0
                  ? `+${kpi.overspend_qty} к норме · ${kpi.overspend_pct}%`
                  : 'факт в пределах нормы',
                spark: undefined,
              },
            ].map((m) => (
              <Col xs={12} sm={8} lg={4} key={m.key}>
                <Card className={`admin-kpi-card master-kpi-card tone-${m.tone}`} bordered={false}>
                  <div className="admin-kpi-icon">{m.icon}</div>
                  <div className="admin-kpi-label">{m.label}</div>
                  <div className="admin-kpi-value">{m.value}</div>
                  {m.hint ? <div className="master-kpi-hint">{m.hint}</div> : null}
                  <MasterKpiSpark data={m.spark} />
                </Card>
              </Col>
            ))}
          </Row>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.15 }}
        >
          <Card className="card-luxury master-overview-ai">
            <Row align="middle" className="mb-12">
              <Col flex="auto">
                <Text className="title-gold text-16">AI ДЕТЕЙЛЕР</Text>
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
                  look="ghost"
                  onClick={() => {}}
                >
                  {chip}
                </Button>
              ))}
            </div>
          </Card>
        </motion.div>

        <motion.div
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.3, delay: 0.2 }}
        >
          <Row gutter={[12, 12]} className="master-overview-actions">
            {quickActions.map((action) => (
              <Col xs={12} sm={6} key={action.label}>
                <Card
                  className="card-luxury quick-action-card"
                  hoverable
                  onClick={() => goSection(action.key)}
                  styles={{ body: { padding: '16px 8px' } }}
                >
                  <span className="quick-action-icon text-gold">{action.icon}</span>
                  <span className="quick-action-label text-white d-block">{action.label}</span>
                </Card>
              </Col>
            ))}
          </Row>
        </motion.div>
      </div>
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
                value={kpi.completed_today}
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
                              <Text className="text-gold text-12 detailer-brief">
                                {item.master_brief.startsWith('Детейлер')
                                  ? item.master_brief
                                  : `📋 Заметка: ${item.master_brief}`}
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
                                  look="ghost"
                                  style={{ width: 'auto', height: 32, fontSize: 12 }}
                                >Взять в работу</Button>
                              )}
                              {item.status === 'in_progress' && (
                                <Button
                                  size="small"
                                  icon={<CheckCircleOutlined />}
                                  loading={actionLoading === item.id}
                                  onClick={() => setCloseAppt(item)}
                                  look="gold"
                                  style={{ width: 'auto', height: 32, fontSize: 12 }}
                                >Завершить</Button>
                              )}
                              <Tooltip title="Заметка мастера">
                                <Button
                                  size="small"
                                  icon={<EditOutlined />}
                                  onClick={() => openNotesModal(item)}
                                  look="ghost"
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

        <div className="master-stat-tile">
          <Text className="text-titanium text-13 d-block mb-4">
            Выполнено работ
          </Text>
          <Text className="stat-value-green">
            {completedAppointments.length}
          </Text>
        </div>
      </Card>

      <Button
        type="primary"
        look="gold" className="mt-4"
        icon={<CameraOutlined />}
        onClick={() => goSection('portfolio')}
      >
        Открыть портфолио
      </Button>
    </motion.div>
  );

  const renderPortfolio = () => (
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.4 }}>
      <PortfolioSection
        masterId={user.id}
        masterName={user.full_name}
        masterPhone={user.phone}
        completedCount={completedAppointments.length}
        allServices={masterServices}
      />
    </motion.div>
  );

  /* ============================================================
     RENDER: Notifications
     ============================================================ */
  const renderNotifications = () => (
    <Tabs
      className="notifications-tabs"
      size="large"
      items={[
        {
          key: 'list',
          label: <span><BellOutlined /> Список уведомлений</span>,
          children: <NotificationList title="Мои уведомления" />,
        },
        {
          key: 'settings',
          label: <span>Настройки</span>,
          children: <NotificationSettings />,
        },
      ]}
    />
  );

  /* ============================================================
     RENDER: Content router
     ============================================================ */
  const renderContent = () => {
    const allowed = nav.some((item) => item.key === activeSection);
    const section = allowed ? activeSection : 'overview';
    switch (section) {
      case 'overview': return renderOverview();
      case 'tasks': return renderTasks();
      case 'portfolio': return renderPortfolio();
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
    <Layout className="client-layout master-layout">
      <Header className="header-mobile admin-header-mobile">
        <img src="/images/logo-formula-sport.png" alt="" className="client-header-logo" />
        <Text className="admin-header-title">CAR DETAILING AI</Text>
        <span className="admin-header-badge">Мастер</span>
      </Header>

      <Header className="header-desktop admin-header">
        <Space className="admin-header-brand" size="middle" align="center">
          <img src="/images/logo-formula-sport.png" alt="" className="client-header-logo" />
          <Text className="admin-header-title">CAR DETAILING AI</Text>
          <span className="admin-header-badge">Мастер</span>
        </Space>
        <Space size="middle" className="admin-header-actions" wrap>
          <span className="admin-header-user">
            <UserOutlined />
            <span>{user.full_name}</span>
          </span>
          <NotificationBell />
          <Button
            type="text"
            icon={<LogoutOutlined />}
            onClick={onLogout}
            className="admin-header-btn admin-header-btn-logout"
          >
            Выйти
          </Button>
        </Space>
      </Header>

      <Layout className="admin-body-layout">
        {/* Сайдбар (десктоп) */}
        <Sider
          className="sidebar admin-sidebar"
          breakpoint="md"
          collapsedWidth={0}
          width={228}
          trigger={null}
        >
          {nav.map(item => (
            <button
              key={item.key}
              className={`sidebar-item${activeSection === item.key ? ' active' : ''}`}
              onClick={() => goSection(item.key)}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </Sider>

        {/* Контент */}
        <Content className="client-content admin-content">
          {renderContent()}
        </Content>
      </Layout>

      {/* Нижняя навигация (моб) */}
      <div className="bottom-nav">
        {nav.map(item => (
          <button
            key={item.key}
            className={`bottom-nav-item${activeSection === item.key ? ' active' : ''}`}
            onClick={() => goSection(item.key)}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.short || item.label}</span>
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
              look="gold"
              onClick={handleSaveNotes}
              loading={notesSaving}
            >Сохранить заметку</Button>
          </Space>
        )}
      </Modal>

      <CloseVisitModal
        open={Boolean(closeAppt)}
        appointmentId={closeAppt?.id ?? null}
        role="master"
        onCancel={() => setCloseAppt(null)}
        onClosed={() => {
          setCloseAppt(null);
          fetchAppointments();
        }}
      />
    </Layout>
  );
}
