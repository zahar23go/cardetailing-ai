/* ============================================================
   Gallery — сетка фото с управлением
   ============================================================ */

import React, { useState } from 'react';
import {
  Row, Col, Modal, Button, Space, Typography, Popconfirm,
} from 'antd';
import {
  DeleteOutlined, StarOutlined, ZoomInOutlined, StarFilled, UserOutlined,
} from '@ant-design/icons';
import dayjs from 'dayjs';
import 'dayjs/locale/ru';
import {
  demoPortfolioImage,
  looksLikeFilename,
  portfolioCaption,
  portfolioServiceLabel,
  type Photo,
} from '../api/photos';
import Card from './Card';

dayjs.locale('ru');
const { Text } = Typography;

interface GalleryProps {
  photos: Photo[];
  onPhotoDelete?: (photoId: number) => void;
  onPhotoSetPrimary?: (photoId: number) => void;
  readonly?: boolean;
  columns?: number;
  justify?: 'start' | 'end' | 'center';
  /** «Услуга — мастер» вместо раздельных строк. */
  captionFormat?: 'default' | 'service-master';
  /** Не пересортировывать — порядок задаёт родитель. */
  preserveOrder?: boolean;
}

type Lightbox = { url: string; caption: string; date?: string; description?: string };

function photoDate(iso?: string) {
  if (!iso) return '';
  const d = dayjs(iso);
  return d.isValid() ? d.format('D MMMM YYYY') : '';
}

export default function Gallery({
  photos,
  onPhotoDelete,
  onPhotoSetPrimary,
  readonly = false,
  columns = 4,
  justify = 'start',
  captionFormat = 'default',
  preserveOrder = false,
}: GalleryProps) {
  const [lightbox, setLightbox] = useState<Lightbox | null>(null);
  const unified = captionFormat === 'service-master';

  const openLightbox = (photo: Photo) => {
    const caption = unified ? portfolioCaption(photo) : portfolioServiceLabel(photo);
    const extra = photo.description && !looksLikeFilename(photo.description)
      ? photo.description
      : '';
    setLightbox({
      url: photo.url,
      caption,
      date: photoDate(photo.created_at),
      description: extra === 'Пример работы мастера' ? '' : extra,
    });
  };

  if (photos.length === 0) {
    return (
      <Card variant="luxury" className="gallery-empty">
        <Text className="text-titanium">Нет фотографий</Text>
      </Card>
    );
  }

  const sorted = preserveOrder
    ? photos
    : [...photos].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  const colCount = Math.max(1, Math.min(columns, 4));
  const mdSpan = Math.floor(24 / colCount);

  return (
    <>
      <Row gutter={[16, 16]} className="gallery-grid" justify={justify}>
        {sorted.map((photo) => {
          const date = photoDate(photo.created_at);
          const service = portfolioServiceLabel(photo);
          const caption = unified ? portfolioCaption(photo) : service;
          const extra = photo.description && !looksLikeFilename(photo.description)
            ? photo.description
            : '';
          const showExtra = extra && extra !== 'Пример работы мастера';
          return (
            <Col
              key={photo.id}
              xs={colCount === 1 ? 24 : 12}
              sm={colCount === 1 ? 24 : colCount === 2 ? 12 : 8}
              md={mdSpan}
            >
              <Card
                variant="luxury"
                className={`gallery-item${photo.is_primary ? ' is-primary' : ''}${unified ? ' is-unified' : ''}`}
              >
                <button
                  type="button"
                  className="gallery-item-preview"
                  onClick={() => openLightbox(photo)}
                  aria-label={`Открыть ${caption}`}
                >
                  <img
                    src={photo.thumbnail_url || photo.url}
                    alt={caption}
                    className="gallery-item-img"
                    onError={(e) => {
                      const el = e.currentTarget;
                      if (el.dataset.fallback === '1') return;
                      el.dataset.fallback = '1';
                      el.src = demoPortfolioImage(`${photo.service_name || ''} ${photo.title || ''}`);
                    }}
                  />
                  <span className="gallery-item-zoom" aria-hidden>
                    <ZoomInOutlined />
                  </span>
                </button>

                {photo.is_primary && (
                  <StarFilled className="gallery-item-star" />
                )}

                <div className="gallery-item-meta">
                  <div className="gallery-item-service">{caption}</div>
                  {!unified && photo.uploader_name ? (
                    <div className="gallery-item-master">
                      <UserOutlined />
                      <span>{photo.uploader_name}</span>
                    </div>
                  ) : null}
                  {date ? <div className="gallery-item-date">{date}</div> : null}
                  {showExtra ? (
                    <Text className="text-titanium text-12 gallery-item-desc">
                      {extra}
                    </Text>
                  ) : null}
                </div>

                {!readonly && (
                  <div className="gallery-item-actions">
                    <Space size="small" className="w-full gallery-item-actions-inner">
                      {onPhotoSetPrimary && !photo.is_primary && (
                        <Button
                          size="small"
                          className="btn-action-gold"
                          icon={<StarOutlined />}
                          onClick={() => onPhotoSetPrimary(photo.id)}
                        />
                      )}
                      {onPhotoDelete && (
                        <Popconfirm
                          title="Удалить это фото?"
                          onConfirm={() => onPhotoDelete(photo.id)}
                          okText="Да"
                          cancelText="Нет"
                        >
                          <Button
                            size="small"
                            className="btn-action-danger"
                            icon={<DeleteOutlined />}
                          />
                        </Popconfirm>
                      )}
                      <Button
                        size="small"
                        className="btn-action-gold"
                        icon={<ZoomInOutlined />}
                        onClick={() => openLightbox(photo)}
                      />
                    </Space>
                  </div>
                )}
              </Card>
            </Col>
          );
        })}
      </Row>

      <Modal
        open={!!lightbox}
        footer={null}
        onCancel={() => setLightbox(null)}
        className="modal-command gallery-lightbox"
        width={800}
      >
        {lightbox ? (
          <>
            <img
              alt={lightbox.caption || 'Фото'}
              src={lightbox.url}
              className="gallery-lightbox-img"
              onError={(e) => {
                const el = e.currentTarget;
                if (el.dataset.fallback === '1') return;
                el.dataset.fallback = '1';
                el.src = demoPortfolioImage(lightbox.caption);
              }}
            />
            <div className="gallery-lightbox-meta">
              {lightbox.caption ? (
                <div className="gallery-item-service">{lightbox.caption}</div>
              ) : null}
              {lightbox.date ? (
                <div className="gallery-item-date">{lightbox.date}</div>
              ) : null}
              {lightbox.description ? (
                <Text className="text-titanium">{lightbox.description}</Text>
              ) : null}
            </div>
          </>
        ) : null}
      </Modal>
    </>
  );
}
