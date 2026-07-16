/* ============================================================
   WorkingHoursSettings — управление рабочими часами мастера
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Card, Select, Button, TimePicker, Switch, Space, message, Spin,
} from 'antd';
import { SaveOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';

const { Text } = Typography;
const { Option } = Select;

const DAY_NAMES = ['Понедельник', 'Вторник', 'Среда', 'Четверг', 'Пятница', 'Суббота', 'Воскресенье'];

interface WorkHour {
  day_of_week: number;
  start_time: string;
  end_time: string;
  is_working_day: boolean;
}

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

export default function WorkingHoursSettings() {
  const [hours, setHours] = useState<WorkHour[]>(
    Array.from({ length: 7 }, (_, i) => ({
      day_of_week: i,
      start_time: i < 5 ? '09:00' : i === 5 ? '10:00' : '00:00',
      end_time: i < 5 ? '18:00' : i === 5 ? '16:00' : '00:00',
      is_working_day: i < 6,
    })),
  );
  const [saving, setSaving] = useState(false);
  const [loading, setLoading] = useState(false);
  const [masters, setMasters] = useState<{ id: number; full_name: string }[]>([]);
  const [selectedMaster, setSelectedMaster] = useState<number | null>(null);

  useEffect(() => {
    apiFetch<{ items: { id: number; full_name: string; role: string }[] }>('/api/users?skip=0&limit=100')
      .then((data) => {
        const ms = data.items.filter((u) => u.role === 'master');
        setMasters(ms);
        if (ms.length > 0) setSelectedMaster(ms[0].id);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    if (!selectedMaster) return;
    setLoading(true);
    apiFetch<WorkHour[]>(`/api/masters/working-hours?master_id=${selectedMaster}`)
      .then((data) => {
        if (data.length > 0) setHours(data);
      })
      .catch(() => {})
      .finally(() => setLoading(false));
  }, [selectedMaster]);

  const handleSave = async () => {
    if (!selectedMaster) return;
    setSaving(true);
    try {
      await apiFetch(`/api/masters/working-hours/${selectedMaster}`, {
        method: 'PUT',
        body: JSON.stringify(hours),
      });
      message.success('Рабочие часы сохранены');
    } catch (e: any) {
      message.error(e.message || 'Ошибка сохранения');
    }
    setSaving(false);
  };

  const toggleDay = (idx: number, working: boolean) => {
    const updated = [...hours];
    updated[idx] = { ...updated[idx], is_working_day: working };
    setHours(updated);
  };

  const updateTime = (idx: number, field: 'start_time' | 'end_time', time: dayjs.Dayjs | null) => {
    if (!time) return;
    const updated = [...hours];
    updated[idx] = { ...updated[idx], [field]: time.format('HH:mm') };
    setHours(updated);
  };

  return (
    <Card className="card-luxury">
      <Space direction="vertical" size="middle" className="w-full">
        <div className="flex-space-between">
          <Text className="title-gold text-16">Рабочие часы</Text>
          <Select
            value={selectedMaster}
            onChange={setSelectedMaster}
            style={{ width: 180 }}
            size="small"
          >
            {masters.map((m) => (
              <Option key={m.id} value={m.id}>{m.full_name}</Option>
            ))}
          </Select>
        </div>

        <Spin spinning={loading}>
          {hours.map((h, idx) => (
            <div key={h.day_of_week} className="flex-space-between">
              <Space>
                <Switch
                  checked={h.is_working_day}
                  onChange={(v) => toggleDay(idx, v)}
                  size="small"
                />
                <Text className={h.is_working_day ? 'text-white' : 'text-titanium opacity-70'}>
                  {DAY_NAMES[h.day_of_week]}
                </Text>
              </Space>

              {h.is_working_day ? (
                <Space size="small">
                  <TimePicker
                    value={dayjs(h.start_time, 'HH:mm')}
                    format="HH:mm"
                    onChange={(t) => updateTime(idx, 'start_time', t)}
                    size="small"
                    minuteStep={15}
                  />
                  <Text className="text-titanium">—</Text>
                  <TimePicker
                    value={dayjs(h.end_time, 'HH:mm')}
                    format="HH:mm"
                    onChange={(t) => updateTime(idx, 'end_time', t)}
                    size="small"
                    minuteStep={15}
                  />
                </Space>
              ) : (
                <Text className="text-titanium text-12">Выходной</Text>
              )}
            </div>
          ))}
        </Spin>

        <Button
          type="primary"
          className="btn-gold"
          icon={<SaveOutlined />}
          onClick={handleSave}
          loading={saving}
        >
          Сохранить
        </Button>
      </Space>
    </Card>
  );
}
