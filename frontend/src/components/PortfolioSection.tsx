/* ============================================================
   PortfolioSection — портфолио мастера
   ============================================================ */

import React, { useState, useEffect, useMemo } from 'react';
import { Spin, Select, Typography, message } from 'antd';
import { Button } from '../components/ui';
import { ArrowLeftOutlined, PlusOutlined, UserOutlined } from '@ant-design/icons';
import { getPhotos, deletePhoto, setPrimaryPhoto, getPortfolioServices, getAllPortfolio } from '../api/photos';
import type { Photo, PortfolioService } from '../api/photos';
import Gallery from './Gallery';
import PortfolioUploadModal from './PortfolioUploadModal';
import Card from './Card';
import Badge from './Badge';

const { Text } = Typography;

const CATEGORY_CHIPS = [
  { key: 'all', label: 'Все' },
  { key: 'wash', label: 'Мойка', match: /мойк/i },
  { key: 'polish', label: 'Полировка', match: /полир/i },
  { key: 'chem', label: 'Химчистка', match: /химчист|салон/i },
] as const;

type CategoryKey = typeof CATEGORY_CHIPS[number]['key'];

interface PortfolioSectionProps {
  masterId: number;
  masterName?: string;
  masterPhone?: string;
  completedCount?: number;
  readonly?: boolean;
  allServices?: { id: number; name: string }[];
  showAllSalon?: boolean;
}

function matchesCategory(name: string, key: CategoryKey) {
  const chip = CATEGORY_CHIPS.find((c) => c.key === key);
  if (!chip || chip.key === 'all' || !('match' in chip)) return true;
  return chip.match.test(name || '');
}

export default function PortfolioSection({
  masterId,
  masterName,
  masterPhone,
  completedCount,
  readonly = false,
  allServices = [],
  showAllSalon = false,
}: PortfolioSectionProps) {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [loading, setLoading] = useState(false);
  const [uploadModalOpen, setUploadModalOpen] = useState(false);
  const [serviceFilter, setServiceFilter] = useState<number | undefined>();
  const [category, setCategory] = useState<CategoryKey>('all');
  const [servicesWithPhotos, setServicesWithPhotos] = useState<PortfolioService[]>([]);
  const [scope, setScope] = useState<'salon' | 'mine'>('mine');
  const [salonMaster, setSalonMaster] = useState<string | undefined>();

  const fetchPhotos = async () => {
    setLoading(true);
    try {
      const data = scope === 'salon'
        ? await getAllPortfolio()
        : await getPhotos('portfolio', masterId);
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
  }, [masterId, scope]);

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

  const uniqueServices = useMemo(() => {
    const serviceOptions = [
      ...allServices.map((s) => ({ id: s.id, name: s.name })),
      ...servicesWithPhotos
        .filter((s) => !allServices.find((as) => as.id === s.service_id))
        .map((s) => ({ id: s.service_id, name: s.service_name })),
    ];
    return serviceOptions.filter(
      (s, i, arr) => arr.findIndex((x) => x.id === s.id) === i,
    );
  }, [allServices, servicesWithPhotos]);

  const salonMasters = useMemo(() => {
    const names = Array.from(new Set(photos.map((p) => p.uploader_name).filter(Boolean))) as string[];
    return names.sort();
  }, [photos]);

  const filteredPhotos = useMemo(() => photos.filter((p) => {
    if (serviceFilter && p.service_id !== serviceFilter) return false;
    if (scope === 'salon' && salonMaster && p.uploader_name !== salonMaster) return false;
    if (category !== 'all') {
      const name = p.service_name
        || uniqueServices.find((s) => s.id === p.service_id)?.name
        || '';
      return matchesCategory(name, category);
    }
    return true;
  }), [photos, serviceFilter, category, uniqueServices, scope, salonMaster]);

  const serviceCount = new Set(
    photos.map((p) => p.service_id).filter(Boolean),
  ).size;

  const openSalon = () => {
    setScope('salon');
    setSalonMaster(undefined);
    setServiceFilter(undefined);
    setCategory('all');
  };

  const gallery = (
    <Spin spinning={loading}>
      {filteredPhotos.length === 0 && !loading ? (
        <Card variant="admin" className="gallery-empty">
          <Text className="text-titanium">
            {serviceFilter || category !== 'all' || salonMaster
              ? 'Нет фото для выбранной услуги'
              : 'Нет фотографий в портфолио'}
          </Text>
        </Card>
      ) : (
        <Gallery
          photos={filteredPhotos}
          onPhotoDelete={scope === 'mine' && !readonly ? handleDelete : undefined}
          onPhotoSetPrimary={scope === 'mine' && !readonly ? handleSetPrimary : undefined}
          readonly={scope !== 'mine' || readonly}
          columns={3}
          justify={scope === 'mine' ? 'end' : 'start'}
        />
      )}
    </Spin>
  );

  const filters = (
    <Card variant="admin" className="master-portfolio-filters">
      <div className="portfolio-chips">
        {CATEGORY_CHIPS.map((chip) => (
          <button
            key={chip.key}
            type="button"
            className={`portfolio-chip${category === chip.key ? ' is-active' : ''}`}
            onClick={() => setCategory(chip.key)}
          >
            {chip.label}
          </button>
        ))}
      </div>
      {scope === 'salon' && salonMasters.length > 0 ? (
        <Select
          allowClear
          size="large"
          className="input-luxury client-filter"
          placeholder="Все мастера"
          value={salonMaster}
          onChange={(v) => setSalonMaster(v)}
          options={salonMasters.map((n) => ({ value: n, label: `Работы от ${n}` }))}
        />
      ) : null}
      {uniqueServices.length > 0 ? (
        <Select
          allowClear
          size="large"
          className="input-luxury client-filter"
          placeholder="Все услуги"
          value={serviceFilter}
          onChange={(v) => setServiceFilter(v)}
          options={uniqueServices.map((s) => ({ value: s.id, label: s.name }))}
        />
      ) : null}
    </Card>
  );

  return (
    <div className="master-portfolio">
      {scope === 'mine' ? (
        <>
          <div className="master-portfolio-toolbar">
            <Button
              type="primary"
              look="gold"
              icon={<ArrowLeftOutlined />}
              onClick={openSalon}
            >
              Назад ко всем портфолио
            </Button>
          </div>
          <div className="master-portfolio-top">
            {masterName ? (
              <Card variant="admin" className="master-portfolio-hero">
                <div className="master-portfolio-hero-row">
                  <div className="master-portfolio-avatar" aria-hidden>
                    <UserOutlined />
                  </div>
                  <div className="master-portfolio-who">
                    <div className="master-portfolio-name">{masterName}</div>
                    <Badge variant="gold" size="sm">Мастер-детейлер</Badge>
                    {masterPhone ? (
                      <Text className="text-titanium d-block">{masterPhone}</Text>
                    ) : null}
                  </div>
                </div>
                {!readonly ? (
                  <Button
                    type="primary"
                    look="gold" className="master-portfolio-add"
                    icon={<PlusOutlined />}
                    onClick={() => setUploadModalOpen(true)}
                  >
                    + Добавить фото
                  </Button>
                ) : null}
                <div className="master-portfolio-stats">
                  <div className="master-portfolio-stat">
                    <div className="admin-kpi-value">{photos.length}</div>
                    <div className="admin-kpi-label">Фото</div>
                  </div>
                  <div className="master-portfolio-stat">
                    <div className="admin-kpi-value">{serviceCount}</div>
                    <div className="admin-kpi-label">Услуги</div>
                  </div>
                  <div className="master-portfolio-stat">
                    <div className="admin-kpi-value">{completedCount ?? 0}</div>
                    <div className="admin-kpi-label">Выполнено</div>
                  </div>
                </div>
              </Card>
            ) : (
              <div className="admin-section-head">
                <div>
                  <h3>Портфолио</h3>
                  <Badge variant="gold">Работы мастера</Badge>
                </div>
                {!readonly ? (
                  <Button
                    type="primary"
                    look="gold"
                    icon={<PlusOutlined />}
                    onClick={() => setUploadModalOpen(true)}
                  >
                    + Добавить фото
                  </Button>
                ) : null}
              </div>
            )}
            <div className="master-portfolio-photos">{gallery}</div>
          </div>
          {filters}
        </>
      ) : (
        <>
          <div className="admin-section-head">
            <div>
              <h3>Портфолио салона</h3>
              <Badge variant="gold">Работы всех мастеров</Badge>
            </div>
            <Button type="primary" look="gold" onClick={() => setScope('mine')}>
              Моё портфолио
            </Button>
          </div>
          {filters}
          {gallery}
        </>
      )}

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
