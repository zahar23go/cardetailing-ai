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
import type { Photo } from '../api/photos';
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
}

type Lightbox = { url: string; service?: string; date?: string; description?: string };

function looksLikeFilename(value?: string) {
  if (!value) return false;
  return /\.(jpe?g|png|webp|gif|bmp)$/i.test(value.trim());
}

function photoLabel(photo: Photo) {
  if (photo.service_name) return photo.service_name;
  if (photo.title && !looksLikeFilename(photo.title)) return photo.title;
  return 'Работа';
}

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
}: GalleryProps) {
  const [lightbox, setLightbox] = useState<Lightbox | null>(null);

  const openLightbox = (photo: Photo) => {
    setLightbox({
      url: photo.url,
      service: photoLabel(photo),
      date: photoDate(photo.created_at),
      description: photo.description && !looksLikeFilename(photo.description)
        ? photo.description
        : '',
    });
  };

  if (photos.length === 0) {
    return (
      <Card variant="luxury" className="gallery-empty">
        <Text className="text-titanium">Нет фотографий</Text>
      </Card>
    );
  }

  const sorted = [...photos].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));
  const colCount = Math.max(1, Math.min(columns, 4));
  const mdSpan = Math.floor(24 / colCount);

  return (
    <>
      <Row gutter={[16, 16]} className="gallery-grid" justify={justify}>
        {sorted.map((photo) => {
          const date = photoDate(photo.created_at);
          const service = photoLabel(photo);
          const extra = photo.description && !looksLikeFilename(photo.description)
            ? photo.description
            : '';
          return (
            <Col
              key={photo.id}
              xs={colCount === 1 ? 24 : 12}
              sm={colCount === 1 ? 24 : colCount === 2 ? 12 : 8}
              md={mdSpan}
            >
              <Card
                variant="luxury"
                className={`gallery-item${photo.is_primary ? ' is-primary' : ''}`}
              >
                <button
                  type="button"
                  className="gallery-item-preview"
                  onClick={() => openLightbox(photo)}
                  aria-label={`Открыть ${service}`}
                >
                  <img
                    src={photo.thumbnail_url || photo.url}
                    alt={photo.title || service}
                    className="gallery-item-img"
                  />
                  <span className="gallery-item-zoom" aria-hidden>
                    <ZoomInOutlined />
                  </span>
                </button>

                {photo.is_primary && (
                  <StarFilled className="gallery-item-star" />
                )}

                <div className="gallery-item-meta">
                  <div className="gallery-item-service">{service}</div>
                  {photo.uploader_name ? (
                    <div className="gallery-item-master">
                      <UserOutlined />
                      <span>{photo.uploader_name}</span>
                    </div>
                  ) : null}
                  {date ? <div className="gallery-item-date">{date}</div> : null}
                  {extra ? (
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
              alt={lightbox.service || 'Фото'}
              src={lightbox.url}
              className="gallery-lightbox-img"
            />
            <div className="gallery-lightbox-meta">
              {lightbox.service ? (
                <div className="gallery-item-service">{lightbox.service}</div>
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
