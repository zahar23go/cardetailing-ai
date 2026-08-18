import React from 'react';
import { Tooltip } from 'antd';
import { CameraOutlined, ClockCircleOutlined, FileTextOutlined } from '@ant-design/icons';
import Badge from '../../../components/Badge';
import { formatDuration } from './types';

export function cardMarks(record: {
  blocks?: Array<{ description?: string | null; photo_url?: string | null }>;
}) {
  const blocks = record.blocks || [];
  return {
    hasDescription: blocks.some((b) => Boolean(b.description && b.description.trim())),
    hasPhoto: blocks.some((b) => Boolean(b.photo_url)),
  };
}

export function TechCardMarks({
  hasDescription,
  hasPhoto,
}: {
  hasDescription: boolean;
  hasPhoto: boolean;
}) {
  return (
    <span className="tech-card-marks">
      <Tooltip title={hasDescription ? 'Есть описание' : 'Нет описания'}>
        <Badge variant={hasDescription ? 'gold' : 'neutral'} size="sm">
          <FileTextOutlined />
        </Badge>
      </Tooltip>
      <Tooltip title={hasPhoto ? 'Есть фото' : 'Нет фото'}>
        <Badge variant={hasPhoto ? 'gold' : 'neutral'} size="sm">
          <CameraOutlined />
        </Badge>
      </Tooltip>
    </span>
  );
}

export function DurationMark({ minutes }: { minutes: number }) {
  return (
    <Badge variant="gold" size="sm" className="tech-card-duration">
      <ClockCircleOutlined /> {formatDuration(minutes || 0)}
    </Badge>
  );
}
