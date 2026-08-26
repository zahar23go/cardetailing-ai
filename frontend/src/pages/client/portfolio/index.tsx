/**
 * Портфолио салона — галерея с фильтром по мастеру, услуге и сортировкой.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Button, Select, Spin, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import Gallery from '../../../components/Gallery';
import {
  getAllPortfolio,
  portfolioServiceLabel,
  type Photo,
} from '../../../api/photos';
import { apiFetch, type Master } from '../api';

const { Text } = Typography;

const ALL_MASTERS = 'all';

const CATEGORY_CHIPS = [
  { key: 'all', label: 'Все' },
  { key: 'polish', label: 'Полировка', match: /полир/i },
  { key: 'wash', label: 'Мойка', match: /мойк/i },
  { key: 'chem', label: 'Химчистка', match: /химчист|салон/i },
] as const;

type CategoryKey = typeof CATEGORY_CHIPS[number]['key'];
type SortKey = 'date' | 'service';

function matchesCategory(photo: Photo, key: CategoryKey) {
  const chip = CATEGORY_CHIPS.find((c) => c.key === key);
  if (!chip || chip.key === 'all' || !('match' in chip)) return true;
  const haystack = `${photo.service_name || ''} ${photo.title || ''}`;
  return chip.match.test(haystack);
}

function sortPhotos(list: Photo[], sort: SortKey) {
  const copy = [...list];
  if (sort === 'service') {
    copy.sort((a, b) => {
      const byName = portfolioServiceLabel(a).localeCompare(portfolioServiceLabel(b), 'ru');
      if (byName !== 0) return byName;
      return (b.created_at || '').localeCompare(a.created_at || '');
    });
    return copy;
  }
  copy.sort((a, b) => (b.created_at || '').localeCompare(a.created_at || ''));
  return copy;
}

export default function ClientPortfolioPage() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [salonMasters, setSalonMasters] = useState<Master[]>([]);
  const [masterName, setMasterName] = useState(ALL_MASTERS);
  const [category, setCategory] = useState<CategoryKey>('all');
  const [sort, setSort] = useState<SortKey>('date');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const [data, mastersResp] = await Promise.all([
          getAllPortfolio(),
          apiFetch<{ items: Master[] }>('/api/masters').catch(() => ({ items: [] as Master[] })),
        ]);
        if (!cancelled) {
          setPhotos(data);
          setSalonMasters(mastersResp.items || []);
        }
      } catch {
        if (!cancelled) message.error('Не удалось загрузить портфолио');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const masters = useMemo(() => {
    const fromPhotos = photos.map((p) => p.uploader_name).filter(Boolean) as string[];
    const fromSalon = salonMasters.map((m) => m.full_name).filter(Boolean);
    return Array.from(new Set([...fromSalon, ...fromPhotos])).sort((a, b) => a.localeCompare(b, 'ru'));
  }, [photos, salonMasters]);

  const filtered = useMemo(() => {
    const list = photos.filter((p) => {
      if (masterName !== ALL_MASTERS && p.uploader_name !== masterName) return false;
      if (category !== 'all' && !matchesCategory(p, category)) return false;
      return true;
    });
    return sortPhotos(list, sort);
  }, [photos, masterName, category, sort]);

  const workCount = filtered.length;
  const masterCount = useMemo(
    () => new Set(filtered.map((p) => p.uploader_name).filter(Boolean)).size,
    [filtered],
  );

  const onAddPhoto = () => {
    message.info('Фото в портфолио добавляет мастер салона');
  };

  return (
    <div className="client-portfolio-page">
      <div className="client-portfolio-head">
        <div>
          <h3>Портфолио</h3>
          <Badge variant="gold">{`Работ: ${workCount} | Мастеров: ${masterCount}`}</Badge>
        </div>
        <Button
          type="primary"
          className="btn-gold portfolio-add-cta"
          icon={<PlusOutlined />}
          onClick={onAddPhoto}
        >
          + Добавить фото
        </Button>
      </div>

      <Card variant="admin" className="client-block client-portfolio-filters is-wide">
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
        <Select
          size="large"
          className="input-luxury client-filter"
          value={masterName}
          onChange={(v) => setMasterName(v)}
          options={[
            { value: ALL_MASTERS, label: 'Все мастера' },
            ...masters.map((n) => ({ value: n, label: n })),
          ]}
        />
        <Select
          size="large"
          className="input-luxury client-filter client-filter-sort"
          value={sort}
          onChange={(v) => setSort(v)}
          options={[
            { value: 'date', label: 'По дате (сначала новые)' },
            { value: 'service', label: 'По услуге (по алфавиту)' },
          ]}
        />
      </Card>

      {loading ? (
        <Spin />
      ) : workCount === 0 ? (
        <Card variant="luxury" className="client-portfolio-empty">
          <div className="portfolio-empty-state" role="status">
            <span className="portfolio-empty-icon" aria-hidden>🖼️</span>
            <Text className="portfolio-empty-title">Нет работ. Добавьте первое фото!</Text>
            <Button
              type="primary"
              className="btn-gold portfolio-add-cta"
              icon={<PlusOutlined />}
              onClick={onAddPhoto}
            >
              + Добавить фото
            </Button>
          </div>
        </Card>
      ) : (
        <div className="client-portfolio-photos is-large">
          <Gallery
            photos={filtered}
            readonly
            columns={2}
            justify="start"
            captionFormat="service-master"
            preserveOrder
          />
        </div>
      )}
    </div>
  );
}
