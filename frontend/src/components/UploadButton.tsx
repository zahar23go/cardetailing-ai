/* ============================================================
   UploadButton — загрузка фото с Drag & Drop и превью
   ============================================================ */

import React, { useState } from 'react';
import { Upload, message, Button, Modal, Space, Typography } from 'antd';
import { UploadOutlined, InboxOutlined } from '@ant-design/icons';

const { Dragger } = Upload;
const { Text } = Typography;

interface UploadButtonProps {
  /** Тип сущности: car, appointment, portfolio */
  entityType: 'car' | 'appointment' | 'portfolio';
  /** ID сущности (не нужен для portfolio) */
  entityId?: number;
  /** Колбэк после успешной загрузки */
  onUploadSuccess: () => void;
  /** Максимальное количество файлов */
  maxFiles?: number;
}

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

/** Получить URL для загрузки в зависимости от типа */
function getUploadUrl(entityType: string, entityId?: number): string {
  if (entityType === 'car' && entityId) return `/api/upload/car/${entityId}`;
  if (entityType === 'appointment' && entityId) return `/api/upload/appointment/${entityId}`;
  return '/api/upload/portfolio';
}

export default function UploadButton({
  entityType,
  entityId,
  onUploadSuccess,
  maxFiles = 5,
}: UploadButtonProps) {
  const [previewOpen, setPreviewOpen] = useState(false);
  const [previewImage, setPreviewImage] = useState('');

  const uploadUrl = getUploadUrl(entityType, entityId);

  const handlePreview = (file: any) => {
    setPreviewImage(file.url || file.thumbUrl || URL.createObjectURL(file.originFileObj));
    setPreviewOpen(true);
  };

  return (
    <>
      <Dragger
        name="file"
        action={uploadUrl}
        headers={{
          Authorization: `Bearer ${localStorage.getItem('token')}`,
        }}
        maxCount={maxFiles}
        multiple={false}
        accept=".jpg,.jpeg,.png,.webp"
        showUploadList={true}
        onPreview={handlePreview}
        beforeUpload={(file) => {
          if (!ALLOWED_TYPES.includes(file.type)) {
            message.error(`Недопустимый формат: ${file.type}. Разрешены: JPG, PNG, WEBP`);
            return Upload.LIST_IGNORE;
          }
          if (file.size > MAX_SIZE) {
            message.error(`Файл слишком большой: ${(file.size / 1024 / 1024).toFixed(1)} MB. Максимум: 10 MB`);
            return Upload.LIST_IGNORE;
          }
          return true;
        }}
        onChange={(info) => {
          const { status } = info.file;
          if (status === 'done') {
            message.success(`✅ Фото "${info.file.name}" загружено`);
            onUploadSuccess();
          } else if (status === 'error') {
            message.error(`❌ Ошибка загрузки "${info.file.name}"`);
          }
        }}
      >
        <p className="text-center">
          <InboxOutlined style={{ fontSize: '36px', color: '#C8A977' }} />
        </p>
        <p className="text-titanium">
          <UploadOutlined /> Нажмите или перетащите файл сюда
        </p>
        <p className="text-small">
          JPG, PNG, WEBP. Максимум 10 MB.
        </p>
      </Dragger>

      <Modal
        open={previewOpen}
        title={<span className="text-white">Превью</span>}
        footer={null}
        onCancel={() => setPreviewOpen(false)}
        className="modal-command"
      >
        <img alt="preview" src={previewImage} className="w-full" />
      </Modal>
    </>
  );
}
