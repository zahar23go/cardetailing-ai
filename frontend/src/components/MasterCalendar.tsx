/* ============================================================
   MasterCalendar — календарь мастера с Drag & Drop
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Row, Col, Tag, Spin, Button, Space, message, Select,
} from 'antd';
import { ReloadOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

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
  working_hours: { day_of_week: number; start_time: string; end_time: string; is_working_day: boolean }[];
}

const API_BASE = '';
const STATUS_COLORS: Record<string, string> = {
  pending: 'gold', confirmed: 'blue', in_progress: 'cyan',
  completed: 'green', cancelled: 'red', no_show: 'default',
};
const DAY_NAMES = ['Пн', 'Вт', 'Ср', 'Чт', 'Пт', 'Сб', 'Вс'];

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

export default function MasterCalendar() {
  const [weekOffset, setWeekOffset] = useState(0);
  const [calendar, setCalendar] = useState<CalendarData | null>(null);
  const [loading, setLoading] = useState(false);
  const [masters, setMasters] = useState<{ id: number; full_name: string }[]>([]);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(null);

  const weekStart = dayjs().add(weekOffset, 'week').startOf('week');
  const weekEnd = weekStart.endOf('week');

  const fetchMasters = async () => {
    try {
      const data = await apiFetch<{ items: { id: number; full_name: string; role: string }[]; total: number }>(
        '/api/users?skip=0&limit=100',
      );
      const ms = data.items.filter((u) => u.role === 'master');
      setMasters(ms);
      if (ms.length > 0 && !selectedMaster) setSelectedMaster(ms[0].id);
    } catch { /* ignore */ }
  };

  const fetchCalendar = async () => {
    if (!selectedMaster) return;
    setLoading(true);
    try {
      const start = weekStart.format('YYYY-MM-DD');
      const end = weekEnd.format('YYYY-MM-DD');
      const data = await apiFetch<CalendarData>(
        `/api/calendar/${selectedMaster}?start_date=${start}&end_date=${end}`,
      );
      setCalendar(data);
    } catch {
      message.error('Ошибка загрузки календаря');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchMasters();
  }, []);

  useEffect(() => {
    fetchCalendar();
  }, [selectedMaster, weekOffset]);

  const moveAppt = async (apptId: number, newStart: string) => {
    try {
      await apiFetch(`/api/appointments/${apptId}/move?start_time=${encodeURIComponent(newStart)}`, {
        method: 'PUT',
      });
      message.success('Запись перенесена');
      fetchCalendar();
    } catch (e: any) {
      message.error(e.message || 'Ошибка переноса');
    }
  };

  return (
    <div>
      {/* Header */}
      <div className="flex-space-between mb-12">
        <Text className="title-gold text-18">Календарь мастера</Text>
        <Space>
          <Select
            value={selectedMaster}
            onChange={(v) => { setSelectedMaster(v); setWeekOffset(0); }}
            style={{ width: 200 }}
            placeholder="Выберите мастера"
          >
            {masters.map((m) => (
              <Option key={m.id} value={m.id}>{m.full_name}</Option>
            ))}
          </Select>
          <Button icon={<LeftOutlined />} onClick={() => setWeekOffset((p) => p - 1)} size="small" className="btn-logout" />
          <Text className="text-titanium text-13">
            {weekStart.format('DD.MM')} — {weekEnd.format('DD.MM.YYYY')}
          </Text>
          <Button icon={<RightOutlined />} onClick={() => setWeekOffset((p) => p + 1)} size="small" className="btn-logout" />
          <Button icon={<ReloadOutlined />} onClick={fetchCalendar} size="small" className="btn-logout" />
        </Space>
      </div>

      <Spin spinning={loading}>
        {calendar && (
          <Row gutter={[8, 8]}>
            {calendar.days.map((day) => {
              const wh = calendar.working_hours.find((w) => w.day_of_week === day.day_of_week);
              const isOff = wh && !wh.is_working_day;
              const isToday = dayjs().format('YYYY-MM-DD') === day.date;

              return (
                <Col xs={24} sm={12} md={8} lg={Math.floor(24 / 7)} key={day.date}>
                  <Card
                    className={isToday ? 'card-luxury' : 'card-kpi'}
                    style={{
                      border: isToday ? '1px solid rgba(200,169,119,0.3)' : undefined,
                    }}
                  >
                    <Text className={isToday ? 'text-gold-bold text-14 d-block' : 'text-titanium text-13 d-block'}>
                      {DAY_NAMES[day.day_of_week]}, {dayjs(day.date).format('DD.MM')}
                    </Text>

                    {isOff ? (
                      <Text className="text-titanium text-12 d-block mt-4">Выходной</Text>
                    ) : (
                      <>
                        {wh && (
                          <Text className="text-titanium text-11 d-block opacity-70">
                            {wh.start_time}—{wh.end_time}
                          </Text>
                        )}

                        {day.appointments.length === 0 ? (
                          <Text className="text-titanium text-12 d-block mt-4 opacity-70">Свободно</Text>
                        ) : (
                          <div className="mt-4">
                            {day.appointments.map((appt) => (
                              <div
                                key={appt.id}
                                draggable
                                onDragStart={(e) => e.dataTransfer.setData('text/plain', JSON.stringify({
                                  id: appt.id, duration: dayjs(appt.end_time).diff(dayjs(appt.start_time), 'minute'),
                                }))}
                                onDragOver={(e) => e.preventDefault()}
                                onDrop={(e) => {
                                  e.preventDefault();
                                  try {
                                    const data = JSON.parse(e.dataTransfer.getData('text/plain'));
                                    const newStart = `${day.date}T${dayjs(appt.start_time).format('HH:mm')}:00`;
                                    moveAppt(data.id, newStart);
                                  } catch { /* ignore */ }
                                }}
                                style={{
                                  padding: '4px 8px',
                                  marginBottom: '4px',
                                  borderRadius: '6px',
                                  cursor: 'grab',
                                  fontSize: '12px',
                                  backgroundColor: appt.status === 'confirmed' ? 'rgba(200,169,119,0.15)'
                                    : appt.status === 'in_progress' ? 'rgba(78,203,113,0.15)'
                                    : 'rgba(255,255,255,0.05)',
                                  border: '1px solid rgba(255,255,255,0.06)',
                                }}
                              >
                                <Tag color={STATUS_COLORS[appt.status]} className="tag-status" style={{ fontSize: '10px' }}>
                                  {dayjs(appt.start_time).format('HH:mm')}
                                </Tag>
                                <Text className="text-white text-11">{appt.client_name || `#${appt.id}`}</Text>
                                {appt.service_name && (
                                  <Text className="text-titanium text-11 opacity-70 d-block">
                                    {appt.service_name}
                                  </Text>
                                )}
                              </div>
                            ))}
                          </div>
                        )}
                      </>
                    )}
                  </Card>
                </Col>
              );
            })}
          </Row>
        )}
      </Spin>
    </div>
  );
}
