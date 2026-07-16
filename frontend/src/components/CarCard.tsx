/* ============================================================
   CarCard — карточка автомобиля с фото
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Card, Typography, Space, Spin, message,
} from 'antd';
import { CarOutlined } from '@ant-design/icons';
import { getPhotos, deletePhoto, setPrimaryPhoto } from '../api/photos';
import type { Photo } from '../api/photos';
import UploadButton from './UploadButton';
import Gallery from './Gallery';

const { Text } = Typography;

interface CarCardProps {
  /** ID автомобиля */
  carId: number;
  /** Марка */
  make: string;
  /** Модель */
  model: string;
  /** Госномер */
  licensePlate?: string;
  /** Цвет */
  color?: string;
  /** Год */
  year?: number;
  /** Режим только для чтения */
  readonly?: boolean;
}

export default function CarCard({
  carId,
  make,
  model,
  licensePlate,
  color,
  year,
  readonly = false,
}: CarCardProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchPhotos = async () => {
    setLoading(true);
    try {
      const data = await getPhotos('car', carId);
      setPhotos(data);
    } catch {
      // ignore
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPhotos();
  }, [carId]);

  const handleDelete = async (photoId: number) => {
    try {
      await deletePhoto(photoId);
      message.success('Фото удалено');
      fetchPhotos();
    } catch {
      message.error('Ошибка удаления фото');
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
        {/* Информация об авто */}
        <Space>
          <CarOutlined style={{ color: '#C8A977', fontSize: '20px' }} />
          <Text className="text-white-bold text-16">
            {make} {model}
            {year && <> ({year})</>}
          </Text>
        </Space>

        {color && <Text className="text-titanium text-13">🎨 {color}</Text>}
        {licensePlate && (
          <Text className="text-gold-bold">{licensePlate}</Text>
        )}

        {/* Фото */}
        <Spin spinning={loading}>
          <Gallery
            photos={photos}
            onPhotoDelete={readonly ? undefined : handleDelete}
            onPhotoSetPrimary={readonly ? undefined : handleSetPrimary}
            readonly={readonly}
            columns={3}
          />
        </Spin>

        {/* Кнопка загрузки */}
        {!readonly && (
          <div className="mt-4">
            <UploadButton
              entityType="car"
              entityId={carId}
              onUploadSuccess={fetchPhotos}
            />
          </div>
        )}
      </Space>
    </Card>
  );
}
