/* ============================================================
   PortfolioSection — портфолио мастера
   ============================================================ */

import React, { useState, useEffect } from 'react';
import { Typography, Spin, message } from 'antd';
import { getPhotos, deletePhoto, setPrimaryPhoto } from '../api/photos';
import type { Photo } from '../api/photos';
import UploadButton from './UploadButton';
import Gallery from './Gallery';

const { Text } = Typography;

interface PortfolioSectionProps {
  /** ID мастера */
  masterId: number;
  /** Режим только для чтения */
  readonly?: boolean;
}

export default function PortfolioSection({
  masterId,
  readonly = false,
}: PortfolioSectionProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);

  const fetchPhotos = async () => {
    setLoading(true);
    try {
      const data = await getPhotos('portfolio', masterId);
      setPhotos(data);
    } catch {
      message.error('Ошибка загрузки портфолио');
    }
    setLoading(false);
  };

  useEffect(() => {
    fetchPhotos();
  }, [masterId]);

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
      message.success('Фото отмечено как основное');
      fetchPhotos();
    } catch {
      message.error('Ошибка');
    }
  };

  return (
    <div>
      <Text className="title-gold text-16 d-block mb-8">Портфолио</Text>

      {!readonly && (
        <div className="mb-12">
          <UploadButton
            entityType="portfolio"
            onUploadSuccess={fetchPhotos}
          />
        </div>
      )}

      <Spin spinning={loading}>
        <Gallery
          photos={photos}
          onPhotoDelete={readonly ? undefined : handleDelete}
          onPhotoSetPrimary={readonly ? undefined : handleSetPrimary}
          readonly={readonly}
          columns={3}
        />
      </Spin>
    </div>
  );
}
