import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import { useNavigate } from 'react-router-dom';
import {
  Typography, Card, Row, Col, Statistic, Table, Button, Tag, Space, Tabs, Divider,
  message, Modal, Select, Input, InputNumber, Popconfirm, Badge, Layout, List,
  Empty, Spin, Tooltip, DatePicker, TimePicker, Switch, ColorPicker,
} from 'antd';
import {
  CrownOutlined, ToolOutlined,
  CalendarOutlined, DollarOutlined, ClockCircleOutlined,
  TeamOutlined, DeleteOutlined, EditOutlined,
  PlusOutlined, LogoutOutlined, ReloadOutlined, PhoneOutlined,
  BulbOutlined, SendOutlined, AreaChartOutlined,
  GiftOutlined, StarOutlined, BellOutlined,
  BarChartOutlined, HomeOutlined, FileTextOutlined,
  CarOutlined, UserOutlined, SettingOutlined,
  CameraOutlined, CheckCircleOutlined, SearchOutlined,
  PlayCircleOutlined, CloseCircleOutlined,
} from '@ant-design/icons';
import NotificationBell from './components/NotificationBell';
import NotificationList from './components/NotificationList';
import NotificationSettings from './components/NotificationSettings';
import MasterCalendar from './components/MasterCalendar';
import ReportManager from './components/ReportManager';
import ServiceAnalytics from './components/ServiceAnalytics';
import DiscountIntelligence from './components/DiscountIntelligence';
import ServiceDiscountRecs from './components/ServiceDiscountRecs';
import ExpensesModule from './components/ExpensesModule';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, FunnelChart, Funnel, LabelList,
} from 'recharts';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import { useBrand } from './design';

dayjs.locale('ru');

const { Text } = Typography;
const { TabPane } = Tabs;
const { Header, Content, Sider } = Layout;
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
  cost_price?: number;
  margin_percent?: number;
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
  created_at?: string;
  updated_at?: string;
  client?: { id: number; full_name: string; phone: string };
  master?: { id: number; full_name: string };
  car?: { id: number; make: string; model: string; license_plate: string; vin?: string };
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

interface Expense {
  id: number;
  name: string;
  amount: number;
  category: string;
  expense_date: string;
  notes?: string;
  created_at: string;
}

interface ServiceMargin {
  service_id: number;
  service_name: string;
  category?: string;
  total_revenue: number;
  total_material_cost: number;
  gross_profit: number;
  margin_percent: number;
  appointment_count: number;
}

interface PLReport {
  total_revenue: number;
  completed_appointments: number;
  avg_check: number;
  total_material_cost: number;
  total_expenses: number;
  expenses_by_category: Record<string, number>;
  gross_profit: number;
  gross_margin_percent: number;
  net_profit: number;
  net_margin_percent: number;
  service_margins: ServiceMargin[];
  period: string;
}

interface RevenuePoint {
  date: string;
  revenue: number;
  appointments: number;
}

interface RevenueData {
  daily: RevenuePoint[];
  total: number;
  avg_per_day: number;
  best_day: string | null;
  worst_day: string | null;
  previous_total: number;
  change_percent: number;
  previous_avg_per_day: number;
}

interface HeatmapCell {
  day: number;
  hour: number;
  count: number;
  revenue: number;
  box_id?: number | null;
}

interface BoxItem {
  id: number;
  name: string;
  color?: string | null;
  sort_order: number;
  is_active: boolean;
  service_ids: number[];
}

interface FunnelStage {
  name: string;
  value: number;
  percent: number;
  color: string;
}

interface FunnelData {
  stages: FunnelStage[];
  total: number;
  conversion_rate: number;
}

interface RfmClient {
  id: number;
  full_name: string;
  phone: string;
  role?: string;  // masters loaded via /api/users have this
  recency_days: number;
  frequency: number;
  monetary: number;
  segment: string;
  last_visit: string | null;
  created_at: string | null;
}

interface SegmentCount {
  segment: string;
  count: number;
  total_revenue: number;
  percent: number;
}

interface RfmResponse {
  clients: RfmClient[];
  segments: SegmentCount[];
  total: number;
}

/* ---------- Discounts & Loyalty ---------- */
interface DiscountRule {
  id: number;
  name: string;
  type: string;
  conditions: Record<string, any>;
  discount_percent: number;
  slot_start: string | null;
  slot_end: string | null;
  service_id?: number;
  service_name?: string;
  client_id?: number;
  client_name?: string;
  valid_until?: string;
  is_active: boolean;
  created_at: string;
  updated_at: string;
}

interface DiscountAnalyticsTopRule {
  rule_id: number;
  rule_name: string;
  rule_type: string;
  times_used: number;
  total_discount: number;
  client_count: number;
}

interface DiscountAnalytics {
  total_rules: number;
  active_rules: number;
  total_times_used: number;
  total_discount_amount: number;
  unique_clients_affected: number;
  top_rules: DiscountAnalyticsTopRule[];
}

interface LoyaltyClient {
  client_id: number;
  full_name: string;
  phone: string;
  balance: number;
  total_earned: number;
  total_spent: number;
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

const APPT_ACTIVE_STATUSES = ['pending', 'confirmed', 'in_progress'];
const APPT_FETCH_LIMIT = 500;
const APPT_LIST_PAGE_SIZE = 10;

function formatStatusAge(appt: Appointment): string {
  const from = appt.updated_at || appt.created_at || appt.start_time;
  const mins = Math.max(0, dayjs().diff(dayjs(from), 'minute'));
  if (mins < 60) return `${mins} мин`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ч`;
  return `${Math.floor(hours / 24)} д`;
}

const COLOR_MAP: Record<string, string> = {
  'красный': '#FF6B6B',
  'синий': '#4DABF7',
  'зелёный': '#4ECB71',
  'зеленый': '#4ECB71',
  'жёлтый': '#FFD93D',
  'желтый': '#FFD93D',
  'оранжевый': '#FF9F43',
  'фиолетовый': '#A66CFF',
  'розовый': '#FF6B9D',
  'серый': '#95A5A6',
  'чёрный': '#2D3436',
  'черный': '#2D3436',
  'белый': '#FFFFFF',
};

function normalizeColor(color: string | null | undefined): string | null {
  if (!color) return null;
  const trimmed = color.trim();
  if (!trimmed) return null;
  // Если это уже hex-код, возвращаем как есть
  if (/^#[0-9A-Fa-f]{3,8}$/.test(trimmed)) return trimmed;
  // Иначе ищем в маппинге русских названий
  return COLOR_MAP[trimmed.toLowerCase()] || trimmed;
}

function hexToRgb(hex: string): string {
  return hexToRgbArray(hex).join(', ');
}

function hexToRgbArray(hex: string): number[] {
  const clean = hex.replace('#', '');
  if (clean.length === 3) {
    return [
      parseInt(clean[0] + clean[0], 16),
      parseInt(clean[1] + clean[1], 16),
      parseInt(clean[2] + clean[2], 16),
    ];
  }
  return [
    parseInt(clean.substring(0, 2), 16),
    parseInt(clean.substring(2, 4), 16),
    parseInt(clean.substring(4, 6), 16),
  ];
}

function isLightColor(color: string | null | undefined): boolean {
  if (!color) return false;
  try {
    const [r, g, b] = hexToRgbArray(color);
    // Яркость по формуле WCAG: (0.299*R + 0.587*G + 0.114*B)
    const brightness = 0.299 * r + 0.587 * g + 0.114 * b;
    return brightness > 180;
  } catch {
    return false;
  }
}

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
  const navigate = useNavigate();
  const { brand } = useBrand();
  const [activeTab, setActiveTab] = useState('overview');

  const [kpi, setKpi] = useState<KpiData | null>(null);
  const [kpiLoading, setKpiLoading] = useState(false);

  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [apptsLoading, setApptsLoading] = useState(false);
  const [apptsTotal, setApptsTotal] = useState(0);
  const [apptsPage, setApptsPage] = useState(1);
  const [apptStatusFilter, setApptStatusFilter] = useState<string>('all');
  const [apptMasterFilter, setApptMasterFilter] = useState<number | 'all'>('all');
  const [apptPeriodFilter, setApptPeriodFilter] = useState<string>('all');
  const [apptCustomRange, setApptCustomRange] = useState<[dayjs.Dayjs, dayjs.Dayjs] | null>(null);
  const [apptSearchClient, setApptSearchClient] = useState('');
  const [apptSearchCar, setApptSearchCar] = useState('');
  const [apptSort, setApptSort] = useState<string>('active_first');

  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [servicesTotal, setServicesTotal] = useState(0);
  const [servicesPage, setServicesPage] = useState(1);
  const [allServices, setAllServices] = useState<Service[]>([]);

  const [users, setUsers] = useState<RfmClient[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [userRoleTab, setUserRoleTab] = useState<string>('clients');

  // Modals
  const [serviceModal, setServiceModal] = useState(false);
  const [editingService, setEditingService] = useState<Service | null>(null);
  const [serviceForm, setServiceForm] = useState({
    name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0, cost_price: 0,
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
  const [clientPoints, setClientPoints] = useState<{
    balance: number;
    total_earned: number;
    total_spent: number;
  } | null>(null);

  // Financier chat state
  const [financierMessages, setFinancierMessages] = useState<{role: 'user' | 'ai'; text: string}[]>([]);
  const [financierInput, setFinancierInput] = useState('');
  const [financierLoading, setFinancierLoading] = useState(false);
  const [showSuggestions, setShowSuggestions] = useState(true);

  // Expenses state
  const [expenses, setExpenses] = useState<Expense[]>([]);
  const [expensesLoading, setExpensesLoading] = useState(false);
  const [expensesTotal, setExpensesTotal] = useState(0);
  const [expensesPage, setExpensesPage] = useState(1);
  const [plReport, setPlReport] = useState<PLReport | null>(null);
  const [plLoading, setPlLoading] = useState(false);
  const [expenseModal, setExpenseModal] = useState(false);
  const [expenseForm, setExpenseForm] = useState({ name: '', amount: 0, category: 'other', notes: '' });
  const [expenseSaving, setExpenseSaving] = useState(false);

  // RFM state
  const [rfmData, setRfmData] = useState<RfmResponse | null>(null);
  const [rfmLoading, setRfmLoading] = useState(false);
  const [segmentFilter, setSegmentFilter] = useState<string>('');

  // Discounts & Loyalty state
  const [discountRules, setDiscountRules] = useState<DiscountRule[]>([]);
  const [discountsLoading, setDiscountsLoading] = useState(false);
  const [discountAnalytics, setDiscountAnalytics] = useState<DiscountAnalytics | null>(null);
  const [discountModal, setDiscountModal] = useState(false);
  const [editingDiscount, setEditingDiscount] = useState<DiscountRule | null>(null);
  const [discountForm, setDiscountForm] = useState({
    name: '', type: 'happy_hours',
    discount_percent: 0, slot_start: '', slot_end: '',
    service_id: undefined as number | undefined,
    client_id: undefined as number | undefined,
    valid_until: '',
    is_active: true,
    // Поля конструктора условий
    minVisits: 3,
    maxRecencyDays: 60,
    pointsPercent: 5,
    segment: undefined as string | undefined,
  });
  const [discountSaving, setDiscountSaving] = useState(false);

  const [loyaltyClients, setLoyaltyClients] = useState<LoyaltyClient[]>([]);
  const [loyaltyLoading, setLoyaltyLoading] = useState(false);

  // Chart data state
  const [revenueData, setRevenueData] = useState<RevenueData | null>(null);
  const [revenueLoading, setRevenueLoading] = useState(false);
  const [heatmapData, setHeatmapData] = useState<HeatmapCell[]>([]);
  const [heatmapLoading, setHeatmapLoading] = useState(false);
  const [boxes, setBoxes] = useState<BoxItem[]>([]);
  const [selectedBoxId, setSelectedBoxId] = useState<number | undefined>(undefined);
  const [funnelData, setFunnelData] = useState<FunnelData | null>(null);
  const [funnelLoading, setFunnelLoading] = useState(false);
  const [boxSettingsModal, setBoxSettingsModal] = useState(false);
  const [boxesFull, setBoxesFull] = useState<any[]>([]);
  const [boxSettingsSaving, setBoxSettingsSaving] = useState(false);
  const [boxEditServices, setBoxEditServices] = useState<Record<number, number[]>>({});
  const [newBoxName, setNewBoxName] = useState('');
  const [newBoxColor, setNewBoxColor] = useState('');
  const [creatingBox, setCreatingBox] = useState(false);
  const [editingBox, setEditingBox] = useState<any>(null);
  const [editBoxModalOpen, setEditBoxModalOpen] = useState(false);

  // Heatmap cell click state
  const [heatmapModalOpen, setHeatmapModalOpen] = useState(false);
  const [heatmapSlotAppts, setHeatmapSlotAppts] = useState<Appointment[]>([]);
  const [heatmapSlotLabel, setHeatmapSlotLabel] = useState('');

  // Period selector state
  const [periodStart, setPeriodStart] = useState<string | null>(null);
  const [periodEnd, setPeriodEnd] = useState<string | null>(null);

  // Fetch all data
  useEffect(() => {
    fetchKpi();
    fetchAppointments();
    fetchServices();
    fetchAllServices();
    fetchUsers();
    fetchAllUsers();
    fetchExpenses();
    fetchPL();
    fetchRevenueChart();
    fetchBoxes();
    fetchBoxesFull();
    fetchHeatmap();
    fetchFunnel();
    fetchRFM();
    fetchDiscounts();
    fetchLoyalty();
  }, []);

  const fetchKpi = async () => {
    setKpiLoading(true);
    try {
      const data = await apiFetch<KpiData>('/api/analytics/kpi');
      setKpi(data);
    } catch { /* ignore */ }
    setKpiLoading(false);
  };

  const PAGE_SIZE = 20;

  const fetchAppointments = async (_page = 1) => {
    setApptsLoading(true);
    try {
      const data = await apiFetch<{ items: Appointment[]; total: number }>(
        `/api/appointments?skip=0&limit=${APPT_FETCH_LIMIT}`,
      );
      setAppointments(data.items);
      setApptsTotal(data.total);
      setApptsPage(1);
    } catch { message.error('Ошибка загрузки записей'); }
    setApptsLoading(false);
  };

  const fetchServices = async (page = servicesPage) => {
    setServicesLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data = await apiFetch<{items: Service[]; total: number}>(`/api/services?skip=${skip}&limit=${PAGE_SIZE}`);
      setServices(data.items);
      setServicesTotal(data.total);
      setServicesPage(page);
    } catch { message.error('Ошибка загрузки услуг'); }
    setServicesLoading(false);
  };

  const fetchAllServices = async () => {
    try {
      const data = await apiFetch<{items: Service[]; total: number}>(`/api/services?skip=0&limit=500`);
      setAllServices(data.items);
    } catch { /* ignore */ }
  };

  const fetchUsers = async () => {
    setUsersLoading(true);
    try {
      const data = await apiFetch<RfmResponse>('/api/users/segments');
      setUsers(data.clients);
    } catch { message.error('Ошибка загрузки пользователей'); }
    setUsersLoading(false);
  };

  const fetchAllUsers = async () => {
    try {
      const data = await apiFetch<{items: User[]; total: number}>('/api/users?limit=500');
      setAllUsers(data.items);
    } catch { /* ignore */ }
  };

  /* ---------- Expenses & P&L ---------- */
  const fetchExpenses = async (page = expensesPage) => {
    setExpensesLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data = await apiFetch<{items: Expense[]; total: number}>(`/api/expenses?skip=${skip}&limit=${PAGE_SIZE}`);
      setExpenses(data.items);
      setExpensesTotal(data.total);
      setExpensesPage(page);
    } catch { /* ignore */ }
    setExpensesLoading(false);
  };

  const fetchPL = async () => {
    setPlLoading(true);
    try {
      const data = await apiFetch<PLReport>('/api/analytics/pl');
      setPlReport(data);
    } catch { /* ignore */ }
    setPlLoading(false);
  };

  /* ---------- Analytics Charts ---------- */
  const fetchRevenueChart = async (start?: string, end?: string) => {
    setRevenueLoading(true);
    try {
      let path = '/api/analytics/revenue';
      const params = new URLSearchParams();
      params.set('_t', String(Date.now())); // cache-busting
      if (start && end) {
        params.set('start_date', start);
        params.set('end_date', end);
      }
      path += '?' + params.toString();
      const data = await apiFetch<RevenueData>(path);
      setRevenueData(data);
    } catch { /* ignore */ }
    setRevenueLoading(false);
  };

  const fetchHeatmap = async (boxId?: number) => {
    setHeatmapLoading(true);
    try {
      let path = '/api/analytics/heatmap?days=60';
      if (boxId !== undefined) {
        path += `&box_id=${boxId}`;
      }
      const data = await apiFetch<{cells: HeatmapCell[]; boxes: BoxItem[]}>(path);
      setHeatmapData(data.cells);
      if (data.boxes) setBoxes(data.boxes);
    } catch { /* ignore */ }
    setHeatmapLoading(false);
  };

  const fetchBoxes = async () => {
    try {
      const data = await apiFetch<any[]>('/api/boxes');
      setBoxes(data.map((b: any) => ({ id: b.id, name: b.name, color: b.color, sort_order: b.sort_order, is_active: b.is_active, service_ids: b.service_ids || [] })));
    } catch { /* ignore */ }
  };

  const fetchBoxesFull = async () => {
    try {
      const data = await apiFetch<any[]>('/api/boxes');
      setBoxesFull(data);
    } catch {
      message.error('Ошибка загрузки боксов');
    }
  };

  const handleSaveBoxSettings = async (boxId: number, serviceIds: number[]) => {
    setBoxSettingsSaving(true);
    try {
      await apiFetch(`/api/boxes/${boxId}`, {
        method: 'PUT',
        body: JSON.stringify({ service_ids: serviceIds }),
      });
      message.success('Настройки бокса сохранены');
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setBoxSettingsSaving(false);
  };

  const handleCreateBox = async () => {
    if (!newBoxName.trim()) { message.warning('Укажите название бокса'); return; }
    setCreatingBox(true);
    try {
      await apiFetch('/api/boxes', {
        method: 'POST',
        body: JSON.stringify({
          name: newBoxName.trim(),
          color: normalizeColor(newBoxColor),
          sort_order: boxesFull.length,
          is_active: true,
        }),
      });
      message.success('✅ Бокс создан');
      setNewBoxName('');
      setNewBoxColor('');
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка создания бокса');
    }
    setCreatingBox(false);
  };

  const handleDeleteBox = async (boxId: number, boxName: string) => {
    try {
      await apiFetch(`/api/boxes/${boxId}`, { method: 'DELETE' });
      message.success(`✅ Бокс «${boxName}» удалён`);
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления бокса');
    }
  };

  const openEditBoxModal = (box: any) => {
    setEditingBox(box);
    // Инициализируем услуги из данных бокса (приходят с API)
    setBoxEditServices(prev => ({ ...prev, [box.id]: box.service_ids || [] }));
    setEditBoxModalOpen(true);
  };

  const handleEditBox = async () => {
    if (!editingBox) return;
    if (!editingBox.name?.trim()) { message.warning('Укажите название бокса'); return; }
    setBoxSettingsSaving(true);
    try {
      await apiFetch(`/api/boxes/${editingBox.id}`, {
        method: 'PUT',
        body: JSON.stringify({
          name: editingBox.name.trim(),
          color: normalizeColor(editingBox.color),
          service_ids: boxEditServices[editingBox.id] || [],
        }),
      });
      message.success('✅ Бокс обновлён');
      setEditBoxModalOpen(false);
      setEditingBox(null);
      fetchBoxes();
      fetchBoxesFull();
      fetchHeatmap(selectedBoxId);
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления бокса');
    }
    setBoxSettingsSaving(false);
  };

  const handleHeatmapCellClick = (day: number, hour: number) => {
    const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
    const cell = heatmapData.find(c => c.day === day && c.hour === hour);
    const count = cell?.count || 0;
    setHeatmapSlotLabel(`${dayNames[day]} ${hour}:00 (${count} зап.)`);

    // Фильтруем appointments по дню недели и часу
    const filtered = appointments.filter(a => {
      const start = new Date(a.start_time);
      return start.getDay() === day && start.getHours() === hour;
    });
    // Сортируем по времени
    filtered.sort((a, b) => new Date(a.start_time).getTime() - new Date(b.start_time).getTime());
    setHeatmapSlotAppts(filtered);
    setHeatmapModalOpen(true);
  };

  const fetchFunnel = async (start?: string, end?: string) => {
    setFunnelLoading(true);
    try {
      let path = '/api/analytics/funnel';
      const params = new URLSearchParams();
      params.set('_t', String(Date.now())); // cache-busting
      if (start && end) {
        params.set('start_date', start);
        params.set('end_date', end);
      }
      path += '?' + params.toString();
      const data = await apiFetch<FunnelData>(path);
      setFunnelData(data);
    } catch { /* ignore */ }
    setFunnelLoading(false);
  };

  /* ---------- RFM Segmentation ---------- */
  const fetchRFM = async (segment?: string) => {
    setRfmLoading(true);
    try {
      const path = segment ? `/api/users/segments?segment=${segment}` : '/api/users/segments';
      const data = await apiFetch<RfmResponse>(path);
      setRfmData(data);
    } catch { /* ignore */ }
    setRfmLoading(false);
  };

  const handleSegmentFilter = (value: string) => {
    setSegmentFilter(value);
    fetchRFM(value || '');
  };

  /* ---------- Discounts & Loyalty ---------- */
  const fetchDiscounts = async () => {
    setDiscountsLoading(true);
    try {
      const data = await apiFetch<{items: DiscountRule[]; total: number}>('/api/discounts?skip=0&limit=100');
      setDiscountRules(data.items);
    } catch { /* ignore */ }
    try {
      const analytics = await apiFetch<DiscountAnalytics>('/api/analytics/discounts');
      setDiscountAnalytics(analytics);
    } catch { /* ignore */ }
    setDiscountsLoading(false);
  };

  const fetchLoyalty = async () => {
    setLoyaltyLoading(true);
    try {
      const data = await apiFetch<{items: LoyaltyClient[]; total: number}>('/api/loyalty/points?skip=0&limit=100');
      setLoyaltyClients(data.items);
    } catch { /* ignore */ }
    setLoyaltyLoading(false);
  };

  const fetchDiscountAnalytics = async () => {
    try {
      const data = await apiFetch<DiscountAnalytics>('/api/analytics/discounts');
      setDiscountAnalytics(data);
    } catch { /* ignore */ }
  };

  const openDiscountModal = (rule?: DiscountRule) => {
    if (rule) {
      setEditingDiscount(rule);
      const cond = rule.conditions || {};
      setDiscountForm({
        name: rule.name,
        type: rule.type,
        discount_percent: rule.discount_percent,
        slot_start: rule.slot_start || '',
        slot_end: rule.slot_end || '',
        service_id: rule.service_id || undefined,
        client_id: rule.client_id || undefined,
        valid_until: rule.valid_until || '',
        is_active: rule.is_active,
        minVisits: cond.min_visits || 3,
        maxRecencyDays: cond.max_recency_days || 60,
        pointsPercent: cond.points_percent || 5,
        segment: cond.segment || undefined,
      });
    } else {
      setEditingDiscount(null);
      setDiscountForm({
        name: '', type: 'happy_hours',
        discount_percent: 0, slot_start: '', slot_end: '',
        service_id: undefined,
        client_id: undefined,
        valid_until: '',
        is_active: true,
        minVisits: 3,
        maxRecencyDays: 60,
        pointsPercent: 5,
        segment: undefined,
      });
    }
    setDiscountModal(true);
  };

  const handleSaveDiscount = async () => {
    if (!discountForm.name.trim()) { message.warning('Укажите название правила'); return; }
    if (!discountForm.discount_percent) { message.warning('Укажите процент скидки'); return; }
    setDiscountSaving(true);
    try {
      // Собираем conditions из полей конструктора в зависимости от типа
      let conditions: Record<string, any> = {};
      if (discountForm.type === 'happy_hours') {
        conditions.hour_start = discountForm.slot_start;
        conditions.hour_end = discountForm.slot_end;
      } else if (discountForm.type === 'frequency') {
        conditions.min_visits = discountForm.minVisits;
      } else if (discountForm.type === 'win_back') {
        conditions.max_recency_days = discountForm.maxRecencyDays;
      } else if (discountForm.type === 'cashback') {
        conditions.points_percent = discountForm.pointsPercent;
      } else if (discountForm.type === 'segment') {
        conditions.segment = discountForm.segment;
      } else if (discountForm.type === 'service') {
        // service_id передаётся отдельным полем
      } else if (discountForm.type === 'client') {
        // client_id передаётся отдельным полем
      }
      const body = {
        name: discountForm.name,
        type: discountForm.type,
        conditions,
        discount_percent: discountForm.discount_percent,
        slot_start: discountForm.slot_start || null,
        slot_end: discountForm.slot_end || null,
        service_id: discountForm.service_id || null,
        client_id: discountForm.client_id || null,
        valid_until: discountForm.valid_until || null,
        is_active: discountForm.is_active,
      };
      if (editingDiscount) {
        await apiFetch(`/api/discounts/${editingDiscount.id}`, {
          method: 'PUT',
          body: JSON.stringify(body),
        });
        message.success('Правило скидки обновлено');
      } else {
        await apiFetch('/api/discounts', {
          method: 'POST',
          body: JSON.stringify(body),
        });
        message.success('Правило скидки создано');
      }
      setDiscountModal(false);
      fetchDiscounts();
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setDiscountSaving(false);
  };

  const handleDeleteDiscount = async (id: number, name: string) => {
    try {
      await apiFetch(`/api/discounts/${id}`, { method: 'DELETE' });
      message.success(`Правило «${name}» удалено`);
      fetchDiscounts();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления');
    }
  };

  const createDiscountFromSuggestion = async (s: {
    name: string;
    hour_start: string;
    hour_end: string;
    weekdays: number[];
    discount_percent: number;
  }) => {
    await apiFetch('/api/discounts', {
      method: 'POST',
      body: JSON.stringify({
        name: s.name,
        type: 'happy_hours',
        conditions: {
          hour_start: s.hour_start,
          hour_end: s.hour_end,
          weekdays: s.weekdays,
        },
        discount_percent: s.discount_percent,
        slot_start: s.hour_start,
        slot_end: s.hour_end,
        is_active: true,
      }),
    });
    fetchDiscounts();
  };

  const DISCOUNT_TYPE_LABELS: Record<string, string> = {
    happy_hours: 'Happy Hours',
    service: 'На услугу',
    client: 'Персональная',
    segment: 'По сегменту',
    frequency: 'За частоту',
    win_back: 'Возврат',
    cashback: 'Кэшбек',
  };

  const DISCOUNT_TYPE_COLORS: Record<string, string> = {
    happy_hours: 'blue',
    service: 'gold',
    client: 'purple',
    segment: 'cyan',
    frequency: 'green',
    win_back: 'orange',
    cashback: 'purple',
  };

  const handleAddExpense = async () => {
    if (!expenseForm.name.trim()) { message.warning('Укажите название расхода'); return; }
    if (!expenseForm.amount) { message.warning('Укажите сумму'); return; }
    setExpenseSaving(true);
    try {
      await apiFetch('/api/expenses', {
        method: 'POST',
        body: JSON.stringify(expenseForm),
      });
      message.success('Расход добавлен');
      setExpenseModal(false);
      setExpenseForm({ name: '', amount: 0, category: 'other', notes: '' });
      fetchExpenses();
      fetchPL();
    } catch (e: any) {
      message.error(e.message || 'Ошибка добавления расхода');
    }
    setExpenseSaving(false);
  };

  const handleDeleteExpense = async (id: number, name: string) => {
    try {
      await apiFetch(`/api/expenses/${id}`, { method: 'DELETE' });
      message.success(`Расход «${name}» удалён`);
      fetchExpenses();
      fetchPL();
    } catch (e: any) {
      message.error(e.message || 'Ошибка удаления');
    }
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
        cost_price: service.cost_price ?? service.material_cost ?? 0,
      });
    } else {
      setEditingService(null);
      setServiceForm({ name: '', description: '', category: '', price: 0, duration: 60, material_cost: 0, cost_price: 0 });
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
      fetchAllUsers();
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

  const quickUpdateApptStatus = async (appt: Appointment, status: string) => {
    try {
      await apiFetch(`/api/appointments/${appt.id}`, {
        method: 'PUT',
        body: JSON.stringify({ status }),
      });
      message.success(`Статус: ${STATUS_LABELS[status] || status}`);
      fetchAppointments();
    } catch (e: any) {
      message.error(e.message || 'Ошибка обновления статуса');
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
    setClientPoints(null);
    try {
      const [data, pointsData] = await Promise.all([
        apiFetch<any>(`/api/users/${clientId}`),
        apiFetch<{items: {balance: number; total_earned: number; total_spent: number}[]}>(`/api/loyalty/points?client_id=${clientId}`),
      ]);
      setClientDetail(data);
      if (pointsData.items && pointsData.items.length > 0) {
        setClientPoints(pointsData.items[0]);
      }
    } catch {
      message.error('Ошибка загрузки данных клиента');
      setClientModal(false);
    }
    setClientLoading(false);
  };

  /* ---------- Financier AI ---------- */
  const handleNewDialog = () => {
    setFinancierMessages([]);
    setShowSuggestions(true);
  };

  const handleFinancierQuestion = async () => {
    const question = financierInput.trim();
    if (!question) return;
    setShowSuggestions(false);
    setFinancierMessages(prev => [...prev, { role: 'user', text: question }]);
    setFinancierInput('');
    setFinancierLoading(true);
    try {
      const data = await apiFetch<{response: string}>('/api/ai/financier', {
        method: 'POST',
        body: JSON.stringify({ question }),
      });
      setFinancierMessages(prev => [...prev, { role: 'ai', text: data.response }]);
    } catch (e: any) {
      setFinancierMessages(prev => [...prev, { role: 'ai', text: `❌ ${e.message || 'Ошибка соединения'}` }]);
    }
    setFinancierLoading(false);
  };

  /* ============================================================
     RENDER
     ============================================================ */
  const formatCurrency = (val: number) => `${val.toLocaleString()} ₽`;

  const pendingList = useMemo(
    () => appointments.filter((a) => a.status === 'pending' || a.status === 'confirmed').slice(0, 5),
    [appointments],
  );

  const apptStats = useMemo(() => {
    const weekStart = dayjs().startOf('week');
    return {
      total: apptsTotal || appointments.length,
      in_progress: appointments.filter((a) => a.status === 'in_progress').length,
      waiting: appointments.filter((a) => a.status === 'pending' || a.status === 'confirmed').length,
      completed_week: appointments.filter(
        (a) => a.status === 'completed' && !dayjs(a.start_time).isBefore(weekStart),
      ).length,
      cancelled: appointments.filter((a) => a.status === 'cancelled').length,
    };
  }, [appointments, apptsTotal]);

  const filteredAppointments = useMemo(() => {
    let list = [...appointments];

    if (apptStatusFilter === 'active') {
      list = list.filter((a) => APPT_ACTIVE_STATUSES.includes(a.status));
    } else if (apptStatusFilter === 'completed') {
      list = list.filter((a) => a.status === 'completed');
    } else if (apptStatusFilter === 'cancelled') {
      list = list.filter((a) => a.status === 'cancelled' || a.status === 'no_show');
    } else if (apptStatusFilter !== 'all') {
      list = list.filter((a) => a.status === apptStatusFilter);
    }

    if (apptMasterFilter !== 'all') {
      list = list.filter((a) => a.master_id === apptMasterFilter);
    }

    if (apptPeriodFilter === 'today') {
      list = list.filter((a) => dayjs(a.start_time).isSame(dayjs(), 'day'));
    } else if (apptPeriodFilter === 'week') {
      const start = dayjs().startOf('week');
      const end = dayjs().endOf('week');
      list = list.filter((a) => {
        const t = dayjs(a.start_time);
        return !t.isBefore(start) && !t.isAfter(end);
      });
    } else if (apptPeriodFilter === 'month') {
      list = list.filter((a) => dayjs(a.start_time).isSame(dayjs(), 'month'));
    } else if (apptPeriodFilter === 'custom' && apptCustomRange) {
      const [from, to] = apptCustomRange;
      list = list.filter((a) => {
        const t = dayjs(a.start_time);
        return !t.isBefore(from.startOf('day')) && !t.isAfter(to.endOf('day'));
      });
    }

    const clientQ = apptSearchClient.trim().toLowerCase();
    if (clientQ) {
      list = list.filter((a) => {
        const name = (a.client?.full_name || '').toLowerCase();
        const phone = (a.client?.phone || '').toLowerCase();
        return name.includes(clientQ) || phone.includes(clientQ);
      });
    }

    const carQ = apptSearchCar.trim().toLowerCase();
    if (carQ) {
      list = list.filter((a) => {
        const plate = (a.car?.license_plate || '').toLowerCase();
        const make = (a.car?.make || '').toLowerCase();
        const model = (a.car?.model || '').toLowerCase();
        const vin = (a.car?.vin || '').toLowerCase();
        return plate.includes(carQ) || make.includes(carQ) || model.includes(carQ) || vin.includes(carQ);
      });
    }

    list.sort((a, b) => {
      if (apptSort === 'date_asc') {
        return dayjs(a.start_time).valueOf() - dayjs(b.start_time).valueOf();
      }
      if (apptSort === 'date_desc') {
        return dayjs(b.start_time).valueOf() - dayjs(a.start_time).valueOf();
      }
      if (apptSort === 'master') {
        const an = a.master?.full_name || 'яяя';
        const bn = b.master?.full_name || 'яяя';
        const cmp = an.localeCompare(bn, 'ru');
        if (cmp !== 0) return cmp;
        return dayjs(b.start_time).valueOf() - dayjs(a.start_time).valueOf();
      }
      // active_first (default)
      const aActive = APPT_ACTIVE_STATUSES.includes(a.status) ? 0 : 1;
      const bActive = APPT_ACTIVE_STATUSES.includes(b.status) ? 0 : 1;
      if (aActive !== bActive) return aActive - bActive;
      return dayjs(b.start_time).valueOf() - dayjs(a.start_time).valueOf();
    });

    return list;
  }, [
    appointments,
    apptStatusFilter,
    apptMasterFilter,
    apptPeriodFilter,
    apptCustomRange,
    apptSearchClient,
    apptSearchCar,
    apptSort,
  ]);

  const pagedAppointments = useMemo(() => {
    const start = (apptsPage - 1) * APPT_LIST_PAGE_SIZE;
    return filteredAppointments.slice(start, start + APPT_LIST_PAGE_SIZE);
  }, [filteredAppointments, apptsPage]);

  const mastersForFilter = useMemo(
    () => allUsers.filter((u) => u.role === 'master'),
    [allUsers],
  );

  // sidebar items
  const sidebarItems = [
    { key: 'overview', icon: <HomeOutlined />, label: 'Обзор' },
    { key: 'appointments', icon: <FileTextOutlined />, label: 'Записи' },
    { key: 'calendar', icon: <CalendarOutlined />, label: 'Календарь' },
    { key: 'users', icon: <TeamOutlined />, label: 'Пользователи' },
    { key: 'services', icon: <SettingOutlined />, label: 'Услуги' },
    { key: 'financier', icon: <BulbOutlined />, label: 'AI Финансист' },
    { key: 'finances', icon: <DollarOutlined />, label: 'Финансы' },
    { key: 'analytics', icon: <AreaChartOutlined />, label: 'Аналитика' },
    { key: 'discounts', icon: <GiftOutlined />, label: 'Скидки' },
    { key: 'reports', icon: <BarChartOutlined />, label: 'Отчёты' },
    { key: 'notifications', icon: <BellOutlined />, label: 'Уведомления' },
  ];

  const bottomNavItems = [
    { key: 'overview', icon: <HomeOutlined />, label: 'Обзор' },
    { key: 'appointments', icon: <FileTextOutlined />, label: 'Записи' },
    { key: 'services', icon: <SettingOutlined />, label: 'Услуги' },
    { key: 'finances', icon: <DollarOutlined />, label: 'Финансы' },
    { key: 'users', icon: <TeamOutlined />, label: 'Люди' },
  ];

  const refreshOverview = () => {
    fetchKpi();
    fetchAppointments(1);
  };

  return (
    <Layout className="admin-layout client-layout">
      {/* Мобильный хедер */}
      <Header className="header-mobile admin-header-mobile">
        <Text className="admin-header-title">CAR DETAILING AI</Text>
        <span className="admin-header-badge">Command Center</span>
      </Header>

      {/* Десктоп хедер */}
      <Header className="header-desktop admin-header">
        <Space className="admin-header-brand" size="middle" align="center">
          <CrownOutlined className="admin-header-crown" />
          <Text className="admin-header-title">CarDetailing AI</Text>
          <span className="admin-header-badge">Command Center</span>
        </Space>
        <Space size="middle" className="admin-header-actions" wrap>
          <Button
            type="text"
            className="admin-header-btn"
            onClick={() => navigate('/branding')}
          >
            Брендинг
          </Button>
          <span className="admin-header-user">
            <CrownOutlined />
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

      <Layout>
        {/* Сайдбар (десктоп) */}
        <Sider
          className="sidebar admin-sidebar"
          breakpoint="md"
          collapsedWidth={0}
          width={228}
          trigger={null}
        >
          {sidebarItems.map(item => (
            <button
              key={item.key}
              className={`sidebar-item${activeTab === item.key ? ' active' : ''}`}
              onClick={() => { setActiveTab(item.key); }}
            >
              <span className="sidebar-icon">{item.icon}</span>
              <span>{item.label}</span>
            </button>
          ))}
        </Sider>

        {/* CONTENT */}
        <Content className="client-content admin-content">
        <Tabs
          className="admin-tabs"
          activeKey={activeTab}
          onChange={(key) => { setActiveTab(key); }}
          size="large"
        >
          {/* ===== TAB 1: OVERVIEW (admin) ===== */}
          <TabPane tab={<span><CrownOutlined /> Обзор</span>} key="overview">
            <div className="admin-overview">
              <div className="admin-overview-hero">
                <div>
                  <div className="admin-overview-kicker">Обзор салона</div>
                  <h2>Ключевые показатели</h2>
                  <p className="admin-overview-date">{dayjs().format('D MMMM YYYY, dddd')} · все ключевые показатели в одном месте</p>
                </div>
                <Space wrap>
                  <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={refreshOverview}>
                    Обновить
                  </Button>
                  <Button type="primary" className="btn-gold" onClick={() => setActiveTab('appointments')}>
                    К записям
                  </Button>
                </Space>
              </div>

              <Spin spinning={kpiLoading}>
                <Row gutter={[14, 14]} className="admin-kpi-row">
                  {[
                    { label: 'Клиенты', value: kpi?.total_clients || 0, icon: <TeamOutlined />, tone: 'gold' },
                    { label: 'Мастера', value: kpi?.total_masters || 0, icon: <ToolOutlined />, tone: 'gold' },
                    { label: 'Записи сегодня', value: kpi?.today_appointments || 0, icon: <CalendarOutlined />, tone: 'gold' },
                    { label: 'Ожидают', value: kpi?.pending_appointments || 0, icon: <ClockCircleOutlined />, tone: 'warn' },
                    { label: 'Закрыто за месяц', value: kpi?.completed_month || 0, icon: <CheckCircleOutlined />, tone: 'gold' },
                    { label: 'Услуг в каталоге', value: servicesTotal || allServices.length || 0, icon: <SettingOutlined />, tone: 'gold' },
                  ].map((m) => (
                    <Col xs={12} sm={8} lg={8} key={m.label}>
                      <motion.div initial={{ opacity: 0, y: 10 }} animate={{ opacity: 1, y: 0 }}>
                        <Card className={`admin-kpi-card tone-${m.tone}`} bordered={false}>
                          <div className="admin-kpi-icon">{m.icon}</div>
                          <div className="admin-kpi-label">{m.label}</div>
                          <div className="admin-kpi-value">{m.value}</div>
                        </Card>
                      </motion.div>
                    </Col>
                  ))}
                </Row>
              </Spin>

              <Row gutter={[16, 16]} style={{ marginTop: 16 }}>
                <Col span={24}>
                  <Card
                    className="admin-panel-card"
                    bordered={false}
                    title={<span className="admin-panel-title">Требуют внимания</span>}
                    extra={<Badge count={kpi?.pending_appointments || pendingList.length} style={{ backgroundColor: brand.colors.accent.solid }} />}
                  >
                    {pendingList.length === 0 ? (
                      <Empty description={<span className="text-titanium">Очереди нет</span>} />
                    ) : (
                      <List
                        dataSource={pendingList}
                        renderItem={(item) => (
                          <List.Item className="admin-attention-item" onClick={() => openApptStatusModal(item)}>
                            <List.Item.Meta
                              title={<span className="text-white">{item.service_name || `Запись #${item.id}`}</span>}
                              description={
                                <span className="text-titanium">
                                  {dayjs(item.start_time).format('DD.MM HH:mm')}
                                  {item.client ? ` · ${item.client.full_name}` : ''}
                                </span>
                              }
                            />
                            <Tag color={STATUS_COLORS[item.status]}>{STATUS_LABELS[item.status]}</Tag>
                          </List.Item>
                        )}
                      />
                    )}
                  </Card>
                </Col>
              </Row>
            </div>
          </TabPane>

          {/* ===== TAB 2: APPOINTMENTS ===== */}
          <TabPane tab={<span><CalendarOutlined /> Записи</span>} key="appointments">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">Операции</div>
                <h3>Записи клиентов</h3>
              </div>
            </div>

            <Row gutter={[12, 12]} className="appt-stats-row">
              {[
                { label: 'Всего записей', value: apptStats.total, tone: 'gold' },
                { label: 'В работе', value: apptStats.in_progress, tone: 'ok' },
                { label: 'Ожидают', value: apptStats.waiting, tone: 'warn' },
                { label: 'Завершено за нед.', value: apptStats.completed_week, tone: 'gold' },
                { label: 'Отменено', value: apptStats.cancelled, tone: 'danger' },
              ].map((m) => (
                <Col xs={12} sm={8} md={4} flex="1 1 140px" key={m.label}>
                  <Card className={`admin-kpi-card tone-${m.tone} appt-stat-card`} bordered={false}>
                    <div className="admin-kpi-label">{m.label}</div>
                    <div className="admin-kpi-value">{m.value}</div>
                  </Card>
                </Col>
              ))}
            </Row>

            <div className="appt-filters">
              <div className="appt-filters-search">
                <Input
                  allowClear
                  prefix={<SearchOutlined />}
                  placeholder="Клиент: фамилия или телефон"
                  value={apptSearchClient}
                  onChange={(e) => { setApptSearchClient(e.target.value); setApptsPage(1); }}
                  className="input-luxury"
                />
                <Input
                  allowClear
                  prefix={<CarOutlined />}
                  placeholder="Авто: номер, марка, модель"
                  value={apptSearchCar}
                  onChange={(e) => { setApptSearchCar(e.target.value); setApptsPage(1); }}
                  className="input-luxury"
                />
              </div>
              <div className="appt-filters-controls">
                <Select
                  value={apptStatusFilter}
                  onChange={(v) => { setApptStatusFilter(v); setApptsPage(1); }}
                  className="appt-filter-select"
                  style={{ minWidth: 150 }}
                >
                  <Option value="all">Все статусы</Option>
                  <Option value="active">Активные</Option>
                  <Option value="in_progress">В работе</Option>
                  <Option value="pending">Ожидают</Option>
                  <Option value="completed">Завершённые</Option>
                  <Option value="cancelled">Отменённые</Option>
                </Select>
                <Select
                  value={apptMasterFilter}
                  onChange={(v) => { setApptMasterFilter(v); setApptsPage(1); }}
                  className="appt-filter-select"
                  style={{ minWidth: 170 }}
                >
                  <Option value="all">Все мастера</Option>
                  {mastersForFilter.map((m) => (
                    <Option key={m.id} value={m.id}>{m.full_name}</Option>
                  ))}
                </Select>
                <Select
                  value={apptPeriodFilter}
                  onChange={(v) => { setApptPeriodFilter(v); setApptsPage(1); }}
                  className="appt-filter-select"
                  style={{ minWidth: 150 }}
                >
                  <Option value="all">Весь период</Option>
                  <Option value="today">Сегодня</Option>
                  <Option value="week">Неделя</Option>
                  <Option value="month">Месяц</Option>
                  <Option value="custom">Произвольный</Option>
                </Select>
                {apptPeriodFilter === 'custom' && (
                  <DatePicker.RangePicker
                    value={apptCustomRange}
                    onChange={(v) => {
                      setApptCustomRange(v as [dayjs.Dayjs, dayjs.Dayjs] | null);
                      setApptsPage(1);
                    }}
                    className="appt-range-picker"
                    format="DD.MM.YYYY"
                  />
                )}
                <Select
                  value={apptSort}
                  onChange={(v) => { setApptSort(v); setApptsPage(1); }}
                  className="appt-filter-select"
                  style={{ minWidth: 180 }}
                >
                  <Option value="active_first">Сначала актуальные</Option>
                  <Option value="date_desc">Сначала новые</Option>
                  <Option value="date_asc">Сначала старые</Option>
                  <Option value="master">По мастеру</Option>
                </Select>
                <Button icon={<ReloadOutlined />} className="btn-gold-secondary" onClick={() => fetchAppointments()}>
                  Обновить
                </Button>
              </div>
            </div>

            <Spin spinning={apptsLoading}>
              <div className="toolbar-row appt-list-meta">
                <Text className="text-gold">
                  Показано {pagedAppointments.length} из {filteredAppointments.length}
                  {apptsTotal > appointments.length ? ` (загружено ${appointments.length} из ${apptsTotal})` : ''}
                </Text>
              </div>
              {filteredAppointments.length === 0 && !apptsLoading ? (
                <Empty description={<Text className="text-titanium">Нет записей по фильтрам</Text>} />
              ) : (
                <List
                  dataSource={pagedAppointments}
                  pagination={{
                    current: apptsPage,
                    pageSize: APPT_LIST_PAGE_SIZE,
                    total: filteredAppointments.length,
                    onChange: (page) => setApptsPage(page),
                    showSizeChanger: false,
                    size: 'small',
                  }}
                  renderItem={(item) => (
                    <motion.div
                      initial={{ opacity: 0, y: 5 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.2 }}
                    >
                      <Card size="small" className="card-appointment appt-card-rich" hoverable>
                        <div className="appt-card-main" onClick={() => openApptStatusModal(item)}>
                          <div className="appt-card-left">
                            <div className="appt-card-top">
                              <Text className="text-white-bold">
                                {item.service_name || `Услуга #${item.service_id}`}
                              </Text>
                              <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                                {STATUS_LABELS[item.status]}
                              </Tag>
                              <span className="appt-status-age">
                                <ClockCircleOutlined /> {formatStatusAge(item)}
                              </span>
                            </div>
                            <div className="appt-card-meta">
                              <span>
                                <ClockCircleOutlined /> {dayjs(item.start_time).format('DD.MM.YYYY HH:mm')}
                              </span>
                              <span>
                                <UserOutlined /> {item.client?.full_name || 'Клиент'}
                                {item.client?.phone ? ` · ${item.client.phone}` : ''}
                              </span>
                              <span>
                                <CarOutlined />{' '}
                                {item.car
                                  ? `${item.car.make} ${item.car.model}${item.car.license_plate ? ` · ${item.car.license_plate}` : ''}`
                                  : 'Авто не указано'}
                              </span>
                              <span>
                                <ToolOutlined /> {item.master?.full_name || 'Мастер не назначен'}
                              </span>
                            </div>
                          </div>
                          <div className="appt-card-price">
                            <Text className="text-gold-bold text-16">{formatCurrency(item.total_price)}</Text>
                          </div>
                        </div>
                        <div className="appt-card-actions" onClick={(e) => e.stopPropagation()}>
                          {(item.status === 'pending' || item.status === 'confirmed') && (
                            <Button
                              size="small"
                              className="btn-gold-secondary"
                              icon={<PlayCircleOutlined />}
                              onClick={() => quickUpdateApptStatus(item, 'in_progress')}
                            >
                              В работу
                            </Button>
                          )}
                          {item.status === 'in_progress' && (
                            <Button
                              size="small"
                              className="btn-gold"
                              icon={<CheckCircleOutlined />}
                              onClick={() => quickUpdateApptStatus(item, 'completed')}
                            >
                              Завершить
                            </Button>
                          )}
                          {APPT_ACTIVE_STATUSES.includes(item.status) && (
                            <Popconfirm
                              title="Отменить запись?"
                              okText="Да"
                              cancelText="Нет"
                              onConfirm={() => quickUpdateApptStatus(item, 'cancelled')}
                            >
                              <Button size="small" danger icon={<CloseCircleOutlined />}>
                                Отменить
                              </Button>
                            </Popconfirm>
                          )}
                          <Button
                            size="small"
                            className="btn-action-gold"
                            icon={<EditOutlined />}
                            onClick={() => openApptStatusModal(item)}
                          >
                            Редактировать
                          </Button>
                        </div>
                      </Card>
                    </motion.div>
                  )}
                />
              )}
            </Spin>
          </TabPane>

          {/* ===== TAB 3: SERVICES ===== */}
          <TabPane tab={<span><ToolOutlined /> Услуги</span>} key="services">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">Каталог</div>
                <h3>Услуги детейлинга</h3>
              </div>
            </div>
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
                            <Tag className="tag-category tag-category-table">
                              {record.category}
                            </Tag>
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
                      render: (val) => <Text className="text-titanium">{val ? formatCurrency(val) : '—'}</Text>,
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
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">Команда и клиенты</div>
                <h3>Пользователи</h3>
              </div>
            </div>
            {/* Role tabs */}
            <Tabs activeKey={userRoleTab} onChange={setUserRoleTab}
              className="admin-inner-tabs"
              tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '16px' }}
              size="small"
            >
              {/* ===== CLIENTS ===== */}
              <TabPane tab="👤 Клиенты" key="clients">
                <Spin spinning={usersLoading || rfmLoading}>
                  {rfmData && rfmData.segments.length > 0 && (
                    <Row gutter={[8, 8]} className="mb-12">
                      {rfmData.segments.map(sc => {
                        const segColors: Record<string, string> = { vip: '#C8A977', loyal: '#4ECB71', regular: '#AAB2BF', new: '#69B1FF', sleeping: '#B76A29', lost: '#ff4d4f' };
                        const segLabels: Record<string, string> = { vip: 'VIP', loyal: 'Лояльные', regular: 'Постоянные', new: 'Новые', sleeping: 'Спящие', lost: 'Ушедшие' };
                        return (
                          <Col xs={12} sm={8} md={4} key={sc.segment}>
                            <Card size="small" className="card-kpi"
                              style={{ cursor: 'pointer', borderColor: segmentFilter === sc.segment ? segColors[sc.segment] : undefined }}
                              onClick={() => handleSegmentFilter(segmentFilter === sc.segment ? '' : sc.segment)}>
                              <Statistic
                                title={<Text className="text-titanium text-11">{segLabels[sc.segment] || sc.segment}</Text>}
                                value={sc.count}
                                suffix={<Text className="text-titanium text-11">({sc.percent}%)</Text>}
                                valueStyle={{ color: segColors[sc.segment] || '#AAB2BF', fontSize: '20px', fontWeight: 700 }}
                              />
                            </Card>
                          </Col>
                        );
                      })}
                    </Row>
                  )}

                  {users.length === 0 && !usersLoading ? (
                    <Empty description={<Text className="text-titanium">Нет клиентов</Text>} />
                  ) : (
                    <Table
                      dataSource={users}
                      rowKey="id"
                      pagination={{ pageSize: 20, size: 'small' }}
                      columns={[
                        {
                          title: <Text className="text-gold">Имя</Text>,
                          dataIndex: 'full_name',
                          key: 'full_name',
                          render: (val) => <Text className="text-white text-medium">{val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Телефон</Text>,
                          dataIndex: 'phone',
                          key: 'phone',
                          render: (val) => <Text className="text-titanium"><PhoneOutlined /> {val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Сегмент</Text>,
                          dataIndex: 'segment',
                          key: 'segment',
                          width: 120,
                          render: (val: string) => {
                            const segColors: Record<string, string> = { vip: 'gold', loyal: 'green', regular: 'default', new: 'blue', sleeping: 'orange', lost: 'red' };
                            const segLabels: Record<string, string> = { vip: 'VIP', loyal: 'Лояльный', regular: 'Постоянный', new: 'Новый', sleeping: 'Спящий', lost: 'Ушедший' };
                            return <Tag color={segColors[val] || 'default'} className="tag-status">{segLabels[val] || val}</Tag>;
                          },
                        },
                        {
                          title: <Text className="text-gold">Визиты</Text>,
                          dataIndex: 'frequency',
                          key: 'frequency',
                          width: 70,
                          render: (val) => <Text className="text-white text-13">{val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Сумма</Text>,
                          dataIndex: 'monetary',
                          key: 'monetary',
                          width: 100,
                          render: (val) => <Text className="text-gold-bold text-13">{val.toLocaleString()} ₽</Text>,
                        },
                        {
                          title: <Text className="text-gold">Дата рег.</Text>,
                          dataIndex: 'created_at',
                          key: 'created_at',
                          render: (val) => <Text className="text-titanium">{val ? dayjs(val).format('DD.MM.YYYY') : '—'}</Text>,
                        },
                        {
                          title: '',
                          key: 'actions',
                          width: 80,
                          render: (_, record) => (
                            <Space size="small">
                              <Tooltip title="История клиента">
                                <Button size="small" onClick={() => openClientDetail(record.id)} className="btn-action-gold">📋</Button>
                              </Tooltip>
                              <Popconfirm title={`Удалить клиента «${record.full_name}»?`}
                                description="Будут удалены все автомобили и записи."
                                onConfirm={() => handleDeleteUser(record.id, record.full_name)}
                                okText="Да, удалить" cancelText="Отмена" okButtonProps={{ danger: true }}>
                                <Tooltip title="Удалить клиента">
                                  <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                                </Tooltip>
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                      components={{
                        header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                        body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                      }}
                    />
                  )}
                </Spin>
              </TabPane>

              {/* ===== MASTERS ===== */}
              <TabPane tab="🔧 Мастера" key="masters">
                <Spin spinning={usersLoading}>
                  {allUsers.filter(u => u.role === 'master').length === 0 ? (
                    <Empty description={<Text className="text-titanium">Нет мастеров</Text>} />
                  ) : (
                    <Table
                      dataSource={allUsers.filter(u => u.role === 'master')}
                      rowKey="id"
                      pagination={{ pageSize: 20, size: 'small' }}
                      columns={[
                        {
                          title: <Text className="text-gold">Имя</Text>,
                          dataIndex: 'full_name',
                          key: 'full_name',
                          render: (val) => <Text className="text-white text-medium">{val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Телефон</Text>,
                          dataIndex: 'phone',
                          key: 'phone',
                          render: (val) => <Text className="text-titanium"><PhoneOutlined /> {val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Роль</Text>,
                          dataIndex: 'role',
                          key: 'role',
                          width: 140,
                          render: (val: string) => <Tag color="cyan" className="tag-status">{ROLE_LABELS[val] || val}</Tag>,
                        },
                        {
                          title: <Text className="text-gold">Дата рег.</Text>,
                          dataIndex: 'created_at',
                          key: 'created_at',
                          render: (val) => <Text className="text-titanium">{val ? dayjs(val).format('DD.MM.YYYY') : '—'}</Text>,
                        },
                      ]}
                      components={{
                        header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                        body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                      }}
                    />
                  )}
                </Spin>
              </TabPane>

              {/* ===== ADMINS ===== */}
              <TabPane tab="👑 Админы" key="admins">
                <Spin spinning={usersLoading}>
                  {allUsers.filter(u => u.role === 'admin' || u.role === 'super_admin').length === 0 ? (
                    <Empty description={<Text className="text-titanium">Нет администраторов</Text>} />
                  ) : (
                    <Table
                      dataSource={allUsers.filter(u => u.role === 'admin' || u.role === 'super_admin')}
                      rowKey="id"
                      pagination={{ pageSize: 20, size: 'small' }}
                      columns={[
                        {
                          title: <Text className="text-gold">Имя</Text>,
                          dataIndex: 'full_name',
                          key: 'full_name',
                          render: (val) => <Text className="text-white text-medium">{val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Телефон</Text>,
                          dataIndex: 'phone',
                          key: 'phone',
                          render: (val) => <Text className="text-titanium"><PhoneOutlined /> {val}</Text>,
                        },
                        {
                          title: <Text className="text-gold">Роль</Text>,
                          dataIndex: 'role',
                          key: 'role',
                          width: 160,
                          render: (val: string) => <Tag color="gold" className="tag-status">{ROLE_LABELS[val] || val}</Tag>,
                        },
                        {
                          title: <Text className="text-gold">Дата рег.</Text>,
                          dataIndex: 'created_at',
                          key: 'created_at',
                          render: (val) => <Text className="text-titanium">{val ? dayjs(val).format('DD.MM.YYYY') : '—'}</Text>,
                        },
                        {
                          title: '',
                          key: 'actions',
                          width: 80,
                          render: (_, record) => (
                            <Space size="small">
                              <Popconfirm title={`Удалить пользователя «${record.full_name}»?`}
                                description="Будут удалены все связанные данные."
                                onConfirm={() => handleDeleteUser(record.id, record.full_name)}
                                okText="Да, удалить" cancelText="Отмена" okButtonProps={{ danger: true }}>
                                <Tooltip title="Удалить">
                                  <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                                </Tooltip>
                              </Popconfirm>
                            </Space>
                          ),
                        },
                      ]}
                      components={{
                        header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                        body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                      }}
                    />
                  )}
                </Spin>
              </TabPane>
            </Tabs>
          </TabPane>

          {/* ===== TAB 5: AI FINANCIER ===== */}
          <TabPane tab={<span><BulbOutlined /> AI Финансист</span>} key="financier">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">AI</div>
                <h3>Финансовый консультант</h3>
              </div>
            </div>
            <Card className="card-luxury admin-panel-card">
              <div className="flex-space-between" style={{ marginBottom: '16px' }}>
                <div>
                  <Text className="title-gold" style={{ fontSize: '18px', fontWeight: 700 }}>AI Финансист</Text>
                  <Text className="text-titanium d-block text-13">
                    Аналитика бизнеса, прогнозы и рекомендации
                  </Text>
                </div>
                <BulbOutlined className="text-gold" style={{ fontSize: '28px' }} />
              </div>

              {/* Chat history */}
              <div style={{
                height: '360px', overflowY: 'auto', marginBottom: '12px',
                display: 'flex', flexDirection: 'column', gap: '12px',
                padding: '4px',
              }}>
                {showSuggestions ? (
                  <div className="text-center" style={{ marginTop: '80px' }}>
                    <BulbOutlined className="text-gold" style={{ fontSize: '40px', opacity: 0.5 }} />
                    <Text className="text-titanium d-block text-14" style={{ marginTop: '12px' }}>
                      Задайте вопрос о финансах вашего бизнеса
                    </Text>
                    <div style={{ marginTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px', alignItems: 'center' }}>
                      {['Какая прибыль за месяц?', 'Кто из мастеров эффективнее?', 'Прогноз выручки на неделю'].map(q => (
                        <Button
                          key={q}
                          size="small"
                          className="btn-gold-secondary"
                          style={{ width: '320px', height: '36px', fontSize: '13px' }}
                          onClick={() => {
                            setFinancierInput(q);
                            setTimeout(() => handleFinancierQuestion(), 100);
                          }}
                        >{q}</Button>
                      ))}
                    </div>
                  </div>
                ) : (
                  financierMessages.map((msg, i) => (
                    <div
                      key={i}
                      style={{
                        maxWidth: '85%',
                        alignSelf: msg.role === 'user' ? 'flex-end' : 'flex-start',
                      }}
                    >
                      <Card
                        size="small"
                        className={msg.role === 'user' ? 'card-detail' : 'card-luxury'}
                        style={{
                          padding: msg.role === 'user' ? '8px 14px' : '12px 16px',
                          borderRadius: msg.role === 'user' ? '16px 16px 4px 16px' : '16px 16px 16px 4px',
                          border: msg.role === 'user' ? '1px solid rgba(200,169,119,0.2)' : undefined,
                          marginBottom: 0,
                        }}
                      >
                        {msg.role === 'user' ? (
                          <Text className="text-white text-14">{msg.text}</Text>
                        ) : (
                          <Text className="text-titanium text-13" style={{ whiteSpace: 'pre-wrap' }}>{msg.text}</Text>
                        )}
                      </Card>
                    </div>
                  ))
                )}
                {financierLoading && (
                  <div style={{ alignSelf: 'flex-start', maxWidth: '85%' }}>
                    <Card size="small" className="card-luxury" style={{ padding: '12px 16px', borderRadius: '16px 16px 16px 4px', marginBottom: 0 }}>
                      <Text className="text-titanium text-13">🤔 Анализирую данные...</Text>
                    </Card>
                  </div>
                )}
              </div>

              {/* Input area */}
              <div className="flex-space-between" style={{ gap: '8px' }}>
                <Button
                  icon={<PlusOutlined />}
                  onClick={handleNewDialog}
                  style={{
                    backgroundColor: '#232A33',
                    border: '1px solid rgba(255,255,255,0.1)',
                    color: '#C8A977',
                    borderRadius: '20px',
                    height: '46px',
                    whiteSpace: 'nowrap',
                  }}
                >
                  Новый диалог
                </Button>
                <Input.TextArea
                  className="input-luxury"
                  placeholder="Спросите AI-финансиста..."
                  value={financierInput}
                  onChange={(e) => setFinancierInput(e.target.value)}
                  onPressEnter={(e) => {
                    if (!e.shiftKey) {
                      e.preventDefault();
                      handleFinancierQuestion();
                    }
                  }}
                  rows={1}
                  style={{ flex: 1, height: '46px', resize: 'none', paddingTop: '12px' }}
                />
                <Button
                  className="btn-gold"
                  style={{ width: '56px', height: '46px', padding: 0, minWidth: '56px' }}
                  onClick={handleFinancierQuestion}
                  loading={financierLoading}
                  icon={<SendOutlined />}
                />
              </div>
            </Card>
          </TabPane>

          {/* ===== TAB 6: FINANCES (P&L) ===== */}
          <TabPane tab={<span><DollarOutlined /> Финансы</span>} key="finances">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">P&amp;L</div>
                <h3>Финансы салона</h3>
              </div>
            </div>
            <Spin spinning={plLoading || expensesLoading}>
              {/* P&L Summary Cards */}
              {plReport && (
                <>
                  <Row gutter={[16, 16]} className="mb-12">
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Выручка (месяц)</Text>}
                          value={plReport.total_revenue}
                          prefix={<DollarOutlined className="text-gold" />}
                          precision={0}
                          suffix={<Text className="text-titanium text-12">₽</Text>}
                          valueStyle={{ color: '#C8A977', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Расходы (материалы)</Text>}
                          value={plReport.total_material_cost}
                          precision={0}
                          suffix={<Text className="text-titanium text-12">₽</Text>}
                          valueStyle={{ color: '#AAB2BF', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Постоянные расходы</Text>}
                          value={plReport.total_expenses}
                          precision={0}
                          suffix={<Text className="text-titanium text-12">₽</Text>}
                          valueStyle={{ color: '#ff4d4f', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Чистая прибыль</Text>}
                          value={plReport.net_profit}
                          precision={0}
                          suffix={<Text className="text-titanium text-12">₽</Text>}
                          valueStyle={{ color: plReport.net_profit >= 0 ? '#4ECB71' : '#ff4d4f', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                  </Row>
                  <Row gutter={[16, 16]} className="mb-12">
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Средний чек</Text>}
                          value={plReport.avg_check}
                          precision={0}
                          suffix={<Text className="text-titanium text-12">₽</Text>}
                          valueStyle={{ color: '#C8A977', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Валовая маржа</Text>}
                          value={plReport.gross_margin_percent}
                          precision={1}
                          suffix={<Text className="text-titanium text-12">%</Text>}
                          valueStyle={{ color: '#4ECB71', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Чистая маржа</Text>}
                          value={plReport.net_margin_percent}
                          precision={1}
                          suffix={<Text className="text-titanium text-12">%</Text>}
                          valueStyle={{ color: plReport.net_margin_percent >= 0 ? '#4ECB71' : '#ff4d4f', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                    <Col xs={12} sm={6}>
                      <Card className="card-kpi" size="small">
                        <Statistic
                          title={<Text className="text-titanium text-12">Завершено записей</Text>}
                          value={plReport.completed_appointments}
                          valueStyle={{ color: '#FFFFFF', fontSize: '22px', fontWeight: 700 }}
                        />
                      </Card>
                    </Col>
                  </Row>

                  {/* Service Margins */}
                  <Card className="card-luxury" style={{ marginBottom: '16px' }}>
                    <Text className="title-gold text-16 d-block mb-8">Маржинальность по услугам</Text>
                    {plReport.service_margins.length === 0 ? (
                      <Text className="text-titanium text-13">Нет данных за месяц</Text>
                    ) : (
                      <Table
                        dataSource={plReport.service_margins}
                        rowKey="service_id"
                        pagination={false}
                        size="small"
                        columns={[
                          { title: <Text className="text-titanium text-12">Услуга</Text>, dataIndex: 'service_name', key: 'name',
                            render: (v, r) => <div><Text className="text-white text-13">{v}</Text>{r.category && <Tag className="tag-category" style={{ marginLeft: 6 }}>{r.category}</Tag>}</div> },
                          { title: <Text className="text-titanium text-12">Записей</Text>, dataIndex: 'appointment_count', key: 'cnt', width: 70,
                            render: v => <Text className="text-white text-13">{v}</Text> },
                          { title: <Text className="text-titanium text-12">Выручка</Text>, dataIndex: 'total_revenue', key: 'rev', width: 100,
                            render: v => <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text> },
                          { title: <Text className="text-titanium text-12">Материалы</Text>, dataIndex: 'total_material_cost', key: 'mat', width: 90,
                            render: v => <Text className="text-titanium text-13">{v.toLocaleString()} ₽</Text> },
                          { title: <Text className="text-titanium text-12">Маржа</Text>, dataIndex: 'margin_percent', key: 'margin', width: 80,
                            render: v => <Text className="text-13" style={{ color: v >= 50 ? '#4ECB71' : v >= 30 ? '#C8A977' : '#ff4d4f', fontWeight: 600 }}>{v}%</Text> },
                        ]}
                        components={{
                          header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                          body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                        }}
                      />
                    )}
                  </Card>
                </>
              )}

              {/* Expenses accounting module */}
              <div style={{ marginTop: 16 }}>
                <ExpensesModule />
              </div>
            </Spin>
          </TabPane>

          {/* ===== TAB 7: ANALYTICS CHARTS ===== */}
          <TabPane tab={<span><AreaChartOutlined /> Аналитика</span>} key="analytics">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">Метрики</div>
                <h3>Аналитика</h3>
              </div>
            </div>
            <Spin spinning={revenueLoading || heatmapLoading || funnelLoading}>
              <Row gutter={[16, 16]}>
                {/* Revenue Area Chart with Period Selector */}
                <Col xs={24} lg={14}>
                  <Card className="card-luxury">
                    <div className="flex-space-between mb-12" style={{ flexWrap: 'wrap', gap: 8 }}>
                      <Text className="title-gold text-16">Выручка</Text>
                      <Space size="small" wrap>
                        {/* Quick period buttons */}
                        <Button size="small"
                          className={!periodStart ? 'btn-gold' : 'btn-logout'}
                          onClick={() => {
                            setPeriodStart(null);
                            setPeriodEnd(null);
                            fetchRevenueChart();
                          }}
                        >Месяц</Button>
                        <Button size="small"
                          className={periodStart ? 'btn-gold' : 'btn-logout'}
                          onClick={() => {
                            const end = dayjs();
                            const start = end.subtract(7, 'day');
                            setPeriodStart(start.format('YYYY-MM-DD'));
                            setPeriodEnd(end.format('YYYY-MM-DD'));
                            fetchRevenueChart(start.format('YYYY-MM-DD'), end.format('YYYY-MM-DD'));
                          }}
                        >Неделя</Button>
                        <DatePicker.RangePicker
                          size="small"
                          className="input-luxury"
                          style={{ width: 200 }}
                          onChange={(dates) => {
                            if (dates && dates[0] && dates[1]) {
                              const s = dates[0].format('YYYY-MM-DD');
                              const e = dates[1].format('YYYY-MM-DD');
                              setPeriodStart(s);
                              setPeriodEnd(e);
                              fetchRevenueChart(s, e);
                            }
                          }}
                        />
                        <Button size="small" icon={<ReloadOutlined />}
                          onClick={() => fetchRevenueChart(periodStart || undefined, periodEnd || undefined)}
                          type="text" className="btn-logout" />
                      </Space>
                    </div>

                    {/* Comparison cards */}
                    {revenueData && (
                      <Row gutter={[12, 12]} className="mb-12">
                        <Col xs={12} sm={6}>
                          <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                            <Statistic
                              title={<Text className="text-titanium text-11">Текущий период</Text>}
                              value={revenueData.total}
                              precision={0}
                              suffix={<Text className="text-titanium text-11">₽</Text>}
                              valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }}
                            />
                          </Card>
                        </Col>
                        <Col xs={12} sm={6}>
                          <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                            <Statistic
                              title={<Text className="text-titanium text-11">Прошлый период</Text>}
                              value={revenueData.previous_total}
                              precision={0}
                              suffix={<Text className="text-titanium text-11">₽</Text>}
                              valueStyle={{ color: '#AAB2BF', fontSize: '18px', fontWeight: 700 }}
                            />
                          </Card>
                        </Col>
                        <Col xs={12} sm={6}>
                          <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                            <Statistic
                              title={<Text className="text-titanium text-11">Изменение</Text>}
                              value={revenueData.change_percent}
                              precision={1}
                              suffix={<Text className="text-titanium text-11">%</Text>}
                              valueStyle={{
                                color: revenueData.change_percent >= 0 ? '#4ECB71' : '#ff4d4f',
                                fontSize: '18px', fontWeight: 700,
                              }}
                              prefix={revenueData.change_percent >= 0 ? '↑' : '↓'}
                            />
                          </Card>
                        </Col>
                        <Col xs={12} sm={6}>
                          <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                            <Statistic
                              title={<Text className="text-titanium text-11">В день (тек./прош.)</Text>}
                              value={revenueData.avg_per_day}
                              precision={0}
                              suffix={
                                <Text className="text-titanium text-11">
                                  / {revenueData.previous_avg_per_day.toLocaleString()} ₽
                                </Text>
                              }
                              valueStyle={{ color: '#FFFFFF', fontSize: '16px', fontWeight: 600 }}
                            />
                          </Card>
                        </Col>
                      </Row>
                    )}
                    {revenueData && revenueData.daily.length > 0 ? (
                      <ResponsiveContainer width="100%" height={260}>
                        <AreaChart data={revenueData.daily}>
                          <defs>
                            <linearGradient id="revenueGradient" x1="0" y1="0" x2="0" y2="1">
                              <stop offset="5%" stopColor="#C8A977" stopOpacity={0.3} />
                              <stop offset="95%" stopColor="#C8A977" stopOpacity={0} />
                            </linearGradient>
                          </defs>
                          <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.04)" />
                          <XAxis dataKey="date" tick={{ fill: '#AAB2BF', fontSize: 10 }} tickFormatter={(v) => v.slice(8, 10)} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fill: '#AAB2BF', fontSize: 10 }} axisLine={false} tickLine={false} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                          <RechartsTooltip
                            contentStyle={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '10px', color: '#AAB2BF' }}
                            formatter={(value: number) => [`${value.toLocaleString()} ₽`, 'Выручка']}
                            labelFormatter={(label) => `📅 ${label}`}
                          />
                          <Area type="monotone" dataKey="revenue" stroke="#C8A977" fill="url(#revenueGradient)" strokeWidth={2} />
                        </AreaChart>
                      </ResponsiveContainer>
                    ) : (
                      <div className="text-center" style={{ padding: '60px 0' }}>
                        <Text className="text-titanium text-13">Нет данных за выбранный период</Text>
                      </div>
                    )}
                  </Card>
                </Col>

                {/* Funnel Chart */}
                <Col xs={24} lg={10}>
                  <Card className="card-luxury">
                    <div className="flex-space-between mb-12">
                      <Text className="title-gold text-16">Воронка продаж</Text>
                      <Space size="small">
                        {funnelData && (
                          <Text className="text-titanium text-12">Конверсия: <Text className="text-gold-bold">{funnelData.conversion_rate}%</Text></Text>
                        )}
                        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchFunnel(periodStart || undefined, periodEnd || undefined)} type="text" className="btn-logout" />
                      </Space>
                    </div>
                    {funnelData && funnelData.stages.length > 0 ? (
                      <div style={{ height: 260 }}>
                        {funnelData.stages.map((stage, i) => {
                          const maxVal = funnelData.stages[0]?.value || 1;
                          const widthPct = (stage.value / maxVal) * 100;
                          return (
                            <div key={stage.name} className="mb-8">
                              <div className="flex-space-between" style={{ marginBottom: 4 }}>
                                <Text className="text-titanium text-12">{stage.name}</Text>
                                <Space size="small">
                                  <Text className="text-white-bold text-13">{stage.value}</Text>
                                  <Text className="text-titanium text-11">({stage.percent}%)</Text>
                                </Space>
                              </div>
                              <div style={{ height: 22, backgroundColor: 'rgba(255,255,255,0.04)', borderRadius: 6, overflow: 'hidden' }}>
                                <div style={{ height: '100%', width: `${widthPct}%`, backgroundColor: stage.color, borderRadius: 6, opacity: 1 - i * 0.15 }} />
                              </div>
                            </div>
                          );
                        })}
                      </div>
                    ) : (
                      <div className="text-center" style={{ padding: '60px 0' }}>
                        <Text className="text-titanium text-13">Нет данных за месяц</Text>
                      </div>
                    )}
                  </Card>
                </Col>

                {/* Heatmap */}
                <Col xs={24}>
                  <Card className="card-luxury">
                    <div className="flex-space-between mb-12">
                      <Text className="title-gold text-16">Тепловая карта загрузки</Text>
                      <Space size="small" wrap>
                        <Select
                          size="small"
                          className="input-luxury"
                          placeholder="Все боксы"
                          value={selectedBoxId}
                          onChange={(v) => {
                            setSelectedBoxId(v);
                            fetchHeatmap(v);
                          }}
                          allowClear
                          style={{ minWidth: 160 }}
                          onClear={() => {
                            setSelectedBoxId(undefined);
                            fetchHeatmap(undefined);
                          }}
                        >
                          {boxes.filter(b => b.is_active !== false).sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0)).map((b) => {
                            const boxServiceNames = (b.service_ids || [])
                              .map((sid: number) => services.find(s => s.id === sid)?.name)
                              .filter(Boolean)
                              .join(', ');
                            return (
                              <Option key={b.id} value={b.id}>
                                <Tooltip title={boxServiceNames || 'Нет услуг'} mouseEnterDelay={0.5}>
                                  <Space size={4}>
                                    <div style={{
                                      width: 28,
                                      height: 28,
                                      borderRadius: '50%',
                                      backgroundColor: b.color || '#C8A977',
                                      display: 'inline-flex',
                                      alignItems: 'center',
                                      justifyContent: 'center',
                                      color: isLightColor(b.color) ? '#000000' : '#FFFFFF',
                                      fontSize: 12,
                                      fontWeight: 700,
                                      flexShrink: 0,
                                      cursor: 'pointer',
                                      textShadow: '0 1px 3px rgba(0,0,0,0.5)',
                                    }}>
                                      {b.id}
                                    </div>
                                    <span style={{ color: '#FFFFFF' }}>{b.name}</span>
                                  </Space>
                                </Tooltip>
                              </Option>
                            );
                          })}
                        </Select>
                        <Button size="small" icon={<EditOutlined />}
                          onClick={() => setBoxSettingsModal(true)}
                          className="btn-action-gold">Настройка</Button>
                        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchHeatmap(selectedBoxId)} type="text" className="btn-logout" />
                      </Space>
                    </div>
                    {heatmapData.length > 0 ? (
                      <>
                        <div className="flex-space-between" style={{ marginBottom: 8, paddingLeft: 40 }}>
                          {[8,9,10,11,12,13,14,15,16,17,18,19,20,21,22].map(h => (
                            <Text key={h} className="text-titanium text-11" style={{ width: '6.66%', textAlign: 'center' }}>{h}:00</Text>
                          ))}
                        </div>
                        {[0,1,2,3,4,5,6].map(day => {
                          const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
                          const maxCount = Math.max(...heatmapData.map(c => c.count), 1);
                          const selectedBoxColor = boxes.find(b => b.id === selectedBoxId)?.color;
                          const boxRgb = selectedBoxColor ? hexToRgb(selectedBoxColor) : null;
                          return (
                            <div key={day} className="flex-space-between" style={{ marginBottom: 4 }}>
                              <Text className="text-titanium text-11" style={{ width: 36 }}>{dayNames[day]}</Text>
                              {[8,9,10,11,12,13,14,15,16,17,18,19,20,21,22].map(hour => {
                                const cell = heatmapData.find(c => c.day === day && c.hour === hour);
                                const count = cell?.count || 0;
                                const intensity = count / maxCount;
                                const bgColor = count > 0
                                  ? boxRgb
                                    ? `rgba(${boxRgb}, ${0.15 + intensity * 0.7})`
                                    : `rgba(200, 169, 119, ${0.1 + intensity * 0.6})`
                                  : 'rgba(255,255,255,0.02)';
                                return (
                                  <div
                                    key={`${day}-${hour}`}
                                    className="text-center"
                                    style={{
                                      width: '6.66%', height: 32, backgroundColor: bgColor,
                                      borderRadius: 4, display: 'flex', alignItems: 'center',
                                      justifyContent: 'center', cursor: 'pointer',
                                      ...(selectedBoxId && count > 0 ? {
                                        border: `2px solid ${selectedBoxColor || '#C8A977'}`,
                                        boxShadow: `0 0 6px rgba(${boxRgb}, 0.3)`,
                                      } : {}),
                                    }}
                                    title={count > 0 ? `${count} записей · ${cell?.revenue.toLocaleString()} ₽` : '✅ Свободно'}
                                    onClick={() => handleHeatmapCellClick(day, hour)}
                                  >
                                    <Text className="text-11" style={{ color: count > maxCount * 0.5 ? '#0B0D10' : '#AAB2BF' }}>
                                      {count || '○'}
                                    </Text>
                                  </div>
                                );
                              })}
                            </div>
                          );
                        })}
                      </>
                    ) : (
                      <div className="text-center" style={{ padding: '40px 0' }}>
                        <Text className="text-titanium text-13">Нет данных за месяц</Text>
                      </div>
                    )}
                  </Card>
                </Col>
              </Row>
            </Spin>
          </TabPane>

          {/* ===== TAB 8: DISCOUNTS & LOYALTY ===== */}
          <TabPane tab={<span><GiftOutlined /> Скидки</span>} key="discounts">
            <div className="admin-section-head">
              <div>
                <div className="admin-overview-kicker">Лояльность</div>
                <h3>Скидки и бонусы</h3>
              </div>
            </div>

            <DiscountIntelligence onCreateSuggestion={createDiscountFromSuggestion} />

            <div style={{ marginTop: 16, marginBottom: 16 }}>
              <ServiceDiscountRecs />
            </div>

            <Spin spinning={discountsLoading || loyaltyLoading}>
              <div className="toolbar-right mb-12" style={{ marginTop: 16 }}>
                <Button type="primary" icon={<PlusOutlined />} className="btn-gold" style={{ width: 'auto' }}
                  onClick={() => openDiscountModal()}>Создать правило вручную</Button>
              </div>


              {/* Таблица правил скидок */}
              <Card className="card-luxury" style={{ marginBottom: '16px' }}>
                <Text className="title-gold text-16 d-block mb-8">Правила скидок</Text>
                {discountRules.length === 0 && !discountsLoading ? (
                  <Text className="text-titanium text-13">Нет правил скидок. Создайте первое правило.</Text>
                ) : (
                  <Table
                    dataSource={discountRules}
                    rowKey="id"
                    pagination={false}
                    size="small"
                    columns={[
                      {
                        title: <Text className="text-titanium text-12">Название</Text>,
                        dataIndex: 'name', key: 'name',
                        render: (val, record) => (
                          <Space>
                            <Text className="text-white text-13">{val}</Text>
                            <Tag className="tag-status"
                              color={record.is_active ? 'green' : 'default'}>{record.is_active ? 'Активна' : 'Неактивна'}</Tag>
                          </Space>
                        ),
                      },
                      {
                        title: <Text className="text-titanium text-12">Тип</Text>,
                        dataIndex: 'type', key: 'type',
                        render: (val) => (
                          <Tag className="tag-status" color={DISCOUNT_TYPE_COLORS[val] || 'default'}>
                            {DISCOUNT_TYPE_LABELS[val] || val}
                          </Tag>
                        ),
                      },
                      {
                        title: <Text className="text-titanium text-12">%</Text>,
                        dataIndex: 'discount_percent', key: 'percent',
                        render: (val) => <Text className="text-gold-bold text-13">{val}%</Text>,
                      },
                      {
                        title: <Text className="text-titanium text-12">Привязка</Text>,
                        key: 'binding',
                        render: (_, record) => (
                          <Text className="text-titanium text-12">
                            {record.service_name ? `📋 ${record.service_name}` : record.client_name ? `👤 ${record.client_name}` : '—'}
                          </Text>
                        ),
                      },
                      {
                        title: <Text className="text-titanium text-12">Слот</Text>,
                        key: 'slot',
                        render: (_, record) => (
                          <Text className="text-titanium text-12">
                            {record.slot_start || '∞'} — {record.slot_end || '∞'}
                          </Text>
                        ),
                      },
                      {
                        title: <Text className="text-titanium text-12">До</Text>,
                        dataIndex: 'valid_until', key: 'valid_until',
                        render: (val) => <Text className="text-titanium text-12">{val ? dayjs(val).format('DD.MM.YYYY') : '∞'}</Text>,
                      },
                      {
                        title: '',
                        key: 'actions', width: 100,
                        render: (_, record) => (
                          <Space size="small">
                            <Tooltip title="Редактировать">
                              <Button size="small" icon={<EditOutlined />}
                                className="btn-action-gold" onClick={() => openDiscountModal(record)} />
                            </Tooltip>
                            <Popconfirm title={`Удалить «${record.name}»?`}
                              onConfirm={() => handleDeleteDiscount(record.id, record.name)}
                              okText="Да" cancelText="Нет">
                              <Tooltip title="Удалить">
                                <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                              </Tooltip>
                            </Popconfirm>
                          </Space>
                        ),
                      },
                    ]}
                    components={{
                      header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                      body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                    }}
                  />
                )}
              </Card>

              {/* Баланс баллов клиентов */}
              <Card className="card-luxury">
                <div className="flex-space-between mb-12">
                  <Text className="title-gold text-16"><StarOutlined /> Баланс баллов клиентов</Text>
                  <Button size="small" icon={<ReloadOutlined />} onClick={fetchLoyalty} type="text" className="btn-logout" />
                </div>
                {loyaltyClients.length === 0 && !loyaltyLoading ? (
                  <Text className="text-titanium text-13">Нет данных о баллах. Баллы начисляются за завершённые записи.</Text>
                ) : (
                  <Table
                    dataSource={loyaltyClients}
                    rowKey="client_id"
                    pagination={{ pageSize: 20, size: 'small' }}
                    size="small"
                    columns={[
                      {
                        title: <Text className="text-titanium text-12">Клиент</Text>,
                        dataIndex: 'full_name', key: 'full_name',
                        render: (val) => <Text className="text-white text-13">{val}</Text>,
                      },
                      {
                        title: <Text className="text-titanium text-12">Телефон</Text>,
                        dataIndex: 'phone', key: 'phone',
                        render: (val) => <Text className="text-titanium text-13"><PhoneOutlined /> {val}</Text>,
                      },
                      {
                        title: <Text className="text-titanium text-12">Баллы</Text>,
                        dataIndex: 'balance', key: 'balance',
                        render: (val) => <Text className="text-gold-bold text-13">{val}</Text>,
                      },
                      {
                        title: <Text className="text-titanium text-12">Всего заработано</Text>,
                        dataIndex: 'total_earned', key: 'earned',
                        render: (val) => <Text className="text-white text-13">{val}</Text>,
                      },
                      {
                        title: <Text className="text-titanium text-12">Потрачено</Text>,
                        dataIndex: 'total_spent', key: 'spent',
                        render: (val) => <Text className="text-titanium text-13">{val}</Text>,
                      },
                    ]}
                    components={{
                      header: { cell: (p: any) => <th {...p} className="table-header-cell" /> },
                      body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> },
                    }}
                  />
                )}
              </Card>

              {/* ===== DISCOUNT ANALYTICS ===== */}
              <Card className="card-luxury" style={{ marginTop: '16px' }}>
                <div className="flex-space-between mb-12">
                  <Text className="title-gold text-16"><AreaChartOutlined /> Аналитика скидок</Text>
                  <Button size="small" icon={<ReloadOutlined />} onClick={fetchDiscountAnalytics} type="text" className="btn-logout" />
                </div>
                {discountAnalytics ? (
                  <>
                    <Row gutter={[12, 12]} className="mb-12">
                      <Col xs={12} sm={6}>
                        <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                          <Statistic title={<Text className="text-titanium text-11">Всего правил</Text>}
                            value={discountAnalytics.total_rules}
                            valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }} />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                          <Statistic title={<Text className="text-titanium text-11">Активных</Text>}
                            value={discountAnalytics.active_rules}
                            valueStyle={{ color: '#4ECB71', fontSize: '18px', fontWeight: 700 }} />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                          <Statistic title={<Text className="text-titanium text-11">Применено раз</Text>}
                            value={discountAnalytics.total_times_used}
                            valueStyle={{ color: '#C8A977', fontSize: '18px', fontWeight: 700 }} />
                        </Card>
                      </Col>
                      <Col xs={12} sm={6}>
                        <Card size="small" className="card-kpi" style={{ padding: '8px 12px' }}>
                          <Statistic title={<Text className="text-titanium text-11">Сумма скидок</Text>}
                            value={discountAnalytics.total_discount_amount}
                            precision={0} suffix={<Text className="text-titanium text-11">₽</Text>}
                            valueStyle={{ color: '#FFFFFF', fontSize: '18px', fontWeight: 700 }} />
                        </Card>
                      </Col>
                    </Row>
                    {discountAnalytics.top_rules.length > 0 && (
                      <Table dataSource={discountAnalytics.top_rules} rowKey="rule_id" pagination={false} size="small"
                        columns={[
                          { title: <Text className="text-titanium text-12">Правило</Text>, dataIndex: 'rule_name',
                            render: (v: any, r: any) => <Space><Text className="text-white text-13">{v}</Text><Tag className="tag-status" color={DISCOUNT_TYPE_COLORS[r.rule_type]}>{DISCOUNT_TYPE_LABELS[r.rule_type] || r.rule_type}</Tag></Space> },
                          { title: <Text className="text-titanium text-12">Использований</Text>, dataIndex: 'times_used',
                            render: (v) => <Text className="text-white-bold text-13">{v}</Text> },
                          { title: <Text className="text-titanium text-12">Скидка</Text>, dataIndex: 'total_discount',
                            render: (v) => <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text> },
                          { title: <Text className="text-titanium text-12">Клиентов</Text>, dataIndex: 'client_count',
                            render: (v) => <Text className="text-titanium text-13">{v}</Text> },
                        ]}
                        components={{ header: { cell: (p: any) => <th {...p} className="table-header-cell" /> }, body: { row: (p: any) => <tr {...p} className="table-body-row" />, cell: (p: any) => <td {...p} className="table-body-cell" /> } }}
                      />
                    )}
                  </>
                ) : (
                  <Text className="text-titanium text-13">Нажмите «Обновить» для загрузки аналитики</Text>
                )}
              </Card>
            </Spin>
          </TabPane>

          {/* ===== TAB 9: CALENDAR ===== */}
          <TabPane tab={<span><CalendarOutlined /> Календарь</span>} key="calendar">
            <MasterCalendar />
          </TabPane>

          {/* ===== TAB 10: REPORTS ===== */}
          <TabPane tab={<span><BarChartOutlined /> Отчёты</span>} key="reports">
            <ReportManager />
          </TabPane>

          {/* ===== TAB 11: SERVICE ANALYTICS ===== */}
          <TabPane tab={<span><AreaChartOutlined /> Аналитика услуг</span>} key="service-analytics">
            <ServiceAnalytics />
          </TabPane>

          {/* ===== TAB 12: NOTIFICATIONS ===== */}
          <TabPane tab={<span><BellOutlined /> Уведомления</span>} key="notifications">
            <Tabs size="small" tabBarStyle={{ borderBottom: '1px solid rgba(255,255,255,0.06)', marginBottom: '16px' }}>
              <TabPane tab="📋 Список уведомлений" key="list">
                <NotificationList title="Все уведомления" />
              </TabPane>
              <TabPane tab="⚙️ Настройки" key="settings">
                <NotificationSettings />
              </TabPane>
            </Tabs>
          </TabPane>
        </Tabs>
      </Content>

      {/* ===== SERVICE MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">{editingService ? '✏️ Редактировать услугу' : '➕ Новая услуга'}</Text>}
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
          <div>
            <span className="label-field">Себестоимость (₽)</span>
            <Input
              size="large"
              type="number"
              className="input-luxury"
              value={serviceForm.cost_price}
              onChange={(e) => setServiceForm(prev => ({ ...prev, cost_price: Number(e.target.value) }))}
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
            className="btn-gold"
          >{editingService ? 'Сохранить' : 'Создать'}</Button>
        </Space>
      </Modal>

      {/* ===== APPOINTMENT STATUS MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">📅 Управление записью</Text>}
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
                {allUsers.filter(u => u.role === 'master').map(m => (
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
        title={<Text className="text-gold-bold">👤 Изменить роль</Text>}
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
        title={<Text className="text-gold-bold">📋 Карточка клиента</Text>}
        open={clientModal}
        onCancel={() => { setClientModal(false); setClientDetail(null); setClientPoints(null); }}
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

              {/* Баллы лояльности */}
              <Card size="small" className="card-luxury" style={{ marginTop: '8px' }}>
                <Text className="title-gold text-14 d-block mb-8">🏅 Баллы лояльности</Text>
                {clientPoints ? (
                  <Row gutter={[12, 12]}>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-gold-bold text-24">{clientPoints.balance}</Text>
                        <Text className="text-titanium d-block text-11">Баллы</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-white-bold text-24">{clientPoints.total_earned}</Text>
                        <Text className="text-titanium d-block text-11">Заработано</Text>
                      </div>
                    </Col>
                    <Col span={8}>
                      <div className="text-center">
                        <Text className="text-white-bold text-24">{clientPoints.total_spent}</Text>
                        <Text className="text-titanium d-block text-11">Потрачено</Text>
                      </div>
                    </Col>
                  </Row>
                ) : (
                  <Text className="text-titanium text-12">Нет данных о баллах</Text>
                )}
              </Card>

              {clientDetail.last_visit && (
                <Text className="text-small text-center d-block">
                  🕐 Последний визит: {dayjs(clientDetail.last_visit).format('DD.MM.YYYY HH:mm')}
                </Text>
              )}
            </Space>
          )}
        </Spin>
      </Modal>

      {/* ===== EXPENSE MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">➕ Добавить расход</Text>}
        open={expenseModal}
        onCancel={() => { setExpenseModal(false); setExpenseForm({ name: '', amount: 0, category: 'other', notes: '' }); }}
        footer={null}
        className="modal-command"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Название *</span>
            <Input size="large" className="input-luxury" placeholder="Аренда помещения"
              value={expenseForm.name}
              onChange={(e) => setExpenseForm(prev => ({ ...prev, name: e.target.value }))} />
          </div>
          <div>
            <span className="label-field">Сумма *</span>
            <Input size="large" type="number" className="input-luxury" placeholder="50000"
              value={expenseForm.amount || ''}
              onChange={(e) => setExpenseForm(prev => ({ ...prev, amount: Number(e.target.value) }))} />
          </div>
          <div>
            <span className="label-field">Категория</span>
            <Select size="large" className="w-full" value={expenseForm.category}
              onChange={(v) => setExpenseForm(prev => ({ ...prev, category: v }))}>
              <Option value="rent">Аренда</Option>
              <Option value="salary">Зарплата</Option>
              <Option value="utilities">Коммунальные</Option>
              <Option value="marketing">Маркетинг</Option>
              <Option value="supplies">Расходники</Option>
              <Option value="other">Прочее</Option>
            </Select>
          </div>
          <div>
            <span className="label-field">Заметка</span>
            <TextArea rows={2} className="input-luxury" placeholder="Дополнительная информация"
              value={expenseForm.notes}
              onChange={(e) => setExpenseForm(prev => ({ ...prev, notes: e.target.value }))} />
          </div>
          <Button type="primary" size="large" className="btn-gold" onClick={handleAddExpense} loading={expenseSaving}>
            Добавить расход
          </Button>
        </Space>
      </Modal>

      {/* ===== DISCOUNT MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">{editingDiscount ? '✏️ Редактировать правило скидки' : '➕ Новое правило скидки'}</Text>}
        open={discountModal}
        onCancel={() => { setDiscountModal(false); setEditingDiscount(null); }}
        footer={null}
        width={560}
        className="modal-command"
      >
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Название *</span>
            <Input size="large" className="input-luxury" placeholder="Happy Hours"
              value={discountForm.name}
              onChange={(e) => setDiscountForm(prev => ({ ...prev, name: e.target.value }))} />
          </div>
          <Row gutter={16}>
            <Col span={12}>
              <span className="label-field">Тип скидки *</span>
              <Select size="large" className="w-full" value={discountForm.type}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, type: v }))}>
                <Option value="happy_hours">Happy Hours</Option>
                <Option value="service">На услугу</Option>
                <Option value="client">Персональная</Option>
                <Option value="segment">По сегменту (VIP, Лояльные...)</Option>
                <Option value="frequency">За частоту визитов</Option>
                <Option value="win_back">Возврат клиентов</Option>
                <Option value="cashback">Кэшбек</Option>
              </Select>
            </Col>
            <Col span={12}>
              <span className="label-field">Процент скидки *</span>
              <Input size="large" type="number" className="input-luxury" placeholder="10"
                value={discountForm.discount_percent || ''}
                onChange={(e) => setDiscountForm(prev => ({ ...prev, discount_percent: Number(e.target.value) }))} />
            </Col>
          </Row>
          {/* Time slot — только для happy_hours */}
          {discountForm.type === 'happy_hours' && (
            <Row gutter={16}>
              <Col span={12}>
                <span className="label-field">Время начала слота</span>
                <TimePicker size="large" className="w-full input-luxury" format="HH:mm"
                  value={discountForm.slot_start ? dayjs(discountForm.slot_start, 'HH:mm') : null}
                  onChange={(t) => setDiscountForm(prev => ({ ...prev, slot_start: t ? t.format('HH:mm') : '' }))} />
              </Col>
              <Col span={12}>
                <span className="label-field">Время конца слота</span>
                <TimePicker size="large" className="w-full input-luxury" format="HH:mm"
                  value={discountForm.slot_end ? dayjs(discountForm.slot_end, 'HH:mm') : null}
                  onChange={(t) => setDiscountForm(prev => ({ ...prev, slot_end: t ? t.format('HH:mm') : '' }))} />
              </Col>
            </Row>
          )}

          {/* Услуга — для service */}
          {discountForm.type === 'service' && (
            <div>
              <span className="label-field">Услуга *</span>
              <Select size="large" className="w-full" placeholder="Выберите услугу"
                value={discountForm.service_id}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, service_id: v }))}>
                {allServices.map((s) => (<Option key={s.id} value={s.id}>{s.name} — {s.price} ₽</Option>))}
              </Select>
            </div>
          )}

          {/* Клиент — для client */}
          {discountForm.type === 'client' && (
            <div>
              <span className="label-field">Клиент *</span>
              <Select size="large" className="w-full" placeholder="Выберите клиента" showSearch
                value={discountForm.client_id}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, client_id: v }))}
                filterOption={(input, option) => (option?.label as string || '').toLowerCase().includes(input.toLowerCase())}>
                {allUsers.filter(u => u.role === 'client').map((u) => (
                  <Option key={u.id} value={u.id} label={`${u.full_name} (${u.phone})`}>
                    👤 {u.full_name} · {u.phone}
                  </Option>
                ))}
              </Select>
            </div>
          )}

          {/* Сегмент — для segment */}
          {discountForm.type === 'segment' && (
            <div>
              <span className="label-field">Сегмент клиентов *</span>
              <Select size="large" className="w-full" placeholder="Выберите сегмент"
                value={discountForm.segment}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, segment: v }))}>
                <Option value="vip">⭐ VIP</Option>
                <Option value="loyal">💎 Лояльные</Option>
                <Option value="regular">🔄 Постоянные</Option>
                <Option value="new">🆕 Новые</Option>
                <Option value="sleeping">😴 Спящие</Option>
                <Option value="lost">🚫 Ушедшие</Option>
              </Select>
            </div>
          )}

          {/* Срок действия */}
          <div>
            <span className="label-field">Срок действия (до)</span>
            <DatePicker size="large" className="w-full input-luxury"
              value={discountForm.valid_until ? dayjs(discountForm.valid_until) : null}
              onChange={(d) => setDiscountForm(prev => ({ ...prev, valid_until: d ? d.format('YYYY-MM-DD') : '' }))} />
          </div>

          {/* Статус (Активна/Неактивна) */}
          <div className="flex-space-between" style={{ padding: '8px 0' }}>
            <Text className="text-titanium">Статус скидки</Text>
            <Space>
              <Switch
                checked={discountForm.is_active}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, is_active: v }))}
                checkedChildren="Активна"
                unCheckedChildren="Неактивна"
              />
            </Space>
          </div>

          {/* Конструктор условий — frequency */}
          {discountForm.type === 'frequency' && (
            <div>
              <span className="label-field">Минимальное количество визитов</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={100}
                value={discountForm.minVisits}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, minVisits: v || 1 }))}
                style={{ width: '100%' }}
              />
            </div>
          )}

          {/* Конструктор условий — win_back */}
          {discountForm.type === 'win_back' && (
            <div>
              <span className="label-field">Максимум дней без записи</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={365}
                value={discountForm.maxRecencyDays}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, maxRecencyDays: v || 30 }))}
                style={{ width: '100%' }}
              />
              <Text className="text-titanium text-12 d-block" style={{ marginTop: 4 }}>
                Если клиент не был больше указанного количества дней — применяется скидка
              </Text>
            </div>
          )}

          {/* Конструктор условий — cashback */}
          {discountForm.type === 'cashback' && (
            <div>
              <span className="label-field">Процент кэшбэка</span>
              <InputNumber
                size="large"
                className="w-full input-luxury"
                min={1}
                max={100}
                value={discountForm.pointsPercent}
                onChange={(v) => setDiscountForm(prev => ({ ...prev, pointsPercent: v || 1 }))}
                style={{ width: '100%' }}
              />
              <Text className="text-titanium text-12 d-block" style={{ marginTop: 4 }}>
                Сколько процентов от суммы записи начислять баллами
              </Text>
            </div>
          )}

          <Button type="primary" size="large" className="btn-gold" onClick={handleSaveDiscount} loading={discountSaving}>
            {editingDiscount ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>

      {/* ===== BOX SETTINGS MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">⚙️ Настройка боксов</Text>}
        open={boxSettingsModal}
        onCancel={() => { setBoxSettingsModal(false); setNewBoxName(''); setNewBoxColor(''); }}
        footer={null}
        width={600}
        className="modal-command"
        afterOpenChange={async (open) => {
          if (open) {
            const data = await apiFetch<any[]>('/api/boxes');
            setBoxesFull(data);
            const init: Record<number, number[]> = {};
            data.forEach((b: any) => { init[b.id] = b.service_ids || []; });
            setBoxEditServices(init);
            setNewBoxName('');
            setNewBoxColor('');
          }
        }}
      >
        <Spin spinning={boxSettingsSaving || creatingBox}>
          {/* Create new box */}
          <Card size="small" className="card-luxury" style={{ marginBottom: 16 }}>
            <Text className="text-white text-14 d-block mb-8" style={{ textAlign: 'center' }}>➕ Создать новый бокс</Text>
            <Space direction="vertical" style={{ width: '100%' }} size="middle">
              {/* Капсула-предпросмотр с инлайн-вводом */}
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <div
                  style={{
                    backgroundColor: normalizeColor(newBoxColor) || '#4DABF7',
                    borderRadius: 30,
                    padding: '6px 16px',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 8,
                    border: '2px solid rgba(255,255,255,0.15)',
                    minWidth: 240,
                    flexWrap: 'wrap',
                    justifyContent: 'center',
                  }}
                >
                  <Input
                    value={newBoxName}
                    onChange={(e) => setNewBoxName(e.target.value)}
                    placeholder="Название бокса"
                    style={{
                      background: 'transparent',
                      border: 'none',
                      color: isLightColor(normalizeColor(newBoxColor)) ? '#000000' : '#FFFFFF',
                      fontWeight: 600,
                      fontSize: 16,
                      minWidth: 100,
                      flex: 1,
                      outline: 'none',
                      boxShadow: 'none',
                    }}
                  />
                  <Input
                    value={newBoxColor}
                    onChange={(e) => setNewBoxColor(e.target.value)}
                    placeholder="#C8A977"
                    style={{
                      background: 'rgba(255,255,255,0.15)',
                      border: 'none',
                      color: isLightColor(normalizeColor(newBoxColor)) ? '#000000' : '#FFFFFF',
                      fontSize: 12,
                      width: 80,
                      borderRadius: 12,
                      padding: '4px 8px',
                      outline: 'none',
                      boxShadow: 'none',
                    }}
                  />
                  <ColorPicker
                    value={normalizeColor(newBoxColor) || '#4DABF7'}
                    onChange={(color) => setNewBoxColor(color.toHexString())}
                    size="small"
                  />
                </div>
              </div>
              <div style={{ display: 'flex', justifyContent: 'center' }}>
                <Button
                  className="btn-gold"
                  onClick={handleCreateBox}
                  loading={creatingBox}
                  style={{ width: 200 }}
                >Создать</Button>
              </div>
            </Space>
          </Card>

          {boxesFull.length === 0 ? (
            <Text className="text-titanium text-13">Нет боксов. Создайте первый бокс выше.</Text>
          ) : (
            <Space direction="vertical" size="large" style={{ width: '100%' }}>
              {boxesFull.map((box: any) => (
                <Card key={box.id} size="small" className="card-luxury">
                  <Space direction="vertical" style={{ width: '100%' }}>
                    <div className="flex-space-between">
                      <Space>
                        <Tooltip
                          title={`Услуги: ${(box.service_ids || []).map((sid: number) => services.find(s => s.id === sid)?.name).filter(Boolean).join(', ') || 'не выбраны'}`}
                          mouseEnterDelay={0.5}
                        >
                          <Text className="text-white text-14">{box.name}</Text>
                        </Tooltip>
                        <Tag color={box.is_active ? 'green' : 'default'}>
                          {box.is_active ? 'Активен' : 'Неактивен'}
                        </Tag>
                      </Space>
                      <Space>
                        <Button
                          icon={<EditOutlined />}
                          onClick={() => openEditBoxModal(box)}
                          style={{
                            backgroundColor: 'transparent',
                            border: '1px solid rgba(255,255,255,0.1)',
                            color: '#C8A977',
                            fontSize: 13,
                            height: 32,
                          }}
                        >
                          Редактировать
                        </Button>
                        <Popconfirm
                          title={`Удалить бокс «${box.name}»?`}
                          description="Записи в этом боксе останутся, но бокс будет удалён."
                          onConfirm={() => handleDeleteBox(box.id, box.name)}
                          okText="Да, удалить" cancelText="Отмена" okButtonProps={{ danger: true }}
                        >
                          <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                        </Popconfirm>
                      </Space>
                    </div>
                    <div>
                      <Text className="text-titanium text-12 d-block mb-4">Привязанные услуги</Text>
                      <Select
                        mode="multiple"
                        size="small"
                        className="w-full input-luxury"
                        placeholder="Выберите услуги"
                        value={boxEditServices[box.id] || []}
                        onChange={(vals) => setBoxEditServices(prev => ({ ...prev, [box.id]: vals }))}
                        style={{ width: '100%' }}
                      >
                        {allServices.map((s) => (
                          <Option key={s.id} value={s.id}>{s.name}</Option>
                        ))}
                      </Select>
                      {(boxEditServices[box.id] || []).length > 0 && (
                        <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                          {(boxEditServices[box.id] || []).map((sid: number) => {
                            const svc = services.find(s => s.id === sid);
                            return svc ? (
                              <Tag key={svc.id} color={box.color || '#C8A977'} style={{ borderRadius: 4 }}>
                                {svc.name}
                              </Tag>
                            ) : null;
                          })}
                        </div>
                      )}
                    </div>
                    <Button
                      size="small"
                      className="btn-gold"
                      style={{ alignSelf: 'flex-end' }}
                      onClick={() => handleSaveBoxSettings(box.id, boxEditServices[box.id] || [])}
                      loading={boxSettingsSaving}
                    >Сохранить</Button>
                  </Space>
                </Card>
              ))}
            </Space>
          )}
        </Spin>
      </Modal>

      {/* ===== EDIT BOX MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">✏️ Редактировать бокс</Text>}
        open={editBoxModalOpen}
        onCancel={() => { setEditBoxModalOpen(false); setEditingBox(null); }}
        footer={null}
        width={480}
        className="modal-command"
      >
        {editingBox && (
          <Space direction="vertical" size="middle" style={{ width: '100%' }}>
            <div>
              <span className="label-field">Название</span>
              <Input
                size="large"
                className="input-luxury"
                placeholder="Название бокса"
                value={editingBox.name}
                onChange={(e) => setEditingBox((prev: any) => ({ ...prev, name: e.target.value }))}
              />
            </div>
            <div>
              <span className="label-field">Цвет</span>
              <Input
                size="large"
                className="input-luxury"
                placeholder="#C8A977"
                value={editingBox.color || ''}
                onChange={(e) => setEditingBox((prev: any) => ({ ...prev, color: e.target.value }))}
              />
            </div>
            <div>
              <Tooltip title="Выберите услуги, которые доступны в этом боксе" mouseEnterDelay={0.5}>
                <span className="label-field">Привязанные услуги</span>
              </Tooltip>
              <Select
                mode="multiple"
                size="large"
                className="w-full input-luxury"
                placeholder="Выберите услуги"
                value={boxEditServices[editingBox.id] || []}
                onChange={(vals) => setBoxEditServices(prev => ({ ...prev, [editingBox.id]: vals }))}
                style={{ width: '100%' }}
              >
                {allServices.map((s) => (
                  <Option key={s.id} value={s.id}>{s.name}</Option>
                ))}
              </Select>
              {(boxEditServices[editingBox.id] || []).length > 0 && (
                <div style={{ marginTop: 8, display: 'flex', flexWrap: 'wrap', gap: 6 }}>
                  {(boxEditServices[editingBox.id] || []).map((sid: number) => {
                    const svc = services.find(s => s.id === sid);
                    return svc ? (
                      <Tag key={svc.id} color={editingBox.color || '#C8A977'} style={{ borderRadius: 4 }}>
                        {svc.name}
                      </Tag>
                    ) : null;
                  })}
                </div>
              )}
            </div>
            <Button
              type="primary"
              size="large"
              className="btn-gold"
              onClick={handleEditBox}
              loading={boxSettingsSaving}
            >Сохранить</Button>
          </Space>
        )}
      </Modal>

      {/* ===== HEATMAP SLOT DETAIL MODAL ===== */}
      <Modal
        title={<Text className="text-gold-bold">📅 {heatmapSlotLabel}</Text>}
        open={heatmapModalOpen}
        onCancel={() => setHeatmapModalOpen(false)}
        footer={null}
        className="modal-command"
        width={520}
      >
        {heatmapSlotAppts.length === 0 ? (
          <div style={{ padding: '24px 0', textAlign: 'center' }}>
            <Text className="text-titanium">Нет записей в этот слот</Text>
          </div>
        ) : (
          <List
            dataSource={heatmapSlotAppts}
            renderItem={(item) => (
              <List.Item style={{ padding: '10px 0', borderBottom: '1px solid rgba(255,255,255,0.06)' }}>
                <Space direction="vertical" size={2} style={{ width: '100%' }}>
                  <Space>
                    <Text className="text-white-bold text-13">{item.service_name || `Услуга #${item.service_id}`}</Text>
                    <Tag color={STATUS_COLORS[item.status]} className="tag-status">
                      {STATUS_LABELS[item.status]}
                    </Tag>
                  </Space>
                  <Space size="small">
                    {item.client && <Text className="text-titanium text-12">👤 {item.client.full_name}</Text>}
                    {item.master && <Text className="text-titanium text-12">🔧 {item.master.full_name}</Text>}
                  </Space>
                  <div className="flex-space-between">
                    <Text className="text-titanium text-12">
                      🕐 {dayjs(item.start_time).format('HH:mm')} — {dayjs(item.end_time).format('HH:mm')}
                    </Text>
                    <Text className="text-gold-bold text-13">{formatCurrency(item.total_price)}</Text>
                  </div>
                </Space>
              </List.Item>
            )}
          />
        )}
      </Modal>
      </Layout>

      {/* Нижняя навигация (моб) */}
      <div className="bottom-nav">
        {bottomNavItems.map(item => (
          <button
            key={item.key}
            className={`bottom-nav-item${activeTab === item.key ? ' active' : ''}`}
            onClick={() => { setActiveTab(item.key); }}
          >
            <span className="bottom-nav-icon">{item.icon}</span>
            <span className="bottom-nav-label">{item.label}</span>
          </button>
        ))}
      </div>
    </Layout>
  );
}
