import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Input, Button, Tabs, message, List, Tag, Select,
  DatePicker, Form as AntForm, InputNumber, Space, Spin, Empty, Badge,
  Layout, Row, Col, Divider, Modal,
} from 'antd';
import {
  UserOutlined, LockOutlined, PhoneOutlined, CarOutlined,
  CrownOutlined, ToolOutlined, CalendarOutlined, ClockCircleOutlined,
  FileTextOutlined, PlusOutlined, HistoryOutlined,
  ShopOutlined, LogoutOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import OwnerDashboard from './OwnerDashboard';
import MasterDashboard from './MasterDashboard';

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
  service_id: number;
  service_name?: string;
  date: string;
  time?: string;
  car_info: string;
  status: 'pending' | 'confirmed' | 'completed' | 'cancelled';
  notes?: string;
  created_at?: string;
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
  completed: 'green',
  cancelled: 'red',
};

const statusLabel: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  completed: 'Выполнена',
  cancelled: 'Отменена',
};

/* ============================================================
   COMPONENT: ClientDashboard
   ============================================================ */
function ClientDashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState('services');
  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [appointmentsLoading, setAppointmentsLoading] = useState(false);
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

  useEffect(() => {
    fetchServices();
    fetchAppointments();
    fetchCars();
  }, []);

  const fetchServices = async () => {
    setServicesLoading(true);
    try {
      const data = await apiFetch<Service[]>('/api/services');
      setServices(data);
    } catch {
      message.error('Ошибка загрузки услуг');
    }
    setServicesLoading(false);
  };

  const fetchAppointments = async () => {
    setAppointmentsLoading(true);
    try {
      const data = await apiFetch<Appointment[]>('/api/appointments/me');
      setAppointments(data);
    } catch {
      message.error('Ошибка загрузки записей');
    }
    setAppointmentsLoading(false);
  };

  const fetchCars = async () => {
    setCarsLoading(true);
    try {
      const data = await apiFetch<Car[]>('/api/cars');
      setCars(data);
    } catch {
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
      const car = cars.find(c => c.id === carId);
      if (car) {
        setCarInfo(`${car.make} ${car.model}${car.license_plate ? ` (${car.license_plate})` : ''}`);
      }
    } else {
      setCarInfo('');
    }
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
    <Layout style={{ minHeight: '100vh', backgroundColor: '#0B0D10' }}>
      {/* ===================== HEADER ===================== */}
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
          <CarOutlined style={{ fontSize: '22px', color: '#C8A977' }} />
          <Text style={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}>
            CarDetailing AI
          </Text>
        </Space>
        <Space size="middle">
          <Badge count={upcomingAppointments.length} style={{ backgroundColor: '#C8A977', color: '#0B0D10' }}>
            <Text style={{ color: '#AAB2BF' }}>
              {roleIcon[user.role]} {user.full_name}
            </Text>
          </Badge>
          <Tag color="gold" style={{ borderRadius: '10px', border: 'none' }}>
            {roleLabel[user.role]}
          </Tag>
          <Button type="text" icon={<LogoutOutlined />} onClick={onLogout} style={{ color: '#AAB2BF' }}>
            Выйти
          </Button>
        </Space>
      </Header>

      {/* ===================== CONTENT ===================== */}
      <Content style={{ padding: '24px', maxWidth: '960px', width: '100%', margin: '0 auto' }}>
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
                <Empty description={<Text style={{ color: '#AAB2BF' }}>Нет доступных услуг</Text>} />
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
                            style={{
                              backgroundColor: '#13161A',
                              border: '1px solid rgba(255,255,255,0.06)',
                              borderRadius: '20px',
                              height: '100%',
                            }}
                            onClick={() => { setSelectedService(service.id); setActiveTab('new'); }}
                          >
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start' }}>
                              <div>
                                <Title level={5} style={{ color: '#FFFFFF', marginBottom: '4px', fontSize: '16px' }}>
                                  {service.name}
                                </Title>
                                {service.category && (
                                  <Tag style={{
                                    backgroundColor: '#232A33', border: 'none',
                                    color: '#C8A977', borderRadius: '8px',
                                    fontSize: '11px', marginBottom: '8px',
                                  }}>{service.category}</Tag>
                                )}
                                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block' }}>
                                  {service.description}
                                </Text>
                              </div>
                            </div>
                            <Divider style={{ borderColor: 'rgba(255,255,255,0.04)', margin: '12px 0' }} />
                            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                              <Text style={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}>
                                {service.price.toLocaleString()} ₽
                              </Text>
                              <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
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
              <Card style={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '24px' }}>
                <Title level={4} style={{ color: '#FFFFFF', marginBottom: '20px' }}>Запись на услугу</Title>
                <AntForm layout="vertical">
                  <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Услуга</Text>}>
                    <Select
                      placeholder="Выберите услугу"
                      value={selectedService}
                      onChange={setSelectedService}
                      size="large"
                      style={{ width: '100%' }}
                      dropdownStyle={{ backgroundColor: '#1A1E23' }}
                    >
                      {services.map(s => (
                        <Option key={s.id} value={s.id}>
                          {s.name} — {s.price.toLocaleString()} ₽
                        </Option>
                      ))}
                    </Select>
                  </AntForm.Item>
                  <Row gutter={16}>
                    <Col xs={24} sm={12}>
                      <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Дата</Text>}>
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
                      <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Время</Text>}>
                        <Select
                          placeholder="Выберите время"
                          value={apptTime || undefined}
                          onChange={setApptTime}
                          size="large"
                          style={{ width: '100%' }}
                          dropdownStyle={{ backgroundColor: '#1A1E23' }}
                        >
                          {['09:00','10:00','11:00','12:00','13:00','14:00','15:00','16:00','17:00','18:00'].map(t => (
                            <Option key={t} value={t}>{t}</Option>
                          ))}
                        </Select>
                      </AntForm.Item>
                    </Col>
                  </Row>
                  <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Автомобиль</Text>}>
                    <Space.Compact style={{ width: '100%' }}>
                      <Select
                        placeholder="Выберите авто"
                        value={selectedCarId}
                        onChange={handleCarSelect}
                        size="large"
                        style={{ width: '100%' }}
                        dropdownStyle={{ backgroundColor: '#1A1E23' }}
                        notFoundContent={<Text style={{ color: '#AAB2BF' }}>Нет сохранённых авто</Text>}
                      >
                        {cars.map(c => (
                          <Option key={c.id} value={c.id}>
                            <Space>
                              <CarOutlined style={{ color: '#C8A977' }} />
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
                        style={{
                          backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)',
                          color: '#C8A977', borderRadius: '0 14px 14px 0',
                        }}
                      >+</Button>
                    </Space.Compact>
                  </AntForm.Item>
                  <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Комментарий (необязательно)</Text>}>
                    <TextArea
                      rows={3}
                      placeholder="Дополнительные пожелания..."
                      value={apptNotes}
                      onChange={(e) => setApptNotes(e.target.value)}
                      style={{
                        backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)',
                        color: '#FFFFFF', borderRadius: '14px',
                      }}
                    />
                  </AntForm.Item>
                  <Button
                    type="primary" size="large" onClick={handleCreateAppointment} loading={creating}
                    style={{
                      width: '100%', borderRadius: '20px', height: '48px',
                      backgroundColor: '#C8A977', borderColor: '#C8A977',
                      color: '#0B0D10', fontWeight: 600, fontSize: '16px',
                      boxShadow: '0 20px 40px rgba(200,169,119,0.15)',
                    }}
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
                  <Card style={{
                    backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                    borderRadius: '24px', textAlign: 'center', padding: '40px',
                  }}>
                    <Empty
                      description={
                        <Space direction="vertical" size="small">
                          <Text style={{ color: '#AAB2BF', fontSize: '16px' }}>У вас пока нет записей</Text>
                          <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>Выберите услугу и создайте первую запись</Text>
                        </Space>
                      }
                    />
                    <Button
                      type="primary"
                      onClick={() => setActiveTab('services')}
                      style={{
                        marginTop: '16px', borderRadius: '20px',
                        backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10',
                      }}
                    >Посмотреть услуги</Button>
                  </Card>
                </motion.div>
              ) : (
                <List
                  dataSource={appointments}
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
                               item.status === 'confirmed' ? '📅' : '⏳'}
                            </div>
                          }
                          title={
                            <Space>
                              <Text style={{ color: '#FFFFFF', fontWeight: 600 }}>
                                {item.service_name || `Услуга #${item.service_id}`}
                              </Text>
                              <Tag color={statusColors[item.status]} style={{ borderRadius: '8px', border: 'none' }}>
                                {statusLabel[item.status]}
                              </Tag>
                            </Space>
                          }
                          description={
                            <Space direction="vertical" size={2} style={{ marginTop: '4px' }}>
                              <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                                <CalendarOutlined /> {item.date}
                                {item.time && <> · <ClockCircleOutlined /> {item.time}</>}
                              </Text>
                              <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>
                                <CarOutlined /> {item.car_info}
                              </Text>
                              {item.notes && (
                                <Text style={{ color: '#AAB2BF', fontSize: '12px', opacity: 0.7 }}>
                                  <FileTextOutlined /> {item.notes}
                                </Text>
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
              {cars.length === 0 && !carsLoading ? (
                <Card style={{
                  backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
                  borderRadius: '24px', textAlign: 'center', padding: '40px',
                }}>
                  <Empty description={<Text style={{ color: '#AAB2BF', fontSize: '16px' }}>У вас пока нет автомобилей</Text>} />
                  <Button
                    type="primary"
                    onClick={() => setShowAddCar(true)}
                    style={{
                      marginTop: '16px', borderRadius: '20px',
                      backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10',
                    }}
                  ><PlusOutlined /> Добавить автомобиль</Button>
                </Card>
              ) : (
                <>
                  <div style={{ textAlign: 'right', marginBottom: '16px' }}>
                    <Button
                      type="primary"
                      onClick={() => setShowAddCar(true)}
                      style={{
                        borderRadius: '20px', backgroundColor: '#C8A977',
                        borderColor: '#C8A977', color: '#0B0D10',
                      }}
                    ><PlusOutlined /> Добавить</Button>
                  </div>
                  <Row gutter={[16, 16]}>
                    {cars.map(car => (
                      <Col xs={24} sm={12} key={car.id}>
                        <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }} transition={{ duration: 0.3 }}>
                          <Card style={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '20px' }}>
                            <Space direction="vertical" size={4} style={{ width: '100%' }}>
                              <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
                                <div style={{
                                  width: '40px', height: '40px', borderRadius: '10px',
                                  backgroundColor: '#232A33', display: 'flex',
                                  alignItems: 'center', justifyContent: 'center', fontSize: '18px',
                                }}>🚗</div>
                                <div>
                                  <Text style={{ color: '#FFFFFF', fontWeight: 600, fontSize: '16px' }}>
                                    {car.make} {car.model}
                                  </Text>
                                  {car.year && <Text style={{ color: '#AAB2BF', fontSize: '13px', marginLeft: '8px' }}>{car.year}</Text>}
                                </div>
                              </div>
                              {car.license_plate && <Text style={{ color: '#C8A977', fontSize: '14px', fontWeight: 500 }}>{car.license_plate}</Text>}
                              {car.color && <Text style={{ color: '#AAB2BF', fontSize: '13px' }}>🎨 {car.color}</Text>}
                              {car.notes && <Text style={{ color: '#AAB2BF', fontSize: '12px', opacity: 0.7 }}>📝 {car.notes}</Text>}
                            </Space>
                          </Card>
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
        title={<span style={{ color: '#FFFFFF' }}>🚗 Добавить автомобиль</span>}
        open={showAddCar}
        onCancel={() => {
          setShowAddCar(false);
          setCarForm({ make: '', model: '', year: undefined, license_plate: '', color: '', notes: '' });
        }}
        footer={null}
        styles={{
          content: { backgroundColor: '#13161A', borderRadius: '24px', border: '1px solid rgba(255,255,255,0.06)' },
          mask: { backgroundColor: 'rgba(0,0,0,0.7)' },
        }}
      >
        <AntForm layout="vertical">
          <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Марка *</Text>}>
            <Input size="large" placeholder="Например: BMW" value={carForm.make}
              onChange={(e) => setCarForm(prev => ({ ...prev, make: e.target.value }))} />
          </AntForm.Item>
          <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Модель *</Text>}>
            <Input size="large" placeholder="Например: X5" value={carForm.model}
              onChange={(e) => setCarForm(prev => ({ ...prev, model: e.target.value }))} />
          </AntForm.Item>
          <Row gutter={16}>
            <Col xs={12}>
              <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Год</Text>}>
                <InputNumber size="large" placeholder="2024" value={carForm.year}
                  onChange={(val) => setCarForm(prev => ({ ...prev, year: val ?? undefined }))}
                  min={1990} max={2027} style={{ width: '100%' }} />
              </AntForm.Item>
            </Col>
            <Col xs={12}>
              <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Цвет</Text>}>
                <Input size="large" placeholder="Чёрный" value={carForm.color}
                  onChange={(e) => setCarForm(prev => ({ ...prev, color: e.target.value }))} />
              </AntForm.Item>
            </Col>
          </Row>
          <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Госномер</Text>}>
            <Input size="large" placeholder="А123БВ777" value={carForm.license_plate}
              onChange={(e) => setCarForm(prev => ({ ...prev, license_plate: e.target.value }))} />
          </AntForm.Item>
          <AntForm.Item label={<Text style={{ color: '#AAB2BF' }}>Заметки</Text>}>
            <TextArea rows={2} placeholder="Особые приметы, доп. информация..." value={carForm.notes}
              onChange={(e) => setCarForm(prev => ({ ...prev, notes: e.target.value }))}
              style={{ backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', borderRadius: '14px' }} />
          </AntForm.Item>
          <Button
            type="primary" size="large" onClick={handleAddCar} loading={carFormLoading}
            style={{
              width: '100%', borderRadius: '20px', height: '46px',
              backgroundColor: '#C8A977', borderColor: '#C8A977',
              color: '#0B0D10', fontWeight: 600, fontSize: '15px',
            }}
          >Сохранить</Button>
        </AntForm>
      </Modal>
    </Layout>
  );
}

/* ============================================================
   MAIN APP COMPONENT
   ============================================================ */
function App() {
  const [activeTab, setActiveTab] = useState('login');
  const [loading, setLoading] = useState(false);
  const [isAuthenticated, setIsAuthenticated] = useState(false);
  const [user, setUser] = useState<User | null>(null);

  const [registerPhone, setRegisterPhone] = useState('');
  const [registerPassword, setRegisterPassword] = useState('');
  const [registerName, setRegisterName] = useState('');

  const [loginPhone, setLoginPhone] = useState('');
  const [loginPassword, setLoginPassword] = useState('');

  useEffect(() => {
    const token = localStorage.getItem('token');
    if (token) fetchUser(token);
  }, []);

  const fetchUser = async (token: string) => {
    try {
      const response = await fetch(`${API_BASE}/api/me`, {
        headers: { Authorization: `Bearer ${token}` },
      });
      if (response.ok) {
        const data = await response.json();
        setUser(data);
        setIsAuthenticated(true);
      } else {
        localStorage.removeItem('token');
      }
    } catch {
      localStorage.removeItem('token');
    }
  };

  const handleRegister = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: registerPhone, password: registerPassword, full_name: registerName }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setIsAuthenticated(true);
        message.success(`👋 Добро пожаловать, ${data.user.full_name}!`);
        setRegisterPhone('');
        setRegisterPassword('');
        setRegisterName('');
      } else {
        message.error(data.detail || 'Ошибка регистрации');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const handleLogin = async () => {
    setLoading(true);
    try {
      const response = await fetch(`${API_BASE}/api/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ phone: loginPhone, password: loginPassword }),
      });
      const data = await response.json();
      if (response.ok) {
        localStorage.setItem('token', data.token);
        setUser(data.user);
        setIsAuthenticated(true);
        message.success(`👋 Добро пожаловать, ${data.user.full_name}!`);
      } else {
        message.error(data.detail || '❌ Неверный телефон или пароль');
      }
    } catch {
      message.error('❌ Ошибка соединения с сервером');
    }
    setLoading(false);
  };

  const handleLogout = () => {
    localStorage.removeItem('token');
    setIsAuthenticated(false);
    setUser(null);
    message.info('👋 Вы вышли из системы');
  };

  // ============================================================
  // AUTHENTICATED
  // ============================================================
  if (isAuthenticated && user) {
    if (user.role === 'client') {
      return <ClientDashboard user={user} onLogout={handleLogout} />;
    }

    // Master / Admin / Super Admin
    if (user.role === 'admin' || user.role === 'super_admin') {
      return <OwnerDashboard user={user} onLogout={handleLogout} />;
    }

    // Master
    if (user.role === 'master') {
      return <MasterDashboard user={user} onLogout={handleLogout} />;
    }
  }

  // ============================================================
  // NOT AUTHENTICATED — Login / Register
  // ============================================================
  return (
    <div style={{
      display: 'flex', justifyContent: 'center', alignItems: 'center',
      minHeight: '100vh', backgroundColor: '#0B0D10', padding: '16px',
    }}>
      <motion.div
        initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }} style={{ maxWidth: '400px', width: '100%' }}
      >
        <Card style={{
          backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)',
          borderRadius: '24px', padding: '24px 20px', boxShadow: '0 20px 60px rgba(0,0,0,0.6)',
        }}>
          <div style={{ textAlign: 'center', marginBottom: '4px' }}>
            <CarOutlined style={{ fontSize: '36px', color: '#C8A977' }} />
          </div>
          <Title level={1} style={{ color: '#C8A977', textAlign: 'center', marginBottom: '2px', fontSize: '26px', fontWeight: 700 }}>
            CarDetailing AI
          </Title>
          <Text style={{ color: '#AAB2BF', display: 'block', textAlign: 'center', marginBottom: '20px', fontSize: '13px' }}>
            🚀 Luxury Automotive Command Center
          </Text>

          <Tabs activeKey={activeTab} onChange={setActiveTab} centered style={{ marginBottom: '16px' }}
            tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)' }}
          >
            <TabPane tab={<span style={{ color: activeTab === 'login' ? '#C8A977' : '#AAB2BF', fontWeight: 500 }}>Вход</span>} key="login">
              <Input size="large" placeholder="Телефон (+7XXXXXXXXXX)" prefix={<PhoneOutlined style={{ color: '#AAB2BF' }} />}
                value={loginPhone} onChange={(e) => setLoginPhone(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input.Password size="large" placeholder="Пароль" prefix={<LockOutlined style={{ color: '#AAB2BF' }} />}
                value={loginPassword} onChange={(e) => setLoginPassword(e.target.value)} onPressEnter={handleLogin}
                style={{ marginBottom: '16px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Button type="primary" size="large" onClick={handleLogin} loading={loading}
                style={{ width: '100%', borderRadius: '20px', height: '46px', backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10', fontWeight: 600, fontSize: '15px', boxShadow: '0 20px 40px rgba(200,169,119,0.15)' }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#D5B98D'; e.currentTarget.style.boxShadow = '0 20px 50px rgba(200,169,119,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 20px 40px rgba(200,169,119,0.15)'; }}
              >▶ Войти</Button>
            </TabPane>

            <TabPane tab={<span style={{ color: activeTab === 'register' ? '#C8A977' : '#AAB2BF', fontWeight: 500 }}>Регистрация</span>} key="register">
              <Input size="large" placeholder="Полное имя" prefix={<UserOutlined style={{ color: '#AAB2BF' }} />}
                value={registerName} onChange={(e) => setRegisterName(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input size="large" placeholder="Телефон (+7XXXXXXXXXX)" prefix={<PhoneOutlined style={{ color: '#AAB2BF' }} />}
                value={registerPhone} onChange={(e) => setRegisterPhone(e.target.value)}
                style={{ marginBottom: '12px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />
              <Input.Password size="large" placeholder="Пароль" prefix={<LockOutlined style={{ color: '#AAB2BF' }} />}
                value={registerPassword} onChange={(e) => setRegisterPassword(e.target.value)}
                style={{ marginBottom: '16px', borderRadius: '14px', backgroundColor: '#1A1E23', borderColor: 'rgba(255,255,255,0.06)', color: '#FFFFFF', height: '46px' }}
                onFocus={(e) => { e.currentTarget.style.borderColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 0 0 3px rgba(200,169,119,0.1)'; }}
                onBlur={(e) => { e.currentTarget.style.borderColor = 'rgba(255,255,255,0.06)'; e.currentTarget.style.boxShadow = 'none'; }}
              />

              <div style={{ marginBottom: '14px' }}>
                <Text style={{ color: '#AAB2BF', fontSize: '13px', display: 'block', marginBottom: '8px' }}>Вы получите роль:</Text>
                <div className="role-selector">
                  <div className="role-btn role-btn-active">👤 Клиент</div>
                  <div className="role-btn" style={{ cursor: 'default' }}>🔧 Мастер</div>
                  <div className="role-btn" style={{ cursor: 'default' }}>👑 Владелец</div>
                </div>
                <Text style={{ color: '#AAB2BF', fontSize: '11px', display: 'block', marginTop: '6px', opacity: 0.6 }}>Роль назначается администратором</Text>
              </div>

              <Button type="primary" size="large" onClick={handleRegister} loading={loading}
                style={{ width: '100%', borderRadius: '20px', height: '46px', backgroundColor: '#C8A977', borderColor: '#C8A977', color: '#0B0D10', fontWeight: 600, fontSize: '15px', boxShadow: '0 20px 40px rgba(200,169,119,0.15)' }}
                onMouseEnter={(e) => { e.currentTarget.style.backgroundColor = '#D5B98D'; e.currentTarget.style.boxShadow = '0 20px 50px rgba(200,169,119,0.25)'; }}
                onMouseLeave={(e) => { e.currentTarget.style.backgroundColor = '#C8A977'; e.currentTarget.style.boxShadow = '0 20px 40px rgba(200,169,119,0.15)'; }}
              >🚀 Зарегистрироваться</Button>
            </TabPane>
          </Tabs>

          <div style={{ marginTop: '16px', display: 'flex', gap: '10px', justifyContent: 'center', flexWrap: 'wrap', padding: '12px', backgroundColor: '#1A1E23', borderRadius: '14px', border: '1px solid rgba(255,255,255,0.03)' }}>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><UserOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Клиент</span>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><ToolOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Мастер</span>
            <span style={{ color: '#AAB2BF', fontSize: '12px', display: 'flex', alignItems: 'center', gap: '4px' }}><CrownOutlined style={{ color: '#C8A977', fontSize: '11px' }} /> Владелец</span>
          </div>

          <div style={{ marginTop: '12px', textAlign: 'center' }}>
            <Text style={{ color: '#AAB2BF', fontSize: '10px', opacity: 0.5, letterSpacing: '0.5px' }}>
              CarDetailing AI v1.0 — AI-управляющий автомойкой
            </Text>
          </div>
        </Card>
      </motion.div>
    </div>
  );
}

export default App;
