/**
 * Запись — услуга, мастер, дата/время, автомобиль.
 * Слоты учитывают загрузку боксов (GET /api/ai/detailer/slots), если сетка есть.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';
import { DatePicker, Select, Space, Spin, Typography, message } from 'antd';
import { Button } from '../../../components/ui';
import dayjs, { Dayjs } from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  Car,
  DetailerSlot,
  Master,
  Service,
  apiFetch,
  formatCurrency,
  tzOffsetMinutes,
} from '../api';

dayjs.locale('ru');
const { Text } = Typography;

const SLOTS = Array.from({ length: 22 }, (_, i) => {
  const h = 9 + Math.floor(i / 2);
  const m = i % 2 === 0 ? '00' : '30';
  return `${String(h).padStart(2, '0')}:${m}`;
});

type LocState = {
  serviceId?: number;
  inspectId?: number;
  startTime?: string;
  boxId?: number;
} | null;

export default function ClientBookingPage() {
  const navigate = useNavigate();
  const location = useLocation();
  const preset = (location.state as LocState) || {};

  const [services, setServices] = useState<Service[]>([]);
  const [masters, setMasters] = useState<Master[]>([]);
  const [cars, setCars] = useState<Car[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [floor, setFloor] = useState<DetailerSlot[]>([]);

  const [serviceId, setServiceId] = useState<number | undefined>(preset.serviceId);
  const [masterId, setMasterId] = useState<number | undefined>();
  const [carId, setCarId] = useState<number | undefined>();
  const [date, setDate] = useState<Dayjs | null>(
    preset.startTime ? dayjs(preset.startTime) : dayjs().add(1, 'day'),
  );
  const [slot, setSlot] = useState<string | undefined>(
    preset.startTime ? dayjs(preset.startTime).format('HH:mm') : '10:00',
  );
  const [boxId, setBoxId] = useState<number | undefined>(preset.boxId);
  const inspectId = preset.inspectId;

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

  useEffect(() => {
    if (!date) return;
    let cancelled = false;
    const qs = new URLSearchParams({
      date: date.format('YYYY-MM-DD'),
      tz_offset: String(tzOffsetMinutes()),
    });
    if (serviceId) qs.set('service_id', String(serviceId));
    apiFetch<{ items: DetailerSlot[] }>(`/api/ai/detailer/slots?${qs.toString()}`)
      .then((d) => {
        if (!cancelled) setFloor(d.items || []);
      })
      .catch(() => {
        if (!cancelled) setFloor([]);
      });
    return () => { cancelled = true; };
  }, [date, serviceId]);

  const service = useMemo(
    () => services.find((s) => s.id === serviceId),
    [services, serviceId],
  );

  const floorByTime = useMemo(() => {
    const map = new Map<string, DetailerSlot>();
    for (const item of floor) {
      if (item.time) map.set(item.time, item);
    }
    return map;
  }, [floor]);

  const pickSlot = (time: string) => {
    const info = floorByTime.get(time);
    if (info && info.available === false) return;
    setSlot(time);
    if (info?.box_id) setBoxId(info.box_id);
  };

  const handleBook = async () => {
    if (!serviceId) { message.warning('Выберите услугу'); return; }
    if (!carId) { message.warning('Добавьте автомобиль в профиле'); return; }
    if (!date || !slot) { message.warning('Выберите дату и время'); return; }
    const info = floorByTime.get(slot);
    if (info?.available === false) {
      message.warning('Этот слот занят — выберите другой');
      return;
    }
    const start = info?.start_time
      ? dayjs(info.start_time)
      : dayjs(`${date.format('YYYY-MM-DD')}T${slot}:00`);
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
          box_id: info?.box_id || boxId || null,
          inspect_id: inspectId || null,
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
          <Badge variant="gold">
            {inspectId ? 'Сводка детейлера уйдёт мастеру' : 'Услуга, мастер, дата и время'}
          </Badge>
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
              {SLOTS.map((t) => {
                const info = floorByTime.get(t);
                const busy = info?.available === false;
                return (
                  <button
                    key={t}
                    type="button"
                    disabled={busy}
                    title={
                      busy
                        ? 'Боксы заняты'
                        : (info?.box_name ? `${info.box_name} · свободно ${info.free_boxes}` : undefined)
                    }
                    className={`client-slot${slot === t ? ' is-active' : ''}${busy ? ' is-busy' : ''}`}
                    onClick={() => pickSlot(t)}
                  >
                    {t}
                  </button>
                );
              })}
            </div>
          </div>

          <Button
            type="primary"
            size="large"
            look="gold"
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
