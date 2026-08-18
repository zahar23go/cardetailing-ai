/**
 * Профиль клиента: имя, телефон, авто, история записей.
 */
import React, { useEffect, useState } from 'react';
import {
  Button, Empty, Input, InputNumber, Space, Spin, Typography, message,
} from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import {
  APPT_STATUS,
  Appointment,
  Car,
  apiFetch,
  formatCurrency,
} from '../api';

dayjs.locale('ru');
const { Text } = Typography;

type Profile = { id: number; phone: string; full_name: string; role: string };

export default function ClientSettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [fullName, setFullName] = useState('');
  const [cars, setCars] = useState<Car[]>([]);
  const [history, setHistory] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [carForm, setCarForm] = useState({ make: '', model: '', year: undefined as number | undefined, license_plate: '', color: '' });
  const [addingCar, setAddingCar] = useState(false);

  const reload = async () => {
    const [me, carData, appts] = await Promise.all([
      apiFetch<Profile>('/api/me'),
      apiFetch<{ items: Car[] }>('/api/cars?skip=0&limit=50'),
      apiFetch<{ items: Appointment[] }>('/api/appointments/me?skip=0&limit=50'),
    ]);
    setProfile(me);
    setFullName(me.full_name || '');
    setCars(carData.items || []);
    setHistory(appts.items || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        await reload();
      } catch {
        if (!cancelled) message.error('Не удалось загрузить профиль');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const saveProfile = async () => {
    if (!fullName.trim()) { message.warning('Укажите имя'); return; }
    setSaving(true);
    try {
      const updated = await apiFetch<Profile>('/api/me', {
        method: 'PUT',
        body: JSON.stringify({ full_name: fullName.trim() }),
      });
      setProfile(updated);
      message.success('Профиль сохранён');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка сохранения');
    }
    setSaving(false);
  };

  const addCar = async () => {
    if (!carForm.make.trim() || !carForm.model.trim()) {
      message.warning('Укажите марку и модель');
      return;
    }
    setAddingCar(true);
    try {
      await apiFetch('/api/cars', {
        method: 'POST',
        body: JSON.stringify({
          make: carForm.make.trim(),
          model: carForm.model.trim(),
          year: carForm.year || null,
          license_plate: carForm.license_plate.trim() || null,
          color: carForm.color.trim() || null,
        }),
      });
      setCarForm({ make: '', model: '', year: undefined, license_plate: '', color: '' });
      message.success('Автомобиль добавлен');
      await reload();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось добавить авто');
    }
    setAddingCar(false);
  };

  if (loading) return <Spin />;

  return (
    <>
      <div className="admin-section-head">
        <div>
          <h3>Профиль</h3>
          <Text className="text-titanium">Имя, телефон, автомобиль и история</Text>
        </div>
      </div>

      <Card variant="admin" className="client-block">
        <Space direction="vertical" size="middle" style={{ width: '100%' }}>
          <div>
            <span className="label-field">Имя</span>
            <Input
              size="large"
              className="input-luxury"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div>
            <span className="label-field">Телефон</span>
            <Input size="large" className="input-luxury" value={profile?.phone || ''} disabled />
          </div>
          <Button type="primary" className="btn-gold" loading={saving} onClick={saveProfile}>
            Сохранить
          </Button>
        </Space>
      </Card>

      <div className="client-section-title">Автомобиль</div>
      {cars.map((c) => (
        <Card key={c.id} variant="admin" className="client-block">
          <div className="client-appt-name">{c.make} {c.model}</div>
          <Text className="text-titanium">
            {[c.year, c.color, c.license_plate].filter(Boolean).join(' · ') || 'Без доп. данных'}
          </Text>
        </Card>
      ))}
      <Card variant="admin" className="client-block">
        <Space direction="vertical" size="small" style={{ width: '100%' }}>
          <span className="label-field">Добавить автомобиль</span>
          <Input className="input-luxury" placeholder="Марка" value={carForm.make} onChange={(e) => setCarForm((p) => ({ ...p, make: e.target.value }))} />
          <Input className="input-luxury" placeholder="Модель" value={carForm.model} onChange={(e) => setCarForm((p) => ({ ...p, model: e.target.value }))} />
          <InputNumber className="input-luxury" style={{ width: '100%' }} placeholder="Год" min={1990} max={2030} value={carForm.year} onChange={(v) => setCarForm((p) => ({ ...p, year: v || undefined }))} />
          <Input className="input-luxury" placeholder="Госномер" value={carForm.license_plate} onChange={(e) => setCarForm((p) => ({ ...p, license_plate: e.target.value }))} />
          <Input className="input-luxury" placeholder="Цвет" value={carForm.color} onChange={(e) => setCarForm((p) => ({ ...p, color: e.target.value }))} />
          <Button icon={<PlusOutlined />} className="btn-gold-secondary" loading={addingCar} onClick={addCar}>
            Добавить
          </Button>
        </Space>
      </Card>

      <div className="client-section-title">История записей</div>
      {history.length === 0 ? (
        <Empty description={<Text className="text-titanium">История пуста</Text>} />
      ) : (
        history.map((a) => {
          const st = APPT_STATUS[a.status] || APPT_STATUS.pending;
          return (
            <Card key={a.id} variant="admin" className="client-block">
              <div className="client-appt-row">
                <div>
                  <div className="client-appt-name">{a.service_name || a.service?.name || 'Услуга'}</div>
                  <Text className="text-titanium">{dayjs(a.start_time).format('D MMMM YYYY, HH:mm')}</Text>
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
    </>
  );
}
