/**
 * Портфолио салона — галерея с фильтром по мастеру и услуге.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Empty, Select, Space, Spin, Typography, message } from 'antd';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import Gallery from '../../../components/Gallery';
import { getAllPortfolio, getPortfolioServices, type Photo, type PortfolioService } from '../../../api/photos';

const { Text } = Typography;

export default function ClientPortfolioPage() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [services, setServices] = useState<PortfolioService[]>([]);
  const [serviceId, setServiceId] = useState<number | undefined>();
  const [masterName, setMasterName] = useState<string | undefined>();
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    getPortfolioServices().then(setServices).catch(() => undefined);
  }, []);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await getAllPortfolio(serviceId);
        if (!cancelled) setPhotos(data);
      } catch {
        if (!cancelled) message.error('Не удалось загрузить портфолио');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, [serviceId]);

  const masters = useMemo(() => {
    const names = Array.from(new Set(photos.map((p) => p.uploader_name).filter(Boolean))) as string[];
    return names.sort();
  }, [photos]);

  const filtered = useMemo(() => {
    if (!masterName) return photos;
    return photos.filter((p) => p.uploader_name === masterName);
  }, [photos, masterName]);

  return (
    <>
      <div className="admin-section-head">
        <div>
          <h3>Портфолио</h3>
          <Text className="text-titanium">Работы мастеров: полировка, мойка, химчистка</Text>
        </div>
      </div>

      <Card variant="admin" className="client-block">
        <Space wrap>
          <Select
            allowClear
            placeholder="Услуга"
            className="input-luxury"
            style={{ minWidth: 200 }}
            value={serviceId}
            onChange={(v) => setServiceId(v)}
            options={services.map((s) => ({
              value: s.service_id,
              label: `${s.service_name} (${s.photo_count})`,
            }))}
          />
          <Select
            allowClear
            placeholder="Мастер"
            className="input-luxury"
            style={{ minWidth: 200 }}
            value={masterName}
            onChange={(v) => setMasterName(v)}
            options={masters.map((n) => ({ value: n, label: `Работы от ${n}` }))}
          />
        </Space>
      </Card>

      {loading ? (
        <Spin />
      ) : filtered.length === 0 ? (
        <Empty description={<Text className="text-titanium">Пока нет фото</Text>} />
      ) : (
        <>
          {masterName ? (
            <div className="client-section-title">
              <Badge variant="gold">{`Работы от ${masterName}`}</Badge>
            </div>
          ) : null}
          <Gallery photos={filtered} readonly columns={3} />
        </>
      )}
    </>
  );
}
