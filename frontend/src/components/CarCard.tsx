/* ============================================================
   CarCard — карточка авто: карусель, VIN, таймлайн
   ============================================================ */

import React, { useCallback, useEffect, useState } from 'react';
import { Spin, Typography } from 'antd';
import { CarOutlined, LeftOutlined, RightOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import { getPhotos, deletePhoto, setPrimaryPhoto, type Photo } from '../api/photos';
import UploadButton from './UploadButton';
import { Button } from './ui';
import CarCondition from './CarCondition';
import { saveCarCondition, type CarCondition as CarConditionData } from '../api/carCondition';

dayjs.locale('ru');
const { Text } = Typography;

const STATUS: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  in_progress: 'В работе',
  completed: 'Выполнена',
  no_show: 'Не явился',
};

export type CarVisit = {
  appointment_id: number;
  start_time: string;
  status: string;
  service_name: string;
  master_name?: string | null;
  price: number;
  notes?: string | null;
};

export type CarCardData = {
  id: number;
  make: string;
  model: string;
  year?: number | null;
  license_plate?: string | null;
  color?: string | null;
  vin?: string | null;
  body_type?: string | null;
  mileage?: number | null;
  paint_type?: string | null;
  glass_defects?: string[] | null;
  care_requirements?: string[] | null;
  condition_notes?: string | null;
  photos: Photo[];
  timeline: CarVisit[];
};

interface CarCardProps {
  carId: number;
  readonly?: boolean;
  compact?: boolean;
  canEditCondition?: boolean;
}

async function fetchCard(carId: number): Promise<CarCardData> {
  const token = localStorage.getItem('token');
  const res = await fetch(`/api/cars/${carId}`, {
    headers: {
      'Content-Type': 'application/json',
      ...(token ? { Authorization: `Bearer ${token}` } : {}),
    },
  });
  if (!res.ok) {
    const body = await res.json().catch(() => ({}));
    throw new Error(body.detail || `Ошибка ${res.status}`);
  }
  return res.json();
}

function formatKm(n?: number | null) {
  if (n == null) return null;
  return `${n.toLocaleString('ru-RU')} км`;
}

export default function CarCard({ carId, readonly = false, compact = false, canEditCondition = !readonly }: CarCardProps) {
  const [card, setCard] = useState<CarCardData | null>(null);
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [idx, setIdx] = useState(0);
  const [loading, setLoading] = useState(true);

  const load = useCallback(async () => {
    setLoading(true);
    try {
      const data = await fetchCard(carId);
      setCard(data);
      setPhotos(data.photos || []);
      setIdx(0);
    } catch {
      try {
        const fallback = await getPhotos('car', carId);
        setPhotos(fallback);
      } catch { /* ignore */ }
    }
    setLoading(false);
  }, [carId]);

  useEffect(() => {
    load();
  }, [load]);

  const handleDelete = async (photoId: number) => {
    await deletePhoto(photoId);
    await load();
  };

  const handleSetPrimary = async (photoId: number) => {
    await setPrimaryPhoto(photoId);
    await load();
  };

  const handleSaveCondition = async (data: CarConditionData) => {
    await saveCarCondition(carId, data);
    await load();
  };

  const current = photos[idx];
  const specRows = card
    ? [
        card.license_plate ? { label: 'Госномер', value: card.license_plate } : null,
        card.vin ? { label: 'VIN', value: card.vin } : null,
        card.year ? { label: 'Год', value: String(card.year) } : null,
        card.color ? { label: 'Цвет', value: card.color } : null,
        card.body_type ? { label: 'Кузов', value: card.body_type } : null,
        formatKm(card.mileage) ? { label: 'Пробег', value: formatKm(card.mileage)! } : null,
      ].filter(Boolean) as { label: string; value: string }[]
    : [];

  return (
    <div className="apple-car-card">
      <Spin spinning={loading}>
        <div className="apple-car-hero">
          {current ? (
            <img src={current.url} alt="" className="apple-car-photo" />
          ) : (
            <div className="apple-car-empty">
              <CarOutlined />
              <span>Добавьте фото авто</span>
            </div>
          )}
          <div className="apple-car-hero-fade" />
          {photos.length > 1 && (
            <>
              <button
                type="button"
                className="apple-car-nav apple-car-nav-left"
                aria-label="Предыдущее фото"
                onClick={() => setIdx((i) => (i - 1 + photos.length) % photos.length)}
              >
                <LeftOutlined />
              </button>
              <button
                type="button"
                className="apple-car-nav apple-car-nav-right"
                aria-label="Следующее фото"
                onClick={() => setIdx((i) => (i + 1) % photos.length)}
              >
                <RightOutlined />
              </button>
              <div className="apple-car-dots">
                {photos.map((p, i) => (
                  <button
                    key={p.id}
                    type="button"
                    className={i === idx ? 'on' : ''}
                    aria-label={`Фото ${i + 1}`}
                    onClick={() => setIdx(i)}
                  />
                ))}
              </div>
            </>
          )}
          <div className="apple-car-hero-meta">
            <div className="apple-car-model">
              {card ? `${card.make} ${card.model}` : 'Автомобиль'}
            </div>
            {card?.license_plate ? (
              <div className="apple-car-plate">
                <span className="flag" />
                <span className="num">{card.license_plate}</span>
              </div>
            ) : null}
          </div>
        </div>

        {specRows.length > 0 && (
          <div className="apple-car-specs">
            {specRows.map((row) => (
              <div key={row.label} className="apple-car-spec">
                <span className="apple-car-spec-label">{row.label}</span>
                <span className="apple-car-spec-value">{row.value}</span>
              </div>
            ))}
          </div>
        )}

        {card && (
          <div className="apple-car-condition">
            <CarCondition
              value={card}
              editable={canEditCondition}
              onSave={canEditCondition ? handleSaveCondition : undefined}
            />
          </div>
        )}

        {!readonly && (
          <div className="apple-car-upload">
            <UploadButton entityType="car" entityId={carId} onUploadSuccess={load} />
            {current && photos.length > 0 && (
              <div className="apple-car-photo-actions">
                {!current.is_primary && (
                  <Button size="small" look="ghost" onClick={() => handleSetPrimary(current.id)}>
                    Сделать основной
                  </Button>
                )}
                <Button size="small" look="ghost" onClick={() => handleDelete(current.id)}>
                  Удалить фото
                </Button>
              </div>
            )}
          </div>
        )}

        {!compact && (
          <div className="apple-car-timeline">
            <Text className="apple-car-timeline-title">Обслуживание</Text>
            {card && card.timeline.length === 0 ? (
              <Text className="text-titanium d-block">Пока нет визитов по этому авто</Text>
            ) : (
              <ul className="apple-car-visits">
                {(card?.timeline || []).map((v) => (
                  <li key={v.appointment_id}>
                    <span className="dot" />
                    <div>
                      <div className="visit-name">{v.service_name || 'Визит'}</div>
                      <div className="visit-meta">
                        {dayjs(v.start_time).format('D MMMM YYYY')}
                        {' · '}
                        {STATUS[v.status] || v.status}
                        {v.master_name ? ` · ${v.master_name}` : ''}
                      </div>
                    </div>
                    <div className="visit-price">
                      {Number(v.price || 0).toLocaleString('ru-RU')} ₽
                    </div>
                  </li>
                ))}
              </ul>
            )}
          </div>
        )}
      </Spin>
    </div>
  );
}
