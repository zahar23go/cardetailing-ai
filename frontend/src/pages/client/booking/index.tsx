/**
 * Запись — услуга, мастер, дата/время, автомобиль.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { Button, DatePicker, Select, Space, Spin, Typography, message } from 'antd';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  Car,
  Master,
  Service,
  apiFetch,
  formatCurrency,
} from '../api';

dayjs.locale('ru');
const { Text } = Typography;

const SLOTS = Array.from({ length: 22 }, (_, i) => {
  const h = 9 + Math.floor(i / 2);
  const m = i % 2 === 0 ? '00' : '30';
  return `${String(h).padStart(2, '0')}:${m}`;
});

type LocState = { serviceId?: number } | null;

export default function ClientBookingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const preset = (location.state as LocState)?.serviceId;

  const [services, setServices] = useState<Service[]>([]);
  const [masters, setMasters] = useState<Master[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);

  const [serviceId, setServiceId] = useState<number | undefined>(preset);
  const [masterId, setMasterId] = useState<number | undefined>();
  const [carId, setCarId] = useState<number | undefined>();
  const [date, setDate] = useState<Dayjs | null>(dayjs().add(1, 'day'));
  const [slot, setSlot] = useState<string | undefined>('10:00');

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [svc, mst, car] = await Promise.all([
          apiFetch<{ items: Service[] }>('/api/services?skip=0&limit=200'),
          apiFetch<{ items: Master[] }>('/api/masters'),
          apiFetch<{ items: Car[] }>('/api/cars?skip=0&limit=50'),
        ]);
        if (!cancelled) {
          setServices(svc.items || []);
          setMasters(mst.items || []);
          const carItems = car.items || [];
          setCars(carItems);
          if (!carId && carItems[0]) setCarId(carItems[0].id);
        }
      } catch {
        message.error('Не удалось загрузить данные для записи');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const service = useMemo(
    () => services.find((s) => s.id === serviceId),
    [services, serviceId],
  );

  const handleBook = async () => {
    if (!serviceId) { message.warning('Выберите услугу'); return; }
    if (!carId) { message.warning('Добавьте автомобиль в профиле'); return; }
    if (!date || !slot) { message.warning('Выберите дату и время'); return; }
    const start = dayjs(`${date.format('YYYY-MM-DD')}T${slot}:00`);
    if (start.isBefore(dayjs())) {
      message.warning('Выберите время в будущем');
      return;
    }
    setSaving(true);
    try {
      await apiFetch('/api/appointments', {
        method: 'POST',
        body: JSON.stringify({
          service_id: serviceId,
          car_id: carId,
          master_id: masterId || null,
          start_time: start.toISOString(),
        }),
      });
      message.success('Заявка отправлена');
      navigate('/client');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось записаться');
    }
    setSaving(false);
  };

  if (loading) return <Spin />;

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Запись</h3>
          <Badge variant="gold">Услуга, мастер, дата и время</Badge>
        </div>
      </div>

      <Card variant="admin" className="client-block">
        <Space direction="vertical" size="middle" className="client-stack">
          <div>
            <span className="label-field">Услуга</span>
            <Select
              size="large"
              className="input-luxury client-field"
              placeholder="Выберите услугу"
              value={serviceId}
              onChange={setServiceId}
              showSearch
              optionFilterProp="label"
              options={services.map((s) => ({
                value: s.id,
                label: `${s.name} · ${formatCurrency(s.price)}`,
              }))}
            />
            {service ? (
              <div className="client-service-hint">
                <Badge variant="gold" size="sm">~{service.duration} мин</Badge>
                {service.category ? <Badge variant="neutral" size="sm">{service.category}</Badge> : null}
              </div>
            ) : null}
          </div>

          <div>
            <span className="label-field">Мастер</span>
            <Select
              size="large"
              className="input-luxury client-field"
              allowClear
              placeholder="Любой свободный"
              value={masterId}
              onChange={setMasterId}
              options={masters.map((m) => ({ value: m.id, label: m.full_name }))}
            />
          </div>

          <div>
            <span className="label-field">Автомобиль</span>
            {cars.length === 0 ? (
              <div>
                <Text className="text-titanium">Сначала добавьте авто в профиле.</Text>
                {' '}
                <Button type="link" className="client-link" onClick={() => navigate('/client/settings')}>
                  Перейти
                </Button>
              </div>
            ) : (
              <Select
                size="large"
                className="input-luxury client-field"
                value={carId}
                onChange={setCarId}
                options={cars.map((c) => ({
                  value: c.id,
                  label: `${c.make} ${c.model}${c.license_plate ? ` · ${c.license_plate}` : ''}`,
                }))}
              />
            )}
          </div>

          <div>
            <span className="label-field">Дата</span>
            <DatePicker
              size="large"
              className="input-luxury client-field"
              value={date}
              onChange={setDate}
              disabledDate={(d) => d && d.isBefore(dayjs().startOf('day'))}
              format="DD MMMM YYYY"
            />
          </div>

          <div>
            <span className="label-field">Время</span>
            <div className="client-slots">
              {SLOTS.map((t) => (
                <button
                  key={t}
                  type="button"
                  className={`client-slot${slot === t ? ' is-active' : ''}`}
                  onClick={() => setSlot(t)}
                >
                  {t}
                </button>
              ))}
            </div>
          </div>

          <Button
            type="primary"
            size="large"
            className="btn-gold"
            loading={saving}
            onClick={handleBook}
          >
            Записаться
          </Button>
        </Space>
      </Card>
    </>
  );
}
