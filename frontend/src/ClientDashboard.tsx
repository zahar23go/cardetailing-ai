import React, { useState, useEffect } from 'react';
import { Typography, Card, Input, Button, message, Tabs, Tag, Select,
  DatePicker, Form, InputNumber, Space, Spin, Empty, Modal, List } from 'antd';
import { CarOutlined, CalendarOutlined, ClockCircleOutlined,
  FileTextOutlined, PlusOutlined, HistoryOutlined, LogoutOutlined,
  BellOutlined, CrownOutlined, BulbOutlined, SendOutlined,
  CameraOutlined, GiftOutlined, HomeOutlined, SettingOutlined,
  UserOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import CarCard from './components/CarCard';
import PortfolioSection from './components/PortfolioSection';
import NotificationList from './components/NotificationList';
import NotificationSettings from './components/NotificationSettings';
import LoyaltyCard from './components/LoyaltyCard';

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

interface Service { id: number; name: string; description: string; price: number; duration: number; category?: string; }
interface Appointment { id: number; client_id: number; master_id: number | null; car_id: number; service_id: number; start_time: string; end_time: string; status: string; total_price: number; discount_applied: number; client_notes: string | null; master_brief: string | null; service_name: string | null; car?: { id: number; make: string; model: string; license_plate: string }; }
interface Car { id: number; client_id: number; make: string; model: string; year?: number; license_plate?: string; color?: string; notes?: string; }
interface User { id: number; phone: string; full_name: string; role: string; }

const API_BASE = '';
async function apiFetch<T>(path: string, options?: RequestInit): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, { ...options, headers: { 'Content-Type': 'application/json', ...(token ? { Authorization: `Bearer ${token}` } : {}), ...options?.headers } });
  if (!res.ok) { const body = await res.json().catch(() => ({})); throw new Error(body.detail || `Ошибка ${res.status}`); }
  return res.json();
}

export default function ClientDashboard({ user, onLogout }: { user: User; onLogout: () => void }) {
  const [activeTab, setActiveTab] = useState('overview');
  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [apptsLoading, setApptsLoading] = useState(false);
  const [apptsTotal, setApptsTotal] = useState(0);
  const [cars, setCars] = useState<Car[]>([]);
  const [carsLoading, setCarsLoading] = useState(false);
  const [showAddCar, setShowAddCar] = useState(false);
  const [carForm, setCarForm] = useState({ make: '', model: '', year: undefined as number | undefined, license_plate: '', color: '', notes: '' });
  const [carFormLoading, setCarFormLoading] = useState(false);
  const [editModal, setEditModal] = useState(false);
  const [editingAppt, setEditingAppt] = useState<Appointment | null>(null);
  const [consultantMessages, setConsultantMessages] = useState<{role: string; text: string}[]>([]);
  const [consultantInput, setConsultantInput] = useState('');
  const [consultantLoading, setConsultantLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);
  const [portfolioServices, setPortfolioServices] = useState<Service[]>([]);

  useEffect(() => { fetchServices(); fetchAppointments(); fetchCars(); }, []);

  const fetchServices = async () => {
    setServicesLoading(true);
    try { const d = await apiFetch<{items: Service[]; total: number}>('/api/services?skip=0&limit=100'); setServices(d.items); } catch {}
    setServicesLoading(false);
  };
  const fetchAppointments = async () => {
    setApptsLoading(true);
    try { const d = await apiFetch<{items: Appointment[]; total: number}>('/api/appointments/me?skip=0&limit=50'); setAppointments(d.items); setApptsTotal(d.total); } catch {}
    setApptsLoading(false);
  };
  const fetchCars = async () => {
    setCarsLoading(true);
    try { const d = await apiFetch<Car[]>('/api/cars'); setCars(Array.isArray(d) ? d : []); } catch {}
    setCarsLoading(false);
  };

  const nextAppt = appointments.filter(a => a.status !== 'cancelled' && a.status !== 'completed')
    .sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime())[0];
  const firstCar = Array.isArray(cars) && cars.length > 0 ? cars[0] : null;

  const handleNewDialog = () => { setConsultantMessages([]); setShowSuggestions(true); };
  const handleConsultantQuestion = async () => {
    const q = consultantInput.trim(); if (!q) return;
    setShowSuggestions(false); setConsultantMessages(p => [...p, { role: 'user', text: q }]);
    setConsultantInput(''); setConsultantLoading(true);
    try { const d = await apiFetch<{response: string}>('/api/ai/consultant', { method: 'POST', body: JSON.stringify({ question: q }) }); setConsultantMessages(p => [...p, { role: 'ai', text: d.response }]); }
    catch (e: any) { setConsultantMessages(p => [...p, { role: 'ai', text: `❌ ${e.message}` }]); }
    setConsultantLoading(false);
  };

  const renderOverview = () => (
    <div style={{ backgroundColor: '#000', minHeight: '100vh', fontFamily: "'Open Sans', sans-serif", color: '#fff', paddingBottom: 80 }}>
      {/* Header */}
      <div style={{ padding: '15px 20px', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 700, fontSize: 18, letterSpacing: 1 }}>CAR DETAILING AI</div>
        <div style={{ width: 40, height: 40, borderRadius: '50%', background: 'linear-gradient(135deg, #f0c14b, #e8b33a)', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 16 }}>👤</div>
      </div>

      {/* Car Card */}
      <div style={{ margin: '10px 20px', borderRadius: 15, overflow: 'hidden', boxShadow: '0 8px 25px rgba(0,0,0,0.6)', position: 'relative' }}>
        <img src="https://images.unsplash.com/photo-1607153333879-c174d265f1d2?ixlib=rb-4.0.3&auto=format&fit=crop&w=800&q=80" alt="BMW" style={{ width: '100%', height: 280, objectFit: 'cover', display: 'block' }} />
        <div style={{ position: 'absolute', bottom: 0, left: 0, right: 0, background: 'linear-gradient(to top, rgba(0,0,0,0.9), transparent)', padding: 20 }}>
          <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 700, fontSize: 22 }}>{firstCar ? `${firstCar.make} ${firstCar.model}` : 'BMW X5'}</div>
          <div style={{ fontSize: 14, color: '#aaa' }}>{firstCar?.year || '2023'} • {firstCar?.color || 'Черный металлик'}</div>
          <div style={{ display: 'inline-flex', alignItems: 'center', gap: 6, backgroundColor: 'rgba(39,174,96,0.2)', border: '1px solid rgba(39,174,96,0.4)', borderRadius: 20, padding: '6px 12px', marginTop: 10 }}>
            <div style={{ width: 6, height: 6, borderRadius: '50%', backgroundColor: '#27AE60' }} />
            <div style={{ fontSize: 12, color: '#27AE60', fontWeight: 500 }}>Автомобиль в идеальном состоянии</div>
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 15 }}>
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: '#f0c14b' }} />
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'rgba(240,193,75,0.4)' }} />
            <div style={{ width: 8, height: 8, borderRadius: '50%', backgroundColor: 'rgba(240,193,75,0.4)' }} />
          </div>
        </div>
      </div>

      {/* Service */}
      <div style={{ margin: 20, backgroundColor: '#111', borderRadius: 12, padding: '15px 20px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 15 }}>
          <div>
            <div style={{ fontSize: 14, color: '#aaa' }}>Завтра</div>
            <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 600, fontSize: 16, color: '#f0c14b' }}>15:00 — {nextAppt?.service_name || 'Комплексная мойка'} • Бокс №04</div>
          </div>
          {nextAppt && <button onClick={() => { setEditingAppt(nextAppt); setEditModal(true); }} style={{ background: 'none', border: 'none', color: '#f0c14b', fontSize: 14, cursor: 'pointer' }}>Изменить →</button>}
        </div>
        <button style={{ width: '100%', background: 'linear-gradient(135deg, #f0c14b, #e8b33a)', border: 'none', borderRadius: 25, padding: 18, fontFamily: "'Montserrat', sans-serif", fontWeight: 700, fontSize: 16, color: '#000', cursor: 'pointer', boxShadow: '0 4px 15px rgba(240,193,75,0.3)' }}>Записаться</button>
      </div>

      {/* AI Детейлер */}
      <div style={{ margin: 20 }}>
        <div style={{ fontFamily: "'Montserrat', sans-serif", fontWeight: 600, fontSize: 16, marginBottom: 5 }}>AI Детейлер</div>
        <div style={{ fontSize: 14, color: '#aaa', marginBottom: 15 }}>Что хотите сделать с автомобилем? Спросите AI или выберите услугу</div>
        <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 12 }}>
          {['🚿', '✨', '🛡️', '🧼'].map((icon, i) => (
            <div key={i} style={{ backgroundColor: '#111', border: '1px solid #222', borderRadius: 12, padding: '20px 15px', textAlign: 'center', cursor: 'pointer' }}>
              <div style={{ fontSize: 32, marginBottom: 10 }}>{icon}</div>
              <div style={{ fontSize: 14, fontWeight: 500 }}>{['Мойка','Полировка','Керамика','Химчистка'][i]}</div>
            </div>
          ))}
        </div>
      </div>

      {/* Быстрые действия */}
      <div style={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 10, margin: 20 }}>
        {[
          { icon: '📋', label: 'История услуг' },
          { icon: '🚗', label: 'Мои автомобили' },
          { icon: '🎁', label: 'Акции' },
          { icon: '💡', label: 'Рекомендации AI' },
        ].map((item, i) => (
          <div key={i} style={{ backgroundColor: '#111', borderRadius: 10, padding: 15, display: 'flex', alignItems: 'center', gap: 12 }}>
            <div style={{ width: 40, height: 40, background: 'linear-gradient(135deg, #f0c14b, #e8b33a)', borderRadius: '50%', display: 'flex', alignItems: 'center', justifyContent: 'center', fontSize: 18 }}>{item.icon}</div>
            <div style={{ fontSize: 14, fontWeight: 500 }}>{item.label}</div>
          </div>
        ))}
      </div>

      {/* Nav */}
      <div style={{ position: 'fixed', bottom: 0, left: 0, right: 0, backgroundColor: '#111', padding: '12px 0', display: 'flex', justifyContent: 'space-around', alignItems: 'center', maxWidth: 430, margin: '0 auto', boxShadow: '0 -4px 20px rgba(0,0,0,0.5)', zIndex: 100 }}>
        {[
          { icon: '🏠', label: 'Главная', key: 'overview' },
          { icon: '📅', label: 'Запись', key: 'services' },
          { icon: '⚡', label: 'Услуги', key: 'services' },
          { icon: '💬', label: 'AI', key: 'consultant' },
          { icon: '👤', label: 'Профиль', key: 'profile' },
        ].map((item, i) => (
          <button key={i} onClick={() => setActiveTab(item.key)} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', background: 'none', border: 'none', color: activeTab === item.key ? '#f0c14b' : '#666', fontSize: 12, cursor: 'pointer', fontFamily: "'Open Sans', sans-serif" }}>
            <div style={{ fontSize: 24, marginBottom: 4 }}>{item.icon}</div>
            <div style={{ fontSize: 11 }}>{item.label}</div>
          </button>
        ))}
      </div>
    </div>
  );

  return <div>{renderOverview()}</div>;
}
