/* ============================================================
   ServiceAnalytics — тренды, топ-5, сравнение, прогноз
   ============================================================ */

import React, { useState, useEffect } from 'react';
import { Typography, Card, Row, Col, Spin, Space, Tag, Table } from 'antd';
import {
  BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer,
  LineChart, Line, Legend,
} from 'recharts';

const { Text } = Typography;
const API_BASE = '';

interface TrendPoint { month: string; revenue: number; count: number }
interface Trend { service_id: number; service_name: string; category?: string; monthly: TrendPoint[] }
interface Comparison { service_id: number; service_name: string; current_revenue: number; previous_revenue: number; change_percent: number }
interface TopService { service_id: number; service_name: string; category?: string; total_revenue: number; total_count: number; avg_price: number }
interface ForecastPoint { month: string; forecast: number; lower_bound: number; upper_bound: number }
interface AnalyticsData { trends: Trend[]; comparison: Comparison[]; top_services: TopService[]; forecast: ForecastPoint[] }

async function apiFetch<T>(path: string): Promise<T> {
  const token = localStorage.getItem('token');
  const res = await fetch(`${API_BASE}${path}`, {
    headers: { ...(token ? { Authorization: `Bearer ${token}` } : {}) },
  });
  if (!res.ok) throw new Error(`Ошибка ${res.status}`);
  return res.json();
}

export default function ServiceAnalytics() {
  const [data, setData] = useState<AnalyticsData | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    apiFetch<AnalyticsData>('/api/analytics/services?months=6')
      .then(setData)
      .catch(() => {})
      .finally(() => setLoading(false));
  }, []);

  if (loading) return <Spin />;
  if (!data) return <Text className="text-titanium">Нет данных</Text>;

  // Топ-5 для графика
  const topNames = data.top_services.map((s) => s.service_name.slice(0, 12));

  return (
    <Space direction="vertical" size="large" className="w-full">
      {/* === Топ-5 услуг === */}
      <Card className="card-luxury">
        <Text className="title-gold text-16 d-block mb-8">Топ-5 услуг</Text>
        <ResponsiveContainer width="100%" height={250}>
          <BarChart data={data.top_services}>
            <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
            <XAxis dataKey="service_name" tick={{ fill: '#AAB2BF', fontSize: 11 }} />
            <YAxis tick={{ fill: '#AAB2BF', fontSize: 11 }} />
            <Tooltip
              contentStyle={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px' }}
              labelStyle={{ color: '#FFFFFF' }}
            />
            <Bar dataKey="total_revenue" fill="#C8A977" radius={[6, 6, 0, 0]} name="Выручка" />
          </BarChart>
        </ResponsiveContainer>
      </Card>

      {/* === Тренды по услугам === */}
      {data.trends.length > 0 && (
        <Card className="card-luxury">
          <Text className="title-gold text-16 d-block mb-8">Динамика по месяцам</Text>
          <ResponsiveContainer width="100%" height={250}>
            <LineChart data={data.trends[0]?.monthly || []}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="month" tick={{ fill: '#AAB2BF', fontSize: 11 }} />
              <YAxis tick={{ fill: '#AAB2BF', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px' }}
                labelStyle={{ color: '#FFFFFF' }}
              />
              <Line type="monotone" dataKey="revenue" stroke="#C8A977" strokeWidth={2} dot={{ fill: '#C8A977' }} name="Выручка" />
            </LineChart>
          </ResponsiveContainer>
        </Card>
      )}

      {/* === Сравнение периодов === */}
      {data.comparison.length > 0 && (
        <Card className="card-luxury">
          <Text className="title-gold text-16 d-block mb-8">Сравнение с прошлым месяцем</Text>
          <Table
            dataSource={data.comparison}
            rowKey="service_id"
            pagination={false}
            size="small"
            columns={[
              { title: <Text className="text-titanium text-12">Услуга</Text>, dataIndex: 'service_name',
                render: (v) => <Text className="text-white text-13">{v}</Text> },
              { title: <Text className="text-titanium text-12">Текущий</Text>, dataIndex: 'current_revenue',
                render: (v) => <Text className="text-gold-bold text-13">{v.toLocaleString()} ₽</Text> },
              { title: <Text className="text-titanium text-12">Прошлый</Text>, dataIndex: 'previous_revenue',
                render: (v) => <Text className="text-titanium text-13">{v.toLocaleString()} ₽</Text> },
              { title: <Text className="text-titanium text-12">Изменение</Text>, dataIndex: 'change_percent',
                render: (v) => (
                  <Text className={v >= 0 ? 'text-gold-bold' : 'text-titanium'}>
                    {v >= 0 ? '+' : ''}{v}%
                  </Text>
                )},
            ]}
          />
        </Card>
      )}

      {/* === Прогноз === */}
      {data.forecast.length > 0 && (
        <Card className="card-luxury">
          <Text className="title-gold text-16 d-block mb-8">Прогноз на 3 месяца</Text>
          <ResponsiveContainer width="100%" height={200}>
            <BarChart data={data.forecast}>
              <CartesianGrid strokeDasharray="3 3" stroke="rgba(255,255,255,0.06)" />
              <XAxis dataKey="month" tick={{ fill: '#AAB2BF', fontSize: 11 }} />
              <YAxis tick={{ fill: '#AAB2BF', fontSize: 11 }} />
              <Tooltip
                contentStyle={{ backgroundColor: '#13161A', border: '1px solid rgba(255,255,255,0.06)', borderRadius: '8px' }}
                labelStyle={{ color: '#FFFFFF' }}
              />
              <Bar dataKey="forecast" fill="#C8A977" radius={[6, 6, 0, 0]} name="Прогноз" />
              <Bar dataKey="lower_bound" fill="rgba(200,169,119,0.3)" radius={[6, 6, 0, 0]} name="Нижняя граница" />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      )}
    </Space>
  );
}
