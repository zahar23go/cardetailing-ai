/**
 * Записи — /upload/records
 * Локальный state: список, фильтры, модалка статуса. Без OwnerDashboard Context.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';
import { motion } from 'framer-motion';
import {
  Typography,
  Card,
  Row,
  Col,
  Tag,
  Space,
  Select,
  Popconfirm,
  Empty,
  Spin,
  Tooltip,
  DatePicker,
  List,
  message,
} from 'antd';
import { Button, Modal, Input } from '../../../components/ui';
import {
  ToolOutlined, CalendarOutlined, ClockCircleOutlined, ReloadOutlined,
  CarOutlined, UserOutlined, SearchOutlined, PlayCircleOutlined,
  CheckCircleOutlined, CloseCircleOutlined, EditOutlined, FileTextOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/ru';
import CloseVisitModal from '../../../components/CloseVisitModal';

dayjs.locale('ru');

const { Text } = Typography;
const { Option } = Select;
const { TextArea } = Input;

const API_BASE = '';
const APPT_ACTIVE_STATUSES = ['pending', 'confirmed', 'in_progress'];
const APPT_FETCH_LIMIT = 500;
const APPT_LIST_PAGE_SIZE = 10;

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

interface MasterUser {
  id: number;
  full_name: string;
  role: string;
}

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

function formatCurrency(val: number) {
  return `${val.toLocaleString()} ₽`;
}

function formatStatusAge(appt: Appointment): string {
  const from = appt.updated_at || appt.created_at || appt.start_time;
  const mins = Math.max(0, dayjs().diff(dayjs(from), 'minute'));
  if (mins < 60) return `${mins} мин`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} ч`;
  return `${Math.floor(hours / 24)} д`;
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

export default function RecordsPage() {
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [apptsLoading, setApptsLoading] = useState(false);
  const [apptsTotal, setApptsTotal] = useState(0);
  const [apptsPage, setApptsPage] = useState(1);
  const [apptStatusFilter, setApptStatusFilter] = useState('all');
  const [apptMasterFilter, setApptMasterFilter] = useState<number | 'all'>('all');
  const [apptPeriodFilter, setApptPeriodFilter] = useState('all');
  const [apptCustomRange, setApptCustomRange] = useState<[Dayjs, Dayjs] | null>(null);
  const [apptSearchClient, setApptSearchClient] = useState('');
  const [apptSearchCar, setApptSearchCar] = useState('');
  const [apptSort, setApptSort] = useState('active_first');

  const [masters, setMasters] = useState<MasterUser[]>([]);

  const [apptStatusModal, setApptStatusModal] = useState(false);
  const [selectedAppt, setSelectedAppt] = useState<Appointment | null>(null);
  const [apptNewStatus, setApptNewStatus] = useState('');
  const [apptMasterId, setApptMasterId] = useState<number | undefined>(undefined);
  const [apptBrief, setApptBrief] = useState('');
  const [closeAppt, setCloseAppt] = useState<Appointment | null>(null);

  const fetchAppointments = useCallback(async () => {
    setApptsLoading(true);
    try {
      const data = await apiFetch<{ items: Appointment[]; total: number }>(
        `/api/appointments?skip=0&limit=${APPT_FETCH_LIMIT}`,
      );
      setAppointments(data.items);
      setApptsTotal(data.total);
      setApptsPage(1);
    } catch {
      message.error('Ошибка загрузки записей');
    }
    setApptsLoading(false);
  }, []);

  const fetchMasters = useCallback(async () => {
    try {
      const data = await apiFetch<{ items: MasterUser[] }>('/api/users?limit=500');
      setMasters(data.items.filter((u) => u.role === 'master'));
    } catch { /* ignore */ }
  }, []);

  useEffect(() => {
    fetchAppointments();
    fetchMasters();
  }, [fetchAppointments, fetchMasters]);

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
      const body: Record<string, unknown> = {};
      if (apptNewStatus !== selectedAppt.status) body.status = apptNewStatus;
      if (apptMasterId !== selectedAppt.master_id) body.master_id = apptMasterId;
      if (apptBrief !== (selectedAppt.master_brief || '')) body.master_brief = apptBrief;
      if (Object.keys(body).length === 0) {
        setApptStatusModal(false);
        return;
      }
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

  const applyApptWidgetFilter = (key: string) => {
    setApptsPage(1);
    if (key === 'total') {
      setApptStatusFilter('all');
      setApptPeriodFilter('all');
      return;
    }
    if (key === 'in_progress') {
      setApptStatusFilter('in_progress');
      setApptPeriodFilter('all');
      return;
    }
    if (key === 'waiting') {
      setApptStatusFilter('waiting');
      setApptPeriodFilter('all');
      return;
    }
    if (key === 'completed_week') {
      setApptStatusFilter('completed');
      setApptPeriodFilter('week');
      return;
    }
    if (key === 'cancelled') {
      setApptStatusFilter('cancelled');
      setApptPeriodFilter('all');
    }
  };

  const clearApptFilters = () => {
    setApptStatusFilter('all');
    setApptMasterFilter('all');
    setApptPeriodFilter('all');
    setApptCustomRange(null);
    setApptSearchClient('');
    setApptSearchCar('');
    setApptSort('active_first');
    setApptsPage(1);
  };

  const toggleApptSort = (column: 'date' | 'client' | 'master' | 'status' | 'price') => {
    setApptsPage(1);
    if (column === 'date') {
      setApptSort((prev) => (prev === 'date_desc' ? 'date_asc' : 'date_desc'));
      return;
    }
    if (column === 'client') {
      setApptSort((prev) => (prev === 'client_asc' ? 'client_desc' : 'client_asc'));
      return;
    }
    if (column === 'master') {
      setApptSort((prev) => (prev === 'master' ? 'master_desc' : 'master'));
      return;
    }
    if (column === 'status') {
      setApptSort((prev) => (prev === 'status_asc' ? 'status_desc' : 'status_asc'));
      return;
    }
    setApptSort((prev) => (prev === 'price_desc' ? 'price_asc' : 'price_desc'));
  };

  const apptSortArrow = (column: 'date' | 'client' | 'master' | 'status' | 'price') => {
    const map: Record<string, string[]> = {
      date: ['date_desc', 'date_asc'],
      client: ['client_asc', 'client_desc'],
      master: ['master', 'master_desc'],
      status: ['status_asc', 'status_desc'],
      price: ['price_desc', 'price_asc'],
    };
    const keys = map[column];
    if (!keys.includes(apptSort)) return '';
    if (apptSort.endsWith('_asc') || apptSort === 'master') return ' ↑';
    return ' ↓';
  };

  const filteredAppointments = useMemo(() => {
    let list = [...appointments];

    if (apptStatusFilter === 'active') {
      list = list.filter((a) => APPT_ACTIVE_STATUSES.includes(a.status));
    } else if (apptStatusFilter === 'waiting') {
      list = list.filter((a) => a.status === 'pending' || a.status === 'confirmed');
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
      if (apptSort === 'master' || apptSort === 'master_desc') {
        const an = a.master?.full_name || '';
        const bn = b.master?.full_name || '';
        const cmp = an.localeCompare(bn, 'ru');
        if (cmp !== 0) return apptSort === 'master_desc' ? -cmp : cmp;
      }
      if (apptSort === 'client_asc' || apptSort === 'client_desc') {
        const an = a.client?.full_name || '';
        const bn = b.client?.full_name || '';
        const cmp = an.localeCompare(bn, 'ru');
        if (cmp !== 0) return apptSort === 'client_desc' ? -cmp : cmp;
      }
      if (apptSort === 'status_asc' || apptSort === 'status_desc') {
        const cmp = a.status.localeCompare(b.status);
        if (cmp !== 0) return apptSort === 'status_desc' ? -cmp : cmp;
      }
      if (apptSort === 'price_asc' || apptSort === 'price_desc') {
        const cmp = a.total_price - b.total_price;
        if (cmp !== 0) return apptSort === 'price_desc' ? -cmp : cmp;
      }
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

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Операции</div>
          <h3>Записи клиентов</h3>
        </div>
      </div>

      <Row gutter={[12, 12]} className="appt-stats-row">
        {[
          { key: 'total', label: 'Всего записей', value: apptStats.total, tone: 'gold', active: apptStatusFilter === 'all' && apptPeriodFilter === 'all' },
          { key: 'in_progress', label: 'В работе', value: apptStats.in_progress, tone: 'ok', active: apptStatusFilter === 'in_progress' },
          { key: 'waiting', label: 'Ожидают', value: apptStats.waiting, tone: 'warn', active: apptStatusFilter === 'waiting' },
          { key: 'completed_week', label: 'Завершено за нед.', value: apptStats.completed_week, tone: 'gold', active: apptStatusFilter === 'completed' && apptPeriodFilter === 'week' },
          { key: 'cancelled', label: 'Отменено', value: apptStats.cancelled, tone: 'danger', active: apptStatusFilter === 'cancelled' },
        ].map((m) => (
          <Col xs={12} sm={8} md={4} flex="1 1 140px" key={m.key}>
            <Card
              className={`admin-kpi-card tone-${m.tone} appt-stat-card${m.active ? ' is-active' : ''}`}
              bordered={false}
              onClick={() => applyApptWidgetFilter(m.key)}
              role="button"
              tabIndex={0}
              onKeyDown={(e) => {
                if (e.key === 'Enter' || e.key === ' ') {
                  e.preventDefault();
                  applyApptWidgetFilter(m.key);
                }
              }}
            >
              <div className="admin-kpi-label">{m.label}</div>
              <div className="admin-kpi-value">{m.value}</div>
            </Card>
          </Col>
        ))}
      </Row>

      <div className="appt-filters">
        <div className="appt-filters-label">Фильтры</div>
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
            <Option value="waiting">Ожидают</Option>
            <Option value="pending">Ожидание</Option>
            <Option value="confirmed">Подтверждена</Option>
            <Option value="in_progress">В работе</Option>
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
            {masters.map((m) => (
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
                setApptCustomRange(v as [Dayjs, Dayjs] | null);
                setApptsPage(1);
              }}
              className="appt-range-picker"
              format="DD.MM.YYYY"
            />
          )}
          <Select
            value={
              ['active_first', 'date_desc', 'date_asc', 'master', 'master_desc', 'client_asc', 'client_desc', 'status_asc', 'status_desc', 'price_desc', 'price_asc'].includes(apptSort)
                ? apptSort
                : 'active_first'
            }
            onChange={(v) => { setApptSort(v); setApptsPage(1); }}
            className="appt-filter-select"
            style={{ minWidth: 180 }}
          >
            <Option value="active_first">Сначала актуальные</Option>
            <Option value="date_desc">Дата ↓</Option>
            <Option value="date_asc">Дата ↑</Option>
            <Option value="client_asc">Клиент А–Я</Option>
            <Option value="master">Мастер А–Я</Option>
            <Option value="status_asc">По статусу</Option>
            <Option value="price_desc">Цена ↓</Option>
          </Select>
          <Button icon={<ReloadOutlined />} look="ghost" onClick={() => fetchAppointments()}>
            Обновить
          </Button>
          <Button look="ghost" onClick={clearApptFilters}>
            Сбросить
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

        <div className="appt-sort-columns" role="row">
          <button type="button" className="appt-sort-col" onClick={() => toggleApptSort('date')}>
            Дата{apptSortArrow('date')}
          </button>
          <button type="button" className="appt-sort-col" onClick={() => toggleApptSort('client')}>
            Клиент{apptSortArrow('client')}
          </button>
          <button type="button" className="appt-sort-col" onClick={() => toggleApptSort('master')}>
            Мастер{apptSortArrow('master')}
          </button>
          <button type="button" className="appt-sort-col" onClick={() => toggleApptSort('status')}>
            Статус{apptSortArrow('status')}
          </button>
          <button type="button" className="appt-sort-col appt-sort-col-price" onClick={() => toggleApptSort('price')}>
            Цена{apptSortArrow('price')}
          </button>
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
                        look="ghost"
                        icon={<PlayCircleOutlined />}
                        onClick={() => quickUpdateApptStatus(item, 'in_progress')}
                      >
                        В работу
                      </Button>
                    )}
                    {(item.status === 'in_progress' || item.status === 'confirmed') && (
                      <Button
                        size="small"
                        look="gold"
                        icon={<CheckCircleOutlined />}
                        onClick={() => setCloseAppt(item)}
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
                    {item.status === 'completed' && (
                      <Button
                        size="small"
                        look="gold"
                        icon={<FileTextOutlined />}
                        onClick={() => setCloseAppt(item)}
                      >
                        Чек
                      </Button>
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
              <Select size="large" value={apptNewStatus} onChange={setApptNewStatus}>
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
                {masters.map((m) => (
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

            <Space wrap>
              <Button
                type="primary"
                size="large"
                onClick={handleUpdateAppointment}
                look="gold"
              >
                Сохранить
              </Button>
              {selectedAppt.status === 'completed' && (
                <Button
                  size="large"
                  look="ghost"
                  icon={<FileTextOutlined />}
                  onClick={() => {
                    const appt = selectedAppt;
                    setApptStatusModal(false);
                    setCloseAppt(appt);
                  }}
                >
                  Чек
                </Button>
              )}
            </Space>
          </Space>
        )}
      </Modal>

      <CloseVisitModal
        open={Boolean(closeAppt)}
        appointmentId={closeAppt?.id ?? null}
        role="admin"
        onCancel={() => setCloseAppt(null)}
        onClosed={() => {
          setCloseAppt(null);
          fetchAppointments();
        }}
      />
    </>
  );
}
