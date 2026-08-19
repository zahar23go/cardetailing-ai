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
import type { Photo } from '../api/photos';
import Card from './Card';

const { Text } = Typography;

interface GalleryProps {
  photos: Photo[];
  onPhotoDelete?: (photoId: number) => void;
  onPhotoSetPrimary?: (photoId: number) => void;
  readonly?: boolean;
  columns?: number;
}

export default function Gallery({
  photos,
  onPhotoDelete,
  onPhotoSetPrimary,
  readonly = false,
  columns = 4,
}: GalleryProps) {
  const [lightboxOpen, setLightboxOpen] = useState(false);
  const [lightboxUrl, setLightboxUrl] = useState('');

  const openLightbox = (url: string) => {
    setLightboxUrl(url);
    setLightboxOpen(true);
  };

  if (photos.length === 0) {
    return (
      <Card variant="luxury" className="gallery-empty">
        <Text className="text-titanium">Нет фотографий</Text>
      </Card>
    );
  }

  const sorted = [...photos].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

  return (
    <>
      <Row gutter={[12, 12]}>
        {sorted.map((photo) => (
          <Col key={photo.id} xs={12} sm={8} md={Math.floor(24 / columns)}>
            <Card
              variant="luxury"
              className={`gallery-item${photo.is_primary ? ' is-primary' : ''}`}
            >
              <img
                src={photo.thumbnail_url || photo.url}
                alt={photo.title || 'Фото'}
                onClick={() => openLightbox(photo.url)}
                className="gallery-item-img"
              />

              {photo.is_primary && (
                <StarFilled className="gallery-item-star" />
              )}

              {photo.service_name && (
                <span className="tag-category gallery-item-tag">
                  {photo.service_name}
                </span>
              )}

              {photo.description && (
                <div className="gallery-item-caption">
                  <Text className="text-titanium text-12">{photo.description}</Text>
                </div>
              )}

              {photo.uploader_name && (
                <div className="gallery-item-master">
                  <UserOutlined />
                  <Text className="text-titanium text-11">{photo.uploader_name}</Text>
                </div>
              )}

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
                      onClick={() => openLightbox(photo.url)}
                    />
                  </Space>
                </div>
              )}
            </Card>
          </Col>
        ))}
      </Row>

      <Modal
        open={lightboxOpen}
        footer={null}
        onCancel={() => setLightboxOpen(false)}
        className="modal-command"
        width={800}
      >
        <img
          alt="lightbox"
          src={lightboxUrl}
          className="gallery-lightbox-img"
        />
      </Modal>
    </>
  );
}
