/* ============================================================
   PortfolioUploadModal — модальное окно для загрузки фото
   в портфолио с привязкой к услуге и описанием
   ============================================================ */

import React, { useState, useEffect } from 'react';
import {
  Modal, Upload, Select, Input, Button, Space, Typography, message,
} from 'antd';
import { InboxOutlined } from '@ant-design/icons';
import { uploadPortfolioPhoto } from '../api/photos';

const { Text } = Typography;
const { Dragger } = Upload;
const { Option } = Select;
const { TextArea } = Input;

const ALLOWED_TYPES = ['image/jpeg', 'image/png', 'image/webp'];
const MAX_SIZE = 10 * 1024 * 1024; // 10 MB

interface ServiceOption {
  id: number;
  name: string;
}

interface PortfolioUploadModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess: () => void;
  services: ServiceOption[];
}

export default function PortfolioUploadModal({
  open,
  onClose,
  onSuccess,
  services,
}: PortfolioUploadModalProps) {
  const [file, setFile] = useState<File | null>(null);
  const [serviceId, setServiceId] = useState<number | undefined>(undefined);
  const [description, setDescription] = useState('');
  const [title, setTitle] = useState('');
  const [uploading, setUploading] = useState(false);

  // Reset form on open
  useEffect(() => {
    if (open) {
      setFile(null);
      setServiceId(undefined);
      setDescription('');
      setTitle('');
    }
  }, [open]);

  const handleUpload = async () => {
    if (!file) {
      message.warning('Выберите фото');
      return;
    }
    setUploading(true);
    try {
      await uploadPortfolioPhoto(
        file,
        title || undefined,
        serviceId,
        description || undefined,
      );
      message.success('✅ Фото добавлено в портфолио');
      onSuccess();
      onClose();
    } catch (e: any) {
      message.error(e.message || 'Ошибка загрузки');
    }
    setUploading(false);
  };

  return (
    <Modal
      title={<Text className="text-white">📸 Добавить фото в портфолио</Text>}
      open={open}
      onCancel={onClose}
      footer={null}
      className="modal-command"
      width={520}
    >
      <Space direction="vertical" size="middle" className="w-full">
        {/* Выбор файла */}
        <div>
          <Text className="text-titanium d-block mb-4">Фото *</Text>
          <Dragger
            name="file"
            multiple={false}
            accept=".jpg,.jpeg,.png,.webp"
            showUploadList={true}
            beforeUpload={(f) => {
              if (!ALLOWED_TYPES.includes(f.type)) {
                message.error(`Недопустимый формат: ${f.type}`);
                return Upload.LIST_IGNORE;
              }
              if (f.size > MAX_SIZE) {
                message.error(`Файл слишком большой (макс. 10 MB)`);
                return Upload.LIST_IGNORE;
              }
              setFile(f);
              return false; // Prevent auto upload
            }}
            onRemove={() => setFile(null)}
          >
            <p className="text-center">
              <InboxOutlined style={{ fontSize: '36px', color: '#C8A977' }} />
            </p>
            <p className="text-titanium">
              Нажмите или перетащите файл сюда
            </p>
            <p className="text-small">JPG, PNG, WEBP. До 10 MB.</p>
          </Dragger>
        </div>

        {/* Название (опционально) */}
        <div>
          <Text className="text-titanium d-block mb-4">Название (опционально)</Text>
          <Input
            className="input-luxury"
            placeholder="Например: Полировка фар"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
          />
        </div>

        {/* Выбор услуги */}
        <div>
          <Text className="text-titanium d-block mb-4">Услуга</Text>
          <Select
            className="w-full"
            size="large"
            placeholder="Выберите услугу"
            value={serviceId}
            onChange={setServiceId}
            allowClear
          >
            {services.map((s) => (
              <Option key={s.id} value={s.id}>{s.name}</Option>
            ))}
          </Select>
        </div>

        {/* Описание работы (было → стало) */}
        <div>
          <Text className="text-titanium d-block mb-4">
            Описание работы (было → стало)
          </Text>
          <TextArea
            className="input-luxury"
            rows={3}
            placeholder="Например: Было: фары жёлтые, потёртые → Стало: прозрачные, как новые"
            value={description}
            onChange={(e) => setDescription(e.target.value)}
          />
        </div>

        {/* Кнопки */}
        <div className="flex-space-between" style={{ paddingTop: 8 }}>
          <Button onClick={onClose} className="btn-logout">
            Отмена
          </Button>
          <Button
            type="primary"
            className="btn-gold"
            onClick={handleUpload}
            loading={uploading}
            disabled={!file}
          >
            Загрузить
          </Button>
        </div>
      </Space>
    </Modal>
  );
}
