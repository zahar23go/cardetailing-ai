/* ============================================================
   MasterCalendar — календарь загрузки (неделя/день) в gold-стиле
   ============================================================ */

import React, { useCallback, useEffect, useMemo, useState } from 'react';
import {
  Typography, Spin, Button, Space, message, Select, Segmented, Tooltip,
} from 'antd';
import {
  ReloadOutlined, LeftOutlined, RightOutlined, UserOutlined, CalendarOutlined,
} from '@ant-design/icons';
import dayjs, { Dayjs } from 'dayjs';
import isoWeek from 'dayjs/plugin/isoWeek';
import 'dayjs/locale/ru';

dayjs.extend(isoWeek);
dayjs.locale('ru');

const { Text } = Typography;
const { Option } = Select;

interface CalendarAppt {
  id: number;
  client_name?: string;
  service_name?: string;
  start_time: string;
  end_time: string;
  status: string;
  total_price: number;
  car_info?: string;
  master_id?: number;
  master_name?: string;
}

interface CalendarDay {
  date: string;
  day_of_week: number;
  appointments: CalendarAppt[];
}

interface CalendarData {
  master_id: number;
  master_name: string;
  days: CalendarDay[];
}

interface MasterInfo {
  id: number;
  full_name: string;
  color: string;
}

type ViewMode = 'day' | 'week';

const API_BASE = '';
const HOUR_START = 9;
const HOUR_END = 22;
const HOUR_PX = 56;
const DAY_NAMES = ['ПН', 'ВТ', 'СР', 'ЧТ', 'ПТ', 'СБ', 'ВС'];

const MASTER_COLORS = [
  '#E85D75', '#4ECB71', '#F0A04B', '#5B8DEF',
  '#E85D5D', '#2EC4B6', '#A78BFA', '#D4A84B',
  '#FF8FAB', '#7BDFF2',
];

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  in_progress: 'В работе',
  completed: 'Выполнена',
  cancelled: 'Отменена',
  no_show: 'Неявка',
};

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

function hoursList() {
  const list: number[] = [];
  for (let h = HOUR_START; h <= HOUR_END; h += 1) list.push(h);
  return list;
}

function minutesFromStart(iso: string) {
  const t = dayjs(iso);
  return (t.hour() - HOUR_START) * 60 + t.minute();
}

function apptTopPx(iso: string) {
  return (minutesFromStart(iso) / 60) * HOUR_PX;
}

function apptHeightPx(start: string, end: string) {
  const mins = Math.max(dayjs(end).diff(dayjs(start), 'minute'), 30);
  return (mins / 60) * HOUR_PX;
}

export default function MasterCalendar() {
  const [viewMode, setViewMode] = useState<ViewMode>('week');
  const [anchorDate, setAnchorDate] = useState<Dayjs>(() => dayjs());
  const [loading, setLoading] = useState(false);
  const [masters, setMasters] = useState<MasterInfo[]>([]);
  const [appointments, setAppointments] = useState<CalendarAppt[]>([]);
  const [statusFilter, setStatusFilter] = useState<string>('all');

  const rangeStart = useMemo(
    () => (viewMode === 'week' ? anchorDate.startOf('isoWeek') : anchorDate.startOf('day')),
    [anchorDate, viewMode],
  );
  const rangeEnd = useMemo(
    () => (viewMode === 'week' ? anchorDate.endOf('isoWeek') : anchorDate.endOf('day')),
    [anchorDate, viewMode],
  );

  const days = useMemo(() => {
    if (viewMode === 'day') return [rangeStart];
    return Array.from({ length: 7 }, (_, i) => rangeStart.add(i, 'day'));
  }, [rangeStart, viewMode]);

  const hours = useMemo(() => hoursList(), []);
  const gridHeight = (HOUR_END - HOUR_START + 1) * HOUR_PX;

  const fetchAll = useCallback(async () => {
    setLoading(true);
    try {
      const users = await apiFetch<{ items: { id: number; full_name: string; role: string }[] }>(
        '/api/users?skip=0&limit=100',
      );
      const masterList = users.items
        .filter((u) => u.role === 'master')
        .map((m, i) => ({
          id: m.id,
          full_name: m.full_name,
          color: MASTER_COLORS[i % MASTER_COLORS.length],
        }));
      setMasters(masterList);

      const start = rangeStart.format('YYYY-MM-DD');
      const end = rangeEnd.format('YYYY-MM-DD');

      if (masterList.length === 0) {
        setAppointments([]);
        return;
      }

      const calendars = await Promise.all(
        masterList.map((m) =>
          apiFetch<CalendarData>(`/api/calendar/${m.id}?start_date=${start}&end_date=${end}`)
            .catch(() => null),
        ),
      );

      const nameById = Object.fromEntries(masterList.map((m) => [m.id, m.full_name]));
      const flat: CalendarAppt[] = [];

      calendars.forEach((cal, idx) => {
        if (!cal) return;
        const mid = masterList[idx].id;
        cal.days.forEach((d) => {
          d.appointments.forEach((a) => {
            flat.push({
              ...a,
              master_id: mid,
              master_name: nameById[mid] || cal.master_name,
            });
          });
        });
      });

      setAppointments(flat);
    } catch {
      message.error('Ошибка загрузки календаря');
    } finally {
      setLoading(false);
    }
  }, [rangeStart, rangeEnd]);

  useEffect(() => {
    fetchAll();
  }, [fetchAll]);

  const filtered = useMemo(() => {
    if (statusFilter === 'all') return appointments;
    return appointments.filter((a) => a.status === statusFilter);
  }, [appointments, statusFilter]);

  const masterColor = useMemo(
    () => Object.fromEntries(masters.map((m) => [m.id, m.color])),
    [masters],
  );

  const masterFirstName = (full?: string) => {
    if (!full) return 'Мастер';
    return full.split(' ')[0];
  };

  const shiftRange = (dir: -1 | 1) => {
    setAnchorDate((d) => d.add(dir, viewMode === 'week' ? 'week' : 'day'));
  };

  const rangeLabel = viewMode === 'week'
    ? `${rangeStart.format('D MMMM')} – ${rangeEnd.format('D MMMM YYYY')}`
    : rangeStart.format('D MMMM YYYY, dddd');

  const navLabel = viewMode === 'week'
    ? `${rangeStart.format('YYYY')}-${rangeStart.isoWeek()}нед`
    : rangeStart.format('DD.MM.YYYY');

  const dotsForDay = (day: Dayjs) => {
    const key = day.format('YYYY-MM-DD');
    const ids = new Set(
      filtered
        .filter((a) => dayjs(a.start_time).format('YYYY-MM-DD') === key && a.master_id)
        .map((a) => a.master_id as number),
    );
    return Array.from(ids).slice(0, 5);
  };

  return (
    <div className="workload-calendar">
      <div className="workload-calendar-head">
        <div>
          <div className="admin-overview-kicker">Расписание</div>
          <h3 className="workload-calendar-title">Календарь загрузки</h3>
          <p className="workload-calendar-range">{rangeLabel}</p>
        </div>
      </div>

      <div className="workload-toolbar">
        <Space wrap size={8}>
          <Button icon={<LeftOutlined />} className="btn-gold-secondary" size="small" onClick={() => shiftRange(-1)} />
          <span className="workload-nav-label">
            <CalendarOutlined /> {navLabel}
          </span>
          <Button icon={<RightOutlined />} className="btn-gold-secondary" size="small" onClick={() => shiftRange(1)} />
          <Button icon={<ReloadOutlined />} className="btn-gold-secondary" size="small" onClick={fetchAll} />
        </Space>

        <Space wrap size={8}>
          <Segmented
            className="workload-segmented"
            value={viewMode}
            onChange={(v) => setViewMode(v as ViewMode)}
            options={[
              { label: 'День', value: 'day' },
              { label: 'Неделя', value: 'week' },
            ]}
          />
          <Select
            value={statusFilter}
            onChange={setStatusFilter}
            className="workload-status-select"
            popupClassName="workload-select-dropdown"
            style={{ minWidth: 160 }}
          >
            <Option value="all">Все статусы</Option>
            {Object.entries(STATUS_LABELS).map(([k, label]) => (
              <Option key={k} value={k}>{label}</Option>
            ))}
          </Select>
        </Space>
      </div>

      <Spin spinning={loading}>
        <div className="workload-body">
          <div className="workload-grid-wrap">
            <div
              className="workload-grid"
              style={{
                gridTemplateColumns: `56px repeat(${days.length}, minmax(88px, 1fr))`,
              }}
            >
              <div className="workload-corner" />
              {days.map((day) => {
                const isToday = day.isSame(dayjs(), 'day');
                const masterIds = dotsForDay(day);
                return (
                  <div key={day.format('YYYY-MM-DD')} className={`workload-day-head${isToday ? ' is-today' : ''}`}>
                    <div className="day-name">{DAY_NAMES[day.isoWeekday() - 1]}</div>
                    <div className="day-num">{day.format('D')}</div>
                    <div className="day-dots">
                      {masterIds.map((id) => (
                        <span key={id} className="day-dot" style={{ background: masterColor[id] }} />
                      ))}
                      {(() => {
                        const count = filtered.filter((a) => dayjs(a.start_time).isSame(day, 'day')).length;
                        return count > masterIds.length ? (
                          <span className="day-more">+{count - masterIds.length}</span>
                        ) : null;
                      })()}
                    </div>
                  </div>
                );
              })}

              <div className="workload-hours" style={{ height: gridHeight }}>
                {hours.map((h) => (
                  <div key={h} className="workload-hour-label" style={{ height: HOUR_PX }}>
                    {String(h).padStart(2, '0')}:00
                  </div>
                ))}
              </div>

              {days.map((day) => {
                const key = day.format('YYYY-MM-DD');
                const dayAppts = filtered.filter((a) => dayjs(a.start_time).format('YYYY-MM-DD') === key);
                return (
                  <div key={key} className="workload-day-col" style={{ height: gridHeight }}>
                    {hours.map((h) => (
                      <div key={h} className="workload-hour-line" style={{ height: HOUR_PX }} />
                    ))}
                    {dayAppts.map((appt, idx) => {
                      const color = masterColor[appt.master_id || 0] || '#D4A84B';
                      const top = Math.max(0, apptTopPx(appt.start_time));
                      const height = Math.min(apptHeightPx(appt.start_time, appt.end_time), gridHeight - top);
                      const overlapOffset = (idx % 3) * 4;
                      return (
                        <Tooltip
                          key={appt.id}
                          title={(
                            <div>
                              <div>{appt.master_name}</div>
                              <div>{appt.service_name || 'Услуга'}</div>
                              <div>{appt.client_name || 'Клиент'}</div>
                              <div>
                                {dayjs(appt.start_time).format('HH:mm')}–{dayjs(appt.end_time).format('HH:mm')}
                              </div>
                              <div>{STATUS_LABELS[appt.status] || appt.status}</div>
                            </div>
                          )}
                        >
                          <button
                            type="button"
                            className="workload-block"
                            style={{
                              top,
                              height: Math.max(height, 28),
                              left: 4 + overlapOffset,
                              right: 4,
                              background: `${color}33`,
                              borderColor: color,
                              color,
                            }}
                          >
                            <span className="workload-block-name">{masterFirstName(appt.master_name)}</span>
                            {height > 40 && (
                              <span className="workload-block-time">
                                {dayjs(appt.start_time).format('HH:mm')}
                              </span>
                            )}
                          </button>
                        </Tooltip>
                      );
                    })}
                  </div>
                );
              })}
            </div>
          </div>

          <aside className="workload-masters">
            <h4>Мастера</h4>
            {masters.length === 0 ? (
              <Text className="text-titanium text-13">Нет мастеров</Text>
            ) : (
              <ul>
                {masters.map((m) => (
                  <li key={m.id}>
                    <span className="master-dot" style={{ background: m.color }} />
                    <span className="master-avatar"><UserOutlined /></span>
                    <span className="master-name">{m.full_name}</span>
                  </li>
                ))}
              </ul>
            )}
          </aside>
        </div>
      </Spin>
    </div>
  );
}
