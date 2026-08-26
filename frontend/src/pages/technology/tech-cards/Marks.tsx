import React from 'react';
import { ClockCircleOutlined } from '@ant-design/icons';
import { formatDuration } from './types';

export function DurationMark({ minutes }: { minutes: number }) {
  return (
    <span className="tech-card-duration">
      <ClockCircleOutlined />
      {formatDuration(minutes || 0)}
    </span>
  );
}
