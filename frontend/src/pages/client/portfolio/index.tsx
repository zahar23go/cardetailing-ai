/**
 * Портфолио салона — галерея с фильтром по мастеру и услуге.
 * Неполный ряд дополняется заглушками, чтобы справа не оставалось пустого места.
 */
import React, { useEffect, useMemo, useState } from 'react';
import { Button, Select, Spin, Typography, message } from 'antd';
import { PlusOutlined } from '@ant-design/icons';
import Card from '../../../components/Card';
import Badge from '../../../components/Badge';
import Gallery from '../../../components/Gallery';
import { getAllPortfolio, type Photo } from '../../../api/photos';

const { Text } = Typography;

const CATEGORY_CHIPS = [
  { key: 'all', label: 'Все' },
  { key: 'polish', label: 'Полировка', match: /полир/i },
  { key: 'wash', label: 'Мойка', match: /мойк/i },
  { key: 'chem', label: 'Химчистка', match: /химчист|салон/i },
] as const;

const DEMO_CARDS = [
  { key: 'wash', label: 'Мойка', icon: '🧽', tone: 'blue', visual: 'is-wash' },
  { key: 'polish', label: 'Полировка', icon: '✨', tone: 'gold', visual: 'is-polish' },
  { key: 'chem', label: 'Химчистка', icon: '🧴', tone: 'green', visual: 'is-chem' },
] as const;

type CategoryKey = typeof CATEGORY_CHIPS[number]['key'];
type DemoCard = typeof DEMO_CARDS[number];

function matchesCategory(photo: Photo, key: CategoryKey) {
  const chip = CATEGORY_CHIPS.find((c) => c.key === key);
  if (!chip || chip.key === 'all' || !('match' in chip)) return true;
  const haystack = `${photo.service_name || ''} ${photo.title || ''}`;
  return chip.match.test(haystack);
}

function padDemos(photoCount: number): DemoCard[] {
  const remainder = photoCount % 3;
  const need = photoCount === 0 ? 3 : remainder === 0 ? 0 : 3 - remainder;
  const cards: DemoCard[] = [];
  for (let i = 0; i < need; i += 1) {
    cards.push(DEMO_CARDS[i % DEMO_CARDS.length]);
  }
  return cards;
}

function PlaceholderCard({ demo }: { demo: DemoCard }) {
  return (
    <Card variant="luxury" className={`gallery-item portfolio-ph is-${demo.tone}`}>
      <div className={`portfolio-ph-visual ${demo.visual}`}>
        <span className="portfolio-ph-icon" aria-hidden>{demo.icon}</span>
        <span className="portfolio-ph-label">{demo.label}</span>
      </div>
      <div className="gallery-item-meta">
        <div className="gallery-item-service">{demo.label}</div>
        <div className="gallery-item-date">Пример работы мастера</div>
      </div>
    </Card>
  );
}

export default function ClientPortfolioPage() {
  const [photos, setPhotos] = useState<Photo[]>([]);
  const [masterName, setMasterName] = useState<string | undefined>();
  const [category, setCategory] = useState<CategoryKey>('all');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    let cancelled = false;
    (async () => {
      setLoading(true);
      try {
        const data = await getAllPortfolio();
        if (!cancelled) setPhotos(data);
      } catch {
        if (!cancelled) message.error('Не удалось загрузить портфолио');
      }
      if (!cancelled) setLoading(false);
    })();
    return () => { cancelled = true; };
  }, []);

  const masters = useMemo(() => {
    const names = Array.from(new Set(photos.map((p) => p.uploader_name).filter(Boolean))) as string[];
    return names.sort();
  }, [photos]);

  const filtered = useMemo(() => photos.filter((p) => {
    if (masterName && p.uploader_name !== masterName) return false;
    if (category !== 'all' && !matchesCategory(p, category)) return false;
    return true;
  }), [photos, masterName, category]);

  const fillers = padDemos(filtered.length);
  const empty = filtered.length === 0;
  const categoryLabel = CATEGORY_CHIPS.find((c) => c.key === category)?.label;
  const masterCaption = masterName
    ? (category !== 'all' && categoryLabel
      ? `${categoryLabel} от ${masterName}`
      : `Работы от ${masterName}`)
    : null;

  const onAddPhoto = () => {
    message.info('Фото в портфолио добавляет мастер салона');
  };

  return (
    <div className="client-portfolio-page">
      <div className="client-portfolio-head">
        <div>
          <h3>Портфолио</h3>
          <Badge variant="gold">Работы мастеров: полировка, мойка, химчистка</Badge>
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
          allowClear
          size="large"
          placeholder="Мастер"
          className="input-luxury client-filter"
          value={masterName}
          onChange={(v) => setMasterName(v)}
          options={masters.map((n) => ({ value: n, label: `Работы от ${n}` }))}
        />
        {masterCaption ? (
          <Badge variant="gold">{masterCaption}</Badge>
        ) : null}
      </Card>

      {loading ? (
        <Spin />
      ) : (
        <div className="client-portfolio-photos">
          {empty ? (
            <div className="portfolio-add-wrap">
              <Button
                type="primary"
                className="btn-gold portfolio-add-cta"
                icon={<PlusOutlined />}
                onClick={onAddPhoto}
              >
                + Добавить фото
              </Button>
              <Text className="text-titanium portfolio-empty-hint">
                Пока мало фото — справа примеры услуг салона.
              </Text>
            </div>
          ) : null}
          {masterName ? (
            <div className="client-section-title">
              <Badge variant="gold">{`Работы от ${masterName}`}</Badge>
            </div>
          ) : null}
          {filtered.length > 0 ? (
            <Gallery photos={filtered} readonly columns={3} justify="start" />
          ) : null}
          {fillers.map((demo, index) => (
            <PlaceholderCard key={`${demo.key}-${index}`} demo={demo} />
          ))}
        </div>
      )}
    </div>
  );
}
