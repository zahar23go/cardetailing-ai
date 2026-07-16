import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Input, Button, Tabs, message, List, Tag, Select,
  DatePicker, Form as AntForm, InputNumber, Space, Spin, Empty, Badge,
  Layout, Row, Col, Divider, Modal,
} from 'antd';
import {
  CarOutlined, CalendarOutlined, ClockCircleOutlined,
  FileTextOutlined, PlusOutlined, HistoryOutlined,
  ShopOutlined, LogoutOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import CarCard from './components/CarCard';

const { Title, Text } = Typography;
const { TabPane } = Tabs;
const { Header, Content } = Layout;
const { Option } = Select;
const { TextArea } = Input;

/* ============================================================
   TYPES
   ============================================================ */
interface Service {
  id: number;
  name: string;
  description: string;
  price: number;
  duration: number;
  category?: string;
}

interface Appointment {
  id: number;
  client_id: number;
  master_id: number | null;
  car_id: number;
  service_id: number;
  start_time: string;
  end_time: string;
  status: 'pending' | 'confirmed' | 'in_progress' | 'completed' | 'cancelled' | 'no_show';
  total_price: number;
  discount_applied: number;
  client_notes: string | null;
  master_brief: string | null;
  service_name: string | null;
  created_at?: string;
  updated_at?: string;
  client?: { id: number; full_name: string; phone: string };
  master?: { id: number; full_name: string };
  car?: { id: number; make: string; model: string; license_plate: string };
  service?: { id: number; name: string; price: number };
}

interface Car {
  id: number;
  client_id: number;
  make: string;
  model: string;
  year?: number;
  license_plate?: string;
  color?: string;
  notes?: string;
}

interface User {
  id: number;
  phone: string;
  full_name: string;
  role: 'client' | 'master' | 'admin' | 'super_admin';
}

/* ============================================================
   HELPERS
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

const roleIcon: Record<string, string> = {
  client: '👤',
  master: '🔧',
  admin: '👑',
  super_admin: '⭐',
};

const roleLabel: Record<string, string> = {
  client: 'Клиент',
  master: 'Мастер-детейлер',
  admin: 'Владелец',
  super_admin: 'Супер-админ',
};

const statusColors: Record<string, string> = {
  pending: 'gold',
  confirmed: 'blue',
  in_progress: 'cyan',
  completed: 'green',
  cancelled: 'red',
  no_show: 'default',
};

const statusLabel: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  in_progress: 'В работе',
  completed: 'Выполнена',
  cancelled: 'Отменена',
  no_show: 'Не явился',
};

/* ============================================================
   COMPONENT: ClientDashboard
   ============================================================ */
export default function ClientDashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState('services');
  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [appointmentsLoading, setAppointmentsLoading] = useState(false);
  const [appointmentsTotal, setAppointmentsTotal] = useState(0);
  const [appointmentsPage, setAppointmentsPage] = useState(1);
  const MY_PAGE_SIZE = 10;
  const [creating, setCreating] = useState(false);

  const [selectedService, setSelectedService] = useState<number | undefined>(undefined);
  const [apptDate, setApptDate] = useState<string>('');
  const [apptTime, setApptTime] = useState<string>('');
  const [carInfo, setCarInfo] = useState('');
  const [apptNotes, setApptNotes] = useState('');

  const [cars, setCars] = useState<Car[]>([]);
  const [carsLoading, setCarsLoading] = useState(false);
  const [showAddCar, setShowAddCar] = useState(false);
  const [selectedCarId, setSelectedCarId] = useState<number | undefined>(undefined);
  const [carForm, setCarForm] = useState({
    make: '', model: '', year: undefined as number | undefined,
    license_plate: '', color: '', notes: '',
  });
  const [carFormLoading, setCarFormLoading] = useState(false);

  const [serviceCategory, setServiceCategory] = useState<string>('all');

  // Edit appointment state
  const [editModal, setEditModal] = useState(false);
  const [editingAppt, setEditingAppt] = useState<Appointment | null>(null);
  const [editDate, setEditDate] = useState<string>('');
  const [editTime, setEditTime] = useState<string>('');
  const [editCarId, setEditCarId] = useState<number | undefined>(undefined);
  const [editSaving, setEditSaving] = useState(false);

  useEffect(() => {
    fetchServices();
    fetchAppointments();
    fetchCars();
  }, []);

  const fetchServices = async () => {
    setServicesLoading(true);
    try {
      const data = await apiFetch<{items: Service[]; total: number}>('/api/services?skip=0&limit=100');
      setServices(data.items);
    } catch {
      message.error('Ошибка загрузки услуг');
    }
    setServicesLoading(false);
  };

  const fetchAppointments = async (page = appointmentsPage) => {
    setAppointmentsLoading(true);
    try {
      const skip = (page - 1) * MY_PAGE_SIZE;
      const data = await apiFetch<{items: Appointment[]; total: number}>(`/api/appointments/me?skip=${skip}&limit=${MY_PAGE_SIZE}`);
      setAppointments(data.items);
      setAppointmentsTotal(data.total);
      setAppointmentsPage(page);
    } catch {
      message.error('Ошибка загрузки записей');
    }
    setAppointmentsLoading(false);
  };

  const fetchCars = async () => {
    setCarsLoading(true);
    try {
      const data = await apiFetch<Car[]>('/api/cars');
      setCars(Array.isArray(data) ? data : []);
    } catch {
      setCars([]);
      message.error('Ошибка загрузки автомобилей');
    }
    setCarsLoading(false);
  };

  const handleAddCar = async () => {
    if (!carForm.make.trim()) { message.warning('Укажите марку'); return; }
    if (!carForm.model.trim()) { message.warning('Укажите модель'); return; }
    setCarFormLoading(true);
    try {
      const newCar = await apiFetch<Car>('/api/cars', {
        method: 'POST',
        body: JSON.stringify({
          make: carForm.make.trim(),
          model: carForm.model.trim(),
          year: carForm.year || undefined,
          license_plate: carForm.license_plate.trim() || undefined,
          color: carForm.color.trim() || undefined,
          notes: carForm.notes.trim() || undefined,
        }),
      });
      setCars(prev => [...prev, newCar]);
      setSelectedCarId(newCar.id);
      setCarInfo(`${newCar.make} ${newCar.model}${newCar.license_plate ? ` (${newCar.license_plate})` : ''}`);
      setShowAddCar(false);
      setCarForm({ make: '', model: '', year: undefined, license_plate: '', color: '', notes: '' });
      message.success('✅ Автомобиль добавлен!');
    } catch (e: any) {
      message.error(e.message || 'Ошибка добавления автомобиля');
    }
    setCarFormLoading(false);
  };

  const handleCarSelect = (carId: number | undefined) => {
    setSelectedCarId(carId);
    if (carId) {
      const car = Array.isArray(cars) ? cars.find(c => c.id === carId) : undefined;
      if (car) {
        setCarInfo(`${car.make} ${car.model}${car.license_plate ? ` (${car.license_plate})` : ''}`);
      }
    } else {
      setCarInfo('');
    }
  };

  const [cancellingId, setCancellingId] = useState<number | null>(null);

  const handleCancelAppointment = async (appointmentId: number) => {
    setCancellingId(appointmentId);
    try {
      await apiFetch(`/api/appointments/${appointmentId}/cancel`, { method: 'PUT' });
      message.success('✅ Запись отменена');
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка отмены записи');
    }
    setCancellingId(null);
  };

  const openEditModal = (appt: Appointment) => {
    setEditingAppt(appt);
    setEditDate(dayjs(appt.start_time).format('YYYY-MM-DD'));
    setEditTime(dayjs(appt.start_time).format('HH:mm'));
    setEditCarId(appt.car_id);
    setEditModal(true);
  };

  const handleEditAppointment = async () => {
    if (!editingAppt) return;
    if (!editDate) { message.warning('Выберите дату'); return; }
    if (!editTime) { message.warning('Выберите время'); return; }
    if (!editCarId) { message.warning('Выберите автомобиль'); return; }
    setEditSaving(true);
    try {
      const startTime = `${editDate}T${editTime}:00`;
      await apiFetch(`/api/appointments/${editingAppt.id}/edit`, {
        method: 'PUT',
        body: JSON.stringify({
          start_time: startTime,
          car_id: editCarId,
        }),
      });
      message.success('✅ Запись обновлена');
      setEditModal(false);
      setEditingAppt(null);
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления записи');
    }
    setEditSaving(false);
  };

  const handleCreateAppointment = async () => {
    if (!selectedService) { message.warning('Выберите услугу'); return; }
    if (!apptDate) { message.warning('Выберите дату'); return; }
    if (!apptTime) { message.warning('Выберите время'); return; }
    if (!selectedCarId) { message.warning('Выберите автомобиль'); return; }
    setCreating(true);
    try {
      const startTime = `${apptDate}T${apptTime}:00`;
      await apiFetch('/api/appointments', {
        method: 'POST',
        body: JSON.stringify({
          service_id: selectedService,
          car_id: selectedCarId,
          start_time: startTime,
          notes: apptNotes.trim() || undefined,
        }),
      });
      message.success('✅ Запись создана!');
      setSelectedService(undefined);
      setSelectedCarId(undefined);
      setApptDate('');
      setApptTime('');
      setCarInfo('');
      setApptNotes('');
      fetchAppointments();
      setActiveTab('my');
    } catch (e: any) {
      message.error(e.message || 'Ошибка создания записи');
    }
    setCreating(false);
  };

  const categories = Array.from(new Set(services.map(s => s.category).filter(Boolean) as string[]));
  const filteredServices = serviceCategory === 'all'
    ? services
    : services.filter(s => s.category === serviceCategory);

  const upcomingAppointments = appointments.filter(a => a.status !== 'cancelled' && a.status !== 'completed');

  return (
    <Layout style={{ minHeight: '100vh' }}>
      {/* ===================== HEADER ===================== */}
      <Header className="header-command">
        <Space>
          <CarOutlined className="text-gold icon-command" />
          <Text className="title-gold title-command">
            CarDetailing AI
          </Text>
        </Space>
        <Space size="middle">
          <Badge count={upcomingAppointments.length} className="badge-gold">
            <Text className="text-titanium">
              {roleIcon[user.role]} {user.full_name}
            </Text>
          </Badge>
          <Tag color="gold" className="tag-category">
            {roleLabel[user.role]}
          </Tag>
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} className="btn-logout">
            Выйти
          </Button>
        </Space>
      </Header>

      {/* ===================== CONTENT ===================== */}
      <Content className="content-command">
        <Tabs
          activeKey={activeTab}
          onChange={setActiveTab}
          size="large"
          tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '24px' }}
        >
          {/* -------- TAB 1: SERVICES -------- */}
          <TabPane tab={<span><ShopOutlined /> Услуги</span>} key="services">
            <Spin spinning={servicesLoading}>
              {services.length === 0 && !servicesLoading ? (
                <Empty description={<Text className="text-titanium">Нет доступных услуг</Text>} />
              ) : (
                <>
                  {categories.length > 0 && (
                    <div style={{ marginBottom: '16px' }}>
                      <Space wrap>
                        <Button
                          size="small"
                          type={serviceCategory === 'all' ? 'primary' : 'default'}
                          onClick={() => setServiceCategory('all')}
                          style={serviceCategory === 'all' ? undefined : {
                            backgroundColor: '#1A1E23',
                            borderColor: 'rgba(255,255,255,0.06)',
                            color: '#AAB2BF',
                          }}
                        >Все</Button>
                        {categories.map(cat => (
                          <Button
                            key={cat}
                            size="small"
                            type={serviceCategory === cat ? 'primary' : 'default'}
                            onClick={() => setServiceCategory(cat)}
                            style={serviceCategory === cat ? undefined : {
                              backgroundColor: '#1A1E23',
                              borderColor: 'rgba(255,255,255,0.06)',
                              color: '#AAB2BF',
                            }}
                          >{cat}</Button>
                        ))}
                      </Space>
                    </div>
                  )}
                  <Row gutter={[16, 16]}>
                    {filteredServices.map(service => (
                      <Col xs={24} sm={12} key={service.id}>
                        <motion.div
                          initial={{ opacity: 0, y: 10 }}
                          animate={{ opacity: 1, y: 0 }}
                          transition={{ duration: 0.3 }}
                        >
                          <Card
                            hoverable
                            className="card-luxury"
                            onClick={() => { setSelectedService(service.id); setActiveTab('new'); }}
                          >
                            <div className="flex-space-between">
                              <div>
                                <Title level={5} className="text-white text-16">
                                  {service.name}
                                </Title>
                                {service.category && (
                                  <Tag className="tag-category">{service.category}</Tag>
                                )}
                                <Text className="text-titanium d-block">
                                  {service.description}
                                </Text>
                              </div>
                            </div>
                            <Divider className="divider-dim" />
                            <div className="flex-space-between">
                              <Text className="text-gold-bold text-18">
                                {service.price.toLocaleString()} ₽
                              </Text>
                              <Text className="text-titanium">
                                <ClockCircleOutlined /> ~{service.duration} мин
                              </Text>
                            </div>
                          </Card>
                        </motion.div>
                      </Col>
                    ))}
                  </Row>
                </>
              )}
            </Spin>
          </TabPane>

          {/* -------- TAB 2: NEW APPOINTMENT -------- */}
          <TabPane tab={<span><PlusOutlined /> Новая запись</span>} key="new">
            <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
              <Card className="card-luxury">
                <Title level={4} className="text-white" style={{ marginBottom: '20px' }}>Запись на услугу</Title>
                <div className="text-titanium text-12 mb-8">Услуг загружено: {services.length}</div>
                <div className="label-field">Услуга</div>
                <Select
                  placeholder="Выберите услугу"
                  size="large"
                  className="w-full mb-12"
                  value={selectedService}
                  onChange={setSelectedService}
                >
                  {services.map(s => (
                    <Option key={s.id} value={s.id}>
                      {s.name} — {s.price.toLocaleString()} ₽
                    </Option>
                  ))}
                </Select>
                <AntForm layout="vertical">
                    <Row gutter={16}>
                      <Col xs={24} sm={12}>
                        <AntForm.Item label={<Text className="text-titanium">Дата</Text>}>
                          <DatePicker
                            size="large"
                            style={{ width: '100%' }}
                            value={apptDate ? dayjs(apptDate, 'YYYY-MM-DD') : null}
                            onChange={(date) => setApptDate(date ? date.format('YYYY-MM-DD') : '')}
                            disabledDate={(current) => current && current.isBefore(dayjs().startOf('day'))}
                            placeholder="Выберите дату"
                          />
                        </AntForm.Item>
                      </Col>
                      <Col xs={24} sm={12}>
                        <AntForm.Item label={<Text className="text-titanium">Время</Text>}>
                          <Select
                            placeholder="Выберите время"
                            value={apptTime || undefined}
                            onChange={setApptTime}
                            size="large"
                            className="w-full"
                          >
                            {['09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00'].map(t => (
                              <Option key={t} value={t}>{t}</Option>
                            ))}
                          </Select>
                        </AntForm.Item>
                      </Col>
                    </Row>
                    <AntForm.Item label={<Text className="text-titanium">Автомобиль</Text>}>
                      <Space.Compact style={{ width: '100%' }}>
                        <Select
                          placeholder="Выберите авто"
                          value={selectedCarId}
                          onChange={handleCarSelect}
                          size="large"
                          className="w-full"
                          notFoundContent={<Text className="text-titanium">Нет сохранённых авто</Text>}
                        >
                          {Array.isArray(cars) && cars.map(c => (
                            <Option key={c.id} value={c.id}>
                              <Space>
                                <CarOutlined className="text-gold" />
                                {c.make} {c.model}
                                {c.license_plate ? ` (${c.license_plate})` : ''}
                                {c.year ? `, ${c.year}` : ''}
                              </Space>
                            </Option>
                          ))}
                        </Select>
                        <Button
                          size="large"
                          onClick={() => setShowAddCar(true)}
                          className="btn-gold-secondary"
                          style={{ width: 'auto', borderRadius: '0 14px 14px 0' }}
                        >+</Button>
                      </Space.Compact>
                    </AntForm.Item>
                    <AntForm.Item label={<Text className="text-titanium">Комментарий (необязательно)</Text>}>
                      <TextArea
                        rows={3}
                        className="input-luxury"
                        placeholder="Дополнительные пожелания..."
                        value={apptNotes}
                        onChange={(e) => setApptNotes(e.target.value)}
                      />
                    </AntForm.Item>
                    <Button
                      type="primary" size="large" onClick={handleCreateAppointment} loading={creating}
                      className="btn-gold"
                    >Создать запись</Button>
                  </AntForm>
              </Card>
            </motion.div>
          </TabPane>

          {/* -------- TAB 3: MY APPOINTMENTS -------- */}
          <TabPane tab={<span><HistoryOutlined /> Мои записи</span>} key="my">
            <Spin spinning={appointmentsLoading}>
              {appointments.length === 0 && !appointmentsLoading ? (
                <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                  <Card className="card-luxury" style={{ textAlign: 'center' }}>
                    <Empty
                      description={
                        <Space direction="vertical" size="small">
                          <Text className="text-titanium text-16">У вас пока нет записей</Text>
                          <Text className="text-titanium text-13">Выберите услугу и создайте первую запись</Text>
                        </Space>
                      }
                    />
                    <Button
                      type="primary"
                      onClick={() => setActiveTab('services')}
                      className="btn-gold"
                      style={{ marginTop: '16px' }}
                    >Посмотреть услуги</Button>
                  </Card>
                </motion.div>
              ) : (
                <List
                  dataSource={appointments}
                  pagination={{
                    current: appointmentsPage,
                    pageSize: MY_PAGE_SIZE,
                    total: appointmentsTotal,
                    onChange: (page) => fetchAppointments(page),
                    showSizeChanger: false,
                    size: 'small',
                  }}
                  renderItem={(item, index) => (
                    <motion.div
                      initial={{ opacity: 0, y: 10 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.3, delay: index * 0.05 }}
                    >
                      <List.Item style={{
                        backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                        borderRadius: '20px', padding: '16px 20px', marginBottom: '12px',
                      }}>
                        <List.Item.Meta
                          avatar={
                            <div style={{
                              width: '44px', height: '44px', borderRadius: '12px',
                              backgroundColor: '#232A33', display: 'flex',
                              alignItems: 'center', justifyContent: 'center', fontSize: '20px',
                            }}>
                              {item.status === 'completed' ? '✅' :
                               item.status === 'cancelled' ? '❌' :
                               item.status === 'in_progress' ? '🔧' :
                               item.status === 'no_show' ? '🚫' :
                               item.status === 'confirmed' ? '📅' : '⏳'}
                            </div>
                          }
                          title={
                            <Space>
                              <Text className="text-white-bold">
                                {item.service_name || `Услуга #${item.service_id}`}
                              </Text>
                              <Tag color={statusColors[item.status]} style={{ borderRadius: '8px', border: 'none' }}>
                                {statusLabel[item.status]}
                              </Tag>
                            </Space>
                          }
                          description={
                            <Space direction="vertical" size={2} style={{ marginTop: '4px' }}>
                              <Text className="text-titanium text-13">
                                <CalendarOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY')}
                                {' · '}<ClockCircleOutlined /> {dayjs(item.start_time).format('HH:mm')}
                                {' — '}{dayjs(item.end_time).format('HH:mm')}
                              </Text>
                              <Text className="text-titanium text-13">
                                <CarOutlined /> {item.car ? `${item.car.make} ${item.car.model}${item.car.license_plate ? ` (${item.car.license_plate})` : ''}` : '—'}
                              </Text>
                              {item.client_notes && (
                                <Text className="text-titanium text-12 opacity-70">
                                  <FileTextOutlined /> {item.client_notes}
                                </Text>
                              )}
                              {(item.status === 'pending' || item.status === 'confirmed') && (
                                <Space size="small">
                                  <Button
                                    size="small"
                                    className="btn-action-gold"
                                    onClick={() => openEditModal(item)}
                                  >Редактировать</Button>
                                  <Button
                                    size="small"
                                    className="btn-action-danger"
                                    loading={cancellingId === item.id}
                                    disabled={cancellingId !== null}
                                    onClick={() => handleCancelAppointment(item.id)}
                                  >Отменить</Button>
                                </Space>
                              )}
                            </Space>
                          }
                        />
                      </List.Item>
                    </motion.div>
                  )}
                />
              )}
            </Spin>
          </TabPane>

          {/* -------- TAB 4: MY CARS -------- */}
          <TabPane tab={<span><CarOutlined /> Мои автомобили</span>} key="cars">
            <Spin spinning={carsLoading}>
              {(cars?.length ?? 0) === 0 && !carsLoading ? (
                <Card className="card-luxury" style={{ textAlign: 'center' }}>
                  <Empty description={<Text className="text-titanium text-16">У вас пока нет автомобилей</Text>} />
                  <Button
                    type="primary"
                    onClick={() => setShowAddCar(true)}
                    className="btn-gold"
                    style={{ marginTop: '16px' }}
                  ><PlusOutlined /> Добавить автомобиль</Button>
                </Card>
              ) : (
                <>
                  <div className="toolbar-right">
                    <Button
                      type="primary"
                      onClick={() => setShowAddCar(true)}
                      className="btn-gold"
                    ><PlusOutlined /> Добавить</Button>
                  </div>
                  <Row gutter={[16, 16]}>
                    {Array.isArray(cars) && cars.map(car => (
                      <Col xs={24} sm={12} key={car.id}>
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                          <CarCard
                            carId={car.id}
                            make={car.make}
                            model={car.model}
                            licensePlate={car.license_plate}
                            color={car.color}
                            year={car.year}
                          />
                        </motion.div>
                      </Col>
                    ))}
                  </Row>
                </>
              )}
            </Spin>
          </TabPane>
        </Tabs>
      </Content>

      {/* ===================== ADD CAR MODAL ===================== */}
      <Modal
        title={<span className="text-white">🚗 Добавить автомобиль</span>}
        open={showAddCar}
        onCancel={() => {
          setShowAddCar(false);
          setCarForm({ make: '', model: '', year: undefined, license_plate: '', color: '', notes: '' });
        }}
        footer={null}
        className="modal-command"
      >
        <AntForm layout="vertical">
          <AntForm.Item label={<Text className="text-titanium">Марка *</Text>}>
            <Input size="large" placeholder="Например: BMW" value={carForm.make}
              onChange={(e) => setCarForm(prev => ({ ...prev, make: e.target.value }))} />
          </AntForm.Item>
          <AntForm.Item label={<Text className="text-titanium">Модель *</Text>}>
            <Input size="large" placeholder="Например: X5" value={carForm.model}
              onChange={(e) => setCarForm(prev => ({ ...prev, model: e.target.value }))} />
          </AntForm.Item>
          <Row gutter={16}>
            <Col xs={12}>
              <AntForm.Item label={<Text className="text-titanium">Год</Text>}>
                <InputNumber size="large" placeholder="2024" value={carForm.year}
                  onChange={(val) => setCarForm(prev => ({ ...prev, year: val ?? undefined }))}
                  min={1990} max={2027} style={{ width: '100%' }} />
              </AntForm.Item>
            </Col>
            <Col xs={12}>
              <AntForm.Item label={<Text className="text-titanium">Цвет</Text>}>
                <Input size="large" placeholder="Чёрный" value={carForm.color}
                  onChange={(e) => setCarForm(prev => ({ ...prev, color: e.target.value }))} />
              </AntForm.Item>
            </Col>
          </Row>
          <AntForm.Item label={<Text className="text-titanium">Госномер</Text>}>
            <Input size="large" placeholder="А123БВ777" value={carForm.license_plate}
              onChange={(e) => setCarForm(prev => ({ ...prev, license_plate: e.target.value }))} />
          </AntForm.Item>
          <AntForm.Item label={<Text className="text-titanium">Заметки</Text>}>
            <TextArea rows={2} className="input-luxury" placeholder="Особые приметы, доп. информация..." value={carForm.notes}
              onChange={(e) => setCarForm(prev => ({ ...prev, notes: e.target.value }))} />
          </AntForm.Item>
          <Button
            type="primary" size="large" onClick={handleAddCar} loading={carFormLoading}
            className="btn-gold"
          >Сохранить</Button>
        </AntForm>
      </Modal>

      {/* ===================== EDIT APPOINTMENT MODAL ===================== */}
      <Modal
        title={<span className="text-white">✏️ Редактировать запись</span>}
        open={editModal}
        onCancel={() => { setEditModal(false); setEditingAppt(null); }}
        footer={null}
        className="modal-command"
      >
        <Space direction="vertical" size="middle" className="w-full">
          {editingAppt && (
            <>
              <div>
                <Text className="text-titanium d-block mb-8">Услуга: <Text className="text-white">{editingAppt.service_name}</Text></Text>
              </div>
              <Row gutter={16}>
                <Col xs={24} sm={12}>
                  <span className="label-field">Дата</span>
                  <DatePicker
                    size="large"
                    className="w-full"
                    value={editDate ? dayjs(editDate, 'YYYY-MM-DD') : null}
                    onChange={(date) => setEditDate(date ? date.format('YYYY-MM-DD') : '')}
                    disabledDate={(current) => current && current.isBefore(dayjs().startOf('day'))}
                  />
                </Col>
                <Col xs={24} sm={12}>
                  <span className="label-field">Время</span>
                  <Select
                    size="large"
                    className="w-full"
                    value={editTime || undefined}
                    onChange={setEditTime}
                  >
                    {['09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00'].map(t => (
                      <Option key={t} value={t}>{t}</Option>
                    ))}
                  </Select>
                </Col>
              </Row>
              <div>
                <span className="label-field">Автомобиль</span>
                <Select
                  size="large"
                  className="w-full"
                  value={editCarId}
                  onChange={setEditCarId}
                >
                  {Array.isArray(cars) && cars.map(c => (
                    <Option key={c.id} value={c.id}>
                      <Space>
                        <CarOutlined className="text-gold" />
                        {c.make} {c.model}
                        {c.license_plate ? ` (${c.license_plate})` : ''}
                      </Space>
                    </Option>
                  ))}
                </Select>
              </div>
              <Button
                type="primary" size="large"
                className="btn-gold"
                onClick={handleEditAppointment}
                loading={editSaving}
              >Сохранить изменения</Button>
            </>
          )}
        </Space>
      </Modal>
    </Layout>
  );
}
