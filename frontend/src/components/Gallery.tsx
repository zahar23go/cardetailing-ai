/* ============================================================
   Gallery — сетка фото с управлением
   ============================================================ */

import React, { useState } from 'react';
import {
  Row, Col, Card, Modal, Button, Space, Typography, Popconfirm, message,
} from 'antd';
import {
  DeleteOutlined, StarOutlined, ZoomInOutlined, StarFilled,
} from '@ant-design/icons';
import type { Photo } from '../api/photos';

const { Text } = Typography;

interface GalleryProps {
  /** Массив фото */
  photos: Photo[];
  /** Колбэк удаления */
  onPhotoDelete?: (photoId: number) => void;
  /** Колбэк установки основного */
  onPhotoSetPrimary?: (photoId: number) => void;
  /** Режим только для чтения */
  readonly?: boolean;
  /** Максимальное кол-во колонок */
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
      <div className="card-luxury" style={{ padding: '24px', textAlign: 'center' }}>
        <Text className="text-titanium">Нет фотографий</Text>
      </div>
    );
  }

  const sorted = [...photos].sort((a, b) => (a.sort_order || 0) - (b.sort_order || 0));

  return (
    <>
      <Row gutter={[12, 12]}>
        {sorted.map((photo) => (
          <Col key={photo.id} xs={12} sm={8} md={Math.floor(24 / columns)}>
            <div
              className="card-luxury"
              style={{
                padding: '8px',
                position: 'relative',
                border: photo.is_primary ? '2px solid #C8A977' : '1px solid rgba(255,255,255,0.06)',
                borderRadius: '14px',
                overflow: 'hidden',
                textAlign: 'center',
              }}
            >
              {/* Фото */}
              <img
                src={photo.thumbnail_url || photo.url}
                alt={photo.title || 'Фото'}
                onClick={() => openLightbox(photo.url)}
                style={{
                  width: '100%',
                  height: '120px',
                  objectFit: 'cover',
                  borderRadius: '10px',
                  cursor: 'pointer',
                  display: 'block',
                }}
              />

              {/* Индикатор основного фото */}
              {photo.is_primary && (
                <div style={{ position: 'absolute', top: '14px', left: '14px' }}>
                  <StarFilled style={{ color: '#C8A977', fontSize: '16px' }} />
                </div>
              )}

              {/* Название услуги (для портфолио) */}
              {photo.service_name && (
                <div style={{ position: 'absolute', top: '14px', right: '14px' }}>
                  <span className="tag-category" style={{
                    fontSize: '10px', padding: '2px 8px', borderRadius: '8px',
                    backgroundColor: 'rgba(200,169,119,0.2)', color: '#C8A977',
                  }}>
                    {photo.service_name}
                  </span>
                </div>
              )}

              {/* Описание работы */}
              {photo.description && (
                <div style={{ marginTop: '8px', padding: '4px 4px 0' }}>
                  <Text className="text-titanium text-12"
                    style={{ lineHeight: '1.3', display: 'block' }}>
                    {photo.description}
                  </Text>
                </div>
              )}

              {/* Имя мастера (для портфолио) */}
              {photo.uploader_name && (
                <div style={{ marginTop: '2px', padding: '0 4px' }}>
                  <Text className="text-titanium text-11">🔧 {photo.uploader_name}</Text>
                </div>
              )}

              {/* Действия */}
              {!readonly && (
                <div style={{ marginTop: '8px' }}>
                  <Space size="small" className="w-full" style={{ justifyContent: 'center' }}>
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
            </div>
          </Col>
        ))}
      </Row>

      {/* Lightbox */}
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
          style={{ width: '100%', borderRadius: '12px', display: 'block' }}
        />
      </Modal>
    </>
  );
}
