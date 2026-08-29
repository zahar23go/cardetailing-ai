/**
 * Живая сетка боксов — /upload/boxes
 * Состояния: свободен / подготовка слота / в работе / забронирован.
 */
import React, { useCallback, useEffect, useState } from 'react';
import { Card, Empty, Spin, Tag, Typography, message } from 'antd';
import {
  CheckCircleOutlined, ClockCircleOutlined, PlayCircleOutlined, ReloadOutlined,
} from '@ant-design/icons';
import { Button } from '../../../components/ui';
import CloseVisitModal from '../../../components/CloseVisitModal';

const { Text } = Typography;

const API_BASE = '';
const POLL_MS = 10000;

interface LiveVisit {
  id: number;
  status: string;
  service_name: string;
  client_name: string;
  master_name: string | null;
  master_id: number | null;
  start_time: string;
  end_time: string;
  elapsed_minutes: number;
  remaining_minutes: number;
  overrun: boolean;
}

interface LiveBox {
  box_id: number;
  name: string;
  color: string | null;
  is_active: boolean;
  state: 'free' | 'preparing' | 'occupied' | 'booked' | 'inactive';
  state_label: string;
  current: LiveVisit | null;
  next: LiveVisit | null;
}

interface LiveResponse {
  server_time: string;
  prep_minutes: number;
  boxes: LiveBox[];
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

const STATE_CLASS: Record<LiveBox['state'], string> = {
  occupied: 'tone-gold',
  preparing: 'tone-warn',
  booked: 'tone-gold',
  free: '',
  inactive: '',
};

function minutesLabel(v: LiveVisit) {
  if (v.overrun) {
    const late = Math.abs(v.remaining_minutes);
    if (late >= 24 * 60) return `В работе · просрочен ${Math.floor(late / 60)} ч`;
    return `Просрочен ${late} мин`;
  }
  if (v.status === 'in_progress') {
    return `Идёт ${v.elapsed_minutes} мин · осталось ${Math.max(0, v.remaining_minutes)} мин`;
  }
  if (v.remaining_minutes >= 0 && v.status !== 'in_progress') {
    const start = new Date(v.start_time);
    return `Старт ${start.toLocaleTimeString('ru-RU', { hour: '2-digit', minute: '2-digit' })}`;
  }
  return `Осталось ${Math.max(0, v.remaining_minutes)} мин`;
}

export default function BoxesFloorPage() {
  const [data, setData] = useState<LiveResponse | null>(null);
  const [loading, setLoading] = useState(false);
  const [actionId, setActionId] = useState<number | null>(null);
  const [closeId, setCloseId] = useState<number | null>(null);

  const refresh = useCallback(async (silent = false) => {
    if (!silent) setLoading(true);
    try {
      const next = await apiFetch<LiveResponse>('/api/boxes/live');
      setData(next);
    } catch (e: any) {
      if (!silent) message.error(e.message || 'Не удалось загрузить боксы');
    }
    if (!silent) setLoading(false);
  }, []);

  useEffect(() => {
    refresh();
    const id = window.setInterval(() => refresh(true), POLL_MS);
    return () => window.clearInterval(id);
  }, [refresh]);

  const startWork = async (apptId: number) => {
    setActionId(apptId);
    try {
      await apiFetch(`/api/appointments/${apptId}`, {
        method: 'PUT',
        body: JSON.stringify({ status: 'in_progress' }),
      });
      message.success('Бокс взят в работу');
      await refresh(true);
    } catch (e: any) {
      message.error(e.message || 'Не удалось взять в работу');
    }
    setActionId(null);
  };

  const visit = (box: LiveBox) => box.current || box.next;

  return (
    <>
      <div className="admin-section-head">
        <div>
          <div className="admin-overview-kicker">Этаж</div>
          <h3>Боксы сейчас</h3>
          <Text className="text-titanium text-13">
            Обновление каждые {POLL_MS / 1000} с · подготовка слота за {data?.prep_minutes ?? 15} мин до старта
          </Text>
        </div>
        <Button look="ghost" icon={<ReloadOutlined />} onClick={() => refresh()}>
          Обновить
        </Button>
      </div>

      <Spin spinning={loading && !data}>
        {!data?.boxes.length ? (
          <Empty description={<span className="text-titanium">Боксы не заведены</span>} />
        ) : (
          <div
            style={{
              display: 'grid',
              gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
              gap: 16,
            }}
          >
            {data.boxes.map((box) => {
              const v = visit(box);
              return (
                <Card
                  key={box.box_id}
                  className={`card-luxury admin-kpi-card ${STATE_CLASS[box.state]}`}
                  size="small"
                  style={{
                    borderTop: `3px solid ${box.color || 'var(--color-gold, #C8A977)'}`,
                    opacity: box.state === 'inactive' ? 0.55 : 1,
                  }}
                >
                  <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: 8 }}>
                    <Text className="text-white text-16" style={{ fontWeight: 700 }}>{box.name}</Text>
                    <Tag>{box.state_label}</Tag>
                  </div>
                  {v ? (
                    <>
                      <Text className="text-gold-bold text-14 d-block">{v.service_name}</Text>
                      <Text className="text-titanium text-13 d-block">{v.client_name}</Text>
                      {v.master_name && (
                        <Text className="text-titanium text-12 d-block">Мастер: {v.master_name}</Text>
                      )}
                      <Text className="text-white text-12 d-block" style={{ marginTop: 8 }}>
                        <ClockCircleOutlined /> {minutesLabel(v)}
                      </Text>
                      <div style={{ marginTop: 12, display: 'flex', gap: 8, flexWrap: 'wrap' }}>
                        {box.state === 'preparing' && v.status !== 'in_progress' && (
                          <Button
                            size="small"
                            look="ghost"
                            icon={<PlayCircleOutlined />}
                            loading={actionId === v.id}
                            onClick={() => startWork(v.id)}
                          >
                            В работу
                          </Button>
                        )}
                        {box.state === 'occupied' && (
                          <Button
                            size="small"
                            look="gold"
                            icon={<CheckCircleOutlined />}
                            onClick={() => setCloseId(v.id)}
                          >
                            Закрыть заезд
                          </Button>
                        )}
                      </div>
                      {box.next && box.current && box.next.id !== box.current.id && (
                        <Text className="text-titanium text-12 d-block" style={{ marginTop: 10 }}>
                          Далее: {box.next.service_name} · {box.next.client_name}
                        </Text>
                      )}
                    </>
                  ) : (
                    <Text className="text-titanium text-13">Слот свободен</Text>
                  )}
                </Card>
              );
            })}
          </div>
        )}
      </Spin>

      <CloseVisitModal
        open={closeId != null}
        appointmentId={closeId}
        role="admin"
        onCancel={() => setCloseId(null)}
        onClosed={() => {
          setCloseId(null);
          refresh(true);
        }}
      />
    </>
  );
}
