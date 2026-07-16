/* ============================================================
   HistoryTimeline — временная шкала изменений записи
   ============================================================ */

import React from 'react';
import { Typography, Tag, Space, Empty } from 'antd';
import dayjs from 'dayjs';
import type { HistoryEntry } from '../api/history';

const { Text } = Typography;

const CHANGE_ICONS: Record<string, string> = {
  create: '✅',
  update: '✏️',
  cancel: '❌',
  move: '🕐',
  status_change: '📝',
};

const CHANGE_LABELS: Record<string, string> = {
  create: 'Создание',
  update: 'Изменение',
  cancel: 'Отмена',
  move: 'Перенос',
  status_change: 'Статус',
};

const FIELD_LABELS: Record<string, string> = {
  status: 'статус',
  start_time: 'время',
  end_time: 'время окончания',
  total_price: 'цена',
  master_id: 'мастера',
  car_id: 'автомобиль',
  service_id: 'услугу',
  client_notes: 'заметки',
  master_brief: 'заметки мастера',
  appointment: 'запись',
};

interface HistoryTimelineProps {
  items: HistoryEntry[];
}

function formatChange(item: HistoryEntry): string {
  const field = FIELD_LABELS[item.field_name || ''] || item.field_name;

  if (item.change_type === 'create') return item.new_value || 'Запись создана';
  if (item.change_type === 'cancel') return 'Запись отменена';
  if (item.change_type === 'status_change') return `${item.old_value} → ${item.new_value}`;
  if (item.change_type === 'move') return `${item.old_value?.slice(11, 16) || ''} → ${item.new_value?.slice(11, 16) || ''}`;
  if (item.change_type === 'update' && field) return `${field}: ${item.old_value || '—'} → ${item.new_value || '—'}`;
  return item.new_value || '';
}

function groupByDate(items: HistoryEntry[]): Map<string, HistoryEntry[]> {
  const groups = new Map<string, HistoryEntry[]>();
  const today = dayjs().format('YYYY-MM-DD');
  const yesterday = dayjs().subtract(1, 'day').format('YYYY-MM-DD');

  for (const item of items) {
    const date = item.created_at ? dayjs(item.created_at).format('YYYY-MM-DD') : today;
    let label = date;
    if (date === today) label = 'Сегодня';
    else if (date === yesterday) label = 'Вчера';
    else label = dayjs(date).format('DD.MM.YYYY');

    if (!groups.has(label)) groups.set(label, []);
    groups.get(label)!.push(item);
  }
  return groups;
}

export default function HistoryTimeline({ items }: HistoryTimelineProps) {
  if (items.length === 0) {
    return <Empty description={<Text className="text-titanium">Нет изменений</Text>} />;
  }

  const groups = groupByDate(items);

  return (
    <div>
      {Array.from(groups.entries()).map(([dateLabel, dateItems]) => (
        <div key={dateLabel} className="mb-12">
          <Text className="text-gold-bold text-13 d-block mb-8">{dateLabel}</Text>

          {dateItems.map((item) => (
            <div
              key={item.id}
              className="card-detail"
              style={{
                padding: '10px 14px',
                marginBottom: '8px',
                borderRadius: '12px',
                border: '1px solid rgba(255,255,255,0.06)',
                borderLeft: `3px solid ${
                  item.change_type === 'create' ? '#4ECB71'
                  : item.change_type === 'cancel' ? '#ff4d4f'
                  : item.change_type === 'status_change' ? '#C8A977'
                  : item.change_type === 'move' ? '#4ECB71'
                  : '#AAB2BF'
                }`,
              }}
            >
              <Space direction="vertical" size={2} style={{ width: '100%' }}>
                <Space>
                  <Text className="text-small">{CHANGE_ICONS[item.change_type] || '📌'}</Text>
                  <Text className="text-white text-13">
                    {item.changed_by?.full_name || 'Система'}
                  </Text>
                  {item.change_type !== 'create' && (
                    <Text className="text-titanium text-12">
                      изменил(а) {FIELD_LABELS[item.field_name || ''] || item.field_name || 'поле'}
                    </Text>
                  )}
                </Space>

                <Text className="text-titanium text-13">{formatChange(item)}</Text>

                <Text className="text-titanium text-11 opacity-70">
                  {item.created_at ? dayjs(item.created_at).format('HH:mm') : ''}
                </Text>
              </Space>
            </div>
          ))}
        </div>
      ))}
    </div>
  );
}
