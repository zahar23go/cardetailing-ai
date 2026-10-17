/**
 * ИИ-Администратор — /ai/admin
 * Настройка салона: услуги, цены, боксы, скидки, мастера. POST /api/ai/admin.
 * Изменения ассистент выполняет только после подтверждения.
 */
import React from 'react';
import { SettingOutlined } from '@ant-design/icons';
import AdminAiChat from '../../../components/AdminAiChat';

export default function AiAdminPage() {
  return (
    <AdminAiChat
      endpoint="/api/ai/admin"
      kicker="AI-ассистент"
      title="ИИ-Администратор"
      lead="Услуги, цены, боксы, скидки и мастера — изменения только после подтверждения"
      assistantLabel="ИИ-Администратор"
      icon={<SettingOutlined />}
      suggestions={[
        'Покажи услуги и цены',
        'Кто из мастеров работает в салоне?',
        'Подготовь скидку 10% на полировку по будням',
      ]}
      emptyTitle="Настройка салона в диалоге"
      emptyHint="Попросите показать или изменить услуги, боксы, скидки и состав мастеров"
      placeholder="Спросите ИИ-администратора…"
      typingText="Проверяю настройки салона…"
    />
  );
}
