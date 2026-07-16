/* ============================================================
   AppointmentDetail — детали записи с фото работ
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Card, Typography, Space, Spin, Tag, message,
} from 'antd';
import { ClockCircleOutlined, CalendarOutlined } from '@ant-design/icons';
import dayjs from 'dayjs';
import { getPhotos, deletePhoto, setPrimaryPhoto } from '../api/photos';
import type { Photo } from '../api/photos';
import UploadButton from './UploadButton';
import Gallery from './Gallery';

const { Text } = Typography;

interface AppointmentBrief {
  id: number;
  status: string;
  service_name?: string;
  start_time: string;
  total_price: number;
  client?: { full_name: string; phone: string };
  master?: { full_name: string };
  car?: { make: string; model: string; license_plate: string };
}

interface AppointmentDetailProps {
  appointment: AppointmentBrief;
  /** Текущий пользователь (для проверки прав) */
  currentUserRole: string;
  /** Режим только для чтения */
  readonly?: boolean;
}

const STATUS_LABELS: Record<string, string> = {
  pending: 'Ожидает',
  confirmed: 'Подтверждена',
  in_progress: 'В работе',
  completed: 'Выполнена',
  cancelled: 'Отменена',
  no_show: 'Не явился',
};

const STATUS_COLORS: Record<string, string> = {
  pending: 'gold',
  confirmed: 'blue',
  in_progress: 'cyan',
  completed: 'green',
  cancelled: 'red',
  no_show: 'default',
};

export default function AppointmentDetail({
  appointment,
  currentUserRole,
  readonly = false,
}: AppointmentDetailProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);

  const isAdmin = currentUserRole === 'admin' || currentUserRole === 'super_admin';
  const canEdit = !readonly && (isAdmin || currentUserRole === 'master');

  const fetchPhotos = async () => {
    setLoading(true);
    try {
      const data = await getPhotos('appointment', appointment.id);
      setPhotos(data);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPhotos();
  }, [appointment.id]);

  const handleDelete = async (photoId: number) => {
    try {
      await deletePhoto(photoId);
      message.success('Фото удалено');
      fetchPhotos();
    } catch {
      message.error('Ошибка удаления');
    }
  };

  const handleSetPrimary = async (photoId: number) => {
    try {
      await setPrimaryPhoto(photoId);
      message.success('Основное фото обновлено');
      fetchPhotos();
    } catch {
      message.error('Ошибка');
    }
  };

  return (
    <Card className="card-luxury">
      <Space direction="vertical" size="small" className="w-full">
        {/* Информация о записи */}
        <Space className="flex-space-between w-full">
          <Text className="text-white-bold text-16">
            {appointment.service_name || `Запись #${appointment.id}`}
          </Text>
          <Tag color={STATUS_COLORS[appointment.status]} className="tag-status">
            {STATUS_LABELS[appointment.status]}
          </Tag>
        </Space>

        <Text className="text-titanium text-13">
          <CalendarOutlined /> {dayjs(appointment.start_time).format('DD.MM.YYYY')}
          {' · '}
          <ClockCircleOutlined /> {dayjs(appointment.start_time).format('HH:mm')}
        </Text>

        {appointment.client && (
          <Text className="text-titanium text-13">
            👤 {appointment.client.full_name} · {appointment.client.phone}
          </Text>
        )}

        {appointment.master && (
          <Text className="text-titanium text-13">
            🔧 {appointment.master.full_name}
          </Text>
        )}

        {appointment.car && (
          <Text className="text-titanium text-13">
            🚗 {appointment.car.make} {appointment.car.model}
            {appointment.car.license_plate ? ` (${appointment.car.license_plate})` : ''}
          </Text>
        )}

        <Text className="text-gold-bold text-18">
          {appointment.total_price.toLocaleString()} ₽
        </Text>

        {/* Фото работ */}
        <Text className="title-gold text-14 d-block mt-4">
          📸 Фото работ
        </Text>

        {canEdit && (
          <div className="mb-12">
            <UploadButton
              entityType="appointment"
              entityId={appointment.id}
              onUploadSuccess={fetchPhotos}
            />
          </div>
        )}

        <Spin spinning={loading}>
          <Gallery
            photos={photos}
            onPhotoDelete={canEdit ? handleDelete : undefined}
            onPhotoSetPrimary={canEdit ? handleSetPrimary : undefined}
            readonly={!canEdit}
            columns={3}
          />
        </Spin>
      </Space>
    </Card>
  );
}
