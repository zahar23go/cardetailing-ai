import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Typography, Card, Row, Col, Statistic, Table, Button, Tag, Space, Tabs,
  message, Modal, Select, Input, Popconfirm, Badge, Layout, List,
  Empty, Spin, Tooltip, DatePicker, TimePicker, Switch,
} from 'antd';
import {
  CrownOutlined, ToolOutlined,
  CalendarOutlined, DollarOutlined, ClockCircleOutlined,
  TeamOutlined, DeleteOutlined, EditOutlined,
  PlusOutlined, LogoutOutlined, ReloadOutlined, PhoneOutlined,
  BulbOutlined, SendOutlined, AreaChartOutlined,
  GiftOutlined, StarOutlined, BellOutlined,
  BarChartOutlined,
} from '@ant-design/icons';
import NotificationBell from './components/NotificationBell';
import NotificationList from './components/NotificationList';
import NotificationSettings from './components/NotificationSettings';
import MasterCalendar from './components/MasterCalendar';
import ReportManager from './components/ReportManager';
import ServiceAnalytics from './components/ServiceAnalytics';
import {
  AreaChart, Area, XAxis, YAxis, CartesianGrid, Tooltip as RechartsTooltip,
  ResponsiveContainer, FunnelChart, Funnel, LabelList,
} from 'recharts';
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
  const [apptsTotal, setApptsTotal] = useState(0);
  const [apptsPage, setApptsPage] = useState(1);

  const [services, setServices] = useState<Service[]>([]);
  const [servicesLoading, setServicesLoading] = useState(false);
  const [servicesTotal, setServicesTotal] = useState(0);
  const [servicesPage, setServicesPage] = useState(1);

  const [users, setUsers] = useState<RfmClient[]>([]);
  const [usersLoading, setUsersLoading] = useState(false);
  const [allUsers, setAllUsers] = useState<User[]>([]);
  const [userRoleTab, setUserRoleTab] = useState<string>('clients');

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

  // Financier chat state
  const [financierMessages, setFinancierMessages] = useState<{role: 'user' | 'ai'; text: string}[]>([]);
  const [financierInput, setFinancierInput] = useState('');
  const [financierLoading, setFinancierLoading] = useState(false);

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
    name: '', type: 'happy_hours', conditions: '{}',
    discount_percent: 0, slot_start: '', slot_end: '',
    service_id: undefined as number | undefined,
    client_id: undefined as number | undefined,
    valid_until: '',
    is_active: true,
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

  // Period selector state
  const [periodStart, setPeriodStart] = useState<string | null>(null);
  const [periodEnd, setPeriodEnd] = useState<string | null>(null);

  // Fetch all data
  useEffect(() => {
    fetchKpi();
    fetchAppointments();
    fetchServices();
    fetchUsers();
    fetchAllUsers();
    fetchExpenses();
    fetchPL();
    fetchRevenueChart();
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

  const fetchAppointments = async (page = apptsPage) => {
    setApptsLoading(true);
    try {
      const skip = (page - 1) * PAGE_SIZE;
      const data = await apiFetch<{items: Appointment[]; total: number}>(`/api/appointments?skip=${skip}&limit=${PAGE_SIZE}`);
      setAppointments(data.items);
      setApptsTotal(data.total);
      setApptsPage(page);
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
      if (start && end) {
        path += `?start_date=${start}&end_date=${end}`;
      }
      const data = await apiFetch<RevenueData>(path);
      setRevenueData(data);
    } catch { /* ignore */ }
    setRevenueLoading(false);
  };

  const fetchHeatmap = async (boxId?: number) => {
    setHeatmapLoading(true);
    try {
      let path = '/api/analytics/heatmap';
      if (boxId !== undefined) {
        path += `?box_id=${boxId}`;
      }
      const data = await apiFetch<{cells: HeatmapCell[]; boxes: BoxItem[]}>(path);
      setHeatmapData(data.cells);
      if (data.boxes) setBoxes(data.boxes);
    } catch { /* ignore */ }
    setHeatmapLoading(false);
  };

  const fetchFunnel = async () => {
    setFunnelLoading(true);
    try {
      const data = await apiFetch<FunnelData>('/api/analytics/funnel');
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
      setDiscountForm({
        name: rule.name,
        type: rule.type,
        conditions: JSON.stringify(rule.conditions || {}, null, 2),
        discount_percent: rule.discount_percent,
        slot_start: rule.slot_start || '',
        slot_end: rule.slot_end || '',
        service_id: rule.service_id || undefined,
        client_id: rule.client_id || undefined,
        valid_until: rule.valid_until || '',
        is_active: rule.is_active,
      });
    } else {
      setEditingDiscount(null);
      setDiscountForm({
        name: '', type: 'happy_hours', conditions: '{}',
        discount_percent: 0, slot_start: '', slot_end: '',
        service_id: undefined,
        client_id: undefined,
        valid_until: '',
        is_active: true,
      });
    }
    setDiscountModal(true);
  };

  const handleSaveDiscount = async () => {
    if (!discountForm.name.trim()) { message.warning('Укажите название правила'); return; }
    if (!discountForm.discount_percent) { message.warning('Укажите процент скидки'); return; }
    setDiscountSaving(true);
    try {
      let conditions: Record<string, any> = {};
      try { conditions = JSON.parse(discountForm.conditions); } catch { conditions = {}; }
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

  const DISCOUNT_TYPE_LABELS: Record<string, string> = {
    happy_hours: 'Happy Hours',
    service: 'На услугу',
    client: 'Персональная',
    frequency: 'За частоту',
    win_back: 'Возврат',
    cashback: 'Кэшбек',
  };

  const DISCOUNT_TYPE_COLORS: Record<string, string> = {
    happy_hours: 'blue',
    service: 'gold',
    client: 'purple',
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

  /* ---------- Financier AI ---------- */
  const handleFinancierQuestion = async () => {
    const question = financierInput.trim();
    if (!question) return;
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
          <NotificationBell />
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
                <Text className="text-titanium">Всего: {apptsTotal}</Text>
                <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchAppointments(apptsPage)} type="text" className="btn-logout" />
              </div>
              {appointments.length === 0 && !apptsLoading ? (
                <Empty description={<Text className="text-titanium">Нет записей</Text>} />
              ) : (
                <List
                  dataSource={appointments}
                  pagination={{
                    current: apptsPage,
                    pageSize: PAGE_SIZE,
                    total: apptsTotal,
                    onChange: (page) => fetchAppointments(page),
                    showSizeChanger: false,
                    size: 'small',
                  }}
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
                  pagination={{
                    current: servicesPage,
                    pageSize: PAGE_SIZE,
                    total: servicesTotal,
                    onChange: (page) => fetchServices(page),
                    showSizeChanger: false,
                  }}
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
            {/* Role tabs */}
            <Tabs activeKey={userRoleTab} onChange={setUserRoleTab}
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
                          title: <Text className="text-titanium">Сегмент</Text>,
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
                          title: <Text className="text-titanium">Визиты</Text>,
                          dataIndex: 'frequency',
                          key: 'frequency',
                          width: 70,
                          render: (val) => <Text className="text-white text-13">{val}</Text>,
                        },
                        {
                          title: <Text className="text-titanium">Сумма</Text>,
                          dataIndex: 'monetary',
                          key: 'monetary',
                          width: 100,
                          render: (val) => <Text className="text-gold-bold text-13">{val.toLocaleString()} ₽</Text>,
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
                          width: 140,
                          render: (val: string) => <Tag color="cyan" className="tag-status">{ROLE_LABELS[val] || val}</Tag>,
                        },
                        {
                          title: <Text className="text-titanium">Дата рег.</Text>,
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
                          width: 160,
                          render: (val: string) => <Tag color="gold" className="tag-status">{ROLE_LABELS[val] || val}</Tag>,
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
            <Card className="card-luxury">
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
                {financierMessages.length === 0 ? (
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

              {/* Expenses */}
              <Card className="card-luxury">
                <div className="flex-space-between mb-12">
                  <Text className="title-gold text-16">Постоянные расходы</Text>
                  <Button size="small" icon={<PlusOutlined />} className="btn-action-gold" onClick={() => setExpenseModal(true)}>Добавить</Button>
                </div>
                {expenses.length === 0 ? (
                  <Text className="text-titanium text-13">Нет расходов за месяц</Text>
                ) : (
                  <Table
                    dataSource={expenses}
                    rowKey="id"
                    pagination={{
                      current: expensesPage,
                      pageSize: PAGE_SIZE,
                      total: expensesTotal,
                      onChange: (page) => fetchExpenses(page),
                      showSizeChanger: false,
                    }}
                    size="small"
                    columns={[
                      { title: <Text className="text-titanium text-12">Название</Text>, dataIndex: 'name', key: 'name',
                        render: v => <Text className="text-white text-13">{v}</Text> },
                      { title: <Text className="text-titanium text-12">Категория</Text>, dataIndex: 'category', key: 'cat', width: 110,
                        render: v => <Tag className="tag-category">{v}</Tag> },
                      { title: <Text className="text-titanium text-12">Сумма</Text>, dataIndex: 'amount', key: 'amount', width: 110,
                        render: v => <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text> },
                      { title: <Text className="text-titanium text-12">Дата</Text>, dataIndex: 'expense_date', key: 'date', width: 100,
                        render: v => <Text className="text-titanium text-13">{v ? dayjs(v).format('DD.MM') : '—'}</Text> },
                      { title: '', key: 'actions', width: 50,
                        render: (_, r) => (
                          <Popconfirm title={`Удалить «${r.name}»?`} onConfirm={() => handleDeleteExpense(r.id, r.name)} okText="Да" cancelText="Нет">
                            <Button size="small" icon={<DeleteOutlined />} className="btn-action-danger" />
                          </Popconfirm>
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
            </Spin>
          </TabPane>

          {/* ===== TAB 7: ANALYTICS CHARTS ===== */}
          <TabPane tab={<span><AreaChartOutlined /> Аналитика</span>} key="analytics">
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
                        <Button size="small" icon={<ReloadOutlined />} onClick={fetchFunnel} type="text" className="btn-logout" />
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
                          {boxes.map((b) => (
                            <Option key={b.id} value={b.id}>
                              {b.name}
                            </Option>
                          ))}
                        </Select>
                        <Button size="small" icon={<ReloadOutlined />} onClick={() => fetchHeatmap(selectedBoxId)} type="text" className="btn-logout" />
                      </Space>
                    </div>
                    {heatmapData.length > 0 ? (
                      <>
                        <div className="flex-space-between" style={{ marginBottom: 8, paddingLeft: 40 }}>
                          {[9,10,11,12,13,14,15,16,17,18,19,20].map(h => (
                            <Text key={h} className="text-titanium text-11" style={{ width: '8.33%', textAlign: 'center' }}>{h}:00</Text>
                          ))}
                        </div>
                        {[0,1,2,3,4,5,6].map(day => {
                          const dayNames = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];
                          const maxCount = Math.max(...heatmapData.map(c => c.count), 1);
                          return (
                            <div key={day} className="flex-space-between" style={{ marginBottom: 4 }}>
                              <Text className="text-titanium text-11" style={{ width: 36 }}>{dayNames[day]}</Text>
                              {[9,10,11,12,13,14,15,16,17,18,19,20].map(hour => {
                                const cell = heatmapData.find(c => c.day === day && c.hour === hour);
                                const count = cell?.count || 0;
                                const intensity = count / maxCount;
                                const bgColor = count > 0
                                  ? `rgba(200, 169, 119, ${0.1 + intensity * 0.6})`
                                  : 'rgba(255,255,255,0.02)';
                                return (
                                  <div
                                    key={`${day}-${hour}`}
                                    className="text-center"
                                    style={{
                                      width: '8.33%', height: 32, backgroundColor: bgColor,
                                      borderRadius: 4, display: 'flex', alignItems: 'center',
                                      justifyContent: 'center',
                                    }}
                                    title={count > 0 ? `${count} записей · ${cell?.revenue.toLocaleString()} ₽` : ''}
                                  >
                                    <Text className="text-11" style={{ color: count > maxCount * 0.5 ? '#0B0D10' : '#AAB2BF' }}>
                                      {count || ''}
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
            <Spin spinning={discountsLoading || loyaltyLoading}>
              <div className="toolbar-right mb-12">
                <Button type="primary" icon={<PlusOutlined />} className="btn-gold" style={{ width: 'auto' }}
                  onClick={() => openDiscountModal()}>Создать правило</Button>
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

      {/* ===== EXPENSE MODAL ===== */}
      <Modal
        title={<Text className="text-white">➕ Добавить расход</Text>}
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
        title={<Text className="text-white">{editingDiscount ? '✏️ Редактировать правило скидки' : '➕ Новое правило скидки'}</Text>}
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
                {services.map((s) => (<Option key={s.id} value={s.id}>{s.name}</Option>))}
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

          {/* Условия (JSON) — для всех, кроме happy_hours */}
          {discountForm.type !== 'happy_hours' && (
            <div>
              <span className="label-field">Условия (JSON)</span>
              <TextArea rows={3} className="input-luxury" placeholder='{"min_visits": 3}'
                value={discountForm.conditions}
                onChange={(e) => setDiscountForm(prev => ({ ...prev, conditions: e.target.value }))} />
            </div>
          )}

          {/* Подсказки по типам — для всех, кроме happy_hours */}
          {discountForm.type !== 'happy_hours' && (
            <div>
              <Text className="text-titanium text-12 d-block mb-8">
                <span className="text-gold">happy_hours:</span> слот задаётся выше ↑<br />
                <span className="text-gold">service:</span> услуга выше ↑<br />
                <span className="text-gold">client:</span> клиент выше ↑<br />
                <span className="text-gold">frequency:</span> {'{'} "min_visits": 3 {'}'}<br />
                <span className="text-gold">win_back:</span> {'{'} "max_recency_days": 60 {'}'}<br />
                <span className="text-gold">cashback:</span> {'{'} "points_percent": 5 {'}'}<br />
                <span className="text-gold">Любой тип:</span> {'{'} "min_price": 500 {'}'} — минимальная цена после скидки
              </Text>
            </div>
          )}
          <Button type="primary" size="large" className="btn-gold" onClick={handleSaveDiscount} loading={discountSaving}>
            {editingDiscount ? 'Сохранить' : 'Создать'}
          </Button>
        </Space>
      </Modal>
    </Layout>
  );
}
