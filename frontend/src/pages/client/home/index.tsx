/**
 * Главная клиента — текущие записи и рекомендации по истории.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { Button, Empty, Spin, Typography } from 'antd';
import { CalendarOutlined, ClockCircleOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  APPT_STATUS,
  Appointment,
  Service,
  apiFetch,
  formatCurrency,
} from '../api';

dayjs.locale('ru');
const { Text } = Typography;

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
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [appts, svc] = await Promise.all([
          apiFetch<{ items: Appointment[] }>('/api/appointments/me?skip=0&limit=50'),
          apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200'),
        ]);
        if (!cancelled) {
          setAppointments(appts.items || []);
          setServices(svc.items || []);
        }
      } catch {
        /* ignore */
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
      <div className="admin-section-head">
        <div>
          <h3>Главная</h3>
          <Text className="text-titanium">Ваши записи и рекомендации к ближайшим мойкам</Text>
        </div>
        <Button type="primary" className="btn-gold" onClick={() => navigate('/client/booking')}>
          Записаться
        </Button>
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

      <div className="client-section-title">Что рекомендуется в ближайшие мойки</div>
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
                className="btn-gold-secondary"
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
