/* ============================================================
   PortfolioSection — портфолио мастера
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Typography, Spin, Select, Button, Space, message, Row, Col, Card,
} from 'antd';
import { PlusOutlined, FilterOutlined } from '@ant-design/icons';
import { getPhotos, deletePhoto, setPrimaryPhoto, getPortfolioServices } from '../api/photos';
import type { Photo, PortfolioService } from '../api/photos';
import Gallery from './Gallery';
import PortfolioUploadModal from './PortfolioUploadModal';

const { Text } = Typography;
const { Option } = Select;

interface PortfolioSectionProps {
  /** ID мастера */
  masterId: number;
  /** Режим только для чтения */
  readonly?: boolean;
  /** Список всех услуг для селектора */
  allServices?: { id: number; name: string }[];
}

export default function PortfolioSection({
  masterId,
  readonly = false,
  allServices = [],
}: PortfolioSectionProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [serviceFilter, setServiceFilter] = useState<number | undefined>(undefined);
  const [servicesWithPhotos, setServicesWithPhotos] = useState<PortfolioService[]>([]);

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

  const fetchServices = async () => {
    try {
      const data = await getPortfolioServices();
      setServicesWithPhotos(data);
    } catch { /* ignore */ }
  };

  useEffect(() => {
    fetchPhotos();
    fetchServices();
  }, [masterId]);

  const handleDelete = async (photoId: number) => {
    try {
      await deletePhoto(photoId);
      message.success('Фото удалено');
      fetchPhotos();
      fetchServices();
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

  // Фильтрация по услуге
  const filteredPhotos = serviceFilter
    ? photos.filter((p) => p.service_id === serviceFilter)
    : photos;

  // Объединённый список услуг (из всех услуг системы + те, у кого есть фото)
  const serviceOptions = [
    ...allServices.map((s) => ({ id: s.id, name: s.name })),
    ...servicesWithPhotos
      .filter((s) => !allServices.find((as) => as.id === s.service_id))
      .map((s) => ({ id: s.service_id, name: s.service_name })),
  ];
  // Уникальные
  const uniqueServices = serviceOptions.filter(
    (s, i, arr) => arr.findIndex((x) => x.id === s.id) === i,
  );

  return (
    <div>
      <div className="flex-space-between mb-12">
        <Text className="title-gold text-16">Портфолио</Text>
        {!readonly && (
          <Button
            size="small"
            icon={<PlusOutlined />}
            className="btn-action-gold"
            onClick={() => setUploadModalOpen(true)}
          >
            Добавить фото
          </Button>
        )}
      </div>

      {/* Фильтр по услугам */}
      {uniqueServices.length > 0 && (
        <div className="mb-12">
          <Space size="small">
            <FilterOutlined className="text-titanium" />
            <Select
              size="small"
              className="input-luxury"
              placeholder="Все услуги"
              value={serviceFilter}
              onChange={setServiceFilter}
              allowClear
              style={{ minWidth: 180 }}
              onClear={() => setServiceFilter(undefined)}
            >
              {uniqueServices.map((s) => (
                <Option key={s.id} value={s.id}>{s.name}</Option>
              ))}
            </Select>
          </Space>
        </div>
      )}

      <Spin spinning={loading}>
        {filteredPhotos.length === 0 && !loading ? (
          <Card className="card-luxury">
            <Text className="text-titanium d-block text-center">
              {serviceFilter
                ? 'Нет фото для выбранной услуги'
                : 'Нет фотографий в портфолио'}
            </Text>
          </Card>
        ) : (
          <Gallery
            photos={filteredPhotos}
            onPhotoDelete={readonly ? undefined : handleDelete}
            onPhotoSetPrimary={readonly ? undefined : handleSetPrimary}
            readonly={readonly}
            columns={3}
          />
        )}
      </Spin>

      {/* Модальное окно загрузки */}
      <PortfolioUploadModal
        open={uploadModalOpen}
        onClose={() => setUploadModalOpen(false)}
        onSuccess={() => {
          fetchPhotos();
          fetchServices();
        }}
        services={allServices}
      />
    </div>
  );
}
