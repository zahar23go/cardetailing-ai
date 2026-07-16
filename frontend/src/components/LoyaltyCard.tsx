/* ============================================================
   LoyaltyCard — карточка уровня лояльности
   ============================================================ */

import React, { useState, useEffect } from 'react';
import { Typography, Card, Spin, Space, Progress } from 'antd';
import { CrownOutlined } from '@ant-design/icons';

const { Text } = Typography;

const API_BASE = '';

const TIER_COLORS: Record<string, string> = {
  bronze: '#CD7F32',
  silver: '#C0C0C0',
  gold: '#FFD700',
  platinum: '#E5E4E2',
};

const TIER_ICONS: Record<string, string> = {
  bronze: '🥉',
  silver: '🥈',
  gold: '🥇',
  platinum: '💎',
};

const TIER_LABELS: Record<string, string> = {
  bronze: 'Бронза',
  silver: 'Серебро',
  gold: 'Золото',
  platinum: 'Платина',
};

interface ClientTier {
  client_id: number;
  full_name: string;
  phone: string;
  tier: string;
  total_spent: number;
  total_visits: number;
  points_balance: number;
  next_tier: string | null;
  next_tier_progress: number;
  next_tier_remaining: number;
}

async function apiFetch<T>(path: string): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) throw new Error(`Ошибка ${res.status}`);
  return res.json();
}

export default function LoyaltyCard() {
  const [data, setData] = useState<ClientTier | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<ClientTier>('/api/loyalty/my-tier')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin />;
  if (!data) return null;

  const color = TIER_COLORS[data.tier] || '#CD7F32';
  const label = TIER_LABELS[data.tier] || data.tier;
  const icon = TIER_ICONS[data.tier] || '🏆';
  const hasNextTier = data.next_tier && data.next_tier_progress < 100;

  return (
    <Card className="card-luxury">
      <Space direction="vertical" size="middle" className="w-full text-center">
        <div style={{ fontSize: '48px' }}>{icon}</div>

        <Text className="title-gold text-24 d-block">{label}</Text>

        <div
          className="card-detail"
          style={{
            padding: '12px',
            borderRadius: '12px',
            border: `1px solid ${color}20`,
          }}
        >
          <Space direction="vertical" size={4} className="w-full text-center">
            <Text className="text-gold-bold text-18">
              {data.points_balance.toLocaleString()} баллов
            </Text>
            <Text className="text-titanium text-13">
              Потрачено: {data.total_spent.toLocaleString()} ₽
            </Text>
            <Text className="text-titanium text-13">
              Визитов: {data.total_visits}
            </Text>
          </Space>
        </div>

        {hasNextTier && data.next_tier && (
          <div className="w-full">
            <div className="flex-space-between mb-8">
              <Text className="text-titanium text-12">
                До уровня {TIER_LABELS[data.next_tier] || data.next_tier}
              </Text>
              <Text className="text-gold-bold text-12">
                {data.next_tier_remaining.toLocaleString()} ₽
              </Text>
            </div>
            <Progress
              percent={Math.round(data.next_tier_progress)}
              strokeColor={TIER_COLORS[data.next_tier] || '#FFD700'}
              trailColor="rgba(255,255,255,0.06)"
              showInfo={true}
              size="small"
            />
          </div>
        )}
      </Space>
    </Card>
  );
}
