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
} from '@ant-design/icons';
import dayjs from 'dayjs';
import PortfolioSection from './components/PortfolioSection';

const { Text } = Typography;
const { TabPane } = Tabs;
const { Header, Content } = Layout;
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

/* ============================================================
   COMPONENT: MasterDashboard
   ============================================================ */
interface MasterDashboardProps {
  user: { id: number; phone: string; full_name: string; role: string };
  onLogout: () => void;
}

export default function MasterDashboard({ user, onLogout }: MasterDashboardProps) {
  const [activeTab, setActiveTab] = useState('tasks');

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(false);

  const [notesModal, setNotesModal] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [notesText, setNotesText] = useState('');
  const [notesSaving, setNotesSaving] = useState(false);

  const [actionLoading, setActionLoading] = useState<number | null>(null);

  useEffect(() => {
    fetchAppointments();
  }, []);

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
    a => a.status === 'confirmed' || a.status === 'in_progress'
  );
  const completedAppointments = appointments.filter(
    a => a.status === 'completed'
  );

  const formatCurrency = (val: number) => `${val.toLocaleString()} ₽`;

  /* ============================================================
     RENDER
     ============================================================ */
  return (
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0B0D10' }}>
      {/* HEADER */}
      <Header style={{
        backgroundColor: '#13161A',
        borderBottom: '1px solid rgba(255,255,255,0.06)',
        padding: '0 24px',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'space-between',
        height: '64px',
      }}>
        <Space>
          <ToolOutlined style={{ fontSize: '22px', color: '#C8A977' }} />
          <Text style={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}>
            CarDetailing AI
          </Text>
          <Tag color="gold" style={{ borderRadius: '10px', border: 'none', marginLeft: '8px' }}>
            Мастер
          </Tag>
        </Space>
        <Space size="middle">
          <Text style={{ color: '#AAB2BF' }}>
            🔧 {user.full_name}
          </Text>
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} style={{ color: '#AAB2BF' }}>
            Выйти
          </Button>
        </Space>
      </Header>

      {/* CONTENT */}
      <Content style={{ padding: '24px', maxWidth: '960px', width: '100%', margin: '0 auto' }}>
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '24px' }}
        >
          {/* ===== TAB 1: TASKS ===== */}
          <TabPane tab={<span><ToolOutlined /> Мои задания</span>} key="tasks">
            <Spin spinning={loading}>
              {/* Stats bar */}
              <Row gutter={[16, 16]} style={{ marginBottom: '24px' }}>
                <Col xs={12} sm={6}>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                    <Card style={{
                      backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '20px', textAlign: 'center',
                    }}>
                      <Statistic
                        title={<Text style={{ color: '#AAB2BF', fontSize: '12px' }}>Активные</Text>}
                        value={activeAppointments.length}
                        valueStyle={{ color: '#C8A977', fontSize: '28px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.05 }}>
                    <Card style={{
                      backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '20px', textAlign: 'center',
                    }}>
                      <Statistic
                        title={<Text style={{ color: '#AAB2BF', fontSize: '12px' }}>Выполнено сегодня</Text>}
                        value={completedAppointments.filter(a =>
                          dayjs(a.start_time).isSame(dayjs(), 'day')
                        ).length}
                        valueStyle={{ color: '#4ECB71', fontSize: '28px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.1 }}>
                    <Card style={{
                      backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '20px', textAlign: 'center',
                    }}>
                      <Statistic
                        title={<Text style={{ color: '#AAB2BF', fontSize: '12px' }}>Всего заданий</Text>}
                        value={appointments.length}
                        valueStyle={{ color: '#FFFFFF', fontSize: '28px', fontWeight: 700 }}
                      />
                    </Card>
                  </motion.div>
                </Col>
                <Col xs={12} sm={6}>
                  <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3, delay: 0.15 }}>
                    <Card style={{
                      backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                      borderRadius: '20px', textAlign: 'center',
                    }}>
                      <Button
                        icon={<ReloadOutlined />}
                        onClick={fetchAppointments}
                        type="text"
                        style={{ color: '#AAB2BF', marginTop: '12px' }}
                      >
                        Обновить
                      </Button>
                    </Card>
                  </motion.div>
                </Col>
              </Row>

              {appointments.length === 0 && !loading ? (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                  <Card style={{
                    backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '24px', textAlign: 'center', padding: '40px',
                  }}>
                    <Empty
                      description={
                        <Space direction="vertical" size="small">
                          <Text style={{ color: '#AAB2BF', fontSize: '16px' }}>Нет назначенных заданий</Text>
                          <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                            Когда администратор назначит вам запись, она появится здесь
                          </Text>
                        </Space>
                      }
                    />
                  </Card>
                </motion.div>
              ) : (
                <>
                  {/* Active tasks */}
                  {activeAppointments.length > 0 && (
                    <>
                      <Text style={{ color: '#C8A977', fontSize: '15px', fontWeight: 600, display: 'block', marginBottom: '12px' }}>
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
                              style={{
                                backgroundColor: '#13161A',
                                border: item.status === 'in_progress'
                                  ? '1px solid rgba(200,169,119,0.3)'
                                  : '1px solid rgba(255,255,255,0.06)',
                                borderRadius: '20px',
                                marginBottom: '12px',
                              }}
                            >
                              <Row justify="space-between" align="middle" gutter={[12, 8]}>
                                <Col xs={24} md={14}>
                                  <Space direction="vertical" size={4}>
                                    <Space>
                                      <Text style={{ color: '#FFFFFF', fontWeight: 600, fontSize: '15px' }}>
                                        {item.service_name || `Услуга #${item.service_id}`}
                                      </Text>
                                      <Tag color={STATUS_COLORS[item.status]} style={{ borderRadius: '8px', border: 'none', fontSize: '11px' }}>
                                        {STATUS_LABELS[item.status]}
                                      </Tag>
                                    </Space>
                                    <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                                      <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                                      {' — '}{dayjs(item.end_time).format('HH:mm')}
                                    </Text>
                                    {item.client && (
                                      <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                                        <UserOutlined /> {item.client.full_name}
                                        {' '}<PhoneOutlined /> {item.client.phone}
                                      </Text>
                                    )}
                                    {item.car && (
                                      <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                                        <CarOutlined /> {item.car.make} {item.car.model}
                                        {item.car.license_plate ? ` (${item.car.license_plate})` : ''}
                                      </Text>
                                    )}
                                    {item.client_notes && (
                                      <Text style={{ color: '#AAB2BF', fontSize: '12px', opacity: 0.7 }}>
                                        <FileTextOutlined /> Клиент: {item.client_notes}
                                      </Text>
                                    )}
                                    {item.master_brief && (
                                      <Text style={{ color: '#C8A977', fontSize: '12px' }}>
                                        📋 Заметка: {item.master_brief}
                                      </Text>
                                    )}
                                  </Space>
                                </Col>
                                <Col xs={24} md={10}>
                                  <Space direction="vertical" size="small" style={{ width: '100%' }}>
                                    <Text style={{ color: '#C8A977', fontSize: '16px', fontWeight: 700, display: 'block', textAlign: 'right' }}>
                                      {formatCurrency(item.total_price)}
                                    </Text>
                                    <Space style={{ width: '100%', justifyContent: 'flex-end' }} wrap>
                                      {item.status === 'confirmed' && (
                                        <Button
                                          size="small"
                                          icon={<PlayCircleOutlined />}
                                          loading={actionLoading === item.id}
                                          onClick={() => handleChangeStatus(item, 'in_progress')}
                                          style={{
                                            backgroundColor: '#232A33', border: 'none',
                                            color: '#C8A977', borderRadius: '10px',
                                          }}
                                        >
                                          Взять в работу
                                        </Button>
                                      )}
                                      {item.status === 'in_progress' && (
                                        <Button
                                          size="small"
                                          icon={<CheckCircleOutlined />}
                                          loading={actionLoading === item.id}
                                          onClick={() => handleChangeStatus(item, 'completed')}
                                          style={{
                                            backgroundColor: '#0F5D46', border: 'none',
                                            color: '#FFFFFF', borderRadius: '10px',
                                          }}
                                        >
                                          Завершить
                                        </Button>
                                      )}
                                      <Tooltip title="Заметка мастера">
                                        <Button
                                          size="small"
                                          icon={<EditOutlined />}
                                          onClick={() => openNotesModal(item)}
                                          style={{
                                            backgroundColor: 'transparent',
                                            border: '1px solid rgba(255,255,255,0.1)',
                                            color: '#AAB2BF', borderRadius: '10px',
                                          }}
                                        >
                                          Заметка
                                        </Button>
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

                  {/* Completed tasks */}
                  {completedAppointments.length > 0 && (
                    <>
                      <Text style={{
                        color: '#AAB2BF', fontSize: '14px', fontWeight: 500,
                        display: 'block', marginBottom: '12px', marginTop: '24px',
                      }}>
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
                              style={{
                                backgroundColor: '#13161A',
                                border: '1px solid rgba(255,255,255,0.04)',
                                borderRadius: '20px',
                                marginBottom: '8px',
                                opacity: 0.7,
                              }}
                            >
                              <Row justify="space-between" align="middle" gutter={[12, 8]}>
                                <Col xs={24} md={16}>
                                  <Space direction="vertical" size={2}>
                                    <Space>
                                      <Text style={{ color: '#FFFFFF', fontWeight: 500, fontSize: '14px' }}>
                                        {item.service_name || `Услуга #${item.service_id}`}
                                      </Text>
                                      <Tag color={STATUS_COLORS[item.status]} style={{ borderRadius: '8px', border: 'none', fontSize: '11px' }}>
                                        {STATUS_LABELS[item.status]}
                                      </Tag>
                                    </Space>
                                    <Text style={{ color: '#AAB2BF', fontSize: '12px' }}>
                                      <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                                      {item.client && <> · {item.client.full_name}</>}
                                      {item.car && <> · {item.car.make} {item.car.model}</>}
                                    </Text>
                                  </Space>
                                </Col>
                                <Col xs={24} md={8} style={{ textAlign: 'right' }}>
                                  <Text style={{ color: '#C8A977', fontSize: '14px', fontWeight: 600 }}>
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
          </TabPane>

          {/* ===== TAB 2: PROFILE ===== */}
          <TabPane tab={<span><UserOutlined /> Профиль</span>} key="profile">
            <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.5 }}>
              <Card style={{
                backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                borderRadius: '24px', padding: '24px 20px',
                maxWidth: '480px', margin: '0 auto',
                boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
              }}>
                <div style={{
                  width: '72px', height: '72px', borderRadius: '50%', backgroundColor: '#232A33',
                  margin: '0 auto 16px', display: 'flex', alignItems: 'center', justifyContent: 'center',
                  border: '2px solid #C8A977', fontSize: '32px',
                }}>🔧</div>
                <Text style={{ color: '#FFFFFF', fontSize: '22px', fontWeight: 700, display: 'block', textAlign: 'center' }}>
                  {user.full_name}
                </Text>
                <Text style={{ color: '#C8A977', fontSize: '15px', display: 'block', textAlign: 'center', marginBottom: '4px' }}>
                  Мастер-детейлер
                </Text>
                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', textAlign: 'center', marginBottom: '20px' }}>
                  <PhoneOutlined /> {user.phone}
                </Text>

                <div style={{
                  backgroundColor: '#1A1E23', borderRadius: '14px',
                  padding: '16px', textAlign: 'center',
                }}>
                  <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '4px' }}>
                    Выполнено работ
                  </Text>
                  <Text style={{ color: '#4ECB71', fontSize: '32px', fontWeight: 700 }}>
                    {completedAppointments.length}
                  </Text>
                </div>
              </Card>

              {/* Портфолио мастера */}
              <div className="mt-4">
                <PortfolioSection masterId={user.id} />
              </div>
            </motion.div>
          </TabPane>
        </Tabs>
      </Content>

      {/* ===== NOTES MODAL ===== */}
      <Modal
        title={<span style={{ color: '#FFFFFF' }}>📋 Заметка мастера</span>}
        open={notesModal}
        onCancel={() => setNotesModal(false)}
        footer={null}
        styles={{
          content: {
            backgroundColor: '#13161A', borderRadius: '24px',
            border: '1px solid rgba(255,255,255,0.06)',
          },
          mask: { backgroundColor: 'rgba(0,0,0,0.7)' },
        }}
      >
        {selectedAppt && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '4px' }}>
                Услуга: <Text style={{ color: '#FFFFFF' }}>{selectedAppt.service_name}</Text>
              </Text>
              {selectedAppt.client && (
                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '4px' }}>
                  Клиент: <Text style={{ color: '#FFFFFF' }}>{selectedAppt.client.full_name}</Text>
                </Text>
              )}
              {selectedAppt.car && (
                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '12px' }}>
                  Авто: <Text style={{ color: '#FFFFFF' }}>{selectedAppt.car.make} {selectedAppt.car.model}</Text>
                </Text>
              )}
            </div>

            <div>
              <Text style={{ color: '#AAB2BF', display: 'block', marginBottom: '6px' }}>
                Что сделано / примечания
              </Text>
              <TextArea
                rows={4}
                placeholder="Опишите выполненную работу, особенности, расходники..."
                value={notesText}
                onChange={(e) => setNotesText(e.target.value)}
                style={{
                  backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)',
                  color: '#FFFFFF', borderRadius: '14px',
                }}
              />
            </div>

            <Button
              type="primary"
              size="large"
              onClick={handleSaveNotes}
              loading={notesSaving}
              style={{
                width: '100%', borderRadius: '20px', height: '46px',
                backgroundColor: '#C8A977', borderColor: '#C8A977',
                color: '#0B0D10', fontWeight: 600, fontSize: '15px',
              }}
            >
              Сохранить заметку
            </Button>
          </Space>
        )}
      </Modal>
    </Layout>
  );
}
