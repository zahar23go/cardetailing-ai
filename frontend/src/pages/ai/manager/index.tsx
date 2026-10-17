/**
 * ИИ-Управляющий — /ai/manager
 * Операционка смены: расписание, загрузка боксов и мастеров. POST /api/ai/manager.
 */
import React from 'react';
import { ScheduleOutlined } from '@ant-design/icons';
import AdminAiChat from '../../../components/AdminAiChat';

export default function AiManagerPage() {
  return (
    <AdminAiChat
      endpoint="/api/ai/manager"
      kicker="AI-ассистент"
      title="ИИ-Управляющий"
      lead="Расписание смены, загрузка боксов и мастеров — по реальным данным салона"
      assistantLabel="ИИ-Управляющий"
      icon={<ScheduleOutlined />}
      suggestions={[
        'Что сегодня в расписании?',
        'Где просадка по загрузке за неделю?',
        'Что требует внимания прямо сейчас?',
      ]}
      emptyTitle="Смена под контролем"
      emptyHint="Спросите про расписание, загрузку боксов, неподтверждённые и просроченные заезды"
      placeholder="Спросите ИИ-управляющего…"
      typingText="Смотрю расписание и загрузку…"
    />
  );
}
