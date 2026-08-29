/**
 * Профиль клиента: имя, телефон, авто, история записей.
 */
import React, { useEffect, useState } from 'react';
import {
  Empty,
  InputNumber,
  Space,
  Spin,
  Table,
  Typography,
  message,
} from 'antd';
import { Button, Input } from '../../../components/ui';
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
type CarDraft = {
  make: string;
  model: string;
  year: number | undefined;
  license_plate: string;
  color: string;
};

const emptyCar = (): CarDraft => ({
  make: '', model: '', year: undefined, license_plate: '', color: '',
});

function carToDraft(c: Car): CarDraft {
  return {
    make: c.make || '',
    model: c.model || '',
    year: c.year || undefined,
    license_plate: c.license_plate || '',
    color: c.color || '',
  };
}

export default function ClientSettingsPage() {
  const [profile, setProfile] = useState<Profile | null>(null);
  const [fullName, setFullName] = useState('');
  const [phone, setPhone] = useState('');
  const [cars, setCars] = useState<Car[]>([]);
  const [history, setHistory] = useState<Appointment[]>([]);
  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [carForm, setCarForm] = useState<CarDraft>(emptyCar());
  const [addingCar, setAddingCar] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState<CarDraft>(emptyCar());
  const [savingCar, setSavingCar] = useState(false);

  const reload = async () => {
    const [me, carData, appts] = await Promise.all([
      apiFetch<Profile>('/api/me'),
      apiFetch<{ items: Car[] }>('/api/cars?skip=0&limit=50'),
      apiFetch<{ items: Appointment[] }>('/api/appointments/me?skip=0&limit=50'),
    ]);
    setProfile(me);
    setFullName(me.full_name || '');
    setPhone(me.phone || '');
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
    if (!phone.trim()) { message.warning('Укажите телефон'); return; }
    setSaving(true);
    try {
      const updated = await apiFetch<Profile>('/api/me', {
        method: 'PUT',
        body: JSON.stringify({ full_name: fullName.trim(), phone: phone.trim() }),
      });
      setProfile(updated);
      setPhone(updated.phone);
      message.success('Профиль сохранён');
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Ошибка сохранения');
    }
    setSaving(false);
  };

  const payloadFromDraft = (d: CarDraft) => ({
    make: d.make.trim(),
    model: d.model.trim(),
    year: d.year || null,
    license_plate: d.license_plate.trim() || null,
    color: d.color.trim() || null,
  });

  const addCar = async () => {
    if (!carForm.make.trim() || !carForm.model.trim()) {
      message.warning('Укажите марку и модель');
      return;
    }
    setAddingCar(true);
    try {
      await apiFetch('/api/cars', {
        method: 'POST',
        body: JSON.stringify(payloadFromDraft(carForm)),
      });
      setCarForm(emptyCar());
      message.success('Автомобиль добавлен');
      await reload();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось добавить авто');
    }
    setAddingCar(false);
  };

  const saveCar = async (carId: number) => {
    if (!editDraft.make.trim() || !editDraft.model.trim()) {
      message.warning('Укажите марку и модель');
      return;
    }
    setSavingCar(true);
    try {
      await apiFetch(`/api/cars/${carId}`, {
        method: 'PUT',
        body: JSON.stringify(payloadFromDraft(editDraft)),
      });
      message.success('Автомобиль обновлён');
      setEditingId(null);
      await reload();
    } catch (e: unknown) {
      message.error(e instanceof Error ? e.message : 'Не удалось сохранить авто');
    }
    setSavingCar(false);
  };

  if (loading) return <Spin />;

  return (
    <>
      <div className="client-section-head">
        <div>
          <h3>Профиль</h3>
          <Badge variant="gold">Имя, телефон, автомобиль и история</Badge>
        </div>
      </div>

      <Card variant="admin" className="client-block">
        <Space direction="vertical" size="middle" className="client-stack">
          <div>
            <span className="label-field">Имя</span>
            <Input
              size="large"
              className="input-luxury client-field"
              value={fullName}
              onChange={(e) => setFullName(e.target.value)}
            />
          </div>
          <div>
            <span className="label-field">Телефон</span>
            <Input
              size="large"
              className="input-luxury client-field"
              value={phone}
              onChange={(e) => setPhone(e.target.value)}
            />
          </div>
          <Button type="primary" look="gold" loading={saving} onClick={saveProfile}>
            Сохранить
          </Button>
        </Space>
      </Card>

      <div className="client-section-title">Автомобиль</div>
      {cars.map((c) => (
        <Card key={c.id} variant="admin" className="client-block">
          {editingId === c.id ? (
            <Space direction="vertical" size="small" className="client-stack">
              <Input className="input-luxury client-field" placeholder="Марка" value={editDraft.make} onChange={(e) => setEditDraft((p) => ({ ...p, make: e.target.value }))} />
              <Input className="input-luxury client-field" placeholder="Модель" value={editDraft.model} onChange={(e) => setEditDraft((p) => ({ ...p, model: e.target.value }))} />
              <InputNumber className="input-luxury client-field" placeholder="Год" min={1990} max={2030} value={editDraft.year} onChange={(v) => setEditDraft((p) => ({ ...p, year: v || undefined }))} />
              <Input className="input-luxury" placeholder="Госномер" value={editDraft.license_plate} onChange={(e) => setEditDraft((p) => ({ ...p, license_plate: e.target.value }))} />
              <Input className="input-luxury" placeholder="Цвет" value={editDraft.color} onChange={(e) => setEditDraft((p) => ({ ...p, color: e.target.value }))} />
              <Space>
                <Button look="gold" loading={savingCar} onClick={() => saveCar(c.id)}>Сохранить</Button>
                <Button look="ghost" onClick={() => setEditingId(null)}>Отмена</Button>
              </Space>
            </Space>
          ) : (
            <div className="client-appt-row">
              <div>
                <div className="client-appt-name">{c.make} {c.model}</div>
                <Text className="text-titanium">
                  {[c.year, c.color, c.license_plate].filter(Boolean).join(' · ') || 'Без доп. данных'}
                </Text>
              </div>
              <Button
                size="small"
                look="ghost"
                onClick={() => { setEditingId(c.id); setEditDraft(carToDraft(c)); }}
              >
                Изменить
              </Button>
            </div>
          )}
        </Card>
      ))}
      <Card variant="admin" className="client-block">
        <Space direction="vertical" size="small" className="client-stack">
          <span className="label-field">Добавить автомобиль</span>
          <Input className="input-luxury client-field" placeholder="Марка" value={carForm.make} onChange={(e) => setCarForm((p) => ({ ...p, make: e.target.value }))} />
          <Input className="input-luxury client-field" placeholder="Модель" value={carForm.model} onChange={(e) => setCarForm((p) => ({ ...p, model: e.target.value }))} />
          <InputNumber className="input-luxury client-field" placeholder="Год" min={1990} max={2030} value={carForm.year} onChange={(v) => setCarForm((p) => ({ ...p, year: v || undefined }))} />
          <Input className="input-luxury" placeholder="Госномер" value={carForm.license_plate} onChange={(e) => setCarForm((p) => ({ ...p, license_plate: e.target.value }))} />
          <Input className="input-luxury" placeholder="Цвет" value={carForm.color} onChange={(e) => setCarForm((p) => ({ ...p, color: e.target.value }))} />
          <Button icon={<PlusOutlined />} look="ghost" loading={addingCar} onClick={addCar}>
            Добавить
          </Button>
        </Space>
      </Card>

      <div className="client-section-title">История записей</div>
      <Card variant="admin" className="client-block">
        {history.length === 0 ? (
          <Empty description={<Text className="text-titanium">История пуста</Text>} />
        ) : (
          <Table
            dataSource={history}
            rowKey="id"
            pagination={false}
            scroll={{ x: 520 }}
            columns={[
              {
                title: <Text className="text-gold">Услуга</Text>,
                key: 'service',
                render: (_: unknown, a: Appointment) => (
                  <Text className="text-white text-medium">
                    {a.service_name || a.service?.name || 'Услуга'}
                  </Text>
                ),
              },
              {
                title: <Text className="text-gold">Дата</Text>,
                key: 'date',
                render: (_: unknown, a: Appointment) => (
                  <Text className="text-titanium">
                    {dayjs(a.start_time).format('D MMMM YYYY, HH:mm')}
                  </Text>
                ),
              },
              {
                title: <Text className="text-gold">Статус</Text>,
                key: 'status',
                render: (_: unknown, a: Appointment) => {
                  const st = APPT_STATUS[a.status] || APPT_STATUS.pending;
                  return <Badge variant={st.variant} size="sm">{st.label}</Badge>;
                },
              },
              {
                title: <Text className="text-gold">Сумма</Text>,
                key: 'price',
                align: 'right' as const,
                render: (_: unknown, a: Appointment) => (
                  <Text className="text-gold-bold">{formatCurrency(a.total_price)}</Text>
                ),
              },
            ]}
            components={{
              header: {
                cell: (props: React.ThHTMLAttributes<HTMLTableCellElement>) => (
                  <th {...props} className="table-header-cell" />
                ),
              },
              body: {
                row: (props: React.HTMLAttributes<HTMLTableRowElement>) => (
                  <tr {...props} className="table-body-row" />
                ),
                cell: (props: React.TdHTMLAttributes<HTMLTableCellElement>) => (
                  <td {...props} className="table-body-cell" />
                ),
              },
            }}
          />
        )}
      </Card>
    </>
  );
}
