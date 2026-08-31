/**
 * Главная клиента — текущие записи и рекомендации по истории.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Empty, Spin, Typography } from 'antd';
import { CalendarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import { Button, Card, Badge } from '../../../components/ui';
import {
  APPT_STATUS,
  Appointment,
  Car,
  Service,
  apiFetch,
  formatCurrency,
} from '../api';
import { APPT_OFFLINE_KEY } from '../../../pwa';
import CarCard from '../../../components/CarCard';

dayjs.locale('ru');
const { Text } = Typography;

const INTENT_CHIPS = [
  { label: 'Просто помыть', prompt: 'Хочу просто помыть машину. Что подойдёт?' },
  { label: 'Убрать царапину', prompt: 'На кузове царапина. Что делать и сколько стоит?' },
  { label: 'Обновить керамику', prompt: 'Пора обновить керамическое покрытие. Расскажи и запиши.' },
];

function recommendFromHistory(appointments: Appointment[], services: Service[]): Service[] {
  const completed = appointments.filter((a) => a.status === 'completed');
  const recentIds = new Set(
    completed
      .filter((a) => dayjs().diff(dayjs(a.start_time), 'day') < 45)
      .map((a) => a.service_id),
  );
  const usedCats = new Set(
    completed
      .map((a) => services.find((s) => s.id === a.service_id)?.category)
      .filter(Boolean) as string[],
  );
  const unused = services.filter((s) => !recentIds.has(s.id));
  const byCat = unused.filter((s) => s.category && usedCats.has(s.category));
  const pool = byCat.length ? [...byCat, ...unused.filter((s) => !byCat.includes(s))] : unused;
  return pool.slice(0, 4);
}

export default function ClientHomePage() {
  const navigate = useNavigate();
  const [appointments, setAppointments] = useState<Appointment[]>([]);
  const [services, setServices] = useState<Service[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [offline, setOffline] = useState(false);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [appts, svc, carData] = await Promise.all([
          apiFetch<{ items: Appointment[] }>('/api/appointments/me?skip=0&limit=50'),
          apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200'),
          apiFetch<{ items: Car[] }>('/api/cars?skip=0&limit=20').catch(() => ({ items: [] as Car[] })),
        ]);
        if (!cancelled) {
          setAppointments(appts.items || []);
          setServices(svc.items || []);
          setCars(carData.items || []);
          setOffline(false);
          try {
            localStorage.setItem(APPT_OFFLINE_KEY, JSON.stringify(appts));
          } catch {
            /* quota */
          }
        }
      } catch {
        if (!cancelled) {
          try {
            const raw = localStorage.getItem(APPT_OFFLINE_KEY);
            if (raw) {
              const cached = JSON.parse(raw) as { items?: Appointment[] };
              setAppointments(cached.items || []);
              setOffline(true);
            }
          } catch {
            /* ignore */
          }
        }
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const upcoming = useMemo(
    () => appointments
      .filter((a) => !['cancelled', 'completed'].includes(a.status)
        && dayjs(a.start_time).isAfter(dayjs().subtract(1, 'hour')))
      .sort((a, b) => dayjs(a.start_time).valueOf() - dayjs(b.start_time).valueOf()),
    [appointments],
  );

  const recs = useMemo(
    () => recommendFromHistory(appointments, services),
    [appointments, services],
  );

  if (loading) return <Spin />;

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Главная</h3>
          <Badge variant="gold">
            {offline ? 'Нет сети · показаны сохранённые записи' : 'Твой эксперт по уходу за авто'}
          </Badge>
        </div>
        <div className="client-section-actions">
          <Button type="primary" look="gold" onClick={() => navigate('/client/booking')}>
            Записаться
          </Button>
          <Button look="ghost" onClick={() => navigate('/client/chat', { state: { inspect: true } })}>
            Оценить авто
          </Button>
        </div>
      </div>

      {cars[0] ? (
        <>
          <div className="client-section-title">Автомобиль</div>
          <div className="client-block apple-car-wrap">
            <CarCard carId={cars[0].id} compact readonly />
          </div>
        </>
      ) : (
        <Card variant="admin" className="client-block">
          <div className="client-appt-name">Добавьте ваш автомобиль</div>
          <Text className="text-titanium">BMW, госномер, фото — чтобы Детейлер знал машину.</Text>
          <div className="client-section-actions" style={{ marginTop: 12 }}>
            <Button type="primary" look="gold" onClick={() => navigate('/client/settings')}>
              Добавить авто
            </Button>
          </div>
        </Card>
      )}

      <div className="client-section-title">Что хотите сделать с автомобилем?</div>
      <div className="client-intent-chips">
        {INTENT_CHIPS.map((chip) => (
          <button
            key={chip.label}
            type="button"
            className="client-intent-chip"
            onClick={() => navigate('/client/chat', { state: { prompt: chip.prompt } })}
          >
            {chip.label}
          </button>
        ))}
      </div>

      <div className="client-section-title">Текущие записи</div>
      {upcoming.length === 0 ? (
        <Card variant="admin" className="client-block">
          <Empty
            description={<Text className="text-titanium">Нет активных записей</Text>}
          />
        </Card>
      ) : (
        upcoming.map((a) => {
          const st = APPT_STATUS[a.status] || APPT_STATUS.pending;
          return (
            <Card key={a.id} variant="admin" className="client-block">
              <div className="client-appt-row">
                <div>
                  <div className="client-appt-name">{a.service_name || a.service?.name || 'Услуга'}</div>
                  <Text className="text-titanium">
                    <CalendarOutlined /> {dayjs(a.start_time).format('D MMMM, HH:mm')}
                    {' · '}
                    <ClockCircleOutlined /> {dayjs(a.end_time).diff(dayjs(a.start_time), 'minute')} мин
                  </Text>
                  {a.master?.full_name ? (
                    <div><Text className="text-titanium">Мастер: {a.master.full_name}</Text></div>
                  ) : null}
                </div>
                <div className="client-appt-meta">
                  <Badge variant={st.variant} size="sm">{st.label}</Badge>
                  <Text className="text-gold-bold">{formatCurrency(a.total_price)}</Text>
                </div>
              </div>
            </Card>
          );
        })
      )}

      <div className="client-section-title">Рекомендованные услуги</div>
      {recs.length === 0 ? (
        <Card variant="admin" className="client-block">
          <Text className="text-titanium">
            После первых визитов здесь появятся услуги по вашей истории.
          </Text>
        </Card>
      ) : (
        recs.map((s) => (
          <Card key={s.id} variant="admin" className="client-block client-rec">
            <div>
              <div className="client-appt-name">{s.name}</div>
              {s.description ? <Text className="text-titanium">{s.description}</Text> : null}
              {s.category ? <div><Badge variant="gold" size="sm">{s.category}</Badge></div> : null}
            </div>
            <div className="client-appt-meta">
              <Text className="text-gold-bold">{formatCurrency(s.price)}</Text>
              <Button
                size="small"
                look="ghost"
                onClick={() => navigate('/client/booking', { state: { serviceId: s.id } })}
              >
                Записаться
              </Button>
            </div>
          </Card>
        ))
      )}
    </>
  );
}
